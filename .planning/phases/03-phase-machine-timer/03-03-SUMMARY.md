---
phase: 03-phase-machine-timer
plan: "03"
subsystem: ui
tags: [react, react-router, socket-io-client, phase-machine, game-screen, bridge]

# Dependency graph
requires:
  - phase: 03-01
    provides: TurnMachine broadcasting phase_changed + game_ended events via Pyro5 callbacks
  - phase: 03-02
    provides: GameServer.advance_phase RPC, Bridge on_phase_changed/on_game_ended callback methods, Lobby navigate to /game/:roomCode
provides:
  - React GameScreen component at /game/:roomCode
  - PhaseBadge pill component with phase-to-label and phase-to-color maps
  - CountdownDisplay component with local setInterval ticker
  - Bridge join_room Socket.IO handler so GameScreen clients join the correct room
  - /game/:roomCode route registered in App.tsx
affects: [04-game-actions, 07-reconnection, 08-timer-visual-states]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GameScreen useEffect pattern: emit join_room on mount, register phase_changed/game_ended listeners, clear interval and off() listeners on unmount"
    - "Client-side countdown: setInterval at 1000ms decrements local remainingSeconds; resets to server value on each phase_changed event"
    - "Bridge join_room handler: allows GameScreen (non-create/join path) to join Socket.IO room for room-scoped event delivery"

key-files:
  created:
    - frontend/src/pages/GameScreen.tsx
    - frontend/src/components/PhaseBadge.tsx
    - frontend/src/components/CountdownDisplay.tsx
  modified:
    - frontend/src/App.tsx
    - bridge/bridge.py

key-decisions:
  - "join_room Socket.IO handler added to bridge (Rule 2): GameScreen navigates from Lobby and must rejoin the Socket.IO room independently since create_game/join_game flow already handled room joining in Lobby context"
  - "intervalRef uses ReturnType<typeof setInterval> for cross-platform compatibility (browser vs Node types)"
  - "GameScreen shows 'Conectando...' when currentPhase is null (before first phase_changed event) per UI-SPEC copywriting contract"

patterns-established:
  - "Pattern: Socket.IO room joining for non-create/join flows — emit join_room with {room_code} on component mount"
  - "Pattern: Countdown tick using local setInterval; clear on phase_changed reset and on component unmount"

requirements-completed:
  - TURN-01
  - TURN-03

# Metrics
duration: 15min
completed: 2026-05-14
---

# Phase 3 Plan 03: GameScreen + Checkpoint Summary

**React GameScreen at /game/:roomCode rendering live phase badge and countdown from Pyro5-driven phase_changed events via Flask-SocketIO bridge**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-14T14:48:00Z
- **Completed:** 2026-05-14T15:02:26Z
- **Tasks:** 1 of 2 (Task 2 is a human-verify checkpoint — awaiting smoke test)
- **Files modified:** 5

## Accomplishments

- PhaseBadge component with Portuguese labels and per-phase hex background colors matching UI-SPEC Phase Badge Color Map
- CountdownDisplay component (28px/600 weight, aria-live polite) rendering "{N}s" format
- GameScreen with full socket lifecycle: join_room on mount, phase_changed handler with setInterval reset, game_ended handler stopping countdown
- App.tsx route `/game/:roomCode` added after `/lobby/:sessionId`
- Bridge `join_room` Socket.IO handler added so GameScreen clients can join room after navigation from Lobby (Rule 2 deviation)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PhaseBadge, CountdownDisplay, GameScreen + wire App.tsx and bridge join_room** - `f30c990` (feat)

**Plan metadata commit:** pending (after checkpoint approval)

## Files Created/Modified

- `frontend/src/components/PhaseBadge.tsx` - Pill badge with PHASE_LABELS + PHASE_COLORS maps, aria-label
- `frontend/src/components/CountdownDisplay.tsx` - Large countdown display with aria-live polite
- `frontend/src/pages/GameScreen.tsx` - GameScreen with socket lifecycle, phase/countdown/turn state
- `frontend/src/App.tsx` - Added `/game/:roomCode` route + GameScreen import
- `bridge/bridge.py` - Added `join_room` Socket.IO event handler

## Decisions Made

- **join_room handler in bridge:** GameScreen navigates from Lobby via React Router without going through `create_game`/`join_game` bridge handlers (which call Flask-SocketIO `join_room` internally). The browser's Socket.IO connection persists but the server-side room membership is not automatically transferred to the new Socket.IO request context. A dedicated `join_room` handler is required so `phase_changed`/`game_ended` emits with `to=room_code` reach the GameScreen client.
- **intervalRef closure:** `secs` variable captured in closure from `data.remaining_seconds` at each `phase_changed` event; does not read stale React state inside the interval callback.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added join_room Socket.IO handler to bridge**
- **Found during:** Task 1 (GameScreen implementation)
- **Issue:** GameScreen emits `socket.emit('join_room', { room_code: roomCode })` on mount (per UI-SPEC and RESEARCH.md Pattern 4). The bridge had no handler for this event — the emit would be silently ignored. Without joining the Socket.IO room, the client would never receive `phase_changed` or `game_ended` events (both routed via `to=data["room_code"]`), making the entire GameScreen inert.
- **Fix:** Added `@socketio.on("join_room")` handler in bridge.py that calls Flask-SocketIO's `join_room(room_code)`.
- **Files modified:** bridge/bridge.py
- **Verification:** Build passes; all 15 pytest tests pass; handler follows the same join_room() pattern as create_game/join_game handlers.
- **Committed in:** f30c990 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for end-to-end correctness — without the bridge handler, GameScreen would never receive any server events. No scope creep.

## Issues Encountered

- `node_modules` not symlinked in worktree — build run from main repo frontend directory which shares source files via git. Build succeeded with 0 TypeScript errors and 15/15 pytest tests passing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GameScreen is a display-only skeleton ready for Phase 4 (4-zone layout: image panel, hints, action zone, scoreboard)
- All socket event listeners established in GameScreen.tsx — Phase 4 adds game action event emits
- Bridge join_room handler serves as the pattern for any future "reconnect and rejoin room" flows (Phase 7)
- Smoke test checkpoint (Task 2) must be verified before Phase 3 is considered complete

## Threat Surface Scan

No new network endpoints beyond what was planned. The `join_room` bridge handler accepts any `room_code` from an untrusted browser — consistent with T-03-10 accepted risk (display-only, no sensitive data, deferred auth).

## Self-Check: PASSED

- FOUND: frontend/src/pages/GameScreen.tsx
- FOUND: frontend/src/components/PhaseBadge.tsx
- FOUND: frontend/src/components/CountdownDisplay.tsx
- FOUND: frontend/src/App.tsx (contains /game/:roomCode route)
- FOUND: bridge/bridge.py (contains join_room handler)
- FOUND: f30c990 (Task 1 commit)
- BUILD: 0 TypeScript errors, dist/ updated
- TESTS: 15/15 passed

---
*Phase: 03-phase-machine-timer*
*Completed: 2026-05-14*
