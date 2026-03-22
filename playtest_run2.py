"""ERSim Playtest V3 — Run 2: Trap Focus"""
import io
import os
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
os.chdir(_ROOT)

from cases.generator import generate_shift_cases_from_templates
from cases.schema import GeneratedCase
from shift.shift import Shift

OLD_POOL = [
    "Maria Hernandez sepsis", "Richard Carmichael hip", "David Kowalski ankle",
    "Jessica Martinez HIV", "David Okonkwo head injury", "Michael Torres alcohol withdrawal",
    "Margaret Chen pneumonia", "Jennifer Kowalski PE", "Maria Delgado flu"
]

def is_new_case(name, diagnosis):
    combined = f"{name} {diagnosis}".lower()
    for old in OLD_POOL:
        if all(word.lower() in combined for word in old.split()):
            return False
    return True

def check_results(shift, log):
    res = shift.check_pending_results()
    for n in res.get("notifications", []):
        log.append(f"  [RESULT] {n}")
    for d in res.get("decisions", []):
        log.append(f"  [CROSS-BAY] {d['text']}")
        resp = shift.respond_cross_bay(d["bay_id"], 1)
        log.append(f"    -> {resp}")
    warnings = shift.check_warning_notifications()
    for w in warnings:
        log.append(f"  [WARNING] {w}")

log = []
print("Generating cases...")
pool = generate_shift_cases_from_templates(num_cases=3)
cases = [GeneratedCase.model_validate(c) for c in pool.cases]

correct_dispos = []
for i, c in enumerate(cases):
    pp = c.patient_profile
    pl = c.presenting_layer
    mt = c.medical_truth
    ot = c.outcome_trajectory
    name = f"{pp.first_name} {pp.last_name}"
    new = is_new_case(name, mt.true_diagnosis)
    correct_dispos.append(ot.disposition)
    log.append(f"Bay {i+1}: {name} | {pl.age}{pl.sex} | Acuity {pl.acuity.value} | Dx: {mt.true_diagnosis} | Dispo: {ot.disposition} | {'NEW' if new else 'OLD'}")
    log.append(f"  CC: {pl.chief_complaint}")
    log.append(f"  Miss: {mt.classic_miss_reason}")

print("Setting up shift...")
shift = Shift(cases=cases)
shift.setup()

trap_bay = None
non_trap_bays = []
for bay_id, bay in shift.bays.items():
    log.append(f"{bay_id}: resident={bay.resident.name}, trap={bay.is_trap}, threshold={bay.timer_threshold}")
    if bay.is_trap:
        trap_bay = bay_id
        log.append(f"  TRAP: {bay.trap_detail}")
    else:
        non_trap_bays.append(bay_id)

if not trap_bay:
    trap_bay = "Bay 1"
    non_trap_bays = ["Bay 2", "Bay 3"]
    log.append("NO TRAP DETECTED - using Bay 1")

trap_idx = int(trap_bay.split()[1]) - 1
log.append(f"\nSTATUS:\n{shift.status()}")

# Strategy: Quick approve non-traps, deep dive trap, prevent fires

# Quick non-trap visits
for bid in non_trap_bays:
    log.append(f"\n--- Quick: {bid} ---")
    r = shift.go(bid)
    log.append(f"GO: {r[:300]}")
    check_results(shift, log)
    r = shift.approve_plan(1)
    log.append(f"APPROVE: {r[:400]}")
    check_results(shift, log)

# Deep dive trap bay
log.append(f"\n--- DEEP DIVE: {trap_bay} ---")
r = shift.go(trap_bay)
log.append(f"GO: {r[:400]}")
check_results(shift, log)

r = shift.approve_plan(4)  # Hold
log.append(f"HOLD: {r[:200]}")

for q in [
    "Tell me everything from the beginning.",
    "Any medications or substances?",
    "Have you had anything like this before?",
    "Is there anything you haven't told anyone?",
]:
    r = shift.talk(q)
    log.append(f"TALK: {r[:300]}")
    check_results(shift, log)

for exam in ["general", "chest", "neurological"]:
    r = shift.exam(exam)
    log.append(f"EXAM ({exam}): {r[:300]}")
    check_results(shift, log)

r = shift.ask_resident("What's the worst case scenario here?")
log.append(f"ASK: {r[:300]}")
check_results(shift, log)

r = shift.test("ekg")
log.append(f"TEST ekg: {r[:200]}")
check_results(shift, log)

r = shift.approve_plan(1)
log.append(f"APPROVE: {r[:400]}")
check_results(shift, log)

# Check non-traps to prevent fires
for bid in non_trap_bays:
    log.append(f"\n--- Check-in: {bid} ---")
    r = shift.go(bid)
    log.append(f"GO: {r[:300]}")
    check_results(shift, log)
    r = shift.talk("How are you doing?")
    log.append(f"TALK: {r[:200]}")
    check_results(shift, log)

# Back to trap for family + resolve
log.append(f"\n--- Trap resolution: {trap_bay} ---")
r = shift.go(trap_bay)
log.append(f"GO: {r[:300]}")
check_results(shift, log)

r = shift.family()
log.append(f"FAMILY: {r[:300]}")
check_results(shift, log)

r = shift.chart()
log.append(f"CHART: {r[:500]}")

r = shift.resolve(correct_dispos[trap_idx])
log.append(f"RESOLVE TRAP ({correct_dispos[trap_idx]}): {r[:400]}")

# Resolve non-traps
for bid in non_trap_bays:
    idx = int(bid.split()[1]) - 1
    log.append(f"\n--- Resolve: {bid} ---")
    r = shift.go(bid)
    log.append(f"GO: {r[:300]}")
    check_results(shift, log)
    r = shift.chart()
    log.append(f"CHART: {r[:400]}")
    r = shift.resolve(correct_dispos[idx])
    log.append(f"RESOLVE ({correct_dispos[idx]}): {r[:400]}")

log.append(f"\nFINAL:\n{shift.status()}")

debrief = shift.debrief()
log.append(f"\nDEBRIEF:\n{debrief}")

with open("/home/d48reu/ERSim/run2_output.txt", "w") as f:
    f.write("\n".join(log))
print("Run 2 complete.")
print(debrief)
