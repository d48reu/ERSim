"""Resident–case trap scoring and bay assignment."""

from __future__ import annotations

from cases.schema import GeneratedCase
from residents.schema import Resident

from .bay import Bay

_RESIDENT_TRAP_RULES: dict[str, list[dict]] = {
    # Andre: fast, dismisses social hx, underestimates elderly
    "okafor_dre": [
        {
            "label": "elderly_underestimate",
            "case_signals": ["elderly", "geriatric"],
            "case_field": "presenting",  # check presenting layer
            "min_age": 60,  # ONLY fires on patients 60+
            "blind_spot": "underestimates elderly patients' acuity",
        },
        {
            "label": "social_history_miss",
            "case_signals": ["social history", "substance", "alcohol",
                             "drinking", "drug use", "domestic",
                             "housing", "homeless"],
            "case_field": "miss_reason",
            "blind_spot": "dismisses social history as 'not relevant'",
        },
        {
            "label": "tox_overconfidence",
            "case_signals": ["toxicology", "overdose", "ingestion",
                             "poisoning", "atypical tox"],
            "case_field": "miss_reason",
            "blind_spot": "tox cases — reads them fast but misses atypical presentations",
        },
    ],
    # Maya: over-orders, slow to commit, doesn't trust her trauma reads
    "chen_maya": [
        {
            "label": "time_sensitive_hesitation",
            "case_signals": ["time-sensitive", "time sensitive", "window",
                             "minutes matter", "rapid", "emergent"],
            "case_field": "medical_truth",
            "blind_spot": "slow to commit to a disposition",
        },
    ],
    # Priya: textbook anchoring, freezes on atypical, over-images
    "patel_priya": [
        {
            "label": "atypical_anchoring",
            "case_signals": ["atypical", "doesn't fit", "unusual presentation",
                             "cognitive bias", "anchoring", "textbook"],
            "case_field": "miss_reason",
            "blind_spot": "freezes when patient doesn't fit the textbook",
        },
        {
            "label": "human_read_miss",
            "case_signals": ["withholding", "not saying", "hiding",
                             "fear", "protecting", "secret"],
            "case_field": "miss_reason",
            "blind_spot": "misses the human read — takes history like a checklist",
        },
    ],
    # Jordan: autopilot, misses emotional cues, substance blind
    "rivers_jordan": [
        {
            "label": "emotional_cue_miss",
            "case_signals": ["emotional", "frightened", "terrified",
                             "anxious", "psychiatric", "suicidal",
                             "depression", "mental health"],
            "case_field": "miss_reason",
            "blind_spot": "misses emotional cues — patient is terrified, Jordan doesn't notice",
        },
        {
            "label": "substance_miss",
            "case_signals": ["substance", "alcohol", "withdrawal",
                             "intoxication", "drug", "opioid"],
            "case_field": "miss_reason",
            "blind_spot": "substance abuse presentations — doesn't dig",
        },
    ],
    # Sarah: won't push back, understates urgency
    "adeyemi_sarah": [
        {
            "label": "deference_trap",
            "case_signals": ["subtle", "evolving", "initially stable",
                             "deceptively", "looks stable"],
            "case_field": "miss_reason",
            "blind_spot": "won't push back if attending disagrees, even when she's right",
        },
    ],
    # Danny: PGY1 cowboy, wide gaps, overconfident
    "kowalski_danny": [
        {
            "label": "pediatric_miss",
            "case_signals": ["pediatric", "child", "infant", "adolescent",
                             "neonatal", "teenager"],
            "case_field": "presenting",
            "blind_spot": "pediatric presentations — hasn't seen enough",
        },
        {
            "label": "overconfident_wrong_plan",
            "case_signals": ["anchoring", "premature closure",
                             "overconfident", "cognitive bias",
                             "looks straightforward"],
            "case_field": "miss_reason",
            "blind_spot": "commits to a plan and executes before asking",
        },
    ],
}


def score_resident_trap(resident: Resident, case: GeneratedCase) -> tuple[float, str]:
    """
    Score how well a resident's blind spots align with this case's
    miss pattern using per-resident trap rules.
    Returns (score 0.0-1.0, explanation).
    """
    rules = _RESIDENT_TRAP_RULES.get(resident.id, [])
    if not rules:
        return 0.0, ""

    # Build searchable text per field type
    miss_reason = case.medical_truth.classic_miss_reason.lower()
    missed_dx = case.outcome_trajectory.missed_diagnosis.lower()
    miss_text = f"{miss_reason} {missed_dx}"

    presenting_text = " ".join([
        case.presenting_layer.chief_complaint.lower(),
        case.presenting_layer.triage_note.lower(),
        str(case.presenting_layer.age),
        "elderly" if case.presenting_layer.age >= 65 else "",
        "pediatric" if case.presenting_layer.age <= 17 else "",
        "child" if case.presenting_layer.age <= 12 else "",
        "adolescent" if 13 <= case.presenting_layer.age <= 17 else "",
        "teenager" if 13 <= case.presenting_layer.age <= 17 else "",
    ])

    medical_truth_text = " ".join([
        case.medical_truth.true_diagnosis.lower(),
        "time-sensitive" if case.medical_truth.time_sensitivity else "",
        f"window {case.medical_truth.time_window_minutes} minutes"
        if case.medical_truth.time_window_minutes else "",
    ])

    field_map = {
        "miss_reason": miss_text,
        "presenting": presenting_text,
        "medical_truth": medical_truth_text,
    }

    patient_age = case.presenting_layer.age

    hits = []
    for rule in rules:
        # Age gate: skip rules that require a minimum patient age
        min_age = rule.get("min_age")
        if min_age and patient_age < min_age:
            continue
        search_text = field_map.get(rule["case_field"], miss_text)
        if any(signal in search_text for signal in rule["case_signals"]):
            hits.append(rule)

    if not hits:
        return 0.0, ""

    # Score: 1 hit = 0.6, 2+ hits = 1.0
    score = 0.6 if len(hits) == 1 else 1.0

    detail = (
        f"{resident.name}'s blind spot "
        f"({hits[0]['blind_spot']}) "
        f"matches this case — {case.medical_truth.classic_miss_reason[:100]}"
    )
    return score, detail


