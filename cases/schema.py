from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class AcuityLevel(int, Enum):
    IMMEDIATE = 1    # life threatening, act now
    EMERGENT = 2     # high risk, act fast
    URGENT = 3       # stable but needs care soon
    LESS_URGENT = 4  # minor, can wait
    NON_URGENT = 5   # could be elsewhere


class RevealTrigger(str, Enum):
    VOLUNTEERED = "volunteered"
    DIRECT_QUESTION = "direct_question"
    TRUST_ESTABLISHED = "trust_established"
    TEST_RESULT = "test_result"
    FAMILY_PRESENT = "family_present"
    PHYSICAL_EXAM = "physical_exam"
    PROLONGED_STAY = "prolonged_stay"


class RevealNode(BaseModel):
    trigger: RevealTrigger
    trigger_detail: str = Field(
        description="Specific condition — e.g. 'asked directly about alcohol' "
                    "or 'troponin result returned'. Be precise."
    )
    information: str = Field(
        description="The actual fact being revealed. Clinical and specific."
    )
    patient_language: str = Field(
        description="Exactly how this patient says or shows it. "
                    "In their voice, not medical language."
    )
    emotional_register: str = Field(
        description="How they feel in the moment of revealing this. "
                    "Specific, not generic."
    )


class Vitals(BaseModel):
    hr: int
    bp_systolic: int
    bp_diastolic: int
    rr: int
    temp_f: float
    o2_sat: int
    gcs: Optional[int] = None


class PresentingLayer(BaseModel):
    chief_complaint: str
    age: int
    sex: Literal["M", "F"]
    vitals: Vitals
    triage_note: str = Field(
        description="One sentence. Clinical shorthand. All the attending gets initially."
    )
    acuity: AcuityLevel
    arrival_method: Literal[
        "walk-in", "ambulance", "police", "family drop-off", "self-referral"
    ]
    time_in_waiting_room_minutes: int


class MedicalTruth(BaseModel):
    true_diagnosis: str
    supporting_findings: List[str]
    what_labs_show: str
    what_imaging_shows: Optional[str] = None
    time_sensitivity: bool
    time_window_minutes: Optional[int] = None
    red_herrings: List[str]
    classic_miss_reason: str


class PatientProfile(BaseModel):
    first_name: str
    last_name: str
    occupation: str
    living_situation: str
    why_they_came_today: str
    what_theyre_not_saying: str
    what_they_fear: str
    what_they_are_protecting: str
    communication_style: str
    attitude_toward_medical_system: str
    key_person: str
    key_person_relationship: str


class OutcomeTrajectory(BaseModel):
    correct_treatment: str
    correct_outcome: str
    missed_diagnosis: str
    resident_catches_it_unsupervised: str
    resident_misses_it_unsupervised: str
    disposition: Literal[
        "discharge", "admit-floor", "admit-icu", "OR",
        "cath-lab", "transfer", "AMA", "death"
    ]
    follow_up_hook: Optional[str] = None


class SystemicFlags(BaseModel):
    world_event_connection: Optional[str] = None
    shift_case_connection: Optional[str] = None
    return_patient: bool
    prior_visit_summary: Optional[str] = None
    future_seed: Optional[str] = None


class GeneratedCase(BaseModel):
    case_id: str
    narrative_hook: str = Field(
        description="One sentence. The human story underneath the medical presentation. "
                    "Never the diagnosis."
    )
    presenting_layer: PresentingLayer
    medical_truth: MedicalTruth
    patient_profile: PatientProfile
    reveal_sequence: List[RevealNode]
    outcome_trajectory: OutcomeTrajectory
    systemic_flags: SystemicFlags


class ShiftCasePool(BaseModel):
    shift_id: str
    cases: List[GeneratedCase]
