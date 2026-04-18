from __future__ import annotations

import asyncio

from api.commands import _shift_ended_payload, process_command
from api.session import GameSession
from residents.schema import select_shift_roster
from shift.shift import Shift


def test_shift_ended_payload_includes_feedback_context(three_cases) -> None:
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    session = GameSession(shift=shift, session_id="session-123")
    debrief = shift.debrief()

    payload = _shift_ended_payload(session, debrief)
    feedback = payload["feedback_context"]

    assert payload["summary"] == debrief
    assert feedback["session_id"] == "session-123"
    assert feedback["build_version"] == session.build_version
    assert feedback["grade"]
    assert feedback["metrics"]["disposition_accuracy"] is not None
    assert "clinical_depth" in feedback["metrics"]
    assert "resolved_cases" in feedback["metrics"]
    assert "total_cases" in feedback["metrics"]


class _StubPatientSession:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.exams: list[str] = []

    def interact(self, message: str) -> str:
        self.messages.append(message)
        return "I had my last drink this morning."

    def examine(self, maneuver: str) -> str:
        self.exams.append(maneuver)
        return f"[Exam: {maneuver}]\nFinding: focal tenderness\nPatient: Ow."

    def get_reveal_summary(self) -> dict:
        return {
            "revealed": [],
            "locked": [],
            "family_present": False,
            "turns": len(self.messages),
            "tests_ordered": [],
        }


class _RecordingSession:
    def __init__(self, shift: Shift) -> None:
        self.shift = shift
        self.session_id = "test-session"
        self.build_version = "alpha-local"
        self.sent: list[tuple[str, str]] = []
        self.payloads: list[tuple[str, dict]] = []

    async def send_text(self, text: str, source: str = "system") -> None:
        self.sent.append((source, text))

    async def send(self, msg_type: str, payload: dict) -> None:
        self.payloads.append((msg_type, payload))


def test_process_command_routes_free_text_to_patient_talk(three_cases) -> None:
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    bay = shift.bays["Bay 1"]
    bay.patient_session = _StubPatientSession()
    shift.go("1")

    session = _RecordingSession(shift)
    asyncio.run(process_command(session, "When did you last have a drink?"))

    assert bay.patient_session.messages == ["When did you last have a drink?"]
    patient_name = bay.patient_name.split()[0].upper()
    assert session.sent == [
        ("patient", f"[{patient_name}]: I had my last drink this morning."),
    ]
    assert any(
        event.actor == "attending" and event.event_type == "talk"
        for event in bay.events
    )


def test_process_command_routes_bare_disposition_alias_to_resolve(three_cases) -> None:
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    shift.bays["Bay 1"].patient_session = _StubPatientSession()
    shift.go("1")
    session = _RecordingSession(shift)

    asyncio.run(process_command(session, "admit-floor"))

    assert session.sent
    source, text = session.sent[-1]
    assert source == "system"
    assert "Too early to disposition" in text


def test_process_command_routes_exam_to_shift_exam(three_cases) -> None:
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    bay = shift.bays["Bay 1"]
    bay.patient_session = _StubPatientSession()
    shift.go("1")
    session = _RecordingSession(shift)

    asyncio.run(process_command(session, "exam chest"))

    assert bay.patient_session.exams == ["chest"]
    assert session.sent == [
        ("system", "[Exam: chest]\nFinding: focal tenderness\nPatient: Ow."),
    ]
    assert any(
        event.actor == "attending" and event.event_type == "exam"
        for event in bay.events
    )


def test_process_command_quit_always_emits_shift_ended_payload(three_cases) -> None:
    shift = Shift(cases=three_cases, residents=select_shift_roster()[:3])
    session = _RecordingSession(shift)

    asyncio.run(process_command(session, "quit"))

    assert session.sent
    assert session.sent[-1][0] == "system"
    assert session.payloads
    msg_type, payload = session.payloads[-1]
    assert msg_type == "shift_ended"
    assert payload["feedback_context"]["session_id"] == "test-session"
    assert payload["feedback_context"]["build_version"] == "alpha-local"
