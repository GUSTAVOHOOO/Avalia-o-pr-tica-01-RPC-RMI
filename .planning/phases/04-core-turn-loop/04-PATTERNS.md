# Phase 4: Core Turn Loop - Pattern Map

**Mapped:** 2026-05-14
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `server/turn_state.py` | model/dataclass | CRUD | `server/game_server.py` (PlayerInfo, GameSession dataclasses) | role-match |
| `server/turn_machine.py` | service (state machine) | event-driven | `server/turn_machine.py` itself — extend `_advance_to()` | exact |
| `server/game_server.py` | service (RPC) | request-response | `server/game_server.py` itself — `join_game()`, `start_game()` patterns | exact |
| `server/event_broadcaster.py` | service (fan-out) | event-driven | `server/event_broadcaster.py` itself — `send_to_player()` already exists | exact |
| `bridge/bridge.py` | middleware/bridge | request-response + event-driven | `bridge/bridge.py` itself — `on_phase_changed`, `handle_start_game` patterns | exact |
| `frontend/src/pages/GameScreen.tsx` | component (page) | event-driven | `frontend/src/pages/GameScreen.tsx` itself + `Lobby.tsx` socket patterns | exact |
| `server/images/` (dir + manifest.json) | config/static | file-I/O | `bridge/bridge.py` `serve_spa` → `send_from_directory` | partial |
| `tests/test_turn_state.py` | test | CRUD | `tests/test_turn_machine.py` (FakeBroadcaster, pytest structure) | exact |
| `tests/test_scoring.py` | test | CRUD | `tests/test_turn_machine.py` (pure function test pattern) | exact |

---

## Pattern Assignments

### `server/turn_state.py` (model/dataclass, CRUD)

**Analog:** `server/game_server.py` — `PlayerInfo` and `GameSession` dataclasses (lines 34–73)

**Imports pattern** (game_server.py lines 1–18):
```python
import dataclasses
from typing import List, Optional
```

**Core dataclass pattern** (game_server.py lines 34–73):
```python
@dataclasses.dataclass
class PlayerInfo:
    player_id: str
    player_name: str
    callback_uri: str
    is_host: bool


@dataclasses.dataclass
class GameSession:
    room_code: str
    host_id: str
    max_turns: int
    status: str  # "WAITING" | "IN_PROGRESS" | "ENDED"
    players: List[PlayerInfo] = dataclasses.field(default_factory=list)
    turn_machine: object = dataclasses.field(default=None, repr=False)

    @property
    def player_count(self) -> int:
        return len(self.players)

    def get_player_dicts(self) -> list:
        return [
            {
                "player_id": p.player_id,
                "player_name": p.player_name,
                "is_host": p.is_host,
            }
            for p in self.players
        ]
```

**TurnState shape to implement** (from CONTEXT.md D-03, confirmed by RESEARCH.md Pattern 1):
```python
@dataclasses.dataclass
class TurnState:
    turn_number: int
    player_ids: list
    hints_submitted: dict = dataclasses.field(default_factory=dict)   # player_id → hint word (str)
    guesses_made: dict = dataclasses.field(default_factory=dict)      # guesser_id → target_player_id | None
    correct_guesses: list = dataclasses.field(default_factory=list)   # ordered by arrival
    image_assignments: dict = dataclasses.field(default_factory=dict) # player_id → object_name

    def all_hints_submitted(self) -> bool:
        return len(self.hints_submitted) >= len(self.player_ids)
```

**No Pyro5 import** — TurnState is a pure Python module, no Pyro5 dependency. Copy the import block from `game_server.py` but remove the Pyro5, config, and server imports. Only `dataclasses` and `typing` needed.

---

### `server/turn_machine.py` (service, event-driven) — MODIFY

**Analog:** `server/turn_machine.py` itself

**Imports to add** (at top of turn_machine.py, after existing imports):
```python
from server.turn_state import TurnState
```

**Constructor signature change** (turn_machine.py line 46–57 — add `player_ids` param):
```python
def __init__(self, room_code: str, max_turns: int, broadcaster,
             on_game_ended=None):
    self.room_code = room_code
    self.max_turns = max_turns
    self.broadcaster = broadcaster
    self._on_game_ended = on_game_ended

    self.lock = threading.RLock()
    self.current_phase: str = "WAITING"
    self.current_turn: int = 1
    self._generation: int = 0
    self._timer_handle: Optional[threading.Timer] = None
    self._phase_start_time: float = 0.0
```
Add `player_ids: list` parameter and `self.player_ids = player_ids`, plus `self.current_turn_state: Optional[TurnState] = None`.

