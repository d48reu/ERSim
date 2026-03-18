# Resident Workup Approval System
# Design Document — ERSim

---

## THE PROBLEM IT SOLVES

Right now the player types "bundle blood cultures, BMP, lactate, procalcitonin."
A normal person cannot do this. They don't know what those are.

The approval system removes test ordering from the player entirely.
Residents order tests. The player decides whether to trust them.

This is also more realistic. Attendings don't order tests.
They approve or redirect the resident who does.

---

## THE CORE INTERACTION

When the player enters a bay, the resident intercepts them as they do now.
But instead of just presenting the case, the resident ends with a plan
and waits for a response.

Example — Maya (overcalibrated) on the PE case:

  [MAYA intercepts you at Bay 1]

  Maya: Jennifer Kowalski, 34F. SOB, recent long drive, O2 sat 93,
  RR 24, chest is clear. Vitals otherwise okay. I'm worried about PE.
  D-dimer is going to be positive, I can feel it.

  I want to run: CT angiography, D-dimer, EKG, troponin, BMP.
  Also want to ask about leg swelling and birth control.
  That work for you?

    > 1. Go ahead — run your workup
      2. Add something
      3. Change the direction
      4. Hold — I want to talk to the patient first

The player picks 1, 2, 3, or 4.

---

## THE FOUR CHOICES IN DETAIL

### 1. Approve — "Go ahead"
Resident runs their full workup autonomously.
Results come back while the player is in this bay or another.
No test names ever appear in the player UI — just "Maya's workup is running."
When results are ready, the pivot interrupt fires as it does now.

This is the fast path. Trust your resident, move to another bay.

### 2. Add something
Player types what they want to add in plain language.
The system (or resident) interprets it.

  [YOU]: add something
  [YOU]: I want to check her for clotting history

Resident responds in character and folds it in:
  Maya: Good call. I'll ask about prior DVT and family history.
  Starting the workup now.

This is the "I know one thing more than my resident" path.
Gives the player agency without requiring medical knowledge.

### 3. Change the direction
Player redirects the workup. Resident reacts per personality.

  [YOU]: change the direction
  What if this is cardiac, not PE?

Maya (overcalibrated): Oh god, you're right, I didn't think about
that. Should I add an echo? Do you want me to hold the CTA?

Andre (cowboy): ...I mean it could be. But the drive, the O2,
the clear lungs — I'm still on PE. You want me to add echo on top
of the CTA or actually pivot?

Priya (academic): Statistically, given the Wells criteria,
PE is still favored, but you're right that ACS can present
atypically. I'd recommend we pursue both — CTA plus troponin
serial, which I had in the workup anyway.

The redirect creates the disagreement dynamic that makes residents
feel like real people rather than tools.

### 4. Hold — talk to the patient first
Player wants to gather information before committing to a workup.
Resident steps back. Normal patient conversation resumes.
After a few exchanges player can type "approve Maya's plan" or
the resident will prompt again naturally.

  Maya: No problem. I'll be right here. Just flag me when
  you're ready to move.

---

## RESIDENT PERSONALITY SHAPES THE PLAN

The plan the resident presents reflects their competency and blind spots.
This is already in the data — we just need to surface it.

Maya (overcalibrated): over-orders. Her default workup has 6 tests
when 4 would do. She flags everything. Approving her plan is safe
but slow. The player learns over time that Maya's plans are
comprehensive but redundant.

Andre (cowboy): under-orders. His workup is targeted and fast —
3 tests, confident framing. 90% of the time this is correct and
efficient. 10% of the time he's missed something critical.
The player learns to add one thing to Andre's plan as insurance.

Priya (academic): complete but slow. Her workup is textbook-correct
but may miss the human angle. She'll order the right tests for the
wrong reason. Her plans work best on classic presentations.

Burning out: minimal plan. Does enough to not get in trouble.
The player learns they need to push this resident harder or
the patient gets a bare-minimum workup.

Steady: scoped correctly. Their plan is usually the right call.
Easy to trust. The player earns this trust over multiple shifts.

---

## AUTONOMOUS WORKUP (WHEN PLAYER IS IN ANOTHER BAY)

If the player never enters a bay, the resident runs their default
workup autonomously after the timer threshold — same as now.
But the report-back when the player arrives changes:

  [ANDRE — Bay 2 report]
  Andre: Started the workup while you were tied up. CXR, CBC,
  sputum gram stain. CXR came back — upper lobe infiltrate,
  possible cavitation. I didn't isolate her yet. Wanted you
  to make that call.

The resident reports what they did, flags what they held for
the attending. This creates the "what did Andre do while I was
gone" dynamic that makes autonomous actions consequential.

---

