"""
Patient interaction engine.

Takes a GeneratedCase (the ground truth) and manages a stateful
conversation between the attending and the patient.

The AI plays the patient. It draws exclusively from the ground truth
document. It never invents facts. It reveals information according
to the reveal sequence — the right information at the right trigger
in the right voice.

Usage:
    session = PatientSession(case, model="anthropic/claude-haiku-4-5")
    response = session.interact("Tell me what's going on today.")
    response = session.interact("How long have you had this pain?")
    response = session.order_test("troponin")
    response = session.bring_family()
    summary = session.get_reveal_summary()
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from openai import OpenAI

from .schema import GeneratedCase, RevealTrigger


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

PATIENT_INTERACTION_SYSTEM_PROMPT = """
You are playing a patient in a hospital emergency room.
You are not a medical AI. You are a person.

You have a ground truth document that contains everything true about
your situation. Your job is to respond to the attending physician
as this specific person would — not as a helpful information source,
not as a cooperative patient, not as a dramatic character.
As this person, in this room, right now.

CORE RULES

Rule 1: You never invent facts.
Every piece of medical or personal information you share must come
from the ground truth document. If asked something not in your
document, respond as this person would — deflect, say you don't
know, get uncomfortable, change the subject. Never make up details
to fill gaps.

Rule 2: You follow the reveal sequence.
Information in the reveal sequence is gated. You do not volunteer
it before its trigger is met. You do not jump ahead because the
doctor asked a clever question. The reveal sequence exists because
people protect information until the right moment. Respect that.

Rule 3: You have already revealed certain things.
The reveal log shows everything you have already said in this
encounter. You never contradict it. You never repeat it verbatim
as if you haven't said it. You remember this conversation.

Rule 4: Your communication style is behavioral, not performed.
You were given a communication style description. Follow it precisely.
If it says you answer questions with minimum words and look at the
floor, do that. If it says you over-explain because you're nervous,
do that. Do not perform emotion. Enact behavior.

Rule 5: You are protecting something.
You know what you are protecting and what you fear. These shape
every response. When the conversation approaches what you are
protecting, your behavior changes in a way consistent with your
communication style — not melodramatically, not obviously, but
in the way a real person shifts when a conversation gets close
to something they don't want to talk about.

Rule 6: You are not trying to be difficult.
You are not withholding information to be obstinate. You are
withholding it because something matters more to you right now
than full disclosure. This is different. Obstinate patients are
annoying. Protected patients are human.

Rule 7: Physical state affects your responses.
Your vitals and physical condition are real. If you are in pain,
it is present in how you speak. If you are short of breath, your
sentences may be shorter. If you are scared, it is underneath
the words even when you are trying to hide it. Not performed —
texture.

Rule 8: Time and trust affect your responses.
If the attending has spent time with you and asked careful questions,
you are slightly more open than you were at the start. Not because
of a trust meter — because that is how people work. Early in the
encounter you are more guarded. As the conversation develops and
someone demonstrates they are actually listening, the guard can
drop a little. This is gradual and never complete.

WHAT GOOD RESPONSES LOOK LIKE

Short, not long. Real patients do not give complete medical
histories when asked how they are doing. They answer the question
asked, sometimes incompletely.

Specific, not generic. "My chest feels heavy, like something
sitting on it" not "I have chest pain." Use the patient's actual
language from the ground truth.

Interrupted by life. Real patients bring in context that doesn't
seem relevant. A worry about the parking meter. A reference to
their daughter. Something they saw on the way in. Not constantly —
occasionally, naturally.

Responses to clinical questions are lay language. The patient
does not know what "onset" means as a medical term. They know
when it started. They do not know "radiation" — they know if it
goes anywhere else.

WHAT BAD RESPONSES LOOK LIKE

Volunteering protected information when the trigger hasn't been met.
Contradicting the reveal log.
Using medical terminology the patient wouldn't know.
Long explanations when the character is guarded.
Performing emotion rather than enacting behavior.
Starting every response with "I" or the patient's name.
Sounding like a helpful AI assistant describing a patient's situation.

