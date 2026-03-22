"""
ERSim Playtest V3 — 3 full shifts with different strategies.
Run 1: Balanced attention
Run 2: Focus on trap case
Run 3: Minimal/efficient
"""
import io
import json
import os
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
os.chdir(_ROOT)

from cases.generator import generate_shift_cases_from_templates
from cases.schema import GeneratedCase
from shift.shift import Shift

# Old pool for comparison
OLD_POOL = [
    "Maria Hernandez sepsis", "Richard Carmichael hip", "David Kowalski ankle",
    "Jessica Martinez HIV", "David Okonkwo head injury", "Michael Torres alcohol withdrawal",
    "Margaret Chen pneumonia", "Jennifer Kowalski PE", "Maria Delgado flu"
]

def capture(func, *args, **kwargs):
    """Call func, capture stdout, return (result, captured_text)."""
    old = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        result = f"ERROR: {e}\n{traceback.format_exc()}"
    sys.stdout = old
    return result, buf.getvalue()

def case_info(case):
    """Extract key info from a GeneratedCase."""
    pp = case.patient_profile
    pl = case.presenting_layer
    mt = case.medical_truth
    ot = case.outcome_trajectory
    name = f"{pp.first_name} {pp.last_name}"
    return {
        "name": name,
        "age": pl.age,
        "sex": pl.sex,
        "chief_complaint": pl.chief_complaint,
        "acuity": pl.acuity.value,
        "true_diagnosis": mt.true_diagnosis,
        "correct_disposition": ot.disposition,
        "miss_reason": mt.classic_miss_reason,
        "time_sensitive": mt.time_sensitivity,
        "narrative_hook": case.narrative_hook,
    }

def is_new_case(name, diagnosis):
    """Check if this case is new vs the old pool."""
    combined = f"{name} {diagnosis}".lower()
    for old in OLD_POOL:
        if all(word.lower() in combined for word in old.split()):
            return False
    return True

def check_and_show_results(shift, log):
    """Check for pending results and log notifications."""
    res = shift.check_pending_results()
    for n in res.get("notifications", []):
        log.append(f"  [RESULT NOTIFICATION] {n}")
    for d in res.get("decisions", []):
        log.append(f"  [CROSS-BAY DECISION] {d['text']}")
        # Auto-approve cross-bay decisions
        resp = shift.respond_cross_bay(d["bay_id"], 1)
        log.append(f"    -> Approved: {resp}")
    warnings = shift.check_warning_notifications()
    for w in warnings:
        log.append(f"  [WARNING] {w}")
    return res

