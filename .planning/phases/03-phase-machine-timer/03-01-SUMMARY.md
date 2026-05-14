---
phase: 03-phase-machine-timer
plan: "01"
subsystem: api
tags: [python, threading, state-machine, timer, generation-counter, pytest]

# Dependency graph
requires:
  - phase: 02-player-session-lobby
    provides: EventBroadcaster.broadcast() fan-out pattern, GameSession/GameServer RLock pattern
provides:
  - TurnMachine class with start(), advance_phase_manual(), remaining_seconds
  - PHASE_SEQUENCE constant (ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END)
  - PHASE_DURATIONS config dict (7 entries, tunable without touching game logic)
  - 5 unit tests covering TURN-01 through TURN-04 and D-07
affects: [03-02, game-server-wiring, bridge, frontend-game-screen]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Generation counter: _generation int incremented on every advance; timer callback checks expected_generation before acting — prevents stale timer double-advance"
    - "Broadcast-outside-lock: all broadcaster.broadcast() calls after with self.lock block exits — no network I/O under RLock"
    - "Monkeypatch-and-restore: timing tests patch config.PHASE_DURATIONS with 0.05s values in try/finally"

key-files:
  created:
    - server/turn_machine.py
    - tests/test_turn_machine.py
  modified:
    - config.py

key-decisions:
  - "TurnMachine is a pure Python class with no Pyro5 import — enables in-process unit testing without daemon startup"
  - "GAME_ENDED is handled by _compute_next returning 'GAME_ENDED' when current_turn >= max_turns at TURN_END"
  - "test_game_ended_after_last_turn requires 7 advance_phase_manual() calls (6 to reach TURN_END + 1 from TURN_END to GAME_ENDED)"

patterns-established:
  - "Pattern: TurnMachine._advance_to() uses broadcast-outside-lock (collect state under lock, broadcast after lock release)"
  - "Pattern: Timer closure captures gen_snapshot local variable — never references self._generation directly in closure"
  - "Pattern: FakeBroadcaster collects {type, phase, data} dicts for test assertions"

requirements-completed: [TURN-01, TURN-02, TURN-03, TURN-04]

# Metrics
duration: 20min
completed: 2026-05-14
---

# Phase 03 Plan 01: TurnMachine State Machine Summary

**Generation-counter-guarded TurnMachine driving 7-phase game loop via threading.Timer, with 5 pytest unit tests verifying TURN-01 through TURN-04**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-14T00:00:00Z
- **Completed:** 2026-05-14
- **Tasks:** 3
- **Files modified:** 3 (config.py modified; server/turn_machine.py created; tests/test_turn_machine.py created)

## Accomplishments

- Added PHASE_DURATIONS dict to config.py (7 entries from D-04, one canonical tuning location)
- Implemented TurnMachine as pure Python class with generation counter, RLock, and broadcast-outside-lock pattern
- Delivered 5 passing unit tests covering the full TURN-01 through TURN-04 + D-07 requirement set

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PHASE_DURATIONS to config.py** - `3c13326` (feat)
2. **Task 2: Implement TurnMachine in server/turn_machine.py** - `f15604e` (feat)
3. **Task 3: Write unit tests in tests/test_turn_machine.py** - `cc99301` (test)

## Files Created/Modified

- `config.py` — Added PHASE_DURATIONS dict with 7 phase timer values (D-04)
- `server/turn_machine.py` — TurnMachine class: start(), _advance_to(), _compute_next(), advance_phase_manual(), remaining_seconds
- `tests/test_turn_machine.py` — 5 unit tests using FakeBroadcaster; timing tests monkeypatch config.PHASE_DURATIONS

## Decisions Made

- TurnMachine is pure Python (no Pyro5 import) so it can be unit tested in-process without any daemon startup overhead
- test_game_ended_after_last_turn needs 7 advance calls (not 6): 6 to reach TURN_END, then 1 more from TURN_END to trigger GAME_ENDED via _compute_next
- Timer closure captures `gen_snapshot` and `_phase_snapshot` as local variables to avoid stale-closure bugs on mutable self fields

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test count for game_ended test corrected from 6 to 7 advances**
- **Found during:** Task 3 (test_turn_machine.py)
- **Issue:** Plan stated "advance_phase_manual() 6 times to reach TURN_END" then asserted game_ended event, but GAME_ENDED is triggered by advancing FROM TURN_END (requires 7th call). First run showed 7 phase_changed events ending at TURN_END with no game_ended.
- **Fix:** Added 7th `tm.advance_phase_manual()` call in test_game_ended_after_last_turn
- **Files modified:** tests/test_turn_machine.py
- **Verification:** All 5 tests pass; 15/15 full suite green
- **Committed in:** cc99301 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test count)
**Impact on plan:** Minor test fix; no scope change. The TurnMachine implementation was correct — plan description was slightly ambiguous about whether the assertion was on the 6th or 7th advance.

## Issues Encountered

None beyond the test count correction documented above.

## User Setup Required

None - no external service configuration required. All tests run in-process without any daemon startup.

## Next Phase Readiness

- TurnMachine fully tested and ready for integration into GameServer (Plan 03-02)
- Plan 03-02 will: add session.turn_machine to GameSession, call turn_machine.start() in start_game(), add advance_phase() RPC method to GameServer
- Plan 03-02 will also add on_phase_changed/on_game_ended to BridgeCallbackReceiver
- No blockers

---
*Phase: 03-phase-machine-timer*
*Completed: 2026-05-14*
