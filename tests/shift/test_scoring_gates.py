"""Regression tests for the scoring and UX calibration fixes (commit ca4b63a).

Covers:
  - #1 guaranteed trap fallback when no rule-based match exists
  - #2 thin-chart gate now requires returned tests OR 2+ reveals OR family
  - #2 thin-chart correct dispo yields 0.5 dispo credit
  - #3 Next: nudge is negation-aware (normal ECG doesn't escalate)
  - #3 Next: nudge still escalates on real abnormalities
  - #4 header-only result bodies don't hijack the summary line
  - #6 short-form aliases (CMP, CXR, UA) normalize and validate
  - #7 tick() emits no further fire/warning after autonomous_fired
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cases.interaction import InteractionTurn, PatientSession
from cases.schema import (
    AcuityLevel, GeneratedCase, MedicalTruth, OutcomeTrajectory,
    PatientProfile, PresentingLayer, SystemicFlags, Vitals,
)
from residents.schema import make_default_roster, select_shift_roster
from shift.bay import Bay, BayStatus
from shift.shift import Shift
from shift.tests_mixin import ShiftTestsMixin
from shift.traps import detect_and_assign_traps


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_case(case_id: str, acuity: int, miss_reason: str = "m") -> GeneratedCase:
    """Build a minimal valid GeneratedCase for isolated trap/thin-chart tests."""
    return GeneratedCase(
        case_id=case_id,
        narrative_hook="x",
        presenting_layer=PresentingLayer(
            chief_complaint="c", age=40, sex="M",
            vitals=Vitals(hr=80, bp_systolic=120, bp_diastolic=80, rr=16, temp_f=98.6, o2_sat=98),
            triage_note="t", acuity=AcuityLevel(acuity),
            arrival_method="walk-in", time_in_waiting_room_minutes=10,
        ),
        medical_truth=MedicalTruth(
            true_diagnosis="d", supporting_findings=["x"], what_labs_show="y",
            what_imaging_shows=None, time_sensitivity=False, time_window_minutes=None,
            red_herrings=["r"], classic_miss_reason=miss_reason,
        ),
        patient_profile=PatientProfile(
            first_name="A", last_name="B", occupation="o", living_situation="l",
            why_they_came_today="w", what_theyre_not_saying="n", what_they_fear="f",
            what_they_are_protecting="p", communication_style="c",
            attitude_toward_medical_system="a", key_person="k", key_person_relationship="r",
        ),
        reveal_sequence=[],
        outcome_trajectory=OutcomeTrajectory(
            correct_treatment="c", correct_outcome="o", missed_diagnosis="m",
            resident_catches_it_unsupervised="s", resident_misses_it_unsupervised="s",
            disposition="discharge",
        ),
        systemic_flags=SystemicFlags(return_patient=False),
    )


class _NudgeStub(ShiftTestsMixin):
    """Minimal subclass to exercise _suggest_next_step / _summarize_result directly."""
    pass


# ---------------------------------------------------------------------------
# #1 — trap fallback
# ---------------------------------------------------------------------------

def test_trap_fallback_flags_one_bay_even_with_no_keyword_match() -> None:
    """When cases share no keywords with rule library, fallback still picks one."""
    cases = [
        _make_case("T1", acuity=3, miss_reason="Very unusual presentation with no common keywords."),
        _make_case("T2", acuity=4, miss_reason="Another benign case with no hits."),
        _make_case("T3", acuity=5, miss_reason="Third case, still no hits."),
    ]
    roster = select_shift_roster(make_default_roster())[:3]
    bays = {
        f"Bay {i+1}": Bay(bay_id=f"Bay {i+1}", case=cases[i], resident=roster[i])
        for i in range(3)
    }
    detect_and_assign_traps(bays)
    flagged = [bid for bid, b in bays.items() if b.is_trap]
    assert len(flagged) == 1, f"expected exactly 1 trap, got {flagged}"
    assert bays[flagged[0]].trap_detail, "trap_detail must be populated"


def test_trap_fallback_picks_highest_acuity_bay() -> None:
    cases = [
        _make_case("T1", acuity=5),  # lowest urgency
        _make_case("T2", acuity=2),  # most urgent
        _make_case("T3", acuity=4),
    ]
    roster = select_shift_roster(make_default_roster())[:3]
    bays = {
        f"Bay {i+1}": Bay(bay_id=f"Bay {i+1}", case=cases[i], resident=roster[i])
        for i in range(3)
    }
    detect_and_assign_traps(bays)
    flagged = next(bid for bid, b in bays.items() if b.is_trap)
    assert flagged == "Bay 2", f"fallback should pick the most acute bay, picked {flagged}"


# ---------------------------------------------------------------------------
# #2 — thin-chart gate + half dispo credit
# ---------------------------------------------------------------------------

def _build_shift_with_stub_sessions(three_cases):
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    for bay in shift.bays.values():
        bay.patient_session = PatientSession(bay.case)  # stateful holder, no LLM
    stub_assessment = SimpleNamespace(
        what_they_say="x", plan_summary="y", plan_tests=[], plan_questions=[],
        differential=[], flags=[], confidence="",
    )
    for bay_id in shift.bays:
        shift.apply_setup_result(bay_id, resident_ai=object(), assessment=stub_assessment)
    return shift


def _register_attending_action(bay) -> None:
    bay.events.append(SimpleNamespace(
        actor="attending", event_type="talk", content="x", internal="", turn=0,
    ))


def test_thin_chart_fires_when_no_signal_even_with_many_turns(three_cases) -> None:
    shift = _build_shift_with_stub_sessions(three_cases)
    shift.go("1")
    bay = shift.bays["Bay 1"]
    _register_attending_action(bay)
    # 12 turns of chatter, no reveals, no tests, no family
    for _ in range(12):
        bay.patient_session.history.append(InteractionTurn(role="attending", content="x"))
        bay.patient_session.history.append(InteractionTurn(role="patient", content="y"))
    bay._test_results = {}

    shift.resolve(three_cases[0].outcome_trajectory.disposition)
    assert bay.low_evidence_disposition is True


def test_thin_chart_does_not_fire_with_one_returned_test(three_cases) -> None:
    shift = _build_shift_with_stub_sessions(three_cases)
    shift.go("1")
    bay = shift.bays["Bay 1"]
    _register_attending_action(bay)
    bay._test_results = {"ecg": "normal"}  # one signal is enough

    shift.resolve(three_cases[0].outcome_trajectory.disposition)
    assert bay.low_evidence_disposition is False


def test_thin_chart_correct_dispo_yields_half_credit(three_cases) -> None:
    shift = _build_shift_with_stub_sessions(three_cases)
    shift.go("1")
    bay1 = shift.bays["Bay 1"]
    _register_attending_action(bay1)
    bay1._test_results = {}  # thin chart
    shift.resolve(three_cases[0].outcome_trajectory.disposition)

    for bid in ("2", "3"):
        shift.go(bid)
        bay = shift.bays[f"Bay {bid}"]
        _register_attending_action(bay)
        bay._test_results = {"ecg": "normal"}  # full chart
        shift.resolve(three_cases[int(bid) - 1].outcome_trajectory.disposition)

    debrief = shift.debrief()
    # 1 half-credit + 2 full = 2.5/3
    assert "2.5/3" in debrief, f"expected half-credit tally, got tail:\n{debrief[-400:]}"
    # Grade should not be A with a thin-chart dispo
    assert "SHIFT GRADE: A\n" not in debrief


# ---------------------------------------------------------------------------
# #3 — negation-aware Next: nudges
# ---------------------------------------------------------------------------

@pytest.fixture
def nudge_stub():
    return _NudgeStub()


@pytest.fixture
def unrelated_bay():
    return SimpleNamespace(case=SimpleNamespace(case_id="UNRELATED"))


@pytest.mark.parametrize("label,result,expected_fragment", [
    ("normal ecg w/ no acute ischemic changes",
     "Impression: Sinus tachycardia. No acute ischemic changes.",
     "closer to discharge"),
    ("normal ecg w/ no acute coronary syndrome",
     "Sinus tachycardia. No acute coronary syndrome.",
     "closer to discharge"),
    ("normal troponin value",
     "Troponin: 0.01 ng/mL, within normal limits.",
     "closer to discharge"),
    ("head ct negative for bleed",
     "No acute intracranial hemorrhage. Unremarkable.",
     "closer to discharge"),
])
def test_nudge_does_not_escalate_on_negated_findings(nudge_stub, unrelated_bay, label, result, expected_fragment):
    got = nudge_stub._suggest_next_step(unrelated_bay, "ecg", result)
    assert expected_fragment.lower() in got.lower(), f"[{label}] got: {got}"


@pytest.mark.parametrize("label,test_name,result,expected_fragment", [
    ("stemi ecg", "ecg", "ST elevation in V2-V4, consistent with anterior STEMI.",
     "cardiac escalation"),
    ("elevated troponin", "troponin", "Troponin: 2.4 ng/mL, elevated 80x normal.",
     "cardiac escalation"),
    ("elevated lactate", "lactate", "Lactate: 3.2 mmol/L, elevated.",
     "sepsis"),
    ("sah on head ct", "head ct", "Diffuse subarachnoid hemorrhage in basal cisterns.",
     "neurosurgery"),
])
def test_nudge_still_escalates_on_real_abnormalities(nudge_stub, unrelated_bay, label, test_name, result, expected_fragment):
    got = nudge_stub._suggest_next_step(unrelated_bay, test_name, result)
    assert expected_fragment.lower() in got.lower(), f"[{label}] got: {got}"


# ---------------------------------------------------------------------------
# #4 — header-only result bodies
# ---------------------------------------------------------------------------

def test_header_only_body_does_not_become_the_summary(nudge_stub):
    got = nudge_stub._summarize_result("noncontrast head ct", "**IMPRESSION:**")
    assert "IMPRESSION" not in got or "open the chart" in got.lower()
    assert "open the chart" in got.lower()


def test_header_plus_body_picks_the_body(nudge_stub):
    got = nudge_stub._summarize_result(
        "head ct",
        "**IMPRESSION:**\n1. No acute intracranial hemorrhage.\n2. Age-appropriate atrophy.",
    )
    assert "no acute" in got.lower()
    assert got.strip() != "**IMPRESSION:**"


# ---------------------------------------------------------------------------
# #6 — short-form aliases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("CMP", "bmp"),
    ("cmp", "bmp"),
    ("CXR", "chest x"),
    ("chem 7", "bmp"),
    ("tft", "tsh"),
    ("hs troponin", "troponin"),
    ("d dimer", "d-dimer"),
    ("u/a", "ua"),
])
def test_short_form_aliases_normalize(nudge_stub, raw, expected):
    assert nudge_stub._normalize_test_name(raw) == expected
    assert nudge_stub._validate_test_name(expected)


@pytest.mark.parametrize("short", ["UA", "ua", "PT"])
def test_two_char_known_short_forms_validate(nudge_stub, short):
    assert nudge_stub._validate_test_name(short)


@pytest.mark.parametrize("junk", ["34F", "16M", "a", "xyz"])
def test_junk_still_rejected(nudge_stub, junk):
    assert not nudge_stub._validate_test_name(junk)


# ---------------------------------------------------------------------------
# #7 — warning / fire silence after autonomous
# ---------------------------------------------------------------------------

def test_tick_silent_after_autonomous_fired() -> None:
    bay = Bay(bay_id="Bay 1", case=_make_case("T", acuity=1), resident=make_default_roster()[0])
    bay.status = BayStatus.SUPERVISED
    # Drain the pre-autonomous sequence: warning then fire
    for _ in range(6):
        bay.tick()
    bay.autonomous_fired = True
    # Simulate go()+leave() resetting the transient fields
    bay.timer_ticks = 0
    bay.warning_fired = False

    signals = [bay.tick() for _ in range(10)]
    assert all(s == "ok" for s in signals), f"expected all ok post-fire, got {signals}"


def test_warning_still_fires_in_normal_path() -> None:
    bay = Bay(bay_id="Bay 1", case=_make_case("T", acuity=1), resident=make_default_roster()[0])
    bay.status = BayStatus.SUPERVISED
    assert bay.warning_threshold == 4
    # First 4 ticks: 3 ok + 1 warning (ticks 1,2,3 < 4; tick 4 == warning_threshold)
    signals = [bay.tick() for _ in range(4)]
    assert "warning" in signals, f"warning should still fire in normal path, got {signals}"


# ---------------------------------------------------------------------------
# #9 — approve_plan is one attending action, not two
# ---------------------------------------------------------------------------

def test_approve_plan_is_one_tick_not_two(three_cases) -> None:
    """Regression: prior behavior ticked once in approve_plan AND once in
    bundle_test, so Acuity-1 bays were force-visited first. Now a single
    approve_plan produces a single tick on other bays.
    """
    shift = _build_shift_with_stub_sessions(three_cases)
    # Seed a plan with tests on Bay 2 so _execute_plan goes through bundle_test
    shift.bays["Bay 2"]._pending_plan = SimpleNamespace(
        what_they_say="x",
        plan_summary="y",
        plan_tests=["cbc", "bmp"],
        plan_questions=[],
        differential=[],
        flags=[],
        confidence="",
    )
    # Stub resident_ai enough for approve_plan
    shift.bays["Bay 2"].resident_ai = SimpleNamespace(
        attending_backed=lambda _: None,
        attending_overrode=lambda _: None,
    )

    # Enter Bay 2 — this flips Bay 1 and Bay 3 to SUPERVISED without ticking
    shift.go("2")
    ticks_before = {bid: b.timer_ticks for bid, b in shift.bays.items() if bid != "Bay 2"}

    shift.approve_plan(1)

    ticks_after = {bid: b.timer_ticks for bid, b in shift.bays.items() if bid != "Bay 2"}
    for bid in ticks_before:
        delta = ticks_after[bid] - ticks_before[bid]
        assert delta == 1, f"{bid} should tick exactly once per approve_plan, got {delta}"