**`_advance_to()` extension pattern** (turn_machine.py lines 68–147 — the `with self.lock:` block):

The lock/broadcast-outside-lock ordering is the core invariant. The existing structure:
```python
with self.lock:
    # 1. Stale timer check (from_timer path)
    # 2. Cancel existing timer
    # 3. Increment _generation, capture gen_snapshot
    # 4. Set current_phase, _phase_start_time
    # 5. Build broadcast_data dict
    # 6. Schedule threading.Timer (or set game_ended=True)

# OUTSIDE lock:
self.broadcaster.broadcast("phase_changed", broadcast_data)
```

Phase 4 adds phase-specific hooks INSIDE the lock at step 5, and may queue additional outside-lock calls:
```python
# Inside `with self.lock:` at step 5, BEFORE building broadcast_data:
if phase == "HINT_PHASE":
    self.current_turn_state = TurnState(
        turn_number=self.current_turn,
        player_ids=list(self.player_ids),
    )
    # Capture assignments snapshot for private delivery AFTER lock exit
    image_assignments_snapshot = {}  # populated by image assignment logic

elif phase == "GUESS_PHASE":
    # Fill empty hints for non-submitters (D-07)
    for pid in self.current_turn_state.player_ids:
        if pid not in self.current_turn_state.hints_submitted:
            self.current_turn_state.hints_submitted[pid] = ""
    # Augment broadcast_data AFTER it is built below:
    # broadcast_data["hints"] = dict(self.current_turn_state.hints_submitted)

elif phase == "SCORING_PHASE":
    score_deltas = _calculate_score_deltas(self.current_turn_state)
    # capture for outside-lock SCORE_UPDATED broadcast
```

**Timer callback pattern** (turn_machine.py lines 120–131 — do NOT change):
```python
def _timer_callback():
    next_phase = self._compute_next(_phase_snapshot)
    self._advance_to(
        next_phase,
        from_timer=True,
        expected_generation=gen_snapshot,
    )

self._timer_handle = threading.Timer(duration, _timer_callback)
self._timer_handle.daemon = True
self._timer_handle.start()
```

**`on_game_ended` callback injection pattern** (turn_machine.py lines 141–145) — use same pattern for `on_scoring_phase`:
```python
# Outside lock, after broadcaster.broadcast():
if game_ended:
    self.broadcaster.broadcast("game_ended", broadcast_data)
    if self._on_game_ended is not None:
        self._on_game_ended()
```
Add an analogous `self._on_scoring_phase` callable that receives `score_deltas: dict` — called with no lock held, after the SCORE_UPDATED broadcast.

---

### `server/game_server.py` (service/RPC, request-response) — MODIFY

**Analog:** `server/game_server.py` — `join_game()` (lines 194–253) for the lock/broadcast-outside-lock + error dict pattern; `start_game()` (lines 282–331) for TurnMachine construction update.

**New RPC method shape — `submit_hint()`** — copy from `join_game()` lock pattern (lines 218–253):
```python
# Established lock → snapshot → outside-lock broadcast pattern:
broadcast_data = None

with self.lock:
    # 1. Validate session exists and is in correct state
    session = self.sessions.get(room_code)
    if session is None:
        return {"error": "..."}
    # 2. Mutate state
    # 3. Build broadcast_data snapshot before releasing lock
    broadcast_data = {
        "room_code": room_code,
        ...
    }

# Broadcast OUTSIDE the lock
self.broadcaster.broadcast("event_name", broadcast_data)
return {"ok": True}
```

**Error dict return pattern** (consistent across all existing methods):
```python
return {"error": "sala nao encontrada"}   # on failure
return {"player_id": ..., "room_code": ...}  # on success
```

**`_player_to_room` lookup pattern** (game_server.py lines 303–306) — copy for all new RPC methods:
```python
with self.lock:
    room_code = self._player_to_room.get(player_id)
    session = self.sessions.get(room_code) if room_code else None
    if session is None:
        return {"error": "no_active_session"}
```

**`start_game()` TurnMachine construction** (lines 317–322) — must add `player_ids` when construction signature changes:
```python
target_session.turn_machine = TurnMachine(
    room_code=target_session.room_code,
    max_turns=target_session.max_turns,
    broadcaster=self.broadcaster,
    on_game_ended=lambda: self._set_session_ended(room_code_for_cb),
)
```
Add `player_ids=[p.player_id for p in target_session.players]` to this constructor call.

