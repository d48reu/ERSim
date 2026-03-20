"""
Resident AI engine.

Manages a single resident's behavior across three modes:
- proactive(): resident initiates case presentation
- respond(): resident answers attending question
- act_autonomously(): timer expired, resident acts alone

All three modes draw from the same character — competency profile,
personality archetype, current state, relationship with attending.
"""

import json
import os
import re
import sys
from typing import Optional

from openai import OpenAI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from llm import get_client, get_model

from .schema import (
    Resident,
    ResidentAssessment,
    ResidentAutonomousAction,
    ResidentPivot,
)
from .prompts import (
    PROACTIVE_SYSTEM_PROMPT,
    RESPONSIVE_SYSTEM_PROMPT,
    AUTONOMOUS_SYSTEM_PROMPT,
    PIVOT_SYSTEM_PROMPT,
    build_proactive_prompt,
    build_responsive_prompt,
    build_autonomous_prompt,
    build_pivot_prompt,
)


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()


def _call(
    client: OpenAI,
    system: str,
    user: str,
    model: str,
    max_tokens: int = 900,
) -> dict:
    """Make a single LLM call and return parsed JSON."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content
    return json.loads(_clean_json(raw))


class ResidentAI:
    """
    Manages a single resident's AI behavior.
    One ResidentAI instance per resident per shift.
    """

    def __init__(
        self,
        resident: Resident,
        model: str = "anthropic/claude-haiku-4-5",
    ):
        self.resident = resident
        self.model = get_model("gameplay", override=model)
        self.client = get_client()
        self._shift_context: dict = {}

    def set_shift_context(self, context: dict):
        """Set the current shift context (time, hospital state, etc.)."""
        self._shift_context = context

    def update_state(self, **kwargs):
        """Update resident state fields directly."""
        for k, v in kwargs.items():
            if hasattr(self.resident.state, k):
                setattr(self.resident.state, k, v)

    # ------------------------------------------------------------------
    # Mode 1: Proactive — resident presents a new case
    # ------------------------------------------------------------------

    def proactive(self, case) -> ResidentAssessment:
        """
        Resident initiates — presents a new case to the attending.
        Called when a new patient arrives and the resident has done
        their initial assessment.
        """
        user_prompt = build_proactive_prompt(
            resident=self.resident,
            case=case,
            shift_context=self._shift_context,
        )

        try:
            data = _call(
                client=self.client,
                system=PROACTIVE_SYSTEM_PROMPT,
                user=user_prompt,
                model=self.model,
            )
            return ResidentAssessment(
                differential=data.get("differential", []),
                recommended_workup=data.get("recommended_workup", []),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", "moderate"),
                flags=data.get("flags", []),
                what_they_say=data.get("what_they_say", ""),
                plan_summary=data.get("plan_summary", ""),
                plan_tests=data.get("plan_tests", []),
                plan_questions=data.get("plan_questions", []),
            )
        except Exception as e:
            # Fallback so the game never hard-crashes on a resident
            import sys
            print(f"[WARN] proactive() failed ({type(e).__name__}: {e})", file=sys.stderr)
            r = self.resident
            return ResidentAssessment(
                differential=[],
                recommended_workup=[],
                reasoning="",
                confidence="moderate",
                flags=[],
                what_they_say=(
                    f"Hey, got a patient in bay — "
                    f"{case.presenting_layer.triage_note} "
                    f"Want me to run with it?"
                ),
                plan_summary="Run standard workup — standing by for your direction.",
                plan_tests=[],
                plan_questions=["Can you tell me what brought you in today?"],
            )

    # ------------------------------------------------------------------
    # Mode 2: Responsive — attending asks a question
    # ------------------------------------------------------------------

    def respond(
        self,
        case,
        question: str,
        interaction_summary: str = "",
    ) -> ResidentAssessment:
        """
        Attending asks the resident something directly.
        question: what the attending said
        interaction_summary: brief text of what's happened so far
        """
        user_prompt = build_responsive_prompt(
            resident=self.resident,
            case=case,
            question=question,
            interaction_summary=interaction_summary,
            shift_context=self._shift_context,
        )

        try:
            data = _call(
                client=self.client,
                system=RESPONSIVE_SYSTEM_PROMPT,
                user=user_prompt,
                model=self.model,
            )
            return ResidentAssessment(
                differential=data.get("differential", []),
                recommended_workup=data.get("recommended_workup", []),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", "moderate"),
                flags=data.get("flags", []),
                what_they_say=data.get("what_they_say", ""),
            )
        except Exception as e:
            return ResidentAssessment(
                differential=[],
                recommended_workup=[],
                reasoning="",
                confidence="moderate",
                flags=[],
                what_they_say="Let me think on that and get back to you.",
            )

    # ------------------------------------------------------------------
    # Mode 3: Pivot interrupt — test result changes the picture
    # ------------------------------------------------------------------

    def pivot_interrupt(
        self,
        case,
        test_name: str,
        test_result: str,
        interaction_summary: str = "",
    ) -> ResidentPivot:
        """
        Called automatically after every test result.
        Returns a pivot if the result materially changes the picture,
        otherwise returns triggered=False (silent — don't show anything).
        """
        user_prompt = build_pivot_prompt(
            resident=self.resident,
            case=case,
            test_name=test_name,
            test_result=test_result,
            interaction_summary=interaction_summary,
            shift_context=self._shift_context,
        )

        try:
            data = _call(
                client=self.client,
                system=PIVOT_SYSTEM_PROMPT,
                user=user_prompt,
                model=self.model,
                max_tokens=300,
            )
            return ResidentPivot(
                triggered=data.get("triggered", False),
                pivot_reason=data.get("pivot_reason", ""),
                what_they_say=data.get("what_they_say", ""),
                options=data.get("options", []),
                recommended=data.get("recommended", 0),
                plan_tests=data.get("plan_tests", []),
            )
        except Exception:
            return ResidentPivot(
                triggered=False,
                pivot_reason="",
                what_they_say="",
                options=[],
                recommended=0,
            )

    # ------------------------------------------------------------------
    # Mode 4: Autonomous — timer expired, resident acts alone
    # ------------------------------------------------------------------

    def act_autonomously(
        self,
        case,
        timer_duration_minutes: int,
        case_state_at_timer: dict,
    ) -> ResidentAutonomousAction:
        """
        Timer expired. Resident acted without the attending.
        Returns what they did, why, and how they report it.
        """
        user_prompt = build_autonomous_prompt(
            resident=self.resident,
            case=case,
            timer_duration_minutes=timer_duration_minutes,
            case_state_at_timer=case_state_at_timer,
            shift_context=self._shift_context,
        )

        try:
            data = _call(
                client=self.client,
                system=AUTONOMOUS_SYSTEM_PROMPT,
                user=user_prompt,
                model=self.model,
                max_tokens=800,
            )

            action = ResidentAutonomousAction(
                action_taken=data.get("action_taken", ""),
                reasoning=data.get("reasoning", ""),
                what_they_tell_attending=data.get("what_they_tell_attending", ""),
                what_they_dont_say=data.get("what_they_dont_say", ""),
            )

            # Update resident state based on outcome
            confidence = data.get("confidence_in_action", "moderate")
            self.resident.state.last_case_outcome = (
                f"Acted autonomously on {case.presenting_layer.chief_complaint} "
                f"({confidence} confidence)"
            )

            return action

        except Exception as e:
            r = self.resident
            pl = case.presenting_layer
            return ResidentAutonomousAction(
                action_taken=f"Continued monitoring {pl.chief_complaint}",
                reasoning="Attending unavailable, maintained current management",
                what_they_tell_attending=(
                    f"Hey — you were pulled away so I kept an eye on them. "
                    f"Held the current plan. Wanted to check with you before "
                    f"moving forward."
                ),
                what_they_dont_say="",
            )

    # ------------------------------------------------------------------
    # Relationship updates
    # ------------------------------------------------------------------

    def attending_overrode(self, context: str):
        """Call when attending overrides resident's call."""
        self.resident.relationship.attending_has_corrected_them += 1
        if context:
            self.resident.relationship.notable_moments.append(
                f"Overridden: {context}"
            )
        # Being corrected affects state differently by personality
        p = self.resident.personality.value
        if p == "overcalibrated":
            self.resident.state.stress_level = "high"
        elif p == "cowboy":
            # Slightly defensive, then recalibrates
            self.resident.state.recent_mistake = context

    def attending_backed(self, context: str):
        """Call when attending trusts resident's call."""
        self.resident.relationship.attending_has_backed_them += 1
        if context:
            self.resident.relationship.notable_moments.append(
                f"Backed: {context}"
            )
        # Being trusted reduces stress
        if self.resident.state.stress_level == "high":
            self.resident.state.stress_level = "moderate"

    def end_shift(self):
        """Update relationship at end of shift."""
        self.resident.relationship.shifts_together += 1
        backed = self.resident.relationship.attending_has_backed_them
        corrected = self.resident.relationship.attending_has_corrected_them

        # Evolve trust level based on track record
        if self.resident.relationship.shifts_together >= 5 and backed > corrected * 2:
            self.resident.relationship.trust_level = "strong"
        elif self.resident.relationship.shifts_together >= 3:
            self.resident.relationship.trust_level = "established"
        elif self.resident.relationship.shifts_together >= 1:
            self.resident.relationship.trust_level = "developing"

        # Reset per-shift state
        self.resident.state.hours_into_shift = 0.0
        self.resident.state.active_cases = 0
        self.resident.state.stress_level = "low"
        self.resident.state.had_break = False
        self.resident.state.recent_mistake = None
        self.resident.state.consecutive_difficult_cases = 0
