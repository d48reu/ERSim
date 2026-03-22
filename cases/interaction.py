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

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from openai import OpenAI

from llm import get_client, get_model

logger = logging.getLogger("ersim.triggers")

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

ANTI-REPETITION

If your last 2-3 responses used an italicized gesture action, do NOT
use one this turn. Vary between: speaking with texture in the words
themselves, silence that communicates something, answering a question
the attending didn't quite ask, or a single physical gesture you
haven't used yet.

If the attending keeps asking open-ended questions and you've already
answered the obvious ones, start bringing in life details from your
ground truth — your job, your living situation, the person in the
waiting room, what you were doing before you came in, something that
happened this week. These are natural things real patients mention
when they're sitting in an ER with time to fill. They are not medical
reveals — they are human texture.

Never produce a response that is ONLY a stage direction with no speech.
Even a quiet patient says something, even if it's "I don't know" or
"Can I get some water?" or a non-answer that reveals their state of mind.
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
        self.model = get_model("gameplay", override=model)
        self.client = get_client()

        self.history: list[InteractionTurn] = []
        self.reveal_states = [
            RevealState(node_index=i)
            for i in range(len(case.reveal_sequence))
        ]
        self.ordered_tests: list[str] = []
        self._test_result_cache: dict[str, str] = {}
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
        canonical = self._canonical_test_name(test_name)
        if canonical not in self.ordered_tests:
            self.ordered_tests.append(canonical)
        triggered = self._check_test_triggers(canonical)

        # Return what the test shows, drawn from medical truth
        if canonical not in self._test_result_cache:
            self._test_result_cache[canonical] = self._get_test_result(canonical)
        result = self._test_result_cache[canonical]

        status = f"[Test ordered: {canonical}]\n{result}"
        if triggered:
            status += f"\n[Reveal unlocked: patient will now disclose related information]"

        self.history.append(InteractionTurn(
            role="system",
            content=f"Test ordered: {canonical}. Result: {result}",
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
                # Generate player-facing hints instead of raw trigger data
                hint_type, hint_text = self._player_hint(node)
                locked.append({
                    "trigger_needed": hint_type,
                    "trigger_detail": hint_text,
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
    # Player-facing hint generation
    # ------------------------------------------------------------------

    _TEST_NAME_ALIASES = {
        "electrocardiogram": "ecg",
        "electrocardiography": "ecg",
        "ekg": "ecg",
        "12-lead ekg": "ecg",
        "12-lead ecg": "ecg",
        "chest xray": "chest x-ray",
        "portable chest x-ray": "chest x-ray",
        "chest radiograph": "chest x-ray",
        "xray": "x-ray",
        "complete blood count": "cbc",
        "complete blood count with differential": "cbc",
        "cbc with differential": "cbc",
        "basic metabolic panel": "bmp",
        "comprehensive metabolic panel": "cmp",
        "d dimer": "d-dimer",
        "free thyroxine": "free t4",
        "thyroid function tests": "tsh",
        "urine drug screen": "urine drug screen",
        "pt/inr and ptt": "coagulation studies",
        "coags": "coagulation studies",
    }

    def _canonical_test_name(self, test_name: str) -> str:
        lowered = re.sub(r"\s+", " ", test_name.strip().lower())
        return self._TEST_NAME_ALIASES.get(lowered, lowered)

    _EXAM_HINT_KEYWORDS = {
        "exam", "palpat", "auscult", "percuss", "inspect",
        "lymph", "node", "finding", "perform",
        "lymphadenopathy", "hepatosplenomegaly", "edema",
        "tenderness", "mass", "murmur",
    }

    def _player_hint(self, node) -> tuple[str, str]:
        """
        Convert raw trigger data into actionable player-facing hints.
        Returns (hint_type, hint_text).
        """
        trigger = node.trigger.value
        detail = node.trigger_detail

        # trust_established: don't show the impossible-to-guess condition
        if node.trigger == RevealTrigger.TRUST_ESTABLISHED:
            return ("spend_time", "Keep talking to the patient — don't rush")

        # direct_question that describes an exam → show as physical_exam
        if node.trigger == RevealTrigger.DIRECT_QUESTION:
            detail_lower = detail.lower()
            if any(kw in detail_lower for kw in self._EXAM_HINT_KEYWORDS):
                # Extract the body area from the detail for the hint
                area_hints = []
                for cluster in self._EXAM_SYNONYMS:
                    if any(word in detail_lower for word in cluster):
                        # Pick the most common/readable word from the cluster
                        readable = sorted(cluster, key=len)[1] if len(cluster) > 1 else list(cluster)[0]
                        area_hints.append(readable)
                        break
                if area_hints:
                    return ("physical_exam", f"Try examining: {area_hints[0]}")
                return ("physical_exam", "A physical exam may reveal something")

        # prolonged_stay
        if node.trigger == RevealTrigger.PROLONGED_STAY:
            return ("spend_time", "Patient may open up after more time passes")

        # volunteered
        if node.trigger == RevealTrigger.VOLUNTEERED:
            return ("spend_time", "Patient volunteers this after a few interactions")

        # family_present — this one is clear enough
        if node.trigger == RevealTrigger.FAMILY_PRESENT:
            return ("family", "Bring the family member into the room")

        # test_result — already clear
        if node.trigger == RevealTrigger.TEST_RESULT:
            return ("test_result", detail)

        # physical_exam — already clear
        if node.trigger == RevealTrigger.PHYSICAL_EXAM:
            return ("physical_exam", detail)

        # direct_question (non-exam) — make it more actionable
        if node.trigger == RevealTrigger.DIRECT_QUESTION:
            detail_lower = detail.lower()
            if "alcohol" in detail_lower or "drink" in detail_lower:
                return ("ask_patient", "Ask directly about recent drinking or alcohol use")
            if "who is at home" in detail_lower or "who needs to be called" in detail_lower:
                return ("ask_patient", "Ask who is at home or who should be called")
            if "drive" in detail_lower or "incident" in detail_lower or "swerve" in detail_lower:
                return ("ask_patient", "Ask exactly what happened during the drive")
            if "productive" in detail_lower or "cough" in detail_lower or "when exactly" in detail_lower:
                return ("ask_patient", "Ask for a more exact cough timeline and whether it became productive")
            if "risk factors" in detail_lower or "hiv" in detail_lower or "tb" in detail_lower:
                return ("ask_patient", "Ask directly about infection risk factors or immune compromise")
            return ("ask_patient", f"Ask directly about: {detail}")

        # Fallback
        return (trigger, detail)

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
        """Check physical_exam triggers AND direct_question nodes
        whose trigger_detail describes an exam finding."""
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
            # B2 fix: direct_question nodes that describe exam findings
            # should also unlock when the matching exam is performed
            elif node.trigger == RevealTrigger.DIRECT_QUESTION:
                detail_lower = node.trigger_detail.lower()
                exam_keywords = {
                    "exam", "palpat", "auscult", "percuss", "inspect",
                    "lymph", "node", "finding", "perform", "abdomen",
                    "chest", "lung", "cardiac", "neuro", "skin", "rash",
                    "lymphadenopathy", "hepatosplenomegaly", "edema",
                    "tenderness", "mass", "murmur",
                }
                has_exam_language = any(kw in detail_lower for kw in exam_keywords)
                if has_exam_language and self._exam_words_match(maneuver, node.trigger_detail):
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

    @staticmethod
    def _robust_json_parse(raw: str) -> dict:
        """Parse JSON robustly, handling common LLM response quirks.

        Handles: markdown fences, trailing commas, Python bool literals
        (True/False), and partial JSON fragments.
        """
        # Strip markdown code fences
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Fix Python-style booleans (True/False → true/false)
        fixed = re.sub(r'\bTrue\b', 'true', cleaned)
        fixed = re.sub(r'\bFalse\b', 'false', fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Remove trailing commas before closing braces/brackets
        fixed2 = re.sub(r',\s*([}\]])', r'\1', fixed)
        try:
            return json.loads(fixed2)
        except json.JSONDecodeError:
            pass

        # Try to extract a JSON object from surrounding text
        m = re.search(r'\{[^}]*"triggered"\s*:\s*(true|false)[^}]*\}', fixed2, re.IGNORECASE)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        # Last resort: look for the word true/false after "triggered"
        m = re.search(r'"?triggered"?\s*[:=]\s*(true|false)', fixed2, re.IGNORECASE)
        if m:
            return {"triggered": m.group(1).lower() == "true"}

        raise json.JSONDecodeError("Could not extract triggered value", raw, 0)

    @staticmethod
    def _keyword_fallback(attending_message: str, trigger_detail: str) -> bool:
        """Keyword-based fallback for trigger evaluation.

        Checks both individual words and 2-word phrases from the
        trigger_detail against the attending message.
        """
        _STOPWORDS = {
            "the", "a", "an", "is", "are", "was", "were", "has", "have",
            "do", "did", "how", "what", "when", "where", "why", "who",
            "long", "been", "you", "your", "i", "it", "in", "of", "to",
            "and", "or", "for", "that", "this", "with", "about",
        }

        def _clean(s):
            return re.sub(r"[^\w\s]", "", s.lower())

        msg_clean = _clean(attending_message)
        detail_clean = _clean(trigger_detail)

        msg_words = set(msg_clean.split())
        detail_words = set(detail_clean.split())

        # Single-word overlap (excluding stopwords)
        overlap = (msg_words & detail_words) - _STOPWORDS
        if overlap:
            return True

        # 2-word phrase matching from trigger_detail against message
        detail_word_list = detail_clean.split()
        for i in range(len(detail_word_list) - 1):
            bigram = f"{detail_word_list[i]} {detail_word_list[i+1]}"
            # Skip if both words are stopwords
            if detail_word_list[i] in _STOPWORDS and detail_word_list[i+1] in _STOPWORDS:
                continue
            if bigram in msg_clean:
                return True

        return False

    def _evaluate_trigger(self, node, attending_message: str) -> bool:
        """
        Use the LLM to evaluate whether a conversational trigger
        condition has been met. Conservative — only fires when clear.
        """
        # VOLUNTEERED: check if enough turns have passed
        if node.trigger == RevealTrigger.VOLUNTEERED:
            logger.debug("VOLUNTEERED trigger: turn_count=%d, threshold=3", self.turn_count)
            return self.turn_count >= 3

        # PROLONGED_STAY: check turn count as proxy for time
        if node.trigger == RevealTrigger.PROLONGED_STAY:
            logger.debug("PROLONGED_STAY trigger: turn_count=%d, threshold=8", self.turn_count)
            return self.turn_count >= 8

        # TRUST_ESTABLISHED: passive unlock based on engagement, not LLM judgment.
        # Unlocks when the attending has had enough positive interactions:
        # - At least 4 turns of conversation (they didn't rush)
        # - At least 2 direct patient interactions in history
        # The idea: trust is built by showing up, not by saying magic words.
        if node.trigger == RevealTrigger.TRUST_ESTABLISHED:
            patient_interactions = sum(
                1 for t in self.history if t.role == "attending"
            )
            result = self.turn_count >= 4 and patient_interactions >= 2
            logger.debug(
                "TRUST_ESTABLISHED trigger: turn_count=%d, patient_interactions=%d, result=%s",
                self.turn_count, patient_interactions, result,
            )
            return result

        # For DIRECT_QUESTION only: use LLM to evaluate
        logger.debug(
            "Evaluating DIRECT_QUESTION trigger: detail=%r, message=%r",
            node.trigger_detail[:80], attending_message[:80],
        )

        max_attempts = 2  # 1 initial + 1 retry
        last_raw = ""
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=150,
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
                last_raw = response.choices[0].message.content.strip()
                result = self._robust_json_parse(last_raw)
                triggered = result.get("triggered", False)
                logger.debug(
                    "Trigger eval attempt %d succeeded: raw=%r, triggered=%s",
                    attempt + 1, last_raw[:120], triggered,
                )
                return triggered
            except json.JSONDecodeError:
                logger.warning(
                    "Trigger eval attempt %d: JSON parse failed, raw=%r",
                    attempt + 1, last_raw[:200],
                )
                # Retry on first attempt
                if attempt < max_attempts - 1:
                    continue
            except Exception as e:
                logger.warning(
                    "Trigger eval attempt %d failed (%s: %s)",
                    attempt + 1, type(e).__name__, e,
                )
                break  # Don't retry on non-JSON errors (API failures etc.)

        # Fallback for direct_question: keyword + bigram overlap
        if node.trigger == RevealTrigger.DIRECT_QUESTION:
            fallback_result = self._keyword_fallback(attending_message, node.trigger_detail)
            logger.debug(
                "Keyword fallback for DIRECT_QUESTION: result=%s, detail=%r",
                fallback_result, node.trigger_detail[:80],
            )
            return fallback_result
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
{self._warmth_injection()}
"""

    def _warmth_injection(self) -> str:
        """After turn 3, nudge the patient to bring in life details."""
        if self.turn_count < 3:
            return ""
        pp = self.case.patient_profile
        return f"""
THINGS YOU CAN NATURALLY BRING UP (not all at once — one per turn max):
- Your work: {pp.occupation}
- Your living situation: {pp.living_situation}
- The person waiting for you: {pp.key_person} ({pp.key_person_relationship})
- What you were doing before you came in / why today: {pp.why_they_came_today}
These are NOT gated reveals. They are normal things a patient mentions
when they're sitting in an ER. Use them to fill silence and show who
you are as a person, not just a chief complaint.
"""

    def _format_history_for_prompt(self) -> list[dict]:
        """Convert interaction history to OpenAI message format.
        Only sends last 3 pairs (6 messages) to keep system prompt dominant
        and prevent the LLM from pattern-matching on its own gestures."""
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
        return messages[-6:]  # 3 pairs = 6 messages max

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
                max_tokens=350,    # Room for a real sentence + one behavioral beat
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

    # Override with stricter, test-specific result generation so the
    # ordered study and returned content stay aligned.
    def _get_test_result(self, test_name: str) -> str:
        test_lower = self._canonical_test_name(test_name)

        if any(w in test_lower for w in [
            "troponin", "bnp", "cbc", "bmp", "cmp", "lactate", "d-dimer",
            "tsh", "free t4", "coagulation", "inr", "ptt", "hiv", "tb",
            "afb", "culture", "urinalysis", "ua", "pregnancy", "hcg",
            "magnesium",
        ]):
            return self._generate_structured_test_result(test_lower, "lab")

        if any(w in test_lower for w in [
            "x-ray", "chest x-ray", "cxr", "ct", "cta", "mri", "ultrasound", "echo",
        ]):
            return self._generate_structured_test_result(test_lower, "imaging")

        if any(w in test_lower for w in ["ekg", "ecg", "electrocardiogram"]):
            return self._generate_structured_test_result(test_lower, "ecg")

        mt = self.case.medical_truth
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
                            "Be specific and clinical. Results must be consistent with the diagnosis. "
                            "The result must ONLY match the ordered test and must not mention unrelated studies."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"True diagnosis: {mt.true_diagnosis}\n"
                            f"Known lab findings: {mt.what_labs_show}\n"
                            f"Known imaging findings: {mt.what_imaging_shows or 'N/A'}\n"
                            f"Test ordered: {test_name}\n\n"
                            "Generate the result for this specific test only."
                        ),
                    },
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"[{test_name}]: Result pending."

    def _generate_structured_test_result(self, test_name: str, category: str) -> str:
        mt = self.case.medical_truth
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=180,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate one emergency department test result.\n"
                            "Rules:\n"
                            "- Match the ordered test exactly.\n"
                            "- Lab results may only contain lab-style findings.\n"
                            "- Imaging results may only contain imaging findings/impression.\n"
                            "- ECG results may only contain rhythm/rate/interval/ST-T findings.\n"
                            "- Never mention another modality or unrelated study.\n"
                            "- If source truth is broad, generate a conservative compatible result."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Ordered test: {test_name}\n"
                            f"Category: {category}\n"
                            f"True diagnosis: {mt.true_diagnosis}\n"
                            f"Known lab findings: {mt.what_labs_show}\n"
                            f"Known imaging findings: {mt.what_imaging_shows or 'N/A'}\n"
                            "Return only the result text for the ordered test."
                        ),
                    },
                ],
            )
            result = response.choices[0].message.content.strip()
            if self._result_matches_category(result, category):
                return result
        except Exception:
            pass
        if category == "lab":
            if "urinalysis" in test_name or test_name == "ua":
                return (
                    f"[Lab result - {test_name}]: UA shows specific gravity 1.025, "
                    f"trace blood, negative nitrite, negative leukocyte esterase."
                )
            return (
                f"[Lab result - {test_name}]: WBC 10.8, hemoglobin 13.2, "
                f"creatinine 0.9, interpreted in clinical context."
            )
        if category == "imaging":
            return f"[Imaging - {test_name}]: Findings compatible with the suspected diagnosis."
        return f"[ECG - {test_name}]: Sinus rhythm interpreted in clinical context."

    def _result_matches_category(self, result: str, category: str) -> bool:
        text = result.lower()
        lab_words = (
            "wbc", "hemoglobin", "hematocrit", "platelets",
            "sodium", "potassium", "creatinine", "troponin",
            "ua", "urinalysis", "nitrite", "leukocyte", "specific gravity",
        )
        imaging_words = ("impression", "findings", "x-ray", "ct", "mri", "ultrasound", "fracture", "infiltrate", "effusion")
        ecg_words = ("ecg", "ekg", "rhythm", "rate", "qrs", "st", "t wave", "sinus")

        if category == "lab":
            return any(word in text for word in lab_words) and not any(word in text for word in ("ct head", "mri", "ultrasound"))
        if category == "imaging":
            return any(word in text for word in imaging_words) and not any(word in text for word in ("hemoglobin", "platelets", "creatinine", "potassium"))
        if category == "ecg":
            return any(word in text for word in ecg_words) and not any(word in text for word in ("creatinine", "platelets", "impression: no acute"))
        return True


# _get_client() removed — using centralized llm.get_client()
