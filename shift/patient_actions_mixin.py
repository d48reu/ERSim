"""Patient and chart interactions in the active bay."""

from __future__ import annotations

from .bay import Bay


class ShiftPatientActionsMixin:
    def ask_resident(self, question: str) -> str:
        """Ask the resident a question about the current case."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        # Build interaction summary from bay events
        summary = self._bay_interaction_summary(bay)

        response = bay.resident_ai.respond(
            case=bay.case,
            question=question,
            interaction_summary=summary,
        )

        res_name = bay.resident.name.split()[0]
        bay.record("attending", "resident_response",
                  question, internal=response.reasoning)
        bay.record("resident", "resident_response", response.what_they_say)

        output = [f"[{res_name.upper()}]: {response.what_they_say}"]
        if response.flags:
            # Show flags as subtle pressure — not a list, just the most urgent
            urgent = [f for f in response.flags if any(
                w in f.lower() for w in
                ["cardiac", "sepsis", "ischemi", "immediate", "emergent", "time"]
            )]
            if urgent:
                output.append(f"  [{res_name} looks concerned about: {urgent[0]}]")

        return "\n".join(output)

    def get_resident_read(self) -> str:
        """Get resident's unprompted current assessment."""
        return self.ask_resident(
            "What's your current read? What should we be doing?"
        )

    def family(self) -> str:
        """Bring family member into the current bay."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        self._tick_others(self.active_bay_id)
        self.global_turn += 1

        result = bay.patient_session.bring_family()
        bay.record("attending", "family", result)

        # Patient reacts
        pp = bay.case.patient_profile
        reaction = bay.patient_session.interact(
            f"[{pp.key_person} has entered the room]"
        )
        patient_name = bay.patient_name.split()[0]
        bay.record("patient", "family", reaction)

        return f"{result}\n[{patient_name.upper()}]: {reaction}"

    def chart(self) -> str:
        """Show what has been revealed in the current bay."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        summary = bay.patient_session.get_reveal_summary()
        lines = [f"--- CHART: {bay.patient_name} (turn {summary['turns']}) ---"]
        lines.append(f"Family present: {summary['family_present']}")

        # Pending tests
        if bay.pending_results:
            pending_names = [r[1] for r in bay.pending_results]
            lines.append(f"Pending: {', '.join(pending_names)}")

        # Completed test results — full reports here
        test_results = getattr(bay, '_test_results', {})
        if test_results:
            lines.append(f"\n--- TEST RESULTS ---")
            for test_name, full_result in test_results.items():
                lines.append(f"\n[{test_name.upper()}]")
                lines.append(full_result)
        elif summary['tests_ordered']:
            lines.append(f"Tests ordered: {', '.join(summary['tests_ordered'])} (pending)")

        # Revealed clinical info
        if summary["revealed"]:
            lines.append(f"\n--- WHAT YOU LEARNED ({len(summary['revealed'])}) ---")
            for r in summary["revealed"]:
                lines.append(f"  {r['information']}")

        if summary["locked"]:
            lines.append(f"\n--- STILL HIDDEN ({len(summary['locked'])}) ---")
            for l in summary["locked"]:
                lines.append(f"  [{l['trigger_needed']}] {l['trigger_detail']}")

        return "\n".join(lines)
