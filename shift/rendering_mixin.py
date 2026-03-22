"""Player-facing text assembly for bays and shift overview."""

from __future__ import annotations

from collections import Counter

from .bay import Bay
from .constants import SHIFT_DURATION_TURNS, SHIFT_MINUTES_PER_TURN


class ShiftRenderingMixin:
    def _render_shift_start(self) -> str:
        lines = [
            "",
            "=" * 60,
            "SHIFT STARTING",
            "=" * 60,
            f"{len(self.bays)} patients waiting.",
            "",
        ]
        for bay_id, bay in self.bays.items():
            acuity_label = {
                1: "IMMEDIATE", 2: "EMERGENT", 3: "URGENT",
                4: "LESS URGENT", 5: "NON-URGENT"
            }.get(bay.acuity, str(bay.acuity))
            res_name = bay.resident.name
            lines.append(
                f"  {bay_id}  [{bay.acuity} {acuity_label}]  "
                f"{bay.triage_summary[:55]}"
            )
            lines.append(f"        Resident: {res_name}")
        lines.append("")
        lines.append("Type 'go <bay>' to enter a bay.")
        lines.append("Type 'status' for overview at any time.")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _render_bay_header(self, bay: Bay) -> str:
        pp = bay.case.patient_profile
        pl = bay.case.presenting_layer
        acuity_label = {
            1: "IMMEDIATE", 2: "EMERGENT", 3: "URGENT",
            4: "LESS URGENT", 5: "NON-URGENT"
        }.get(bay.acuity, str(bay.acuity))

        lines = [
            f"\n--- {bay.bay_id}: {bay.patient_name} "
            f"[{bay.acuity} — {acuity_label}] ---",
            f"  {pl.triage_note}",
            f"  Vitals: HR {pl.vitals.hr}  "
            f"BP {pl.vitals.bp_systolic}/{pl.vitals.bp_diastolic}  "
            f"O2 {pl.vitals.o2_sat}%  "
            f"Temp {pl.vitals.temp_f}F",
            f"  Resident: {bay.resident.name}",
        ]
        return "\n".join(lines)

    def _render_status(self) -> str:
        clock = self._format_clock(self.global_turn)
        turns_left = SHIFT_DURATION_TURNS - self.global_turn
        hours_left = (turns_left * SHIFT_MINUTES_PER_TURN) // 60
        mins_left = (turns_left * SHIFT_MINUTES_PER_TURN) % 60
        lines = [f"\n--- STATUS  [{clock}  —  {hours_left}h{mins_left:02d}m remaining] ---"]
        for bay_id, bay in self.bays.items():
            marker = ">> " if bay_id == self.active_bay_id else "   "
            status_str = bay.status.value.upper()
            timer_str = f"  {bay.timer_pressure}" if bay.timer_pressure else ""
            acuity = bay.acuity
            # Show pending result count if any
            pending_str = f"  ({len(bay.pending_results)} pending)" if bay.pending_results else ""
            # Show reveal progress
            reveal_str = ""
            if bay.patient_session:
                rs = bay.patient_session.get_reveal_summary()
                revealed = len(rs.get("revealed", []))
                total = revealed + len(rs.get("locked", []))
                if total > 0:
                    reveal_str = f"  {revealed}/{total} revealed"
            lines.append(
                f"{marker}{bay_id}  [{acuity}]  {bay.patient_name:<20} "
                f"{status_str:<12}{timer_str}{pending_str}{reveal_str}"
            )
        return "\n".join(lines)

    def _render_reveal_hints(self, bay: Bay) -> str:
        """Show locked reveal trigger types when entering a bay."""
        if not bay.patient_session:
            return ""
        rs = bay.patient_session.get_reveal_summary()
        locked = rs.get("locked", [])
        if not locked:
            return ""

        revealed = len(rs.get("revealed", []))
        total = revealed + len(locked)

        # Count trigger types
        trigger_counts = Counter(l["trigger_needed"] for l in locked)
        hints = [f"{v}x {k}" for k, v in trigger_counts.items()]

        return (
            f"\n  Reveals: {revealed}/{total} unlocked"
            f"  |  Locked: {', '.join(hints)}"
        )

    def _bay_interaction_summary(self, bay: Bay) -> str:
        """Brief text summary of what's happened in a bay so far."""
        if not bay.events:
            return "No interaction yet."

        summary = bay.patient_session.get_reveal_summary() if bay.patient_session else {
            "revealed": [],
            "locked": [],
            "family_present": False,
            "turns": 0,
            "tests_ordered": [],
        }
        lines = [
            f"Reveals unlocked: {len(summary.get('revealed', []))}",
            f"Family present: {'yes' if summary.get('family_present') else 'no'}",
        ]
        tests_ordered = summary.get("tests_ordered", [])
        if tests_ordered:
            lines.append(f"Tests ordered: {', '.join(tests_ordered[:4])}")
        test_results = getattr(bay, "_test_results", {})
        if test_results:
            lines.append(f"Results back: {', '.join(list(test_results.keys())[:4])}")

        recent = bay.events[-8:]
        for e in recent:
            if e.actor == "attending":
                prefix = "ATT"
            elif e.actor == "patient":
                prefix = "PT"
            elif e.actor == "resident":
                prefix = "RES"
            else:
                prefix = "SYS"
            lines.append(f"{prefix}: {e.content[:90]}")
        return "\n".join(lines)
