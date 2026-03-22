"""
Combined shift test — the real game loop.

Loads 3 cases, assigns residents, starts a shift.
You manage attention across multiple bays simultaneously.
Timer ticks. Residents act autonomously when you're away too long.

Run from ERSim directory:
    python -m shift.test_shift

Commands:
    go <number>          move to a bay  (e.g. 'go 1', 'go 2', 'go 3')
    <message>            talk to patient (free text, no slash needed)
    exam <maneuver>      physical exam
    test <name>          order a test
    ask <question>       ask resident a question
    resident             get resident's current read on this case
    family               bring family member in
    chart                see what's been revealed
    resolve <dispo>      close case (discharge / admit-floor / admit-icu)
    leave                step out of current bay
    status               overview of all bays
    quit                 end shift
"""

import json
import sys
import random
import argparse
from cases.schema import GeneratedCase
from residents.schema import select_shift_roster
from .shift import Shift


def _load_legacy_cases(num_bays: int) -> list[GeneratedCase]:
    """Load cases from pre-generated test_output.json (legacy mode)."""
    try:
        with open("test_output.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("No test_output.json found. Run test_generation first.")
        sys.exit(1)

    cases_raw = data.get("cases", [])
    if len(cases_raw) < num_bays:
        num_bays = len(cases_raw)

    # Pick a mix of acuity levels for an interesting session
    by_acuity: dict[int, list] = {}
    for c in cases_raw:
        a = c["presenting_layer"]["acuity"]
        by_acuity.setdefault(a, []).append(c)

    if num_bays == 3 and len(cases_raw) >= num_bays:
        high   = by_acuity.get(1, []) + by_acuity.get(2, [])
        mid    = by_acuity.get(3, [])
        low    = by_acuity.get(4, []) + by_acuity.get(5, [])
        pool   = [high, mid, low]
        picks  = []
        for bucket in pool:
            if bucket:
                picks.append(random.choice(bucket))
        remaining = [c for c in cases_raw if c not in picks]
        while len(picks) < num_bays and remaining:
            pick = random.choice(remaining)
            picks.append(pick)
            remaining.remove(pick)
    else:
        picks = random.sample(cases_raw, min(num_bays, len(cases_raw)))

    return [GeneratedCase.model_validate(c) for c in picks]


def _generate_template_cases(num_bays: int, model: str) -> list[GeneratedCase]:
    """Generate fresh cases from the template bank (new default)."""
    from cases.generator import generate_shift_cases_from_templates

    shift_context = {
        "day_of_week": random.choice([
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]),
        "shift_type": random.choice(["day", "evening", "night"]),
        "season": random.choice(["spring", "summer", "fall", "winter"]),
        "weeks_into_campaign": 1,
        "recent_outcomes": [],
    }

    print(f"Generating {num_bays} cases from template bank...")
    pool = generate_shift_cases_from_templates(
        num_cases=num_bays,
        shift_context=shift_context,
        model=model,
    )
    return pool.cases


def run(num_bays: int = 3, model: str = "anthropic/claude-haiku-4-5",
        legacy: bool = False):
    # Load or generate cases
    if legacy:
        print("Using legacy mode: loading from test_output.json")
        cases = _load_legacy_cases(num_bays)
    else:
        cases = _generate_template_cases(num_bays, model)

    if not cases:
        print("No cases available. Exiting.")
        sys.exit(1)

    residents = select_shift_roster()  # Picks 3 of 6 with PGY balance

    shift = Shift(cases=cases, residents=residents, model=model)
    shift.setup()

    print("\nType 'help' for commands. Type 'quit' to end shift.\n")

    while True:
        # Show any test results that came in
        results = shift.check_pending_results()
        for r in results:
            print(f"\n  ** RESULT IN:\n{r}\n")

        # Show any warning notifications
        warnings = shift.check_warning_notifications()
        for w in warnings:
            print(f"\n  ⚠ WARNING:\n{w}\n")

        # Show any autonomous action notifications
        notes = shift.check_autonomous_notifications()
        for note in notes:
            print(f"\n  !! RESIDENT ACTED:\n{note}\n")

        # Prompt
        bay_indicator = f" [{shift.active_bay_id}]" if shift.active_bay_id else ""
        try:
            raw = input(f"\n[YOU{bay_indicator}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Shift ended]")
            break

        if not raw:
            continue

        # Strip leading slash — support both 'exam abdomen' and '/exam abdomen'
        if raw.startswith("/"):
            raw = raw[1:]

        # @ prefix = talk to resident, e.g. "@what's your read?"
        if raw.startswith("@"):
            print(shift.ask_resident(raw[1:].strip()))
            continue

        cmd = raw.lower()
        first_word = cmd.split()[0]
        rest = raw[len(first_word):].strip()

        # ---------------------------------------------------------------
        # Navigation
        # ---------------------------------------------------------------
        if first_word in ("go", "bay", "enter"):
            target = rest or (raw.split()[-1] if raw.split() else "")
            print(shift.go(target))

        elif first_word == "leave":
            print(shift.leave())

        elif first_word in ("status", "overview", "floor"):
            print(shift.status())

        # ---------------------------------------------------------------
        # In-bay actions
        # ---------------------------------------------------------------
        elif first_word == "exam":
            print(shift.exam(rest))

        elif first_word == "test":
            print(shift.test(rest))

        elif first_word in ("1", "2", "3", "4") and len(cmd.split()) == 1:
            # Could be plan approval or pivot suggestion — plan takes priority
            bay = shift._require_active_bay()
            n = int(first_word)
            if bay and bay._pending_plan:
                print(shift.approve_plan(n))
            else:
                print(shift.follow_suggestion(n))

        elif first_word == "add":
            # Approve plan + add something (free text)
            print(shift.approve_plan(2, addendum=rest))

        elif first_word == "redirect":
            # Change the direction of the plan (free text)
            print(shift.approve_plan(3, addendum=rest))

        elif first_word in ("bundle", "order"):
            items = [t.strip() for t in rest.split(",") if t.strip()]
            if not items:
                print("Usage: bundle <test1>, <test2>, ...")
            else:
                print(shift.bundle_test(items))

        elif first_word in ("ask",):
            print(shift.ask_resident(rest))

        elif first_word in ("resident", "res"):
            print(shift.get_resident_read())

        elif first_word == "family":
            print(shift.family())

        elif first_word == "chart":
            print(shift.chart())

        elif first_word in ("resolve", "discharge", "admit", "dispo"):
            dispo = rest if rest else "discharge"
            print(shift.resolve(dispo))

        # ---------------------------------------------------------------
        # Meta
        # ---------------------------------------------------------------
        elif first_word in ("help", "?", "commands"):
            print("""
Commands:
  go <number>       move to a bay (e.g. go 1, go 2, go 3)
  leave             step out of current bay
  status            overview of all bays and timers
  chart             see what's been revealed in current bay
  exam <maneuver>   physical exam (e.g. exam abdomen)
  1 / 2 / 3 / 4    respond to plan (approve/add/redirect/hold) or pivot (go ahead/redirect)
  add <text>        approve plan and add something in plain language
  redirect <text>   change the direction of the plan
  test <name>       order test manually (e.g. test troponin)
  bundle <t1>, <t2> order multiple tests at once (comma-separated)
  ask <question>    ask resident a question
  @<question>       shorthand for ask (e.g. @what's your read?)
  resident          get resident's unprompted assessment
  family            bring family member into bay
  resolve <dispo>   close case (discharge / admit-floor / admit-icu / OR)
  quit              end shift

Free text (no command prefix) = talk to the patient.
            """)

        elif first_word in ("quit", "exit", "end"):
            print("\n--- SHIFT SUMMARY ---")
            resolved = [b for b in shift.bays.values()
                       if b.status.value == "resolved"]
            unresolved = [b for b in shift.bays.values()
                         if b.status.value != "resolved"]
            print(f"Resolved: {len(resolved)}/{len(shift.bays)}")
            for bay in resolved:
                print(f"  {bay.bay_id}: {bay.patient_name} — {bay.disposition}")
            if unresolved:
                print(f"Unresolved: {len(unresolved)}")
                for bay in unresolved:
                    correct = bay.case.outcome_trajectory.disposition
                    print(f"  {bay.bay_id}: {bay.patient_name} "
                          f"— should have been {correct}")
            break

        else:
            # Free text = talk to patient
            if shift.active_bay_id:
                print(shift.talk(raw))
            else:
                print("You're not in a bay. Use 'go <number>' to enter one.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bays", type=int, default=3,
                        help="Number of simultaneous bays (default: 3)")
    parser.add_argument("--model", type=str,
                        default="anthropic/claude-haiku-4-5")
    parser.add_argument("--legacy", action="store_true",
                        help="Use legacy mode: load from test_output.json "
                             "instead of generating from template bank")
    args = parser.parse_args()
    run(num_bays=args.bays, model=args.model, legacy=args.legacy)
