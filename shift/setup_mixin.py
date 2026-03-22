"""Parallel resident setup and shift initialization."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from cases.interaction import PatientSession
from cases.schema import GeneratedCase
from residents.schema import Resident
from residents.resident import build_initial_resident_state

from .bay import Bay, BayStatus


class ShiftSetupMixin:
    def setup(self):
        """Initialize all bays. Call before starting the session."""
        shift_context, setup_jobs = self.prepare_setup_jobs()
        max_workers = min(4, max(1, len(setup_jobs)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(
                    build_initial_resident_state,
                    resident,
                    case,
                    self.model,
                    shift_context,
                    trap_context,
                ): bay_id
                for bay_id, resident, case, trap_context in setup_jobs
            }

            for future in as_completed(future_map):
                bay_id = future_map[future]
                resident_ai, assessment = future.result()
                self.apply_setup_result(bay_id, resident_ai, assessment)

        print(self._render_shift_start())

    def prepare_setup_jobs(self) -> tuple[dict, list[tuple[str, Resident, GeneratedCase, str]]]:
        """Initialize bay-local state and return resident-opening jobs."""
        shift_context = {
            "shift_type": "evening",
            "hours_elapsed": 0,
            "department_pressure": "moderate",
        }
        setup_jobs = []
        for bay_id, bay in self.bays.items():
            bay.patient_session = PatientSession(bay.case, model=self.model)
            setup_jobs.append((
                bay_id,
                bay.resident,
                bay.case,
                bay.trap_detail if bay.is_trap else "",
            ))
        return shift_context, setup_jobs

    def apply_setup_result(self, bay_id: str, resident_ai, assessment):
        """Attach one generated resident opening to its bay."""
        bay = self.bays[bay_id]
        bay.resident_ai = resident_ai
        bay.resident_opening = assessment.what_they_say
        bay.resident_opening_data = assessment
        bay._pending_plan = assessment
        bay.status = BayStatus.SUPERVISED
