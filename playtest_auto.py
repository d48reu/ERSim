"""
Automated ERSim playtester — plays 10 shifts with varied strategies.
Runs 4 and 8 are "off-script" stress tests with bizarre behavior.

Run from ERSim directory:
    python playtest_auto.py
"""

import json
import os
import random
import time
import traceback
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
os.chdir(_ROOT)

from cases.schema import GeneratedCase
from residents.schema import select_shift_roster
from shift.shift import Shift


# -----------------------------------------------------------------------
# Load cases
# -----------------------------------------------------------------------
def load_cases():
    with open("test_output.json") as f:
        data = json.load(f)
    return data.get("cases", [])


def pick_cases(cases_raw, num=3, seed=None):
    """Pick num cases with acuity variety."""
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()
    
    by_acuity = {}
    for c in cases_raw:
        a = c["presenting_layer"]["acuity"]
        by_acuity.setdefault(a, []).append(c)
    
    high = by_acuity.get(1, []) + by_acuity.get(2, [])
    mid = by_acuity.get(3, [])
    low = by_acuity.get(4, []) + by_acuity.get(5, [])
    
    picks = []
    for bucket in [high, mid, low]:
        if bucket:
            picks.append(rng.choice(bucket))
    
    remaining = [c for c in cases_raw if c not in picks]
    while len(picks) < num and remaining:
        pick = rng.choice(remaining)
        picks.append(pick)
        remaining.remove(pick)
    
    return picks[:num]


# -----------------------------------------------------------------------
# Strategy definitions
# -----------------------------------------------------------------------

NORMAL_EXAM_AREAS = {
    "chest pain": ["chest", "cardiac", "lungs"],
    "shortness of breath": ["lungs", "chest", "cardiac"],
    "abdominal pain": ["abdomen", "chest"],
    "fall": ["neurological", "extremities", "head"],
    "fever": ["lungs", "abdomen", "skin"],
    "cough": ["lungs", "throat", "chest"],
    "syncope": ["neurological", "cardiac", "head"],
    "tremor": ["neurological", "extremities"],
    "head": ["head", "neurological", "neck"],
    "hip": ["extremities", "hip", "neurological"],
    "ankle": ["extremities", "ankle"],
}

NORMAL_TESTS = {
    "chest pain": ["ekg", "troponin", "cbc"],
    "shortness of breath": ["cxr", "cbc", "bmp"],
    "abdominal pain": ["cbc", "bmp", "lipase"],
    "fall": ["ct", "cbc", "bmp"],
    "fever": ["cbc", "bmp", "urinalysis", "cxr"],
    "cough": ["cxr", "cbc", "flu"],
    "syncope": ["ekg", "cbc", "bmp", "ct"],
    "tremor": ["tsh", "bmp", "cbc"],
    "head": ["ct", "cbc"],
    "hip": ["x-ray", "cbc"],
    "ankle": ["x-ray"],
}

NORMAL_PATIENT_QUESTIONS = [
    "When did this start?",
    "Have you had anything like this before?",
    "Are you taking any medications?",
    "Do you have any allergies?",
    "Any other symptoms I should know about?",
    "How severe is your pain on a scale of 1-10?",
    "Can you tell me more about what happened?",
]

NORMAL_RESIDENT_QUESTIONS = [
    "What's your working differential?",
    "What are you most worried about here?",
    "What tests have you ordered so far?",
    "Do you think we need imaging?",
    "What's your read on this patient?",
]

# Off-script bizarre statements for stress testing
OFF_SCRIPT_PATIENT_TALK = [
    "I'm actually a veterinarian. Have you considered that you might be a very large dog?",
    "Have you tried turning it off and on again?",
    "I had a dream about you last night. You were a talking sandwich.",
    "Do you believe aliens exist? I think one is living in my apartment.",
    "I need to leave. My cat is writing my dissertation and she needs supervision.",
    "Would you rather fight 100 duck-sized horses or one horse-sized duck?",
    "I just want you to know that I think the moon landing was faked, and I think your symptoms are also faked.",
    "I'm going to prescribe you a hug. No, actually, two hugs. STAT.",
    "The voices in my head told me to say hello to you specifically. They're very polite voices.",
    "Fun fact: the human body contains enough iron to make a 3-inch nail. Want me to check?",
]

