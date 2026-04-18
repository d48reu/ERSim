from __future__ import annotations

import llm
from cases.interaction import PatientSession
from residents.resident import ResidentAI
from residents.schema import select_shift_roster


def test_get_model_uses_available_ollama_gameplay_fallback(monkeypatch) -> None:
    llm.reset()
    monkeypatch.setenv("ERSIM_BACKEND", "ollama")
    monkeypatch.delenv("ERSIM_MODEL", raising=False)
    monkeypatch.delenv("ERSIM_GEN_MODEL", raising=False)
    monkeypatch.setattr(
        llm,
        "_fetch_ollama_models",
        lambda: ["gemma4:26b-a4b-it-q4_K_M", "qwen3.5:9b"],
    )

    assert llm.get_model("gameplay") == "qwen3.5:9b"


def test_get_model_uses_available_ollama_generation_fallback(monkeypatch) -> None:
    llm.reset()
    monkeypatch.setenv("ERSIM_BACKEND", "ollama")
    monkeypatch.delenv("ERSIM_MODEL", raising=False)
    monkeypatch.delenv("ERSIM_GEN_MODEL", raising=False)
    monkeypatch.setattr(
        llm,
        "_fetch_ollama_models",
        lambda: ["gemma4:26b-a4b-it-q4_K_M", "qwen3.5-27b-fast:latest"],
    )

    assert llm.get_model("generation") == "qwen3.5-27b-fast:latest"


def test_get_model_falls_back_to_first_non_embedding_ollama_model(monkeypatch) -> None:
    llm.reset()
    monkeypatch.setenv("ERSIM_BACKEND", "ollama")
    monkeypatch.delenv("ERSIM_MODEL", raising=False)
    monkeypatch.delenv("ERSIM_GEN_MODEL", raising=False)
    monkeypatch.setattr(
        llm,
        "_fetch_ollama_models",
        lambda: ["qwen3-embedding:8b", "custom-local-chat:latest", "qwen2.5vl:7b"],
    )

    assert llm.get_model("gameplay") == "custom-local-chat:latest"


def test_per_purpose_model_override_wins_over_legacy_gameplay_override(monkeypatch) -> None:
    llm.reset()
    monkeypatch.setenv("ERSIM_BACKEND", "ollama")
    monkeypatch.setenv("ERSIM_MODEL", "legacy-model")
    monkeypatch.setenv("ERSIM_MODEL_PATIENT_LIVE", "patient-model")

    assert llm.get_model("patient_live") == "patient-model"
    assert llm.get_model("resident_live") == "legacy-model"


def test_per_purpose_backend_override_is_used(monkeypatch) -> None:
    llm.reset()
    monkeypatch.setenv("ERSIM_BACKEND", "openrouter")
    monkeypatch.setenv("ERSIM_BACKEND_PATIENT_LIVE", "ollama")
    monkeypatch.setattr(
        llm,
        "_fetch_ollama_models",
        lambda: ["qwen3.5:9b"],
    )

    assert llm.get_backend("patient_live") == "ollama"
    assert llm.get_model("patient_live") == "qwen3.5:9b"


def test_patient_session_uses_patient_live_route_by_default(three_cases, monkeypatch) -> None:
    llm.reset()
    monkeypatch.setenv("ERSIM_BACKEND", "openrouter")
    monkeypatch.setenv("ERSIM_BACKEND_PATIENT_LIVE", "ollama")
    monkeypatch.setenv("ERSIM_MODEL_PATIENT_LIVE", "patient-local")

    session = PatientSession(three_cases[0])

    assert session.model == "patient-local"


def test_resident_ai_uses_resident_live_route_by_default(monkeypatch) -> None:
    llm.reset()
    monkeypatch.setenv("ERSIM_BACKEND", "openrouter")
    monkeypatch.setenv("ERSIM_MODEL_RESIDENT_LIVE", "resident-remote")

    ai = ResidentAI(select_shift_roster()[0])

    assert ai.model == "resident-remote"
