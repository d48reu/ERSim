"""Smoke tests for Shift composition (no LLM setup, no network)."""

from __future__ import annotations

from types import SimpleNamespace

import llm

from residents.schema import select_shift_roster
from shift.bay import BayStatus
from shift.shift import Shift


def test_shift_builds_bays_and_trap_flags(three_cases) -> None:
    roster = select_shift_roster()[:3]
    shift = Shift(cases=three_cases, residents=roster)
    assert set(shift.bays.keys()) == {"Bay 1", "Bay 2", "Bay 3"}
    trapped = sum(1 for bay in shift.bays.values() if getattr(bay, "is_trap", False))
    assert trapped >= 1


def test_navigation_without_setup(three_cases) -> None:
    """go/leave/status must not require setup() (no resident LLM calls)."""
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    assert shift.active_bay_id is None
    out = shift.go("1")
    assert shift.active_bay_id == "Bay 1"
    assert "Bay 1" in out
    shift.leave()
    assert shift.active_bay_id is None
    status = shift.status()
    assert "STATUS" in status


def test_roster_info_shape(three_cases) -> None:
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    roster = shift.get_roster_info()
    assert len(roster) == 3
    for row in roster:
        assert "bay_id" in row and "name" in row and "patient_name" in row


def test_bays_start_ready_and_other_clocks_begin_after_first_entry(three_cases) -> None:
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    stub_assessment = SimpleNamespace(
        what_they_say="Resident ready.",
        plan_summary="Basic evaluation.",
        plan_tests=[],
        plan_questions=[],
        differential=[],
        flags=[],
        confidence="",
    )

    for bay_id in shift.bays:
        shift.apply_setup_result(bay_id, resident_ai=object(), assessment=stub_assessment)

    assert all(bay.status == BayStatus.WAITING for bay in shift.bays.values())

    shift.go("1")

    assert shift.bays["Bay 1"].status == BayStatus.ACTIVE
    assert shift.bays["Bay 2"].status == BayStatus.SUPERVISED
    assert shift.bays["Bay 3"].status == BayStatus.SUPERVISED
    assert shift.bays["Bay 2"].timer_ticks == 0
    assert shift.bays["Bay 3"].timer_ticks == 0


def test_shift_setup_uses_patient_live_route_for_patient_sessions(
    three_cases,
    monkeypatch,
) -> None:
    llm.reset()
    monkeypatch.setenv("ERSIM_BACKEND", "openrouter")
    monkeypatch.setenv("ERSIM_MODEL", "legacy-resident-model")
    monkeypatch.setenv("ERSIM_MODEL_PATIENT_LIVE", "patient-live-model")

    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    shift.prepare_setup_jobs()

    assert all(
        bay.patient_session and bay.patient_session.model == "patient-live-model"
        for bay in shift.bays.values()
    )


def test_responsive_assessments_do_not_overwrite_case_frame_with_full_speech(
    three_cases,
) -> None:
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    bay = shift.bays["Bay 1"]
    bay.seed_case_memory()
    original_frame = bay.resident_case_memory.current_frame

    assessment = SimpleNamespace(
        differential=[],
        what_they_say="The new clue is there was a dog on the highway. I was still leaning PE, but that changes it.",
        plan_summary="Tighten the workup.",
        plan_tests=[],
        plan_questions=[],
        recommended_workup=[],
        confidence="moderate",
    )

    bay.absorb_resident_assessment(assessment, mode="responsive")

    assert bay.resident_case_memory.current_frame == original_frame
