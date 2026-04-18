"""End-of-shift debrief, grading, and teaching moments."""

from __future__ import annotations

import re

from .bay import Bay


class ShiftDebriefMixin:
    @staticmethod
    def _debrief_excerpt(text: str, max_chars: int = 140) -> str:
        compact = re.sub(r"\s+", " ", (text or "")).strip()
        if len(compact) <= max_chars:
            return compact

        sentence_endings = [". ", "! ", "? "]
        best_cut = 0
        for ending in sentence_endings:
            idx = compact.rfind(ending, 0, max_chars)
            if idx > best_cut:
                best_cut = idx + 1
        if best_cut:
            return compact[:best_cut].strip()

        truncated = compact[:max_chars].rsplit(" ", 1)[0].strip()
        return f"{truncated or compact[:max_chars].strip()}..."

    def _clinical_depth_score(self, bay: Bay) -> float:
        """Estimate whether the attending built enough signal before closing."""
        if not bay.patient_session:
            return 0.0
        summary = bay.patient_session.get_reveal_summary()
        revealed = len(summary.get("revealed", []))
        total = revealed + len(summary.get("locked", []))
        reveal_ratio = (revealed / total) if total else 0.0
        attending_actions = sum(
            1 for e in bay.events
            if e.actor == "attending" and e.event_type != "resolve"
        )
        completed_results = len(getattr(bay, "_test_results", {}))
        challenged_plan = any(
            e.actor == "attending" and (
                e.event_type in ("pivot_redirected", "redirect_pivot")
                or (e.event_type == "approve_plan" and any(
                    word in e.content.lower() for word in ("held plan", "redirected", "approved + added")
                ))
            )
            for e in bay.events
        )

        did_direct_work = any(
            e.actor == "attending" and e.event_type in ("attend", "exam", "family", "resident_response")
            for e in bay.events
        )
        pending_results = len(getattr(bay, "pending_results", []))

        score = 0.0
        score += min(0.35, reveal_ratio * 0.35)
        score += min(0.15, (min(attending_actions, 3) / 3) * 0.15)
        if completed_results > 0:
            score += 0.20
        if did_direct_work:
            score += 0.10
        if summary.get("family_present") or revealed >= 2:
            score += 0.10
        if challenged_plan:
            score += 0.10
        if pending_results > 0 and (completed_results > 0 or revealed >= 2):
            score += 0.05
        return min(1.0, score)

    def _trap_catch_quality(self, bay: Bay, is_resolved: bool, dispo_correct: bool) -> tuple[str, list[str]]:
        """
        Classify trap handling.
        Returns one of: full, partial, missed, unresolved.
        """
        if not bay.is_trap:
            return "none", []

        summary = bay.patient_session.get_reveal_summary() if bay.patient_session else {}
        revealed = len(summary.get("revealed", []))
        completed_results = len(getattr(bay, "_test_results", {}))

        reasons = []
        if any(
            e.actor == "attending" and e.event_type == "approve_plan" and "held plan" in e.content.lower()
            for e in bay.events
        ):
            reasons.append("held the resident plan to gather your own signal")
        if any(
            e.actor == "attending" and e.event_type == "approve_plan"
            and any(word in e.content.lower() for word in ("redirected", "approved + added"))
            for e in bay.events
        ):
            reasons.append("changed or added to the resident's plan")
        if any(
            e.actor == "attending" and e.event_type in ("attend", "exam", "family")
            for e in bay.events
        ):
            reasons.append("did direct attending-side information gathering")
        if revealed >= 2:
            reasons.append("opened more than one reveal in the bay")
        if completed_results > 0:
            reasons.append("used objective data before closing")

        if not is_resolved:
            return "unresolved", reasons
        if not dispo_correct:
            return "missed", reasons
        if len(reasons) >= 3:
            return "full", reasons
        if len(reasons) >= 1:
            return "partial", reasons
        return "partial", reasons

    # ------------------------------------------------------------------
    # End-of-Shift Debrief
    # ------------------------------------------------------------------

    def debrief(self) -> str:
        """
        Generate end-of-shift report card.
        Call when all bays are resolved or player quits.
        """
        lines = [
            "",
            "=" * 60,
            "SHIFT DEBRIEF",
            "=" * 60,
            "",
        ]

        total_bays = len(self.bays)
        resolved_bays = 0
        correct_dispositions = 0
        traps_caught = 0
        traps_partial = 0
        traps_total = 0
        total_turns_in_bay = 0
        autonomous_fires = 0
        consequences_major = 0
        warnings_heeded = 0
        warnings_ignored = 0  # warned but still fired autonomously
        bay_turn_counts = {}
        thin_chart_dispositions = 0
        process_scores = []
        showcase_highlights = []
        showcase_lowlights = []

        for bay_id, bay in self.bays.items():
            pp = bay.case.patient_profile
            pl = bay.case.presenting_layer
            mt = bay.case.medical_truth
            ot = bay.case.outcome_trajectory
            res_name = bay.resident.name.split()[0]

            # Count turns spent in this bay
            turns_here = sum(1 for e in bay.events if e.actor == "attending")
            bay_turn_counts[bay_id] = turns_here
            total_turns_in_bay += turns_here

            is_resolved = bay.status.value == "resolved"
            if is_resolved:
                resolved_bays += 1
                if getattr(bay, "low_evidence_disposition", False):
                    thin_chart_dispositions += 1
            process_scores.append(self._clinical_depth_score(bay))

            # Header
            if is_resolved:
                correct_dispo = ot.disposition
                player_dispo = bay.disposition or ""

                def _norm(s):
                    s = s.lower().replace("-", "").replace("_", "").replace(" ", "")
                    aliases = {
                        "admiticu": "admiticu", "icu": "admiticu",
                        "admitfloor": "admitfloor", "floor": "admitfloor",
                        "admit": "admitfloor", "discharge": "discharge",
                        "discharged": "discharge", "home": "discharge",
                        "transfer": "transfer", "or": "or", "ortho": "or",
                        "cathlab": "cathlab", "cath": "cathlab", "ama": "ama",
                    }
                    return aliases.get(s, s)

                norm_player = _norm(player_dispo)
                norm_correct = _norm(correct_dispo)
                dispo_correct = norm_player == norm_correct
                dispo_mismatch = None if dispo_correct else self._dispo_mismatch_type(norm_player, norm_correct)
                thin_chart = getattr(bay, "low_evidence_disposition", False)
                if dispo_correct:
                    # Thin-chart correct dispo: right call, but unsupported by
                    # returned results / reveals / family. Half credit — a
                    # coin-flip that landed, not a judgment that was earned.
                    correct_dispositions += 0.5 if thin_chart else 1
                    mark = "~" if thin_chart else "OK"
                elif dispo_mismatch == "wrong_level":
                    # Partial credit for right direction, wrong level
                    correct_dispositions += 0.5
                    mark = "~"
                else:
                    mark = "XX"

                lines.append(
                    f"  {bay_id}: {bay.patient_name} — "
                    f"{player_dispo.upper()} [{mark}]"
                )
            else:
                lines.append(
                    f"  {bay_id}: {bay.patient_name} — UNRESOLVED"
                )

            # Human-readable ground truth
            lines.append(f"    What was really going on: {mt.true_diagnosis}")

            # Disposition accuracy
            if is_resolved:
                if dispo_correct:
                    lines.append(
                        f"    Outcome: {ot.correct_outcome}"
                    )
                elif dispo_mismatch == "wrong_level":
                    lines.append(
                        f"    Should have been: {ot.disposition}"
                    )
                    if norm_player == "admiticu" and norm_correct == "admitfloor":
                        lines.append(
                            f"    Outcome: ICU bed wasn't needed. Transferred to floor after 6 hours. No harm done."
                        )
                    elif norm_player == "admitfloor" and norm_correct == "admiticu":
                        lines.append(
                            f"    Outcome: Decompensated on the floor. Rapid response at 3am, upgraded to ICU."
                        )
                    else:
                        lines.append(
                            f"    Outcome: Admitted to suboptimal level. Course corrected during stay."
                        )
                else:
                    lines.append(
                        f"    Should have been: {ot.disposition}"
                    )
                    lines.append(
                        f"    Consequence: {ot.missed_diagnosis}"
                    )

            # Trap case
            if bay.is_trap:
                traps_total += 1
                catch_quality, trap_reasons = self._trap_catch_quality(
                    bay, is_resolved, dispo_correct if is_resolved else False
                )
                # Did the attending override the resident's read?
                # Check if there was a redirect/push-back event
                attending_intervened = any(
                    e.event_type in ("redirect", "approve_modified", "talk")
                    and e.actor == "attending"
                    for e in bay.events
                )
                if catch_quality == "full":
                    traps_caught += 1
                    showcase_highlights.append(
                        f"Trap caught in {bay_id}: you overruled {res_name}'s blind spot and landed {mt.true_diagnosis}."
                    )
                    if trap_reasons:
                        lines.append(f"    How: {trap_reasons[0]}")
                    lines.append(
                        f"    ** TRAP CASE — You caught it. "
                        f"{res_name}'s blind spot: {self._debrief_excerpt(bay.trap_detail, max_chars=110)}"
                    )
                elif catch_quality == "partial":
                    showcase_lowlights.append(
                        f"Trap only partially recovered in {bay_id}: final dispo landed, but the resident frame was only lightly challenged."
                    )
                    lines.append(
                        f"    ** TRAP CASE - Recovered correctly, but with limited explicit challenge. "
                        f"Blind spot: {self._debrief_excerpt(bay.trap_detail, max_chars=110)}"
                    )
                    traps_partial += 1
                    if trap_reasons:
                        lines.append(f"    How: {trap_reasons[0]}")
                elif is_resolved:
                    showcase_lowlights.append(
                        f"Trap missed in {bay_id}: {res_name}'s read pulled the shift off the true diagnosis."
                    )
                    lines.append(
                        f"    ** TRAP CASE — Missed. "
                        f"{res_name} led you wrong. "
                        f"Blind spot: {self._debrief_excerpt(bay.trap_detail, max_chars=110)}"
                    )
                else:
                    lines.append(
                        f"    ** TRAP CASE — Unresolved. "
                        f"{res_name}'s read may have been off."
                    )

            # Autonomous action
            if bay.autonomous_fired:
                autonomous_fires += 1
                report = getattr(bay, '_pending_autonomous_report', None)
                # Also check events for autonomous action records
                auto_events = [e for e in bay.events
                               if e.event_type == "autonomous_action"]
                if auto_events:
                    last_auto = auto_events[-1]
                    lines.append(
                        f"    Resident moved without you: {res_name} acted - "
                        f"{self._debrief_excerpt(last_auto.content, max_chars=110)}"
                    )
                    # Check severity from bay record
                    sev = bay.autonomous_consequence_severity
                    if sev in ("major", "critical"):
                        consequences_major += 1
                        showcase_lowlights.append(
                            f"{bay_id} escalated while unattended: {res_name} acted alone and the consequence was {sev}."
                        )
                        lines.append(
                            f"    !! CONSEQUENCE ({sev.upper()})"
                        )

            # Warning tracking: heeded vs ignored
            had_warning = any(e.event_type == "warning" for e in bay.events)
            if had_warning and not bay.autonomous_fired:
                warnings_heeded += 1
                lines.append(
                    f"    Warning heeded — no autonomous fire"
                )
            elif had_warning and bay.autonomous_fired:
                warnings_ignored += 1

            # Reveal count
            if bay.patient_session:
                reveal_summary = bay.patient_session.get_reveal_summary()
                revealed = len(reveal_summary.get("revealed", []))
                total_reveals = revealed + len(reveal_summary.get("locked", []))
                lines.append(
                    f"    Reveals: {revealed}/{total_reveals} unlocked"
                )
                if getattr(bay, "low_evidence_disposition", False):
                    lines.append("    Closed with limited evidence")
                    showcase_lowlights.append(
                        f"{bay_id} was closed on a thin chart before enough signal was collected."
                    )

            # Teaching moment
            teaching = self._teaching_moment(bay, is_resolved, dispo_correct if is_resolved else False)
            if teaching:
                lines.append(f"    >> {teaching}")

            # Time
            lines.append(f"    Attending turns: {turns_here}")
            lines.append(f"    Resident: {bay.resident.name}")
            lines.append("")

        # --- Shift-level grades ---
        lines.append("-" * 40)

        # Disposition accuracy
        if resolved_bays > 0:
            dispo_pct = correct_dispositions / resolved_bays * 100
            # Format: show as "2.5/3" if fractional, "2/3" if integer
            cd_str = f"{correct_dispositions:g}"
            lines.append(
                f"  Disposition accuracy: "
                f"{cd_str}/{resolved_bays} "
                f"({dispo_pct:.0f}%)"
            )
        else:
            dispo_pct = 0
            lines.append("  Disposition accuracy: no cases resolved")

        # Resolution rate
        lines.append(
            f"  Cases resolved: {resolved_bays}/{total_bays}"
        )

        # Attention distribution
        attention_balanced = False
        if bay_turn_counts and total_turns_in_bay > 0:
            max_turns = max(bay_turn_counts.values())
            attention_pct = max_turns / total_turns_in_bay * 100
            if attention_pct > 70:
                attn_grade = "poor (tunnel vision)"
            elif attention_pct > 50:
                attn_grade = "uneven"
            else:
                attn_grade = "balanced"
                attention_balanced = True
            lines.append(
                f"  Attention distribution: {attn_grade} "
                f"(heaviest bay: {attention_pct:.0f}%)"
            )

        # Trap performance
        if traps_total > 0:
            lines.append(
                f"  Trap cases fully caught: {traps_caught}/{traps_total}"
            )
            if traps_partial > 0:
                lines.append(
                    f"  Trap cases partially recovered: {traps_partial}/{traps_total}"
                )

        process_pct = (sum(process_scores) / len(process_scores) * 100) if process_scores else 0
        lines.append(f"  Clinical depth: {process_pct:.0f}/100")

        resolved_rate_val = resolved_bays / total_bays * 100 if total_bays else 0
        warning_bonus = warnings_heeded * 2
        attention_bonus_applied = (
            attention_balanced
            and autonomous_fires == 0
            and process_pct >= 60
        )
        clean_sheet_bonus_applied = (
            autonomous_fires == 0
            and dispo_pct == 100
            and resolved_rate_val == 100
            and thin_chart_dispositions == 0
            and process_pct >= 70
            and (traps_total == 0 or traps_caught == traps_total)
        )

        if thin_chart_dispositions > 0:
            lines.append(
                f"  Thin-chart dispositions: {thin_chart_dispositions} "
                f"(half dispo credit — no returned results, <2 reveals, no family)"
            )

        # Autonomous fires
        if autonomous_fires > 0:
            lines.append(
                f"  Autonomous actions: {autonomous_fires} "
                f"({consequences_major} with major consequences)"
            )

        # Warnings heeded (warning fired but player intervened before autonomous)
        if warnings_heeded > 0:
            lines.append(
                f"  Warnings heeded: {warnings_heeded} "
                f"(+{warning_bonus} pts)"
            )

        # Attention bonus
        if attention_bonus_applied:
            lines.append(
                f"  Attention bonus: +5 pts (balanced coverage)"
            )

        # Clean sheet check
        if clean_sheet_bonus_applied:
            lines.append(
                f"  Clean sheet bonus: +8 pts"
            )

        # Overall grade
        grade = self._compute_grade(
            dispo_pct=dispo_pct,
            resolved_rate=resolved_rate_val,
            traps_caught=traps_caught,
            traps_partial=traps_partial,
            traps_total=traps_total,
            process_score=process_pct,
            consequences_major=consequences_major,
            autonomous_fires=autonomous_fires,
            warnings_heeded=warnings_heeded,
            warnings_ignored=warnings_ignored,
            attention_balanced=attention_balanced,
            thin_chart_dispositions=thin_chart_dispositions,
        )
        headline = self._debrief_headline(
            grade=grade,
            traps_caught=traps_caught,
            traps_total=traps_total,
            consequences_major=consequences_major,
            thin_chart_dispositions=thin_chart_dispositions,
            resolved_bays=resolved_bays,
            total_bays=total_bays,
        )
        next_rep = self._next_rep_focus(
            traps_caught=traps_caught,
            traps_total=traps_total,
            autonomous_fires=autonomous_fires,
            thin_chart_dispositions=thin_chart_dispositions,
            attention_balanced=attention_balanced,
            resolved_bays=resolved_bays,
            total_bays=total_bays,
        )
        lines.insert(4, f"Headline: {headline}")
        lines.insert(5, "")
        insert_at = 6
        if showcase_highlights:
            lines.insert(insert_at, f"Highlight: {showcase_highlights[0]}")
            insert_at += 1
        if showcase_lowlights:
            lines.insert(insert_at, f"Watchout: {showcase_lowlights[0]}")
            insert_at += 1
        lines.insert(insert_at, f"Next rep: {next_rep}")
        lines.insert(insert_at + 1, "")
        lines.append("")
        lines.append(f"  SHIFT GRADE: {grade}")
        lines.append("=" * 60)

        self._last_debrief_meta = {
            "headline": headline,
            "highlight": showcase_highlights[0] if showcase_highlights else "",
            "watchout": showcase_lowlights[0] if showcase_lowlights else "",
            "next_rep": next_rep,
            "grade": grade,
            "shift_mode": "flagship",
            "metrics": {
                "disposition_accuracy": round(dispo_pct, 1),
                "resolved_cases": resolved_bays,
                "total_cases": total_bays,
                "clinical_depth": round(process_pct, 1),
                "trap_cases_fully_caught": traps_caught,
                "trap_cases_partially_recovered": traps_partial,
                "autonomous_actions": autonomous_fires,
                "warnings_heeded": warnings_heeded,
                "attention_distribution": attn_grade if bay_turn_counts and total_turns_in_bay > 0 else "unknown",
            },
        }

        return "\n".join(lines)
    def _debrief_headline(
        self,
        grade: str,
        traps_caught: int,
        traps_total: int,
        consequences_major: int,
        thin_chart_dispositions: int,
        resolved_bays: int,
        total_bays: int,
    ) -> str:
        if resolved_bays == total_bays and traps_total > 0 and traps_caught == traps_total and consequences_major == 0:
            return "Strong supervisory shift. You caught the key resident blind spot and kept the department stable."
        if consequences_major > 0:
            return "The shift got away from you in at least one bay. The main story is delayed intervention under pressure."
        if thin_chart_dispositions > 0:
            return "Clinical instincts landed some calls, but the shift leaned too hard on early closure."
        if resolved_bays < total_bays:
            return "You stabilized part of the board, but the shift ended with unfinished work still on the table."
        if grade.startswith("A") or grade.startswith("B"):
            return "Solid shift. The decisions mostly held up and the supervision loop is starting to click."
        return "Mixed shift. The right framework is there, but the execution still feels one question short."

    def _next_rep_focus(
        self,
        traps_caught: int,
        traps_total: int,
        autonomous_fires: int,
        thin_chart_dispositions: int,
        attention_balanced: bool,
        resolved_bays: int,
        total_bays: int,
    ) -> str:
        if thin_chart_dispositions > 0:
            return "Before disposition, get one more human clue or one more objective datapoint."
        if autonomous_fires > 0:
            return "Treat warnings as interrupts, not background noise. Check back in before residents act alone."
        if traps_total > 0 and traps_caught < traps_total:
            return "When a resident sounds smooth, ask what they may be underweighting before you sign off."
        if not attention_balanced:
            return "Spread attending turns earlier so one bay does not consume the whole board."
        if resolved_bays < total_bays:
            return "Close the loop faster on lower-complexity bays so the shift reaches a cleaner finish."
        return "Keep the same rhythm: hear the resident, pressure-test the story, then close with evidence."
    _ARCHETYPE_TENDENCIES = {
        "cowboy": "act faster and check less",
        "overcalibrated": "escalate everything and freeze on disposition",
        "academic": "order more tests and delay decisive action",
        "burning_out": "do the minimum and miss nuance",
        "steady": "understate urgency — listen carefully when they hedge",
    }

    def _teaching_moment(self, bay: Bay, is_resolved: bool, dispo_correct: bool) -> str:
        """Generate a one-line teaching moment for the debrief."""
        ot = bay.case.outcome_trajectory
        mt = bay.case.medical_truth
        res_name = bay.resident.name.split()[0]
        archetype = bay.resident.personality.value

        # Trap missed — most important teaching moment
        if bay.is_trap and is_resolved and not dispo_correct:
            # Find first locked reveal that could have caught it
            clue = ""
            if bay.patient_session:
                rs = bay.patient_session.get_reveal_summary()
                locked = rs.get("locked", [])
                if locked:
                    detail = self._debrief_excerpt(locked[0]["trigger_detail"], max_chars=80)
                    clue = f" Asking about '{detail}' would have surfaced it."
            return (
                f"The clue: {self._debrief_excerpt(mt.classic_miss_reason)}.{clue}"
            )

        # Trap caught — positive reinforcement
        if bay.is_trap and is_resolved and dispo_correct:
            return f"Good catch. {self._debrief_excerpt(bay.case.narrative_hook)}"

        # Wrong dispo (not a trap) — show what was missed
        if is_resolved and not dispo_correct:
            key_finding = mt.supporting_findings[0] if mt.supporting_findings else mt.classic_miss_reason
            return (
                f"Key finding: {self._debrief_excerpt(key_finding, max_chars=110)} "
                f"Correct path: {self._debrief_excerpt(ot.correct_treatment, max_chars=120)}"
            )

        # Autonomous fired — archetype-specific advice
        if bay.autonomous_fired:
            tendency = self._ARCHETYPE_TENDENCIES.get(archetype, "")
            if tendency:
                return (
                    f"{res_name} ({archetype}) under pressure tends to {tendency}. "
                    f"Check in earlier next time."
                )

        # Unresolved — flag what's still pending
        if not is_resolved:
            return f"Still needs: {self._debrief_excerpt(ot.correct_treatment, max_chars=140)}"

        # All correct, no drama — just the human story
        return self._debrief_excerpt(bay.case.narrative_hook)
    def _compute_grade(
        self,
        dispo_pct: float,
        resolved_rate: float,
        traps_caught: int,
        traps_partial: int,
        traps_total: int,
        process_score: float,
        consequences_major: int,
        autonomous_fires: int,
        warnings_heeded: int = 0,
        warnings_ignored: int = 0,
        attention_balanced: bool = False,
        thin_chart_dispositions: int = 0,
    ) -> str:
        """Compute letter grade from shift metrics.

        Scoring breakdown (max ~100+ with bonuses):
          - Disposition accuracy: 45 pts (core clinical skill)
          - Resolution rate:      15 pts
          - Trap catch:           20 pts (key mechanic)
          - Clean sheet bonus:    15 pts (no fires + perfect dispo + 100% resolved)
          - Near-clean bonus:      5 pts (no major consequences even with fires)
          - Attention bonus:       5 pts (heaviest bay < 50% of turns)
          - Warning heeded:        3 pts each (warning that didn't escalate)
          - Autonomous fire:      -2 pts each
          - Major consequence:    -5 pts if warning was ignored, -3 pts otherwise
        """
        score = 0.0

        score += (dispo_pct / 100) * 35
        score += (resolved_rate / 100) * 15

        if traps_total > 0:
            trap_credit = traps_caught + (traps_partial * 0.25)
            score += (trap_credit / traps_total) * 15
        else:
            score += 10

        score += (process_score / 100) * 20

        warned_consequences = min(consequences_major, warnings_ignored)
        unwarned_consequences = consequences_major - warned_consequences
        score -= warned_consequences * 5.0
        score -= unwarned_consequences * 3.0
        score -= autonomous_fires * 2.0
        # Thin-chart penalty lives in dispo_pct now (half credit per bay), so
        # no additional subtraction here. The thin_chart_dispositions counter
        # is still used to gate the clean-sheet bonus below.

        if attention_balanced and autonomous_fires == 0 and process_score >= 60:
            score += 5
        score += warnings_heeded * 2

        if (
            autonomous_fires == 0
            and dispo_pct == 100
            and resolved_rate == 100
            and thin_chart_dispositions == 0
            and process_score >= 70
            and (traps_total == 0 or traps_caught == traps_total)
        ):
            score += 8
        if (
            consequences_major == 0
            and autonomous_fires > 0
            and dispo_pct == 100
            and process_score >= 55
        ):
            score += 3

        if score >= 85:
            return "A"
        elif score >= 75:
            return "B+"
        elif score >= 65:
            return "B"
        elif score >= 55:
            return "C+"
        elif score >= 45:
            return "C"
        elif score >= 35:
            return "D"
        else:
            return "F"
