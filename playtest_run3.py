"""ERSim Playtest V3 — Run 3: Minimal/Efficient"""
import os
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

print("Setting up shift...")
shift = Shift(cases=cases)
shift.setup()

for bay_id, bay in shift.bays.items():
    log.append(f"{bay_id}: resident={bay.resident.name}, trap={bay.is_trap}, threshold={bay.timer_threshold}")
    if bay.is_trap:
        log.append(f"  TRAP: {bay.trap_detail}")

log.append(f"\nSTATUS:\n{shift.status()}")

# MINIMAL: Visit each bay: go, approve plan (1), one talk, leave
for i in range(1, 4):
    bid = f"Bay {i}"
    log.append(f"\n--- {bid} (visit 1) ---")
    r = shift.go(bid)
    log.append(f"GO: {r[:300]}")
    check_results(shift, log)
    r = shift.approve_plan(1)
    log.append(f"APPROVE: {r[:400]}")
    check_results(shift, log)
    r = shift.talk("What brought you in?")
    log.append(f"TALK: {r[:200]}")
    check_results(shift, log)

# Pass 2: Resolve all
for i in range(1, 4):
    bid = f"Bay {i}"
    log.append(f"\n--- {bid} (resolve) ---")
    r = shift.go(bid)
    log.append(f"GO: {r[:300]}")
    check_results(shift, log)
    r = shift.chart()
    log.append(f"CHART: {r[:400]}")
    r = shift.resolve(correct_dispos[i-1])
    log.append(f"RESOLVE ({correct_dispos[i-1]}): {r[:400]}")

log.append(f"\nFINAL:\n{shift.status()}")

debrief = shift.debrief()
log.append(f"\nDEBRIEF:\n{debrief}")

with open("/home/d48reu/ERSim/run3_output.txt", "w") as f:
    f.write("\n".join(log))
print("Run 3 complete.")
print(debrief)
