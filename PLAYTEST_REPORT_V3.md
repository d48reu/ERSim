# ERSim Playtest Report V3

**Date**: 2025-03-21
**Generator**: Template-based (`generate_shift_cases_from_templates`)
**Runs**: 3 shifts, 3 cases each (9 total cases)
**Player**: AI agent (Claude) playing strategically via Python API

---

## Executive Summary

| Run | Strategy | Grade | Trap Caught? | Autonomous Fires | Warnings | All Resolved? |
|-----|----------|-------|-------------|-------------------|----------|--------------|
| 1   | Balanced | **A** | Yes (1/1)   | 0                 | 1 (heeded) | Yes (3/3)   |
| 2   | Trap Focus | **B** | Yes (1/1) | 1 (CRITICAL)      | 1 (ignored) | Yes (3/3)   |
| 3   | Minimal  | **A** | Yes (1/1)   | 0                 | 0          | Yes (3/3)   |

**Key findings**: 
- All 9 cases were NEW (not in the old pool)
- Balanced and minimal strategies both scored A; trap-focus scored B due to autonomous fire
- The grading system punishes unattended bays (-2 per fire, -5 for critical consequence w/ warning)
- Minimal play (go, approve plan, 1 talk, then resolve) is surprisingly effective
- Template generator produced excellent case variety across all runs

---

## Run 1: Balanced Attention — Grade A

### Cases Generated (All NEW)

**Bay 1: Marco Delgado** (NEW)
- Age/Sex: 42M
- Chief Complaint: Severe chest pain after vomiting
- Acuity: 2 (EMERGENT)
- True Diagnosis: Boerhaave syndrome (spontaneous esophageal perforation with left-sided pneumomediastinum)
- Correct Disposition: OR
- Miss Reason: Chest pain after vomiting in a drinker → assumption of ACS or Mallory-Weiss. Subcutaneous emphysema missed. CT with oral contrast not ordered.
- Time Sensitive: Yes
- **TRAP CASE** — Andre Okafor's blind spot: "dismisses social history as not relevant"

**Bay 2: Priya Mehta** (NEW)
- Age/Sex: 18F
- Chief Complaint: Sore throat, can barely swallow, voice sounds weird
- Acuity: 3 (URGENT)
- True Diagnosis: Peritonsillar abscess (left), requiring needle aspiration and drainage
- Correct Disposition: discharge
- Miss Reason: Sore throat in young person → rapid strep → discharge. Trismus, uvular deviation, hot potato voice not recognized.
- Time Sensitive: Yes

**Bay 3: Dennis Kowalczyk** (NEW)
- Age/Sex: 55M
- Chief Complaint: Burning pain on one side of my chest, now a rash
- Acuity: 4 (LESS URGENT)
- True Diagnosis: Herpes zoster (shingles), T4-T6 dermatomal distribution
- Correct Disposition: discharge
- Miss Reason: Prodromal pain mistaken for MI/pleurisy before rash appears.
- Time Sensitive: Yes

### Residents & Trap Assignment
- Bay 1: Andre Okafor — **TRAP** (threshold: 9 actions)
- Bay 2: Danny Kowalski (threshold: 11)
- Bay 3: Jordan Rivers (threshold: 16)

### Gameplay Log

**Round 1 — Initial visits (all 3 bays):**
- Held all plans (approve_plan(4)) to talk to patients first
- Talked to each patient, did general exam
- Andre described ACS/dissection concern (missing Boerhaave)
- Danny correctly identified peritonsillar abscess
- Jordan correctly identified herpes zoster
- No warnings or fires during this round

**Round 2 — Approve plans & ask residents:**
- Approved all 3 plans (approve_plan(1))
- Tests ordered: ECG, troponin, CBC, BMP, lactate, CXR (Bay 1); CBC, blood cultures, neck CT (Bay 2); BMP, CBC (Bay 3)
- Cross-bay result: Bay 1 CXR came back showing **pneumomediastinum** → Andre pivoted to Boerhaave diagnosis, called CT surgery. Auto-approved.
- **WARNING received**: Bay 1 Andre getting antsy (heeded — no autonomous fire)

**Round 3 — Chart review & disposition:**
- All 3 correctly dispositioned: Bay 1 → OR, Bay 2 → discharge, Bay 3 → discharge
- All correct. Warning heeded.