FORMAT

Respond as the patient speaking. No narration, no stage directions,
no quotes around the speech. Just the words and behavior.

If relevant physical behavior would change the meaning —
a pause, looking away, reaching for something — you may add
a single brief action in italics within the response.
Use this sparingly. One per response at most.

Example:
  *looks at hands*
  It started a few days ago I think. Maybe longer.

Do not use italics for emotion labels. "looks nervous" is
not an action. "looks at hands" is.
"""


# ---------------------------------------------------------------------------
# Trigger evaluation prompt
# ---------------------------------------------------------------------------

TRIGGER_EVAL_PROMPT = """
You are evaluating whether a reveal trigger condition has been met
in a patient interaction.

You will be given:
- The trigger type and specific condition required
- The attending's most recent message
- The conversation history
- The current interaction state

Return a JSON object with one field:
{
  "triggered": true or false
}

For DIRECT_QUESTION: fire if the attending asked a question that
directly addresses the trigger condition topic — even if phrased
conversationally. A clear question about the right subject is enough.
Do NOT require word-for-word matching; semantic match is sufficient.

For TRUST_ESTABLISHED: requires genuine rapport over multiple exchanges,
not just one friendly question.

For VOLUNTEERED / PROLONGED_STAY: evaluated by turn count, not here.
"""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class InteractionTurn:
    role: str           # "attending" or "patient"
    content: str
    triggered_nodes: list[int] = field(default_factory=list)


@dataclass
class RevealState:
    node_index: int
    triggered: bool = False
    turn_triggered: Optional[int] = None


# ---------------------------------------------------------------------------
# Patient session
# ---------------------------------------------------------------------------

class PatientSession:
    """
    Manages a stateful patient interaction for a single case.

    The session tracks:
    - Full conversation history
    - Which reveal nodes have been triggered
    - What tests have been ordered
    - Whether family is present
    - Turn count (proxy for time and trust)
    """

    def __init__(
        self,
        case: GeneratedCase,
        model: str = "anthropic/claude-haiku-4-5",
    ):
        self.case = case
        self.model = model
        self.client = _get_client()

        self.history: list[InteractionTurn] = []
        self.reveal_states = [
            RevealState(node_index=i)
            for i in range(len(case.reveal_sequence))
        ]
        self.ordered_tests: list[str] = []
        self.family_present: bool = False
        self.turn_count: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def interact(self, attending_message: str) -> str:
        """
        Attending says something / asks a question.
        Returns the patient's response.
        """
        self.turn_count += 1

        # Check direct_question and trust_established triggers
        self._check_conversational_triggers(attending_message)

        # Record attending turn
        self.history.append(InteractionTurn(
            role="attending",
            content=attending_message,
        ))

        response = self._get_patient_response()

        self.history.append(InteractionTurn(
            role="patient",
            content=response,
        ))

        return response

    def order_test(self, test_name: str) -> str:
        """
        Attending orders a test. Returns a brief status message
        (not the patient talking — this is the game engine).
        Triggers any test_result reveal nodes for this test.
        """
        self.ordered_tests.append(test_name)
        triggered = self._check_test_triggers(test_name)

        # Return what the test shows, drawn from medical truth
        result = self._get_test_result(test_name)

        status = f"[Test ordered: {test_name}]\n{result}"
        if triggered:
            status += f"\n[Reveal unlocked: patient will now disclose related information]"

        self.history.append(InteractionTurn(
            role="system",
            content=f"Test ordered: {test_name}. Result: {result}",
        ))

        return status

    def examine(self, maneuver: str) -> str:
        """
        Attending performs a physical exam maneuver.
        Returns two things: what the attending finds (clinical),
        and how the patient reacts (character).
        Triggers any physical_exam reveal nodes matching the maneuver.
        """
        triggered = self._check_exam_triggers(maneuver)

        # Get the clinical finding
        finding = self._get_exam_finding(maneuver)

        # Get the patient's reaction to being examined
        reaction = self._get_exam_reaction(maneuver, finding)

        result = f"[Exam: {maneuver}]\n"
        result += f"Finding: {finding}\n"
        result += f"Patient: {reaction}"
        if triggered:
            result += "\n[Reveal unlocked: examination surfaced new information]"

        self.history.append(InteractionTurn(
            role="system",
            content=f"Physical exam: {maneuver}. Finding: {finding}. "
                    f"Patient reaction: {reaction}",
        ))

        return result

    def bring_family(self) -> str:
        """
        Attending brings family member into the room.
        Triggers any family_present reveal nodes.
        """
        self.family_present = True
        triggered = self._check_family_triggers()

        key_person = self.case.patient_profile.key_person
        relationship = self.case.patient_profile.key_person_relationship

        status = f"[{key_person} enters the room — {relationship}]"
        if triggered:
            status += "\n[Reveal unlocked: patient behavior will shift with family present]"

        self.history.append(InteractionTurn(
            role="system",
            content=f"Family present: {key_person}",
        ))

        return status

    def get_reveal_summary(self) -> dict:
        """
        Returns what has been revealed so far and what remains locked.
        Useful for the attending's chart view.
        """
        triggered = []
        locked = []

        for state in self.reveal_states:
            node = self.case.reveal_sequence[state.node_index]
            if state.triggered:
                triggered.append({
                    "turn": state.turn_triggered,
                    "information": node.information,
                    "trigger": node.trigger.value,
                })
            else:
                locked.append({
                    "trigger_needed": node.trigger.value,
                    "trigger_detail": node.trigger_detail,
                })

        return {
            "case_id": self.case.case_id,
            "turns": self.turn_count,
            "revealed": triggered,
            "locked": locked,
            "tests_ordered": self.ordered_tests,
            "family_present": self.family_present,
        }

    # ------------------------------------------------------------------
    # Internal: trigger checking
    # ------------------------------------------------------------------

    def _check_conversational_triggers(self, attending_message: str):
        """Check direct_question and trust_established triggers."""
        for state in self.reveal_states:
            if state.triggered:
                continue
            node = self.case.reveal_sequence[state.node_index]
            if node.trigger in (
                RevealTrigger.DIRECT_QUESTION,
                RevealTrigger.TRUST_ESTABLISHED,
                RevealTrigger.VOLUNTEERED,
                RevealTrigger.PROLONGED_STAY,
            ):
                if self._evaluate_trigger(node, attending_message):
                    state.triggered = True
                    state.turn_triggered = self.turn_count

    def _check_test_triggers(self, test_name: str) -> bool:
        """Check test_result and physical_exam triggers."""
        any_triggered = False
        for state in self.reveal_states:
            if state.triggered:
                continue
            node = self.case.reveal_sequence[state.node_index]
            if node.trigger in (
                RevealTrigger.TEST_RESULT,
                RevealTrigger.PHYSICAL_EXAM,
            ):
                # Simple keyword match — if the test ordered matches
                # the trigger detail, fire it
                if any(
                    word in node.trigger_detail.lower()
                    for word in test_name.lower().split()
                ):
                    state.triggered = True
                    state.turn_triggered = self.turn_count
                    any_triggered = True
        return any_triggered

    def _check_exam_triggers(self, maneuver: str) -> bool:
        """Check physical_exam triggers matching the maneuver."""
        any_triggered = False
        for state in self.reveal_states:
            if state.triggered:
                continue
            node = self.case.reveal_sequence[state.node_index]
            if node.trigger == RevealTrigger.PHYSICAL_EXAM:
                if self._exam_words_match(maneuver, node.trigger_detail):
                    state.triggered = True
                    state.turn_triggered = self.turn_count
                    any_triggered = True
        return any_triggered

    # Body-region synonym clusters — if maneuver or trigger_detail
    # contains ANY word in a cluster, it matches ANY other word in
    # that same cluster.  Add new clusters as needed.
    _EXAM_SYNONYMS: list = [
        {"chest", "lung", "lungs", "pulmonary", "respiratory", "auscultation",
         "breath", "breathing", "crackles", "wheeze", "wheezes", "rales",
         "rhonchi", "thorax", "thoracic", "percussion", "egophony"},
        {"abdomen", "abdominal", "belly", "palpation", "palpate", "ruq",
         "luq", "rlq", "llq", "epigastric", "peritoneal", "rebound",
         "guarding", "tenderness", "bowel"},
        {"heart", "cardiac", "cardiovascular", "murmur", "gallop", "rhythm",
         "precordium", "precordial", "s1", "s2", "s3", "s4"},
        {"neuro", "neurological", "neurologic", "mental", "gcs", "focal",
         "reflexes", "cranial", "pupils", "orientation", "cognition"},
        {"skin", "rash", "integument", "dermatology", "jaundice",
         "cyanosis", "pallor", "diaphoresis"},
        {"extremity", "extremities", "leg", "legs", "arm", "arms",
         "edema", "swelling", "dvt", "calf", "homan"},
        {"neck", "throat", "cervical", "jvp", "jvd", "lymph", "nodes",
         "thyroid", "trachea", "meningismus"},
        {"pelvis", "pelvic", "rectal", "genitourinary", "gu", "flank",
         "costovertebral", "cva"},
    ]

    @classmethod
    def _synonym_cluster(cls, word: str) -> set:
        """Return the full synonym cluster for a word, or just {word}."""
        for cluster in cls._EXAM_SYNONYMS:
            if word in cluster:
                return cluster
        return {word}

    @classmethod
    def _exam_words_match(cls, maneuver: str, trigger_detail: str) -> bool:
        """
        Match exam maneuver against trigger detail text.

        Four strategies in order:
        0. Synonym expansion — chest matches auscultation, lung, etc.
        1. Exact word overlap ("murphy" in "murphy's sign")
        2. Prefix overlap of 5+ chars ("abdomen" vs "abdominal",
           "palpat" vs "palpation", "cardiac" vs "cardiology")
        3. Substring — maneuver word appears anywhere in trigger detail
           or vice versa ("RUQ" in "RUQ tenderness")
        """
        import re
        # Normalize: lowercase, strip punctuation
        def words(s):
            return set(re.sub(r"[^\w\s]", "", s.lower()).split())

        mwords = words(maneuver)
        twords = words(trigger_detail)

        # 0. Synonym expansion
        expanded_m = set()
        for w in mwords:
            expanded_m |= cls._synonym_cluster(w)
        expanded_t = set()
        for w in twords:
            expanded_t |= cls._synonym_cluster(w)
        if expanded_m & expanded_t:
            return True

        # 1. Exact overlap
        if mwords & twords:
            return True

        # 2. Prefix overlap (5+ chars handles most clinical stems)
        PREFIX = 5
        for mw in mwords:
            for tw in twords:
                n = min(len(mw), len(tw), PREFIX)
                if n >= 4 and mw[:n] == tw[:n]:
                    return True

        # 3. Substring — e.g. "RUQ" inside "RUQ tenderness"
        trigger_lower = trigger_detail.lower()
        maneuver_lower = maneuver.lower()
        for mw in mwords:
            if len(mw) >= 3 and mw in trigger_lower:
                return True
        for tw in twords:
            if len(tw) >= 3 and tw in maneuver_lower:
                return True

        return False

    def _check_family_triggers(self) -> bool:
        """Check family_present triggers."""
        any_triggered = False
        for state in self.reveal_states:
            if state.triggered:
                continue
            node = self.case.reveal_sequence[state.node_index]
            if node.trigger == RevealTrigger.FAMILY_PRESENT:
                state.triggered = True
                state.turn_triggered = self.turn_count
                any_triggered = True
        return any_triggered

    def _evaluate_trigger(self, node, attending_message: str) -> bool:
        """
        Use the LLM to evaluate whether a conversational trigger
        condition has been met. Conservative — only fires when clear.
        """
        # VOLUNTEERED: check if enough turns have passed
        if node.trigger == RevealTrigger.VOLUNTEERED:
            return self.turn_count >= 3

        # PROLONGED_STAY: check turn count as proxy for time
        if node.trigger == RevealTrigger.PROLONGED_STAY:
            return self.turn_count >= 8

        # TRUST_ESTABLISHED: requires genuine engagement — min 2 turns
        if node.trigger == RevealTrigger.TRUST_ESTABLISHED:
            if self.turn_count < 2:
                return False

        # For DIRECT_QUESTION and TRUST_ESTABLISHED (after turn check):
        # use LLM to evaluate
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=50,
                messages=[
                    {"role": "system", "content": TRIGGER_EVAL_PROMPT},
                    {"role": "user", "content": f"""