**`@Pyro5.api.oneway` decoration rule** (game_server.py line 115):
```python
@Pyro5.api.oneway
def broadcast_test(self, message: str) -> None:
```
Submit methods that trigger broadcasts should NOT be `@oneway` — the bridge needs the return value (`{"ok": True}` or `{"error": ...}`) to give the client acknowledgment. Only fire-and-forget push methods use `@oneway`.

**`_set_session_ended` callback pattern** (lines 271–279) — copy for `on_scoring_phase` callback:
```python
def _set_session_ended(self, room_code: str) -> None:
    """Called from TurnMachine on_game_ended callback."""
    with self.lock:
        session = self.sessions.get(room_code)
        if session is not None:
            session.status = "ENDED"
```
Pattern: small private method that acquires the lock independently, called from TurnMachine's timer thread which never holds GameServer.lock.

**`GameSession` dataclass extension** (lines 44–73) — add `accumulated_scores` field:
```python
@dataclasses.dataclass
class GameSession:
    room_code: str
    host_id: str
    max_turns: int
    status: str
    players: List[PlayerInfo] = dataclasses.field(default_factory=list)
    turn_machine: object = dataclasses.field(default=None, repr=False)
    # ADD:
    accumulated_scores: dict = dataclasses.field(default_factory=dict)  # player_id → total int
```

---

### `server/event_broadcaster.py` (service, event-driven) — no new code needed

**Analog:** `server/event_broadcaster.py` itself — `send_to_player()` (lines 82–98)

`send_to_player()` already exists and handles targeted private delivery:
```python
def send_to_player(self, player_id: str, event_type: str, data: dict):
    """Deliver event_type to a single registered player."""
    with self.lock:
        uri = self.callbacks.get(player_id)

    if uri is None:
        return

    try:
        with Pyro5.api.Proxy(uri) as proxy:
            method = getattr(proxy, "on_" + event_type.lower())
            method(data)
    except Exception as e:
        print(f"[EventBroadcaster] send_to_player failed for {player_id}: {e}",
              flush=True)
        with self.lock:
            self.callbacks.pop(player_id, None)
```

The bridge routes targeted events by checking `target_player_id` in the payload — EventBroadcaster itself does not need changes. `send_to_player()` is called from TurnMachine OUTSIDE the lock (same rule as `broadcast()`).

---

### `bridge/bridge.py` (middleware/bridge, event-driven) — MODIFY

**Analog:** `bridge/bridge.py` itself

**BridgeCallbackReceiver new method pattern** — copy from `on_phase_changed` (lines 94–102) for room-broadcast methods; from `on_game_started` (lines 74–82) for private/targeted variants:
```python
@Pyro5.api.oneway
@Pyro5.api.callback
def on_phase_changed(self, data: dict):
    """Receives PHASE_CHANGED push from TurnMachine; routes to room."""
    try:
        socketio.emit("phase_changed", data, to=data["room_code"])
        print(f"[BRIDGE] phase_changed emitted to room {data['room_code']} phase={data.get('phase')}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_phase_changed: {exc}", flush=True)
```

**Targeted (private) delivery pattern** — new pattern for `on_object_assigned`. Route to SID instead of room:
```python
@Pyro5.api.oneway
@Pyro5.api.callback
def on_object_assigned(self, data: dict):
    target_player_id = data.get("target_player_id")
    if target_player_id:
        with _sid_lock:
            sid = _player_to_sid.get(target_player_id)
        if sid:
            socketio.emit("object_assigned", data, to=sid)
            print(f"[BRIDGE] object_assigned → sid={sid}", flush=True)
    # silently drop if SID not found (player disconnected)
```

**`_player_to_sid` reverse map** — add alongside existing `_sid_to_player` (bridge.py line 138):
```python
_sid_to_player: dict = {}   # existing — request.sid → player_id
_player_to_sid: dict = {}   # ADD — player_id → request.sid (for private delivery)
```

**Populate both maps in `handle_create_game`** (lines 229–237) and `handle_join_game` (lines 251–259):
```python
if "error" not in result:
    with _sid_lock:
        _sid_to_player[request.sid] = result["player_id"]
        _player_to_sid[result["player_id"]] = request.sid  # ADD
    join_room(result["room_code"])
```

