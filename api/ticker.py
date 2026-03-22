"""
Background ticker — checks all active sessions for pending results
and autonomous actions, pushes them over WebSocket.

Runs as an asyncio task. Fires every 3 seconds.
"""

import asyncio
import logging

from . import session as session_store

logger = logging.getLogger("ersim.ticker")


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
                logger.exception(
                    "tick failed for session=%s; continuing loop",
                    session_id,
                )


async def _tick_session(session):
    """Check a single session for pending events and push them."""
    shift = session.shift

    # Test results due — now returns {notifications, decisions}
    pending = shift.check_pending_results()
    for r in pending.get("notifications", []):
        await session.send("result", {
            "text": r,
            "source": "result",
        })
    for d in pending.get("decisions", []):
        await session.send("cross_bay_decision", {
            "bay_id": d["bay_id"],
            "resident_name": d["resident_name"],
            "patient_name": d["patient_name"],
            "text": d["text"],
            "options": d["options"],
        })

    # Warning notifications (resident getting antsy)
    warnings = shift.check_warning_notifications()
    for w in warnings:
        await session.send("warning", {
            "text": w,
            "source": "resident",
        })

    # Autonomous resident actions
    notes = shift.check_autonomous_notifications()
    for note in notes:
        await session.send("autonomous", {
            "text": note,
            "source": "resident",
        })
