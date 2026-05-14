---
phase: 04-core-turn-loop
plan: "01"
subsystem: testing
tags: [pytest, pillow, image-bank, wave-0]

# Dependency graph
requires:
  - phase: 03-phase-machine-timer
    provides: TurnMachine tests and existing pytest structure used as the model for Phase 4 stubs
provides:
  - Skipped pytest stubs for Phase 4 turn-state behavior
  - Skipped pytest stubs for Phase 4 scoring behavior
  - Static image bank manifest and JPEG placeholder assets
affects: [04-02-turn-state, 04-03-scoring, 04-04-bridge-static-images]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 stubs skip before importing future production modules"
    - "Image manifest maps filename to canonical lowercase object name"

key-files:
  created:
    - tests/test_turn_state.py
    - tests/test_scoring.py
    - server/images/manifest.json
    - server/images/*.jpg
  modified: []

key-decisions:
  - "Use 12 single-word English nouns in manifest.json so 4 players can play 3 turns without repeats"
  - "Generate simple JPEG placeholders locally with Pillow instead of adding external image dependencies"

patterns-established:
  - "Pattern: Future-facing pytest stubs call pytest.skip before imports for modules planned later in the phase"
  - "Pattern: Static image assets live under server/images with manifest-controlled filenames"

requirements-completed:
  - HINT-01
  - HINT-02
  - HINT-03
  - HINT-04
  - GUESS-01
  - GUESS-02
  - GUESS-04
  - GUESS-05
  - IMAGE-01
  - IMAGE-02
  - SCORE-01
  - SCORE-02
  - SCORE-03
  - SCORE-04
  - SCORE-05

# Metrics
duration: 25min
completed: 2026-05-14
---

# Phase 04 Plan 01: Test Infrastructure and Image Bank Summary

**Wave 0 pytest stubs and a static image manifest establish the executable contract for Phase 4 implementation.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-14T18:22:00Z
- **Completed:** 2026-05-14T18:47:00Z
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments

- Added 14 skipped `tests/test_turn_state.py` stubs covering hints, guesses, image assignment payloads, and score retrieval.
- Added 4 skipped `tests/test_scoring.py` stubs covering tiered guesser points, solo bonus, owner scoring, and score payload shape.
- Created `server/images/manifest.json` with 12 canonical object names and matching placeholder JPEGs.
- Verified the new stubs collect cleanly and the full existing test suite still passes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test stubs for TurnState behavior** - `fce2156` (test)
2. **Task 2: Create scoring test stubs and image bank** - `b4e6609` (test)

## Files Created/Modified

- `tests/test_turn_state.py` - Skipped future tests for HINT/GUESS/IMAGE/SCORE server behavior.
- `tests/test_scoring.py` - Skipped future tests for pure scoring logic and score payload shape.
- `server/images/manifest.json` - Filename-to-object mapping for static image assignment.
- `server/images/*.jpg` - Pillow-generated placeholder JPEGs for every manifest entry.

## Verification

- `python -m pytest tests/test_turn_state.py -v` - 14 skipped, exit 0.
- `python -m pytest tests/test_scoring.py -v` - 4 skipped, exit 0.
- `python -c "import json, pathlib; ..."` - manifest OK: 12 entries, 12 jpg files.
- `python -m pytest tests/ -x` - 15 passed, 18 skipped.

## Decisions Made

- Used 12 objects rather than the minimum 8 to support three 4-player turns without immediate reuse.
- Kept object names lowercase, single-word English nouns to match the later synonym/arbitration contract.

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

Ready for `04-02`: production `TurnState`, image manifest loading, per-phase hooks, and hint/image assignment behavior can now replace the Wave 0 skips.

---
*Phase: 04-core-turn-loop*
*Completed: 2026-05-14*