**Clean both maps in `handle_disconnect`** (lines 317–328):
```python
with _sid_lock:
    player_id = _sid_to_player.pop(request.sid, None)
    if player_id:
        _player_to_sid.pop(player_id, None)  # ADD
```

**New Socket.IO handlers for game actions** — copy from `handle_start_game` (lines 277–298):
```python
@socketio.on("start_game")
def handle_start_game(data):
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "sessao nao encontrada"}
    proxy = get_game_server_proxy()
    success = proxy.start_game(player_id)
    if not success:
        socketio.emit(
            "start_game_error",
            {"error": "Nao autorizado ou jogadores insuficientes"},
            to=request.sid,
        )
    return {"success": success}
```
`handle_submit_hint`, `handle_submit_guess`, `handle_skip_guess` all follow this shape: resolve `player_id` from `_sid_to_player`, call RPC, return result dict.

**Flask static image route** — add BEFORE the `serve_spa` catch-all (bridge.py line 336). Copy `send_from_directory` call from `serve_spa` (lines 344–350):
```python
@app.route("/static/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "..", "server", "images"),
        filename
    )
```
Register this route before `serve_spa` — Flask matches routes in registration order and the `/<path:path>` catch-all must remain last.

---

### `frontend/src/pages/GameScreen.tsx` (component/page, event-driven) — MODIFY

**Analog:** `frontend/src/pages/GameScreen.tsx` itself (socket listener pattern, lines 27–67) + `frontend/src/pages/Lobby.tsx` (state + conditional rendering, lines 22–84)

**Socket listener registration pattern** (GameScreen.tsx lines 27–67):
```typescript
useEffect(() => {
    if (!socket.connected) socket.connect()
    socket.emit('join_room', { room_code: roomCode })

    const handlePhaseChanged = (data: PhaseChangedPayload) => { ... }
    const handleGameEnded = (_data: object) => { ... }

    socket.on('phase_changed', handlePhaseChanged)
    socket.on('game_ended', handleGameEnded)

    return () => {
      // Cleanup — matches the registration above, one-to-one
      socket.off('phase_changed', handlePhaseChanged)
      socket.off('game_ended', handleGameEnded)
    }
}, [roomCode])
```
Add `object_assigned`, `hint_received`, `guess_result`, `score_updated` handlers in the same `useEffect` block. Each handler is a named `const` so the cleanup `socket.off()` can reference the same function identity.

**State declaration pattern** (GameScreen.tsx lines 17–22):
```typescript
const [currentPhase, setCurrentPhase] = useState<string | null>(null)
const [remainingSeconds, setRemainingSeconds] = useState(0)
const [currentTurn, setCurrentTurn] = useState(1)
const [maxTurns, setMaxTurns] = useState(1)
const [gameEnded, setGameEnded] = useState(false)
```
Add Phase 4 state variables using the same `useState<T>` pattern. New state needed:
- `myObjectAssignment` (image_url + object_name)
- `hintsCount` / `totalPlayers` (for "N/M hints received" counter)
- `myHintSubmitted: boolean`
- `hints: Record<string, string>` (revealed at GUESS_PHASE start, from `phase_changed` payload)
- `myGuessSubmitted: boolean`
- `scores` array (from `score_updated`)
- `myPlayerId: string` (from localStorage — see commented-out line 26)

**Conditional rendering pattern** (GameScreen.tsx lines 128–161 — the body area `<div>`):
```tsx
{gameEnded ? (
    <p>Jogo encerrado...</p>
) : currentPhase === null ? (
    <p>Conectando...</p>
) : (
    <p>Aguardando ação do servidor...</p>
)}
```
Replace the last branch with phase-specific panels using the same ternary/`&&` pattern:
```tsx
) : currentPhase === 'HINT_PHASE' ? (
    <HintPanel ... />
) : currentPhase === 'GUESS_PHASE' ? (
    <GuessPanel ... />
) : currentPhase === 'SCORING_PHASE' ? (
    <ScorePanel ... />
) : (
    <p>Aguardando ação do servidor...</p>
)}
```

**`useCallback` pattern for handlers** (Lobby.tsx lines 41–63) — use for new event handlers to avoid stale closure issues when handlers depend on state:
```typescript
const handlePlayerJoined = useCallback((data: { players: Player[] }) => {
    setPlayers(data.players)
}, [])
```