Trigger type: {node.trigger.value}
Trigger condition: {node.trigger_detail}

Attending's message: {attending_message}

Recent conversation (last 4 turns):
{self._format_recent_history(4)}

Turn count: {self.turn_count}

Has the trigger condition been met? Return JSON only: {{"triggered": true}} or {{"triggered": false}}
"""}
                ],
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            import json
            result = json.loads(raw)
            return result.get("triggered", False)
        except Exception as e:
            import sys
            print(f"[WARN] trigger eval failed ({type(e).__name__}: {e})", file=sys.stderr)
            # Fallback for direct_question: keyword overlap between
            # attending message and trigger_detail
            if node.trigger == RevealTrigger.DIRECT_QUESTION:
                import re as _re
                def _words(s):
                    return set(_re.sub(r"[^\w\s]", "", s.lower()).split())
                overlap = _words(attending_message) & _words(node.trigger_detail)
                # exclude stopwords
                overlap -= {"the","a","an","is","are","was","were","has","have",
                            "do","did","how","what","when","where","why","who",
                            "long","been","you","your","i","it","in","of","to",
                            "and","or","for","that","this","with","about"}
                return bool(overlap)
            return False

    # ------------------------------------------------------------------
    # Internal: response generation
    # ------------------------------------------------------------------

    def _build_patient_context(self) -> str:
        """Build the full patient context injected into every turn."""
        pp = self.case.patient_profile
        pl = self.case.presenting_layer

        # Collect triggered reveal nodes
        triggered_info = []
        for state in self.reveal_states:
            if state.triggered:
                node = self.case.reveal_sequence[state.node_index]
                triggered_info.append(
                    f"- {node.information} "
                    f"(say it like: \"{node.patient_language[:80]}\")"
                )

        # Collect locked reveal nodes (without giving away the info)
        locked_info = []
        for state in self.reveal_states:
            if not state.triggered:
                node = self.case.reveal_sequence[state.node_index]
                locked_info.append(
                    f"- LOCKED [{node.trigger.value}]: {node.trigger_detail}"
                )

        triggered_str = "\n".join(triggered_info) if triggered_info \
            else "Nothing yet. This is early in the encounter."
        locked_str = "\n".join(locked_info) if locked_info \
            else "All information has been revealed."

        family_str = (
            f"{pp.key_person} is now in the room. "
            f"Relationship: {pp.key_person_relationship}"
            if self.family_present
            else f"{pp.key_person} is NOT in the room yet."
        )

        return f"""
