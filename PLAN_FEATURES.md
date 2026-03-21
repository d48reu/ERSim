# ERSim Feature Plan — Scoring, Consequences, Holy Shit Cases, Resident Roster Expansion

## FEATURE 1: End-of-Shift Scoring / Debrief

### What exists now
- resolve() compares player disposition to correct disposition
- Says "Correct disposition" or "Recommended was X"
- _build_shift_summary() in commands.py lists resolved/unresolved bays
- OutcomeTrajectory has: correct_treatment, correct_outcome, missed_diagnosis, resident_catches/misses_unsupervised

### What to build
Add a `ShiftScorecard` dataclass to shift.py tracking per-bay metrics:

Per bay:
- disposition_correct: bool
- time_to_resolve: int (turns)
- reveals_unlocked: int / total
- autonomous_fired: bool (did you ignore this bay long enough?)
- autonomous_consequence: str (what happened because you weren't there)
- key_finding_caught: bool (did you or resident catch the critical thing?)
- resident_was_wrong: bool (was this a "holy shit" case?)
- resident_was_corrected: bool (did you catch it?)

Shift-level:
- total_resolved: int / total
- avg_time_per_case: float
- attention_balance: score (penalize spending 80% in one bay)
- grade: A/B/C/D/F based on composite

### Debrief screen
After "quit" or all bays resolved, show:
```
SHIFT DEBRIEF
Bay 1: Maria Hernandez — ADMIT ICU ✓
  True dx: sepsis from UTI. You caught it.
  Reveals: 6/8 unlocked. Missed: alcohol history.
  Time: 12 turns (efficient)

Bay 2: Marcus Thompson — DISCHARGE ✗ (should have been ADMIT-FLOOR)
  True dx: cardiac contusion. Resident said clear, you trusted him.
  Andre's blind spot: underestimates elderly acuity.
  Consequence: patient returns in 4h with tamponade.

Bay 3: David Kowalski — UNRESOLVED
  Autonomous: Maya ordered full panel, results pending.
  Consequence: delayed diagnosis, workable but slower.

GRADE: C+
  Disposition accuracy: 1/2
  Attention distribution: poor (70% in Bay 1)
  Critical catch: 1/2
  Teaching moment: Trust Andre's speed, verify his elderly reads.
```

## FEATURE 2: More Visible Consequences

### What exists now
- autonomous_fired flag on bay
- ResidentAutonomousAction has was_correct and consequence fields
- But these aren't shown to the player in any impactful way

### What to build
- When autonomous fires and resident acts WRONG, the consequence is visible:
  "Bay 2 update: Andre ordered CT head but skipped coags. Patient is on warfarin."
- Add `consequence_severity` to ResidentAutonomousAction: minor/moderate/major/critical
- Critical consequences affect the debrief grade heavily
- Show consequences in the status sidebar: bay card turns red, shows "!! COMPLICATION"
- When attending finally goes to the bay, resident explains what happened with personality-appropriate shame/defensiveness/denial

### Autonomous outcome quality
- Currently the LLM decides. Add schema guidance:
  - If resident's blind_spots match the case, autonomous action should reflect the blind spot
  - Cowboy: acts fast, may be wrong on complex cases
  - Overcalibrated: delays action, patient waits too long but nothing harmful
  - Academic: orders everything, nothing harmful but wastes resources
  - Burning out: may miss something obvious
  - Steady: usually handles it fine (reward for giving steady residents the complex case)

## FEATURE 3: "Holy Shit" Cases

### Concept
One case per shift where the resident's initial read is WRONG and the attending needs to catch it.
Not "resident is dumb" — the case is genuinely tricky and hits the resident's specific blind spot.

### Implementation
- In case generation prompt, add a flag: `resident_trap: bool`
- When true, the case is designed so the assigned resident's specific blind_spots cause a misread
- The resident's proactive opening presents the WRONG diagnosis confidently
- The correct diagnosis is findable if the attending:
  a) Talks to the patient (reveal sequence unlocks key info)
  b) Does a specific exam (physical exam trigger)
  c) Catches a subtle lab abnormality

### Examples by archetype
- Andre (cowboy) on elderly AMS: "It's a fall, ortho consult" → actually a stroke
- Maya (overcalibrated) won't fire but: she floods the workup, misses that one simple test matters
- Priya (academic): textbook says X, but patient presents atypically → she anchors on the wrong dx

### Generation changes
- cases/prompts.py: add resident_trap instruction to batch generation
- cases/schema.py: add `resident_trap: bool` and `trap_details: str` to GeneratedCase
- Ensure 1 per shift of 3 bays is a trap case
- Match trap case to resident whose blind_spots align

## FEATURE 4: Expanded Resident Roster (3→6, pick 3 per run)

### New residents to add

4. JORDAN RIVERS (PGY2, BURNING_OUT)
   - Was a star intern. Something broke 6 months ago (won't say what).
   - Still technically competent but running on autopilot.
   - Misses the emotional read. Patient is terrified? Jordan doesn't notice.
   - Blind spots: emotional cues, substance abuse presentations, follow-up planning
   - Strength: procedures, when engaged on a genuinely interesting case the old Jordan shows up
   - Voice: flat, efficient, slightly detached. Occasional flashes of real engagement.

5. SARAH OKONKWO (PGY3, STEADY)
   - Quietly the best resident in the program. Nobody talks about it.
   - Doesn't present dramatically. Doesn't volunteer extra. Just gets it right.
   - When she says "I want to make sure" she's actually worried. Learn to hear it.
   - Blind spots: advocacy — won't push back if attending disagrees, even when she's right
   - Strength: clinical gestalt, knows when something is off before labs confirm it
   - Voice: calm, measured, slightly understated. Trust builds through accuracy, not charisma.

6. DANNY KOWALSKI (PGY1, COWBOY — but PGY1 cowboy is different from PGY3 cowboy)
   - First year who acts like a third year. Confident, fast, sometimes right.
   - Andre's speed with none of Andre's experience. More dangerous.
   - Will commit to a plan and execute it before asking. Sometimes that plan is wrong.
   - Blind spots: everything he doesn't know he doesn't know (wide), pediatric presentations
   - Strength: genuinely good hands, calm in chaos, will do the thing nobody else wants to do
   - Voice: casual, slightly cocky, "I got this" energy. Gets quieter when he's wrong.

### Roster mechanics
- make_default_roster() returns all 6
- session.py picks 3 randomly (with constraints: at least 1 PGY1-2, at least 1 PGY3+)
- Each run feels different because personality combos change
- Andre + Sarah is very different from Danny + Jordan

## IMPLEMENTATION ORDER

1. Resident roster expansion (schema + make_default_roster) — foundational, everything else benefits
2. Holy shit cases (generation prompt + schema + trap matching) — needs roster to match blind spots
3. Consequences (autonomous severity + blind spot matching) — needs roster clarity
4. End-of-shift scoring (ShiftScorecard + debrief render) — capstone, needs everything else
