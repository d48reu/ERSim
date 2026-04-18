from __future__ import annotations

import pytest

import residents.resident as resident_module
from residents.resident import ResidentAI
from residents.schema import ResidentCaseMemory, make_default_roster, select_shift_roster


def test_resident_fallback_uses_latest_clue_when_provider_fails(three_cases, monkeypatch) -> None:
    ai = ResidentAI(select_shift_roster()[0])

    def _raise_call(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(resident_module, "_call", _raise_call)

    response = ai.respond(
        three_cases[0],
        "What changed?",
        interaction_summary=(
            "Reveals unlocked: 1\n"
            "PT: I had my last drink this morning.\n"
            "SYS: O2 sat 89% on room air."
        ),
    )

    assert response.what_they_say
    assert response.what_they_say != "Let me think on that and get back to you."
    assert "drinking most nights" in response.what_they_say.lower()
    assert response.flags


@pytest.mark.parametrize(
    ("resident_id", "expected_phrase"),
    [
        ("okafor_dre", "don't love widening"),
        ("chen_maya", "less comfortable"),
        ("patel_priya", "reorders the differential"),
        ("rivers_jordan", "feels more like"),
        ("adeyemi_sarah", "changes the picture"),
    ],
)
def test_archetype_followups_reference_new_clue_in_distinct_voice(
    three_cases,
    monkeypatch,
    resident_id: str,
    expected_phrase: str,
) -> None:
    resident = next(r for r in make_default_roster() if r.id == resident_id)
    ai = ResidentAI(resident)

    def _raise_call(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(resident_module, "_call", _raise_call)

    memory = ResidentCaseMemory(
        current_frame="viral illness with tremor",
        current_plan="supportive care",
        current_confidence="moderate",
        latest_clue="She had her last drink this morning and feels shaky now.",
        last_attending_intervention="asked patient directly about alcohol use",
        was_challenged=True,
        correction_stage="reconsidering",
    )

    response = ai.respond(
        three_cases[0],
        "What changed?",
        interaction_summary="PT: I had my last drink this morning and I feel shaky.",
        case_memory=memory,
    )

    lowered = response.what_they_say.lower()
    assert "drinking most nights" in lowered or "last drink" in lowered
    assert expected_phrase in lowered
    assert "the new clue is" not in lowered
    assert "get symptom control started" in lowered or "next, " in lowered or "methodically," in lowered
    assert "let me think on that and get back to you" not in lowered


def test_resident_persistence_keeps_voice_across_intro_clue_and_updated_read(
    three_cases,
    monkeypatch,
) -> None:
    resident = next(r for r in make_default_roster() if r.id == "okafor_dre")
    ai = ResidentAI(resident)

    def _raise_call(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(resident_module, "_call", _raise_call)

    opening = ai.proactive(three_cases[0])
    assert opening.what_they_say

    memory = ResidentCaseMemory(
        current_frame="bronchitis with tachycardia",
        current_plan="tight targeted workup",
        current_confidence="high",
        latest_clue="She had her last drink this morning and the tremor started after that.",
        last_attending_intervention="asked patient directly about recent drinking",
        was_challenged=True,
        correction_stage="reconsidering",
    )

    changed = ai.respond(
        three_cases[0],
        "What changed?",
        interaction_summary="PT: I had my last drink this morning and the tremor started after that.",
        case_memory=memory,
    )
    memory.current_frame = "alcohol withdrawal is moving higher on the list"
    memory.current_plan = "symptom control and monitored admission"
    memory.correction_stage = "updated"

    updated = ai.respond(
        three_cases[0],
        "What's your read?",
        interaction_summary="PT: I had my last drink this morning and the tremor started after that.",
        case_memory=memory,
    )

    assert "cleanest read" in changed.what_they_say.lower() or "don't love widening" in changed.what_they_say.lower()
    assert "drinking most nights" in changed.what_they_say.lower() or "last drink" in changed.what_they_say.lower()
    assert "alcohol withdrawal" in updated.what_they_say.lower()
    assert "cleanest read" in updated.what_they_say.lower() or "don't love widening" in updated.what_they_say.lower()


def test_academic_fallback_proactive_reads_like_hallway_speech(
    three_cases,
    monkeypatch,
) -> None:
    resident = next(r for r in make_default_roster() if r.id == "patel_priya")
    ai = ResidentAI(resident)

    def _raise_call(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(resident_module, "_call", _raise_call)

    opening = ai.proactive(three_cases[1])
    lowered = opening.what_they_say.lower()

    assert "first-pass frame is the story is" not in lowered
    assert "i'm most concerned about" in lowered


def test_followup_surfaces_reveal_as_human_summary_not_author_note(
    three_cases,
    monkeypatch,
) -> None:
    resident = next(r for r in make_default_roster() if r.id == "okafor_dre")
    ai = ResidentAI(resident)

    def _raise_call(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(resident_module, "_call", _raise_call)

    memory = ResidentCaseMemory(
        current_frame="anxiety with tremor",
        current_plan="symptom control",
        latest_clue="He will admit to 'drinking more than he should' over the past three months due to shoulder pain making him irritable.",
        was_challenged=True,
        correction_stage="reconsidering",
    )

    response = ai.respond(
        three_cases[0],
        "What changed?",
        interaction_summary="PT: I have been drinking more than I let on.",
        case_memory=memory,
    )

    lowered = response.what_they_say.lower()
    assert "will admit to" not in lowered
    assert "drinking more than he should" in lowered


def test_changed_followup_ignores_hallucinated_model_history_and_uses_memory(
    three_cases,
    monkeypatch,
) -> None:
    resident = next(r for r in make_default_roster() if r.id == "patel_priya")
    ai = ResidentAI(resident)

    def _hallucinated_call(**kwargs):
        return {
            "what_they_say": (
                "So I talked to him more directly about alcohol use and when I pressed "
                "he admitted heavy daily drinking."
            ),
            "confidence": "moderate",
        }

    monkeypatch.setattr(resident_module, "_call", _hallucinated_call)

    memory = ResidentCaseMemory(
        current_frame="anxiety with tremor",
        current_plan="rule out organic causes",
        latest_clue="drinking more than he should over the past three months",
        was_challenged=True,
        correction_stage="reconsidering",
    )

    response = ai.respond(
        three_cases[0],
        "What changed?",
        interaction_summary="PT: I've been having beers most nights.",
        case_memory=memory,
    )

    lowered = response.what_they_say.lower()
    assert "talked to him more directly" not in lowered
    assert "when i pressed" not in lowered
    assert "drinking more than he should" in lowered


def test_followup_surfaces_patient_will_admit_clue_without_author_scaffold(
    three_cases,
    monkeypatch,
) -> None:
    resident = next(r for r in make_default_roster() if r.id == "rivers_jordan")
    ai = ResidentAI(resident)

    def _raise_call(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(resident_module, "_call", _raise_call)

    memory = ResidentCaseMemory(
        current_frame="anxiety vs PE",
        current_plan="cardiopulmonary workup",
        latest_clue="Patient will admit she started Yasmin two weeks ago for period control but did not see the connection to the shortness of breath.",
        was_challenged=True,
        correction_stage="reconsidering",
    )

    response = ai.respond(
        three_cases[1],
        "What changed?",
        interaction_summary="PT: I started Yasmin two weeks ago.",
        case_memory=memory,
    )

    lowered = response.what_they_say.lower()
    assert "patient will admit" not in lowered
    assert "started yasmin two weeks ago" in lowered


def test_followup_paraphrases_drive_story_instead_of_echoing_patient_quote(
    three_cases,
    monkeypatch,
) -> None:
    resident = next(r for r in make_default_roster() if r.id == "adeyemi_sarah")
    ai = ResidentAI(resident)

    def _raise_call(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(resident_module, "_call", _raise_call)

    memory = ResidentCaseMemory(
        current_frame="anxiety vs PE",
        current_plan="cardiopulmonary workup",
        latest_clue="There was a dog. I hit the guardrail but it was low speed, I don't think I'm hurt from that.",
        was_challenged=True,
        correction_stage="reconsidering",
    )

    response = ai.respond(
        three_cases[1],
        "What changed?",
        interaction_summary="PT: There was a dog. I hit the guardrail but it was low speed.",
        case_memory=memory,
    )

    lowered = response.what_they_say.lower()
    assert "swerved to avoid a dog and hit the guardrail" in lowered
    assert "there was a dog. i hit the guardrail" not in lowered


def test_followup_paraphrases_alcohol_story_instead_of_echoing_quote(
    three_cases,
    monkeypatch,
) -> None:
    resident = next(r for r in make_default_roster() if r.id == "okafor_dre")
    ai = ResidentAI(resident)

    def _raise_call(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(resident_module, "_call", _raise_call)

    memory = ResidentCaseMemory(
        current_frame="anxiety with tremor",
        current_plan="symptom control",
        latest_clue="Look, I've been having some beers most nights. It's not a big deal. I stopped a few days ago to focus on this new contract.",
        was_challenged=True,
        correction_stage="reconsidering",
    )

    response = ai.respond(
        three_cases[0],
        "What's your read?",
        interaction_summary="PT: I've been having beers most nights and stopped a few days ago.",
        case_memory=memory,
    )

    lowered = response.what_they_say.lower()
    assert "drinking most nights and stopped a few days ago" in lowered
    assert "look, ive been having some beers" not in lowered