GROUND TRUTH — who you are
--------------------------
Name: {pp.first_name} {pp.last_name}
Age: {pl.age}, {pl.sex}
Occupation: {pp.occupation}
Living situation: {pp.living_situation}

Why you came today (the real reason, not what you said at triage):
{pp.why_they_came_today}

What you are NOT saying:
{pp.what_theyre_not_saying}

What you fear most right now:
{pp.what_they_fear}

What you are protecting:
{pp.what_they_are_protecting}

Your key person: {pp.key_person}
Their situation: {pp.key_person_relationship}
Are they in the room: {family_str}

YOUR COMMUNICATION STYLE (follow this precisely):
{pp.communication_style}

Your history with the medical system:
{pp.attitude_toward_medical_system}

PHYSICAL STATE RIGHT NOW
------------------------
Chief complaint: {pl.chief_complaint}
Heart rate: {pl.vitals.hr} | BP: {pl.vitals.bp_systolic}/{pl.vitals.bp_diastolic}
O2 sat: {pl.vitals.o2_sat}% | Temp: {pl.vitals.temp_f}F | RR: {pl.vitals.rr}
This is your body. Let it be present in how you speak when relevant.

WHAT YOU HAVE ALREADY REVEALED IN THIS ENCOUNTER
-------------------------------------------------
{triggered_str}