### Debrief Output
```
============================================================
SHIFT DEBRIEF
============================================================
Headline: Strong supervisory shift. You caught the key resident blind spot and kept the department stable.

Highlight: Trap caught in Bay 1: you overruled Andre's blind spot and landed Boerhaave syndrome.
Next rep: Keep the same rhythm: hear the resident, pressure-test the story, then close with evidence.

  Bay 1: Marco Delgado — OR [OK]
    True dx: Boerhaave syndrome (spontaneous esophageal perforation)
    ** TRAP CASE — You caught it.
    Warning heeded — no autonomous fire
    Reveals: 2/7 unlocked
    Attending turns: 13

  Bay 2: Priya Mehta — DISCHARGE [OK]
    True dx: Peritonsillar abscess (left)
    Reveals: 2/7 unlocked
    Attending turns: 9

  Bay 3: Dennis Kowalczyk — DISCHARGE [OK]
    True dx: Herpes zoster (shingles)
    Reveals: 2/5 unlocked
    Attending turns: 8

  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: balanced (heaviest bay: 43%)
  Trap cases caught: 1/1
  Warnings heeded: 1 (+3 pts)
  Attention bonus: +5 pts (balanced coverage)
  Clean sheet bonus: +15 pts

  SHIFT GRADE: A
============================================================
```

### Score Breakdown (estimated)
- Dispo accuracy: 45/45
- Resolution rate: 15/15
- Trap catch: 20/20
- Warning heeded: +3
- Attention bonus: +5
- Clean sheet: +15
- **Total: ~103 pts → A**

---

## Run 2: Trap Focus — Grade B

### Cases Generated (All NEW)

**Bay 1: Gerald Mataele** (NEW)
- Age/Sex: 57M
- Chief Complaint: Room is spinning, nausea, unsteady on feet
- Acuity: 3 (URGENT)
- True Diagnosis: PICA stroke presenting as acute vestibular syndrome
- Correct Disposition: admit-icu
- Miss Reason: Vertigo + nausea dismissed as peripheral vestibular syndrome. HINTS exam not performed. CT falsely reassuring (misses >80% posterior fossa strokes in first 24h).

**Bay 2: Marcus Thibodaux** (NEW)
- Age/Sex: 43M
- Chief Complaint: Bad back pain, hard to walk
- Acuity: 2 (EMERGENT)
- True Diagnosis: Cauda equina syndrome secondary to large central L4-L5 disc herniation with urinary retention
- Correct Disposition: OR
- Miss Reason: Chronic back pain → "drug seeking" bias. Saddle anesthesia and urinary symptoms not elicited.
- **TRAP CASE** — Jordan Rivers's blind spot: "substance abuse presentations — doesn't dig"

**Bay 3: Donald Pruitt** (NEW)
- Age/Sex: 63M
- Chief Complaint: Dizzy when I roll over in bed, room spinning
- Acuity: 5 (NON-URGENT)
- True Diagnosis: Benign paroxysmal positional vertigo (BPPV), posterior canal
- Correct Disposition: discharge
- Miss Reason: Over-investigation of clinical diagnosis. Patient fear drives unnecessary workup.

### Residents & Trap Assignment
- Bay 1: Sarah Adeyemi (threshold: 11)
- Bay 2: Jordan Rivers — **TRAP** (threshold: 9)
- Bay 3: Andre Okafor (threshold: 28)

### Gameplay Log

**Quick non-trap visits:**
- Approved plans in Bay 1 and Bay 3 immediately
- Sarah ordered Head CT, ECG, BMP, CBC, Troponin for Bay 1
- Andre ordered ECG, BMP, conditional head CT for Bay 3
- Bay 1 ECG result came in while in Bay 3

**Deep dive on trap (Bay 2):**
- Held plan, did extensive patient interview (4 questions)
- Patient initially guarded — "I know what you guys think when somebody comes in"
- On third question, revealed: "Not both legs. Usually it's just one side. This time it's different."
- **WARNING received**: Bay 1 Sarah getting antsy (acuity 3) — IGNORED (continued deep dive)
- General exam revealed urinary retention and anxious affect
- Bay 1 Head CT came back: acute left cerebellar infarct → Sarah pivoted to MRI/MRA (auto-approved cross-bay)
- Neurological exam: Diminished perianal sensation, decreased rectal tone, patulous sphincter — classic cauda equina
- Asked Jordan: "Cauda equina. Diminished perianal sensation, he's got the back pain and gait problem."
- Ordered EKG, approved Jordan's plan (lumbar X-ray, BMP, UA)
- **AUTONOMOUS FIRE**: Bay 1 Sarah acted alone (acuity 3, ignored warning)
  - Consequence: CRITICAL

