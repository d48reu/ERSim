"""
Shift — the top-level game session.

Owns all active bays, routes attending attention,
manages the global turn counter, fires autonomous
resident actions when timers cross threshold.

The attending's action surface:
  go <bay>        — move attention to a bay
  talk <message>  — talk to current patient
  exam <maneuver> — physical exam
  test <name>     — order a test
  ask <question>  — ask resident a question
  resident        — get resident's current read
  family          — bring family member in
  resolve <dispo> — close the case (discharge/admit/etc)
  status          — overview of all bays

Every action ticks the timer on all OTHER bays.
"""

from dataclasses import dataclass, field
from typing import Optional

from cases.schema import GeneratedCase
from residents.schema import Resident, make_default_roster
from .bay import Bay, BayStatus

# ---------------------------------------------------------------------------
# Test result delays — in global turns (1 turn ~ 5 min)
# ---------------------------------------------------------------------------
# Special value 999 = never resolves this shift (blood cultures, PPD, etc.)

TEST_DELAYS = {
    # Near-instant
    "glucose":          1,
    "fingerstick":      1,
    "ekg":              2,
    "ecg":              2,
    # Quick labs
    "cxr":              4,
    "chest x":          4,
    "xray":             4,
    "x-ray":            4,
    "urinalysis":       3,
    "ua":               3,
    "urine":            3,
    "flu swab":         3,
    "flu":              3,
    "strep":            3,
    "monospot":         4,
    "pregnancy":        2,
    "hcg":              2,
    # Standard labs (45 min)
    "bmp":              9,
    "cbc":              9,
    "troponin":         9,
    "lactate":          9,
    "procalcitonin":    9,
    "d-dimer":          9,
    "ddimer":           9,
    "bnp":              9,
    "liver":            9,
    "coag":             9,
    "inr":              9,
    "lipase":           9,
    "tsh":              9,
    "thyroid":          9,
    "hiv":              9,
    "monospot":         9,
    # Imaging (30-60 min)
    "ct":               8,
    "cta":              8,
    "mri":             12,
    "ultrasound":       8,
    "echo":            10,
    # Never resolves this shift
    "blood culture":  999,
    "culture":        999,
    "ppd":            999,
    "tb":             999,
    "sputum":         999,
}

SHIFT_START_TURN = 0
SHIFT_START_HOUR = 19   # 7 PM
SHIFT_MINUTES_PER_TURN = 5
SHIFT_DURATION_TURNS = 96  # 8 hours


@dataclass
class ShiftStatus:
    """Snapshot of the current shift state."""
    active_bay: Optional[str]
    bays: list
    global_turn: int
    shift_elapsed_actions: int


