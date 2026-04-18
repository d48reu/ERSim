from __future__ import annotations

import asyncio

from api.ticker import _tick_session


class _EndingSession:
    def __init__(self) -> None:
        self.is_ending = True
        self.shift = object()
        self.sent: list[tuple[str, dict]] = []

    async def send(self, msg_type: str, payload: dict) -> None:
        self.sent.append((msg_type, payload))


def test_tick_session_skips_sessions_marked_ending() -> None:
    session = _EndingSession()

    asyncio.run(_tick_session(session))

    assert session.sent == []
