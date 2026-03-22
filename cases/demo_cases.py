"""
Curated demo shift metadata.

These notes are designed to improve the quality of the first playable demo
without fully spoiling the cases.
"""

CURATED_DEMO_CASES = {
    "SHIFT_20260317_0118_05": {
        "title": "Withdrawal Hidden In Plain Sight",
        "setup_focus": "A strong surface story can hide the real problem unless someone asks directly about recent drinking.",
        "play_hint": "The story may be too tidy. Ask one direct behavior question instead of another broad symptom check.",
        "dispo_warning": "This bay usually needs one human clue about recent drinking or one more confirming datapoint before you close it.",
        "result_nudge": "This is the reframe moment. Treat recent drinking and withdrawal risk like the center of the case, not a side note.",
    },
    "SHIFT_20260317_0118_06": {
        "title": "Anxiety Or Something Worse",
        "setup_focus": "The trap is letting a respiratory case stay framed as anxiety when the physiology is slightly off.",
        "play_hint": "If the physiology feels off, ask what changed during the drive and look for risk, not just symptoms.",
        "dispo_warning": "This bay is dangerous to close before you pressure-test the travel story or get objective workup back.",
        "result_nudge": "Do not let this stay framed as anxiety. If the physiology is off, escalate around the risk story.",
    },
    "SHIFT_20260317_0118_02": {
        "title": "The Easy Win You Still Have To Finish",
        "setup_focus": "This is the stabilizer bay in the demo shift: a clean, winnable case if you do not overcomplicate it.",
        "play_hint": "Move this one cleanly. Confirm the injury, disposition decisively, and free your attention for the harder bays.",
        "dispo_warning": "Do not close it blind, but once the fracture is objectively confirmed this should be a fast, decisive admission.",
        "result_nudge": "This is your confidence-builder. Once the fracture is confirmed, close it cleanly and reclaim your attention.",
    },
}

CURATED_DEMO_CASE_IDS = tuple(CURATED_DEMO_CASES.keys())


def get_demo_case_meta(case_id: str) -> dict:
    return CURATED_DEMO_CASES.get(case_id, {})
