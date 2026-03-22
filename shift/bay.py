"""
Bay — one patient room.

A Bay owns:
- The case (ground truth)
- The patient session (stateful conversation)
- The assigned resident
- The timer (turn count until autonomous action)
- The bay status (active, resolved, autonomous-fired)

The timer ticks every time the attending takes ANY action
in ANY bay. When it hits the threshold the resident acts.

A WARNING fires at 75% of threshold (rounded up) to give the
attending a chance to intervene before autonomous action.

Timer threshold varies by acuity:
  Acuity 1: 5 actions  (immediate — don't leave this one alone)
  Acuity 2: 7 actions
  Acuity 3: 11 actions
  Acuity 4: 16 actions
  Acuity 5: 28 actions (non-urgent — resident can hold this a while)
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum

from cases.schema import GeneratedCase
from cases.interaction import PatientSession
from residents.schema import Resident
from residents.resident import ResidentAI


class BayStatus(str, Enum):
    WAITING    = "waiting"       # Patient in bay, not yet seen
    ACTIVE     = "active"        # Attending currently in this bay
    SUPERVISED = "supervised"    # Attending stepped out, resident holding
    AUTONOMOUS = "autonomous"    # Timer fired, resident acted
    RESOLVED   = "resolved"      # Case closed — discharged or admitted


ACUITY_TIMER_THRESHOLDS = {
    1: 5,
    2: 9,
    3: 11,
    4: 16,
    5: 28,
}


@dataclass
class BayEvent:
    """One recorded event in the bay's history."""
    turn: int
    actor: Literal["attending", "resident", "patient", "system"]
    event_type: str    # "attend", "exam", "test", "resident_proactive",
                       # "resident_response", "autonomous_action", "resolve"
    content: str
    internal: str = ""  # Game engine only — reasoning, not shown to player


@dataclass
class Bay:
    """A single patient bay."""
    bay_id: str
    case: GeneratedCase
    resident: Resident

    # Initialized after construction
    patient_session: Optional[PatientSession] = None
    resident_ai: Optional[ResidentAI] = None

    status: BayStatus = BayStatus.WAITING
    timer_ticks: int = 0
    timer_threshold: int = 8
    warning_fired: bool = False
    autonomous_fired: bool = False

    events: list = field(default_factory=list)

    # What the resident last said proactively (shown when attending arrives)
    resident_opening: str = ""
    resident_opening_data: Optional[object] = None

    # Disposition when resolved
    disposition: str = ""
    resolution_note: str = ""

    # Trap case — resident's blind spots align with this case's miss reason
    is_trap: bool = False
    trap_detail: str = ""  # Why this is a trap for THIS resident

    # Consequence severity from autonomous action (none/minor/moderate/major/critical)
    autonomous_consequence_severity: str = "none"

    # Approval system state
    _pending_plan: Optional[object] = None   # ResidentAssessment with plan fields
    _plan_prompt_turns: int = 0              # Patient turns since plan was presented
    _plan_on_hold: bool = False              # True when player chose "hold"

    # Test result delay queue: list of (due_turn, test_name, result_text)
    pending_results: list = field(default_factory=list)

    def __post_init__(self):
        acuity = self.case.presenting_layer.acuity.value
        self.timer_threshold = ACUITY_TIMER_THRESHOLDS.get(acuity, 8)

    def setup(self, model: str = "anthropic/claude-haiku-4-5"):
        """Initialize the patient session and resident AI."""
        self.patient_session = PatientSession(self.case, model=model)
        self.resident_ai = ResidentAI(self.resident, model=model)

    @property
    def warning_threshold(self) -> int:
        """Warning fires at 75% of timer_threshold, rounded up."""
        return math.ceil(self.timer_threshold * 0.75)

    def tick(self) -> str:
        """
        Advance timer by one tick.
        Returns:
          'fire'    — autonomous action threshold just crossed
          'warning' — warning threshold just crossed (75% of timer)
          'ok'      — nothing special
        Timer pauses when attending is present and plan is on hold.
        """
        if self.status == BayStatus.SUPERVISED:
            # Don't tick if attending is actively deciding (hold)
            if self._plan_on_hold:
                return 'ok'
            self.timer_ticks += 1
            if self.timer_ticks >= self.timer_threshold and not self.autonomous_fired:
                return 'fire'
            if self.timer_ticks >= self.warning_threshold and not self.warning_fired:
                self.warning_fired = True
                return 'warning'
        return 'ok'

    def record(self, actor, event_type, content, internal=""):
        self.events.append(BayEvent(
            turn=self.timer_ticks,
            actor=actor,
            event_type=event_type,
            content=content,
            internal=internal,
        ))

    @property
    def acuity(self) -> int:
        return self.case.presenting_layer.acuity.value

    @property
    def patient_name(self) -> str:
        pp = self.case.patient_profile
        return f"{pp.first_name} {pp.last_name}"

    @property
    def triage_summary(self) -> str:
        return self.case.presenting_layer.triage_note

    @property
    def timer_pressure(self) -> str:
        """Human-readable timer status."""
        if self.status != BayStatus.SUPERVISED:
            return ""
        remaining = self.timer_threshold - self.timer_ticks
        if remaining <= 1:
            return "!! ACTING SOON"
        elif remaining <= 3:
            return f"! {remaining} actions left"
        else:
            return f"{remaining} actions"