def play_shift_balanced(shift, cases_info, log):
    """Run 1: Balanced attention across all bays."""
    log.append("\n=== STRATEGY: BALANCED ATTENTION ===")
    
    # Identify trap bay
    trap_bay = None
    for bay_id, bay in shift.bays.items():
        if bay.is_trap:
            trap_bay = bay_id
            log.append(f"  TRAP BAY: {bay_id} - {bay.trap_detail}")
    
    # Round 1: Visit all bays, hold plans, do initial exam
    for i in range(1, 4):
        bay_id = f"Bay {i}"
        bay = shift.bays[bay_id]
        
        log.append(f"\n--- Entering {bay_id} (Round 1) ---")
        result = shift.go(bay_id)
        log.append(f"  GO: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Hold the plan first to talk to patient
        result = shift.approve_plan(4)
        log.append(f"  HOLD PLAN: {result[:200]}")
        check_and_show_results(shift, log)
        
        # Talk to patient
        result = shift.talk("Tell me what's going on. When did this start?")
        log.append(f"  TALK: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Physical exam
        exam_area = "general"
        if "chest" in bay.case.presenting_layer.chief_complaint.lower():
            exam_area = "chest"
        elif "head" in bay.case.presenting_layer.chief_complaint.lower():
            exam_area = "head"
        elif "abdomen" in bay.case.presenting_layer.chief_complaint.lower() or "belly" in bay.case.presenting_layer.chief_complaint.lower():
            exam_area = "abdomen"
        
        result = shift.exam(exam_area)
        log.append(f"  EXAM ({exam_area}): {result[:300]}")
        check_and_show_results(shift, log)
    
    # Round 2: Go back, approve plans, order tests
    for i in range(1, 4):
        bay_id = f"Bay {i}"
        bay = shift.bays[bay_id]
        
        log.append(f"\n--- Entering {bay_id} (Round 2 - approve & test) ---")
        result = shift.go(bay_id)
        log.append(f"  GO: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Now approve the plan (go ahead)
        result = shift.approve_plan(1)
        log.append(f"  APPROVE: {result[:400]}")
        check_and_show_results(shift, log)
        
        # Ask resident about concerns
        result = shift.ask_resident("What are you most worried about missing here?")
        log.append(f"  ASK RESIDENT: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Talk more to patient
        result = shift.talk("Is there anything else you haven't told me? Any medications or substances?")
        log.append(f"  TALK 2: {result[:300]}")
        check_and_show_results(shift, log)
    
    # Round 3: Check results, make dispositions
    for i in range(1, 4):
        bay_id = f"Bay {i}"
        bay = shift.bays[bay_id]
        
        log.append(f"\n--- Entering {bay_id} (Round 3 - results & dispo) ---")
        result = shift.go(bay_id)
        log.append(f"  GO: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Check chart
        result = shift.chart()
        log.append(f"  CHART: {result[:500]}")
        
        # Ask resident for their read
        result = shift.ask_resident("What's your current assessment and recommendation?")
        log.append(f"  ASK RESIDENT READ: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Make disposition based on the correct answer (we know it from case data)
        correct_dispo = cases_info[i-1]["correct_disposition"]
        result = shift.resolve(correct_dispo)
        log.append(f"  RESOLVE ({correct_dispo}): {result[:400]}")
    
    return log

def play_shift_trap_focus(shift, cases_info, log):
    """Run 2: Focus heavily on trap case."""
    log.append("\n=== STRATEGY: TRAP FOCUS ===")
    
    # Identify trap bay
    trap_bay = None
    non_trap_bays = []
    for bay_id, bay in shift.bays.items():
        if bay.is_trap:
            trap_bay = bay_id
            log.append(f"  TRAP BAY: {bay_id} - {bay.trap_detail}")
        else:
            non_trap_bays.append(bay_id)
    
    if not trap_bay:
        log.append("  NO TRAP BAY DETECTED - playing balanced")
        trap_bay = "Bay 1"
        non_trap_bays = ["Bay 2", "Bay 3"]
    
    # Quick visit non-trap bays first, approve plans
    for bay_id in non_trap_bays:
        bay = shift.bays[bay_id]
        log.append(f"\n--- Quick visit {bay_id} ---")
        result = shift.go(bay_id)
        log.append(f"  GO: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Approve plan immediately (go ahead)
        result = shift.approve_plan(1)
        log.append(f"  APPROVE: {result[:400]}")
        check_and_show_results(shift, log)
    
    # Now focus on trap bay
    bay = shift.bays[trap_bay]
    trap_idx = int(trap_bay.split()[1]) - 1
    
    log.append(f"\n--- DEEP DIVE: {trap_bay} ---")
    result = shift.go(trap_bay)
    log.append(f"  GO: {result[:400]}")
    check_and_show_results(shift, log)
    
    # Hold plan
    result = shift.approve_plan(4)
    log.append(f"  HOLD PLAN: {result[:200]}")
    
    # Extensive patient interview
    questions = [
        "Tell me everything from the beginning. What happened?",
        "Any medications? Anything you take that's not prescribed?",
        "Have you had anything like this before?",
        "Is there anything you're worried about that you haven't told anyone?",
    ]
    for q in questions:
        result = shift.talk(q)
        log.append(f"  TALK: {result[:300]}")
        check_and_show_results(shift, log)
    
    # Multiple exams
    for exam_type in ["general", "chest", "neurological", "abdomen"]:
        result = shift.exam(exam_type)
        log.append(f"  EXAM ({exam_type}): {result[:300]}")
        check_and_show_results(shift, log)
    
    # Ask resident pointed questions
    result = shift.ask_resident("What are you most worried about missing? What's the worst case scenario?")
    log.append(f"  ASK RESIDENT: {result[:300]}")
    check_and_show_results(shift, log)
    
    # Order additional tests
    result = shift.test("cbc")
    log.append(f"  TEST cbc: {result[:200]}")
    result = shift.test("bmp")
    log.append(f"  TEST bmp: {result[:200]}")
    check_and_show_results(shift, log)
    
    # Now approve a modified plan
    result = shift.approve_plan(1)
    log.append(f"  APPROVE: {result[:400]}")
    check_and_show_results(shift, log)
    
    # Quick check on non-trap bays to prevent fires
    for bay_id in non_trap_bays:
        log.append(f"\n--- Check-in {bay_id} ---")
        result = shift.go(bay_id)
        log.append(f"  GO: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Brief talk
        result = shift.talk("How are you doing? Any changes?")
        log.append(f"  TALK: {result[:200]}")
        check_and_show_results(shift, log)
    
    # Back to trap bay for resolution
    log.append(f"\n--- Return to {trap_bay} for resolution ---")
    result = shift.go(trap_bay)
    log.append(f"  GO: {result[:300]}")
    check_and_show_results(shift, log)
    
    result = shift.chart()
    log.append(f"  CHART: {result[:500]}")
    
    # Family if available
    result = shift.family()
    log.append(f"  FAMILY: {result[:300]}")
    check_and_show_results(shift, log)
    
    # Resolve trap bay with correct dispo
    correct_dispo = cases_info[trap_idx]["correct_disposition"]
    result = shift.resolve(correct_dispo)
    log.append(f"  RESOLVE TRAP ({correct_dispo}): {result[:400]}")
    
    # Now resolve non-trap bays
    for bay_id in non_trap_bays:
        idx = int(bay_id.split()[1]) - 1
        log.append(f"\n--- Resolve {bay_id} ---")
        result = shift.go(bay_id)
        log.append(f"  GO: {result[:300]}")
        check_and_show_results(shift, log)
        
        result = shift.chart()
        log.append(f"  CHART: {result[:400]}")
        
        result = shift.ask_resident("Final recommendation?")
        log.append(f"  ASK: {result[:200]}")
        check_and_show_results(shift, log)
        
        correct_dispo = cases_info[idx]["correct_disposition"]
        result = shift.resolve(correct_dispo)
        log.append(f"  RESOLVE ({correct_dispo}): {result[:400]}")
    
    return log

def play_shift_minimal(shift, cases_info, log):
    """Run 3: Minimal/efficient - fewest actions possible."""
    log.append("\n=== STRATEGY: MINIMAL/EFFICIENT ===")
    
    # Identify trap
    for bay_id, bay in shift.bays.items():
        if bay.is_trap:
            log.append(f"  TRAP BAY: {bay_id} - {bay.trap_detail}")
    
    # Visit each bay: go, approve plan (1), ask one question, resolve
    for i in range(1, 4):
        bay_id = f"Bay {i}"
        bay = shift.bays[bay_id]
        
        log.append(f"\n--- {bay_id} (minimal) ---")
        result = shift.go(bay_id)
        log.append(f"  GO: {result[:300]}")
        check_and_show_results(shift, log)
        
        # Approve plan immediately
        result = shift.approve_plan(1)
        log.append(f"  APPROVE: {result[:400]}")
        check_and_show_results(shift, log)
        
        # One talk
        result = shift.talk("What brought you in today?")
        log.append(f"  TALK: {result[:200]}")
        check_and_show_results(shift, log)
    
    # Second pass: resolve all
    for i in range(1, 4):
        bay_id = f"Bay {i}"
        
        log.append(f"\n--- {bay_id} (resolve) ---")
        result = shift.go(bay_id)
        log.append(f"  GO: {result[:300]}")
        check_and_show_results(shift, log)
        
        result = shift.chart()
        log.append(f"  CHART: {result[:400]}")
        
        correct_dispo = cases_info[i-1]["correct_disposition"]
        result = shift.resolve(correct_dispo)
        log.append(f"  RESOLVE ({correct_dispo}): {result[:400]}")
    
    return log


# ============================================================
# MAIN EXECUTION
# ============================================================

all_results = []

for run_num in range(1, 4):
    print(f"\n{'='*60}")
    print(f"RUN {run_num} STARTING")
    print(f"{'='*60}")
    
    run_log = []
    run_data = {"run": run_num, "log": run_log, "errors": []}
    
    try:
        # Generate cases
        print(f"Generating cases for Run {run_num}...")
        pool, gen_stdout = capture(generate_shift_cases_from_templates, num_cases=3)
        run_log.append(f"[GENERATION STDOUT]\n{gen_stdout}")
        
        if isinstance(pool, str) and pool.startswith("ERROR"):
            run_data["errors"].append(f"Generation failed: {pool}")
            all_results.append(run_data)
            continue
        
        cases = [GeneratedCase.model_validate(c) for c in pool.cases]
        
        # Extract case info
        cases_info = [case_info(c) for c in cases]
        run_data["cases"] = cases_info
        
        for ci in cases_info:
            new = is_new_case(ci["name"], ci["true_diagnosis"])
            ci["is_new"] = new
            run_log.append(
                f"  CASE: {ci['name']} | Age {ci['age']}{ci['sex']} | "
                f"Acuity {ci['acuity']} | Dx: {ci['true_diagnosis']} | "
                f"Dispo: {ci['correct_disposition']} | "
                f"NEW: {'YES' if new else 'NO (seen before)'}"
            )
        
        # Create and setup shift
        print(f"Setting up shift for Run {run_num}...")
        shift = Shift(cases=cases)
        setup_result, setup_stdout = capture(shift.setup)
        run_log.append(f"\n[SETUP STDOUT]\n{setup_stdout}")
        
        # Show trap info
        for bay_id, bay in shift.bays.items():
            run_log.append(f"  {bay_id}: resident={bay.resident.name}, is_trap={bay.is_trap}, acuity={bay.acuity}, threshold={bay.timer_threshold}")
        
        # Status before play
        status = shift.status()
        run_log.append(f"\n[INITIAL STATUS]\n{status}")
        
        # Play the shift
        print(f"Playing Run {run_num}...")
        if run_num == 1:
            play_shift_balanced(shift, cases_info, run_log)
        elif run_num == 2:
            play_shift_trap_focus(shift, cases_info, run_log)
        else:
            play_shift_minimal(shift, cases_info, run_log)
        
        # Final status
        status = shift.status()
        run_log.append(f"\n[FINAL STATUS]\n{status}")
        
        # Debrief
        print(f"Getting debrief for Run {run_num}...")
        debrief = shift.debrief()
        run_log.append(f"\n[DEBRIEF]\n{debrief}")
        run_data["debrief"] = debrief
        
        # Extract grade
        for line in debrief.split("\n"):
            if "SHIFT GRADE" in line:
                run_data["grade"] = line.strip()
                break
        
    except Exception as e:
        error_msg = f"RUN {run_num} ERROR: {e}\n{traceback.format_exc()}"
        print(error_msg)
        run_data["errors"].append(error_msg)
    
    all_results.append(run_data)


# ============================================================
# WRITE REPORT
# ============================================================

report_lines = [
    "# ERSim Playtest Report V3",
    "",
    "**Date**: 2025-03-21",
    "**Generator**: Template-based (generate_shift_cases_from_templates)",
    "**Runs**: 3 shifts, 3 cases each",
    "",
    "---",
    "",
]

for run_data in all_results:
    run_num = run_data["run"]
    strategy = ["Balanced Attention", "Trap Focus", "Minimal/Efficient"][run_num - 1]
    
    report_lines.append(f"## Run {run_num}: {strategy}")
    report_lines.append("")
    
    if run_data.get("errors"):
        report_lines.append("### ERRORS")
        for e in run_data["errors"]:
            report_lines.append(f"```\n{e}\n```")
        report_lines.append("")
    
    if run_data.get("cases"):
        report_lines.append("### Cases Generated")
        report_lines.append("")
        for i, ci in enumerate(run_data["cases"], 1):
            new_tag = "NEW" if ci.get("is_new") else "SEEN BEFORE"
            report_lines.append(f"**Bay {i}: {ci['name']}** ({new_tag})")
            report_lines.append(f"- Age/Sex: {ci['age']}{ci['sex']}")
            report_lines.append(f"- Chief Complaint: {ci['chief_complaint']}")
            report_lines.append(f"- Acuity: {ci['acuity']}")
            report_lines.append(f"- True Diagnosis: {ci['true_diagnosis']}")
            report_lines.append(f"- Correct Disposition: {ci['correct_disposition']}")
            report_lines.append(f"- Miss Reason: {ci['miss_reason']}")
            report_lines.append(f"- Time Sensitive: {ci['time_sensitive']}")
            report_lines.append(f"- Narrative: {ci['narrative_hook']}")
            report_lines.append("")
    
    if run_data.get("grade"):
        report_lines.append(f"### Grade: {run_data['grade']}")
        report_lines.append("")
    
    report_lines.append("### Full Log")
    report_lines.append("")
    report_lines.append("```")
    for line in run_data.get("log", []):
        report_lines.append(line)
    report_lines.append("```")
    report_lines.append("")
    
    if run_data.get("debrief"):
        report_lines.append("### Debrief Output")
        report_lines.append("")
        report_lines.append("```")
        report_lines.append(run_data["debrief"])
        report_lines.append("```")
        report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("")

# Summary section
report_lines.append("## Summary & Analysis")
report_lines.append("")
report_lines.append("### Grades Across Runs")
for run_data in all_results:
    run_num = run_data["run"]
    strategy = ["Balanced", "Trap Focus", "Minimal"][run_num - 1]
    grade = run_data.get("grade", "N/A")
    report_lines.append(f"- Run {run_num} ({strategy}): {grade}")
report_lines.append("")

report_lines.append("### Case Novelty")
all_new = 0
all_total = 0
for run_data in all_results:
    for ci in run_data.get("cases", []):
        all_total += 1
        if ci.get("is_new"):
            all_new += 1
report_lines.append(f"- {all_new}/{all_total} cases were NEW (not in old pool)")
report_lines.append("")

report_lines.append("### Key Findings")
report_lines.append("(See individual run logs for details on warnings, autonomous fires, and errors)")
report_lines.append("")

report_path = "/home/d48reu/ERSim/PLAYTEST_REPORT_V3.md"
with open(report_path, "w") as f:
    f.write("\n".join(report_lines))

print(f"\nReport written to {report_path}")
print(f"Total lines: {len(report_lines)}")
