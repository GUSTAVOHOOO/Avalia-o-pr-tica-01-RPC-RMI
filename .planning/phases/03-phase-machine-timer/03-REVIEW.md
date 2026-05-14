---
phase: 03-phase-machine-timer
reviewed: 2026-05-14T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - bridge/bridge.py
  - frontend/src/App.tsx
  - frontend/src/components/CountdownDisplay.tsx
  - frontend/src/components/PhaseBadge.tsx
  - frontend/src/pages/GameScreen.tsx
  - server/game_server.py
  - server/turn_machine.py
  - tests/test_turn_machine.py
findings:
  critical: 3
  warning: 5
  info: 3
  total: 11
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 3 implements TurnMachine (server-side FSM with threading.Timer), GameServer wiring for phase progression, and the GameScreen frontend component. The core architecture is sound: the generation-counter anti-double-advance guard (TURN-04), lock-release-before-broadcast pattern, and per-thread Pyro5 proxy are all correctly applied.

Three blockers were found. Two relate to unguarded dict access in the bridge that crash the SocketIO handler on malformed client payloads. One is an unhandled `ValueError` in `_compute_next` triggered when `advance_phase` is called via RPC on a session that has already ended (the player is still in `_player_to_room` after game end, no status guard in the explicit-player-id path).

---

## Critical Issues

### CR-01: `_compute_next` crashes with `ValueError` on out-of-sequence phases

**File:** `server/turn_machine.py:167`
**Issue:** `PHASE_SEQUENCE.index(current_phase)` raises `ValueError` if `current_phase` is not in `PHASE_SEQUENCE`. Two reachable states are not covered:

- `"WAITING"` — initial state before `start()` is called. If `advance_phase_manual()` is called before `start()` (e.g., by a race via the `advance_phase` RPC), the crash is uncaught inside `TurnMachine` and propagates to the RPC caller as an unhandled exception.
- `"GAME_ENDED"` — state after the game finishes. `_set_session_ended` marks `session.status = "ENDED"` but does **not** clear `_player_to_room`. The explicit-player-id path in `GameServer.advance_phase` (line 344) resolves the room via `_player_to_room` without checking `session.status`, then calls `tm.advance_phase_manual()` on the ended machine — `_compute_next("GAME_ENDED")` raises `ValueError`.

```python
# server/turn_machine.py:161-168 — current code
def _compute_next(self, current_phase: str) -> str:
    with self.lock:
        if current_phase == "TURN_END":
            if self.current_turn >= self.max_turns:
                return "GAME_ENDED"
            self.current_turn += 1
            return "HINT_PHASE"
        idx = PHASE_SEQUENCE.index(current_phase)   # crashes on WAITING / GAME_ENDED
        return PHASE_SEQUENCE[idx + 1]
```

**Fix — two-part:**

Part 1: Guard `_compute_next` against terminal/pre-start states:
```python
def _compute_next(self, current_phase: str) -> str:
    with self.lock:
        if current_phase == "TURN_END":
            if self.current_turn >= self.max_turns:
                return "GAME_ENDED"
            self.current_turn += 1
            return "HINT_PHASE"
        if current_phase in ("GAME_ENDED", "WAITING"):
            # No valid transition from terminal/pre-start state
            return current_phase   # no-op
        try:
            idx = PHASE_SEQUENCE.index(current_phase)
        except ValueError:
            logger.warning("[TurnMachine] Unknown phase '%s' in _compute_next", current_phase)
            return current_phase
        return PHASE_SEQUENCE[idx + 1]
```

Part 2: Guard `GameServer.advance_phase` against non-IN_PROGRESS sessions when a player_id is provided:
```python
# server/game_server.py — inside advance_phase, after resolving session
if session is None or session.turn_machine is None:
    return False
if session.status != "IN_PROGRESS":   # add this guard
    return False
```

---

### CR-02: Unguarded `data[key]` access in `handle_create_game` and `handle_join_game` crashes SocketIO handler

**File:** `bridge/bridge.py:227` and `bridge/bridge.py:249`
**Issue:** Both handlers access dict keys directly without a try/except or key-existence check. A client sending a malformed payload (missing `player_name`, `max_turns`, or `room_code`) causes a `KeyError` that propagates uncaught out of the SocketIO handler. Flask-SocketIO swallows unhandled exceptions in event handlers without sending an error acknowledgment to the client, silently dropping the connection-level ack.

```python
# bridge/bridge.py:227 — direct access, no guard
result = proxy.create_game(
    data["player_name"], _cb_uri, int(data["max_turns"])   # KeyError if missing
)

# bridge/bridge.py:249
result = proxy.join_game(
    data["player_name"], _cb_uri, data["room_code"]        # KeyError if missing
)
```