**`phase_changed` payload extension** (D-06) — when phase is `GUESS_PHASE`, the payload includes `hints` dict. Handle this in the existing `handlePhaseChanged`:
```typescript
const handlePhaseChanged = (data: PhaseChangedPayload) => {
    // ... existing code ...
    if (data.phase === 'GUESS_PHASE' && data.hints) {
        setHints(data.hints as Record<string, string>)
    }
}
```
Add `hints?: Record<string, string>` to the `PhaseChangedPayload` interface.

**Socket emit pattern for game actions** (Lobby.tsx lines 98–107 — `socket.emit` with ack callback):
```typescript
socket.emit('start_game', { player_id: playerId }, (resp: { success: boolean; error?: string }) => {
    if (!resp.success) {
        setGameStarting(false)
        addToast(resp.error ?? 'Não foi possível iniciar o jogo.', 'error')
    }
})
```
Use the same `socket.emit(event, data, ackCallback)` form for `submit_hint`, `submit_guess`, `skip_guess`.

---

### `server/images/manifest.json` + image files (config/static, file-I/O) — NEW

**Analog:** `bridge/bridge.py` `serve_spa` + `send_from_directory` pattern (lines 344–350)

No Python code pattern to copy — the manifest is a plain JSON file. Shape:
```json
{
  "apple.jpg": "apple",
  "bicycle.png": "bicycle",
  "chair.jpg": "chair",
  "clock.png": "clock",
  "guitar.jpg": "guitar",
  "hat.png": "hat",
  "laptop.jpg": "laptop",
  "umbrella.png": "umbrella"
}
```
Minimum 8 entries (D-12 / RESEARCH.md). Server loads at `GameServer.__init__()` using `json.load()` stdlib — no custom parser.

**Loading pattern in GameServer.__init__** — follows the existing `self.sessions = {}` initialization style:
```python
import json
import os

# In __init__:
_manifest_path = os.path.join(os.path.dirname(__file__), "images", "manifest.json")
with open(_manifest_path) as f:
    self._image_manifest: dict = json.load(f)  # {filename: object_name}
self._used_images_this_game: dict = {}  # room_code → set of used filenames (Pitfall 3)
```

---

### `tests/test_turn_state.py` (test, CRUD) — NEW

**Analog:** `tests/test_turn_machine.py` — exact structural match

**Module-level FakeBroadcaster pattern** (test_turn_machine.py lines 26–35):
```python
class FakeBroadcaster:
    def __init__(self):
        self.events = []

    def broadcast(self, event_type, data, exclude=None):
        self.events.append({
            "type": event_type,
            "phase": data.get("phase"),
            "data": data,
        })
```
Add `send_to_player` method to FakeBroadcaster for Phase 4:
```python
    def send_to_player(self, player_id, event_type, data):
        self.events.append({
            "type": event_type,
            "player_id": player_id,
            "data": data,
        })
```

**Test function naming pattern** (test_turn_machine.py line 42 onward):
```python
def test_phase_cycle():
    """TURN-01: description of requirement being tested."""
    broadcaster = FakeBroadcaster()
    tm = TurnMachine("ROOM1", max_turns=1, broadcaster=broadcaster)
    ...
    assert ..., "Descriptive failure message"
```
Each test: one requirement ID in docstring, one assertion cluster, descriptive failure message string.

**In-process testing without Pyro5 daemon** (test_turn_machine.py line 53–68) — TurnMachine has no Pyro5 dependency; TurnState also has no Pyro5 dependency. Tests instantiate directly:
```python
from server.turn_state import TurnState
from server.game_server import GameServer

def test_submit_hint():
    server = GameServer()
    # Bypass Pyro5 — call method directly on the object
    server.create_game(...)
    result = server.submit_hint(player_id, "apple")
    assert result == {"ok": True}
```

**Daemon-based test pattern** (test_session.py lines 28–37) — use only if testing Pyro5 serialization boundary:
```python
def _start_daemon(obj, object_id: str):
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    uri = daemon.register(obj, objectId=object_id)
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return daemon, str(uri)
```
For `test_turn_state.py`, prefer direct instantiation (no daemon needed — all logic is in-process).

---

### `tests/test_scoring.py` (test, CRUD) — NEW

**Analog:** `tests/test_turn_machine.py` — pure function test structure (no Pyro5, no daemon)

