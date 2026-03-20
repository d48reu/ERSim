"""
Session manager — maps session_id to live Shift objects.

In-memory for now. Redis would replace this for horizontal scaling.
"""

import uuid
import json
import os
import sys
from typing import Optional
from fastapi import WebSocket

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from llm import get_model

from cases.schema import GeneratedCase
from residents.schema import make_default_roster
from shift.shift import Shift


# ---------------------------------------------------------------------------
# Active sessions
# ---------------------------------------------------------------------------

_sessions: dict[str, "GameSession"] = {}


class GameSession:
    """One player's active game state."""

    def __init__(self, shift: Shift, session_id: str):
        self.session_id = session_id
        self.shift = shift
        self.websocket: Optional[WebSocket] = None
        self.setup_complete: bool = False

    async def send(self, msg_type: str, payload: dict):
        """Push a message to the connected WebSocket client."""
        if self.websocket:
            try:
                await self.websocket.send_json({
                    "type": msg_type,
                    **payload,
                })
            except Exception:
                pass  # Client disconnected — handled elsewhere

    async def send_text(self, text: str, source: str = "system"):
        """Convenience: push a plain text message."""
        await self.send("message", {"text": text, "source": source})


def create_session(num_bays: int = 3, model: str | None = None) -> GameSession:
    """
    Create a new game session.
    Loads cases from test_output.json, builds Shift, returns session.
    """
    import random

    cases_path = os.path.join(os.path.dirname(__file__), "..", "test_output.json")
    with open(cases_path) as f:
        data = json.load(f)

    cases_raw = data.get("cases", [])
    if len(cases_raw) < num_bays:
        num_bays = len(cases_raw)

    # Bucket by acuity, randomly sample for variety
    by_acuity: dict[int, list] = {}
    for c in cases_raw:
        a = c["presenting_layer"]["acuity"]
        by_acuity.setdefault(a, []).append(c)

    if num_bays == 3 and len(cases_raw) >= num_bays:
        high  = by_acuity.get(1, []) + by_acuity.get(2, [])
        mid   = by_acuity.get(3, [])
        low   = by_acuity.get(4, []) + by_acuity.get(5, [])
        picks = []
        for bucket in [high, mid, low]:
            if bucket:
                picks.append(random.choice(bucket))
        remaining = [c for c in cases_raw if c not in picks]
        while len(picks) < num_bays and remaining:
            pick = random.choice(remaining)
            picks.append(pick)
            remaining.remove(pick)
    else:
        picks = random.sample(cases_raw, min(num_bays, len(cases_raw)))

    cases = [GeneratedCase.model_validate(c) for c in picks]
    residents = make_default_roster()
    random.shuffle(residents)

    shift = Shift(cases=cases, residents=residents, model=model)

    session_id = str(uuid.uuid4())
    session = GameSession(shift=shift, session_id=session_id)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[GameSession]:
    return _sessions.get(session_id)


def remove_session(session_id: str):
    _sessions.pop(session_id, None)