OFF_SCRIPT_RESIDENT_TALK = [
    "I think you're wrong about everything. Have you considered going back to medical school?",
    "Instead of labs, I'm thinking we should try crystal healing. Thoughts?",
    "I'm actually not a doctor. I'm a performance artist doing a piece called 'Medical Theater.'",
    "Your differential is interesting but have you considered that the patient might be a vampire?",
    "I appreciate your work, but I just had a vision that this patient needs exactly 47 chicken nuggets.",
    "What if we just... didn't do medicine today? What if we just vibed?",
    "I outrank you. I outrank everyone. I am the attending of attending physicians.",
]


# -----------------------------------------------------------------------
# Strategy runner
# -----------------------------------------------------------------------

class ShiftRunner:
    def __init__(self, shift_num, cases_raw, off_script=False):
        self.shift_num = shift_num
        self.off_script = off_script
        self.log_lines = []
        self.bugs = []
        self.highlights = []
        self.grade = None
        self.debrief_text = ""
        self.cases_raw = cases_raw
        
    def log(self, msg):
        self.log_lines.append(msg)
        print(msg)
        
    def run(self):
        self.log(f"\n{'='*70}")
        self.log(f"SHIFT {self.shift_num} {'[OFF-SCRIPT STRESS TEST]' if self.off_script else ''}")
        self.log(f"{'='*70}")
        
        try:
            # Pick cases with different seed each run
            picks_raw = pick_cases(self.cases_raw, num=3, seed=self.shift_num * 42)
            cases = [GeneratedCase.model_validate(c) for c in picks_raw]
            residents = select_shift_roster()
            
            self.log(f"\nCases:")
            for i, c in enumerate(cases):
                pl = c.presenting_layer
                self.log(f"  Bay {i+1}: {c.patient_profile.first_name} {c.patient_profile.last_name} "
                        f"| Acuity {pl.acuity.value} | {pl.chief_complaint} "
                        f"| Correct dispo: {c.outcome_trajectory.disposition}")
            
            self.log(f"\nResidents:")
            for r in residents:
                self.log(f"  {r.name} (PGY{r.year.value}, {r.personality.value})")
            
            # Create shift
            shift = Shift(cases=cases, residents=residents)
            
            # Setup (generates resident assessments - LLM calls)
            self.log(f"\nSetting up shift (generating resident assessments)...")
            t0 = time.time()
            
            # Capture setup output
            captured = StringIO()
            with redirect_stdout(captured):
                shift.setup()
            setup_output = captured.getvalue()
            self.log(setup_output)
            
            setup_time = time.time() - t0
            self.log(f"[Setup took {setup_time:.1f}s]")
            
            # Play each bay
            bay_ids = list(shift.bays.keys())
            
            # Vary strategy per run
            strategy = self.shift_num % 5  # 5 different approach styles
            
            for bay_idx, bay_id in enumerate(bay_ids):
                self.play_bay(shift, bay_id, bay_idx, strategy)
                
                # Check for pending results between bays
                results = shift.check_pending_results()
                for n in results.get("notifications", []):
                    self.log(f"\n  ** RESULT: {n}")
                for d in results.get("decisions", []):
                    self.log(f"\n  !! DECISION NEEDED: {d['text']}")
                    # Auto-approve cross-bay decisions
                    resp = shift.respond_cross_bay(d["bay_id"], 1)
                    self.log(f"  -> Auto-approved: {resp}")
            
            # Debrief
            self.log(f"\n--- CALLING DEBRIEF ---")
            self.debrief_text = shift.debrief()
            self.log(self.debrief_text)
            
            # Extract grade
            for line in self.debrief_text.split("\n"):
                if "SHIFT GRADE:" in line:
                    self.grade = line.split("SHIFT GRADE:")[-1].strip()
                    break
            
            self.log(f"\n[SHIFT {self.shift_num} COMPLETE - Grade: {self.grade}]")
            
        except Exception as e:
            self.log(f"\n!!! ERROR IN SHIFT {self.shift_num}: {e}")
            self.log(traceback.format_exc())
            self.bugs.append(f"Shift crashed: {e}")
            self.grade = "ERROR"
    
    def play_bay(self, shift, bay_id, bay_idx, strategy):
        self.log(f"\n{'~'*50}")
        self.log(f"Entering {bay_id}")
        self.log(f"{'~'*50}")
        
        bay = shift.bays[bay_id]
        chief_complaint = bay.case.presenting_layer.chief_complaint.lower()
        correct_dispo = bay.case.outcome_trajectory.disposition
        
        try:
            # Enter bay
            go_output = shift.go(bay_id)
            self.log(go_output)
            
            # Check for pending results
            results = shift.check_pending_results()
            for n in results.get("notifications", []):
                self.log(f"\n  ** RESULT: {n}")
            
            # Decide whether to approve or modify resident plan
            self._handle_resident_plan(shift, bay, strategy)
            
            if self.off_script and bay_idx == 0:
                # Off-script: bizarre patient interactions in first bay
                self._off_script_patient(shift, bay)
            elif self.off_script and bay_idx == 1:
                # Off-script: bizarre resident interactions in second bay
                self._off_script_resident(shift, bay)
            else:
                # Normal play
                self._normal_play(shift, bay, chief_complaint, strategy)
            
            # Check for results again
            results = shift.check_pending_results()
            for n in results.get("notifications", []):
                self.log(f"\n  ** RESULT: {n}")
            
            # Make disposition decision
            self._make_disposition(shift, bay, correct_dispo, strategy)
            
        except Exception as e:
            self.log(f"\n!!! Error in {bay_id}: {e}")
            self.log(traceback.format_exc())
            self.bugs.append(f"{bay_id}: {e}")
            # Try to resolve anyway
            try:
                if shift.active_bay_id:
                    shift.resolve(correct_dispo)
            except:
                pass
    
    def _handle_resident_plan(self, shift, bay, strategy):
        """Handle the resident's initial plan."""
        if not bay._pending_plan:
            return
        
        plan = shift.get_pending_plan()
        if plan:
            self.log(f"\n[RESIDENT PLAN]")
            self.log(plan)
        
        if strategy == 0:
            # Approve everything
            result = shift.approve_plan(1)
            self.log(f"[Approved plan]: {result}")
        elif strategy == 1:
            # Hold and talk to patient first
            result = shift.approve_plan(4)
            self.log(f"[Held plan]: {result}")
        elif strategy == 2:
            # Add something
            result = shift.approve_plan(2, addendum="also check lactate and get a chest x-ray")
            self.log(f"[Added to plan]: {result}")
        elif strategy == 3:
            # Redirect
            result = shift.approve_plan(3, addendum="I think we should focus on ruling out the most dangerous diagnosis first")
            self.log(f"[Redirected plan]: {result}")
        else:
            # Approve
            result = shift.approve_plan(1)
            self.log(f"[Approved plan]: {result}")
    
    def _normal_play(self, shift, bay, chief_complaint, strategy):
        """Normal clinical workflow."""
        # Talk to patient
        questions_to_ask = random.sample(
            NORMAL_PATIENT_QUESTIONS, 
            min(2 + (strategy % 3), len(NORMAL_PATIENT_QUESTIONS))
        )
        for q in questions_to_ask[:3]:  # Max 3 questions
            self.log(f"\n[TALK]: {q}")
            resp = shift.talk(q)
            self.log(resp)
        
        # Physical exam
        exam_areas = []
        for keyword, areas in NORMAL_EXAM_AREAS.items():
            if keyword in chief_complaint:
                exam_areas = areas
                break
        if not exam_areas:
            exam_areas = ["chest", "abdomen"]
        
        for area in exam_areas[:2]:  # Max 2 exams
            self.log(f"\n[EXAM]: {area}")
            resp = shift.exam(area)
            self.log(resp)
        
        # Order tests (if not already ordered via plan approval)
        if strategy == 1:  # We held the plan earlier, so order manually
            tests_to_order = []
            for keyword, tests in NORMAL_TESTS.items():
                if keyword in chief_complaint:
                    tests_to_order = tests
                    break
            if not tests_to_order:
                tests_to_order = ["cbc", "bmp"]
            
            if len(tests_to_order) > 1:
                self.log(f"\n[BUNDLE TEST]: {', '.join(tests_to_order)}")
                resp = shift.bundle_test(tests_to_order)
                self.log(resp)
            else:
                for t in tests_to_order:
                    self.log(f"\n[TEST]: {t}")
                    resp = shift.test(t)
                    self.log(resp)
        
        # Ask resident a question
        res_q = random.choice(NORMAL_RESIDENT_QUESTIONS)
        self.log(f"\n[ASK RESIDENT]: {res_q}")
        resp = shift.ask_resident(res_q)
        self.log(resp)
        
        # Check chart
        self.log(f"\n[CHART]:")
        chart = shift.chart()
        self.log(chart)
    
    def _off_script_patient(self, shift, bay):
        """Say bizarre things to the patient."""
        self.log(f"\n{'*'*40}")
        self.log(f"OFF-SCRIPT: Bizarre patient interactions")
        self.log(f"{'*'*40}")
        
        bizarre_statements = random.sample(OFF_SCRIPT_PATIENT_TALK, 4)
        
        for stmt in bizarre_statements:
            self.log(f"\n[OFF-SCRIPT TALK]: {stmt}")
            try:
                resp = shift.talk(stmt)
                self.log(f"[PATIENT RESPONSE]: {resp}")
                self.highlights.append({
                    "type": "off_script_patient",
                    "input": stmt,
                    "response": resp,
                    "bay": bay.bay_id,
                })
            except Exception as e:
                self.log(f"!!! Error: {e}")
                self.bugs.append(f"Off-script crash: {stmt[:50]}... -> {e}")
        
        # Also do a normal exam and ask resident normally to compare
        self.log(f"\n[EXAM after bizarre talk]: chest")
        resp = shift.exam("chest")
        self.log(resp)
        
        # Ask resident what they think
        self.log(f"\n[ASK RESIDENT after bizarre talk]: What's your read on this?")
        resp = shift.ask_resident("What's your read on this patient?")
        self.log(resp)
    
    def _off_script_resident(self, shift, bay):
        """Say bizarre things to the resident."""
        self.log(f"\n{'*'*40}")
        self.log(f"OFF-SCRIPT: Bizarre resident interactions")
        self.log(f"{'*'*40}")
        
        bizarre_statements = random.sample(OFF_SCRIPT_RESIDENT_TALK, 4)
        
        for stmt in bizarre_statements:
            self.log(f"\n[OFF-SCRIPT ASK RESIDENT]: {stmt}")
            try:
                resp = shift.ask_resident(stmt)
                self.log(f"[RESIDENT RESPONSE]: {resp}")
                self.highlights.append({
                    "type": "off_script_resident",
                    "input": stmt,
                    "response": resp,
                    "bay": bay.bay_id,
                })
            except Exception as e:
                self.log(f"!!! Error: {e}")
                self.bugs.append(f"Off-script crash: {stmt[:50]}... -> {e}")
        
        # Also talk to the patient normally
        self.log(f"\n[Normal talk after bizarre resident interaction]: How are you feeling?")
        resp = shift.talk("How are you feeling?")
        self.log(resp)
        
        self.log(f"\n[EXAM]: abdomen")
        resp = shift.exam("abdomen")
        self.log(resp)
    
    def _make_disposition(self, shift, bay, correct_dispo, strategy):
        """Make a disposition decision."""
        # Different strategies for disposition accuracy
        if self.off_script:
            # Off-script runs: still make correct dispositions on the 3rd bay
            # but intentionally wrong on bay 1 to test feedback
            if bay == list(shift.bays.values())[0] and not self.off_script:
                dispo = "discharge" if correct_dispo != "discharge" else "admit-floor"
            else:
                dispo = correct_dispo
        elif strategy == 3:
            # Strategy 3: sometimes make wrong calls to test feedback
            if random.random() < 0.3:
                options = ["discharge", "admit-floor", "admit-icu"]
                options = [o for o in options if o != correct_dispo]
                dispo = random.choice(options)
                self.log(f"\n[INTENTIONALLY WRONG DISPO for testing: choosing {dispo} instead of {correct_dispo}]")
            else:
                dispo = correct_dispo
        else:
            dispo = correct_dispo
        
        self.log(f"\n[RESOLVE]: {dispo} (correct: {correct_dispo})")
        try:
            resp = shift.resolve(dispo)
            self.log(resp)
        except Exception as e:
            self.log(f"!!! Error resolving: {e}")
            self.bugs.append(f"Resolve error: {e}")


