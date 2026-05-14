# Phase 3: Phase Machine + Timer - Research

**Researched:** 2026-05-14
**Domain:** Python threading.Timer state machine + Pyro5 broadcast + React game screen
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase machine logic lives in `server/turn_machine.py` as a new `TurnMachine` class.
- **D-02:** `GameSession` holds `session.turn_machine`. `GameServer` delegates; gains no new timer methods.
- **D-03:** `TurnMachine.__init__` receives `EventBroadcaster` as a dependency injection argument. Calls `broadcaster.broadcast()` directly; no back-reference to `GameServer`.
- **D-04:** Per-phase durations configured as `PHASE_DURATIONS` dict in `config.py`. One canonical place to tune.
- **D-05:** ROUND_START and TURN_END are 5-second transitional phases.
- **D-06:** ROUND_START happens once at game start. Turn 2+ goes TURN_END → HINT_PHASE (skips ROUND_START).
- **D-07:** When `current_turn == max_turns` at TURN_END, server broadcasts `GAME_ENDED` and sets `session.status = "ENDED"`.
- **D-08:** `TurnMachine` owns `current_turn` (starts at 1) and `max_turns`. Single source of truth for turn progress.
- **D-09:** Phase 3 adds minimal React game screen at `/game/:roomCode`. Shows phase name + countdown seconds only (no action buttons).
- **D-10:** Bridge gains `on_phase_changed` and `on_game_ended` methods on `BridgeCallbackReceiver`, routing to the Socket.IO room via `data["room_code"]`.

### Claude's Discretion