**Pure function test pattern** (test_turn_machine.py `test_phase_cycle` lines 42–68):
```python
def test_tiered_guessers():
    """SCORE-01: Tiered guesser points — 1st=20, 2nd=15, 3rd=10, 4th=max(5,...)."""
    ts = TurnState(turn_number=1, player_ids=["p1", "p2", "p3", "p4"])
    ts.image_assignments = {"p1": "apple", "p2": "bicycle", "p3": "chair", "p4": "clock"}
    ts.guesses_made = {"p1": "p2", "p2": "p1", "p3": "p1", "p4": "p1"}
    ts.correct_guesses = ["p1", "p2", "p3", "p4"]  # ordered by arrival

    deltas = _calculate_score_deltas(ts)

    assert deltas["p1"] == 20, f"1st correct should get 20pts, got {deltas['p1']}"
    assert deltas["p2"] == 15, f"2nd correct should get 15pts, got {deltas['p2']}"
    assert deltas["p3"] == 10, f"3rd correct should get 10pts, got {deltas['p3']}"
    assert deltas["p4"] == 5,  f"4th correct should get max(5, ...) pts, got {deltas['p4']}"
```
`_calculate_score_deltas` is a pure function imported directly — no server or broadcaster instance needed.

---

## Shared Patterns

### Lock / broadcast-outside-lock invariant
**Source:** `server/game_server.py` lines 218–252 (`join_game`) and lines 299–331 (`start_game`)
**Apply to:** all new `GameServer` RPC methods (`submit_hint`, `submit_guess`, `skip_guess`, `get_scores`)
```python
broadcast_data = None
with self.lock:
    # All state reads and mutations here
    # Build broadcast_data snapshot before releasing lock
    broadcast_data = {"room_code": room_code, ...}

# OUTSIDE lock: network I/O
self.broadcaster.broadcast("event_name", broadcast_data)
return {"ok": True}
```

### `@Pyro5.api.oneway @Pyro5.api.callback` decoration
**Source:** `bridge/bridge.py` lines 51–53, 64–66, 74–76, 84–86, 94–96, 104–106
**Apply to:** all new `BridgeCallbackReceiver.on_*` methods
```python
@Pyro5.api.oneway
@Pyro5.api.callback
def on_hint_received(self, data: dict):
    try:
        socketio.emit("hint_received", data, to=data["room_code"])
        print(f"[BRIDGE] hint_received emitted to room {data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_hint_received: {exc}", flush=True)
```

### Error dict return convention
**Source:** `server/game_server.py` lines 222–224, 228, 230 (`join_game` validation block)
**Apply to:** all new RPC methods
```python
return {"error": "no_active_session"}   # failure path
return {"ok": True}                     # success path (submit actions)
return {"player_id": ..., ...}          # success path (create/join style)
```

### `_sid_to_player` player_id resolution in bridge handlers
**Source:** `bridge/bridge.py` lines 286–290 (`handle_start_game`)
**Apply to:** `handle_submit_hint`, `handle_submit_guess`, `handle_skip_guess`
```python
with _sid_lock:
    player_id = _sid_to_player.get(request.sid)
if not player_id:
    return {"error": "sessao nao encontrada"}
```
Player ID is NEVER trusted from client payload — always resolved from the server-side SID map.

### `get_game_server_proxy()` per-thread usage
**Source:** `bridge/bridge.py` lines 154–164
**Apply to:** all new bridge socket event handlers
```python
def get_game_server_proxy() -> Pyro5.api.Proxy:
    if not hasattr(_thread_local, "proxy"):
        _thread_local.proxy = Pyro5.api.Proxy(
            f"PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}"
        )
    return _thread_local.proxy
```
Always call `proxy = get_game_server_proxy()` inside the handler, never share across handlers.

### React socket event cleanup pattern
**Source:** `frontend/src/pages/GameScreen.tsx` lines 56–66
**Apply to:** all new socket listeners in `GameScreen.tsx`
```typescript
socket.on('phase_changed', handlePhaseChanged)
socket.on('game_ended', handleGameEnded)

return () => {
    socket.off('phase_changed', handlePhaseChanged)
    socket.off('game_ended', handleGameEnded)
}
```
Every `socket.on` must have a matching `socket.off` in the cleanup return. Use named `const` handlers (not inline lambdas) so `.off()` removes the correct listener.

---

## No Analog Found

All files have close matches in the codebase. No files require falling back to RESEARCH.md-only patterns.

---

## Metadata

**Analog search scope:** `server/`, `bridge/`, `tests/`, `frontend/src/`
**Files scanned:** 10 source files read in full
**Pattern extraction date:** 2026-05-14
