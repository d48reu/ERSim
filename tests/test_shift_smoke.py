"""Smoke tests for Shift composition (no LLM setup, no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cases.schema import GeneratedCase
from residents.schema import select_shift_roster
from shift.shift import Shift

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CASES_FILE = _REPO_ROOT / "test_output.json"


@pytest.fixture
def three_cases() -> list[GeneratedCase]:
    if not _CASES_FILE.is_file():
        pytest.skip(f"Missing {_CASES_FILE.name} (generated case bundle).")
    data = json.loads(_CASES_FILE.read_text(encoding="utf-8"))
    raw = data.get("cases", [])
    if len(raw) < 3:
        pytest.skip("Need at least 3 cases in test_output.json for this test.")
    return [GeneratedCase.model_validate(c) for c in raw[:3]]


def test_shift_builds_bays_and_trap_flags(three_cases: list[GeneratedCase]) -> None:
    roster = select_shift_roster()[:3]
    shift = Shift(cases=three_cases, residents=roster)
    assert set(shift.bays.keys()) == {"Bay 1", "Bay 2", "Bay 3"}
    trapped = sum(1 for b in shift.bays.values() if getattr(b, "is_trap", False))
    assert trapped >= 1


def test_navigation_without_setup(three_cases: list[GeneratedCase]) -> None:
    """go/leave/status must not require setup() (no resident LLM calls)."""
    roster = select_shift_roster()[:3]
    s = Shift(cases=three_cases, residents=roster)
    assert s.active_bay_id is None
    out = s.go("1")
    assert s.active_bay_id == "Bay 1"
    assert "Bay 1" in out
    s.leave()
    assert s.active_bay_id is None
    status = s.status()
    assert "STATUS" in status


def test_roster_info_shape(three_cases: list[GeneratedCase]) -> None:
    s = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    roster = s.get_roster_info()
    assert len(roster) == 3
    for row in roster:
        assert "bay_id" in row and "name" in row and "patient_name" in row