**Fix:** Add input validation at the handler boundary:
```python
@socketio.on("create_game")
def handle_create_game(data):
    if not isinstance(data, dict):
        return {"error": "payload invalido"}
    player_name = data.get("player_name", "")
    max_turns_raw = data.get("max_turns")
    if not player_name or max_turns_raw is None:
        return {"error": "player_name e max_turns sao obrigatorios"}
    try:
        max_turns = int(max_turns_raw)
    except (TypeError, ValueError):
        return {"error": "max_turns deve ser inteiro"}
    proxy = get_game_server_proxy()
    result = proxy.create_game(player_name, _cb_uri, max_turns)
    ...
```

Apply equivalent validation to `handle_join_game` for `player_name` and `room_code`.

---

### CR-03: `handle_join_room` joins any arbitrary Socket.IO room without server-side authorization

**File:** `bridge/bridge.py:301-314`
**Issue:** `handle_join_room` calls `join_room(room_code)` for any non-empty string supplied by the client, with no verification that the room_code exists in `GameServer.sessions` or that the caller is a participant. Any connected client can join any room by sending `{room_code: "XYZABC"}` and will receive all subsequent `phase_changed` and `game_ended` events for that room — including turn counts and timing information.

```python
@socketio.on("join_room")
def handle_join_room(data):
    room_code = (data or {}).get("room_code", "")
    if not room_code:
        return {"error": "room_code required"}
    join_room(room_code)   # no authorization check
```

**Fix:** Verify the requesting client's `player_id` (from `_sid_to_player`) is actually a member of the requested room before calling `join_room`:
```python
@socketio.on("join_room")
def handle_join_room(data):
    room_code = (data or {}).get("room_code", "")
    if not room_code:
        return {"error": "room_code required"}
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "nao autenticado"}
    # Verify membership via RPC (or keep a local set of player->room mappings)
    proxy = get_game_server_proxy()
    session = proxy.get_session(room_code)
    if "error" in session:
        return {"error": "sala nao encontrada"}
    if not any(p["player_id"] == player_id for p in session.get("players", [])):
        return {"error": "nao autorizado"}
    join_room(room_code)
```

---

## Warnings

### WR-01: Countdown `setInterval` never self-terminates when `remainingSeconds` reaches zero

**File:** `frontend/src/pages/GameScreen.tsx:42-45`
**Issue:** The interval created in `handlePhaseChanged` decrements `secs` until it hits 0 via `Math.max(0, secs - 1)`, but is never cleared when `secs === 0`. The interval keeps firing every second indefinitely, calling `setRemainingSeconds(0)` on every tick until the next `phase_changed` event arrives (or component unmounts). For long phases (HINT_PHASE: 60s, GUESS_PHASE: 60s) the timer runs up to an additional 60+ seconds of superfluous state updates after expiry.

```tsx
// Current — interval never stops at 0
intervalRef.current = setInterval(() => {
  secs = Math.max(0, secs - 1)
  setRemainingSeconds(secs)
}, 1000)
```

**Fix:**
```tsx
intervalRef.current = setInterval(() => {
  secs = Math.max(0, secs - 1)
  setRemainingSeconds(secs)
  if (secs === 0) {
    clearInterval(intervalRef.current!)
    intervalRef.current = null
  }
}, 1000)
```

---

### WR-02: `PHASE_DURATIONS.get(phase, 30)` default in `_advance_to` vs `default=0` in `remaining_seconds` — inconsistent fallback

**File:** `server/turn_machine.py:107` and `server/turn_machine.py:189`
**Issue:** Two calls to `PHASE_DURATIONS.get()` use different defaults. In `_advance_to` (timer scheduling), an unrecognized phase gets a 30-second timer. In `remaining_seconds` (property), the same phase returns 0 immediately. If any new phase is introduced and `config.py` is not updated, the timer fires after 30 seconds but the client UI reports 0 seconds remaining from the moment the phase starts. The inconsistency will produce a confusing UX and will be hard to diagnose.

**Fix:** Use the same fallback value in both locations, or (better) raise/log a warning on unknown phase rather than silently falling back:
```python
# In _advance_to line 107:
duration = config.PHASE_DURATIONS.get(phase)
if duration is None:
    logger.warning("[TurnMachine] No duration configured for phase '%s', defaulting to 0", phase)
    duration = 0
```
Apply the same pattern in `remaining_seconds`.

---

### WR-03: `advance_phase` fallback selects "first IN_PROGRESS session" non-deterministically in multi-room scenarios

