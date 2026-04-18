from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from api.session import (
    GameSession,
    create_session,
    get_session,
    prune_expired_sessions,
    store_session,
)


def _now() -> datetime:
    return datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)


def test_create_session_stores_game_session() -> None:
    session = create_session(num_bays=1, model="test-model")
    stored = get_session(session.session_id)
    assert stored is session
    assert session.shift_mode == "flagship"
    assert session.build_version


def test_mark_connected_and_disconnected_updates_lifecycle_fields() -> None:
    start = _now()
    session = GameSession(shift=SimpleNamespace(), session_id="session-1", now=start)
    websocket = object()

    session.mark_connected(websocket=websocket, now=start + timedelta(minutes=1))
    assert session.websocket is websocket
    assert session.connected_at == start + timedelta(minutes=1)
    assert session.last_seen_at == start + timedelta(minutes=1)
    assert session.disconnected_at is None

    session.mark_disconnected(now=start + timedelta(minutes=2))
    assert session.websocket is None
    assert session.disconnected_at == start + timedelta(minutes=2)
    assert session.last_seen_at == start + timedelta(minutes=2)


def test_prune_never_connected_sessions_after_unopened_ttl() -> None:
    start = _now()
    session = GameSession(shift=SimpleNamespace(), session_id="never-opened", now=start)
    store_session(session)
    pruned = prune_expired_sessions(
        now=start + timedelta(minutes=11),
    )

    assert pruned == [("never-opened", "never_connected_ttl")]
    assert get_session("never-opened") is None


def test_prune_disconnected_sessions_after_disconnected_ttl() -> None:
    start = _now()
    session = GameSession(shift=SimpleNamespace(), session_id="disconnected", now=start)
    store_session(session)
    session.mark_connected(websocket=object(), now=start + timedelta(minutes=1))
    session.mark_disconnected(now=start + timedelta(minutes=2))

    pruned = prune_expired_sessions(
        now=start + timedelta(minutes=33),
    )

    assert pruned == [("disconnected", "disconnected_ttl")]
    assert get_session("disconnected") is None


def test_preserve_active_connected_sessions_during_prune() -> None:
    start = _now()
    session = GameSession(shift=SimpleNamespace(), session_id="connected", now=start)
    store_session(session)
    session.mark_connected(websocket=object(), now=start + timedelta(minutes=1))

    pruned = prune_expired_sessions(now=start + timedelta(hours=5))

    assert pruned == []
    assert get_session("connected") is session


class _SlowWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.inflight = 0
        self.overlap_detected = False

    async def send_json(self, payload: dict) -> None:
        self.inflight += 1
        if self.inflight > 1:
            self.overlap_detected = True
        await asyncio.sleep(0.01)
        self.sent.append(payload)
        self.inflight -= 1


def test_game_session_serializes_websocket_sends() -> None:
    session = GameSession(shift=SimpleNamespace(), session_id="send-lock")
    websocket = _SlowWebSocket()
    session.mark_connected(websocket=websocket)

    async def _run() -> None:
        await asyncio.gather(
            session.send("message", {"text": "one"}),
            session.send("message", {"text": "two"}),
        )

    asyncio.run(_run())

    assert websocket.overlap_detected is False
    assert len(websocket.sent) == 2
