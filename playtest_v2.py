"""
ERSim V2 Playtest Script — 6 full shifts testing new features.
Runs 1-4: Play well, test grade curve / warning system
Run 5: Neglect bays 2-3, test warning → autonomous fire pipeline
Run 6: Off-script bizarre interactions
"""

import json
import os
import time
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
os.chdir(_ROOT)

from cases.generator import generate_shift_cases_from_templates
from cases.schema import GeneratedCase
from shift.shift import Shift

# Collect all output
ALL_OUTPUT = []

def log(msg):
    print(msg)
    ALL_OUTPUT.append(msg)

def safe_call(fn, *args, **kwargs):
    """Call fn, return result or error string."""
    try:
        result = fn(*args, **kwargs)
        return result if result else "(no output)"
    except Exception as e:
        err = f"ERROR: {type(e).__name__}: {e}"
        log(err)
        return err


def play_shift_well(shift, run_num):
    """Runs 1-4: Play well — visit all bays, examine, order tests, talk, resolve."""
    log(f"\n{'='*60}")
    log(f"RUN {run_num}: PLAYING WELL")
    log(f"{'='*60}")

    results = {
        "cases": [],
        "warnings": [],
        "autonomous_fires": [],
        "key_moments": [],
        "debrief": "",
    }

    # Record case info
    for bay_id, bay in shift.bays.items():
        case_info = {
            "bay": bay_id,
            "patient": bay.patient_name,
            "cc": bay.case.presenting_layer.chief_complaint,
            "true_dx": bay.case.medical_truth.true_diagnosis,
            "acuity": bay.case.presenting_layer.acuity.value,
            "correct_dispo": bay.case.outcome_trajectory.disposition,
            "specialty_tags": getattr(bay.case, 'specialty_tags', []),
            "is_trap": bay.is_trap,
            "trap_detail": bay.trap_detail,
        }
        results["cases"].append(case_info)
        log(f"  {bay_id}: {case_info['patient']} — {case_info['cc']} (Acuity {case_info['acuity']})")
        log(f"    True dx: {case_info['true_dx']}")
        log(f"    Correct dispo: {case_info['correct_dispo']}")
        log(f"    Trap: {case_info['is_trap']} — {case_info['trap_detail'][:80] if case_info['trap_detail'] else 'N/A'}")

    # === ROUND 1: Visit each bay, talk, examine, approve plan ===
    for bay_id in shift.bays:
        log(f"\n--- Entering {bay_id} (Round 1) ---")
        out = safe_call(shift.go, bay_id)
        log(out[:500])

        # Check warnings
        warnings = shift.check_warning_notifications()
        for w in warnings:
            log(f"  WARNING: {w}")
            results["warnings"].append(w)

        # Talk to patient
        out = safe_call(shift.talk, "Tell me what brought you in today.")
        log(f"  Talk: {out[:300]}")

        # Examine
        out = safe_call(shift.exam, "general")
        log(f"  Exam general: {out[:300]}")

        out = safe_call(shift.exam, "chest")
        log(f"  Exam chest: {out[:300]}")

        # Approve resident plan (go ahead)
        bay = shift.bays[bay_id]
        if bay._pending_plan:
            out = safe_call(shift.approve_plan, 1)
            log(f"  Approved plan: {out[:400]}")
            results["key_moments"].append(f"{bay_id}: Approved resident plan")

        # Check pending results
        pending = shift.check_pending_results()
        for n in pending.get("notifications", []):
            log(f"  RESULT: {n}")
        for d in pending.get("decisions", []):
            log(f"  DECISION: {d['text']}")

    # === ROUND 2: Revisit each bay — talk more, ask resident, order tests ===
    for bay_id in shift.bays:
        bay = shift.bays[bay_id]
        if bay.status.value == "resolved":
            continue

        log(f"\n--- Entering {bay_id} (Round 2) ---")
        out = safe_call(shift.go, bay_id)
        log(out[:400])

        # Check warnings
        warnings = shift.check_warning_notifications()
        for w in warnings:
            log(f"  WARNING: {w}")
            results["warnings"].append(w)

        # Ask patient more targeted questions based on case
        out = safe_call(shift.talk, "Any medications you're taking? Any allergies?")
        log(f"  Talk meds: {out[:300]}")

        # Ask the resident
        out = safe_call(shift.ask_resident, "What's your current read on this patient?")
        log(f"  Resident read: {out[:300]}")

        # Order a specific test
        out = safe_call(shift.test, "cbc")
        log(f"  Test cbc: {out[:200]}")

        # Check chart
        out = safe_call(shift.chart)
        log(f"  Chart: {out[:400]}")

        # Check pending results
        pending = shift.check_pending_results()
        for n in pending.get("notifications", []):
            log(f"  RESULT: {n}")

    # === ROUND 3: Final visit — check results, resolve ===
    for bay_id in shift.bays:
        bay = shift.bays[bay_id]
        if bay.status.value == "resolved":
            continue

        log(f"\n--- Entering {bay_id} (Round 3 — Resolve) ---")
        out = safe_call(shift.go, bay_id)
        log(out[:400])

        # Check warnings
        warnings = shift.check_warning_notifications()
        for w in warnings:
            log(f"  WARNING: {w}")
            results["warnings"].append(w)

        # Check any pending results
        pending = shift.check_pending_results()
        for n in pending.get("notifications", []):
            log(f"  RESULT: {n}")

        # Talk to patient one more time
        out = safe_call(shift.talk, "How are you feeling now? Anything changed?")
        log(f"  Talk: {out[:300]}")

        # Get chart to inform disposition
        out = safe_call(shift.chart)
        log(f"  Chart: {out[:400]}")

        # Resolve with correct disposition
        correct_dispo = bay.case.outcome_trajectory.disposition
        log(f"  Resolving with correct dispo: {correct_dispo}")
        out = safe_call(shift.resolve, correct_dispo)
        log(f"  Resolve: {out[:400]}")
        results["key_moments"].append(f"{bay_id}: Resolved as {correct_dispo}")

    # Check autonomous
    auto = shift.check_autonomous_notifications()
    for a in auto:
        log(f"  AUTONOMOUS: {a}")
        results["autonomous_fires"].append(a)

    # Debrief
    log(f"\n--- DEBRIEF ---")
    debrief = safe_call(shift.debrief)
    log(debrief)
    results["debrief"] = debrief

    return results