- Generation counter: `TurnMachine._generation: int`, incremented on every advance. Timer callbacks receive expected generation at creation; check `self._generation == expected_generation` before acting.
- Phase order (TURN-01): WAITING → ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END (→ HINT_PHASE for next turn, or GAME_ENDED if last).
- `advance_phase(player_id=None)` exposed on `GameServer` for smoke-test RPC call (success criterion #3).
- `TurnMachine` lock: `threading.RLock` protecting `current_phase`, `current_turn`, `_generation`, and active `threading.Timer` handle.

### Deferred Ideas (OUT OF SCOPE)

- Timer color states (green/yellow/red) on frontend countdown — Phase 8.
- Per-game configurable phase durations by host — v2.
- Authorization on `advance_phase` — later phase.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TURN-01 | Server controls state machine: WAITING → DISTRIBUTING → ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END | TurnMachine class with ordered phase list; transition method with generation check |
| TURN-02 | Each phase has configurable timer (30–60s) managed by `threading.Timer`; on expiry, phase advances automatically | PHASE_DURATIONS in config.py; threading.Timer with generation counter; timer handle cancelled on manual advance |
| TURN-03 | Phase transition sends broadcast `PHASE_CHANGED` to all clients | `broadcaster.broadcast("phase_changed", {...})` after each advance; BridgeCallbackReceiver.on_phase_changed routes to Socket.IO room |
| TURN-04 | Phase timer uses generation counter to prevent race condition from stale timers firing after manual advance | `_generation` field incremented on every advance; timer callback is a no-op if generation has changed |
</phase_requirements>

---

## Summary

Phase 3 implements a server-side finite state machine (`TurnMachine`) that drives the game through a fixed sequence of phases, each with an auto-expiring `threading.Timer`. The generation counter pattern (TURN-04) prevents double-advances: every manual or timer-driven advance increments `_generation`, and timer callbacks hold the generation value at creation time — they no-op if the value has changed by the time they fire.

The codebase from Phases 1–2 provides all required primitives: `EventBroadcaster.broadcast()` for fan-out, `BridgeCallbackReceiver` extension pattern, the `@Pyro5.api.oneway @Pyro5.api.callback` decorator pair, room-based Socket.IO routing via `room_code` in payload, and `threading.RLock` protecting `GameServer` state. `TurnMachine` slots into this infrastructure as a new module, owned by `GameSession`, with dependency injection of `EventBroadcaster`.

The frontend addition is a minimal `GameScreen` React component at `/game/:roomCode` that listens for `phase_changed` and `game_ended` Socket.IO events and displays a phase badge + local countdown ticker. Navigation from Lobby to GameScreen on `game_started` is already wired in `Lobby.tsx`.

**Primary recommendation:** Implement `TurnMachine` as a pure-Python class with no Pyro5 dependency; it calls `EventBroadcaster` directly. Expose only `advance_phase()` on `GameServer` as the single new RPC method. The generation counter is the critical correctness mechanism — test it explicitly.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Phase state machine logic | API / Backend (`server/turn_machine.py`) | — | Server is authoritative; clients are notified, never drive transitions |
| Timer management | API / Backend (`server/turn_machine.py`) | — | `threading.Timer` lives in the same process as the state; no external scheduler needed |
| Phase transition broadcast | API / Backend (`server/event_broadcaster.py`) | — | `EventBroadcaster.broadcast()` already handles fan-out with failure cleanup |
| Event routing to browser rooms | Bridge (`bridge/bridge.py` BridgeCallbackReceiver) | — | Bridge converts Pyro5 callbacks to Socket.IO room emits — established pattern |
| Phase indicator UI | Frontend Server (React SPA in browser) | — | Client renders phase name + countdown locally; server sends values on each transition |
| Client-side countdown tick | Browser / Client (`GameScreen` setInterval) | — | Local decrement avoids server polling; resets on each `phase_changed` event |
| Config for phase durations | API / Backend (`config.py`) | — | Single source of truth for tuning; `TurnMachine` reads from import |

---

## Standard Stack

### Core (all already installed — no new packages required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `threading.Timer` | stdlib | Auto-fire phase advance after N seconds | Built-in; no additional dependency; integrates cleanly with `threading.RLock` |
| Python `threading.RLock` | stdlib | Protect `TurnMachine` mutable state | Re-entrant lock matches `GameServer.lock` pattern already in codebase |
| Pyro5 | 5.16 | RPC for `advance_phase()` call from test client | Already installed; `@Pyro5.api.expose` on `GameServer` |
| Flask-SocketIO | 5.6.1 | Emit `phase_changed` / `game_ended` events to browser rooms | Already installed; `socketio.emit(..., to=room_code)` established in bridge |
| React + React Router | 19.x / 7.x | New `/game/:roomCode` route + `GameScreen` component | Already installed in frontend |
| socket.io-client | 4.8.3 | Browser side — listen for `phase_changed` / `game_ended` | Already installed |

[VERIFIED: codebase grep — all packages confirmed in venv and package.json]

**No new packages required for Phase 3.**

---

## Architecture Patterns

### System Architecture Diagram

```
[GameServer.start_game()]
        │
        ▼
[GameSession.turn_machine = TurnMachine(room_code, max_turns, broadcaster)]
        │
        ▼
[TurnMachine.start()]  ──────────────────────────────────────────────────┐
        │                                                                   │
        │  acquires RLock                                                   │
        │  sets current_phase = "ROUND_START"                              │
        │  increments _generation                                           │
        │  schedules threading.Timer(duration, _on_timer_fire, gen)        │
        │  releases RLock                                                   │
        │                                                                   │
        │  calls broadcaster.broadcast("phase_changed", payload)           │
        │            │                                                      │
        │            ▼                                                      │
        │  [EventBroadcaster]                                               │
        │       iterates callback URIs (outside lock)                       │
        │       creates fresh Pyro5.Proxy per URI per call                  │
        │       calls proxy.on_phase_changed(data)                          │
        │            │                                                      │
        │            ▼                                                      │
        │  [BridgeCallbackReceiver.on_phase_changed()]  (@oneway @callback) │
        │       socketio.emit("phase_changed", data, to=data["room_code"]) │
        │            │                                                      │
        │            ▼                                                      │
        │  [Browser: GameScreen]                                            │
        │       updates currentPhase + remainingSeconds state               │
        │       resets setInterval countdown tick                            │
        │                                                                   │
        ◄───────────────────── threading.Timer fires ──────────────────────┘
        │  (or GameServer.advance_phase() called via RPC)
        │
        ▼
[TurnMachine._advance()]
        │  acquires RLock
        │  checks _generation == expected_generation  ←─── GATE (TURN-04)
        │    if mismatch: no-op (stale timer) → log + return
        │    if match:
        │      cancels current timer handle
        │      increments _generation
        │      computes next_phase (from PHASE_SEQUENCE list)
        │      handles TURN_END → HINT_PHASE loop vs GAME_ENDED
        │      schedules new threading.Timer for next phase
        │  releases RLock
        │  calls broadcaster.broadcast("phase_changed" or "game_ended", ...)
        │
        ▼
[Cycle continues until last TURN_END → GAME_ENDED]
```

### Recommended Project Structure

```
server/
├── game_server.py        # Existing — add advance_phase() RPC method
├── event_broadcaster.py  # Existing — unchanged
├── turn_machine.py       # NEW — TurnMachine class
└── __init__.py

bridge/
└── bridge.py             # Existing — add on_phase_changed(), on_game_ended()

config.py                 # Existing — add PHASE_DURATIONS dict

frontend/src/
├── pages/
│   └── GameScreen.tsx    # NEW — /game/:roomCode route
├── components/
│   ├── PhaseBadge.tsx    # NEW — colored phase label pill
│   └── CountdownDisplay.tsx  # NEW — large countdown number
├── App.tsx               # Existing — add /game/:roomCode Route
└── socket.ts             # Existing — unchanged

tests/
└── test_turn_machine.py  # NEW — TURN-01 through TURN-04 unit tests
```

### Pattern 1: TurnMachine — core implementation skeleton

**What:** State machine class with generation counter and timer management.
**When to use:** Any server-side auto-advancing phase loop.

```python
# Source: CONTEXT.md D-03, D-04, Claude's Discretion section (generation counter)
import threading
import time
import logging
from typing import Optional
import config

logger = logging.getLogger(__name__)

PHASE_SEQUENCE = [
    "ROUND_START",
    "HINT_PHASE",
    "GUESS_PHASE",
    "EXCHANGE_PHASE",
    "SPY_PHASE",
    "SCORING_PHASE",
    "TURN_END",
]

class TurnMachine:
    def __init__(self, room_code: str, max_turns: int, broadcaster):
        self.room_code = room_code
        self.max_turns = max_turns
        self.broadcaster = broadcaster
        self.lock = threading.RLock()
        self.current_phase: str = "WAITING"
        self.current_turn: int = 1
        self._generation: int = 0
        self._timer_handle: Optional[threading.Timer] = None
        self._phase_start_time: float = 0.0

    def start(self):
        """Called by GameServer.start_game() after GAME_STARTED broadcast."""
        self._advance_to("ROUND_START")

    def _advance_to(self, phase: str, from_timer: bool = False,
                    expected_generation: int = -1):
        """Core transition method. Always called with lock NOT held by caller."""
        broadcast_data = None
        game_ended = False

        with self.lock:
            if from_timer:
                # Generation check — stale timer guard (TURN-04)
                if self._generation != expected_generation:
                    logger.info(
                        "[TurnMachine] Stale timer suppressed "
                        "(room=%s gen_expected=%d gen_current=%d)",
                        self.room_code, expected_generation, self._generation
                    )
                    return

            # Cancel any running timer before proceeding
            if self._timer_handle is not None:
                self._timer_handle.cancel()
                self._timer_handle = None

            self._generation += 1
            self.current_phase = phase
            self._phase_start_time = time.monotonic()
            duration = config.PHASE_DURATIONS.get(phase, 30)
            gen_snapshot = self._generation  # capture for closure

            # Handle GAME_ENDED edge case
            if phase == "GAME_ENDED":
                game_ended = True
                broadcast_data = {
                    "room_code": self.room_code,
                    "current_turn": self.current_turn,
                    "max_turns": self.max_turns,
                }
            else:
                def _timer_callback():
                    next_phase = self._compute_next(phase)
                    self._advance_to(next_phase, from_timer=True,
                                     expected_generation=gen_snapshot)

                self._timer_handle = threading.Timer(duration, _timer_callback)
                self._timer_handle.daemon = True
                self._timer_handle.start()

                broadcast_data = {
                    "room_code": self.room_code,
                    "phase": phase,
                    "remaining_seconds": duration,
                    "current_turn": self.current_turn,
                    "max_turns": self.max_turns,
                }

        # Broadcast OUTSIDE the lock — network I/O must never hold the state lock
        if game_ended:
            self.broadcaster.broadcast("game_ended", broadcast_data)
        else:
            self.broadcaster.broadcast("phase_changed", broadcast_data)

    def _compute_next(self, current_phase: str) -> str:
        """Determine the next phase given current_phase and turn state."""
        with self.lock:
            if current_phase == "TURN_END":
                if self.current_turn >= self.max_turns:
                    return "GAME_ENDED"
                self.current_turn += 1
                return "HINT_PHASE"  # Skip ROUND_START on subsequent turns (D-06)
            idx = PHASE_SEQUENCE.index(current_phase)
            return PHASE_SEQUENCE[idx + 1]

    def advance_phase_manual(self):
        """Test/operator RPC hook — skip current phase immediately."""
        with self.lock:
            next_phase = self._compute_next(self.current_phase)
        self._advance_to(next_phase)

    @property
    def remaining_seconds(self) -> int:
        """Approximate seconds left in current phase (for get_game_state)."""
        with self.lock:
            duration = config.PHASE_DURATIONS.get(self.current_phase, 0)
            elapsed = time.monotonic() - self._phase_start_time
            return max(0, int(duration - elapsed))
```

[ASSUMED] — the exact method signatures and class layout above are derived from CONTEXT.md decisions and established codebase patterns; not verified against a pre-existing test suite for this class.

### Pattern 2: BridgeCallbackReceiver extension (on_phase_changed, on_game_ended)

**What:** Two new methods on the existing `BridgeCallbackReceiver`, following the exact pattern from Phases 1–2.
**When to use:** Every new server-to-browser event type follows this pattern.

```python
# Source: bridge/bridge.py existing pattern (VERIFIED: codebase read)
@Pyro5.api.oneway
@Pyro5.api.callback
def on_phase_changed(self, data: dict):
    """Routes PHASE_CHANGED to the correct Socket.IO room."""
    try:
        socketio.emit("phase_changed", data, to=data["room_code"])
        print(f"[BRIDGE] phase_changed emitted to room {data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_phase_changed: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_game_ended(self, data: dict):
    """Routes GAME_ENDED to the correct Socket.IO room."""
    try:
        socketio.emit("game_ended", data, to=data["room_code"])
        print(f"[BRIDGE] game_ended emitted to room {data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_game_ended: {exc}", flush=True)
```

[VERIFIED: codebase read — matches existing on_player_joined / on_game_started / on_host_changed pattern exactly]

### Pattern 3: PHASE_DURATIONS in config.py

```python
# Source: CONTEXT.md D-04 (exact values locked by user)
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

[VERIFIED: codebase read — config.py structure exists; `PHASE_DURATIONS` key is not yet present, needs adding]

### Pattern 4: GameScreen React component (skeleton)

```typescript
// Source: 03-UI-SPEC.md §Screen Layout Contract + Interaction Contracts
// (VERIFIED: codebase read)
import { useEffect, useState, useRef } from 'react'
import { useParams } from 'react-router'
import socket from '../socket'
import PhaseBadge from '../components/PhaseBadge'
import CountdownDisplay from '../components/CountdownDisplay'

interface PhaseChangedPayload {
  phase: string
  remaining_seconds: number
  current_turn: number
  max_turns: number
}

export default function GameScreen() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const [currentPhase, setCurrentPhase] = useState<string | null>(null)
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [currentTurn, setCurrentTurn] = useState(1)
  const [maxTurns, setMaxTurns] = useState(1)
  const [gameEnded, setGameEnded] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!socket.connected) socket.connect()
    socket.emit('join_room', { room_code: roomCode })

    const handlePhaseChanged = (data: PhaseChangedPayload) => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      setCurrentPhase(data.phase)
      setRemainingSeconds(data.remaining_seconds)
      setCurrentTurn(data.current_turn)
      setMaxTurns(data.max_turns)
      let secs = data.remaining_seconds
      intervalRef.current = setInterval(() => {
        secs = Math.max(0, secs - 1)
        setRemainingSeconds(secs)
      }, 1000)
    }

    const handleGameEnded = () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      setGameEnded(true)
    }

    socket.on('phase_changed', handlePhaseChanged)
    socket.on('game_ended', handleGameEnded)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      socket.off('phase_changed', handlePhaseChanged)
      socket.off('game_ended', handleGameEnded)
    }
  }, [roomCode])

  // ... render PhaseHeader with PhaseBadge + CountdownDisplay
}
```

[VERIFIED: UI-SPEC.md §Interaction Contracts — event names, payload shape, setInterval pattern confirmed]

### Pattern 5: App.tsx route addition

```typescript
// Source: frontend/src/App.tsx (VERIFIED: codebase read)
// Add alongside existing routes:
import GameScreen from './pages/GameScreen'
// ...
<Route path="/game/:roomCode" element={<GameScreen />} />
```

[VERIFIED: codebase read — App.tsx uses React Router v7 `<Routes>/<Route>` pattern; `/game/:roomCode` is not yet present]

### Anti-Patterns to Avoid

- **Broadcasting while holding the RLock:** `EventBroadcaster.broadcast()` does network I/O; calling it inside the `with self.lock` block will deadlock if a callback response triggers a re-entrant RPC. All broadcast calls in `TurnMachine` must happen after the `with self.lock:` block exits. [VERIFIED: existing game_server.py join_game/start_game pattern]
- **Sharing the threading.Timer callback closure over a mutable variable:** Capture `gen_snapshot = self._generation` as a local variable before creating the timer; do not reference `self._generation` directly in the lambda/closure.
- **Cancelling a timer from inside the RLock and then calling cancel() again:** Timer.cancel() is safe to call on an already-fired timer (no-op), but the handle should be set to `None` after cancel to avoid confusing double-cancel logic.
- **Calling `_compute_next()` while holding the outer RLock:** `_compute_next` acquires `self.lock` itself. Since the lock is an `RLock`, re-entry from the same thread is safe — but do not call `_compute_next` from a different (non-owner) thread while expecting it to observe latest state.
- **React router param mismatch:** Lobby navigates to `/game/${sessionId}` where `sessionId` is the `room_code`. GameScreen must use `useParams<{ roomCode: string }>()` and the route must be `path="/game/:roomCode"` — both sides must match.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timer that fires once after N seconds | Custom polling loop with sleep | `threading.Timer(duration, callback)` | stdlib; cancellable; daemon-thread-safe; zero overhead |
| Race-condition guard for double-advance | Complex mutex + flag logic | Generation counter (integer increment + check) | Simple, stateless, reliable; no deadlock risk; loggable |
| Thread-safe state field | Manual double-check locking | `threading.RLock` + read/write inside `with self.lock` | RLock is re-entrant; avoids self-deadlock on nested calls |
| Fan-out to multiple Pyro5 clients | Custom loop in TurnMachine | `EventBroadcaster.broadcast()` (already written) | Handles failure cleanup, snapshot-under-lock, per-call proxy |

**Key insight:** `threading.Timer` is the simplest correct solution for a "fire once after N seconds" requirement. The only subtlety is cancellation — hold the handle, call `.cancel()` before scheduling the next timer.

---

## Common Pitfalls

### Pitfall 1: Broadcast inside the RLock causes deadlock
**What goes wrong:** `TurnMachine._advance_to()` holds `self.lock` and calls `broadcaster.broadcast()`. The broadcast creates a Pyro5 proxy and calls `proxy.on_phase_changed(data)`. If the BridgeCallbackReceiver's response somehow re-enters the server (e.g., via another RPC call on the same thread), the RLock is re-entered — or if a different thread tries to acquire it, they block for the duration of network I/O.
**Why it happens:** Confusing "lock protects state mutation" with "lock wraps the entire advance logic including I/O."
**How to avoid:** Collect all mutable state changes inside `with self.lock`, snapshot broadcast data into a local variable, exit the lock block, then call `broadcaster.broadcast()`. [VERIFIED: game_server.py join_game/start_game implement this exact pattern]
**Warning signs:** Server appears to freeze during phase transitions; logs stop mid-broadcast.

### Pitfall 2: Stale timer fires after manual advance
**What goes wrong:** Player manually skips a phase via `advance_phase()`. Two milliseconds later, the original `threading.Timer` fires and calls `_advance_to()` again, double-advancing the game.
**Why it happens:** `threading.Timer.cancel()` only prevents a not-yet-fired timer. If the timer fires between `cancel()` and the lock acquisition in the callback, the callback runs.
**How to avoid:** Generation counter. Timer callback checks `self._generation == expected_generation`. If mismatch: stale, log, return. This is TURN-04 and is the primary correctness requirement for Phase 3.
**Warning signs:** Phase sequence skips two steps in test logs; `_generation` increments twice within a few milliseconds.

### Pitfall 3: `_compute_next` modifies turn state in wrong thread
**What goes wrong:** `_compute_next("TURN_END")` increments `self.current_turn`. If this is called in the timer callback thread without the lock, and another thread simultaneously reads `current_turn`, a race condition occurs.
**Why it happens:** `current_turn` mutation buried inside a helper that's called from a background timer thread.
**How to avoid:** Always call `_compute_next` from inside `_advance_to` which holds `self.lock`. Keep `_compute_next` lock-aware or require it to be called under the lock.
**Warning signs:** `current_turn` skips a value or shows an incorrect final count.

### Pitfall 4: GameScreen receives `game_started` but no `phase_changed` before mounting
**What goes wrong:** Lobby navigates to `/game/:roomCode` when `game_started` fires. GameScreen mounts and immediately listens for `phase_changed`. But `TurnMachine.start()` fires synchronously in `GameServer.start_game()` — the `phase_changed` broadcast may arrive before the GameScreen socket listener is registered.
**Why it happens:** Race between server broadcast timing and React component mount + socket.on registration.
**How to avoid:** The bridge already handles this correctly: `game_started` triggers navigation; the bridge only emits `phase_changed` after `TurnMachine.start()` is called from `start_game()`. The key is that `start()` should be called AFTER the `game_started` broadcast in `start_game()`. If ROUND_START fires too fast (5s is short), add a brief `time.sleep(0.2)` between `game_started` broadcast and `turn_machine.start()`, or make `ROUND_START` duration long enough (currently 5s — adequate for navigation).
**Warning signs:** GameScreen mounts showing "Conectando..." indefinitely; no `phase_changed` received.

### Pitfall 5: `advance_phase` RPC method is `@oneway` but needs return value for test
**What goes wrong:** If `advance_phase` is decorated `@oneway`, the test client cannot confirm it executed before checking state.
**Why it happens:** Confusion about when to use `@oneway`. `@oneway` is appropriate for broadcast methods (fire-and-forget, non-blocking). `advance_phase` is a test/operator call where the caller wants confirmation.
**How to avoid:** Do NOT make `advance_phase` `@oneway`. It should be a regular exposed method returning `True`/`False`. The broadcast it triggers (via `broadcaster.broadcast()`) is still `@oneway` at the callback level.
**Warning signs:** Test calls `advance_phase()` and immediately asserts phase, but phase hasn't changed yet because the call hasn't executed.

### Pitfall 6: React Router route param name mismatch
**What goes wrong:** Lobby uses `navigate(\`/game/${sessionId}\`)` (where `sessionId` is the room code). If GameScreen uses `useParams<{ sessionId: string }>()` instead of `{ roomCode: string }`, the param is `undefined`.
**Why it happens:** Route declared as `/game/:roomCode` but param destructured as `sessionId`.
**How to avoid:** Route param name in `App.tsx` route declaration (`/game/:roomCode`) must match `useParams` key in `GameScreen.tsx` (`roomCode`). [VERIFIED: Lobby.tsx uses `sessionId` from its own route `/lobby/:sessionId` — GameScreen uses a new param name]

---

## Code Examples

### Generation counter test (how to verify TURN-04)

```python
# Source: CONTEXT.md success criterion #3 — design of the test
import threading
import time

def test_generation_counter_prevents_double_advance():
    """Timer callback after manual advance must be a no-op."""
    from server.turn_machine import TurnMachine

    class FakeBroadcaster:
        def __init__(self):
            self.events = []
        def broadcast(self, event_type, data, exclude=None):
            self.events.append((event_type, data.get("phase") or event_type))

    broadcaster = FakeBroadcaster()
    # Use very short timers for testing
    import config
    original = config.PHASE_DURATIONS.copy()
    config.PHASE_DURATIONS.update({k: 0.1 for k in config.PHASE_DURATIONS})

    tm = TurnMachine("TESTROOM", max_turns=1, broadcaster=broadcaster)
    tm.start()  # ROUND_START, timer fires in 0.1s

    time.sleep(0.05)  # Timer not yet fired
    tm.advance_phase_manual()  # Manual advance: gen now 3, timer gen is 1 (stale)
    time.sleep(0.2)  # Old timer fires — must be no-op

    phases = [e[1] for e in broadcaster.events]
    # Should see ROUND_START, then the manual advance, not a double-advance
    # Double-advance would show the same next-phase twice
    assert phases.count("HINT_PHASE") == 1, f"Double-advance detected: {phases}"

    config.PHASE_DURATIONS.update(original)
```

[ASSUMED] — exact test structure; depends on TurnMachine implementation details decided at plan time.

### TurnMachine unit test structure (TURN-01 acceptance)

```python
# Pattern mirrors existing test_session.py (VERIFIED: codebase read)
def test_phase_sequence():
    """TURN-01: TurnMachine advances through full sequence."""
    # Use FakeBroadcaster, short durations, verify phase order
    # ...

def test_timer_auto_advance():
    """TURN-02: Timer expiry advances phase without manual call."""
    # ...

def test_phase_changed_broadcast():
    """TURN-03: Each advance emits 'phase_changed' with correct payload."""
    # broadcaster.events checked after each advance

def test_generation_counter():
    """TURN-04: Stale timer is suppressed by generation mismatch."""
    # See example above
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Game server drives full turn loop inline | Dedicated `TurnMachine` class (D-01) | Phase 3 design | Separation of concerns; `GameServer` stays thin |
| Flask-SocketIO `eventlet` async_mode | `threading` async_mode | Flask-SocketIO deprecation (confirmed 2025) | No additional complexity for Phase 3; `threading.Timer` + `threading.RLock` are natural fit |

**Deprecated/outdated:**
- `eventlet` as Flask-SocketIO async_mode: deprecated per official docs; `threading` is the correct mode for this project. [VERIFIED: CLAUDE.md, confirmed in Phases 1–2]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `TurnMachine._advance_to()` method signature and closure capture approach | Pattern 1 code example | Implementation may need minor adjustment at plan time; correctness pattern (generation counter, broadcast-outside-lock) is sound |
| A2 | `_compute_next` modifying `current_turn` inside the RLock is safe because `_advance_to` always calls it while holding the lock | Pitfall 3 | If called from outside the lock by mistake, race condition; plan must enforce call discipline |
| A3 | `time.sleep(0.2)` mitigation for GameScreen mount race condition (Pitfall 4) | Pitfall 4 | May not be needed if 5s ROUND_START is sufficient buffer; remove if smoke test shows no race |
| A4 | Test for generation counter uses monkeypatched `PHASE_DURATIONS` with 0.1s | Code Examples | Timing-sensitive test on slow CI may be flaky; use `threading.Event` + callback hooks if flakiness observed |

**If this table is empty:** All claims were verified or cited. (Table is not empty — A1–A4 are design choices not yet proven by running tests.)

---

## Open Questions

1. **Should `advance_phase_manual` be exposed directly on `TurnMachine` or only via `GameServer.advance_phase()`?**
   - What we know: CONTEXT.md says `advance_phase(player_id=None)` is exposed on `GameServer` (operator RPC call). `TurnMachine` has an internal method.
   - What's unclear: Whether the test client calls `GameServer.advance_phase()` which delegates to `session.turn_machine.advance_phase_manual()`, or whether `TurnMachine` itself should be Pyro5-exposed (it should not — it has no `@Pyro5.api.expose`).
   - Recommendation: `GameServer.advance_phase(player_id)` is the single RPC entry point; it looks up the session's `turn_machine` and calls `advance_phase_manual()`. This keeps `TurnMachine` as a plain Python class with no Pyro5 coupling.

2. **Should `TurnMachine.start()` be called before or after `GAME_STARTED` broadcast in `start_game()`?**
   - What we know: CONTEXT.md §Integration Points says "calls `turn_machine.start()` to kick off ROUND_START after broadcasting GAME_STARTED."
   - What's unclear: Exact ordering with respect to the lock release in `start_game()`.
   - Recommendation: `start_game()` should follow: (1) acquire lock, set status, snapshot broadcast_data, (2) release lock, (3) `broadcaster.broadcast("game_started", ...)`, (4) `session.turn_machine.start()`. This ensures browsers navigate before the first `phase_changed` fires.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | TurnMachine (threading.Timer, RLock) | ✓ | 3.11.2 | — |
| Pyro5 | RPC, broadcast | ✓ | 5.16 | — |
| Flask-SocketIO | Bridge emit | ✓ | 5.6.1 (confirmed) | — |
| React / React Router | GameScreen | ✓ | 19.x / 7.x | — |
| socket.io-client | Browser events | ✓ | 4.8.3 | — |
| Node / Vite | Frontend build | ✓ | (confirmed in package.json) | — |

[VERIFIED: codebase read — venv present; package.json present with all dependencies]

No missing dependencies. Phase 3 requires zero new package installs.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pytest.ini` (testpaths = tests) |
| Quick run command | `source venv/bin/activate && python -m pytest tests/test_turn_machine.py -x -q` |
| Full suite command | `source venv/bin/activate && python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TURN-01 | Server state machine advances through full phase sequence | unit | `pytest tests/test_turn_machine.py::test_phase_sequence -x` | ❌ Wave 0 |
| TURN-02 | Timer expiry advances phase automatically | unit | `pytest tests/test_turn_machine.py::test_timer_auto_advance -x` | ❌ Wave 0 |
| TURN-03 | Each phase transition broadcasts `PHASE_CHANGED` with correct payload | unit | `pytest tests/test_turn_machine.py::test_phase_changed_broadcast -x` | ❌ Wave 0 |
| TURN-04 | Generation counter prevents stale timer from double-advancing | unit | `pytest tests/test_turn_machine.py::test_generation_counter -x` | ❌ Wave 0 |

**Frontend smoke test (manual — success criteria #4):** 4-terminal session (NS + GameServer + Bridge + two browser tabs) verifying `phase_changed` events arrive and countdown resets. No automated framework; manual verification checkpoint at end of implementation.

### Sampling Rate

- **Per task commit:** `source venv/bin/activate && python -m pytest tests/test_turn_machine.py -x -q`
- **Per wave merge:** `source venv/bin/activate && python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_turn_machine.py` — covers TURN-01, TURN-02, TURN-03, TURN-04 (new file)

*(Existing test infrastructure: `pytest.ini`, `tests/` directory, `_start_daemon` helper pattern — all reusable. No new conftest or framework config needed.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 3 adds no auth changes |
| V3 Session Management | no | Session model unchanged from Phase 2 |
| V4 Access Control | partial | `advance_phase()` is intentionally unguarded in Phase 3 (test utility); CONTEXT.md explicitly defers authorization to a later phase |
| V5 Input Validation | yes | `advance_phase(player_id)` should validate `player_id` is a non-empty string (consistent with existing GameServer methods) |
| V6 Cryptography | no | No cryptographic operations |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stale timer double-advance | Elevation of Privilege (game state corruption) | Generation counter (TURN-04) — primary mitigation |
| Unauthorized `advance_phase` call | Elevation of Privilege | Deferred to later phase per CONTEXT.md; Phase 3 scope is test utility only |
| Timer thread holding lock during broadcast | Denial of Service (deadlock) | Broadcast-outside-lock pattern (established in Phases 1–2) |

---

## Sources

### Primary (HIGH confidence)

- Codebase: `server/game_server.py` — verified RLock pattern, broadcast-outside-lock pattern, existing method signatures
- Codebase: `server/event_broadcaster.py` — verified `broadcast()` behavior, snapshot-under-lock, failure cleanup
- Codebase: `bridge/bridge.py` — verified `@Pyro5.api.oneway @Pyro5.api.callback` decorator pattern, room routing via `data["room_code"]`
- Codebase: `config.py` — verified existing config structure; `PHASE_DURATIONS` key to be added
- Codebase: `frontend/src/pages/Lobby.tsx` — verified `navigate(\`/game/${sessionId}\`)` on `game_started`, confirms navigation is already wired
- Codebase: `frontend/src/App.tsx` — verified React Router v7 route structure; `/game/:roomCode` not yet present
- Codebase: `frontend/package.json` — verified installed packages (socket.io-client, react-router, lucide-react)
- `.planning/phases/03-phase-machine-timer/03-CONTEXT.md` — locked implementation decisions D-01 through D-10
- `.planning/phases/03-phase-machine-timer/03-UI-SPEC.md` — phase badge colors, layout contract, Socket.IO event payload shapes

### Secondary (MEDIUM confidence)

- Python stdlib docs [ASSUMED from training]: `threading.Timer`, `threading.RLock` — behavior described matches stdlib behavior as expected; no version-specific APIs used

### Tertiary (LOW confidence)

- A1–A4 in Assumptions Log — implementation details not yet validated by running tests

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in codebase
- Architecture: HIGH — all patterns verified against existing Phases 1–2 code
- Generation counter pattern: HIGH — locked decision in CONTEXT.md; widely documented stdlib pattern
- Frontend component structure: HIGH — verified against existing React component patterns in codebase
- Test timing sensitivity (Pitfall 4, A4): MEDIUM — empirical; may need adjustment

**Research date:** 2026-05-14
**Valid until:** 2026-06-14 (stable stdlib + framework stack; no moving parts)
