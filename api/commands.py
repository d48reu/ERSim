"""
Command processor — translates player input into shift actions.

Mirrors the logic in shift/test_shift.py but returns structured
output instead of printing, so the WebSocket layer can push it.

All blocking shift methods (LLM calls) are wrapped in asyncio.to_thread
to avoid freezing the FastAPI event loop.
"""

import asyncio

from .session import GameSession


async def _bg(fn, *args):
    """Run a blocking shift method in a thread."""
    return await asyncio.to_thread(fn, *args)


async def process_command(session: GameSession, raw: str) -> None:
    """
    Parse and execute a player command.
    Pushes results back over the session's WebSocket.
    """
    shift = session.shift

    raw = raw.strip()
    if not raw:
        return

    # Strip leading slash
    if raw.startswith("/"):
        raw = raw[1:]

    # @ prefix = talk to resident
    if raw.startswith("@"):
        result = await _bg(shift.ask_resident, raw[1:].strip())
        await session.send_text(result, source="resident")
        return

    cmd = raw.lower()
    parts = cmd.split()
    first = parts[0] if parts else ""
    rest = raw[len(first):].strip()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    if first in ("go", "bay", "enter"):
        target = rest or (parts[-1] if len(parts) > 1 else "")
        result = await _bg(shift.go, target)
        await session.send_text(result, source="system")

    elif first == "leave":
        result = shift.leave()  # sync, no LLM
        await session.send_text(result, source="system")

    elif first in ("status", "overview", "floor"):
        result = shift.status()  # sync, no LLM
        await session.send_text(result, source="system")

    # ------------------------------------------------------------------
    # Plan approval / pivot responses
    # ------------------------------------------------------------------
    elif first in ("1", "2", "3", "4") and len(parts) == 1:
        n = int(first)
        bay = shift._require_active_bay()
        if bay and bay._pending_plan:
            result = await _bg(shift.approve_plan, n)
        else:
            result = await _bg(shift.follow_suggestion, n)
        await session.send_text(result, source="resident")

    elif first == "add":
        result = await _bg(shift.approve_plan, 2, rest)
        await session.send_text(result, source="resident")

    elif first == "redirect":
        result = await _bg(shift.approve_plan, 3, rest)
        await session.send_text(result, source="resident")

    # ------------------------------------------------------------------
    # In-bay actions
    # ------------------------------------------------------------------
    elif first == "exam":
        result = await _bg(shift.exam, rest)
        await session.send_text(result, source="system")

    elif first == "test":
        result = await _bg(shift.test, rest)
        await session.send_text(result, source="system")

    elif first in ("bundle", "order"):
        items = [t.strip() for t in rest.split(",") if t.strip()]
        if not items:
            await session.send_text("Usage: bundle <test1>, <test2>, ...", source="system")
        else:
            result = await _bg(shift.bundle_test, items)
            await session.send_text(result, source="system")

    elif first in ("ask",):
        result = await _bg(shift.ask_resident, rest)
        await session.send_text(result, source="resident")

    elif first in ("resident", "res"):
        result = await _bg(shift.get_resident_read)
        await session.send_text(result, source="resident")

    elif first == "family":
        result = await _bg(shift.family)
        await session.send_text(result, source="system")

    elif first == "chart":
        result = shift.chart()  # sync, no LLM
        await session.send_text(result, source="chart")

    elif first in ("resolve", "discharge", "admit", "dispo"):
        dispo = rest if rest else "discharge"
        result = await _bg(shift.resolve, dispo)
        await session.send_text(result, source="system")
        # Auto-debrief when all bays resolved
        all_resolved = all(
            b.status.value == "resolved" for b in shift.bays.values()
        )
        if all_resolved:
            debrief = shift.debrief()
            await session.send_text(debrief, source="system")
            await session.send("shift_ended", {"summary": debrief})

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    elif first in ("help", "?", "commands"):
        await session.send_text(HELP_TEXT, source="system")

    elif first in ("quit", "exit", "end"):
        debrief = shift.debrief()
        await session.send_text(debrief, source="system")
        await session.send("shift_ended", {"summary": debrief})

    else:
        # Free text = talk to patient (auto-talk when in a bay)
        if shift.active_bay_id:
            result = await _bg(shift.talk, raw)
            await session.send_text(result, source="patient")
        else:
            await session.send_text(
                "You're not in a bay. Use 'go <number>' to enter one.",
                source="system"
            )


def _build_shift_summary(shift) -> str:
    lines = ["\n--- SHIFT SUMMARY ---"]
    resolved = [b for b in shift.bays.values() if b.status.value == "resolved"]
    unresolved = [b for b in shift.bays.values() if b.status.value != "resolved"]
    lines.append(f"Resolved: {len(resolved)}/{len(shift.bays)}")
    for bay in resolved:
        lines.append(f"  {bay.bay_id}: {bay.patient_name} — {bay.disposition}")
    if unresolved:
        lines.append(f"Unresolved: {len(unresolved)}")
        for bay in unresolved:
            correct = bay.case.outcome_trajectory.disposition
            lines.append(
                f"  {bay.bay_id}: {bay.patient_name} — should have been {correct}"
            )
    return "\n".join(lines)


HELP_TEXT = """
Commands:
  go <number>       move to a bay (e.g. go 1, go 2)
  leave             step out of current bay
  status            overview of all bays and clock
  chart             full test results and revealed info
  exam <maneuver>   physical exam
  test <name>       order a single test
  bundle <t1>, <t2> order multiple tests at once
  ask <question>    ask resident a question
  @<question>       shorthand for ask
  resident          get resident's unprompted read
  family            bring family member in
  resolve <dispo>   close case (discharge/admit-floor/admit-icu/OR)
  1/2/3/4           respond to resident plan or pivot
  add <text>        approve plan + add something
  redirect <text>   change the plan direction
  quit              end shift

Free text = talk to the patient.
""".strip()