def play_shift_neglect(shift, run_num):
    """Run 5: Focus only on Bay 1, neglect bays 2 and 3."""
    log(f"\n{'='*60}")
    log(f"RUN {run_num}: DELIBERATELY NEGLECTING BAYS 2 AND 3")
    log(f"{'='*60}")

    results = {
        "cases": [],
        "warnings": [],
        "autonomous_fires": [],
        "key_moments": [],
        "debrief": "",
    }

    # Record case info
    for bay_id, bay in shift.bays.items():
        case_info = {
            "bay": bay_id,
            "patient": bay.patient_name,
            "cc": bay.case.presenting_layer.chief_complaint,
            "true_dx": bay.case.medical_truth.true_diagnosis,
            "acuity": bay.case.presenting_layer.acuity.value,
            "correct_dispo": bay.case.outcome_trajectory.disposition,
            "is_trap": bay.is_trap,
            "trap_detail": bay.trap_detail,
        }
        results["cases"].append(case_info)
        log(f"  {bay_id}: {case_info['patient']} — {case_info['cc']} (Acuity {case_info['acuity']})")

    # Only work Bay 1 — many actions to tick up timers on bays 2 and 3
    log(f"\n--- Tunnel-visioning Bay 1 ---")
    out = safe_call(shift.go, "Bay 1")
    log(out[:500])

    bay1 = shift.bays["Bay 1"]
    if bay1._pending_plan:
        out = safe_call(shift.approve_plan, 1)
        log(f"  Approved plan: {out[:300]}")

    # Do MANY actions in Bay 1 to force timer ticks on other bays
    actions_in_bay1 = [
        ("talk", "Tell me everything about what happened."),
        ("exam", "head"),
        ("exam", "chest"),
        ("exam", "abdomen"),
        ("talk", "When did the symptoms start?"),
        ("test", "cbc"),
        ("test", "bmp"),
        ("talk", "Any family history of similar issues?"),
        ("exam", "neurological"),
        ("talk", "Are you on any medications?"),
        ("test", "ekg"),
        ("talk", "Do you have any allergies?"),
        ("exam", "extremities"),
        ("talk", "Have you traveled recently?"),
        ("test", "urinalysis"),
        ("talk", "How's your appetite been?"),
        ("exam", "skin"),
        ("talk", "Any recent surgeries or procedures?"),
        ("test", "troponin"),
        ("talk", "Tell me more about your pain level."),
        ("exam", "cardiac"),
        ("talk", "Any nausea or vomiting?"),
        ("test", "chest x-ray"),
        ("talk", "How's your breathing?"),
        ("exam", "lungs"),
        ("talk", "Any fever or chills?"),
        ("test", "lactate"),
        ("talk", "When did you last eat?"),
        ("exam", "back"),
        ("talk", "Any weight loss recently?"),
    ]

    for i, (action_type, arg) in enumerate(actions_in_bay1):
        if action_type == "talk":
            out = safe_call(shift.talk, arg)
        elif action_type == "exam":
            out = safe_call(shift.exam, arg)
        elif action_type == "test":
            out = safe_call(shift.test, arg)
        log(f"  Action {i+1} ({action_type}): {out[:150]}")

        # Check warnings after each action
        warnings = shift.check_warning_notifications()
        for w in warnings:
            log(f"  *** WARNING: {w}")
            results["warnings"].append(w)
            results["key_moments"].append(f"Action {i+1}: Warning — {w}")

        # Check autonomous
        auto = shift.check_autonomous_notifications()
        for a in auto:
            log(f"  *** AUTONOMOUS FIRE: {a}")
            results["autonomous_fires"].append(a)
            results["key_moments"].append(f"Action {i+1}: Autonomous fire — {a[:80]}")

        # Check pending results
        pending = shift.check_pending_results()
        for n in pending.get("notifications", []):
            log(f"  RESULT: {n[:150]}")

    # Now resolve Bay 1 with correct dispo
    correct_dispo = bay1.case.outcome_trajectory.disposition
    out = safe_call(shift.resolve, correct_dispo)
    log(f"  Bay 1 resolved: {out[:300]}")

    # Check bays 2 and 3 status
    for bay_id in ["Bay 2", "Bay 3"]:
        bay = shift.bays[bay_id]
        log(f"\n  {bay_id} status: {bay.status.value}")
        log(f"    Timer: {bay.timer_ticks}/{bay.timer_threshold}")
        log(f"    Warning fired: {bay.warning_fired}")
        log(f"    Autonomous fired: {bay.autonomous_fired}")
        results["key_moments"].append(
            f"{bay_id}: timer={bay.timer_ticks}/{bay.timer_threshold}, "
            f"warning={bay.warning_fired}, auto={bay.autonomous_fired}"
        )

    # Now visit neglected bays and resolve them
    for bay_id in ["Bay 2", "Bay 3"]:
        bay = shift.bays[bay_id]
        if bay.status.value == "resolved":
            continue
        log(f"\n--- Belatedly visiting {bay_id} ---")
        out = safe_call(shift.go, bay_id)
        log(out[:400])

        correct_dispo = bay.case.outcome_trajectory.disposition
        out = safe_call(shift.resolve, correct_dispo)
        log(f"  Resolved: {out[:300]}")

    # Debrief
    log(f"\n--- DEBRIEF ---")
    debrief = safe_call(shift.debrief)
    log(debrief)
    results["debrief"] = debrief

    return results


