"""
Background ticker — checks all active sessions for pending results
and autonomous actions, pushes them over WebSocket.

Runs as an asyncio task. Fires every 3 seconds.
"""

import asyncio
from . import session as session_store


async def tick_loop():
    """
    Main background loop. Runs forever while the server is up.
    Every 3 seconds, checks all sessions for:
    - Pending test results that are now due
    - Autonomous resident actions
    """
    while True:
        await asyncio.sleep(3)
        for session_id, session in list(session_store._sessions.items()):
            if not session.websocket:
                continue
            try:
                await _tick_session(session)
            except Exception:
                pass  # Don't let one broken session kill the loop


async def _tick_session(session):
    """Check a single session for pending events and push them."""
    shift = session.shift

    # Test results due
    results = shift.check_pending_results()
    for r in results:
        await session.send("result", {
            "text": r,
            "source": "result",
        })

    # Autonomous resident actions
    notes = shift.check_autonomous_notifications()
    for note in notes:
        await session.send("autonomous", {
            "text": note,
            "source": "resident",
        })
