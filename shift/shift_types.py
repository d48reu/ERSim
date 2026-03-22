"""Lightweight shift state snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ShiftStatus:
    """Snapshot of the current shift state."""
    active_bay: Optional[str]
    bays: list
    global_turn: int
    shift_elapsed_actions: int