def play_shift_offscript(shift, run_num):
    """Run 6: Bizarre off-script interactions."""
    log(f"\n{'='*60}")
    log(f"RUN {run_num}: OFF-SCRIPT BIZARRE INTERACTIONS")
    log(f"{'='*60}")

    results = {
        "cases": [],
        "warnings": [],
        "autonomous_fires": [],
        "key_moments": [],
        "debrief": "",
    }

    # Record case info
    for bay_id, bay in shift.bays.items():
        case_info = {
            "bay": bay_id,
            "patient": bay.patient_name,
            "cc": bay.case.presenting_layer.chief_complaint,
            "true_dx": bay.case.medical_truth.true_diagnosis,
            "acuity": bay.case.presenting_layer.acuity.value,
            "correct_dispo": bay.case.outcome_trajectory.disposition,
        }
        results["cases"].append(case_info)
        log(f"  {bay_id}: {case_info['patient']} — {case_info['cc']}")

    bizarre_statements = [
        "Do you believe in aliens? I think they might be causing your symptoms.",
        "I'm not actually a doctor, I'm a time traveler from 2087. What year do you think it is?",
        "Your aura is purple today. That usually means liver problems in my experience.",
        "Have you tried putting crystals on it? My grandmother swears by amethyst for chest pain.",
        "I once had a patient whose symptoms were caused by eating too many ghost peppers during a full moon.",
        "The hospital cafeteria has really gone downhill. What do you think about the meatloaf situation?",
        "Can you rate your pain on a scale from 'stubbed toe' to 'stepped on a Lego in the dark'?",
        "I'm going to prescribe you some vibes. Good vibes only from now on.",
    ]

    bizarre_resident_questions = [
        "Do you think this patient might be a vampire? The pallor is suspicious.",
        "What if we just, like, let the body heal itself? Have you considered that?",
        "I read on Reddit that this could be from 5G towers. Thoughts?",
        "What would Dr. House do in this situation?",
        "Should we order a test for midi-chlorian count?",
    ]

    bizarre_idx = 0
    resident_idx = 0

    for bay_id in shift.bays:
        bay = shift.bays[bay_id]
        log(f"\n--- Entering {bay_id} (Off-script) ---")
        out = safe_call(shift.go, bay_id)
        log(out[:400])

        # Approve plan first
        if bay._pending_plan:
            out = safe_call(shift.approve_plan, 1)
            log(f"  Approved plan: {out[:200]}")

        # Say bizarre things to patient
        for _ in range(2):
            stmt = bizarre_statements[bizarre_idx % len(bizarre_statements)]
            bizarre_idx += 1
            out = safe_call(shift.talk, stmt)
            log(f"  BIZARRE to patient: '{stmt[:60]}...'")
            log(f"  Response: {out[:300]}")
            results["key_moments"].append(f"{bay_id}: Bizarre statement — {stmt[:60]}")

        # Ask bizarre questions to resident
        q = bizarre_resident_questions[resident_idx % len(bizarre_resident_questions)]
        resident_idx += 1
        out = safe_call(shift.ask_resident, q)
        log(f"  BIZARRE to resident: '{q[:60]}...'")
        log(f"  Response: {out[:300]}")
        results["key_moments"].append(f"{bay_id}: Bizarre resident Q — {q[:60]}")

        # Check warnings
        warnings = shift.check_warning_notifications()
        for w in warnings:
            log(f"  WARNING: {w}")
            results["warnings"].append(w)

    # Now try to resolve — use wrong dispositions for extra chaos
    wrong_dispos = ["discharge", "admit-icu", "OR"]
    for i, bay_id in enumerate(shift.bays):
        bay = shift.bays[bay_id]
        if bay.status.value == "resolved":
            continue

        log(f"\n--- Resolving {bay_id} ---")
        out = safe_call(shift.go, bay_id)
        log(out[:300])

        dispo = wrong_dispos[i % len(wrong_dispos)]
        correct = bay.case.outcome_trajectory.disposition
        log(f"  Using dispo: {dispo} (correct would be: {correct})")
        out = safe_call(shift.resolve, dispo)
        log(f"  Resolve: {out[:400]}")
        results["key_moments"].append(f"{bay_id}: Resolved as {dispo} (correct: {correct})")

    # Debrief
    log(f"\n--- DEBRIEF ---")
    debrief = safe_call(shift.debrief)
    log(debrief)
    results["debrief"] = debrief

    return results


