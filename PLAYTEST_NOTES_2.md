# ERSim Playtest Notes — March 20, 2026

## Bugs

### B1: Plan updates from other bays unselectable
When you're active in Bay 2 and Bay 1's resident fires a plan update,
the options scroll by in the log but you can't respond -- input is
locked to your current bay. Need cross-bay interrupt handling:
either queue + notification badge, or hold until you leave current bay.

### B2: Reveal trigger mislabeling (direct_question vs physical_exam)
`[direct_question]` trigger described a lymph node exam finding.
Player did `exam lymph node`, got the clinical finding on screen,
but reveal stayed locked because system checked for a question action.
Fix: either fix the case generator labeling, or make reveal matching
smarter -- if the locked hint text matches what just appeared on screen,
unlock it regardless of trigger label.

### B3: trust_established triggers are unactionable
No clear player action unlocks "trust_established." Hint says things like
"explains sepsis risk in non-judgmental way" -- not a game command.
Fix: make trust_established unlock passively based on conversation
turn count + patient rapport (3+ positive interactions, patient shared
personal details, player didn't rush).

### B4: Disposition grading is binary — wrong level = discharge catastrophe
`admit-icu` when correct was `admit-floor` showed the DISCHARGE bad
outcome narrative. Game treats any non-exact-match as "sent home."
Fix: gradations —
- Exact match = correct
- Admit-floor vs admit-icu = wrong level, partial credit, level-appropriate narrative
- Admit vs discharge = fully wrong, bad outcome
- Discharge vs admit = fully wrong, bad outcome

### B5: Double debrief on shift end
Debrief fires twice when all three cases are resolved.
Fix: guard flag `_debrief_shown` that flips once and blocks re-entry.

## Features

### F1: Clickable controls throughout (major UX overhaul)
Replace all typed numbers/commands with clickable buttons.
Top-level action bar always visible:
[Exam] [Test] [Talk to Patient] [Talk to Resident] [Chart] [Status] [Disposition]

Sub-level drill-down on click:
- Exam -> [Head] [Chest] [Abdomen] [Extremities] [Neuro] [Skin] [Back]
- Test -> [CBC] [BMP] [CMP] [CT Head] [X-Ray Chest] [UA] [EKG] [Custom: ___] [Back]
- Talk to Patient -> inline text box + [Send] + [Back]
- Talk to Resident -> [What's your read?] [What changed?] [Run the plan] [Hold] [Custom: ___] [Back]
- Chart -> toggle panel (no bar swap)
- Status -> toggle panel (no bar swap)
- Disposition -> [Admit-Floor] [Admit-ICU] [Discharge] [Transfer] [Back]

Rule: finite choices = buttons. Free-form = text box. Info display = toggle panel.
Never deeper than 2 levels. [Back] on every submenu.

All numbered options (approval flow, plan updates, redirects) become buttons too.

### F2: Cross-bay interrupt notifications
When a resident in another bay needs a decision, show a clickable
notification banner: "[Bay 1: Jordan needs a decision]"
Player can click to jump to that bay, respond, then return.
Or: queue the interrupt and present it when player exits current bay.

### F3: Pre-shift resident roster screen
Shown at shift start. What a real attending does — check who's on.
- Name, PGY level
- Archetype as FLAVOR text (not raw label)
  e.g., "Confident, moves fast, occasionally skips steps" not "cowboy"
- One line from last shift together if applicable
  e.g., "Last shift: made an independent call on a chest pain — turned out fine"
- Sets up trap detection: if you READ that Jordan moves fast, and he
  confidently presents a case that smells off, you have the info to catch it.
NOT an in-game cheat sheet. You learn them by working with them.

## Priority Order (recommended)
1. B5 — double debrief (trivial fix, 5 min)
2. B4 — disposition gradation (high-impact gameplay fix)
3. B1/F2 — cross-bay interrupts (gameplay-breaking)
4. F1 — clickable controls (biggest UX lift, most work)
5. B2 — reveal trigger matching (case generator + matching logic)
6. B3 — trust_established passive unlock (design decision + implementation)
7. F3 — pre-shift roster (new screen, medium effort)
