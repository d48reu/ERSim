"""Test ordering, validation, delays, and bundles."""

from __future__ import annotations

import re

from cases.demo_cases import get_demo_case_meta

from .bay import Bay
from .constants import SHIFT_MINUTES_PER_TURN, SHIFT_START_HOUR, TEST_DELAYS


class ShiftTestsMixin:
    # Known clinical test keywords — any test name must contain at least one
    _KNOWN_TEST_WORDS = {
        "ekg", "ecg", "cxr", "xray", "x-ray", "ct", "mri", "echo", "ultrasound",
        "glucose", "fingerstick", "bmp", "cmp", "cbc", "troponin", "lactate", "d-dimer",
        "ddimer", "bnp", "procalcitonin", "urinalysis", "ua", "urine", "culture",
        "blood", "flu", "strep", "monospot", "hiv", "hcg", "pregnancy", "coag",
        "inr", "pt", "ptt", "liver", "lfts", "lipase", "tsh", "thyroid", "crp",
        "esr", "ferritin", "iron", "b12", "folate", "magnesium", "phosphate",
        "ammonia", "cortisol", "trop", "chest", "abdominal", "pelvis", "pelvic",
        "head", "brain", "spine", "cardiac", "renal", "pulmonary", "angio",
        "cta", "ppd", "tb", "sputum", "gram", "legionella", "urine antigen",
        "monospot", "ebv", "cmv", "rsv", "covid", "panel", "toxicology", "tox",
        "acetaminophen", "aspirin", "alcohol", "ethanol", "drug", "screen",
        "abg", "vbg", "gas", "oximetry", "peak flow", "spirometry",
        # thyroid / endocrine
        "free t4", "free t3", "ft4", "ft3", "t4", "t3", "tft",
        # coag / heme
        "fibrinogen", "d dimer", "anti-xa", "anti xa", "heparin",
        # micro / id
        "antigen", "pcr", "rapid", "swab", "mono", "heterophile",
        # cardiac
        "ck", "ck-mb", "ckmb", "nt-probnp", "ntprobnp",
        # electrolytes / metabolic
        "sodium", "potassium", "creatinine", "bun", "bicarbonate",
        "calcium", "magnesium", "phosphorus", "albumin",
        # imaging long-form
        "electrocardiogram", "radiograph", "angiogram", "angiography",
        "tomography", "resonance", "sonogram", "doppler",
        # drug levels
        "level", "serum", "digoxin", "lithium", "vancomycin", "phenytoin",
        # neuro
        "lumbar", "puncture", "csf", "spinal",
        # other
        "hypercoagulability", "hypercoag", "thrombophilia", "factor",
    }

    # Normalize common long-form test names to canonical keys before lookup
    _TEST_NAME_NORMALIZE = {
        "electrocardiogram": "ecg",
        "electrocardiography": "ecg",
        "12-lead ecg": "ecg",
        "12-lead ekg": "ekg",
        "complete blood count": "cbc",
        "complete blood count with differential": "cbc",
        "cbc with differential": "cbc",
        "cbc w/ diff": "cbc",
        "cbc w diff": "cbc",
        "basic metabolic panel": "bmp",
        "comprehensive metabolic panel": "bmp",
        # Short-form aliases — residents routinely dump these in plan_tests
        "cmp": "bmp",
        "bmp/cmp": "bmp",
        "chem 7": "bmp",
        "chem-7": "bmp",
        "chem10": "bmp",
        "chem 10": "bmp",
        "electrolytes": "bmp",
        "chest x-ray": "chest x",
        "chest xray": "chest x",
        "chest radiograph": "chest x",
        "portable chest x-ray": "chest x",
        "cxr": "chest x",
        "pa/lat cxr": "chest x",
        "arterial blood gas": "abg",
        "venous blood gas": "vbg",
        "arterial or venous blood gas": "abg",
        "free t4": "tsh",
        "free thyroxine": "tsh",
        "thyroid function tests": "tsh",
        "tfts": "tsh",
        "tft": "tsh",
        "d-dimer": "d-dimer",
        "d dimer": "d-dimer",
        "ddimer": "d-dimer",
        "urine drug screen": "urine",
        "urine drug screening": "urine",
        "uds": "urine",
        "tox screen": "tox",
        "toxicology screen": "tox",
        "utox": "tox",
        "urinalysis": "ua",
        "urinalysis with culture": "ua",
        "ua with culture": "ua",
        "u/a": "ua",
        "lipase/amylase": "lipase",
        "coags": "coag",
        "pt/inr": "inr",
        "pt/ptt": "ptt",
        "pt/ptt/inr": "inr",
        "hs troponin": "troponin",
        "hs-troponin": "troponin",
        "high-sensitivity troponin": "troponin",
        "high sensitivity troponin": "troponin",
    }

    def _normalize_test_name(self, test_name: str) -> str:
        """Normalize verbose test names to canonical short keys."""
        lower = test_name.lower().strip()
        return self._TEST_NAME_NORMALIZE.get(lower, test_name)

    def _test_key(self, test_name: str) -> str:
        """Canonical comparison key for duplicate detection."""
        return self._normalize_test_name(test_name).strip().lower()

    def _test_already_known(self, bay, test_name: str) -> bool:
        """True if this test is already pending or has already resulted."""
        key = self._test_key(test_name)
        for _, pending_name, _, _ in bay.pending_results:
            if self._test_key(pending_name) == key:
                return True
        for existing_name in getattr(bay, "_test_results", {}):
            if self._test_key(existing_name) == key:
                return True
        return False

    def _queue_test_result(self, bay, test_name: str, actor: str) -> tuple[bool, str]:
        """Queue a test if it is valid and not already known. Returns (queued, message)."""
        test_name = self._normalize_test_name(test_name)
        if not self._validate_test_name(test_name):
            return False, f"[{test_name}] — not recognized, skipped"
        if self._test_already_known(bay, test_name):
            return False, f"[{test_name}] already ordered - check chart"

        delay = self._get_test_delay(test_name)
        if delay >= 999:
            bay.record(actor, "test", test_name)
            return False, f"[{test_name}] ordered - results not available this shift."
        if delay == 998:
            bay.record(actor, "test", test_name)
            return False, f"[{test_name}] drawn and sent - results post-shift with admitting team"

        full_result = bay.patient_session.order_test(test_name)
        bay.record(actor, "test", test_name)
        bay.record("system", "test_pending", f"{test_name} - due turn {self.global_turn + delay}")
        due_turn = self.global_turn + delay
        due_clock = self._format_clock(due_turn)
        bay.pending_results.append((due_turn, test_name, full_result, bay.bay_id))
        delay_min = delay * SHIFT_MINUTES_PER_TURN
        return True, f"[{test_name}] ordered - due ~{due_clock} (~{delay_min} min)"

    def _validate_test_name(self, test_name: str) -> bool:
        """
        Return True if test_name looks like a real clinical test.
        Rejects: single chars, pure demographics (34F, 16M),
        generic words, and anything under 3 chars.
        """
        name = test_name.strip()
        # Allow 2-char names that are recognized short-form tests (ua, pt, ct).
        if len(name) <= 2:
            return name.lower() in self._KNOWN_TEST_WORDS
        # Reject pure demographic patterns: number + letter (34F, 16M, 71M)
        import re
        if re.match(r'^\d+[MmFf]$', name):
            return False
        # Reject single common words that aren't tests
        _JUNK = {"pain", "fever", "cough", "fall", "home", "chest", "back",
                 "head", "arm", "leg", "x", "test", "result", "the", "and",
                 "with", "for", "days", "male", "female", "old", "year"}
        if name.lower() in _JUNK:
            return False
        # Must contain at least one known clinical word
        name_lower = name.lower()
        return any(kw in name_lower for kw in self._KNOWN_TEST_WORDS)

    _HEADER_PATTERN = re.compile(
        r"^[*_#`\s]*(impression|result|findings?|conclusion|interpretation|report|summary)[:\s*]*$",
        re.IGNORECASE,
    )

    @classmethod
    def _is_header_line(cls, line: str) -> bool:
        """True when a line is a section header with no substantive body.

        Examples: '**IMPRESSION:**', 'Findings:', 'REPORT' all return True;
        'Impression: normal sinus rhythm' returns False.
        """
        stripped = line.strip()
        if cls._HEADER_PATTERN.match(stripped):
            return True
        # Markdown-heavy lines with barely any alphanumeric content
        alnum = sum(1 for ch in stripped if ch.isalnum())
        return alnum < 4

    def _summarize_result(self, test_name: str, full_result: str) -> str:
        """
        Return a short 1-2 sentence summary of a test result.
        Full result is stored for chart view.
        """
        lines = [l.strip() for l in full_result.split('\n') if l.strip()]
        # Drop pure section headers — they're not summaries.
        content_lines = [l for l in lines if not self._is_header_line(l)]

        priority_words = [
            "impression", "result", "finding", "conclusion",
            "interpretation", "positive", "negative", "normal",
            "elevated", "abnormal", "consistent", "confirmed",
            "no acute", "within normal",
        ]
        for word in priority_words:
            for line in content_lines:
                if word in line.lower() and len(line) > 10:
                    return line[:120]
        # Fallback: first substantive non-header line
        for line in content_lines:
            if len(line) > 15:
                return line[:120]
        # Last resort: the test ran but came back with no parseable content.
        return f"{test_name.upper()} — open the chart for the full report"

    # Negation windows: if any of these appear within ~40 chars BEFORE an
    # urgent keyword, the finding is being ruled out, not in.
    _NEGATION_MARKERS = (
        "no acute", "no evidence", "negative for", "without",
        "unremarkable", "within normal", "normal limits",
        "rule out", "ruled out", "not seen", "not present",
        "no sign", "no obvious", "no concerning", "benign",
        "normal ", " no ",
    )

    @classmethod
    def _is_negated(cls, text: str, keyword: str) -> bool:
        """
        Return True if the keyword is preceded by a negation marker within
        ~40 characters. Lets us distinguish "ischemic changes" from
        "no acute ischemic changes".
        """
        idx = text.find(keyword)
        if idx == -1:
            return False
        window = text[max(0, idx - 40):idx]
        return any(marker in window for marker in cls._NEGATION_MARKERS)

    def _has_unnegated(self, text: str, keywords: tuple) -> bool:
        return any(
            kw in text and not self._is_negated(text, kw)
            for kw in keywords
        )

    def _suggest_next_step(self, bay, test_name: str, full_result: str) -> str:
        """Return a short actionable nudge based on obvious result keywords."""
        text = f"{test_name} {full_result}".lower()
        demo_nudge = get_demo_case_meta(bay.case.case_id).get("result_nudge")

        # If the result body is empty/placeholder, do not make claims about it.
        stripped = full_result.strip()
        if len(stripped) < 25 or stripped.lower() in {"impression:", "**impression:**", "pending", "pending - results to follow"}:
            return "Open the chart for the full report — summary was not available."

        if (
            bay.case.case_id == "SHIFT_20260317_0118_02"
            and self._has_unnegated(text, ("fracture", "intertrochanteric", "femoral neck"))
        ):
            return "This is your clean close: admit, call orthopedics, and move on."
        if demo_nudge and self._has_unnegated(text, ("withdrawal", "alcohol", "pe", "embol", "fracture", "hypoxia")):
            return demo_nudge
        if self._has_unnegated(text, ("st elevation", "nstemi", "stemi", "ischemia", "ischemic")):
            return "Consider immediate cardiac escalation or treatment."
        # Troponin elevation (not just troponin ordered): require a number or "elevated"
        if ("troponin" in text and self._has_unnegated(text, ("elevated", "high", "above", "positive"))):
            return "Consider immediate cardiac escalation or treatment."
        if self._has_unnegated(text, ("fracture", "intertrochanteric", "femoral neck")):
            return "Likely needs admission and specialty consultation."
        if self._has_unnegated(text, ("alcohol withdrawal", "withdrawal", "ciwa")):
            return "Reassess withdrawal severity and consider monitored admission."
        if self._has_unnegated(text, ("intracranial hemorrhage", "subarachnoid", "subdural", "epidural hematoma", "mass effect", "midline shift")):
            return "Match this against neuro exam and escalate — neurosurgery input may be needed."
        if self._has_unnegated(text, ("sepsis", "septic shock")) or ("lactate" in text and self._has_unnegated(text, ("elevated", "high"))):
            return "Reassess for sepsis, fluids, and admission need."
        # Only when nothing concerning is found do we say "closer to discharge".
        if any(word in text for word in ("normal", "no acute", "negative", "unremarkable", "within normal")):
            return "Reassuring result — if the bedside picture also fits, you may be closer to discharge."
        return "Open the chart for the full report before deciding."

    def _get_test_delay(self, test_name: str) -> int:
        """Return turn delay for a test. Matches on substring of test name."""
        name_lower = test_name.lower()
        for key, delay in TEST_DELAYS.items():
            if key in name_lower:
                return delay
        return 6  # Default: ~30 min for unknown tests

    def _format_clock(self, turn: int) -> str:
        """Convert global turn to wall clock time string."""
        total_minutes = SHIFT_START_HOUR * 60 + turn * SHIFT_MINUTES_PER_TURN
        h = (total_minutes // 60) % 24
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"

    def test(self, test_name: str, suppress_pivot: bool = False) -> str:
        """Order a test. Result is deferred by realistic delay."""
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        # Normalize then validate
        test_name = self._normalize_test_name(test_name)
        if not self._validate_test_name(test_name):
            return f"[?] '{test_name}' — not recognized as a test. Try being more specific."

        self._tick_others(self.active_bay_id)
        self.global_turn += 1
        bay.note_attending_intervention(f"ordered test: {test_name}")

        _, message = self._queue_test_result(bay, test_name, actor="attending")
        return message

        delay = self._get_test_delay(test_name)

        if delay >= 999:
            bay.record("attending", "test", test_name)
            return (
                f"[{test_name}] ordered — results not available this shift. "
                f"Flag for follow-up."
            )
        if delay == 998:
            bay.record("attending", "test", test_name)
            return (
                f"[{test_name}] drawn and sent — results post-shift, "
                f"will follow with admitting team."
            )

        # Get full result from patient session but don't show it yet
        full_result = bay.patient_session.order_test(test_name)
        bay.record("attending", "test", test_name)
        bay.record("system", "test_pending", f"{test_name} — due turn {self.global_turn + delay}")

        due_turn = self.global_turn + delay
        due_clock = self._format_clock(due_turn)
        # Store (due_turn, test_name, full_result, bay_id)
        bay.pending_results.append((due_turn, test_name, full_result, bay.bay_id))

        delay_min = delay * SHIFT_MINUTES_PER_TURN
        return f"[{test_name}] ordered — results due ~{due_clock} (~{delay_min} min)"

    def bundle_test(self, test_names: list[str], suppress_tick: bool = False) -> str:
        """Order multiple tests as ONE turn, then defer all results.

        suppress_tick=True when called from a flow that already ticked for
        this attending action (e.g. approve_plan -> _execute_plan); prevents
        double-charging the player on one click.
        """
        bay = self._require_active_bay()
        if not bay:
            return "You're not in a bay."

        if not suppress_tick:
            # Tick once for the whole bundle — it's one attending action
            self._tick_others(self.active_bay_id)
            self.global_turn += 1
        bay.note_attending_intervention(
            f"ordered test bundle: {', '.join(test_names[:4])}"
        )

        output = []
        skipped = []
        for name in test_names:
            name = self._normalize_test_name(name)
            if not self._validate_test_name(name):
                skipped.append(name)
                continue
            if self._test_already_known(bay, name):
                output.append(f"  [{name}] already ordered - check chart")
                continue
            _, message = self._queue_test_result(bay, name, actor="attending")
            output.append(f"  {message}")

        if skipped:
            output.append(f"  [skipped — not recognized: {', '.join(skipped)}]")

        return "Tests ordered:\n" + "\n".join(output)