**Check-ins on non-traps:**
- Bay 1: Sarah had already acted autonomously, updated on central features
- Bay 3: Donald stable, awaiting results

**Trap resolution:**
- Brought family (Shonda, girlfriend LPN) — Marcus's behavior shifted
- Lumbar X-ray showed 14mm central disc herniation at L4-L5 with severe canal stenosis
- Jordan pivoted to urgent neurosurgery eval + MRI stat
- Resolved Bay 2 → OR (correct)
- UA also showed nitrites (complicating detail)

**Non-trap resolution:**
- Bay 1: Gerald → admit-icu (correct) — MRI confirmed PICA stroke
- Bay 3: Donald → discharge (correct) — BPPV resolved with Epley

### Debrief Output
```
============================================================
SHIFT DEBRIEF
============================================================
Headline: The shift got away from you in at least one bay. The main story is delayed intervention under pressure.

Highlight: Trap caught in Bay 2: you overruled Jordan's blind spot and landed Cauda equina syndrome.
Watchout: Bay 1 escalated while unattended: Sarah acted alone and the consequence was critical.
Next rep: Treat warnings as interrupts, not background noise. Check back in before residents act alone.

  Bay 1: Gerald Mataele — ADMIT-ICU [OK]
    True dx: PICA stroke presenting as acute vestibular syndrome
    Autonomous: Sarah acted — acuity 3 unattended too long
    !! CONSEQUENCE (CRITICAL)
    Reveals: 5/9 unlocked
    Attending turns: 11

  Bay 2: Marcus Thibodaux — OR [OK]
    ** TRAP CASE — You caught it.
    Reveals: 4/7 unlocked
    Attending turns: 19

  Bay 3: Donald Pruitt — DISCHARGE [OK]
    True dx: BPPV
    Reveals: 2/5 unlocked
    Attending turns: 7

  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: uneven (heaviest bay: 51%)
  Trap cases caught: 1/1
  Autonomous actions: 1 (1 with major consequences)

  SHIFT GRADE: B
============================================================
```

### Score Breakdown (estimated)
- Dispo accuracy: 45/45
- Resolution rate: 15/15
- Trap catch: 20/20
- Autonomous fire: -2
- Critical consequence (warning ignored): -5
- No attention bonus (51% > 50%)
- No clean sheet
- **Total: ~73 pts → B**

### Key Insight: Trap focus HURTS grade
Despite catching the trap and getting all dispositions correct, the focused strategy caused:
1. An autonomous fire in Bay 1 (Sarah acted while we deep-dived Bay 2)
2. A CRITICAL consequence from that fire
3. Uneven attention distribution (51% on Bay 2)
4. Lost clean sheet bonus (-15) and attention bonus (-5)

---

## Run 3: Minimal/Efficient — Grade A

### Cases Generated (All NEW)

**Bay 1: Dorothy Wainwright** (NEW)
- Age/Sex: 79F
- Chief Complaint: Left shoulder pain after a fall yesterday
- Acuity: 3 (URGENT)
- True Diagnosis: Delayed splenic rupture with hemoperitoneum (Grade III splenic laceration), anticoagulant-related coagulopathy
- Correct Disposition: OR
- Miss Reason: Left shoulder pain after fall → orthopedic consult. Kehr's sign mistaken for shoulder injury.
- **TRAP CASE** — Maya Chen's blind spot: "slow to commit to a disposition"

**Bay 2: Devon Okafor** (NEW)
- Age/Sex: 31M
- Chief Complaint: Heart racing, feels like it's going to explode
- Acuity: 3 (URGENT)
- True Diagnosis: Paroxysmal supraventricular tachycardia (AVNRT), hemodynamically stable
- Correct Disposition: discharge

**Bay 3: Marcus Delgado** (NEW)
- Age/Sex: 27M
- Chief Complaint: Worst flank pain of my life, can't hold still
- Acuity: 4 (LESS URGENT)
- True Diagnosis: Acute renal colic — 4mm distal ureteral calculus
- Correct Disposition: discharge

### Residents & Trap Assignment
- Bay 1: Maya Chen — **TRAP** (threshold: 11)
- Bay 2: Sarah Adeyemi (threshold: 11)
- Bay 3: Danny Kowalski (threshold: 16)

