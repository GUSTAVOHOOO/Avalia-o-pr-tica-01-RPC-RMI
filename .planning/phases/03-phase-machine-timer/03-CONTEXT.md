# Phase 3: Phase Machine + Timer - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

The server drives a full WAITING → ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END cycle. Per-phase timers fire automatically via `threading.Timer` with a generation counter to prevent double-advances. After the last turn, the server emits `GAME_ENDED` and marks the session `ENDED`. The React frontend gains a new `/game/:roomCode` route showing a minimal phase indicator (phase name + countdown) to verify PHASE_CHANGED events arrive in real browser sessions.

Requirements in scope: TURN-01, TURN-02, TURN-03, TURN-04

</domain>

<decisions>
## Implementation Decisions

### Phase Machine Structure
- **D-01:** Phase machine logic lives in a new `TurnMachine` class in `server/turn_machine.py`. Follows the existing pattern: each concern is its own module (`game_server.py`, `event_broadcaster.py`, now `turn_machine.py`).
- **D-02:** `GameSession` holds a `TurnMachine` instance (`session.turn_machine`). `GameServer` delegates phase advance and timer management to it — `GameServer` itself gains no new timer methods.
- **D-03:** `TurnMachine.__init__` receives `EventBroadcaster` as a dependency (dependency injection). It calls `broadcaster.broadcast()` directly when a timer fires or a phase advances — no back-reference to `GameServer`.

### Timer Durations
- **D-04:** Per-phase durations are configured as `PHASE_DURATIONS` dict in `config.py`. One place to tune without touching game logic. Example:
  ```python
  PHASE_DURATIONS = {
      "ROUND_START":    5,
      "HINT_PHASE":    60,
      "GUESS_PHASE":   60,
      "EXCHANGE_PHASE": 45,
      "SPY_PHASE":     30,
      "SCORING_PHASE": 15,
      "TURN_END":       5,
  }
  ```
- **D-05:** ROUND_START and TURN_END are short transitional phases (5s each) — just enough for the UI to show "Round starting..." or "Calculating scores..." before the machine advances.

### Multi-Turn Loop
- **D-06:** ROUND_START happens once at game start. From turn 2 onward, TURN_END transitions directly into HINT_PHASE (skipping ROUND_START). Phase 4 will use this moment to trigger image redistribution.
- **D-07:** When the last turn ends (`current_turn == max_turns` at TURN_END), the server broadcasts `GAME_ENDED` and sets `session.status = "ENDED"`. Phase 7 wires the frontend's post-game response to this event.
- **D-08:** `TurnMachine` owns `current_turn` (starts at 1, increments at each TURN_END). `max_turns` is passed in at construction from `GameSession.max_turns`. TurnMachine is the single source of truth for turn progress.

### Frontend Scope
- **D-09:** Phase 3 adds a minimal React game screen at `/game/:roomCode`. After `game_started` fires, all connected browsers navigate to this route. The screen shows: current phase name + countdown seconds. No game action buttons (those come in Phase 4).
- **D-10:** Bridge gains `on_phase_changed` and `on_game_ended` methods on `BridgeCallbackReceiver`, routing events to the correct Flask-SocketIO room via `data["room_code"]`.

### Claude's Discretion
- Generation counter implementation: `TurnMachine` maintains a `_generation: int` field, incremented on every manual or timer-driven advance. Timer callbacks receive the generation at creation; they check `self._generation == expected_generation` before advancing. If mismatch: stale timer, no-op.
- State machine order per TURN-01: WAITING → ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END (→ HINT_PHASE for next turn, or GAME_ENDED if last turn).
- `advance_phase(player_id=None)` is exposed on `GameServer` as a test/operator RPC call, allowing the success-criteria smoke test to manually skip phases and verify timer cancellation.
- `TurnMachine` lock: use a `threading.RLock` (matching `GameServer.lock` pattern) protecting `current_phase`, `current_turn`, `_generation`, and the active `threading.Timer` handle.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §TURN-01 through TURN-04 — Full turn/phase machine requirements with acceptance criteria
- `.planning/ROADMAP.md` §Phase 3 — 4 success criteria that must all be TRUE for phase completion

