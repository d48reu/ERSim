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
    consequence_severity: Literal[
        "none", "minor", "moderate", "major", "critical"
    ] = "none"
    # none: action was correct or neutral
    # minor: suboptimal but no harm (e.g. over-ordered tests)
    # moderate: delayed diagnosis, patient discomfort, wasted resources
    # major: missed diagnosis, wrong treatment, patient at risk
    # critical: immediate patient danger, code blue territory


# ---------------------------------------------------------------------------
# Built-in residents
# ---------------------------------------------------------------------------

def make_default_roster() -> list[Resident]:
    """
    Six residents with distinct personalities and competency profiles.
    Each shift picks 3 via select_shift_roster() for variety.
    """
    return [
        # --- ORIGINAL THREE ---

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

        # --- NEW THREE ---

        Resident(
            id="rivers_jordan",
            name="Jordan Rivers",
            year=ResidentYear.PGY2,
            personality=PersonalityArchetype.BURNING_OUT,
            competency=ResidentCompetency(
                strengths=[
                    "procedures — still has excellent hands",
                    "genuinely interesting cases re-engage him",
                    "efficient with straightforward presentations",
                ],
                blind_spots=[
                    "misses emotional cues — patient is terrified, Jordan doesn't notice",
                    "substance abuse presentations — doesn't dig",
                    "follow-up planning — dispositions without aftercare",
                ],
                overconfident_in=[
                    "routine cases — autopilots through them, misses the atypical one",
                ],
                underconfident_in=[],
            ),
            backstory=(
                "Second year who was a star intern. Something broke about six "
                "months ago — won't say what. Still technically competent but "
                "running on autopilot. The nurses have noticed. His co-residents "
                "cover for him. On a good day the old Jordan shows up and you "
                "see what the fuss was about."
            ),
        ),

        Resident(
            id="adeyemi_sarah",
            name="Sarah Adeyemi",
            year=ResidentYear.PGY3,
            personality=PersonalityArchetype.STEADY,
            competency=ResidentCompetency(
                strengths=[
                    "clinical gestalt — knows when something is off before labs confirm",
                    "builds patient rapport quickly and naturally",
                    "consistent, reliable case management across acuity levels",
                ],
                blind_spots=[
                    "won't push back if attending disagrees, even when she's right",
                    "understates urgency — says 'I want to make sure' when she means 'this is bad'",
                ],
                overconfident_in=[],
                underconfident_in=[
                    "her own judgment — she's usually right but defers too easily",
                ],
            ),
            backstory=(
                "Third year. Quietly the best resident in the program but nobody "
                "talks about it because she doesn't present dramatically. Grew up "
                "in Houston, parents are both nurses. Medicine isn't glamorous to "
                "her — it's a job she happens to be very good at. Trust builds "
                "through accuracy, not charisma."
            ),
        ),

        Resident(
            id="kowalski_danny",
            name="Danny Kowalski",
            year=ResidentYear.PGY1,
            personality=PersonalityArchetype.COWBOY,
            competency=ResidentCompetency(
                strengths=[
                    "genuinely good hands — calm in chaos",
                    "will do the thing nobody else wants to do",
                    "fast triage reads on trauma and acute presentations",
                ],
                blind_spots=[
                    "wide knowledge gaps he doesn't know about yet",
                    "pediatric presentations — hasn't seen enough",
                    "commits to a plan and executes before asking",
                    "medication dosing on complex patients",
                ],
                overconfident_in=[
                    "his own clinical read — PGY1 with PGY3 confidence",
                ],
                underconfident_in=[],
            ),
            backstory=(
                "First year who acts like a third year. Former paramedic, "
                "four years in the field before med school. Confident, fast, "
                "sometimes right. Andre's speed with none of Andre's experience. "
                "Gets quieter when he's wrong, which is how you know. "
                "More dangerous than Priya because he'll actually do it."
            ),
        ),
    ]


def select_shift_roster(
    roster: list[Resident] | None = None,
    num_residents: int = 3,
) -> list[Resident]:
    """
    Pick num_residents from the full roster with PGY balance constraints:
      - At least 1 junior (PGY1-2)
      - At least 1 senior (PGY3+)
    Shuffled so bay assignment is random each run.
    """
    import random as _rnd

    if roster is None:
        roster = make_default_roster()

    if len(roster) <= num_residents:
        picked = list(roster)
        _rnd.shuffle(picked)
        return picked

    juniors = [r for r in roster if r.year.value <= 2]
    seniors = [r for r in roster if r.year.value >= 3]

    picked: list[Resident] = []

    # Guarantee at least one junior
    if juniors:
        j = _rnd.choice(juniors)
        picked.append(j)

    # Guarantee at least one senior
    available_seniors = [s for s in seniors if s not in picked]
    if available_seniors:
        s = _rnd.choice(available_seniors)
        picked.append(s)

    # Fill remaining slots from whoever's left
    remaining = [r for r in roster if r not in picked]
    need = num_residents - len(picked)
    if need > 0 and remaining:
        picked.extend(_rnd.sample(remaining, min(need, len(remaining))))

    _rnd.shuffle(picked)
    return picked
