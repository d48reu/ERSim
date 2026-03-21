# ERSim Playtest Report — 3 Runs on Haiku (OpenRouter)
## March 2026

### Test Setup
- Model: anthropic/claude-haiku-4-5 (gameplay), pre-generated cases (13 in pool)
- Backend: OpenRouter
- 3 bays per shift, 3 of 6 residents randomly selected per run

---

## Run 1: "Trust the Trap" (seed 42)
**Roster:** Danny Kowalski (PGY1 cowboy), Sarah Adeyemi (PGY3 steady), Maya Chen (PGY2 overcalibrated)
**Cases:** 6M head trauma, 71M hip fracture, 34F fever/sepsis
**Trap:** Andre on 6M head trauma (false positive — "elderly" rule matched a pediatric case)
**Result:** 3/3 correct, Grade A

**Finding:** Trap detection matched Andre's "elderly underestimate" blind spot to a 6-year-old case.
This is a bug — the elderly rule should NOT fire on pediatric patients.

## Run 2: "Tunnel Vision Neglect" (seed 99)
**Roster:** Jordan Rivers (PGY2 burning_out), Andre Okafor (PGY3 cowboy), Priya Patel (PGY1 academic)
**Cases:** 19F flu, 61M ankle sprain, 52M biliary colic
**Trap:** Andre on 61M ankle sprain (elderly underestimate — correct match)
**Result:** 3/3 correct, 1 autonomous fire (Priya on Bay 3), Grade B

**Finding:** Spending 10 turns in Bay 1 (85% attention) triggered autonomous on Bay 3.
Priya's autonomous action was competent (ordered appropriate workup). Grade
dropped from A to B purely on attention distribution + autonomous fire.
Patient voice got repetitive after ~5 turns in same bay ("shakes head", "looks up").

## Run 3: "Bad Attending" (seed 17)
**Roster:** Jordan Rivers (PGY2 burning_out), Sarah Adeyemi (PGY3 steady), Andre Okafor (PGY3 cowboy)
**Cases:** 67F TB (unhoused), 19F flu, 52M alcohol withdrawal
**Trap:** Jordan on 67F TB — his blind spot "substance abuse presentations" matched the case
**Result:** 1/2 correct (50%), 1 unresolved, trap MISSED, Grade F

**Finding:** THIS IS THE IDEAL SCENARIO. Jordan presented TB as "straightforward CAP"
with high confidence. He noted weight loss but didn't dig. The blind spot activation
prompt worked perfectly — he was confident, plausible, and subtly wrong.
Discharged a TB patient back to a shelter. Consequence narrative was devastating and specific.

---

## Gameplay Assessment

### WHAT WORKS WELL

1. **Resident voices are distinct and authentic.** Andre's hallway shorthand
   ("Got a 71-year-old, vitals solid, straightforward") vs Sarah's measured
   approach ("Could be straightforward but the hypotension is bugging me")
   vs Jordan's flat efficiency. You can tell who's talking without seeing the name.

2. **The trap system delivers.** Run 3 is the proof case. Jordan's TB miss
   felt natural, not scripted. The blind spot activation prompt made him
   sound like a real PGY2 running on autopilot — he saw the weight loss and
   didn't follow it because that's not where his brain goes. A careful
   attending would have asked "tell me about the weight loss" and caught it.

3. **The debrief is punishing in the right way.** The F grade on Run 3
   with the TB consequence ("she continues spreading TB to others at the
   shelter") hits differently than a generic "wrong answer." It teaches
   by showing you what you caused.

4. **Attention management is real gameplay.** Run 2's B grade despite 100%
   accuracy shows that getting the answer right isn't enough — you have to
   manage your department. That's the management sim feel you wanted.

5. **Case diversity is good.** 13 cases span peds, elderly, psych-adjacent,
   surgical, infectious. The 3-of-13 random selection means variety per run.

### WHAT NEEDS WORK

1. **Trap detection has a false positive bug.** Run 1: Andre's "elderly
   underestimate" rule fired on a 6-year-old patient. The `_score_trap`
   function's "elderly" rule checks the presenting field which synthetically
   adds "elderly" for age >= 65, but Andre's rule also matches "fall" which
   appeared in the peds case. Need to add age gating to elderly rules.

2. **Patient voice gets thin after 5+ turns.** Run 2 showed the patient
   cycling through "shakes head", "looks up", "rubs arm" — stage directions
   without substance. The patient interaction model needs richer turn-by-turn
   content, especially for longer conversations. This might be a prompt issue
   or a Haiku capacity issue.

3. **Reveals aren't getting unlocked organically.** All three runs showed
   0-2/4 reveals unlocked. Players need to either (a) talk to the patient
   more specifically or (b) order specific tests to trigger reveals. The
   current talk() interface doesn't guide players toward reveal triggers.
   Reveal progress should be more visible or the triggers need to be less
   specific.

4. **The autonomous action consequence tracking needs more work.** Run 2's
   Priya autonomous was competent (ordered right tests) but the debrief
   didn't show severity. The `_autonomous_consequence_severity` attribute
   only gets set when autonomous fires through `_fire_autonomous`, and the
   debrief checks `hasattr` — but the attribute isn't consistently set
   because Priya's action didn't go through the updated flow.

5. **Haiku JSON parsing occasionally fails.** Saw 5-6 `[WARN] trigger eval
   failed (JSONDecodeError)` during Run 2. The fallbacks handle it gracefully
   (game continues) but it means some pivot interrupts are silently dropping.
   The pivot prompt may need tighter JSON framing for Haiku.

6. **No teaching moments in the debrief.** The debrief shows what happened
   but doesn't explain WHY you should have caught it. "Jordan's blind spot
   caused a miss" — but what should the attending have done differently?
   A "teaching moment" line per bay would add replay value.

### PRIORITY FIXES

P0: Fix elderly trap rule to exclude patients under 60
P1: Improve patient turn-by-turn depth (prompt tuning or raise max_tokens)
P1: Add reveal progress indicators to status display
P2: Add "teaching moment" to debrief per bay
P2: Harden pivot JSON parsing for Haiku
P3: Autonomous consequence severity consistency

### OVERALL VERDICT

The game works. The core loop — triage, delegate, intervene, resolve — is
functional and produces real gameplay tension. The trap system is the star
feature: it creates moments where trusting your resident is the wrong call,
and the debrief makes you feel the weight of that choice. The management
sim feel is there in the attention distribution scoring.

Haiku is adequate for gameplay but has JSON fragility on complex prompts.
Sonnet would be safer but 3-4x more expensive per turn. A mixed approach
(Haiku for patient talk, Sonnet for resident assessments) might be the
sweet spot.

The patient interaction depth is the weakest link. Cases are rich on paper
(reveal sequences, emotional registers, communication styles) but the
turn-by-turn conversation doesn't surface that depth reliably. This is
the main thing separating "functional prototype" from "compelling game."
