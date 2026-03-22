"""Disposition, coaching hints, and bay guidance."""

from __future__ import annotations

from cases.demo_cases import get_demo_case_meta

from .bay import Bay, BayStatus


class ShiftResolveMixin:
    @staticmethod
    def _dispo_category(norm: str) -> str:
        """Group normalized dispositions into categories for mismatch grading."""
        admit_levels = {"admitfloor", "admiticu"}
        if norm in admit_levels:
            return "admit"
        if norm == "discharge":
            return "discharge"
        # OR, cath-lab, transfer, AMA are each their own direction
        return norm

    @classmethod
    def _dispo_mismatch_type(cls, player: str, correct: str) -> str:
        """Classify a disposition mismatch. Returns: wrong_level, wrong_direction, or other."""
        pc = cls._dispo_category(player)
        cc = cls._dispo_category(correct)
        if pc == cc:
            # Same category but different specific dispo (e.g., admit-floor vs admit-icu)
            return "wrong_level"
        else:
            return "wrong_direction"

    def resolve(self, disposition: str, note: str = "") -> str:
        """
        Close a case. Disposition: discharge, admit-floor, admit-icu,
        OR, cath-lab, transfer, AMA.
        """
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        summary = bay.patient_session.get_reveal_summary()
        completed_results = len(getattr(bay, '_test_results', {}))
        revealed_count = len(summary.get("revealed", []))
        engagement_turns = summary.get("turns", 0)
        family_present = summary.get("family_present", False)
        attending_actions = sum(
            1 for event in bay.events
            if event.actor == "attending" and event.event_type != "resolve"
        )

        if attending_actions == 0:
            return (
                "Too early to disposition this patient.\n"
                "You haven't done anything in this bay yet. Talk to the patient, examine them, "
                "order something, or bring in family before locking in a disposition."
            )

        bay.status = BayStatus.RESOLVED
        bay.disposition = disposition
        bay.resolution_note = note
        bay.record("attending", "resolve", f"{disposition}: {note}")
        bay.low_evidence_disposition = (
            completed_results == 0 and revealed_count <= 1 and not family_present and engagement_turns < 4
        )

        # Compare to correct disposition — normalize both sides
        correct = bay.case.outcome_trajectory.disposition
        patient_name = bay.patient_name

        def _norm_dispo(s: str) -> str:
            """Normalize disposition strings for comparison.
            Handles: admit-icu, admit-ICU, ICU, admit_icu, admiticu, etc."""
            s = s.lower().replace("-", "").replace("_", "").replace(" ", "")
            # Canonical aliases
            aliases = {
                "admiticu": "admiticu",
                "icu": "admiticu",
                "admitfloor": "admitfloor",
                "floor": "admitfloor",
                "admit": "admitfloor",
                "discharge": "discharge",
                "discharged": "discharge",
                "home": "discharge",
                "transfer": "transfer",
                "ortho": "or",
                "or": "or",
                "cathlab": "cathlab",
                "cath": "cathlab",
                "ama": "ama",
            }
            return aliases.get(s, s)

        player_dispo = _norm_dispo(disposition)
        correct_dispo = _norm_dispo(correct)

        lines = [f"[{bay.bay_id}] {patient_name} — {disposition.upper()}"]

        if bay.low_evidence_disposition:
            lines.append("  Thin chart — you locked in a disposition with limited evidence.")
            demo_warning = self._demo_dispo_warning(bay)
            if demo_warning:
                lines.append(f"  Coaching: {demo_warning}")

        if player_dispo == correct_dispo:
            lines.append(f"  Correct disposition.")
            lines.append(f"  Outcome: {bay.case.outcome_trajectory.correct_outcome}")
        else:
            # Determine severity of the mismatch
            mismatch = self._dispo_mismatch_type(player_dispo, correct_dispo)
            if mismatch == "wrong_level":
                # Admitted but to wrong level — not a disaster
                lines.append(f"  Should have been: {correct}")
                if player_dispo == "admiticu" and correct_dispo == "admitfloor":
                    lines.append(
                        f"  Outcome: Patient stabilized and didn't require ICU-level care. "
                        f"Appropriate caution — the ICU bed wasn't needed, but no harm done. "
                        f"Transferred to floor after 6 hours."
                    )
                elif player_dispo == "admitfloor" and correct_dispo == "admiticu":
                    lines.append(
                        f"  Outcome: Patient decompensated on the floor overnight. "
                        f"Rapid response called at 3am, upgraded to ICU. "
                        f"Delay in escalation may have worsened outcome."
                    )
                else:
                    lines.append(
                        f"  Outcome: Patient admitted to a different level than optimal. "
                        f"Course corrected during hospitalization."
                    )
            elif mismatch == "wrong_direction":
                # Discharged when should have been admitted, or vice versa
                lines.append(f"  Should have been: {correct}")
                lines.append(
                    f"  Outcome: {bay.case.outcome_trajectory.missed_diagnosis}"
                )
            else:
                # Other mismatch (OR vs cath-lab, etc.)
                lines.append(f"  Should have been: {correct}")
                lines.append(
                    f"  Outcome: {bay.case.outcome_trajectory.missed_diagnosis}"
                )

        self.active_bay_id = None
        lines.append(self._render_status())
        return "\n".join(lines)

    def get_bay_guidance(self, bay_id: str) -> str:
        """Short, player-facing coaching hint for the active bay."""
        bay = self.bays.get(bay_id)
        if not bay or bay.status == BayStatus.RESOLVED:
            return ""

        summary = bay.patient_session.get_reveal_summary() if bay.patient_session else {}
        revealed = len(summary.get("revealed", []))
        pending_results = len(bay.pending_results)

        if pending_results > 0:
            if bay.case.case_id == "SHIFT_20260317_0118_02":
                return "Hip imaging is in flight. Once fracture is confirmed, close this decisively and free your attention."
            return "A result is already in flight here. Consider using the time on another bay unless the patient is changing."
        if revealed == 0:
            demo_hint = self._demo_play_hint(bay)
            if demo_hint:
                return demo_hint
            return "Start with one concrete question and one focused exam or test before you trust the resident's frame."

        locked = summary.get("locked", [])
        if locked:
            next_trigger = locked[0]
            trigger = next_trigger.get("trigger", "")
            if trigger == "direct_question":
                return "There is still history here that will only open if you ask a more specific question."
            if trigger == "family_present":
                return "If the story still feels incomplete, consider bringing family in."
            if trigger == "physical_exam":
                return "There is still something to earn on exam before this case is fully read."

        return "Pressure-test the current story before disposition. Do not let a smooth presentation substitute for evidence."

    def _demo_play_hint(self, bay: Bay) -> str:
        return get_demo_case_meta(bay.case.case_id).get("play_hint", "")

    def _demo_dispo_warning(self, bay: Bay) -> str:
        return get_demo_case_meta(bay.case.case_id).get("dispo_warning", "")
