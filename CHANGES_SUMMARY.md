# ERSim Changes Summary — Last 6 Commits
## Generated March 2026

This document covers commits 1a335aa through 54ae3b1 — the centralized
LLM factory, async infrastructure, UI polish, roster expansion, trap
cases, end-of-shift grading, and the first 3-run playtest on Haiku.

---

## COMMIT-BY-COMMIT BREAKDOWN

### 1. 1a335aa — Centralized LLM Factory + Entry Points

**What changed:** Eliminated 4+ duplicate `_get_client()` functions scattered
across generator.py, interaction.py, shift.py, and resident.py. Replaced them
with a single centralized `llm.py` module.

**New files:**
- `llm.py` — centralized client factory with backend detection (openrouter/ollama)
- `run.py` — unified launcher with `--ollama`, `--model`, `--gen-model`, `--port` flags
- `ersim-setup` — setup script that detects VRAM, checks Ollama, pulls models
- `models.yaml` — recommended model tiers by GPU VRAM (high/medium/low)

**Key behavior changes:**
- OLD: Hardcoded `anthropic/claude-haiku-4-5` everywhere, OpenRouter only
- NEW: `ERSIM_BACKEND=ollama|openrouter` env var or `--ollama` flag
- Model resolution: CLI flag > env var > default for backend
- Client is cached per-backend (singleton pattern)
- OpenRouter defaults: haiku (gameplay), opus (generation)
- Ollama defaults: qwen3:8b (gameplay), glm-4.7-flash (generation)
- All 4 modules (generator, interaction, shift, resident) now import from llm.py

### 2. 6a4ca65 — P0 Async Session Setup + Non-blocking Commands

**What changed:** Fixed the server freezing during LLM calls.

**Key behavior changes:**
- OLD: Session POST created shift, called setup() synchronously, returned start_text.
  All commands ran synchronously on the FastAPI event loop, blocking everything.
- NEW: Session POST returns immediately with `status: "setting_up"`.
  WebSocket connect triggers `asyncio.to_thread(_run_setup_sync)` for the
  blocking LLM calls. Client gets "Setting up shift..." message, then
  setup_complete event with full bay data when ready.
- ALL blocking commands (talk, exam, test, approve_plan, resolve, etc.) now
  wrapped in `await asyncio.to_thread(fn, *args)`. Non-blocking commands
  (leave, status, chart) remain sync.
- WebSocket ping interval bumped to 30s, ping timeout to 120s (slow local LLMs
  can take >30s per response).
- GameSession gets `setup_complete: bool` flag to track setup state.
- Frontend handles `setup_complete` WS event to update bay sidebar.
- Ollama model defaults changed: gameplay `glm-4.7-flash` -> `qwen3:8b`,
  generation `qwen3.5:27b` -> `glm-4.7-flash` (swapped roles for better perf).

### 3. 514e4e5 — P1 Loading Spinner + Clickable Approval Buttons

**What changed:** UI polish for the web frontend.

**Loading spinner:**
- OLD: "Generating shift..." text with pulse animation
- NEW: Three animated bouncing dots above "Generating shift..." text
- CSS: `.spinner-dots` with `.dot` elements, staggered `dot-bounce` keyframes

**Clickable approval buttons:**
- OLD: Player sees numbered text menu (1. Go ahead / 2. Go ahead, but add
  something / 3. Change the direction / 4. Hold) and must type the number
- NEW: Frontend detects the approval pattern via regex, renders 4 styled
  pill-shaped buttons that send the command on click
- Pattern detected: `1. Go ahead\n2. Go ahead, but add something\n3. Change
  the direction\n4. Hold — I want to talk to the patient first`
- Buttons styled with accent-dim border, hover/active states
- MessageBlock component now receives `sendCommand` prop

### 4. 7046315 — Roster Expansion (6 Residents) + Trap Cases

**ROSTER EXPANSION:**
- OLD: 3 residents (Maya, Andre, Priya) — all 3 used every shift
- NEW: 6 residents — 3 randomly selected per shift with PGY balance

New residents added:
- **Jordan Rivers** (PGY2, BURNING_OUT) — was a star, something broke.
  Blind spots: emotional cues, substance abuse, follow-up planning.
  Strength: procedures, engages on interesting cases.
