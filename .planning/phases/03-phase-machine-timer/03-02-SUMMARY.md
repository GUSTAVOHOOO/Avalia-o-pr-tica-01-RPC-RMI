---
phase: 03-phase-machine-timer
plan: "02"
subsystem: infra
tags: [pyro5, flask-socketio, turn-machine, game-server, bridge, state-machine, callbacks]

# Dependency graph
requires:
  - phase: 03-01
    provides: TurnMachine class with start(), advance_phase_manual(), on_game_ended kwarg support

provides:
  - GameServer.start_game() creates and starts TurnMachine after game_started broadcast
  - GameServer.advance_phase() RPC method for operator/test phase skipping
  - GameServer._set_session_ended() marks session ENDED when TurnMachine game ends (D-07)
  - BridgeCallbackReceiver.on_phase_changed emits phase_changed Socket.IO event to room
  - BridgeCallbackReceiver.on_game_ended emits game_ended Socket.IO event to room

affects:
  - 03-03 (GameScreen frontend listens for phase_changed / game_ended Socket.IO events)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TurnMachine created inside start_game() lock; start() called outside lock after game_started broadcast (T-03-07)"
    - "on_game_ended callback fires from TurnMachine timer thread; acquires GameServer.lock independently (T-03-10)"
    - "advance_phase() NOT @oneway — returns bool so test clients can assert state (Pitfall 5)"
    - "BridgeCallbackReceiver callback methods: @oneway on top, @callback below, try/except wrapping socketio.emit"

key-files:
  created: []
  modified:
    - server/turn_machine.py
    - server/game_server.py
    - bridge/bridge.py

key-decisions:
  - "TurnMachine on_game_ended kwarg added in turn_machine.py; callback fires after broadcaster.broadcast('game_ended',...) with no lock held (deadlock avoidance)"
  - "advance_phase() not @oneway — must return bool for Pyro5 test client assertions (RESEARCH.md Pitfall 5)"
  - "GameSession.turn_machine typed as object rather than TurnMachine to avoid circular import risk"
  - "turn_machine.start() called outside lock immediately after game_started broadcast to ensure browser navigation happens before first phase_changed fires (T-03-07)"

patterns-established:
  - "Pattern: TurnMachine callback ordering — broadcaster.broadcast(game_started) → turn_machine.start() — enforced in start_game()"
  - "Pattern: BridgeCallbackReceiver on_* methods use @Pyro5.api.oneway + @Pyro5.api.callback decorator pair with try/except wrapping"

requirements-completed: [TURN-01, TURN-02, TURN-03, TURN-04]

# Metrics
duration: 15min
completed: 2026-05-14
---

# Phase 3 Plan 02: GameServer + Bridge TurnMachine Wiring Summary

**TurnMachine wired into GameServer.start_game() with on_game_ended session-ENDED callback, advance_phase() RPC method added, and BridgeCallbackReceiver extended with on_phase_changed/on_game_ended Socket.IO forwarding**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-14T00:00:00Z
- **Completed:** 2026-05-14
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- TurnMachine is now created inside start_game() with a closure callback that marks the session ENDED when the game finishes (D-07)
- turn_machine.start() fires after game_started broadcast — ensures browsers navigate to GameScreen before the first phase_changed arrives (T-03-07)
- advance_phase() RPC method added to GameServer for operator/test phase skipping (not @oneway — returns bool)
- BridgeCallbackReceiver extended with on_phase_changed and on_game_ended following the established @oneway+@callback pattern
- All 15 existing tests still pass after changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend GameServer — wire TurnMachine into start_game() and add advance_phase()** - `76b9865` (feat)
2. **Task 2: Extend BridgeCallbackReceiver with on_phase_changed and on_game_ended** - `7ff06c6` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `server/turn_machine.py` - Added on_game_ended kwarg to __init__(); calls it after game_ended broadcast (D-07, T-03-10)
- `server/game_server.py` - Added turn_machine field to GameSession; added _set_session_ended(); modified start_game() to create/start TurnMachine; added advance_phase() method
- `bridge/bridge.py` - Added on_phase_changed and on_game_ended to BridgeCallbackReceiver

## Decisions Made

- TurnMachine typed as `object` in GameSession dataclass to avoid circular import (TurnMachine is in server.turn_machine which imports config, no cycle risk in practice, but typing as object is safer)
- advance_phase() intentionally not @oneway — Pyro5 test clients need the bool return value to assert phase was advanced (RESEARCH.md Pitfall 5)
- on_game_ended callback closure captures room_code_for_cb before lock release — avoids referencing session state that could be mutated after lock is released

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added on_game_ended kwarg to TurnMachine.__init__()**
- **Found during:** Task 1 (wiring TurnMachine into start_game())
- **Issue:** Plan's Task 1 action noted that TurnMachine may not yet have the on_game_ended kwarg — verified it was absent from the constructor in server/turn_machine.py
- **Fix:** Added on_game_ended=None kwarg to __init__, stored as self._on_game_ended; added call after broadcaster.broadcast("game_ended", ...) with lock released (T-03-10 compliance)
- **Files modified:** server/turn_machine.py
- **Verification:** pytest tests/ -q — 15 passed; test_game_ended_after_last_turn explicitly tests the game_ended broadcast path
- **Committed in:** 76b9865 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical functionality required by plan)
**Impact on plan:** Necessary — without on_game_ended in TurnMachine, D-07 session-ENDED wiring was impossible. Plan's action note explicitly anticipated this case.

## Issues Encountered

- Initial verification script ran against the main repo path (not the worktree), causing false "advance_phase missing" assertion. Re-running from the worktree directory confirmed all changes were correctly applied.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GameServer now drives full turn/phase lifecycle via TurnMachine
- BridgeCallbackReceiver forwards phase_changed and game_ended to browsers via Socket.IO
- Phase 03-03 (GameScreen frontend) can now listen for phase_changed and game_ended events and render the appropriate UI for each phase

---
*Phase: 03-phase-machine-timer*
*Completed: 2026-05-14*
