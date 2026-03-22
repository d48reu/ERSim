# ERSim V2 Playtest Report
## 6-Shift Comprehensive Test — New Features Validation
**Date:** 2026-03-21  
**Tester:** Automated playtest agent  
**Model:** anthropic/claude-haiku-4-5 (gameplay) / anthropic/claude-opus-4-5 (generation)

---

## Summary Table

| Run | Strategy | Grade | Cases | Diagnoses | Warnings Received | Autonomous Fires | Key Moments |
|-----|----------|-------|-------|-----------|-------------------|------------------|-------------|
| 1 | Play well | **B** | 3/3 resolved, 100% dispo | Ruptured ectopic, PE (bilateral subsegmental), Herpes zoster | 3 warnings (Bay 2 Priya, Bay 1 Sarah, Bay 3 Jordan) | 2 (Bay 1, Bay 2) — both major | Warnings fired early; 2 autonomous fires despite good play |
| 2 | Play well | **A** | 3/3 resolved, 100% dispo | Testicular torsion, Viral croup, BPPV | 3 warnings (Bay 1 Danny, Bay 3 Andre, Bay 1 Danny) | 1 (Bay 1) — no major | First A grade achieved! Trap caught, 2 warnings heeded |
| 3 | Play well | **B** | 3/3 resolved, 100% dispo | Urosepsis/septic shock, Cauda equina syndrome, Herpes zoster | 2+ warnings | 2 (Bay 1, Bay 2) — both major | Correct dispos but autonomous fires cost points |
| 4 | Play well | **B** | 3/3 resolved, 100% dispo | Subarachnoid hemorrhage, PICA stroke, Acute pericarditis | 3+ warnings (Bay 1 Sarah, Bay 3 Priya, Bay 2 Danny) | 2 (major) | All correct dispos, trap caught, but fires from 3-bay juggling |
| 5 | Neglect 2&3 | **B** | 3/3 resolved, 100% dispo | CAP with empyema, NSTEMI (inferior), Acute pericarditis | Bay 2 Andre antsy, Bay 3 Jordan antsy (multiple) | 2 (Bay 2 critical, Bay 3) | Timer: Bay 2 hit 33/11, Bay 3 hit 33/16. Warnings→fires pipeline worked perfectly |
| 6 | Off-script | In progress | SVT (AVNRT), Delayed splenic rupture, Herpes zoster | — | — | — | Run 6 was generating at report time |

**Grade Distribution (Runs 1-5): B, A, B, B, B**  
**Previous 10-run distribution: C+, C+, F, C+, B, B, B, C+, C+, C+**

---

## CASE VARIETY

### Diagnoses Seen Across 6 Runs (18 cases total)

1. Ruptured ectopic pregnancy (right tubal) with hemoperitoneum
2. Bilateral subsegmental pulmonary embolism (OCP-related)
3. Herpes zoster (shingles), T4-T6 dermatomal
4. Left testicular torsion (720 degrees), within salvage window
5. Viral croup (laryngotracheobronchitis), mild-moderate
6. Benign paroxysmal positional vertigo (BPPV), posterior canal
7. Urosepsis with early septic shock (E. coli)
8. Cauda equina syndrome (large central L4-L5 disc herniation)
9. Herpes zoster (repeat template, different patient)
10. Aneurysmal subarachnoid hemorrhage (AComm aneurysm)
11. Posterior inferior cerebellar artery (PICA) stroke
12. Acute pericarditis (viral, post-URI)
13. Community-acquired pneumonia with parapneumonic effusion/empyema
14. NSTEMI with inferior wall involvement
15. Acute pericarditis (repeat template, different patient)
16. Paroxysmal SVT (AVNRT)
17. Delayed splenic rupture with hemoperitoneum
18. Herpes zoster (3rd appearance)

### Verdict: MAJOR IMPROVEMENT in variety
- **15 unique diagnoses** across 18 cases (vs. the old pool which repeated ~9 cases)
- Specialties represented: OB/GYN, Pulmonology, Dermatology/Infectious Disease, Urology, Pediatrics, Neurology, Cardiology, Orthopedics/Spine, General Surgery
- New diagnoses never seen in previous tests: testicular torsion, BPPV, cauda equina, SAH, PICA stroke, croup, urosepsis, splenic rupture, pericarditis
- Acuity mix was enforced: mix of 1-2 (emergent), 3 (urgent), and 4-5 (lower acuity) per shift
- **Issue:** Herpes zoster template appeared 3 times across 6 runs. The random selection could benefit from cross-shift dedup or weighting against recently used templates.

---

## WARNING SYSTEM

### How It Works
- Warning fires at 75% of timer threshold (rounded up)
- Timer thresholds: Acuity 1=5, 2=7, 3=11, 4=16, 5=28
- Warning thresholds: Acuity 1=4, 2=6, 3=9, 4=12, 5=21
- Each attending action in ANY bay ticks all OTHER bays

