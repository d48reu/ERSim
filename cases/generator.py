import json
import os
import random
import re
from datetime import datetime

from openai import OpenAI
from pydantic import ValidationError

from .schema import ShiftCasePool, GeneratedCase
from .prompts import (
    CASE_GENERATION_SYSTEM_PROMPT,
    build_case_generation_prompt,
    TEMPLATE_CASE_SYSTEM_PROMPT,
    build_template_case_prompt,
)
from .case_templates import CASE_TEMPLATES, get_random_templates

from llm import get_client, get_model


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
    model: str | None = None,
    max_retries: int = 2,
) -> ShiftCasePool:
    """
    Pre-generate the full case pool for a shift in batches.
    Batching avoids output token truncation on large case counts.
    Run this before the shift starts. Never during play.
    """
    client = get_client()
    model = get_model("generation", override=model)

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


# ======================================================================
# Template-based case generation (new)
# ======================================================================

def _generate_single_from_template(
    client: OpenAI,
    template: dict,
    case_id: str,
    shift_context: dict | None,
    model: str,
    max_retries: int = 2,
) -> dict | None:
    """
    Generate one case from a template seed.
    Returns a validated case dict, or None if generation fails.
    """
    user_prompt = build_template_case_prompt(
        template=template,
        case_id=case_id,
        shift_context=shift_context,
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"    template case {case_id} retry {attempt}/{max_retries}...")

            response = client.chat.completions.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": TEMPLATE_CASE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )

            raw = response.choices[0].message.content
            cleaned = _clean_json(raw)
            data = json.loads(cleaned)

            # Force the correct case_id
            data["case_id"] = case_id

            validated = GeneratedCase.model_validate(data)
            return validated.model_dump()

        except (json.JSONDecodeError, ValueError, ValidationError) as e:
            last_error = e
            if attempt < max_retries:
                user_prompt += f"""

CORRECTION NEEDED
-----------------
Previous attempt failed: {e}

Return valid JSON only. One GeneratedCase object.
No markdown. No explanation. Raw JSON only.
"""

    print(f"    WARNING: template case {case_id} failed after "
          f"{max_retries + 1} attempts: {last_error}")
    return None


# Session-level template usage tracking.
# Stores indices of templates used in recent shifts to avoid repeats.
# Resets when the pool is exhausted (all templates used).
_recently_used_templates: set[int] = set()


def generate_shift_cases_from_templates(
    num_cases: int = 3,
    shift_context: dict | None = None,
    model: str | None = None,
    max_retries: int = 2,
    ensure_acuity_mix: bool = True,
) -> ShiftCasePool:
    """
    Generate cases by randomly selecting from the template bank and
    having the LLM flesh each one out individually.

    This produces much higher variety than free-form batch generation
    because each case starts from a different medical template with
    randomized demographics.

    Tracks recently-used templates across shifts within the same process
    to avoid repeats (e.g., herpes zoster 3x in 6 runs). Resets when
    the pool is exhausted.

    Args:
        num_cases: How many cases to generate (default 3 for a shift)
        shift_context: Optional shift context dict
        model: LLM model override
        max_retries: Retries per case on validation failure
        ensure_acuity_mix: If True and num_cases >= 3, ensures at least
            one high-acuity and one lower-acuity case in the mix

    Returns:
        ShiftCasePool with the generated cases
    """
    global _recently_used_templates

    client = get_client()
    model = get_model("generation", override=model)

    shift_id = f"SHIFT_{datetime.now().strftime('%Y%m%d_%H%M')}"
    if shift_context:
        shift_context = {**shift_context, "shift_id": shift_id}

    # Reset recency tracking if pool is nearly exhausted
    # (leave at least num_cases * 2 templates available)
    available_count = len(CASE_TEMPLATES) - len(_recently_used_templates)
    if available_count < num_cases * 2:
        print(f"  Template recency pool exhausted ({available_count} left), resetting...")
        _recently_used_templates = set()

    # Combine session-level recency avoidance with within-shift dedup
    avoid = set(_recently_used_templates)

    # Select templates with optional acuity-mix enforcement
    if ensure_acuity_mix and num_cases >= 3:
        # Get at least one high-acuity (1-2), one mid (3), one lower (4-5)
        high = [(i, t) for i, t in enumerate(CASE_TEMPLATES)
                if t["acuity_range"][0] <= 2 and i not in avoid]
        mid = [(i, t) for i, t in enumerate(CASE_TEMPLATES)
               if 3 in range(t["acuity_range"][0], t["acuity_range"][1] + 1)
               and i not in avoid]
        low = [(i, t) for i, t in enumerate(CASE_TEMPLATES)
               if t["acuity_range"][1] >= 4 and i not in avoid]

        picks: list[tuple[int, dict]] = []
        used_indices: set[int] = set(avoid)

        # One from each bucket
        for bucket in [high, mid, low]:
            available = [(i, t) for i, t in bucket if i not in used_indices]
            if available:
                choice = random.choice(available)
                picks.append(choice)
                used_indices.add(choice[0])
            if len(picks) >= num_cases:
                break

        # Fill remaining from full pool
        if len(picks) < num_cases:
            extras = get_random_templates(
                num_cases - len(picks), avoid_indices=used_indices
            )
            picks.extend(extras)
    else:
        picks = get_random_templates(num_cases, avoid_indices=avoid)

    # Generate each case
    all_cases: list[dict] = []
    for seq, (template_idx, template) in enumerate(picks, start=1):
        case_id = f"{shift_id}_{seq:02d}"
        diag = template["true_diagnosis"][:50]
        print(f"  Case {seq}/{len(picks)}: {diag}...")

        case = _generate_single_from_template(
            client=client,
            template=template,
            case_id=case_id,
            shift_context=shift_context,
            model=model,
            max_retries=max_retries,
        )

        if case is not None:
            all_cases.append(case)
        else:
            # Fallback: try another template
            print(f"    Falling back to alternate template...")
            used = {p[0] for p in picks}
            alts = get_random_templates(1, avoid_indices=used)
            if alts:
                alt_idx, alt_template = alts[0]
                alt_case = _generate_single_from_template(
                    client=client,
                    template=alt_template,
                    case_id=case_id,
                    shift_context=shift_context,
                    model=model,
                    max_retries=max_retries,
                )
                if alt_case is not None:
                    all_cases.append(alt_case)

    if not all_cases:
        raise RuntimeError(
            "Template-based generation produced zero valid cases. "
            "Check LLM connectivity and model availability."
        )

    # Track which templates were used this shift for cross-shift dedup
    for template_idx, _ in picks:
        _recently_used_templates.add(template_idx)

    # Re-number sequentially
    for i, case in enumerate(all_cases):
        case["case_id"] = f"{shift_id}_{i + 1:02d}"

    pool = ShiftCasePool.model_validate({
        "shift_id": shift_id,
        "cases": all_cases,
    })
    return pool