### Architecture
- `.planning/PROJECT.md` §Architecture Decision — Bridge WebSocket diagram; all broadcast paths go GameServer → EventBroadcaster → BridgeCallbackReceiver → socketio.emit()
- `.planning/PROJECT.md` §Key Decisions — locked infrastructure decisions (@oneway, RLock, per-thread proxies)

### Prior Phase Decisions
- `.planning/phases/01-rpc-infrastructure-callback-pipeline/01-CONTEXT.md` §decisions — D-08 (@oneway), D-09 (broadcast methods must be @oneway), D-10 (per-thread proxy)
- `.planning/phases/02-player-session-lobby/02-CONTEXT.md` §decisions — D-12/D-13 (room-based Socket.IO routing via room_code in payload), D-14 (BridgeCallbackReceiver extension pattern)

### Technology
- `CLAUDE.md` §Key Pyro5 Patterns — patterns 1–4 (single-instance server, @oneway, per-thread proxy, bridge callback object)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/game_server.py` — `GameServer` class with `self.lock` (RLock), `self.broadcaster` (EventBroadcaster), `self.sessions` dict. Phase 3 adds `session.turn_machine` to each `GameSession` and a new `advance_phase(player_id)` RPC method.
- `server/event_broadcaster.py` — `EventBroadcaster.broadcast(event_type, data)` already handles fan-out with failure cleanup. `TurnMachine` calls `broadcaster.broadcast("phase_changed", {...})` directly.
- `bridge/bridge.py` — `BridgeCallbackReceiver` extension pattern: add `on_phase_changed` and `on_game_ended` using `@Pyro5.api.oneway @Pyro5.api.callback`, routing to `data["room_code"]` (established in D-14, Phase 2).
- `config.py` — Add `PHASE_DURATIONS` dict alongside existing `NS_HOST`, `BRIDGE_PORT`, etc.

### Established Patterns
- All broadcast-triggering methods on `GameServer` must use `@Pyro5.api.oneway` (D-09, Phase 1) — `advance_phase` if it triggers broadcast must call broadcaster after releasing lock, or be `@oneway` itself.
- Broadcast OUTSIDE the lock — EventBroadcaster does network I/O (established in `join_game`, `start_game`, `leave_game`). TurnMachine timer callbacks must follow the same pattern: release RLock before calling `broadcaster.broadcast()`.
- `BridgeCallbackReceiver` methods use `@Pyro5.api.oneway @Pyro5.api.callback` — new `on_phase_changed` and `on_game_ended` methods follow this exact pattern.
- Room routing: every broadcast payload includes `"room_code"` so the bridge can route to the correct Socket.IO room (`to=data["room_code"]`).

### Integration Points
- `server/game_server.py`: `start_game()` creates `TurnMachine` for the session and calls `turn_machine.start()` to kick off ROUND_START after broadcasting `GAME_STARTED`.
- `server/turn_machine.py` (new): `TurnMachine(room_code, max_turns, broadcaster)` — owns phase state, timer, generation counter.
- `bridge/bridge.py`: Two new `BridgeCallbackReceiver` methods + two new `@socketio.on` handlers if the frontend needs to manually trigger phase advance (for testing).
- `frontend/src/`: New route `/game/:roomCode` in React Router + `GameScreen` component; listens for `phase_changed` Socket.IO event.

</code_context>

<specifics>
## Specific Ideas

- `advance_phase` RPC method on `GameServer` is needed for success criterion #3 (verify manual advance cancels the old timer). Keep it simple — takes `player_id` for authorization but Phase 3 does not need strict authorization; Phase 4+ can tighten it.
- The phase indicator in `/game/:roomCode` should show: current phase name + seconds remaining. No styling beyond readable text — Phase 8 handles polish.
- Timer cancellation: `TurnMachine` holds a reference to the active `threading.Timer` handle. On manual advance, call `timer_handle.cancel()` before starting the new timer.

</specifics>

<deferred>
## Deferred Ideas

- Timer color states (green/yellow/red) on the frontend countdown — deferred to Phase 8 per UI-05 in REQUIREMENTS.md. Phase 3 shows plain countdown numbers.
- Per-game configurable phase durations (host sets their own timer lengths) — deferred to v2 per REQUIREMENTS.md.
- Authorization on `advance_phase` (only host or admin can skip phases) — defer to a later phase; Phase 3 uses it as a test utility.

</deferred>

---

*Phase: 3-phase-machine-timer*
*Context gathered: 2026-05-14*
