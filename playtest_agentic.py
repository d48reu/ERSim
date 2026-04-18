"""ERSim agentic playtester.

Runs a full shift where the "player" is an LLM (Haiku) that sees only what a
human attending sees — no ground-truth peek. The only things this script
pulls from the Shift that a real UI wouldn't show are:

  - the final `shift.debrief()` (needed for scoring)
  - `shift._last_debrief_meta` (already populated by debrief())
  - the list of bay IDs (the sidebar shows these anyway)

The agent picks one action per turn from the real command surface:
  go <bay> / leave / status / chart
  talk <...> / exam <region> / test <name> / family
  ask <question for resident>
  approve <1-4>  (when a plan prompt is open)
  respond <bay> <1-2>  (when a cross-bay pivot is queued)
  resolve <disposition>
  quit

Usage:
    python playtest_agentic.py                    # one balanced-strategy run
    python playtest_agentic.py --runs 3           # three back-to-back runs
    python playtest_agentic.py --max-turns 50     # override default cap
    python playtest_agentic.py --model anthropic/claude-haiku-4-5

Scores each run: grade, dispo accuracy, trap catch, autonomous fires, thin-chart.
Emits a machine-readable JSON line per run at the end for easy aggregation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent
os.chdir(_ROOT)

from cases.generator import generate_shift_cases_from_templates
from cases.schema import GeneratedCase
from llm import get_client, get_model
from shift.shift import Shift


_ALLOWED_DISPOS = {
    "discharge", "admit-floor", "admit-icu", "or", "cath-lab", "transfer", "ama",
}


# ---------------------------------------------------------------------------
# System prompt — the only ground-truth-free briefing the agent gets
# ---------------------------------------------------------------------------

_AGENT_SYSTEM_PROMPT = """You are the attending physician on a 3-bay shift at a county ED.
Three residents are presenting cases to you. Your job is to listen, challenge frames when
they don't fit the data, build enough signal to close each case correctly, and keep the
department stable. You cannot see correct diagnoses or dispositions — work from what the
patient says, the resident's read, the exam, and returned test results.

AVAILABLE ACTIONS (one per turn):
  {"action": "go",       "args": "1" | "2" | "3"}   - enter a bay
  {"action": "leave"}                                - step out of the current bay
  {"action": "status"}                               - board overview
  {"action": "chart"}                                - full chart of the current bay
  {"action": "talk",     "args": "<message>"}        - talk to the patient
  {"action": "exam",     "args": "<region>"}         - focused exam (general/chest/abdomen/neuro/skin/cardiac/extremities)
  {"action": "test",     "args": "<test name>"}      - order a single test
  {"action": "ask",      "args": "<question>"}       - ask the resident in the current bay
  {"action": "family"}                               - bring family in
  {"action": "approve",  "args": "1" | "2" | "3" | "4"} - respond to a pending plan (1=approve, 2=approve+add, 3=redirect, 4=hold)
  {"action": "respond",  "args": "<bay_id> <1|2>"}   - respond to a cross-bay resident pivot (1=approve, 2=redirect)
  {"action": "resolve",  "args": "discharge|admit-floor|admit-icu|OR|cath-lab|transfer|AMA"}  - close the current bay
  {"action": "quit"}                                  - end the shift (only when every bay is closed)

STRATEGY GUIDANCE:
- Start by checking status, then enter the most acute bay first.
- Each attending action ticks a timer on every other supervised bay. Don't linger.
- If a resident's read sounds smooth but the data is thin, ask one direct question before approving.
- You cannot resolve a bay before doing something in it — at minimum, hear the resident, talk to
  the patient, or order a test.
- A well-played shift resolves all three bays in 20-35 actions.

OUTPUT FORMAT:
Return a single JSON object with "action" and optionally "args" — nothing else, no prose. Example:
  {"action": "go", "args": "1"}
  {"action": "talk", "args": "When did the pain start?"}
  {"action": "resolve", "args": "admit-floor"}
