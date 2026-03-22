# Implementation Plan: Interaction Layer + Priority Fixes

## From Playtest Report — Priority Fixes

```
P0: Fix elderly trap rule to exclude patients under 60       ✅ DONE
P1: Improve patient turn-by-turn depth                       THIS PLAN
P1: Add reveal progress indicators to status display         THIS PLAN
P2: Add "teaching moment" to debrief per bay                 THIS PLAN
P2: Harden pivot JSON parsing for Haiku                      THIS PLAN
P3: Autonomous consequence severity consistency              THIS PLAN
```

---

## FIX 1: Patient Turn-by-Turn Depth (P1 — interaction layer)

### The Problem
After 4-5 turns the patient responses collapse into gesture-only stage
directions: "*shakes head*", "*looks up*", "*rubs arm*". The case data
has rich emotional registers and communication styles but Haiku stops
surfacing them.

### Root Causes
1. `max_tokens=200` in `_get_patient_response()` — too low for
   substantive replies. Patients need room to speak.
2. No explicit instruction to AVOID repeating the same gesture patterns.
3. No injection of "what you could talk about" — the patient has rich
   backstory (occupation, living situation, fears, key person) but the
   prompt doesn't nudge the LLM to surface these when the conversation
   goes quiet.
4. The conversation history format sends ALL prior turns, which crowds
   out the system prompt as context grows.

### Implementation
**File: cases/interaction.py**

A. Raise `max_tokens` from 200 to 350 in `_get_patient_response()`
   - Still short enough to be realistic; long enough for a real sentence
     plus one behavioral beat.

B. Add an anti-repetition instruction to the system prompt after the
   FORMAT section:
   ```
   ANTI-REPETITION
   If your last 3 responses used an italicized action, do NOT use one
   this turn. Vary between: speaking with texture in the words, silence
   that communicates, answering a question the attending didn't ask, or
   a brief physical gesture you haven't used before.

   If the attending keeps asking open-ended questions and you've already
   answered, start bringing in life details from your ground truth —
   your occupation, your living situation, the person in the waiting
   room, what you were doing before you came in. These are natural
   things real patients mention when they're sitting in an ER.
   ```

C. Add a "conversation warmth" injection to `_build_patient_context()`:
   After turn 3, inject a hint about available backstory topics:
   ```
   YOU CAN BRING UP (naturally, not all at once):
   - Your work: {occupation}
   - Your living situation: {living_situation}
   - The person waiting: {key_person}
   - Why you really came today (your version, not triage): {why_they_came_today}
   These are NOT reveals — they are normal things patients mention.
   ```

D. Trim conversation history to last 6 turns (3 pairs) instead of 16.
   This keeps the system prompt dominant and prevents the LLM from
   pattern-matching on its own previous gestures.


## FIX 2: Reveal Progress in Status Display (P1)

### The Problem
Players don't know how many reveals exist or how to unlock them. The
game has a rich reveal system but it's invisible during play.

### Implementation
**File: shift/shift.py — `_render_status()`**

Add reveal progress per bay in the status line:
```
   Bay 1  [3]  Maria Hernandez   SUPERVISED   2/4 revealed   ! 3 ticks
```

Also add reveal hints when entering a bay — show locked trigger TYPES
(not the detail) so the player knows what actions might unlock info:
```
  Locked reveals: 1× direct_question, 1× physical_exam, 1× trust_established
```

**File: shift/shift.py — `go()` method**

After the bay header, append reveal hint if any locked reveals exist.


## FIX 3: Teaching Moments in Debrief (P2)

### The Problem
The debrief shows outcomes but doesn't teach. "Jordan's blind spot
caused a miss" — what should the attending have done differently?

### Implementation
**File: shift/shift.py — `debrief()`**

For each bay, add a "teaching moment" line derived from the case data:

- If trap missed: "The clue was {classic_miss_reason}. Asking about
  {first locked reveal trigger_detail} would have surfaced it."
- If dispo wrong: "Key finding: {supporting_findings[0]}.
  The correct path was {correct_treatment}."
- If autonomous fired: "{resident name}'s archetype ({personality})
  under pressure tends to {archetype_tendency}. Checking in earlier
  would have caught this."
- If all correct: "Good read. {narrative_hook}" (just the human story)

Archetype tendencies (hardcoded):
- cowboy: "act faster and check less"
- overcalibrated: "escalate everything and freeze"
- academic: "order more tests and delay action"
- burning_out: "do the minimum and miss nuance"
- steady: "understate urgency"


## FIX 4: Harden Pivot JSON Parsing (P2)

### The Problem
Haiku returns malformed JSON on pivot prompts — 5-6 `JSONDecodeError`
per run. Fallbacks catch it but pivots silently drop.

### Implementation
**File: residents/resident.py — `_call()` helper**

The `_call()` function already strips markdown fences. Add:
1. Strip trailing commas before closing braces (common Haiku error)
2. Strip any text before the first `{` or after the last `}`
3. Try `json.loads(raw, strict=False)` before raising
4. If all JSON strategies fail, try regex extraction of key fields

**File: residents/prompts.py — pivot prompt**

Add to the pivot JSON instruction:
```
CRITICAL: Return ONLY the JSON object. No text before it. No text
after it. No markdown fences. Start with { and end with }.
```


## FIX 5: Autonomous Consequence Severity Consistency (P3)

### The Problem
`_autonomous_consequence_severity` only gets set when `_fire_autonomous`
runs. If an autonomous action is triggered through a different path,
the debrief can't read severity.

### Implementation
**File: shift/bay.py**

Add `_autonomous_consequence_severity` as a proper dataclass field
(default "none") instead of a dynamic attribute.

**File: shift/shift.py — `_fire_autonomous()`**

Already sets it — verify the autonomous action's `consequence_severity`
is correctly propagated from the LLM response through the
ResidentAutonomousAction to the bay attribute.


## Implementation Order

1. Patient depth (Fix 1) — biggest impact, addresses the weakest link
2. Reveal progress (Fix 2) — makes reveals visible and actionable
3. Teaching moments (Fix 3) — debrief becomes a learning tool
4. Pivot JSON hardening (Fix 4) — reliability
5. Consequence severity (Fix 5) — correctness

Estimated scope: ~200 lines changed across 4 files.