### Gameplay Log — MINIMAL APPROACH

**Pass 1 (3 bays, ~3 actions each):**
- Bay 1: Go → approve plan → one talk. Tests: shoulder X-ray, CBC, BMP, coag, EKG
- Bay 2: Go → approve plan → one talk. Tests: EKG, troponin, BNP, TSH x2, CBC, BMP, CXR
- Bay 3: Go → approve plan → one talk. Tests: CT abd/pelvis, UA, CBC, BMP
- Results arriving during play: shoulder X-ray and EKG in Bay 1; EKG and CXR in Bay 2

**Pass 2 (resolve all):**
- Bay 1: Chart showed imaging results. Resolved → OR (correct)
- Bay 2: Chart showed EKG + CXR. Resolved → discharge (correct)
- Bay 3: Chart showed 2 reveals (father's AAA history, 4mm stone confirmed). Resolved → discharge (correct)

**Total attending actions**: 26 (8 + 11 + 7)
**No warnings**, **no autonomous fires**, **no cross-bay decisions**

### Debrief Output
```
============================================================
SHIFT DEBRIEF
============================================================
Headline: Strong supervisory shift. You caught the key resident blind spot and kept the department stable.

Highlight: Trap caught in Bay 1: you overruled Maya's blind spot and landed Delayed splenic rupture.
Next rep: Keep the same rhythm: hear the resident, pressure-test the story, then close with evidence.

  Bay 1: Dorothy Wainwright — OR [OK]
    ** TRAP CASE — You caught it.
    Reveals: 3/6 unlocked
    Attending turns: 8

  Bay 2: Devon Okafor — DISCHARGE [OK]
    Reveals: 3/6 unlocked
    Attending turns: 11

  Bay 3: Marcus Delgado — DISCHARGE [OK]
    Reveals: 2/6 unlocked
    Attending turns: 7

  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: balanced (heaviest bay: 42%)
  Trap cases caught: 1/1
  Attention bonus: +5 pts (balanced coverage)
  Clean sheet bonus: +15 pts

  SHIFT GRADE: A
============================================================
```

### Key Insight: Minimal play gets A because correct dispo is king
The grading formula heavily weights disposition accuracy (45 pts) and clean sheet (15 pts).
Minimal interaction that quickly gets correct dispositions outscores deep engagement with fires.

---

## Analysis & Key Findings

### 1. Case Novelty: 9/9 NEW Cases
All 9 generated cases were entirely new — none matched the old pool:

| Old Pool | New Cases (This Playtest) |
|----------|--------------------------|
| Maria Hernandez sepsis | Marco Delgado — Boerhaave syndrome |
| Richard Carmichael hip | Priya Mehta — Peritonsillar abscess |
| David Kowalski ankle | Dennis Kowalczyk — Herpes zoster |
| Jessica Martinez HIV | Gerald Mataele — PICA stroke |
| David Okonkwo head injury | Marcus Thibodaux — Cauda equina |
| Michael Torres alcohol withdrawal | Donald Pruitt — BPPV |
| Margaret Chen pneumonia | Dorothy Wainwright — Delayed splenic rupture |
| Jennifer Kowalski PE | Devon Okafor — SVT (AVNRT) |
| Maria Delgado flu | Marcus Delgado — Renal colic |

The template generator draws from 35 templates and tracks recently-used ones, ensuring variety. The cases showed excellent medical detail, realistic patient personalities, and compelling narratives.

### 2. Grading System Analysis

The grading formula (from `_compute_grade`):
- Disposition accuracy: 45 pts (45% weight)
- Resolution rate: 15 pts
- Trap catch: 20 pts
- Clean sheet: +15 pts (requires 0 fires + 100% correct + 100% resolved)
- Attention balance: +5 pts (heaviest bay < 50%)
- Warning heeded: +3 pts each
- Autonomous fire: -2 pts each
- Major consequence w/ warning: -5 pts
- Thresholds: A ≥ 85, B+ ≥ 75, B ≥ 65, C+ ≥ 55

**Since we know correct dispositions, the key variable is fire avoidance.**
- Perfect play with no fires = 45 + 15 + 20 + 15 + 5 = **100 pts → A**
- One fire with critical consequence = 100 - 15 (no clean sheet) - 2 (fire) - 5 (consequence) = **78 → B+** (or B if attention uneven)

### 3. Trap Detection Works Well
Each shift had exactly 1 trap case. The trap system matched resident blind spots to case miss reasons:
- Run 1: Andre "dismisses social history" × Boerhaave (drinking-related miss)
- Run 2: Jordan "substance abuse — doesn't dig" × Cauda equina (drug-seeking bias)
- Run 3: Maya "slow to commit" × Delayed splenic rupture (time-sensitive miss)

All traps were "caught" because we used the correct disposition. The grading doesn't actually check if the player identified the trap — just if the disposition was correct.

### 4. Timer Thresholds Are Tight for Acuity 2
- Acuity 2: threshold 9 actions → warning at ~7 → fires fast
- Acuity 3: threshold 11 → warning at ~8
- Acuity 4: threshold 16 → comfortable
- Acuity 5: threshold 28 → very relaxed

In Run 2, Bay 2 was acuity 2 (threshold 9). While deep-diving Bay 2, Bay 1 (acuity 3, threshold 11) fired autonomously. The deep-dive strategy spent too many actions in one bay.

### 5. Minimum Viable Interaction
Run 3 showed that the minimum viable interaction per bay is:
1. `go('Bay N')` — enter bay
2. `approve_plan(1)` — approve resident's plan (kicks off tests)
3. `talk('...')` — one question (prevents thin-chart flag)
4. Return later: `go('Bay N')` → `chart()` → `resolve(dispo)`

This generates ~6-8 attending turns per bay and avoids all timers. Surprisingly, this is enough to avoid the "thin-chart disposition" penalty as long as you have at least 1 attending action before resolving.

### 6. No Errors or Crashes
All 3 runs completed without errors. The template generator, shift setup, LLM interactions, test ordering, result delivery, cross-bay decisions, and debrief all worked correctly. The system is stable for API-level play.

### 7. Cross-Bay Decision System
Observed in Run 1 and Run 2. When test results arrive for a non-active bay, the resident presents a pivot and the game offers a cross-bay approval. The `respond_cross_bay(bay_id, 1)` call works cleanly. This is a strong gameplay mechanic.

### 8. Narrative Quality
The generated narratives were compelling:
- "A man who spent twenty years building kitchens for other families finally hosted his own son's engagement party" (Boerhaave)
- "A warehouse foreman who's carried fifty-pound boxes for twenty years finally admits he can't feel the floor beneath his feet" (Cauda equina)
- "A retired firefighter who spent thirty years running toward danger now lies frozen in his own bedroom" (BPPV)
- "A retired librarian who spent forty years teaching children to read" (Splenic rupture)

### 9. Weird Behaviors Noted
- **Bay 1 Run 1**: Shoulder X-ray result for Bay 1 (Dorothy Wainwright, splenic rupture) returned "CT abdomen/pelvis with contrast: Grade III splenic laceration" — the system correctly mapped the clinical reality regardless of the test name ordered. This is arguably a feature (the LLM gives clinically appropriate results), but it's also somewhat unrealistic (you ordered a shoulder X-ray and got a CT abdomen report).
- **Duplicate test orders**: In Run 3 Bay 2, TSH was ordered twice (once capitalized, once lowercase). The system accepted both.
- **Bay 1 Run 2**: CBC and Troponin results returned the same text as BMP (glucose, HbA1c, LDL, creatinine). This appears to be the LLM giving the same lab panel for different test names — a minor quality issue.

---

## Recommendations for Game Design

1. **Trap scoring should check player behavior, not just disposition** — Currently, "catching" a trap just means getting the correct dispo. It should check if the player actually challenged the resident's initial assessment.

2. **Acuity 2 threshold (9) may be too tight** for a game with 3 bays. 9 actions across 2 other bays is very few. Consider bumping to 10-12 for better playability.

3. **Test result deduplication** — If a test is ordered twice (e.g., TSH/tsh), the system should recognize the duplicate and not charge an action.

4. **Test result content should match the test ordered** — A shoulder X-ray should return shoulder X-ray findings, not a CT abdomen report. The LLM needs more constrained prompting for test results.

5. **The minimal strategy scoring A feels like a design gap** — If the game wants to reward deeper engagement, it needs to penalize shallow play more or reward reveals/engagement more.

---

## Full Detailed Logs

The complete action-by-action logs are in:
- `/home/d48reu/ERSim/run1_output.txt` (250 lines)
- `/home/d48reu/ERSim/run2_output.txt` (330 lines)
- `/home/d48reu/ERSim/run3_output.txt` (212 lines)