"""


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _first_json_object(raw: str) -> Optional[str]:
    start = raw.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                return raw[start:i + 1]
    return None


def _parse_agent_json(raw: str) -> dict:
    """Robust JSON parser for agent turn output."""
    cleaned = _strip_fences(raw)
    for candidate in (cleaned, _first_json_object(raw) or ""):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "action" in parsed:
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    return {"action": "status"}  # safe no-op fallback


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

class AgentPlayer:
    def __init__(self, model: str | None = None, verbose: bool = False):
        self.model = model or get_model("resident_live")
        self.client = get_client("resident_live")
        self.history: list[tuple[str, str]] = []  # (action, engine_result)
        self.verbose = verbose

    def _build_user_prompt(self, initial_status: str) -> str:
        lines = ["SHIFT SO FAR:\n"]
        if not self.history:
            lines.append(initial_status)
        else:
            # Keep a sliding window — last 8 turns is plenty of context
            recent = self.history[-8:]
            for i, (action, result) in enumerate(recent):
                lines.append(f"\n--- turn {len(self.history) - len(recent) + i + 1} ---")
                lines.append(f"you: {action}")
                # Clip engine result to keep tokens reasonable
                lines.append(f"engine: {result[:900]}")
        lines.append("\n\nYour next action (JSON only):")
        return "\n".join(lines)

    def decide(self, initial_status: str) -> dict:
        prompt = self._build_user_prompt(initial_status)
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=200,
            messages=[
                {"role": "system", "content": _AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content or ""
        decision = _parse_agent_json(raw)
        if self.verbose:
            print(f"  AGENT: {decision}")
        return decision

    def record(self, action: str, result: str) -> None:
        self.history.append((action, result))


# ---------------------------------------------------------------------------
# Action dispatch
# ---------------------------------------------------------------------------

def _normalize_dispo(raw: str) -> Optional[str]:
    canon = raw.lower().replace("-", "").replace("_", "").replace(" ", "")
    mapping = {
        "discharge": "discharge", "home": "discharge",
        "admitfloor": "admit-floor", "floor": "admit-floor", "admit": "admit-floor",
        "admiticu": "admit-icu", "icu": "admit-icu",
        "or": "OR", "ortho": "OR",
        "cathlab": "cath-lab", "cath": "cath-lab",
        "transfer": "transfer",
        "ama": "AMA",
    }
    return mapping.get(canon)


def _check_and_append(shift: Shift, bucket: list[str]) -> None:
    """Drain pending results / warnings / autonomous notifications into a text bucket."""
    pending = shift.check_pending_results()
    for note in pending.get("notifications", []):
        bucket.append(f"[RESULT] {note}")
    for decision in pending.get("decisions", []):
        bucket.append(f"[CROSS-BAY NEEDS DECISION] {decision['text']}  (respond <{decision['bay_id']}> 1 or 2)")
    for warn in shift.check_warning_notifications():
        bucket.append(f"[WARNING] {warn}")
    for auto in shift.check_autonomous_notifications():
        bucket.append(f"[AUTONOMOUS] {auto}")


def _all_resolved(shift: Shift) -> bool:
    return all(bay.status.value == "resolved" for bay in shift.bays.values())


def _execute(shift: Shift, decision: dict) -> tuple[str, str]:
    """Run the decision and return (action_label, engine_text)."""
    action = str(decision.get("action", "")).strip().lower()
    args = str(decision.get("args", "")).strip()

    notices: list[str] = []

    def _wrap(text: str) -> str:
        _check_and_append(shift, notices)
        parts = [text] if text else []
        parts.extend(notices)
        return "\n".join(parts)

    if action == "go":
        bay_key = args.replace("Bay ", "").replace("bay ", "").strip()
        if not bay_key:
            return ("go", "No bay specified.")
        result = shift.go(bay_key if bay_key.startswith("Bay") else f"Bay {bay_key}")
        return (f"go {bay_key}", _wrap(result))

    if action == "leave":
        return ("leave", _wrap(shift.leave()))

    if action == "status":
        return ("status", _wrap(shift.status()))

    if action == "chart":
        return ("chart", _wrap(shift.chart()))

    if action == "talk":
        if not args:
            return ("talk", "No message given.")
        return (f"talk {args[:60]}", _wrap(shift.talk(args)))

    if action == "exam":
        if not args:
            return ("exam", "No region given.")
        return (f"exam {args[:40]}", _wrap(shift.exam(args)))

    if action == "test":
        if not args:
            return ("test", "No test given.")
        return (f"test {args[:40]}", _wrap(shift.test(args)))

    if action == "ask":
        if not args:
            return ("ask", "No question given.")
        return (f"ask {args[:60]}", _wrap(shift.ask_resident(args)))

    if action == "family":
        return ("family", _wrap(shift.family()))

    if action == "approve":
        try:
            choice = int(args.split()[0])
        except (ValueError, IndexError):
            return ("approve", "Invalid approval choice.")
        return (f"approve {choice}", _wrap(shift.approve_plan(choice)))

    if action == "respond":
        parts = args.split()
        if len(parts) < 2:
            return ("respond", "Need bay and choice.")
        bay_id = parts[0] if parts[0].startswith("Bay") else f"Bay {parts[0]}"
        try:
            choice = int(parts[1])
        except ValueError:
            return ("respond", "Invalid choice.")
        return (f"respond {bay_id} {choice}", _wrap(shift.respond_cross_bay(bay_id, choice)))

    if action == "resolve":
        dispo = _normalize_dispo(args)
        if not dispo:
            return ("resolve", f"Unknown disposition: {args!r}. Choose from discharge/admit-floor/admit-icu/OR/cath-lab/transfer/AMA.")
        return (f"resolve {dispo}", _wrap(shift.resolve(dispo)))

    if action == "quit":
        return ("quit", _wrap("Agent requested quit."))

    # Unknown action — fall back to status to keep the shift moving
    return (f"unknown:{action}", _wrap(shift.status()))


# ---------------------------------------------------------------------------
# Shift runner
# ---------------------------------------------------------------------------

def run_shift(
    cases: list[GeneratedCase],
    *,
    max_turns: int = 45,
    model: str | None = None,
    verbose: bool = False,
    log_path: Path | None = None,
) -> dict:
    """Play a single shift with an LLM agent. Returns scoring dict."""
    shift = Shift(cases=cases, model=model)
    shift.setup()

    agent = AgentPlayer(model=model, verbose=verbose)
    initial_status = shift.status()
    # Seed the history with the initial board so the first decision has context
    agent.history.append(("<shift start>", initial_status))

    log: list[str] = [f"\n=== AGENTIC PLAYTEST ({len(cases)} bays, max {max_turns} turns) ===\n"]
    log.append(initial_status)

    turns_used = 0
    quit_requested = False
    for turn in range(max_turns):
        turns_used = turn + 1
        if _all_resolved(shift):
            log.append("\nAll bays resolved.")
            break

        decision = agent.decide(initial_status)
        if decision.get("action") == "quit":
            if _all_resolved(shift):
                quit_requested = True
                break
            # Ignore premature quit — nudge back with status
            log.append("\n[agent tried to quit with bays open — forced status]")
            agent.record("<forced status>", shift.status())
            continue

        label, result = _execute(shift, decision)
        log.append(f"\n--- turn {turns_used} ---\n> {label}\n{result[:800]}")
        agent.record(label, result)

        if verbose:
            print(f"turn {turns_used}: {label}  -> {result[:120]}")

    # End-of-shift debrief
    debrief = shift.debrief()
    log.append("\n" + debrief)
    meta = dict(getattr(shift, "_last_debrief_meta", {}))

    if log_path:
        log_path.write_text("\n".join(log), encoding="utf-8")

    summary = {
        "grade": meta.get("grade", "?"),
        "dispo_accuracy_pct": meta.get("metrics", {}).get("disposition_accuracy", 0),
        "resolved_cases": meta.get("metrics", {}).get("resolved_cases", 0),
        "total_cases": meta.get("metrics", {}).get("total_cases", len(cases)),
        "trap_full": meta.get("metrics", {}).get("trap_cases_fully_caught", 0),
        "trap_partial": meta.get("metrics", {}).get("trap_cases_partially_recovered", 0),
        "autonomous_actions": meta.get("metrics", {}).get("autonomous_actions", 0),
        "clinical_depth": meta.get("metrics", {}).get("clinical_depth", 0),
        "attention_distribution": meta.get("metrics", {}).get("attention_distribution", "unknown"),
        "turns_used": turns_used,
        "quit_requested": quit_requested,
        "headline": meta.get("headline", ""),
        "watchout": meta.get("watchout", ""),
    }
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-driven agentic playtester for ERSim.")
    parser.add_argument("--runs", type=int, default=1, help="Number of shifts to play (default 1).")
    parser.add_argument("--max-turns", type=int, default=45, help="Max actions per shift (default 45).")
    parser.add_argument("--model", type=str, default=None, help="Override model id (default: resident_live).")
    parser.add_argument("--num-cases", type=int, default=3, help="Cases per shift (default 3).")
    parser.add_argument("--verbose", action="store_true", help="Print each turn inline.")
    parser.add_argument("--log-dir", type=str, default=None, help="Directory to write full turn logs.")
    args = parser.parse_args()

    log_dir = Path(args.log_dir) if args.log_dir else None
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for run_idx in range(args.runs):
        run_label = f"run-{run_idx + 1}"
        print(f"\n### {run_label} — generating {args.num_cases} cases...", flush=True)
        pool = generate_shift_cases_from_templates(num_cases=args.num_cases)
        cases = [GeneratedCase.model_validate(c) for c in pool.cases]
        for i, c in enumerate(cases):
            pl = c.presenting_layer
            print(f"  Bay {i+1}: {c.patient_profile.first_name} {c.patient_profile.last_name}  "
                  f"[{pl.acuity.value}] {pl.chief_complaint[:60]}")

        log_path = log_dir / f"{run_label}.log" if log_dir else None
        t0 = time.time()
        summary = run_shift(
            cases,
            max_turns=args.max_turns,
            model=args.model,
            verbose=args.verbose,
            log_path=log_path,
        )
        summary["run_label"] = run_label
        summary["elapsed_sec"] = round(time.time() - t0, 1)
        results.append(summary)

        print(
            f"\n{run_label}: grade={summary['grade']}  "
            f"dispo={summary['dispo_accuracy_pct']}%  "
            f"resolved={summary['resolved_cases']}/{summary['total_cases']}  "
            f"trap={summary['trap_full']} full / {summary['trap_partial']} partial  "
            f"auto={summary['autonomous_actions']}  "
            f"turns={summary['turns_used']}  "
            f"{summary['elapsed_sec']}s"
        )
        if summary["watchout"]:
            print(f"  Watchout: {summary['watchout']}")

    # Machine-readable summary line per run
    print("\n### JSON results ###")
    for r in results:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