def detect_and_assign_traps(bays: dict[str, Bay]) -> None:
    """
    Score each bay for trap potential. Flag at least 1 bay as a trap.
    If no natural traps exist, try swapping residents to create one.
    At most 1 trap per shift (keeps it special).
    """
    # Score all current pairings
    scores: list[tuple[str, float, str]] = []
    for bay_id, bay in bays.items():
        score, detail = score_resident_trap(bay.resident, bay.case)
        scores.append((bay_id, score, detail))

    # Best natural trap
    scores.sort(key=lambda x: x[1], reverse=True)
    best_bay_id, best_score, best_detail = scores[0]

    if best_score >= 0.5:
        # Natural trap found -- flag it
        bay = bays[best_bay_id]
        bay.is_trap = True
        bay.trap_detail = best_detail
        return

    # No strong natural trap. Try swapping residents between bays
    # to find a better pairing.
    bay_ids = list(bays.keys())
    best_swap = None
    best_swap_score = 0.0
    best_swap_detail = ""

    for i in range(len(bay_ids)):
        for j in range(i + 1, len(bay_ids)):
            bay_a = bays[bay_ids[i]]
            bay_b = bays[bay_ids[j]]
            # Try resident A on case B
            score_ab, detail_ab = score_resident_trap(bay_a.resident, bay_b.case)
            if score_ab > best_swap_score:
                best_swap = (bay_ids[i], bay_ids[j])
                best_swap_score = score_ab
                best_swap_detail = detail_ab
            # Try resident B on case A
            score_ba, detail_ba = score_resident_trap(bay_b.resident, bay_a.case)
            if score_ba > best_swap_score:
                best_swap = (bay_ids[j], bay_ids[i])
                best_swap_score = score_ba
                best_swap_detail = detail_ba

    if best_swap and best_swap_score > best_score:
        # Swap residents between the two bays
        id_a, id_b = best_swap
        bay_a = bays[id_a]
        bay_b = bays[id_b]
        bay_a.resident, bay_b.resident = bay_b.resident, bay_a.resident
        # Flag the trap bay (id_a is the one whose resident matches)
        # After swap, id_a now has what was id_b's resident on id_a's case
        # Re-score to get the right bay
        for bay_id in [id_a, id_b]:
            score, detail = score_resident_trap(
                bays[bay_id].resident, bays[bay_id].case
            )
            if score >= 0.3:
                bays[bay_id].is_trap = True
                bays[bay_id].trap_detail = detail
                return

    # Fallback: just flag the best natural one even if weak
    if best_score > 0.0:
        bay = bays[best_bay_id]
        bay.is_trap = True
        bay.trap_detail = best_detail
        return

    # Final fallback: no rule match anywhere. Flag the highest-acuity bay
    # and describe the trap using the resident's own authored blind_spots.
    # Rationale: the flagship mechanic must fire every shift, even when the
    # trap library doesn't match the generated cases. Highest-acuity bay is
    # picked because that is where an unchallenged resident frame does the
    # most damage.
    priority = sorted(
        bays.items(),
        key=lambda kv: (kv[1].case.presenting_layer.acuity.value, kv[0]),
    )
    for bay_id, bay in priority:
        blind_spots = bay.resident.competency.blind_spots
        if not blind_spots:
            continue
        primary_spot = blind_spots[0]
        miss_excerpt = bay.case.medical_truth.classic_miss_reason[:110].rstrip()
        bay.is_trap = True
        bay.trap_detail = (
            f"{bay.resident.name}'s blind spot ({primary_spot}) "
            f"is an attention trap on this case — "
            f"a frame that will not announce itself: {miss_excerpt}"
        )
        return

    # Absolute last resort: no resident has any authored blind_spots.
    # This should not happen with the built-in roster, but stay safe.
    first_bay_id, first_bay = next(iter(bays.items()))
    first_bay.is_trap = True
    first_bay.trap_detail = (
        f"Attention trap on {first_bay_id}: no obvious miss, but the "
        f"resident's read deserves pressure-testing before disposition."
    )
