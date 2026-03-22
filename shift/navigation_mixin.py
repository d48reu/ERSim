"""Roster, bay navigation, and floor status."""

from __future__ import annotations

from .bay import Bay, BayStatus


class ShiftNavigationMixin:
    _ARCHETYPE_FLAVOR = {
        "cowboy": "Confident, moves fast, occasionally skips steps",
        "overcalibrated": "Cautious, escalates often, safe but slow to commit",
        "academic": "Textbook-sharp, orders everything, misses the human read",
        "burning_out": "Was a star six months ago — running on autopilot now",
        "steady": "Quietly excellent, easy to underestimate, rarely wrong",
    }

    def get_roster_info(self) -> list[dict]:
        """Return roster data for the pre-shift screen."""
        roster = []
        for bay_id, bay in self.bays.items():
            r = bay.resident
            archetype = r.personality.value
            roster.append({
                "bay_id": bay_id,
                "name": r.name,
                "year": r.year.value,
                "style": self._ARCHETYPE_FLAVOR.get(archetype, archetype),
                "strengths": r.competency.strengths[:2],
                "watch_for": r.competency.blind_spots[:2],
                "backstory": r.backstory,
                "patient_name": bay.patient_name,
                "acuity": bay.case.presenting_layer.acuity.value,
                "chief_complaint": bay.case.presenting_layer.chief_complaint,
            })
        return roster
    def go(self, bay_id: str) -> str:
        """
        Attending moves to a bay.
        Ticks all other bays.
        """
        if bay_id not in self.bays:
            # Try fuzzy match — "3" matches "Bay 3"
            for bid in self.bays:
                if bay_id in bid or bid.lower().endswith(bay_id.lower()):
                    bay_id = bid
                    break
            else:
                available = ", ".join(self.bays.keys())
                return f"No bay '{bay_id}'. Available: {available}"

        bay = self.bays[bay_id]

        if bay.status == BayStatus.RESOLVED:
            return f"{bay_id} is closed — {bay.disposition}."

        # Auto-leave current bay before entering new one
        if self.active_bay_id and self.active_bay_id != bay_id:
            prev_bay = self.bays[self.active_bay_id]
            if prev_bay.status != BayStatus.RESOLVED:
                prev_bay.status = BayStatus.SUPERVISED
                prev_bay.timer_ticks = 0
                prev_bay.warning_fired = False

        # Tick all other supervised bays
        self._tick_others(bay_id)

        # Set active bay
        prev = self.active_bay_id
        self.active_bay_id = bay_id
        bay.status = BayStatus.ACTIVE
        bay.timer_ticks = 0  # Reset timer — attending is here now
        bay.warning_fired = False

        output = []

        # Show resident opening — either first-visit presentation or post-autonomous update
        if bay.resident_opening:
            res_name = bay.resident.name.split()[0]
            is_update = getattr(bay, '_resident_opening_is_update', False)
            label = f"[{res_name} — update]" if is_update else f"[{res_name} intercepts you]"
            output.append(
                f"\n{label}\n"
                f"{res_name}: {bay.resident_opening}\n"
            )
            if not is_update and not getattr(bay, "_demo_hint_shown", False):
                demo_hint = self._demo_play_hint(bay)
                if demo_hint:
                    output.append(f"[Coach] {demo_hint}\n")
                    bay._demo_hint_shown = True
            bay.resident_opening = ""
            bay._resident_opening_is_update = False
            if bay.resident_opening_data and not is_update:
                bay.record("resident", "resident_proactive",
                          bay.resident_opening_data.what_they_say,
                          internal=str(bay.resident_opening_data))

        output.append(self._render_bay_header(bay))

        # Show reveal hints — what actions might unlock new info
        reveal_hint = self._render_reveal_hints(bay)
        if reveal_hint:
            output.append(reveal_hint)

        # Show approval prompt if plan is waiting
        plan_prompt = self.get_pending_plan()
        if plan_prompt:
            output.append(plan_prompt)

        return "\n".join(output)

    def leave(self) -> str:
        """
        Attending leaves current bay.
        Bay goes to SUPERVISED — timer starts ticking.
        """
        if not self.active_bay_id:
            return "You're not in a bay."

        bay = self.bays[self.active_bay_id]
        if bay.status != BayStatus.RESOLVED:
            bay.status = BayStatus.SUPERVISED
            bay.timer_ticks = 0

        self.active_bay_id = None
        return self._render_status()
    def status(self) -> str:
        return self._render_status()
