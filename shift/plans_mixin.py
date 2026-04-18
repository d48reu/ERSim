"""Resident plan approval, pivots, and follow-up suggestions."""

from __future__ import annotations

import json
import re

from llm import get_client

from .bay import Bay


class ShiftPlansMixin:
    def _format_pivot(self, bay, pivot) -> str:
        """Render a pivot interrupt — resident's updated plan, not a menu."""
        res_name = bay.resident.name.split()[0]
        lines = [
            f"\n[{res_name.upper()} — plan update]",
            f"{res_name}: {pivot.what_they_say}",
            f"",
            f"  1. Go ahead",
            f"  2. Redirect",
            f"  (or ignore and keep going)",
        ]
        # Store as a pending plan so 1/2 work
        bay._pending_pivot = pivot
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
        lines = [""]

        # Show the resident's clinical read so the player can evaluate
        if hasattr(plan, "differential") and plan.differential:
            dx_str = " / ".join(plan.differential[:2])
            lines.append(f"  {res_name}'s read: {dx_str}")
        if hasattr(plan, "flags") and plan.flags:
            for flag in plan.flags[:2]:
                lines.append(f"  ! {flag}")
        if hasattr(plan, "confidence"):
            conf = getattr(plan, "confidence", "")
            if conf:
                lines.append(f"  Confidence: {conf}")

        lines.append("")
        lines.append(f"  Plan: {plan.plan_summary}")
        if hasattr(plan, "plan_tests") and plan.plan_tests:
            lines.append(f"  Tests: {', '.join(plan.plan_tests)}")
        if hasattr(plan, "plan_questions") and plan.plan_questions:
            lines.append(f"  Questions: {'; '.join(plan.plan_questions[:2])}")
        lines += [
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
            bay.note_attending_intervention("approved resident plan")
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
            bay.note_attending_intervention(
                f"approved plan but added: {addendum}",
                challenged=True,
            )
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
            bay.note_attending_intervention(
                f"redirected plan: {addendum}",
                challenged=True,
            )
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
            bay.note_attending_intervention(
                "held plan to pressure-test the story first",
                challenged=True,
            )
            bay.record("attending", "approve_plan", "held plan — talking to patient first")
            return f"[{res_name.upper()}]: No problem. I'll be right here."

        return f"Choose 1, 2, 3, or 4."

    def _execute_plan(self, bay, plan) -> str:
        """Run the plan's tests and questions. Returns combined output."""
        output = []
        bay.absorb_resident_assessment(plan, mode="responsive")
        if plan.plan_tests:
            # approve_plan already ticked for this attending action; the
            # bundled orders share that tick so Acuity 1 bays are not
            # double-charged on a single click.
            result = self.bundle_test(plan.plan_tests, suppress_tick=True)
            output.append(result)
        if plan.plan_questions:
            res_name = bay.resident.name.split()[0]
            for q in plan.plan_questions[:2]:  # Max 2 questions per plan
                before_summary = bay.patient_session.get_reveal_summary()
                response = bay.patient_session.interact(q)
                after_summary = bay.patient_session.get_reveal_summary()
                bay.note_reveal_change(before_summary, after_summary)
                patient_name = bay.patient_name.split()[0]
                output.append(f"[{res_name.upper()} asks]: {q}")
                output.append(f"[{patient_name.upper()}]: {response}")
                bay.record("resident", "plan_question", q)
                bay.record("patient", "plan_question", response)
        return "\n".join(output)

    def _interpret_addendum(self, bay, plan, addendum: str) -> dict:
        """Use LLM to interpret player's free-text addition."""
        import json, re
        client = get_client()
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
        import json, re
        client = get_client()
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
        """Respond to resident's pivot plan update. 1=go ahead, 2=redirect."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        pivot = getattr(bay, "_pending_pivot", None)
        if not pivot:
            return "No pending plan update."

        res_name = bay.resident.name.split()[0]
        bay._pending_pivot = None

        if n == 1:
            # Go ahead — execute the resident's recommended plan_tests
            bay.note_attending_intervention("approved updated resident plan")
            bay.record("attending", "pivot_approved", "approved updated plan")
            bay.resident_ai.attending_backed("approved pivot plan")
            tests = pivot.plan_tests if pivot.plan_tests else []
            output = [f"[{res_name.upper()}]: Got it, running with it."]
            if not tests:
                return "\n".join(output)
            # Queue all the updated plan tests
            for test_name in tests:
                _, message = self._queue_test_result(bay, test_name, actor="attending")
                output.append(f"  {message}")
                continue
                if self._validate_test_name(test_name):
                    delay = self._get_test_delay(test_name)
                    if delay == 998:
                        bay.record("attending", "test", test_name)
                        output.append(f"  [{test_name}] drawn and sent — results post-shift")
                    elif delay < 998:
                        full_result = bay.patient_session.order_test(test_name)
                        bay.record("attending", "test", test_name)
                        due_turn = self.global_turn + delay
                        due_clock = self._format_clock(due_turn)
                        bay.pending_results.append((due_turn, test_name, full_result, bay.bay_id))
                        delay_min = delay * SHIFT_MINUTES_PER_TURN
                        output.append(f"  [{test_name}] ordered — due ~{due_clock} (~{delay_min} min)")
                else:
                    output.append(f"  [{test_name}] — not recognized, skipped")
            return "\n".join(output)

        elif n == 2:
            # Redirect — prompt for direction
            bay.note_attending_intervention(
                "redirected updated resident plan",
                challenged=True,
            )
            bay.record("attending", "pivot_redirected", "redirected updated plan")
            bay.resident_ai.attending_overrode("redirected pivot plan")
            return (
                f"[{res_name.upper()}]: Okay, what direction?\n"
                f"  (type: redirect <your thinking>)"
            )

        return "Type 1 to go ahead or 2 to redirect."