- **Sarah Adeyemi** (PGY3, STEADY) — quietly the best, nobody notices.
  Blind spots: won't push back, understates urgency.
  Strength: clinical gestalt, patient rapport.
- **Danny Kowalski** (PGY1, COWBOY) — former paramedic, PGY1 with PGY3 confidence.
  Blind spots: wide knowledge gaps, pediatrics, acts before asking.
  Strength: calm in chaos, fast triage, good hands.

`select_shift_roster()` function: picks 3 of 6 with constraints:
  - At least 1 junior (PGY1-2)
  - At least 1 senior (PGY3+)
  - Shuffled for random bay assignment

**TRAP CASE SYSTEM:**
- NEW: Per-resident trap rules in `_RESIDENT_TRAP_RULES` dict
- Each resident has 1-3 hand-authored trap rules with:
  - `case_signals`: keywords to match in case text
  - `case_field`: which case field to search (presenting, miss_reason, medical_truth)
  - `blind_spot`: the specific weakness that gets activated
- `_score_trap()`: scores resident-case alignment (0.0-1.0)
  - 1 signal hit = 0.6, 2+ = 1.0
- `_detect_traps()`: runs on Shift init, flags at most 1 bay as trap
  - If no natural trap exists, tries swapping residents between bays
  - Falls back to best available even if weak
- Bay gets `is_trap: bool` and `trap_detail: str` fields
- Resident's proactive prompt gets BLIND SPOT ACTIVATION instructions:
  - Present with HIGH confidence about the wrong read
  - Differential leads with plausible-but-wrong diagnosis
  - Don't flag the area they're blind to
  - A probing attending can catch it

Trap rules per resident:
- **Andre**: elderly_underestimate, social_history_miss, tox_overconfidence
- **Maya**: time_sensitive_hesitation
- **Priya**: atypical_anchoring, human_read_miss
- **Jordan**: emotional_cue_miss, substance_miss
- **Sarah**: deference_trap
- **Danny**: pediatric_miss, overconfident_wrong_plan

### 5. 1201aa3 — Consequence Severity + End-of-Shift Debrief Scoring

**CONSEQUENCE SEVERITY:**
- OLD: Autonomous actions had `was_correct` and `consequence` fields, LLM gave
  `confidence_in_action` (low/moderate/high) — severity not tracked
- NEW: `consequence_severity` field on ResidentAutonomousAction:
  none / minor / moderate / major / critical
- LLM prompt now asks for `was_correct`, `consequence`, and `consequence_severity`
- Bay stores `_autonomous_consequence_severity` for debrief scoring
- Resident state updates: incorrect actions record the consequence in `recent_mistake`

**END-OF-SHIFT DEBRIEF:**
- NEW: `shift.debrief()` method generates full report card

Per-bay reporting:
- Disposition result: OK / XX / UNRESOLVED
- True diagnosis revealed
- Correct vs incorrect outcome narrative
- Trap case status (caught/missed/unresolved)
- Autonomous action details with severity
- Reveal count (N/M unlocked)
- Attending turns spent

Shift-level metrics:
- Disposition accuracy (with partial credit for wrong-level admits)
- Cases resolved count
- Attention distribution (balanced / uneven / tunnel vision)
- Trap cases caught
- Autonomous fires + major consequences
- Warnings heeded count

**GRADING FORMULA (initial version in this commit):**
- Dispo accuracy: 40% weight
- Resolution rate: 20% weight
- Trap catch: 20% weight (15 partial credit if no traps exist)
- Consequence penalty: -7.5 per major
- Autonomous fire penalty: -3.3 per
- Clean sheet bonus: +10
- Grade thresholds: A>=90, B+>=80, B>=70, C+>=60, C>=50, D>=40, F<40

### 6. 54ae3b1 — Playtest (3 Runs on Haiku) + Trap Fix

**BUG FIX:**
- Andre's `elderly_underestimate` trap rule was matching pediatric patients
  because the rule also checked for "fall" and "age" keywords
- Fix: narrowed case_signals to just `["elderly", "geriatric"]` and added
  `min_age: 60` gate to the rule
- `_score_trap()` now checks `min_age` field and skips rule if patient is younger

**NEW FILE: PLAYTEST_REPORT.md** — detailed notes from 3 playtests:
- Run 1 (seed 42): 3/3 correct, Grade A, but exposed the elderly trap false positive
- Run 2 (seed 99): 3/3 correct, Grade B, autonomous fire from tunnel vision
- Run 3 (seed 17): 1/2 correct + 1 unresolved, Grade F, trap system working perfectly
  (Jordan presented TB as straightforward CAP with high confidence)

