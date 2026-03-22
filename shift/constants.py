"""Shift timing and test result delay tables."""

# ---------------------------------------------------------------------------
# Test result delays — in global turns (1 turn ~ 5 min)
# ---------------------------------------------------------------------------
# Special value 999 = never resolves this shift (blood cultures, PPD, etc.)

TEST_DELAYS = {
    # Near-instant
    "glucose":          1,
    "fingerstick":      1,
    "blood glucose":    1,
    "ekg":              2,
    "ecg":              2,
    "electrocardiogram": 2,
    "electrocardiography": 2,
    "12-lead":          2,
    "12 lead":          2,
    # Quick labs
    "cxr":              4,
    "chest x":          4,
    "xray":             2,
    "x-ray":            2,
    "chest radiograph": 4,
    "portable chest":   4,
    "urinalysis":       3,
    "ua":               3,
    "urine":            3,
    "flu swab":         3,
    "flu":              3,
    "strep":            3,
    "monospot":         4,
    "pregnancy":        2,
    "hcg":              2,
    # Standard labs (45 min)
    "bmp":              9,
    "cbc":              9,
    "troponin":         9,
    "lactate":          9,
    "procalcitonin":    9,
    "d-dimer":          9,
    "ddimer":           9,
    "bnp":              9,
    "liver":            9,
    "coag":             9,
    "inr":              9,
    "lipase":           9,
    "tsh":              9,
    "thyroid":          9,
    "hiv":              9,
    "monospot":         9,
    # Imaging (30-60 min)
    "ct":               8,
    "cta":              8,
    "mri":             12,
    "ultrasound":       8,
    "echo":            10,
    # Ordered and drawn this shift — results post-shift (sent to admitting team)
    "blood culture":  998,
    "culture":        998,
    "sputum culture": 998,
    "wound culture":  998,
    "urine culture":  998,
    # Truly never resolves (days-weeks)
    "ppd":            999,
    "tb":             999,
}

SHIFT_START_TURN = 0
SHIFT_START_HOUR = 19   # 7 PM
SHIFT_MINUTES_PER_TURN = 5
SHIFT_DURATION_TURNS = 96  # 8 hours