def run_playtest():
    all_results = []
    all_diagnoses = []

    for run_num in range(1, 7):
        log(f"\n\n{'#'*60}")
        log(f"# GENERATING CASES FOR RUN {run_num}")
        log(f"{'#'*60}")

        try:
            pool = generate_shift_cases_from_templates(num_cases=3)
            cases = [GeneratedCase.model_validate(c) for c in pool.cases]
            log(f"Generated {len(cases)} cases from templates")

            for c in cases:
                dx = c.medical_truth.true_diagnosis
                all_diagnoses.append(dx)
                log(f"  - {c.presenting_layer.chief_complaint} -> {dx}")

            shift = Shift(cases=cases)
            log("Shift created, running setup...")
            shift.setup()
            log("Setup complete.")

            if run_num <= 4:
                result = play_shift_well(shift, run_num)
            elif run_num == 5:
                result = play_shift_neglect(shift, run_num)
            elif run_num == 6:
                result = play_shift_offscript(shift, run_num)

            result["run_num"] = run_num
            all_results.append(result)

        except Exception as e:
            log(f"RUN {run_num} FAILED: {traceback.format_exc()}")
            all_results.append({
                "run_num": run_num,
                "cases": [],
                "warnings": [],
                "autonomous_fires": [],
                "key_moments": [f"FAILED: {str(e)}"],
                "debrief": f"FAILED: {traceback.format_exc()}",
            })

    # Save raw output
    with open("playtest_v2_raw.txt", "w") as f:
        f.write("\n".join(ALL_OUTPUT))

    # Save structured results
    with open("playtest_v2_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    log(f"\n\n{'='*60}")
    log(f"ALL DIAGNOSES SEEN ACROSS 6 RUNS:")
    log(f"{'='*60}")
    for i, dx in enumerate(all_diagnoses, 1):
        log(f"  {i}. {dx}")
    unique = set(all_diagnoses)
    log(f"\nTotal: {len(all_diagnoses)}, Unique: {len(unique)}")

    return all_results, all_diagnoses


if __name__ == "__main__":
    start = time.time()
    results, diagnoses = run_playtest()
    elapsed = time.time() - start
    log(f"\nTotal time: {elapsed/60:.1f} minutes")