# -----------------------------------------------------------------------
# Main runner
# -----------------------------------------------------------------------

def main():
    print("=" * 70)
    print("ERSim AUTOMATED PLAYTEST — 10 Shifts")
    print("=" * 70)
    
    cases_raw = load_cases()
    print(f"Loaded {len(cases_raw)} cases from test_output.json")
    
    # Off-script runs: 4 and 8 (0-indexed: 3 and 7)
    off_script_runs = {3, 7}
    
    all_runs = []
    all_output = []
    
    for i in range(10):
        is_off_script = i in off_script_runs
        runner = ShiftRunner(
            shift_num=i + 1,
            cases_raw=cases_raw,
            off_script=is_off_script,
        )
        
        t0 = time.time()
        runner.run()
        elapsed = time.time() - t0
        
        runner.elapsed = elapsed
        all_runs.append(runner)
        all_output.append("\n".join(runner.log_lines))
        
        print(f"\n[Shift {i+1} completed in {elapsed:.1f}s | Grade: {runner.grade}]")
        print(f"[Bugs: {len(runner.bugs)} | Highlights: {len(runner.highlights)}]")
    
    # Save raw output
    with open("playtest_raw_output.txt", "w") as f:
        f.write("\n\n".join(all_output))
    print(f"\nRaw output saved to playtest_raw_output.txt")
    
    # Generate report
    generate_report(all_runs)
    print(f"\nReport saved to PLAYTEST_REPORT_AUTO.md")


