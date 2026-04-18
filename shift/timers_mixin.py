"""Pending results, cross-bay decisions, timers, autonomous actions."""

from __future__ import annotations

from .bay import Bay, BayStatus


class ShiftTimersMixin:
    def check_pending_results(self) -> dict:
        """
        Check all bays for test results that are now due.
        Called at the top of each game loop iteration.
        Returns dict with:
          'notifications': list of result strings to display inline
          'decisions': list of dicts for cross-bay decisions needing player response
                       {bay_id, resident_name, text, options: [{label, value}]}
        """
        notifications = []
        decisions = []
        for bay_id, bay in self.bays.items():
            if not bay.pending_results:
                continue
            due = [r for r in bay.pending_results if r[0] <= self.global_turn]
            still_pending = [r for r in bay.pending_results if r[0] > self.global_turn]
            bay.pending_results = still_pending

            if not due:
                continue

            if not hasattr(bay, '_test_results'):
                bay._test_results = {}

            # Show each result inline
            for (due_turn, test_name, full_result, bid) in due:
                bay._test_results[test_name] = full_result
                bay.record("system", "test_result", f"{test_name}: {full_result}")
                summary_line = self._summarize_result(test_name, full_result)
                bay.note_objective_change(f"{test_name}: {summary_line}")
                header = (
                    f"[{bay_id} — {bay.patient_name}]  "
                    f"{test_name.upper()}  {self._format_clock(self.global_turn)}"
                )
                next_step = self._suggest_next_step(bay, test_name, full_result)
                notifications.append(
                    f"{header}\n"
                    f"  {summary_line}\n"
                    f"  Next: {next_step}\n"
                    f"  (type 'chart' for full report)"
                )

            # Fire ONE batched pivot for all due results this turn
            if len(due) == 1:
                test_name, full_result = due[0][1], due[0][2]
                combined_name = test_name
                combined_result = full_result[:300]
            else:
                combined_name = ", ".join(r[1] for r in due)
                combined_result = "\n".join(
                    f"{r[1].upper()}: {self._summarize_result(r[1], r[2])}"
                    for r in due
                )[:400]

            interaction_summary = self._bay_interaction_summary(bay)
            pivot = bay.resident_ai.pivot_interrupt(
                case=bay.case,
                test_name=combined_name,
                test_result=combined_result,
                interaction_summary=interaction_summary,
                case_memory=bay.resident_case_memory,
            )
            if pivot.triggered and pivot.what_they_say:
                bay._pending_pivot = pivot
                bay.absorb_resident_assessment(pivot, mode="responsive")
                bay.record("resident", "pivot_interrupt", pivot.what_they_say,
                          internal=pivot.pivot_reason)

                # If this is NOT the active bay, queue as a cross-bay decision
                res_name = bay.resident.name.split()[0]
                is_cross_bay = (self.active_bay_id != bay_id)
                if is_cross_bay:
                    decisions.append({
                        "bay_id": bay_id,
                        "resident_name": res_name,
                        "patient_name": bay.patient_name,
                        "text": f"{res_name}: {pivot.what_they_say}",
                        "options": [
                            {"label": "Go ahead", "value": "1"},
                            {"label": "Redirect", "value": "2"},
                        ],
                    })
                else:
                    # Active bay — show inline as before
                    notifications.append(self._format_pivot(bay, pivot))

        return {"notifications": notifications, "decisions": decisions}

    def respond_cross_bay(self, bay_id: str, choice: int, note: str = "") -> str:
        """Respond to a cross-bay pivot decision without entering the bay."""
        bay = self.bays.get(bay_id)
        if not bay:
            return f"Bay {bay_id} not found."
        if not getattr(bay, '_pending_pivot', None):
            return f"No pending decision in {bay_id}."

        pivot = bay._pending_pivot
        res_name = bay.resident.name.split()[0]

        if choice == 1:
            # Go ahead
            bay._pending_pivot = None
            bay.note_attending_intervention(
                f"approved cross-bay pivot in {bay_id}"
            )
            # Queue any tests the resident wants to run
            if pivot.plan_tests:
                for test_name in pivot.plan_tests:
                    self._queue_test_result(bay, test_name, actor="attending")
            bay.record("attending", "approve_pivot", f"Approved {res_name}'s updated plan")
            return f"[{bay_id}] Approved {res_name}'s plan update."
        elif choice == 2:
            # Redirect — need to go to the bay to actually redirect
            bay._pending_pivot = None
            bay.note_attending_intervention(
                f"redirected cross-bay pivot in {bay_id}",
                challenged=True,
            )
            bay.record("attending", "redirect_pivot", f"Redirected {res_name}")
            return (
                f"[{bay_id}] Redirected {res_name}. "
                f"Use 'go {bay_id.split()[-1]}' to give specific instructions."
            )
        else:
            return "Choose 1 (go ahead) or 2 (redirect)."

    # ------------------------------------------------------------------
    # Timer and autonomous actions
    # ------------------------------------------------------------------

    def _tick_others(self, except_bay_id: str):
        """
        Tick all bays except the one the attending is in.
        Fire warnings at 75% threshold, autonomous actions at 100%.
        """
        for bay_id, bay in self.bays.items():
            if bay_id == except_bay_id:
                continue
            if bay.status == BayStatus.SUPERVISED:
                result = bay.tick()
                if result == 'fire':
                    self._fire_autonomous(bay_id)
                elif result == 'warning':
                    self._fire_warning(bay_id)

    def _fire_warning(self, bay_id: str):
        """Queue a warning notification — resident is getting antsy but hasn't acted yet."""
        bay = self.bays[bay_id]
        res_name = bay.resident.name.split()[0]
        acuity = bay.acuity
        remaining = bay.timer_threshold - bay.timer_ticks
        self._warning_queue.append(bay_id)
        bay.record(
            "system", "warning",
            f"{res_name} is getting antsy — acuity {acuity} case needs attention "
            f"({remaining} actions before autonomous)",
        )
        print(
            f"\n  ⚠ [{bay_id}] {res_name} is getting antsy — "
            f"acuity {acuity} case needs attention "
            f"({remaining} actions before autonomous)"
        )

    def _fire_autonomous(self, bay_id: str):
        """Resident acts autonomously. Queue notification for attending."""
        bay = self.bays[bay_id]
        bay.autonomous_fired = True
        bay.status = BayStatus.SUPERVISED  # Still supervised, action taken

        # Build case state at time of firing
        reveal_summary = bay.patient_session.get_reveal_summary()

        # Use approved plan_tests if available, else resident decides autonomously
        pending_plan = bay._pending_plan
        planned_tests = []
        if pending_plan and pending_plan.plan_tests:
            planned_tests = pending_plan.plan_tests
            bay._pending_plan = None  # Consume the plan

        case_state = {
            "known_to_resident": (
                f"Triage: {bay.triage_summary}. "
                f"Tests ordered: {', '.join(reveal_summary['tests_ordered']) or 'none'}. "
                f"Revealed so far: "
                + "; ".join(r["information"] for r in reveal_summary["revealed"])
            ),
            "actions_taken": reveal_summary["tests_ordered"],
            "pending": [l["trigger_detail"] for l in reveal_summary["locked"]],
            "planned_tests": planned_tests,  # Tell resident what was already planned
        }

        action = bay.resident_ai.act_autonomously(
            case=bay.case,
            timer_duration_minutes=bay.timer_ticks * 3,
            case_state_at_timer=case_state,
            case_memory=bay.resident_case_memory,
        )

        # If we had a plan, execute the tests silently in the background
        if planned_tests:
            prev_active = self.active_bay_id
            self.active_bay_id = bay_id  # Temporarily set active for test execution
            for test_name in planned_tests:
                self._queue_test_result(bay, test_name, actor="resident")
            self.active_bay_id = prev_active

        bay.record(
            "resident", "autonomous_action",
            action.what_they_tell_attending,
            internal=(
                f"Action: {action.action_taken} | "
                f"Not saying: {action.what_they_dont_say} | "
                f"Reasoning: {action.reasoning}"
            ),
        )

        # Store for when attending returns
        bay._pending_autonomous_report = action
        bay.autonomous_consequence_severity = getattr(
            action, "consequence_severity", "none"
        )
        self._autonomous_queue.append(bay_id)

        # Re-populate resident_opening with the update so go() shows
        # what happened, not the stale original shift-start greeting
        res_name_short = bay.resident.name.split()[0]
        bay.resident_opening = action.what_they_tell_attending
        bay._resident_opening_is_update = True  # Flag: this is a catch-up, not first visit

        res_name = bay.resident.name.split()[0]
        acuity = bay.acuity
        print(
            f"\n  !! [{bay_id}] {res_name} acted — "
            f"acuity {acuity} case unattended too long"
        )

    def check_autonomous_notifications(self) -> list[str]:
        """
        Return and clear any pending autonomous action notifications.
        Called at start of each go() so attending sees what happened.
        """
        notifications = []
        for bay_id in list(self._autonomous_queue):
            bay = self.bays[bay_id]
            if hasattr(bay, '_pending_autonomous_report'):
                action = bay._pending_autonomous_report
                res_name = bay.resident.name.split()[0]
                notifications.append(
                    f"[{bay_id} — {bay.patient_name}]\n"
                    f"{res_name}: {action.what_they_tell_attending}"
                )
                del bay._pending_autonomous_report
        self._autonomous_queue.clear()
        return notifications

    def check_warning_notifications(self) -> list[str]:
        """
        Return and clear any pending warning notifications.
        Called alongside check_autonomous_notifications().
        """
        notifications = []
        for bay_id in list(self._warning_queue):
            bay = self.bays[bay_id]
            res_name = bay.resident.name.split()[0]
            acuity = bay.acuity
            remaining = bay.timer_threshold - bay.timer_ticks
            notifications.append(
                f"[{bay_id}] {res_name} is getting antsy — "
                f"acuity {acuity} case needs attention"
            )
        self._warning_queue.clear()
        return notifications