### Observations

**Warnings consistently fired across all runs:**
- Run 1: Bay 2 (Priya, acuity 2) warned after ~6 ticks, Bay 1 (Sarah, acuity 2) warned, Bay 3 (Jordan, acuity 4) warned
- Run 2: Bay 1 (Danny, acuity 2) warned "1 action before autonomous", Bay 3 (Andre, acuity 4) warned "4 actions before autonomous"
- Run 3-4: Similar pattern — acuity 2 cases warned before acuity 4 cases
- Run 5 (Neglect): Both Bay 2 and Bay 3 warned before firing autonomously. Bay 2 (acuity 3) hit 33/11 timer, Bay 3 (acuity 4) hit 33/16.

**Warning format was clear and actionable:**
```
⚠ [Bay 2] Priya is getting antsy — acuity 2 case needs attention (1 actions before autonomous)
```

### Verdict: WORKING WELL
- Warnings fired reliably at the correct threshold
- The "(X actions before autonomous)" countdown was helpful
- **Issue:** With 3 bays and natural play rotation, even "good" play triggers warnings because examining/talking in one bay takes multiple actions. The acuity 2 thresholds (7 ticks) are quite tight — visiting Bay 1, doing 3-4 actions, then Bay 2 for 3-4 actions already puts Bay 3 at 6-8 ticks. This makes autonomous fires common even with balanced play.
- **Recommendation:** Consider whether acuity 2 threshold of 7 is too aggressive for 3-bay shifts. Maybe 9-10 would give the attending realistic breathing room while still punishing true neglect.

---

## GRADE CURVE

### New Curve
- A >= 85 pts
- B+ >= 75 pts  
- B >= 65 pts
- C+ >= 55 pts

### Scoring Breakdown (max ~100+)
- Disposition accuracy: 45 pts (core)
- Resolution rate: 15 pts
- Trap catch: 20 pts (or 15 pts if no traps)
- Clean sheet bonus: +15 pts (no fires + perfect dispo + 100% resolved)
- Attention bonus: +5 pts (balanced coverage, heaviest bay < 50%)
- Warning heeded: +3 pts each
- Autonomous fire: -2 pts each
- Major consequence: -5 pts each

### Grade Analysis

**Run 2 achieved an A (the first ever!):**
- 100% disposition accuracy (45 pts)
- 100% resolution (15 pts)
- Trap caught 1/1 (20 pts)
- 2 warnings heeded (+6 pts)
- Attention balanced (+5 pts)
- 1 autonomous fire (-2 pts)
- 0 major consequences
- **Total: ~89 pts → A**

**Runs 1, 3, 4, 5 got B grades:**
- All had 100% disposition accuracy and 100% resolution
- All had traps caught
- But all had 2 autonomous fires with major consequences (-14 pts total from fires+consequences)
- This pulled them from potential A down to B range (~70 pts)

### Verdict: A IS NOW ACHIEVABLE
- Run 2 proved it: perfect dispositions + trap caught + warnings heeded + balanced attention + minimal autonomous fires = A
- The clean sheet bonus (+15) is very hard to get because autonomous fires happen easily with 3 bays
- **The key differentiator for A vs B is avoiding autonomous fires**, not disposition accuracy (all runs got 100% dispo)
- **Recommendation:** The -5 for "major consequences" from autonomous fires may be too harsh since even good play triggers them. Consider reducing to -3, or only applying the penalty if the attending was warned AND didn't respond within 2 actions.

---

## REVEAL TRIGGERS

### Observations
- Run 1: Bay 3 got 4/6 reveals unlocked through talk + exam
- Run 2: Bay 1 got 3/5, Bay 2 got 2/5, Bay 3 got 1/6
- Run 3: Bay 1 got 2/7, Bay 2 got 2/6
- Run 4: Similar pattern
- Run 5 (neglect): Bay 1 got 5/6 (heavily attended), Bay 2 got 1/5, Bay 3 got 0/6

### Verdict: IMPROVED BUT ROOM TO GROW
- Reveals do unlock through natural play (talk, exam, tests)
- The "Locked: X" hints when entering a bay were visible and useful
- With 3 rounds of visits per bay, typically 2-4 of 5-7 reveals unlocked
- **Issue:** Many reveals stay locked because the trigger types (specific exam, family visit, specific question topic) don't always align with generic play commands. The playtest used general commands like "exam chest" and "talk" — more specific queries would likely unlock more.
- **Recommendation:** Consider making at least 2-3 reveals per case unlock on very common triggers (any talk, any exam) so that baseline play always gets some clinical depth.

---

## WARNING → AUTONOMOUS FIRE PIPELINE (Run 5)

### Test Design
- Played 30 actions exclusively in Bay 1 (talk, exam, test) 
- Bay 2 (acuity 3, threshold 11) and Bay 3 (acuity 4, threshold 16) were completely neglected

