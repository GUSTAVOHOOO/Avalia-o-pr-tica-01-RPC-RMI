---
phase: 04-core-turn-loop
plan: "02"
subsystem: backend
tags: [turn-state, turn-machine, game-server, image-assignment, pytest]

# Dependency graph
requires:
  - phase: 04-01
    provides: Phase 4 pytest stubs and static image manifest
provides:
  - TurnState dataclass and hint completion helper
  - TurnMachine hooks for ROUND_START, HINT_PHASE, GUESS_PHASE, and SCORING_PHASE
  - GameServer image manifest loading and per-turn image assignment staging
affects: [04-03-scoring-rpc, 04-04-bridge-events, 04-05-game-screen]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TurnMachine keeps network broadcasts outside its RLock"
    - "ROUND_START assigns images via no-arg GameServer callback; HINT_PHASE consumes staged assignments"
    - "GameSession holds current_image_assignments as the handoff between image assignment and TurnState creation"

key-files:
  created:
    - server/turn_state.py
  modified:
    - server/turn_machine.py
    - server/game_server.py
    - tests/test_turn_state.py

key-decisions:
  - "Kept TurnMachine player_ids optional to preserve existing Phase 3 tests that instantiate TurnMachine directly"
  - "Preserved the existing get_session phase/remaining_seconds enhancement already present in the working tree"

patterns-established:
  - "Pattern: TurnState is pure Python and free of Pyro5/config imports"
  - "Pattern: GameServer stages image assignments in GameSession, then TurnMachine consumes a snapshot at HINT_PHASE"

requirements-completed:
  - HINT-01
  - HINT-02
  - HINT-03
  - HINT-04
  - GUESS-05
  - IMAGE-01
  - IMAGE-02
  - IMAGE-03

# Metrics
duration: 35min
completed: 2026-05-14
---

# Phase 04 Plan 02: TurnState and Image Assignment Summary

**TurnState lifecycle and GameServer image assignment now feed object assignments into the timed phase machine.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-05-14T19:00:00Z
- **Completed:** 2026-05-14T19:35:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `server/turn_state.py` with `TurnState` fields for hints, guesses, correct guesses, and image assignments.
- Extended `TurnMachine` with player IDs, current turn state, HINT_PHASE creation, GUESS_PHASE hint backfill/reveal, ROUND_START image callback, and SCORING_PHASE callback.
- Extended `GameServer` with `_image_manifest`, `_used_images_this_game`, `accumulated_scores`, `current_image_assignments`, image assignment, staged assignment consumption, and TurnMachine callback wiring.
- Unskipped Phase 4 tests for timer backfilled hints, manifest loading, and private object assignment payloads.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TurnState dataclass and extend TurnMachine with phase hooks** - `a51085d` (feat)
2. **Task 2: Extend GameServer with image bank, accumulated_scores, and TurnMachine wiring** - `8dd5a47` (feat)

## Files Created/Modified

- `server/turn_state.py` - Pure dataclass for per-turn state.
- `server/turn_machine.py` - Phase hooks and TurnState lifecycle.
- `server/game_server.py` - Image manifest loading, assignment staging, callback wiring, and score callback stub.
- `tests/test_turn_state.py` - Three now-active tests for HINT-03 and IMAGE-01/02.

## Verification

- `python -m pytest tests/test_turn_machine.py -x` - 5 passed.
- `python -m pytest tests/test_session.py -x` - 6 passed.
- `python -m pytest tests/test_turn_state.py -x -v` - 3 passed, 11 skipped.
- `python -m pytest tests/ -x` - 18 passed, 15 skipped.
- Direct acceptance checks confirmed `TurnState`, `TurnMachine`, `GameServer._image_manifest`, `_used_images_this_game`, `GameSession.accumulated_scores`, and `GameSession.current_image_assignments`.

## Decisions Made

- Kept `player_ids` optional in `TurnMachine.__init__` so Phase 3 unit tests remain compatible while Phase 4 passes player IDs from `GameServer.start_game()`.
- Kept the current working-tree `get_session()` enhancement because the app already relies on `join_room` returning current phase and timer state.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test expectation] Hint backfill test advanced to the wrong phase**
- **Found during:** Task 2 verification
- **Issue:** The test checked empty hint backfill after entering `HINT_PHASE`, but backfill is performed on transition to `GUESS_PHASE`.
- **Fix:** Advanced the test one additional phase before asserting `hints_submitted`.
- **Files modified:** `tests/test_turn_state.py`
- **Verification:** `python -m pytest tests/test_turn_state.py -x -v`
- **Committed in:** `8dd5a47`

---

**Total deviations:** 1 auto-fixed (test expectation).
**Impact on plan:** No scope change; test now matches the phase contract.

## Issues Encountered

Existing working-tree changes in `server/game_server.py` enhanced `get_session()` to return phase and timer state. They were preserved because they support the live `join_room` behavior already working in the browser.

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

- Key files exist.
- Task commits exist.
- Acceptance criteria passed.
- Plan-level verification passed.

## Next Phase Readiness

Ready for `04-03`: RPC methods for hints/guesses, scoring deltas, and score accumulation can now attach to `TurnState`.

---
*Phase: 04-core-turn-loop*
*Completed: 2026-05-14*