---

## CURRENT STATE — KEY REFERENCE

### Full Resident Roster (6 residents, pick 3 per shift)

| ID | Name | Year | Archetype | Key Strength | Key Blind Spot |
|----|------|------|-----------|--------------|----------------|
| chen_maya | Maya Chen | PGY2 | OVERCALIBRATED | Escalates appropriately, thorough hx | Over-orders, slow to commit dispo |
| okafor_dre | Andre Okafor | PGY3 | COWBOY | Fast pattern recognition, cardiac | Dismisses social hx, underestimates elderly |
| patel_priya | Priya Patel | PGY1 | ACADEMIC | Rare presentations, subtle labs | Misses human read, freezes on atypical |
| rivers_jordan | Jordan Rivers | PGY2 | BURNING_OUT | Procedures, engages on interesting cases | Misses emotional cues, substance blind |
| adeyemi_sarah | Sarah Adeyemi | PGY3 | STEADY | Clinical gestalt, patient rapport | Won't push back, understates urgency |
| kowalski_danny | Danny Kowalski | PGY1 | COWBOY | Calm in chaos, fast triage, good hands | Wide gaps, peds, acts before asking |

Selection constraints: at least 1 junior (PGY1-2), at least 1 senior (PGY3+).

### Timer Thresholds (ACUITY_TIMER_THRESHOLDS in bay.py)

| Acuity | Threshold (turns) | Warning at (75%) |
|--------|-------------------|------------------|
| 1 (IMMEDIATE) | 5 | 4 |
| 2 (EMERGENT) | 9 | 7 |
| 3 (URGENT) | 11 | 9 |
| 4 (LESS URGENT) | 16 | 12 |
| 5 (NON-URGENT) | 28 | 21 |

NOTE: Acuity 2 changed from 9 (matches previous knowledge). All others
unchanged from prior state.

### Current Grading Formula (_compute_grade in shift.py)