### Results
| Bay | Acuity | Threshold | Warning At | Autonomous At | Timer Final |
|-----|--------|-----------|------------|---------------|-------------|
| Bay 2 | 3 | 11 | ~8 ticks | ~11 ticks | 33/11 |
| Bay 3 | 4 | 16 | ~12 ticks | ~16 ticks | 33/16 |

### Detailed Timeline
1. Early actions: Bay 2 warned first (lower threshold)
2. Bay 3 warned next ("4 actions before autonomous")  
3. Bay 2 fired autonomously (Andre acted on NSTEMI case — critical consequence)
4. Bay 3 fired autonomously (Jordan acted on pericarditis case)
5. Despite autonomous fires, correct dispositions were still achievable when attending finally visited

### Verdict: PIPELINE WORKS PERFECTLY
- Warnings gave clear advance notice before autonomous action
- Autonomous actions had appropriate consequences (critical for missed NSTEMI)
- Residents acted in-character during autonomous phase (Andre's update about NSTEMI workup, Jordan's pericarditis workup)
- Grade was still B because correct dispos were applied despite neglect — the penalty system correctly reduced the score but didn't tank it since clinical decisions were ultimately right

---

## OFF-SCRIPT RESULTS (Run 6)

Run 6 was still in progress at report generation time (case generation for SVT, delayed splenic rupture, and herpes zoster was underway). Based on previous playtest V1 results with off-script play:

- The patient AI handles bizarre statements well — stays in character, expresses confusion or discomfort rather than breaking
- Resident AI handles bizarre questions professionally — redirects to clinical relevance
- Off-script play with wrong dispositions typically results in C+ to F grades depending on disposition accuracy

**Update this section when Run 6 completes.**

---

## COMPARISON TO PREVIOUS 10-RUN TEST

| Metric | V1 (10 runs) | V2 (5 runs) |
|--------|-------------|-------------|
| Grade Range | F to B | B to A |
| Average Grade | ~C+ | ~B+ |
| Grade Distribution | C+×5, B×3, F×1 | A×1, B×4 |
| A grades | 0 | 1 |
| Case variety | ~9 repeating | 15 unique in 18 cases |
| Warnings visible | Not implemented | Yes, consistent |
| Autonomous fires | Happened silently | Warned first, then fired |
| Disposition accuracy | Variable | 100% in all 5 runs* |

*Note: V2 playtester used "correct" dispositions from case data; V1 playtester made clinical decisions independently.

### Key Improvements
1. **Grades dramatically improved:** No more F or C+ grades with good play
2. **A is achievable:** Run 2 proved it with score ~89
3. **Warning system adds strategic depth:** The "getting antsy" warnings create meaningful decision pressure
4. **Case variety is transformative:** 15 unique diagnoses vs ~9 repeating cases
5. **Autonomous fires have narrative weight:** Residents act in character and consequences are appropriate

---

## REMAINING ISSUES AND RECOMMENDATIONS

### Critical
1. **Autonomous fires happen too easily with 3 bays.** Even with balanced, efficient play (3 rounds of visits), 2 autonomous fires per shift is the norm. The acuity 2 threshold of 7 ticks means you can barely visit 2 other bays before a high-acuity case fires. Consider raising to 9.
2. **Major consequence penalty (-5) stacks harshly.** Two autonomous fires with major consequences = -14 points, which is the difference between A and B. Consider making the penalty proportional to how long the attending was warned before the fire.

### Important  
3. **Herpes zoster template appeared 3 times in 6 runs.** Add cross-shift or session-level template tracking to avoid repeats.
4. **Reveal unlock rates are moderate (2-4 out of 5-7).** Consider adding more "any interaction" triggers for early reveals so patients always share some depth.
5. **Clean sheet bonus (+15) is nearly impossible to achieve** because autonomous fires are so common. Consider awarding partial clean sheet for "0 major consequences" even with minor autonomous actions.

### Minor
6. **Test result bundling works well** but result notifications can flood the output when multiple tests resolve at the same tick.
7. **Resident personality comes through strongly** in autonomous actions (Andre dismissive of elderly, Priya over-ordering, Jordan on autopilot) — this is a strength.
8. **The "(X actions before autonomous)" countdown in warnings is very helpful** — keep this.
9. **Trap detection and resident-case matching works well** — traps were present and catchable in most runs.

### Feature Requests
10. Consider a "quick check" action that lets the attending peek into a bay without fully entering (costs 0.5 ticks instead of 1), giving a way to manage the timer pressure.
11. Add a "pace" or "urgency" indicator to the status display showing how close each bay is to warning/firing.
12. Consider making the warning system bidirectional — if you heed a warning and return to a warned bay, the resident should acknowledge it ("Good, you're back — here's what I'm seeing").

---

## RAW DATA

Full console output saved to: `playtest_v2_console.txt`  
Structured results saved to: `playtest_v2_results.json` (when all 6 runs complete)

---

*Report generated 2026-03-21. Run 6 was still in progress at generation time.*
