from __future__ import annotations

import json
from pathlib import Path

import pytest

from cases.interaction import PatientSession
from cases.schema import GeneratedCase


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CASES_FILE = _REPO_ROOT / "test_output.json"


class _RaisingCompletions:
    def create(self, **kwargs):
        raise RuntimeError("Prompt tokens limit exceeded")


class _RaisingChat:
    def __init__(self) -> None:
        self.completions = _RaisingCompletions()


class _RaisingClient:
    def __init__(self) -> None:
        self.chat = _RaisingChat()


class _EmptyCompletions:
    def create(self, **kwargs):
        class _Message:
            content = ""

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]

        return _Response()


class _EmptyChat:
    def __init__(self) -> None:
        self.completions = _EmptyCompletions()


class _EmptyClient:
    def __init__(self) -> None:
        self.chat = _EmptyChat()


class _ForbiddenTriggerClient:
    def __init__(self) -> None:
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        raise AssertionError("trigger_eval LLM call should not be used for direct-question matching")


def _load_case(predicate) -> GeneratedCase:
    if not _CASES_FILE.is_file():
        pytest.skip(f"Missing {_CASES_FILE.name} (generated case bundle).")

    raw_cases = json.loads(_CASES_FILE.read_text(encoding="utf-8")).get("cases", [])
    for raw_case in raw_cases:
        case = GeneratedCase.model_validate(raw_case)
        if predicate(case):
            return case

    pytest.skip("No matching generated case found in test_output.json.")


def test_direct_alcohol_question_unlocks_reveal_without_llm_response() -> None:
    case = _load_case(
        lambda case: any(
            node.trigger.value == "direct_question"
            and "alcohol" in node.trigger_detail.lower()
            for node in case.reveal_sequence
        )
    )
    session = PatientSession(case)
    session.client = _RaisingClient()

    response = session.interact("When did you last have a drink?")
    summary = session.get_reveal_summary()

    assert response
    assert "Patient interaction error" not in response
    assert any(item["trigger"] == "direct_question" for item in summary["revealed"])
    assert len(summary["revealed"]) >= 1


def test_interact_returns_plain_fallback_when_provider_rejects_turn() -> None:
    case = _load_case(lambda case: bool(case.reveal_sequence))
    session = PatientSession(case)
    session.client = _RaisingClient()

    response = session.interact("Why did you come in today?")

    assert response
    assert "Patient interaction error" not in response
    assert not response.startswith("[")
    assert session.history[-1].content == response


def test_interact_returns_fallback_when_provider_returns_empty_content() -> None:
    case = _load_case(lambda case: bool(case.patient_profile.why_they_came_today))
    session = PatientSession(case)
    session.client = _EmptyClient()

    response = session.interact("Why did you come in today?")

    assert response
    assert response == session.history[-1].content
    assert not response.startswith("[")


def test_interact_replaces_summary_voice_with_bedside_fallback(monkeypatch) -> None:
    case = _load_case(lambda case: bool(case.reveal_sequence))
    session = PatientSession(case)

    monkeypatch.setattr(
        session,
        "_get_patient_response",
        lambda: "He did not call for help and the patient stayed on the floor.",
    )

    response = session.interact("What happened?")

    assert response
    assert response == session.history[-1].content
    assert not response.lower().startswith(("he ", "she ", "they ", "patient ", "the patient "))


def test_fallback_converts_third_person_case_copy_to_bedside_voice() -> None:
    case = _load_case(
        lambda case: case.patient_profile.why_they_came_today.startswith("He did not call for help")
    )
    session = PatientSession(case)
    session.client = _RaisingClient()

    response = session.interact("Why did you come in today?")

    assert response.startswith("I didn't call for help.")
    assert "My neighbor heard a thump" in response
    assert "I was on the floor" in response
    assert "He did not call" not in response