**File:** `server/game_server.py:346-349`
**Issue:** When `advance_phase` is called without a `player_id` (or with a player_id not in `_player_to_room`), it advances the phase of the first `IN_PROGRESS` session returned by `self.sessions.items()`. Dictionary iteration order in CPython 3.7+ is insertion order, but this is still non-deterministic from an API contract perspective. With two concurrent games (possible in this server — there is no single-session constraint), calling `advance_phase()` with no arguments advances the wrong game.

```python
room_code = next(
    (rc for rc, s in self.sessions.items() if s.status == "IN_PROGRESS"),
    None
)
```

**Fix:** Remove the no-argument fallback or require a valid `player_id` / `room_code` always. If the operator hook is needed for testing, require explicit `room_code` as a parameter:
```python
def advance_phase(self, player_id: str = None, room_code: str = None) -> bool:
    ...
    if room_code is None and player_id:
        room_code = self._player_to_room.get(player_id)
    if room_code is None:
        return False   # require explicit targeting; no guessing
```

---

### WR-04: `GameScreen` emits `join_room` without confirming the socket is authenticated

**File:** `frontend/src/pages/GameScreen.tsx:27-29`
**Issue:** On mount, `GameScreen` calls `socket.emit('join_room', { room_code: roomCode })` immediately. If the socket reconnects (e.g. browser tab backgrounded), `_sid_to_player` on the bridge no longer has an entry for the new SID, so the new handler rejects with `"nao autenticado"` once CR-03's fix is applied. More importantly today (before that fix), the socket may not be in the correct Socket.IO room after reconnect, meaning `phase_changed` events are silently dropped. The component has no retry or reconnection handler.

**Fix:** Listen for the `connect` event and re-emit `join_room` on reconnect:
```tsx
useEffect(() => {
  const rejoin = () => socket.emit('join_room', { room_code: roomCode })
  socket.on('connect', rejoin)
  if (socket.connected) rejoin()
  ...
  return () => {
    socket.off('connect', rejoin)
    ...
  }
}, [roomCode])
```

---

### WR-05: `roomCode` from `useParams` is typed `string` but is actually `string | undefined`

**File:** `frontend/src/pages/GameScreen.tsx:16`
**Issue:** React Router v7 (in use per `package.json`) returns `string | undefined` from `useParams`, even when typed as `string`. If `GameScreen` is ever rendered outside the `/game/:roomCode` route (e.g., hot-reload navigation edge case, direct URL without code), `roomCode` is `undefined`. `socket.emit('join_room', { room_code: undefined })` sends a null-coalesced value; the bridge returns `{"error": "room_code required"}`, but `GameScreen` ignores the return value and silently shows "Conectando..." forever.

```tsx
// Current — TypeScript lie; runtime value may be undefined
const { roomCode } = useParams<{ roomCode: string }>()
```

**Fix:**
```tsx
const { roomCode } = useParams<{ roomCode: string }>()
if (!roomCode) {
  // redirect or render error state
  return <p>Código de sala inválido.</p>
}
```

---

## Info

### IN-01: `on_test_event` is dead production code

**File:** `bridge/bridge.py:51-62`
**Issue:** `on_test_event` and the corresponding `broadcast_test` RPC in `game_server.py:115-126` are test/debug artifacts that exist in the production code path. They are never called by game logic but remain `@expose`d and `@oneway`-registered.

**Fix:** Remove both `broadcast_test` from `game_server.py` and `on_test_event` from `bridge.py`, or move them behind an explicit `DEBUG` flag.

---

### IN-02: Commented-out code left in `GameScreen`

**File:** `frontend/src/pages/GameScreen.tsx:25`
**Issue:** `// const playerId = localStorage.getItem('player_id')` is commented-out code in a shipped component.

**Fix:** Remove the line. If `playerId` is needed in a future phase, retrieve it then.

---

### IN-03: `PHASE_DURATIONS.get(phase, 30)` computes `duration` before the `GAME_ENDED` early-exit in `_advance_to`

**File:** `server/turn_machine.py:107`
**Issue:** `duration = config.PHASE_DURATIONS.get(phase, 30)` executes for every phase including `"GAME_ENDED"`, but the result is never used when `phase == "GAME_ENDED"` (the `else` branch that uses `duration` is skipped). This is dead computation that also silences the "no duration configured for GAME_ENDED" feedback that would be useful if the default-fallback warning from WR-02 is added.

**Fix:** Move the `duration` lookup inside the `else` branch (non-GAME_ENDED path):
```python
if phase == "GAME_ENDED":
    game_ended = True
    broadcast_data = { ... }
else:
    duration = config.PHASE_DURATIONS.get(phase, 30)
    ...
    broadcast_data = {
        ...
        "remaining_seconds": duration,
        ...
    }
```

---

_Reviewed: 2026-05-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
