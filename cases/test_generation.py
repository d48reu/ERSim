"""
Test harness for case generation.

Run from the ERSim directory:
    python -m cases.test_generation

Optional args:
    python -m cases.test_generation --cases 4 --model anthropic/claude-haiku-4-5
    python -m cases.test_generation --cases 14 --model anthropic/claude-opus-4-5

Full JSON saved to test_output.json for manual review.
"""

import json
import sys
import argparse
from .generator import generate_shift_cases


SAMPLE_WORLD_STATE = """
SITUATION REPORT — Riverside General Emergency Department
Week of: Campaign Week 1

Community context:
Riverside is a working-class neighborhood adjacent to a mid-size
industrial corridor. Manufacturing employment has declined over the
past decade. Roughly 35% of patients are uninsured or underinsured.
The hospital serves as the primary care provider for a significant
portion of the catchment area — patients who have no other regular
access to the system.

Active conditions:
Late autumn. Respiratory season beginning. Early uptick in
influenza-like illness over the past ten days, not yet at outbreak
threshold. A stretch of unusually cold nights has stressed the
unhoused population in the area. The opioid situation is baseline
for this community — present, not currently spiking.

No active mass casualty events. No hospital-level administrative
crises at this time.

Running threads:
Nothing established yet. First week.
"""

SAMPLE_HOSPITAL_PROFILE = """
Riverside General — Emergency Department

Type: Level 2 trauma center, urban community hospital
Beds: 42 ED beds, 4 trauma bays
Catchment: Mixed urban — working class residential,
           small commercial, adjacent to industrial corridor
Payer mix: ~38% Medicaid, ~22% Medicare, ~18% uninsured,
           ~22% commercial insurance
Volume: ~180 visits per day average

Character: This is not a prestigious academic medical center.
It is the hospital this community actually uses. Staff have been
here a long time. The department has genuine expertise in what
this community gets sick from. Resources are constrained.
Throughput pressure from administration is real and ongoing.
"""

SAMPLE_SHIFT_CONTEXT = {
    "day_of_week": "Thursday",
    "shift_type": "evening",
    "season": "late autumn",
    "weeks_into_campaign": 1,
    "recent_outcomes": [],
}


def run(num_cases: int = 4, model: str = "anthropic/claude-sonnet-4-5"):
    print(f"Generating {num_cases} cases...")
    print(f"Model: {model} via OpenRouter")
    print("This may take 30-120 seconds depending on model and case count.\n")

    try:
        pool = generate_shift_cases(
            world_state=SAMPLE_WORLD_STATE,
            hospital_profile=SAMPLE_HOSPITAL_PROFILE,
            shift_context=SAMPLE_SHIFT_CONTEXT,
            num_cases=num_cases,
            model=model,
        )
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    print(f"Generated {len(pool.cases)} cases for shift {pool.shift_id}\n")
    print("=" * 70)

    for case in pool.cases:
        pl = case.presenting_layer
        mt = case.medical_truth
        sf = case.systemic_flags

        acuity_labels = {1: "IMMEDIATE", 2: "EMERGENT", 3: "URGENT",
                         4: "LESS URGENT", 5: "NON-URGENT"}
        label = acuity_labels.get(pl.acuity.value, str(pl.acuity.value))

        print(f"\n[{case.case_id}] ACUITY {pl.acuity.value} — {label}")
        print(f"  Triage:  {pl.triage_note}")
        print(f"  Hook:    {case.narrative_hook}")
        print(f"  Truth:   {mt.true_diagnosis}")
        print(f"  Miss:    {mt.classic_miss_reason}")
        print(f"  Reveals: {len(case.reveal_sequence)} nodes")
        print(f"  Outcome: {case.outcome_trajectory.disposition}")
        if sf.world_event_connection:
            print(f"  [WORLD]:  {sf.world_event_connection}")
        if sf.shift_case_connection:
            print(f"  [LINKED]: {sf.shift_case_connection}")
        if sf.return_patient:
            print(f"  [RETURN PATIENT]")

    print("\n" + "=" * 70)

    # Quality checks
    print("\nQUALITY CHECKS")
    print("-" * 40)

    acuity_counts = {}
    for case in pool.cases:
        a = case.presenting_layer.acuity.value
        acuity_counts[a] = acuity_counts.get(a, 0) + 1
    print(f"Acuity distribution: {dict(sorted(acuity_counts.items()))}")

    connected = sum(
        1 for c in pool.cases
        if c.systemic_flags.world_event_connection
        or c.systemic_flags.shift_case_connection
    )
    print(f"Connected cases: {connected}/{len(pool.cases)}")

    time_sensitive = sum(1 for c in pool.cases if c.medical_truth.time_sensitivity)
    print(f"Time-sensitive: {time_sensitive}")

    avg_reveals = sum(len(c.reveal_sequence) for c in pool.cases) / len(pool.cases)
    print(f"Avg reveal nodes: {avg_reveals:.1f}")

    # Save full output
    output_path = "test_output.json"
    with open(output_path, "w") as f:
        json.dump(pool.model_dump(), f, indent=2, default=str)
    print(f"\nFull JSON -> {output_path}")
    print("\nRead all cases in test_output.json and ask:")
    print("  - Does the triage note feel like what a real nurse writes?")
    print("  - Does the hook make you want to open the chart?")
    print("  - Is the miss reason honest, not contrived?")
    print("  - Does the communication style describe behavior, not labels?")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=4,
                        help="Number of cases to generate (default: 4 for fast test)")
    parser.add_argument("--model", type=str,
                        default="anthropic/claude-sonnet-4-5",
                        help="OpenRouter model ID")
    args = parser.parse_args()
    run(num_cases=args.cases, model=args.model)