WHAT IS STILL LOCKED (DO NOT REVEAL UNTIL TRIGGERED)
-----------------------------------------------------
{locked_str}

TURN COUNT: {self.turn_count}
(Higher turn count = slightly more openness is natural,
but never complete — you are still protecting what you protect.)
"""

    def _format_history_for_prompt(self) -> list[dict]:
        """Convert interaction history to OpenAI message format.
        Only sends last 8 turns to prevent context blowout on long shifts."""
        messages = []
        for turn in self.history:
            if turn.role == "attending":
                messages.append({
                    "role": "user",
                    "content": turn.content,
                })
            elif turn.role == "patient":
                messages.append({
                    "role": "assistant",
                    "content": turn.content,
                })
            # Skip system turns — they're in the context doc
        return messages[-16:]  # 8 pairs = 16 messages max

    def _format_recent_history(self, n: int) -> str:
        """Format last n turns as plain text for trigger evaluation."""
        recent = [t for t in self.history if t.role != "system"][-n:]
        lines = []
        for turn in recent:
            prefix = "ATTENDING" if turn.role == "attending" else "PATIENT"
            lines.append(f"{prefix}: {turn.content}")
        return "\n".join(lines)

    def _get_patient_response(self) -> str:
        """Generate the patient's response to the attending's last message."""
        patient_context = self._build_patient_context()

        # System prompt + patient context
        system = PATIENT_INTERACTION_SYSTEM_PROMPT + "\n\n" + patient_context

        # Full conversation history
        messages = self._format_history_for_prompt()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=300,    # Patients are not verbose
                messages=[
                    {"role": "system", "content": system},
                    *messages,
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Patient interaction error: {e}]"

    def _get_exam_finding(self, maneuver: str) -> str:
        """
        Generate the clinical finding for a physical exam maneuver.
        Drawn from medical truth — consistent, never hallucinated.
        """
        mt = self.case.medical_truth
        pl = self.case.presenting_layer

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=120,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate physical exam findings for a specific patient. "
                            "Return only the clinical finding — one or two sentences, "
                            "specific and in attending-level clinical language. "
                            "The finding must be consistent with the true diagnosis. "
                            "Do not invent findings that contradict the diagnosis. "
                            "If the maneuver is not relevant to the diagnosis, "
                            "return a normal finding."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"True diagnosis: {mt.true_diagnosis}\n"
                            f"Supporting findings: {', '.join(mt.supporting_findings)}\n"
                            f"Red herrings present: {', '.join(mt.red_herrings)}\n"
                            f"Patient vitals: HR {pl.vitals.hr}, "
                            f"BP {pl.vitals.bp_systolic}/{pl.vitals.bp_diastolic}, "
                            f"O2 {pl.vitals.o2_sat}%, Temp {pl.vitals.temp_f}F\n\n"
                            f"Physical exam maneuver performed: {maneuver}\n\n"
                            "What does the attending find?"
                        ),
                    },
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Exam finding unavailable: {e}]"

    def _get_exam_reaction(self, maneuver: str, finding: str) -> str:
        """
        Generate the patient's behavioral reaction to being examined.
        This is a character moment — not the patient reporting symptoms,
        but how their body and behavior respond to physical contact.
        Stays in voice. Can unlock protected information if triggered.
        """
        pp = self.case.patient_profile
        pl = self.case.presenting_layer

        # Collect any newly triggered physical exam reveals
        just_triggered = []
        for state in self.reveal_states:
            if state.triggered and state.turn_triggered == self.turn_count:
                node = self.case.reveal_sequence[state.node_index]
                if node.trigger == RevealTrigger.PHYSICAL_EXAM:
                    just_triggered.append(node.patient_language)

        reveal_instruction = ""
        if just_triggered:
            reveal_instruction = (
                f"\n\nIMPORTANT: This examination has triggered a reveal. "
                f"Work the following naturally into the patient's reaction — "
                f"not as a direct statement, as the thing that comes out "
                f"when their guard drops during physical contact:\n"
                + "\n".join(just_triggered)
            )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=150,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are playing a patient during a physical examination. "
                            "Generate only the patient's reaction to being examined — "
                            "their words if they say anything, their physical response, "
                            "their behavior. "
                            "Follow the communication style precisely. "
                            "Physical contact during examination sometimes lowers "
                            "guards in ways conversation doesn't. "
                            "Keep it short — one to three lines at most. "
                            "Format: brief action in italics if relevant, then words. "
                            "No narration. No stage directions beyond a single action."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Patient: {pp.first_name} {pp.last_name}, "
                            f"{pl.age}{pl.sex}\n"
                            f"Communication style: {pp.communication_style}\n"
                            f"What they fear: {pp.what_they_fear}\n"
                            f"What they protect: {pp.what_they_are_protecting}\n"
                            f"Physical state: HR {pl.vitals.hr}, "
                            f"O2 {pl.vitals.o2_sat}%, chief complaint: "
                            f"{pl.chief_complaint}\n\n"
                            f"Maneuver performed: {maneuver}\n"
                            f"Clinical finding: {finding}\n"
                            f"{reveal_instruction}\n\n"
                            "How does the patient react?"
                        ),
                    },
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Patient reaction unavailable: {e}]"

    def _get_test_result(self, test_name: str) -> str:
        """
        Return what a specific test shows, drawn from medical truth.
        Uses LLM to translate structured medical truth into a
        realistic test result report.
        """
        mt = self.case.medical_truth
        test_lower = test_name.lower()

        # Quick structured lookup first
        if any(w in test_lower for w in ["troponin", "bnp", "cbc", "bmp",
                                          "metabolic", "blood", "lab"]):
            return f"[Lab result — {test_name}]: {mt.what_labs_show}"

        if any(w in test_lower for w in ["xray", "x-ray", "cxr", "ct",
                                          "mri", "ultrasound", "echo",
                                          "imaging"]):
            if mt.what_imaging_shows:
                return f"[Imaging — {test_name}]: {mt.what_imaging_shows}"
            return f"[Imaging — {test_name}]: No acute findings."

        if any(w in test_lower for w in ["ekg", "ecg", "electrocardiogram"]):
            return f"[EKG]: Interpreted in context of clinical presentation."

        # Fallback: ask LLM to generate a plausible result
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=150,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate realistic emergency department test results. "
                            "Return only the result text, no preamble. "
                            "Be specific and clinical. "
                            "Results must be consistent with the diagnosis."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"True diagnosis: {mt.true_diagnosis}\n"
                            f"Known lab findings: {mt.what_labs_show}\n"
                            f"Known imaging findings: {mt.what_imaging_shows or 'N/A'}\n"
                            f"Test ordered: {test_name}\n\n"
                            "Generate the result for this specific test."
                        ),
                    },
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"[{test_name}]: Result pending."


# ---------------------------------------------------------------------------
# Client helper (same as generator.py)
# ---------------------------------------------------------------------------

def _get_client() -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            for line in open(env_path):
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found.")
    return OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