class Shift:
    """
    The core game session loop.

    Create with a list of cases and a resident roster.
    Call setup() to initialize all bays.
    Then use the action methods to run the session.
    """

    def __init__(
        self,
        cases: list[GeneratedCase],
        residents: Optional[list[Resident]] = None,
        model: str = "anthropic/claude-haiku-4-5",
    ):
        self.model = model
        self.residents = residents or make_default_roster()
        self.global_turn: int = 0
        self.active_bay_id: Optional[str] = None
        self.bays: dict[str, Bay] = {}
        self._autonomous_queue: list[str] = []

        # Assign cases to bays with rotating resident assignment
        for i, case in enumerate(cases):
            bay_id = f"Bay {i+1}"
            resident = self.residents[i % len(self.residents)]
            bay = Bay(
                bay_id=bay_id,
                case=case,
                resident=resident,
            )
            self.bays[bay_id] = bay

    def setup(self):
        """Initialize all bays. Call before starting the session."""
        for bay in self.bays.values():
            bay.setup(model=self.model)
            bay.resident_ai.set_shift_context({
                "shift_type": "evening",
                "hours_elapsed": 0,
                "department_pressure": "moderate",
            })
            # Generate resident's proactive opening for each case
            assessment = bay.resident_ai.proactive(bay.case)
            bay.resident_opening = assessment.what_they_say
            bay.resident_opening_data = assessment
            bay._pending_plan = assessment  # Store for approval flow
            bay.status = BayStatus.SUPERVISED

        print(self._render_shift_start())

    # ------------------------------------------------------------------
    # Attention routing
    # ------------------------------------------------------------------

    def go(self, bay_id: str) -> str:
        """
        Attending moves to a bay.
        Ticks all other bays.
        """
        if bay_id not in self.bays:
            # Try fuzzy match — "3" matches "Bay 3"
            for bid in self.bays:
                if bay_id in bid or bid.lower().endswith(bay_id.lower()):
                    bay_id = bid
                    break
            else:
                available = ", ".join(self.bays.keys())
                return f"No bay '{bay_id}'. Available: {available}"

        bay = self.bays[bay_id]

        if bay.status == BayStatus.RESOLVED:
            return f"{bay_id} is closed — {bay.disposition}."

        # Tick all other supervised bays
        self._tick_others(bay_id)

        # Set active bay
        prev = self.active_bay_id
        self.active_bay_id = bay_id
        bay.status = BayStatus.ACTIVE
        bay.timer_ticks = 0  # Reset timer — attending is here now

        output = []

        # Show resident opening if first visit
        if bay.resident_opening and bay_id != prev:
            res_name = bay.resident.name.split()[0]
            output.append(
                f"\n[{res_name} intercepts you]\n"
                f"{res_name}: {bay.resident_opening}\n"
            )
            bay.resident_opening = ""  # Only show once
            bay.record("resident", "resident_proactive",
                      bay.resident_opening_data.what_they_say if bay.resident_opening_data else "",
                      internal=str(bay.resident_opening_data))

        output.append(self._render_bay_header(bay))

        # Show approval prompt if plan is waiting
        plan_prompt = self.get_pending_plan()
        if plan_prompt:
            output.append(plan_prompt)

        return "\n".join(output)

    def leave(self) -> str:
        """
        Attending leaves current bay.
        Bay goes to SUPERVISED — timer starts ticking.
        """
        if not self.active_bay_id:
            return "You're not in a bay."

        bay = self.bays[self.active_bay_id]
        if bay.status != BayStatus.RESOLVED:
            bay.status = BayStatus.SUPERVISED
            bay.timer_ticks = 0

        self.active_bay_id = None
        return self._render_status()

    # ------------------------------------------------------------------
    # In-bay actions
    # ------------------------------------------------------------------

    def talk(self, message: str) -> str:
        """Talk to the current patient."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay. Use 'go <bay>' first."

        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        response = bay.patient_session.interact(message)
        patient_name = bay.patient_name.split()[0]

        bay.record("attending", "attend", message)
        bay.record("patient", "attend", response)

        output = [f"[{patient_name.upper()}]: {response}"]

        # Nudge logic — if plan is pending and player keeps talking to patient
        if bay._pending_plan and not bay._plan_on_hold:
            bay._plan_prompt_turns += 1
            res_name = bay.resident.name.split()[0]
            if bay._plan_prompt_turns == 2:
                # First nudge — re-show the plan summary
                output.append(self.get_pending_plan())
            elif bay._plan_prompt_turns >= 4:
                # Second nudge — explicit ask
                output.append(
                    f"\n[{res_name.upper()}]: Hey — do you want me to hold on "
                    f"that workup, or should I go ahead?"
                )
                output.append(self.get_pending_plan())
                bay._plan_prompt_turns = 0  # Reset so it doesn't spam

        return "\n".join(output)

    def exam(self, maneuver: str) -> str:
        """Perform a physical exam maneuver."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        result = bay.patient_session.examine(maneuver)
        bay.record("attending", "exam", maneuver)
        bay.record("patient", "exam", result)

        return result

    # Known clinical test keywords — any test name must contain at least one
    _KNOWN_TEST_WORDS = {
        "ekg", "ecg", "cxr", "xray", "x-ray", "ct", "mri", "echo", "ultrasound",
        "glucose", "fingerstick", "bmp", "cbc", "troponin", "lactate", "d-dimer",
        "ddimer", "bnp", "procalcitonin", "urinalysis", "ua", "urine", "culture",
        "blood", "flu", "strep", "monospot", "hiv", "hcg", "pregnancy", "coag",
        "inr", "pt", "ptt", "liver", "lfts", "lipase", "tsh", "thyroid", "crp",
        "esr", "ferritin", "iron", "b12", "folate", "magnesium", "phosphate",
        "ammonia", "cortisol", "trop", "chest", "abdominal", "pelvis", "pelvic",
        "head", "brain", "spine", "cardiac", "renal", "pulmonary", "angio",
        "cta", "ppd", "tb", "sputum", "gram", "legionella", "urine antigen",
        "monospot", "ebv", "cmv", "rsv", "covid", "panel", "toxicology", "tox",
        "acetaminophen", "aspirin", "alcohol", "ethanol", "drug", "screen",
        "abg", "vbg", "gas", "oximetry", "peak flow", "spirometry",
    }

    def _validate_test_name(self, test_name: str) -> bool:
        """
        Return True if test_name looks like a real clinical test.
        Rejects: single chars, pure demographics (34F, 16M),
        generic words, and anything under 3 chars.
        """
        name = test_name.strip()
        if len(name) <= 2:
            return False
        # Reject pure demographic patterns: number + letter (34F, 16M, 71M)
        import re
        if re.match(r'^\d+[MmFf]$', name):
            return False
        # Reject single common words that aren't tests
        _JUNK = {"pain", "fever", "cough", "fall", "home", "chest", "back",
                 "head", "arm", "leg", "x", "test", "result", "the", "and",
                 "with", "for", "days", "male", "female", "old", "year"}
        if name.lower() in _JUNK:
            return False
        # Must contain at least one known clinical word
        name_lower = name.lower()
        return any(kw in name_lower for kw in self._KNOWN_TEST_WORDS)

    def _summarize_result(self, test_name: str, full_result: str) -> str:
        """
        Return a short 1-2 sentence summary of a test result.
        Full result is stored for chart view.
        """
        # Extract the most informative line — look for impression/result/finding
        lines = [l.strip() for l in full_result.split('\n') if l.strip()]
        # Priority: lines containing key summary words
        priority_words = [
            "impression", "result", "finding", "conclusion",
            "interpretation", "positive", "negative", "normal",
            "elevated", "abnormal", "consistent", "confirmed",
            "no acute", "within normal",
        ]
        for word in priority_words:
            for line in lines:
                if word in line.lower() and len(line) > 10:
                    # Cap at 120 chars
                    return line[:120]
        # Fallback: first substantive line
        for line in lines:
            if len(line) > 15:
                return line[:120]
        return full_result[:120]

    def _get_test_delay(self, test_name: str) -> int:
        """Return turn delay for a test. Matches on substring of test name."""
        name_lower = test_name.lower()
        for key, delay in TEST_DELAYS.items():
            if key in name_lower:
                return delay
        return 6  # Default: ~30 min for unknown tests

    def _format_clock(self, turn: int) -> str:
        """Convert global turn to wall clock time string."""
        total_minutes = SHIFT_START_HOUR * 60 + turn * SHIFT_MINUTES_PER_TURN
        h = (total_minutes // 60) % 24
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"

    def test(self, test_name: str, suppress_pivot: bool = False) -> str:
        """Order a test. Result is deferred by realistic delay."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        # Validate before doing anything
        if not self._validate_test_name(test_name):
            return f"[?] '{test_name}' — not recognized as a test. Try being more specific."

        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        delay = self._get_test_delay(test_name)

        if delay >= 999:
            bay.record("attending", "test", test_name)
            return (
                f"[{test_name}] ordered — results not available this shift. "
                f"Flag for follow-up."
            )

        # Get full result from patient session but don't show it yet
        full_result = bay.patient_session.order_test(test_name)
        bay.record("attending", "test", test_name)
        bay.record("system", "test_pending", f"{test_name} — due turn {self.global_turn + delay}")

        due_turn = self.global_turn + delay
        due_clock = self._format_clock(due_turn)
        # Store (due_turn, test_name, full_result, bay_id)
        bay.pending_results.append((due_turn, test_name, full_result, bay.bay_id))

        delay_min = delay * SHIFT_MINUTES_PER_TURN
        return f"[{test_name}] ordered — results due ~{due_clock} (~{delay_min} min)"

    def bundle_test(self, test_names: list[str]) -> str:
        """Order multiple tests as ONE turn, then defer all results."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        # Tick once for the whole bundle — it's one attending action
        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        output = []
        skipped = []
        for name in test_names:
            if not self._validate_test_name(name):
                skipped.append(name)
                continue
            delay = self._get_test_delay(name)
            if delay >= 999:
                bay.record("attending", "test", name)
                output.append(f"  [{name}] — not available this shift, flag for follow-up")
                continue
            full_result = bay.patient_session.order_test(name)
            bay.record("attending", "test", name)
            bay.record("system", "test_pending", f"{name} — due turn {self.global_turn + delay}")
            due_turn = self.global_turn + delay
            due_clock = self._format_clock(due_turn)
            bay.pending_results.append((due_turn, name, full_result, bay.bay_id))
            delay_min = delay * SHIFT_MINUTES_PER_TURN
            output.append(f"  [{name}] ordered — due ~{due_clock} (~{delay_min} min)")

        if skipped:
            output.append(f"  [skipped — not recognized: {', '.join(skipped)}]")

        return "Tests ordered:\n" + "\n".join(output)



    def _format_pivot(self, bay, pivot) -> str:
        """Render a pivot interrupt block."""
        res_name = bay.resident.name.split()[0]
        lines = [
            f"\n[{res_name.upper()} — reacts to results]",
            f"{res_name}: {pivot.what_they_say}",
        ]
        if pivot.options:
            lines.append("")
            for i, opt in enumerate(pivot.options):
                marker = ">" if i == pivot.recommended else " "
                lines.append(f"  {marker} {i+1}. {opt}")
            lines.append("")
            lines.append(
                f"  (type 1/2/3 to follow {res_name}'s suggestion, "
                f"or proceed your own way)"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Approval system
    # ------------------------------------------------------------------

    def get_pending_plan(self) -> str:
        """Return approval prompt if a plan is waiting, else empty string."""
        bay = self._require_active_bay()
        if not bay or not bay._pending_plan:
            return ""
        plan = bay._pending_plan
        res_name = bay.resident.name.split()[0]
        lines = [
            f"\n  {res_name}'s plan: {plan.plan_summary}",
            "",
            "    > 1. Go ahead",
            "      2. Go ahead, but add something",
            "      3. Change the direction",
            "      4. Hold — I want to talk to the patient first",
        ]
        return "\n".join(lines)

    def approve_plan(self, choice: int, addendum: str = "") -> str:
        """
        Process the attending's response to the resident's plan.
        1 = approve, 2 = approve + add, 3 = redirect, 4 = hold
        """
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."
        if not bay._pending_plan:
            return "No pending plan."

        plan = bay._pending_plan
        res_name = bay.resident.name.split()[0]
        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        if choice == 1:
            # Full approval — run the plan as-is
            bay._pending_plan = None
            bay._plan_on_hold = False
            bay.record("attending", "approve_plan", "approved resident plan")
            bay.resident_ai.attending_backed("approved workup plan")
            return self._execute_plan(bay, plan)

        elif choice == 2:
            # Approve + add — interpret addendum then run
            if not addendum:
                return (
                    f"  What do you want to add?\n"
                    f"  (type: add <your addition>)"
                )
            extra = self._interpret_addendum(bay, plan, addendum)
            bay._pending_plan = None
            bay._plan_on_hold = False
            bay.record("attending", "approve_plan", f"approved + added: {addendum}")
            output = [f"[{res_name.upper()}]: Got it — adding {extra['summary']}. Running now."]
            # Merge extra tests into plan
            plan.plan_tests = plan.plan_tests + extra.get("tests", [])
            plan.plan_questions = plan.plan_questions + extra.get("questions", [])
            output.append(self._execute_plan(bay, plan))
            return "\n".join(output)

        elif choice == 3:
            # Redirect — attending changes the direction
            if not addendum:
                return (
                    f"  What direction do you want to take?\n"
                    f"  (type: redirect <your thinking>)"
                )
            redirect = self._interpret_redirect(bay, plan, addendum)
            bay._pending_plan = None
            bay._plan_on_hold = False
            bay.record("attending", "approve_plan", f"redirected: {addendum}")
            bay.resident_ai.attending_overrode(f"redirected workup: {addendum}")
            output = [f"[{res_name.upper()}]: {redirect['reaction']}"]
            plan.plan_tests = redirect.get("tests", plan.plan_tests)
            plan.plan_questions = redirect.get("questions", plan.plan_questions)
            output.append(self._execute_plan(bay, plan))
            return "\n".join(output)

        elif choice == 4:
            # Hold — pause timer, resident waits
            bay._plan_on_hold = True
            bay._plan_prompt_turns = 0
            bay.record("attending", "approve_plan", "held plan — talking to patient first")
            return f"[{res_name.upper()}]: No problem. I'll be right here."

        return f"Choose 1, 2, 3, or 4."

    def _execute_plan(self, bay, plan) -> str:
        """Run the plan's tests and questions. Returns combined output."""
        output = []
        if plan.plan_tests:
            result = self.bundle_test(plan.plan_tests)
            output.append(result)
        if plan.plan_questions:
            res_name = bay.resident.name.split()[0]
            for q in plan.plan_questions[:2]:  # Max 2 questions per plan
                response = bay.patient_session.interact(q)
                patient_name = bay.patient_name.split()[0]
                output.append(f"[{res_name.upper()} asks]: {q}")
                output.append(f"[{patient_name.upper()}]: {response}")
                bay.record("resident", "plan_question", q)
                bay.record("patient", "plan_question", response)
        return "\n".join(output)

    def _interpret_addendum(self, bay, plan, addendum: str) -> dict:
        """Use LLM to interpret player's free-text addition."""
        from openai import OpenAI
        import os, json, re
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            env_path = os.path.expanduser("~/.hermes/.env")
            if os.path.exists(env_path):
                for line in open(env_path):
                    if line.strip().startswith("OPENROUTER_API_KEY="):
                        key = line.strip().split("=", 1)[1]
                        break
        client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
        pl = bay.case.presenting_layer
        try:
            resp = client.chat.completions.create(
                model=self.model,
                max_tokens=150,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Patient: {pl.age}{pl.sex}, {pl.chief_complaint}\n"
                        f"Resident's plan: {plan.plan_summary}\n"
                        f"Attending wants to add: {addendum}\n\n"
                        f"Translate the attending's addition into specific clinical tests "
                        f"and/or patient questions. Return raw JSON only:\n"
                        f"{{\"summary\": \"one phrase\", "
                        f"\"tests\": [\"test1\"], \"questions\": [\"question1\"]}}"
                    )
                }]
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            return json.loads(raw)
        except Exception:
            return {"summary": addendum, "tests": [], "questions": [addendum]}

    def _interpret_redirect(self, bay, plan, redirect_text: str) -> dict:
        """Use LLM to interpret player's redirect and generate resident reaction."""
        from openai import OpenAI
        import os, json, re
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            env_path = os.path.expanduser("~/.hermes/.env")
            if os.path.exists(env_path):
                for line in open(env_path):
                    if line.strip().startswith("OPENROUTER_API_KEY="):
                        key = line.strip().split("=", 1)[1]
                        break
        client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
        pl = bay.case.presenting_layer
        personality = bay.resident.personality.value
        try:
            resp = client.chat.completions.create(
                model=self.model,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Resident personality: {personality}\n"
                        f"Patient: {pl.age}{pl.sex}, {pl.chief_complaint}\n"
                        f"Resident's plan: {plan.plan_summary}\n"
                        f"Attending redirects: {redirect_text}\n\n"
                        f"Generate the resident's reaction in their voice and "
                        f"a revised test list. Return raw JSON only:\n"
                        f"{{\"reaction\": \"resident's words\", "
                        f"\"tests\": [\"test1\"], \"questions\": [\"question1\"]}}"
                    )
                }]
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            return json.loads(raw)
        except Exception:
            return {
                "reaction": "Okay, changing course.",
                "tests": plan.plan_tests,
                "questions": plan.plan_questions,
            }

    def follow_suggestion(self, n: int) -> str:
        """Execute resident's numbered suggestion from the last pivot."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        pivot = getattr(bay, "_pending_pivot", None)
        if not pivot or not pivot.options:
            return "No pending suggestion. Order a test first."

        idx = n - 1
        if idx < 0 or idx >= len(pivot.options):
            return f"Option {n} doesn't exist. Choose 1-{len(pivot.options)}."

        chosen = pivot.options[idx]
        res_name = bay.resident.name.split()[0]
        bay.record("attending", "follow_suggestion", f"chose option {n}: {chosen}")

        # Clear pending pivot so it doesn't re-fire on the next test
        bay._pending_pivot = None

        # Execute it — treat it as a test order (most options are tests/actions)
        result = self.test(chosen)
        return f"[Following {res_name}'s suggestion: {chosen}]\n{result}"

    def ask_resident(self, question: str) -> str:
        """Ask the resident a question about the current case."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        # Build interaction summary from bay events
        summary = self._bay_interaction_summary(bay)

        response = bay.resident_ai.respond(
            case=bay.case,
            question=question,
            interaction_summary=summary,
        )

        res_name = bay.resident.name.split()[0]
        bay.record("attending", "resident_response",
                  question, internal=response.reasoning)
        bay.record("resident", "resident_response", response.what_they_say)

        output = [f"[{res_name.upper()}]: {response.what_they_say}"]
        if response.flags:
            # Show flags as subtle pressure — not a list, just the most urgent
            urgent = [f for f in response.flags if any(
                w in f.lower() for w in
                ["cardiac", "sepsis", "ischemi", "immediate", "emergent", "time"]
            )]
            if urgent:
                output.append(f"  [{res_name} looks concerned about: {urgent[0]}]")

        return "\n".join(output)

    def get_resident_read(self) -> str:
        """Get resident's unprompted current assessment."""
        return self.ask_resident(
            "What's your current read? What should we be doing?"
        )

    def family(self) -> str:
        """Bring family member into the current bay."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        result = bay.patient_session.bring_family()
        bay.record("attending", "family", result)

        # Patient reacts
        pp = bay.case.patient_profile
        reaction = bay.patient_session.interact(
            f"[{pp.key_person} has entered the room]"
        )
        patient_name = bay.patient_name.split()[0]
        bay.record("patient", "family", reaction)

        return f"{result}\n[{patient_name.upper()}]: {reaction}"

    def chart(self) -> str:
        """Show what has been revealed in the current bay."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        summary = bay.patient_session.get_reveal_summary()
        lines = [f"--- CHART: {bay.patient_name} (turn {summary['turns']}) ---"]
        lines.append(f"Family present: {summary['family_present']}")

        # Pending tests
        if bay.pending_results:
            pending_names = [r[1] for r in bay.pending_results]
            lines.append(f"Pending: {', '.join(pending_names)}")

        # Completed test results — full reports here
        test_results = getattr(bay, '_test_results', {})
        if test_results:
            lines.append(f"\n--- TEST RESULTS ---")
            for test_name, full_result in test_results.items():
                lines.append(f"\n[{test_name.upper()}]")
                lines.append(full_result)
        elif summary['tests_ordered']:
            lines.append(f"Tests ordered: {', '.join(summary['tests_ordered'])} (pending)")

        # Revealed clinical info
        if summary["revealed"]:
            lines.append(f"\n--- REVEALED ({len(summary['revealed'])}) ---")
            for r in summary["revealed"]:
                lines.append(f"  {r['information']}")

        if summary["locked"]:
            lines.append(f"\n--- STILL LOCKED ({len(summary['locked'])}) ---")
            for l in summary["locked"]:
                lines.append(f"  [{l['trigger_needed']}] {l['trigger_detail']}")

        return "\n".join(lines)

    def resolve(self, disposition: str, note: str = "") -> str:
        """
        Close a case. Disposition: discharge, admit-floor, admit-icu,
        OR, cath-lab, transfer, AMA.
        """
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        bay.status = BayStatus.RESOLVED
        bay.disposition = disposition
        bay.resolution_note = note
        bay.record("attending", "resolve", f"{disposition}: {note}")

        # Compare to correct disposition
        correct = bay.case.outcome_trajectory.disposition
        patient_name = bay.patient_name

        lines = [f"[{bay.bay_id}] {patient_name} — {disposition.upper()}"]

        if disposition.lower() == correct.lower():
            lines.append(f"  Correct disposition.")
        else:
            lines.append(
                f"  Note: Recommended was {correct}. "
                f"Outcome: {bay.case.outcome_trajectory.missed_diagnosis}"
            )

        self.active_bay_id = None
        lines.append(self._render_status())
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> str:
        return self._render_status()

    def check_pending_results(self) -> list[str]:
        """
        Check all bays for test results that are now due.
        Called at the top of each game loop iteration.
        Returns list of result strings to display.
        """
        notifications = []
        for bay_id, bay in self.bays.items():
            if not bay.pending_results:
                continue
            due = [r for r in bay.pending_results if r[0] <= self.global_turn]
            still_pending = [r for r in bay.pending_results if r[0] > self.global_turn]
            bay.pending_results = still_pending

            for (due_turn, test_name, full_result, bid) in due:
                # Store full result in bay for chart view
                if not hasattr(bay, '_test_results'):
                    bay._test_results = {}
                bay._test_results[test_name] = full_result
                bay.record("system", "test_result", f"{test_name}: {full_result}")

                # Show only a short summary inline
                summary_line = self._summarize_result(test_name, full_result)
                header = (
                    f"[{bay_id} — {bay.patient_name}]  "
                    f"{test_name.upper()}  {self._format_clock(self.global_turn)}"
                )
                notifications.append(f"{header}\n  {summary_line}\n  (type 'chart' for full report)")

                # Fire pivot interrupt with full result (capped for token safety)
                interaction_summary = self._bay_interaction_summary(bay)
                pivot = bay.resident_ai.pivot_interrupt(
                    case=bay.case,
                    test_name=test_name,
                    test_result=full_result[:300],
                    interaction_summary=interaction_summary,
                )
                if pivot.triggered and pivot.what_they_say:
                    notifications.append(self._format_pivot(bay, pivot))
                    bay._pending_pivot = pivot
                    bay.record("resident", "pivot_interrupt", pivot.what_they_say,
                              internal=pivot.pivot_reason)

        return notifications

    # ------------------------------------------------------------------
    # Timer and autonomous actions
    # ------------------------------------------------------------------

    def _tick_others(self, except_bay_id: str):
        """
        Tick all bays except the one the attending is in.
        Fire autonomous actions for any that cross threshold.
        """
        for bay_id, bay in self.bays.items():
            if bay_id == except_bay_id:
                continue
            if bay.status == BayStatus.SUPERVISED:
                crossed = bay.tick()
                if crossed:
                    self._fire_autonomous(bay_id)

    def _fire_autonomous(self, bay_id: str):
        """Resident acts autonomously. Queue notification for attending."""
        bay = self.bays[bay_id]
        bay.autonomous_fired = True
        bay.status = BayStatus.SUPERVISED  # Still supervised, action taken

        # Build case state at time of firing
        reveal_summary = bay.patient_session.get_reveal_summary()
        case_state = {
            "known_to_resident": (
                f"Triage: {bay.triage_summary}. "
                f"Tests ordered: {', '.join(reveal_summary['tests_ordered']) or 'none'}. "
                f"Revealed so far: "
                + "; ".join(r["information"] for r in reveal_summary["revealed"])
            ),
            "actions_taken": reveal_summary["tests_ordered"],
            "pending": [l["trigger_detail"] for l in reveal_summary["locked"]],
        }

        action = bay.resident_ai.act_autonomously(
            case=bay.case,
            timer_duration_minutes=bay.timer_ticks * 3,
            case_state_at_timer=case_state,
        )

        bay.record(
            "resident", "autonomous_action",
            action.what_they_tell_attending,
            internal=(
                f"Action: {action.action_taken} | "
                f"Not saying: {action.what_they_dont_say} | "
                f"Reasoning: {action.reasoning}"
            ),
        )

        # Store for when attending returns
        bay._pending_autonomous_report = action
        self._autonomous_queue.append(bay_id)

        res_name = bay.resident.name.split()[0]
        acuity = bay.acuity
        print(
            f"\n  !! [{bay_id}] {res_name} acted — "
            f"acuity {acuity} case unattended too long"
        )

    def check_autonomous_notifications(self) -> list[str]:
        """
        Return and clear any pending autonomous action notifications.
        Called at start of each go() so attending sees what happened.
        """
        notifications = []
        for bay_id in list(self._autonomous_queue):
            bay = self.bays[bay_id]
            if hasattr(bay, '_pending_autonomous_report'):
                action = bay._pending_autonomous_report
                res_name = bay.resident.name.split()[0]
                notifications.append(
                    f"[{bay_id} — {bay.patient_name}]\n"
                    f"{res_name}: {action.what_they_tell_attending}"
                )
                del bay._pending_autonomous_report
        self._autonomous_queue.clear()
        return notifications

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_shift_start(self) -> str:
        lines = [
            "",
            "=" * 60,
            "SHIFT STARTING",
            "=" * 60,
            f"{len(self.bays)} patients waiting.",
            "",
        ]
        for bay_id, bay in self.bays.items():
            acuity_label = {
                1: "IMMEDIATE", 2: "EMERGENT", 3: "URGENT",
                4: "LESS URGENT", 5: "NON-URGENT"
            }.get(bay.acuity, str(bay.acuity))
            res_name = bay.resident.name
            lines.append(
                f"  {bay_id}  [{bay.acuity} {acuity_label}]  "
                f"{bay.triage_summary[:55]}"
            )
            lines.append(f"        Resident: {res_name}")
        lines.append("")
        lines.append("Type 'go <bay>' to enter a bay.")
        lines.append("Type 'status' for overview at any time.")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _render_bay_header(self, bay: Bay) -> str:
        pp = bay.case.patient_profile
        pl = bay.case.presenting_layer
        acuity_label = {
            1: "IMMEDIATE", 2: "EMERGENT", 3: "URGENT",
            4: "LESS URGENT", 5: "NON-URGENT"
        }.get(bay.acuity, str(bay.acuity))

        lines = [
            f"\n--- {bay.bay_id}: {bay.patient_name} "
            f"[{bay.acuity} — {acuity_label}] ---",
            f"  {pl.triage_note}",
            f"  Vitals: HR {pl.vitals.hr}  "
            f"BP {pl.vitals.bp_systolic}/{pl.vitals.bp_diastolic}  "
            f"O2 {pl.vitals.o2_sat}%  "
            f"Temp {pl.vitals.temp_f}F",
            f"  Resident: {bay.resident.name}",
        ]
        return "\n".join(lines)

    def _render_status(self) -> str:
        clock = self._format_clock(self.global_turn)
        turns_left = SHIFT_DURATION_TURNS - self.global_turn
        hours_left = (turns_left * SHIFT_MINUTES_PER_TURN) // 60
        mins_left = (turns_left * SHIFT_MINUTES_PER_TURN) % 60
        lines = [f"\n--- STATUS  [{clock}  —  {hours_left}h{mins_left:02d}m remaining] ---"]
        for bay_id, bay in self.bays.items():
            marker = ">> " if bay_id == self.active_bay_id else "   "
            status_str = bay.status.value.upper()
            timer_str = f"  {bay.timer_pressure}" if bay.timer_pressure else ""
            acuity = bay.acuity
            # Show pending result count if any
            pending_str = f"  ({len(bay.pending_results)} pending)" if bay.pending_results else ""
            lines.append(
                f"{marker}{bay_id}  [{acuity}]  {bay.patient_name:<20} "
                f"{status_str:<12}{timer_str}{pending_str}"
            )
        return "\n".join(lines)

    def _bay_interaction_summary(self, bay: Bay) -> str:
        """Brief text summary of what's happened in a bay so far."""
        events = [e for e in bay.events if e.actor in ("attending", "patient")]
        if not events:
            return "No interaction yet."
        recent = events[-4:]  # Keep it short — last 4 exchanges only
        lines = []
        for e in recent:
            prefix = "ATT" if e.actor == "attending" else "PT"
            lines.append(f"{prefix}: {e.content[:60]}")  # 60 chars per line max
        return "\n".join(lines)

    def _require_active_bay(self) -> Optional[Bay]:
        if not self.active_bay_id:
            return None
        return self.bays.get(self.active_bay_id)