def test_patient_fields_are_normalized_to_first_person_at_session_setup() -> None:
    case = _load_case(lambda case: bool(case.patient_profile.why_they_came_today))
    session = PatientSession(case)

    normalized = session._normalized_patient_fields

    assert normalized["why_they_came_today"]
    assert not normalized["why_they_came_today"].lower().startswith(
        ("he ", "she ", "they ", "patient ", "the patient ")
    )
    assert all(rule for rule in session.voice_profile.first_person_rules)


def test_repeated_patient_question_stays_consistent_when_provider_fails() -> None:
    case = _load_case(lambda case: bool(case.patient_profile.why_they_came_today))
    session = PatientSession(case)
    session.client = _RaisingClient()
    session._check_conversational_triggers = lambda _: None

    first = session.interact("Why did you come in today?")
    second = session.interact("Why are you here today?")

    assert first
    assert second
    first_words = {word for word in first.lower().split() if len(word) > 4}
    second_words = {word for word in second.lower().split() if len(word) > 4}
    assert first_words & second_words
    assert not second.lower().startswith(("he ", "she ", "they ", "patient "))


def test_exam_uses_graceful_local_fallback_when_provider_rejects() -> None:
    case = _load_case(lambda case: bool(case.reveal_sequence))
    session = PatientSession(case)
    session.client = _RaisingClient()

    result = session.examine("chest")

    assert result
    assert "Exam finding unavailable" not in result
    assert "Patient reaction unavailable" not in result
    assert "[Exam: chest]" in result
    assert "Finding:" in result
    assert "Patient:" in result


def test_exam_uses_graceful_local_fallback_when_provider_returns_empty() -> None:
    case = _load_case(lambda case: bool(case.reveal_sequence))
    session = PatientSession(case)
    session.client = _EmptyClient()

    result = session.examine("general")

    assert result
    assert "Finding: \n" not in result
    assert "Patient: \n" not in result
    assert "Finding: " in result
    assert "Patient: " in result
    assert "[Reveal unlocked:" not in result or "Patient: [Reveal unlocked" not in result


def test_fallback_patient_response_for_medication_question_sounds_human() -> None:
    case = _load_case(lambda case: bool(case.patient_profile.why_they_came_today))
    session = PatientSession(case)
    session.client = _RaisingClient()

    response = session.interact("Are you on any medications or birth control?")

    assert response
    assert "No daily meds" in response or "Nothing major" in response
    assert "medication-related" in response
    assert not response.startswith("[")


def test_fallback_patient_response_for_alcohol_question_stays_bedside() -> None:
    case = _load_case(lambda case: bool(case.patient_profile.why_they_came_today))
    session = PatientSession(case)
    session.client = _RaisingClient()

    response = session.interact("How much have you been drinking lately?")

    assert response
    assert "stressed" in response.lower()
    assert "drinking" in response.lower() or "point" in response.lower()
    assert "Patient interaction error" not in response


def test_direct_question_matching_uses_local_heuristics_only() -> None:
    case = _load_case(
        lambda case: any(
            node.trigger.value == "direct_question"
            and "alcohol" in node.trigger_detail.lower()
            for node in case.reveal_sequence
        )
    )
    session = PatientSession(case)
    session.client = _RaisingClient()
    session.trigger_client = _ForbiddenTriggerClient()

    response = session.interact("When did you last have a drink?")
    summary = session.get_reveal_summary()

    assert response
    assert any(item["trigger"] == "direct_question" for item in summary["revealed"])


def test_chart_reveal_summary_prefers_clean_clinical_text_over_authored_script() -> None:
    case = _load_case(
        lambda case: any(
            "initially say no" in node.patient_language.lower()
            for node in case.reveal_sequence
        )
    )
    session = PatientSession(case)
    scripted_node = next(
        node for node in case.reveal_sequence
        if "initially say no" in node.patient_language.lower()
    )

    rendered = session._chart_reveal_text(scripted_node)

    assert "initially say no" not in rendered.lower()
    assert "after another pause" not in rendered.lower()
    assert rendered == scripted_node.information or rendered in scripted_node.information