**Points (max ~100+ with bonuses):**
- Disposition accuracy: 45 pts (dispo_pct/100 * 45)
- Resolution rate: 15 pts (resolved_rate/100 * 15)
- Trap catch: 20 pts (traps_caught/traps_total * 20, or 15 if no traps)
- Clean sheet bonus: +15 pts (no fires + perfect dispo + 100% resolved)
- Near-clean bonus: +5 pts (no major consequences even with fires, 100% dispo)
- Attention bonus: +5 pts (heaviest bay < 50% of turns)
- Warning heeded: +3 pts each (warning fired but didn't escalate to autonomous)
- Autonomous fire: -2 pts each
- Major consequence (warned): -5 pts each
- Major consequence (unwarned): -3 pts each
- Thin-chart disposition: -5 pts each

**Grade thresholds:**
- A >= 85
- B+ >= 75
- B >= 65
- C+ >= 55
- C >= 45
- D >= 35
- F < 35

**Changes from previous grading:**
- OLD: A>=85, B+>=75, B>=65, C+>=55 (same thresholds)
- OLD: dispo 45pts, resolution 15pts, trap 20pts, consequence -3 to -5,
  autonomous fire -2, clean sheet +15, near-clean +5, attention +5, warning heeded +3
- NEW: Same structure, but added thin-chart disposition penalty (-5 each),
  wrong-level partial credit (0.5 dispo score for admit-floor vs admit-icu),
  and consequence severity is now warned vs unwarned (-5 vs -3).

### Debrief Enhancements (beyond initial scoring)

The current debrief includes features beyond what commit 1201aa3 introduced:
- **Headline**: One-sentence shift summary based on performance pattern
- **Highlight/Watchout**: Best and worst moments called out
- **Next rep focus**: One actionable improvement suggestion
- **Teaching moments**: Per-bay one-liner explaining what to learn
  - Trap missed: shows miss reason + locked reveal that would have caught it
  - Trap caught: positive reinforcement + narrative hook
  - Wrong dispo: key finding + correct treatment path
  - Autonomous fired: archetype tendency under pressure
  - Unresolved: what still needs to happen
- **Partial credit**: wrong-level admits (admit-floor vs admit-icu) get 0.5 credit
  with specific outcome narratives ("Decompensated on the floor. Rapid response at 3am.")
- **Warning tracking**: heeded (warning fired, no autonomous) vs ignored (warning + autonomous)
- **Thin-chart detection**: dispositions locked in with few reveals unlocked

### LLM Configuration (llm.py + models.yaml)

**Backends:**
- `openrouter` (default): OPENROUTER_API_KEY required
  - gameplay: anthropic/claude-haiku-4-5
  - generation: anthropic/claude-opus-4-5
- `ollama`: local inference at localhost:11434
  - gameplay: qwen3:8b
  - generation: glm-4.7-flash

**VRAM tiers (models.yaml):**
- High (20GB+): glm-4.7-flash (gameplay), qwen3.5:27b (generation)
- Medium (12GB+): qwen3:8b for both
- Low (6GB+): qwen3:8b for both

**Entry points:**
- `python run.py` — main launcher
- `python run.py --ollama` — local Ollama
- `python run.py --ollama --model qwen3:30b` — specific model
- `./ersim-setup` — checks prerequisites, detects VRAM, pulls Ollama models

### Infrastructure Changes

- All shift commands (talk, exam, test, approve_plan, etc.) are now async
  via `asyncio.to_thread()` — no more event loop blocking
- Session setup runs in background thread, WebSocket gets "Setting up" message
- WebSocket ping timeout bumped from default to 120s for slow LLMs
- Frontend handles `setup_complete` event type
- Frontend renders approval menus as clickable pill buttons
- Frontend shows animated loading spinner during shift generation

---

## BUGS & ISSUES FROM PLAYTEST

### Fixed:
1. **Elderly trap false positive on peds** (P0, fixed in 54ae3b1)
   - Andre's "elderly" rule matched 6-year-old patient due to "fall" keyword
   - Fix: narrowed signals, added `min_age: 60` gate

### Known Issues (from PLAYTEST_REPORT.md):
1. **Patient voice gets thin after 5+ turns** — cycling through "shakes head",
   "looks up" without substance. May be Haiku capacity issue or prompt issue.
2. **Reveals not unlocking organically** — 0-2/4 reveals per run. Trigger
   conditions may be too specific or players don't know what to ask.
3. **Autonomous consequence severity inconsistency** — `_autonomous_consequence_severity`
   not always set through consistent flow path.
4. **Haiku JSON parsing failures** — 5-6 JSONDecodeError warnings during Run 2.
   Pivot prompts may need tighter JSON framing for Haiku.
5. **No teaching moments in debrief** — at time of playtest. (NOTE: teaching
   moments appear to have been added in subsequent code, as `_teaching_moment()`
   exists in current shift.py but wasn't in the 1201aa3 commit diff.)

### Playtest Priority Fixes Listed:
- P0: Fix elderly trap (DONE)
- P1: Improve patient turn-by-turn depth
- P1: Add reveal progress indicators to status (partially done — status now shows reveal counts)
- P2: Add teaching moment to debrief (appears done in current code)
- P2: Harden pivot JSON parsing for Haiku
- P3: Autonomous consequence severity consistency

---

## FILES CHANGED ACROSS ALL 6 COMMITS

### New files:
- `llm.py` — centralized LLM client factory
- `run.py` — unified launcher
- `ersim-setup` — setup/install script
- `models.yaml` — model tier configuration
- `PLAYTEST_REPORT.md` — 3-run playtest notes

### Modified files:
- `shift/shift.py` — trap detection, debrief, grading, LLM centralization
- `shift/bay.py` — trap fields, consequence severity field
- `residents/schema.py` — 3 new residents, select_shift_roster(), consequence_severity
- `residents/resident.py` — trap_context in proactive(), consequence parsing
- `residents/prompts.py` — blind spot activation prompt, consequence_severity in autonomous prompt
- `cases/generator.py` — centralized LLM client
- `cases/interaction.py` — centralized LLM client
- `api/main.py` — async setup, non-blocking commands
- `api/session.py` — setup_complete flag, centralized LLM
- `api/commands.py` — all commands wrapped in asyncio.to_thread
- `frontend/src/App.jsx` — spinner, approval buttons
- `frontend/src/App.css` — spinner + button styles
- `frontend/src/useGameSocket.js` — setup_complete event handling
- `api/static/` — rebuilt frontend assets (3 rebuilds across commits)
