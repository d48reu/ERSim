import json
import os
import re
from datetime import datetime

from openai import OpenAI
from pydantic import ValidationError

from .schema import ShiftCasePool, GeneratedCase
from .prompts import CASE_GENERATION_SYSTEM_PROMPT, build_case_generation_prompt


def _get_client():
    """OpenRouter client — supports Claude models without a direct Anthropic key."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            for line in open(env_path):
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not found. "
            "Set it in your environment or ~/.hermes/.env"
        )
    return OpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
    )


def _clean_json(raw: str) -> str:
    """Strip markdown fences and whitespace from model output."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()


# Safe per-batch size: 4 cases per batch.
# Haiku is verbose — 5 cases at full schema depth hits 12k tokens.
# 4 cases keeps us well inside the limit with room for retries.
_BATCH_SIZE = 4


def _generate_batch(
    client: OpenAI,
    world_state: str,
    hospital_profile: str,
    shift_context: dict,
    batch_num: int,
    batch_size: int,
    acuity_instruction: str,
    model: str,
    max_retries: int,
) -> list[dict]:
    """
    Generate one batch of cases. Returns a list of raw case dicts.
    Retries on JSON/validation error up to max_retries times.
    """
    shift_id = shift_context["shift_id"]
    offset = (batch_num - 1) * _BATCH_SIZE

    # Build a batch-specific prompt
    batch_context = {
        **shift_context,
        "batch_instruction": (
            f"Generate exactly {batch_size} cases for this batch. "
            f"Number them starting at {offset + 1} "
            f"(case_ids: {shift_id}_{offset+1:02d} through "
            f"{shift_id}_{offset+batch_size:02d}).\n"
            f"Acuity target for this batch: {acuity_instruction}"
        ),
    }

    user_prompt = build_case_generation_prompt(
        world_state=world_state,
        hospital_profile=hospital_profile,
        shift_context=batch_context,
        num_cases=batch_size,
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"    batch {batch_num} retry {attempt}/{max_retries}...")

            response = client.chat.completions.create(
                model=model,
                max_tokens=12000,
                messages=[
                    {"role": "system", "content": CASE_GENERATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )

            raw = response.choices[0].message.content
            cleaned = _clean_json(raw)
            data = json.loads(cleaned)

            # Accept either a ShiftCasePool envelope or a bare list
            if isinstance(data, dict) and "cases" in data:
                cases = data["cases"]
            elif isinstance(data, list):
                cases = data
            else:
                raise ValueError(f"Unexpected JSON shape: {type(data)}")

            # Patch case_ids in case model got them wrong
            for i, case in enumerate(cases):
                expected_id = f"{shift_id}_{offset + i + 1:02d}"
                if not case.get("case_id"):
                    case["case_id"] = expected_id

            # Validate each case individually so one bad case doesn't
            # kill the whole batch
            validated = []
            for case in cases:
                try:
                    validated.append(GeneratedCase.model_validate(case).model_dump())
                except ValidationError as ve:
                    print(f"    WARNING: skipping invalid case {case.get('case_id', '?')}: {ve}")

            if not validated:
                raise ValueError("Batch produced zero valid cases after validation")

            return validated

        except (json.JSONDecodeError, ValueError, ValidationError) as e:
            last_error = e
            if attempt < max_retries:
                user_prompt += f"""

CORRECTION NEEDED
-----------------
Previous attempt failed: {e}

Return valid JSON only. Either a ShiftCasePool object with a "cases"
array, or a bare JSON array of GeneratedCase objects.
No markdown. No explanation. Raw JSON only.
"""

    raise RuntimeError(
        f"Batch {batch_num} failed after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


# Acuity targets per batch for a 14-case shift (4 cases/batch = 4 batches):
#   Batch 1 (4): 1x acuity 1-2, 2x acuity 3, 1x acuity 4
#   Batch 2 (4): 1x acuity 2, 1x acuity 3, 1x acuity 4, 1x acuity 5
#   Batch 3 (4): 1x acuity 2, 2x acuity 3, 1x acuity 4
#   Batch 4 (2): 1x acuity 4, 1x acuity 5
_BATCH_ACUITY = [
    "1 case acuity 1 or 2 (high stakes, time sensitive), 2 cases acuity 3 (require real work), 1 case acuity 4 (routine)",
    "1 case acuity 2 (emergent), 1 case acuity 3 (urgent), 1 case acuity 4 (less urgent), 1 case acuity 5 (non-urgent contrast)",
    "1 case acuity 2 (emergent), 2 cases acuity 3 (urgent), 1 case acuity 4 (routine)",
    "1 case acuity 4 (less urgent), 1 case acuity 5 (non-urgent — genuinely minor, contrast case)",
]


def generate_shift_cases(
    world_state: str,
    hospital_profile: str,
    shift_context: dict,
    num_cases: int = 14,
    model: str = "anthropic/claude-opus-4-5",
    max_retries: int = 2,
) -> ShiftCasePool:
    """
    Pre-generate the full case pool for a shift in batches.
    Batching avoids output token truncation on large case counts.
    Run this before the shift starts. Never during play.
    """
    client = _get_client()

    shift_id = f"SHIFT_{datetime.now().strftime('%Y%m%d_%H%M')}"
    shift_context = {**shift_context, "shift_id": shift_id}

    # Split into batches of _BATCH_SIZE
    batches = []
    remaining = num_cases
    batch_num = 1
    while remaining > 0:
        size = min(_BATCH_SIZE, remaining)
        batches.append((batch_num, size))
        remaining -= size
        batch_num += 1

    all_cases = []
    for i, (bnum, bsize) in enumerate(batches):
        acuity_instr = _BATCH_ACUITY[i] if i < len(_BATCH_ACUITY) else \
            "mix of acuity 2-4, at least one routine case"
        print(f"  Batch {bnum}/{len(batches)} ({bsize} cases)...")
        cases = _generate_batch(
            client=client,
            world_state=world_state,
            hospital_profile=hospital_profile,
            shift_context=shift_context,
            batch_num=bnum,
            batch_size=bsize,
            acuity_instruction=acuity_instr,
            model=model,
            max_retries=max_retries,
        )
        all_cases.extend(cases)

    # Re-number case_ids sequentially across the merged pool
    for i, case in enumerate(all_cases):
        case["case_id"] = f"{shift_id}_{i+1:02d}"

    pool = ShiftCasePool.model_validate({
        "shift_id": shift_id,
        "cases": all_cases,
    })
    return pool
