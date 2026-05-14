---
phase: 04-core-turn-loop
plan: "03"
subsystem: backend
tags: [rpc, scoring, turn-state, pytest]

# Dependency graph
requires:
  - phase: 04-02
    provides: TurnState lifecycle, image assignments, and GameServer callback wiring
provides:
  - submit_hint, submit_guess, skip_guess, and get_scores RPC methods
  - Pure _calculate_score_deltas scoring function
  - Score accumulation and SCORE_UPDATED broadcast payload
affects: [04-04-bridge-events, 04-05-game-screen, 05-exchange-spy-mechanics]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GameServer action RPCs use lock -> snapshot -> outside-lock broadcast"
    - "Scoring is pure function first, session accumulation second"

key-files:
  created: []
  modified:
    - server/turn_machine.py
    - server/game_server.py
    - tests/test_scoring.py
    - tests/test_turn_state.py

key-decisions:
  - "Owner scoring only applies when guesses_made identifies target owners; SCORE-01 unit test isolates guesser tiering without owner targets"
  - "RPC methods return ack dictionaries for bridge/client handling and are not @oneway"

patterns-established:
  - "Pattern: submit_hint auto-advances via TurnMachine.advance_to_guess_phase after all hints arrive"
  - "Pattern: _accumulate_scores fills missing guessers with None before score calculation"

requirements-completed:
  - HINT-01
  - HINT-02
  - HINT-03
  - HINT-04
  - GUESS-01
  - GUESS-02
  - GUESS-04
  - GUESS-05
  - SCORE-01
  - SCORE-02
  - SCORE-03
  - SCORE-04
  - SCORE-05

# Metrics
duration: 45min
completed: 2026-05-14
---

# Phase 04 Plan 03: Turn Action RPC and Scoring Summary

**Hint submission, guessing, skip, score retrieval, and automatic scoring now run through tested server-side RPC methods.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-14T19:35:00Z
- **Completed:** 2026-05-14T20:20:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `_calculate_score_deltas()` with tiered guesser points, solo bonus, and owner scoring.
- Added `TurnMachine.advance_to_guess_phase()` for the all-hints-submitted fast path.
- Added `submit_hint`, `submit_guess`, `skip_guess`, and `get_scores` to `GameServer`.
- Replaced the score callback stub with real accumulated scoring and `score_updated` broadcast.
- Converted all Phase 4 scoring and turn-state stubs into passing tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add scoring deltas and advance_to_guess_phase** - `5ed86c4` (feat)
2. **Task 2: Add action RPC methods and full turn-state tests** - `c62b725` (feat)

## Files Created/Modified

- `server/turn_machine.py` - Scoring function and hint-to-guess fast path.
- `server/game_server.py` - Action RPC methods and score accumulation.
- `tests/test_scoring.py` - 4 passing scoring tests.
- `tests/test_turn_state.py` - 14 passing turn-state/action tests.

## Verification

- `python -m pytest tests/test_scoring.py -v` - 4 passed.
- `python -m pytest tests/test_turn_state.py -v` - 14 passed.
- Score formula spot-check - SCORE-01 OK.
- `python -m pytest tests/ -x` - 33 passed.

## Decisions Made

- Kept score calculation as a module-level pure function for direct unit testing.
- Returned structured ack dictionaries from RPC methods so the bridge can forward errors to the browser.

## Deviations from Plan

None - plan executed exactly as written.

---

**Total deviations:** 0 auto-fixed.
**Impact on plan:** No scope changes.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

- Key files exist.
- Task commits exist.
- Acceptance criteria passed.
- Plan-level verification passed.

## Next Phase Readiness

Ready for `04-04`: bridge Socket.IO handlers can call the new RPC methods and forward callback events to browser rooms.

---
*Phase: 04-core-turn-loop*
*Completed: 2026-05-14*