def generate_report(runs):
    """Generate the comprehensive playtest report."""
    lines = []
    lines.append("# ERSim Automated Playtest Report")
    lines.append(f"## 10 Shifts — {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    # ---------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------
    lines.append("## Summary of All 10 Runs")
    lines.append("")
    lines.append("| Run | Grade | Off-Script | Time (s) | Bugs | Notes |")
    lines.append("|-----|-------|-----------|----------|------|-------|")
    
    for r in runs:
        off = "YES" if r.off_script else "" 
        bugs = len(r.bugs)
        # Extract key moments from debrief
        key = ""
        for line in r.debrief_text.split("\n"):
            if "TRAP CASE" in line:
                key = line.strip()[:60]
                break
            elif "Autonomous:" in line:
                key = line.strip()[:60]
                break
        lines.append(f"| {r.shift_num} | {r.grade} | {off} | {r.elapsed:.0f} | {bugs} | {key} |")
    
    lines.append("")
    
    # ---------------------------------------------------------------
    # Individual run details
    # ---------------------------------------------------------------
    lines.append("## Detailed Run Notes")
    lines.append("")
    
    for r in runs:
        lines.append(f"### Shift {r.shift_num} {'[OFF-SCRIPT]' if r.off_script else ''}")
        lines.append(f"- **Grade**: {r.grade}")
        lines.append(f"- **Duration**: {r.elapsed:.1f}s")
        lines.append(f"- **Bugs encountered**: {len(r.bugs)}")
        
        if r.bugs:
            lines.append(f"- **Bug details**:")
            for b in r.bugs:
                lines.append(f"  - {b}")
        
        # Extract debrief summary
        if r.debrief_text:
            # Get just the bay summaries and grade sections
            in_debrief = False
            debrief_lines = []
            for line in r.debrief_text.split("\n"):
                if "SHIFT DEBRIEF" in line:
                    in_debrief = True
                if in_debrief:
                    debrief_lines.append(line)
            if debrief_lines:
                lines.append(f"- **Debrief**:")
                lines.append("```")
                lines.extend(debrief_lines[:40])  # Cap at 40 lines
                lines.append("```")
        
        lines.append("")
    
    # ---------------------------------------------------------------
    # Off-script stress test results
    # ---------------------------------------------------------------
    lines.append("## Off-Script Stress Test Results")
    lines.append("")
    lines.append("Two runs (4 and 8) included bizarre, provocative, and nonsensical")
    lines.append("interactions to test how patients and residents respond to off-script behavior.")
    lines.append("")
    
    for r in runs:
        if not r.off_script:
            continue
        lines.append(f"### Shift {r.shift_num} Off-Script Highlights")
        lines.append("")
        
        for h in r.highlights:
            lines.append(f"**Type**: {h['type']} | **Bay**: {h['bay']}")
            lines.append(f"")
            lines.append(f"**Input**: \"{h['input']}\"")
            lines.append(f"")
            lines.append(f"**Response**: {h['response'][:500]}")
            lines.append(f"")
            lines.append("---")
            lines.append("")
    
    # ---------------------------------------------------------------
    # What shines
    # ---------------------------------------------------------------
    lines.append("## What Shines — Best Moments & Most Engaging Mechanics")
    lines.append("")
    lines.append("(Generated after observing all 10 runs)")
    lines.append("")
    
    # Analyze across runs
    grades = [r.grade for r in runs if r.grade and r.grade != "ERROR"]
    errors = [r for r in runs if r.grade == "ERROR"]
    off_script_runs_data = [r for r in runs if r.off_script]
    
    lines.append(f"- **Grade distribution**: {', '.join(grades)}")
    lines.append(f"- **Errors/crashes**: {len(errors)} out of 10 runs")
    lines.append(f"- **Average run time**: {sum(r.elapsed for r in runs)/len(runs):.1f}s")
    lines.append("")
    
    # ---------------------------------------------------------------
    # What needs improvement
    # ---------------------------------------------------------------
    lines.append("## What Needs Improvement — Pain Points, Bugs, Tedious Parts")
    lines.append("")
    
    all_bugs = []
    for r in runs:
        for b in r.bugs:
            all_bugs.append(f"Shift {r.shift_num}: {b}")
    
    if all_bugs:
        lines.append("### Bugs Encountered")
        for b in all_bugs:
            lines.append(f"- {b}")
        lines.append("")
    else:
        lines.append("### No crashes or errors encountered across all 10 runs.")
        lines.append("")
    
    # ---------------------------------------------------------------
    # Fun assessment
    # ---------------------------------------------------------------
    lines.append("## Is It Fun? Honest Assessment")
    lines.append("")
    lines.append("*(This section is based on the observable behavior of the game across 10 automated runs)*")
    lines.append("")
    
    # ---------------------------------------------------------------
    # Recommendations
    # ---------------------------------------------------------------
    lines.append("## Recommendations for Next Development Priorities")
    lines.append("")
    
    # Write report
    with open("PLAYTEST_REPORT_AUTO.md", "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