## PIVOT STAYS, CHANGES SLIGHTLY

The pivot interrupt still fires after results come back.
But now it's the resident updating their own plan, not reacting
to the player's order.

Before: "Here's what this result means, here are 3 options."

After: "My workup came back. CXR is clear. I was wrong about
the pulmonary source. I'm pivoting to GYN. Pelvic ultrasound
and UA — ordering now unless you redirect me."

  > 1. Go ahead — let her pivot
    2. Hold — I want to examine the patient first
    3. Override — I think it's urosepsis, focus on UA only

Same mechanic. Better framing. The player is managing a person
making a clinical decision, not reading a menu.

---

## WHAT THE PLAYER NEVER SEES

- Individual test names in ordering UI
- Lab reference ranges
- Medical jargon in the choice menus

They will see test names in results (CXR, troponin) because those
are part of the narrative. But they never have to KNOW or PRODUCE
those names to play.

---

## THE TRUST MECHANIC (PHASE 2)

Not for the first build, but designed in from the start.

Each resident has a hidden accuracy score per case type.
Maya on sepsis: high accuracy. Maya on trauma: lower.
Andre on cardiac: high. Andre on social history: near zero.

The player doesn't see this number. They learn it through play.
"Maya flagged everything and was right." "Andre moved fast and
missed the family history that changed the diagnosis."

Over multiple shifts the player builds a mental model of who
to trust on what. That's the long-game skill.

When the player approves a resident's plan:
  shift.resident_ai.attending_backed(context)

When the player overrides:
  shift.resident_ai.attending_overrode(context)

These already exist in the codebase. We just wire them to
approval choices.

---

## IMPLEMENTATION PLAN

### Step 1 — Approval prompt at bay entry
Modify resident proactive() output to always end with a plan
and an explicit ask for approval.

Add to ResidentAssessment:
  plan_summary: str        # one sentence: "I want to run X, Y, Z"
  plan_rationale: str      # why — in their voice
  plan_tests: list[str]    # actual test names (hidden from player UI)
  plan_questions: list[str] # questions they want to ask the patient

Modify build_proactive_prompt() to require this output.

### Step 2 — Approval command in shift.py
New method: shift.approve_plan(choice, addendum=None)
  choice 1: run resident's plan as-is
  choice 2: run plan + addendum (player's plain text addition)
  choice 3: redirect (player types new direction)
  choice 4: hold

For choice 2 and 3: one LLM call to interpret player's plain text
and translate to test names + resident reaction.

### Step 3 — Wire 1/2/3/4 at bay entry
Currently 1/2/3 only work after a pivot.
Extend to work as approval choices when a pending plan exists on the bay.

### Step 4 — Autonomous workup uses plan_tests
When timer fires and resident acts, they run plan_tests instead of
hallucinating what to do. More consistent. More predictable outcomes.

### Step 5 — Pivot reframed as plan update
Modify pivot prompt: resident is updating their OWN plan, not
reacting to the player's order. Choices become redirect options
not menu items.

---

## WHAT THIS CHANGES FOR THE PLAYER

Before:
  Enter bay -> get case -> type "bundle blood cultures, BMP, lactate"
  -> get results -> type "@maya what do you think"

After:
  Enter bay -> Maya presents case + plan -> pick 1/2/3/4
  -> results come back -> Maya pivots -> pick 1/2/3
  -> resolve

The player's actions are: enter, decide, decide, close.
The medical knowledge lives in the resident.
The player's skill is judgment, timing, and trust calibration.

---

## RESOLVED DESIGN DECISIONS

1. "Add something" is free-text, not a menu.
   Menu implicitly teaches the player what to look for, which undercuts
   the "I thought of that" satisfaction. Free-text preserves discovery.
   One LLM call to interpret. Always worth it.

2. Patient communication is the HUMAN pipeline, not the clinical one.
   Resident owns clinical questions (DVT history, LMP, medications).
   Attending owns human questions (what are you scared of, who should
   I call, I need you to be honest with me about the drinking).
   Some reveal nodes are gated behind attending presence specifically —
   things the patient won't tell the resident but will tell the attending
   who comes in, closes the curtain, and asks directly.
   Every patient turn costs attending time — that's the tradeoff.
   Patient scenes that matter: breaking bad news, patient won't talk to
   resident, family dynamics, moments of fear that need a human being.

3. "Hold" pauses the timer on that bay.
   Attending is present and deciding — resident is not abandoned.

4. If player ignores the approval prompt and talks to the patient:
   Resident waits silently. After 2 patient turns, resident prompts again
   naturally. If still ignored after that, they ask explicitly:
   "Do you want me to hold on that workup?"
   This respects player intent without letting the plan disappear.
