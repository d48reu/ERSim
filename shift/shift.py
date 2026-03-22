"""
Shift — the top-level game session.

Owns all active bays, routes attending attention,
manages the global turn counter, fires autonomous
resident actions when timers cross threshold.

Implementation is split across `shift/*_mixin.py` modules; this file composes them.

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

from __future__ import annotations

from typing import Optional

from llm import get_model

from cases.schema import GeneratedCase
from residents.schema import Resident, select_shift_roster

from .bay import Bay
from .constants import TEST_DELAYS
from .debrief_mixin import ShiftDebriefMixin
from .navigation_mixin import ShiftNavigationMixin
from .patient_actions_mixin import ShiftPatientActionsMixin
from .plans_mixin import ShiftPlansMixin
from .rendering_mixin import ShiftRenderingMixin
from .resolve_mixin import ShiftResolveMixin
from .setup_mixin import ShiftSetupMixin
from .shift_types import ShiftStatus
from .tests_mixin import ShiftTestsMixin
from .timers_mixin import ShiftTimersMixin
from .traps import detect_and_assign_traps


class Shift(
    ShiftSetupMixin,
    ShiftRenderingMixin,
    ShiftNavigationMixin,
    ShiftPatientActionsMixin,
    ShiftTestsMixin,
    ShiftPlansMixin,
    ShiftTimersMixin,
    ShiftResolveMixin,
    ShiftDebriefMixin,
):
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
        model: str | None = None,
    ):
        self.model = get_model("gameplay", override=model)
        self.residents = residents or select_shift_roster()
        self.global_turn: int = 0
        self.active_bay_id: Optional[str] = None
        self.bays: dict[str, Bay] = {}
        self._autonomous_queue: list[str] = []
        self._warning_queue: list[str] = []
        self._last_debrief_meta: dict = {}

        for i, case in enumerate(cases):
            bay_id = f"Bay {i+1}"
            resident = self.residents[i % len(self.residents)]
            self.bays[bay_id] = Bay(
                bay_id=bay_id,
                case=case,
                resident=resident,
            )

        detect_and_assign_traps(self.bays)

    def _require_active_bay(self) -> Optional[Bay]:
        if not self.active_bay_id:
            return None
        return self.bays.get(self.active_bay_id)


__all__ = ["Shift", "ShiftStatus", "TEST_DELAYS"]
