"""
Test harness for the resident AI.

Tests all three modes against the James Kowalski case:
  1. Proactive — resident presents the case
  2. Responsive — attending asks follow-up questions
  3. Autonomous — timer expires, resident acts alone

Run from ERSim directory:
    python -m residents.test_resident

Optional: test a specific resident
    python -m residents.test_resident --resident okafor_dre
    python -m residents.test_resident --resident patel_priya
    python -m residents.test_resident --resident chen_maya
"""

import json
import sys
import argparse

from cases.schema import GeneratedCase
from .schema import make_default_roster
from .resident import ResidentAI


def run(resident_id: str = "chen_maya", case_index: int = 3,
        model: str = "anthropic/claude-haiku-4-5"):

    # Load case
    try:
        with open("test_output.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("No test_output.json found. Run test_generation first.")
        sys.exit(1)

    cases = data.get("cases", [])
    if case_index >= len(cases):
        case_index = 0
    case = GeneratedCase.model_validate(cases[case_index])

    # Load resident
    roster = make_default_roster()
    resident = next((r for r in roster if r.id == resident_id), roster[0])

    print(f"\n{'='*60}")
    print(f"RESIDENT TEST — {resident.name} (PGY-{resident.year.value})")
    print(f"Personality: {resident.personality.value}")
    print(f"Case: {case.case_id} — {case.presenting_layer.triage_note}")
    print(f"True diagnosis (hidden): {case.medical_truth.true_diagnosis}")
    print(f"{'='*60}\n")

    ai = ResidentAI(resident, model=model)
    ai.set_shift_context({
        "shift_type": "evening",
        "hours_elapsed": 3,
        "department_pressure": "moderate",
    })

    # ---------------------------------------------------------------
    # Mode 1: Proactive presentation
    # ---------------------------------------------------------------
    print("[ MODE 1: PROACTIVE PRESENTATION ]")
    print("Resident approaches the attending with a new case...\n")

    assessment = ai.proactive(case)

    print(f"[{resident.name.upper().split()[0]}]: {assessment.what_they_say}")
    print(f"\n--- Internal reasoning (game engine only) ---")
    print(f"Differential: {assessment.differential}")
    print(f"Workup: {assessment.recommended_workup}")
    print(f"Confidence: {assessment.confidence}")
    print(f"Flags: {assessment.flags}")
    print(f"Reasoning: {assessment.reasoning}")

    # ---------------------------------------------------------------
    # Mode 2: Responsive — attending asks questions
    # ---------------------------------------------------------------
    print(f"\n{'='*60}")
    print("[ MODE 2: RESPONSIVE ]")

    questions = [
        (
            "What's your top diagnosis and why?",
            "Resident presented case. No workup done yet."
        ),
        (
            "He mentioned this happened before about a month ago. "
            "Does that change anything?",
            "Resident presented biliary as top diagnosis. "
            "Attending has been talking to patient and learned about prior episode."
        ),
        (
            "Are you sure this isn't cardiac? He's 52, works a stressful job.",
            "Ultrasound ordered. Prior episode noted. "
            "Resident is confident about biliary diagnosis."
        ),
    ]

    for question, summary in questions:
        print(f"\n[ATTENDING]: {question}")
        response = ai.respond(case, question, summary)
        print(f"[{resident.name.upper().split()[0]}]: {response.what_they_say}")
        if response.flags:
            print(f"  (internal flags: {response.flags})")

    # ---------------------------------------------------------------
    # Mode 3: Autonomous action
    # ---------------------------------------------------------------
    print(f"\n{'='*60}")
    print("[ MODE 3: AUTONOMOUS — timer expired ]")
    print("Attending got pulled to trauma bay. 12 minutes passed.\n")

    # Simulate different stress levels for the autonomous test
    ai.update_state(
        hours_into_shift=5.5,
        stress_level="moderate",
        active_cases=3,
    )

    case_state = {
        "known_to_resident": (
            "Patient has RUQ pain x2 hours. Prior similar episode a month ago. "
            "Ultrasound ordered, results pending. "
            "Vitals stable. Patient is irritable and wants to leave."
        ),
        "actions_taken": [
            "IV access placed",
            "Labs ordered: LFTs, lipase, CBC",
            "Ultrasound ordered",
        ],
        "pending": [
            "Ultrasound result not back yet",
            "Attending has not reviewed case",
            "Patient asking about going home",
        ],
    }

    action = ai.act_autonomously(
        case=case,
        timer_duration_minutes=12,
        case_state_at_timer=case_state,
    )

    print(f"Action taken: {action.action_taken}")
    print(f"\n[{resident.name.upper().split()[0]} to attending]:")
    print(f"{action.what_they_tell_attending}")
    print(f"\n--- What they're NOT saying (game engine only) ---")
    print(f"{action.what_they_dont_say}")
    print(f"\nReasoning (internal): {action.reasoning}")

    print(f"\n{'='*60}")
    print("Done. Try different residents with --resident okafor_dre or --resident patel_priya")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resident", type=str, default="chen_maya",
                        choices=["chen_maya", "okafor_dre", "patel_priya"])
    parser.add_argument("--case", type=int, default=3)
    parser.add_argument("--model", type=str, default="anthropic/claude-haiku-4-5")
    args = parser.parse_args()
    run(resident_id=args.resident, case_index=args.case, model=args.model)
