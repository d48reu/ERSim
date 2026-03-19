"""
Resident data structures.

A resident is a persistent character with:
- A fixed competency profile (strengths and specific blind spots)
- A dynamic state (hours in, recent outcomes, stress level)
- A personality archetype (shapes HOW they communicate)
- A relationship state with the attending (builds over shifts)

Competency and personality are fixed at creation.
State and relationship update every shift.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
from enum import Enum


class ResidentYear(int, Enum):
    PGY1 = 1   # Intern — methodical, slow, escalates everything
    PGY2 = 2   # Second year — gaining confidence, occasional overreach
    PGY3 = 3   # Senior — solid, can run cases independently
    PGY4 = 4   # Fellow — subspecialty depth, occasional tunnel vision


class PersonalityArchetype(str, Enum):
    # Knows what they don't know. Escalates constantly. Safe but slow.
    # Drives you crazy until the day you're glad they called.
    OVERCALIBRATED = "overcalibrated"

    # Acts fast, usually right, occasionally catastrophically wrong.
    # Can't be trusted unsupervised on complex cases.
    COWBOY = "cowboy"

    # Textbook decisions, struggles when patient doesn't present textbook.
    # Orders everything, misses the human read.
    ACADEMIC = "academic"

    # Was great six months ago. Something happened.
    # Competence is declining in ways that are painful to watch.
    BURNING_OUT = "burning_out"

    # Quietly excellent. Doesn't showboat. Easy to underestimate.
    # Has a ceiling you haven't found yet.
    STEADY = "steady"


@dataclass
class ResidentCompetency:
    """
    What this resident is actually good at and where they fail.
    Not stats — specific clinical descriptions.
    Shapes what the LLM generates for their assessments.
    """
    strengths: list[str]      # e.g. ["chest pain workups", "trauma assessment"]
    blind_spots: list[str]    # e.g. ["elderly AMS presentations", "social history"]
    overconfident_in: list[str]  # Areas where they think they're better than they are
    underconfident_in: list[str] # Areas where they're better than they think


@dataclass
class ResidentState:
    """
    Dynamic state — resets partially each shift, accumulates over campaign.
    """
    hours_into_shift: float = 0.0
    active_cases: int = 0
    last_case_outcome: str = ""          # Brief description of last resolved case
    last_case_went_well: Optional[bool] = None
    consecutive_difficult_cases: int = 0
    recent_mistake: Optional[str] = None  # If they made a mistake recently
    stress_level: Literal["low", "moderate", "high", "critical"] = "low"
    had_break: bool = False


@dataclass
class ResidentRelationship:
    """
    How this resident relates to the attending. Builds over time.
    """
    shifts_together: int = 0
    trust_level: Literal["new", "developing", "established", "strong"] = "new"
    attending_has_corrected_them: int = 0     # Times attending overrode their call
    attending_has_backed_them: int = 0        # Times attending trusted their call
    notable_moments: list[str] = field(default_factory=list)  # Specific incidents
    # What the resident thinks of the attending (shapes how they communicate)
    resident_perception: str = "uncertain — haven't worked together enough to know"


@dataclass
class Resident:
    """
    A complete resident character.
    """
    id: str
    name: str
    year: ResidentYear
    personality: PersonalityArchetype
    competency: ResidentCompetency
    state: ResidentState = field(default_factory=ResidentState)
    relationship: ResidentRelationship = field(default_factory=ResidentRelationship)

    # Brief backstory — feeds into communication style and motivation
    backstory: str = ""


# ---------------------------------------------------------------------------
# Resident action output structures
# ---------------------------------------------------------------------------

@dataclass
class ResidentPivot:
    """
    What the resident says when a test result materially changes the picture.
    Fired automatically after test results — this is the proactive interrupt.
    """
    triggered: bool               # Did this result actually change anything?
    pivot_reason: str             # Internal: why this is a pivot (not said aloud)
    what_they_say: str            # Natural hallway speech — in their voice
    options: list[str]            # 2-3 display-only choice descriptions for attending
    recommended: int              # Index of their preferred option (0-based)
    plan_tests: list[str] = field(default_factory=list)  # Actual test names to execute on approve

@dataclass
class ResidentAssessment:
    """
    What a resident says when presenting a case or answering a question.
    """
    differential: list[str]          # Their top 1-3 diagnoses, in order
    recommended_workup: list[str]    # Tests/exams they want to run
    reasoning: str                   # Why they think what they think
    confidence: Literal["low", "moderate", "high"]
    flags: list[str]                 # Things they're worried about
    what_they_say: str               # Natural language — in their voice

    # Approval system fields
    plan_summary: str = ""           # One sentence: "I want to run X, Y, Z and ask about A"
    plan_tests: list[str] = field(default_factory=list)    # Actual test names to execute
    plan_questions: list[str] = field(default_factory=list) # Questions for the patient


@dataclass
class ResidentAutonomousAction:
    """
    What a resident does when the timer expires and they act alone.
    """
    action_taken: str                # Specific clinical action
    reasoning: str                   # Internal reasoning (not said aloud)
    what_they_tell_attending: str    # How they report it — in their voice
    what_they_dont_say: str          # What they're quietly not flagging, and why
    was_correct: Optional[bool] = None  # Evaluated after the fact
    consequence: str = ""            # What happens as a result


# ---------------------------------------------------------------------------
# Built-in residents
# ---------------------------------------------------------------------------

def make_default_roster() -> list[Resident]:
    """
    Three starting residents with distinct personalities and competency profiles.
    The attending gets to know all three over the campaign.
    """
    return [
        Resident(
            id="chen_maya",
            name="Maya Chen",
            year=ResidentYear.PGY2,
            personality=PersonalityArchetype.OVERCALIBRATED,
            competency=ResidentCompetency(
                strengths=[
                    "recognizes when she's out of her depth and escalates",
                    "thorough history-taking",
                    "pediatric presentations",
                ],
                blind_spots=[
                    "tends to over-order when uncertain, creating noise",
                    "slow to commit to a disposition",
                ],
                overconfident_in=[],
                underconfident_in=[
                    "trauma assessment — she's actually quite good but doesn't trust it",
                ],
            ),
            backstory=(
                "Second year, came from a small program in the midwest. "
                "Worked as an EMT for two years before medical school. "
                "Has a habit of calling attendings for things she could handle "
                "herself. Gets frustrated when told to trust her instincts."
            ),
        ),

        Resident(
            id="okafor_dre",
            name="Andre Okafor",
            year=ResidentYear.PGY3,
            personality=PersonalityArchetype.COWBOY,
            competency=ResidentCompetency(
                strengths=[
                    "fast pattern recognition on high-acuity cases",
                    "procedures — good hands, calm under pressure",
                    "chest pain and cardiac presentations",
                ],
                blind_spots=[
                    "dismisses social history as 'not relevant'",
                    "underestimates elderly patients' acuity",
                    "moves too fast on complex cases",
                ],
                overconfident_in=[
                    "tox cases — reads them fast but misses atypical presentations",
                ],
                underconfident_in=[],
            ),
            backstory=(
                "Third year, Lagos-trained, transferred after two years abroad. "
                "Technically excellent. Has a reputation for being right "
                "90% of the time and terrifying the other 10%. "
                "Doesn't ask for help easily. "
                "Had a bad outcome six months ago he hasn't talked about."
            ),
        ),

        Resident(
            id="patel_priya",
            name="Priya Patel",
            year=ResidentYear.PGY1,
            personality=PersonalityArchetype.ACADEMIC,
            competency=ResidentCompetency(
                strengths=[
                    "rare presentations and atypical diagnoses",
                    "meticulous documentation",
                    "catches subtle lab abnormalities",
                ],
                blind_spots=[
                    "misses the human read — takes history like a checklist",
                    "freezes when patient doesn't fit the textbook",
                    "over-relies on imaging",
                ],
                overconfident_in=[
                    "diagnosis by exclusion — orders everything to rule out",
                ],
                underconfident_in=[
                    "clinical gestalt — her gut is often right but she ignores it",
                ],
            ),
            backstory=(
                "First year, top of her class at Penn. "
                "Every patient gets a complete review of systems whether they "
                "need it or not. Brilliant with the unusual case. "
                "Struggles when the answer is right in front of her "
                "because the textbook says something different."
            ),
        ),
    ]
