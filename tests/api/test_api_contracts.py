from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import main as api_main
from api.session import create_session


@pytest.fixture
def client(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "feedback.db"
    monkeypatch.setenv("ERSIM_FEEDBACK_DB", str(db_path))
    monkeypatch.setenv("ERSIM_FEEDBACK_EXPORT_TOKEN", "secret-token")

    async def noop_tick_loop():
        return None

    monkeypatch.setattr(api_main, "tick_loop", noop_tick_loop)

    with TestClient(api_main.app) as test_client:
        yield test_client, db_path


def test_post_session_includes_experience_mode_and_build_version(client) -> None:
    test_client, _ = client
    response = test_client.post("/session")
    assert response.status_code == 200
    payload = response.json()
    assert payload["experience_mode"] == "flagship"
    assert payload["build_version"]
    assert payload["session_id"]


def test_post_feedback_happy_path_persists_row(client) -> None:
    test_client, db_path = client
    response = test_client.post(
        "/feedback",
        json={
            "session_id": "session-123",
            "build_version": "alpha-local",
            "shift_mode": "flagship",
            "debrief_grade": "B+",
            "tester_role": "product/tech",
            "overall_rating": 4,
            "best_moment": "The trap catch landed.",
            "most_confusing_part": "The chart needed one more hint.",
            "would_you_use_again": True,
            "optional_contact": "@tester",
            "metrics": {
                "disposition_accuracy": 100.0,
                "resolved_cases": 3,
                "total_cases": 3,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE session_id = ?",
            ("session-123",),
        ).fetchone()
    assert row == (1,)


def test_post_feedback_validation_failures_return_422(client) -> None:
    test_client, _ = client
    response = test_client.post(
        "/feedback",
        json={
            "session_id": "session-123",
            "build_version": "alpha-local",
            "shift_mode": "flagship",
            "debrief_grade": "B+",
            "tester_role": "product/tech",
            "overall_rating": 4,
            "best_moment": "",
            "most_confusing_part": "Confusing part",
            "would_you_use_again": True,
            "metrics": {},
        },
    )

    assert response.status_code == 422


def test_feedback_export_requires_valid_token(client) -> None:
    test_client, _ = client

    forbidden = test_client.get("/feedback/export", params={"token": "wrong"})
    assert forbidden.status_code == 403

    allowed = test_client.get("/feedback/export", params={"token": "secret-token"})
    assert allowed.status_code == 200
    assert "created_at,session_id,build_version" in allowed.text


def test_expired_session_status_returns_404(client) -> None:
    test_client, _ = client
    session = create_session(num_bays=1, model="test-model")
    session.created_at = session.created_at - timedelta(minutes=11)

    response = test_client.get(f"/session/{session.session_id}/status")

    assert response.status_code == 404
