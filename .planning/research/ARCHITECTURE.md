# Architecture Patterns

**Domain:** Pyro5 RPC multiplayer game with WebSocket/web frontend bridge
**Researched:** 2026-05-12
**Confidence:** HIGH (primary sources: official Pyro5 docs, Flask-SocketIO docs)

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  PROCESS 1: Pyro5 Name Server                                   │
│  pyro5 nameserver  (default port 9090)                          │
│  Registers: "game.server", "game.bridge_callback"              │
└───────────────────┬─────────────────────────────────────────────┘
                    │ lookup / register (Pyro5 protocol)
                    │
┌───────────────────▼─────────────────────────────────────────────┐
│  PROCESS 2: GameServer Daemon  (port 9091)                      │
│                                                                 │
│  ┌─────────────────────────────────┐                            │
│  │  GameServer  (@expose)          │                            │
│  │  - join_game(player_id, name)   │                            │
│  │  - leave_game(player_id)        │                            │
│  │  - submit_hint(player_id, word) │                            │
│  │  - submit_guess(player_id, obj) │                            │
│  │  - request_exchange(from, to)   │                            │
│  │  - accept_exchange(from, to)    │                            │
│  │  - attempt_spy(spy, target)     │                            │
│  │  - send_chat(player_id, text)   │                            │
│  │                                 │                            │
│  │  Internal:                      │                            │
│  │  - _state: GameState (RLock)    │                            │
│  │  - _callbacks: dict[str, Proxy] │  ← Proxy to BridgeCB      │
│  │  - _phase_timer: threading.Timer│                            │
│  └─────────────────────────────────┘                            │
│                                                                 │
│  Pyro5 Daemon: threaded server, instance_mode=single           │
│  RLock guards all _state and _callbacks mutations               │
└───────────┬────────────────────────────────────────────────────-┘
            │ Pyro5 RPC (outbound callbacks, @oneway)
            │
┌───────────▼─────────────────────────────────────────────────────┐
│  PROCESS 3: Bridge  (port 5000)                                 │
│                                                                 │
│  ┌──────────────────────────────┐  ┌────────────────────────┐  │
│  │  Flask-SocketIO              │  │  BridgeCallbackReceiver │  │
│  │  (threading async_mode)      │  │  (@expose, @callback)   │  │
│  │                              │  │                         │  │
│  │  on('join')   → RPC call     │  │  on_player_joined()     │  │
│  │  on('hint')   → RPC call     │  │  on_phase_changed()     │  │
│  │  on('guess')  → RPC call     │  │  on_hint_broadcast()    │  │
│  │  on('exchange')→ RPC call    │  │  on_guess_result()      │  │
│  │  on('spy')    → RPC call     │  │  on_exchange_notify()   │  │
│  │  on('chat')   → RPC call     │  │  on_spy_result()        │  │
│  │                              │  │  on_scores_updated()    │  │
│  │  Session map:                │  │  on_chat_message()      │  │
│  │  player_id → sid             │  │  on_private_hint()      │  │
│  │  sid → player_id             │  │                         │  │
│  └──────────────────────────────┘  └──────────┬──────────────┘  │
│                                               │ calls socketio  │
│  Pyro5 Daemon (background thread):            │ .emit() thread- │
│  hosts BridgeCallbackReceiver                 │ safely          │
│  requestLoop() in daemon=True thread          │                 │
└───────────────────────────────────────────────┴─────────────────┘
            ↕ WebSocket (Socket.IO protocol, port 5000)
┌─────────────────────────────────────────────────────────────────┐
│  BROWSER  (React SPA or plain HTML/JS)                          │
│  socket.io client connects to port 5000                         │
│  emits: join, hint, guess, exchange, spy, chat                  │
│  listens: player_joined, phase_changed, hint_broadcast, …       │
└─────────────────────────────────────────────────────────────────┘
```

**Process count:** 3 (Name Server + GameServer + Bridge). Single machine for the academic demo.

**Port map:**
- 9090 — Pyro5 Name Server
- 9091 — GameServer Pyro5 Daemon
- 5000 — Bridge HTTP + WebSocket (Flask-SocketIO)

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Pyro5 Name Server | Service discovery, maps names to URIs | GameServer (registers), Bridge (looks up) |
| GameServer | All game logic, authoritative state, timers, scoring, spy probability | Bridge via Pyro5 callbacks; BridgeCallbackReceiver |
| BridgeCallbackReceiver | Receives Pyro5 callbacks from GameServer; translates to WebSocket emits | Flask-SocketIO (thread-safe emit); GameServer (registers its URI) |
| Flask-SocketIO layer | WebSocket session management, event routing, session↔player_id map | BridgeCallbackReceiver (shared reference); GameServer Proxy (per-thread) |
| Browser SPA | Render game state, capture user actions, show phase UI | Bridge only, via Socket.IO |

---

## Key Design Decisions

### Decision 1: Single Bridge Process

Run Flask-SocketIO and BridgeCallbackReceiver in the same OS process. The SocketIO event handlers share the Python process with the BridgeCallbackReceiver, so `socketio.emit()` is callable directly from within callback methods without IPC.

Alternative (two processes) would require another inter-process channel to forward Pyro5 callbacks to the Socket.IO server — this defeats simplicity and adds a new integration surface without benefit at this scale.

### Decision 2: Bridge Async Mode = threading (not eventlet)

Flask-SocketIO's maintainer is retiring eventlet support (see GitHub discussion #2037, 2026). Use `async_mode='threading'` explicitly:

```python
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')
```

This is fully compatible with standard Python `threading.Thread` (used for the Pyro5 daemon requestLoop inside the bridge process) and with Pyro5 proxies, which are plain blocking sockets.

### Decision 3: One Pyro5 Proxy Per SocketIO Event Handler Call (not shared)

Pyro5 proxies are NOT thread-safe. The official documentation states: "You cannot share Proxy objects among threads. One single thread 'owns' a proxy."

In Flask-SocketIO with threading mode, each event handler runs in a different thread from the thread pool. Therefore:

```python
# WRONG — shared proxy across threads:
game_proxy = Pyro5.api.Proxy("PYRONAME:game.server")  # module-level

# CORRECT — create per handler call (or per thread):
@socketio.on('hint')
def on_hint(data):
    with Pyro5.api.Proxy("PYRONAME:game.server") as proxy:
        proxy.submit_hint(player_id, data['word'])
```

Proxy creation + reconnect is cheap for low-concurrency academic load (2–4 players). If latency becomes a concern, use `threading.local()` to keep one proxy per thread and call `_pyroClaimOwnership()` on reuse.

### Decision 4: GameServer Uses instance_mode=single + RLock

GameServer holds all authoritative game state. It must be a singleton instance (one game per server process in the MVP). With Pyro5's default threaded server, multiple proxies call it concurrently from different threads:

```python
@Pyro5.api.behavior(instance_mode="single")
@Pyro5.api.expose
class GameServer:
    def __init__(self):
        self._lock = threading.RLock()
        self._state = GameState()
        self._callbacks: dict[str, Pyro5.api.Proxy] = {}
    
    def join_game(self, player_id: str, name: str):
        with self._lock:
            # mutate _state safely
```

`RLock` (reentrant lock) is preferred over `Lock` because GameServer methods may call internal helpers that also acquire the lock.

### Decision 5: Callbacks Are @oneway From GameServer to Bridge

When GameServer fires an event (e.g., phase change timer fires), it iterates `_callbacks` and calls each BridgeCallbackReceiver. To avoid blocking the timer thread while waiting for the Bridge's WebSocket emission to complete, mark all callback methods `@oneway` on the GameServer side.

Additionally, this prevents the circular deadlock risk Pyro5 docs warn about: GameServer → Bridge → (possibly back to GameServer for state reads) would deadlock with synchronous calls.

```python
# On GameServer side — fire and forget:
for cb_proxy in self._callbacks.values():
    cb_proxy.on_phase_changed(new_phase, time_remaining)  # @oneway on receiver
```

```python
# On BridgeCallbackReceiver side:
@Pyro5.api.expose
@Pyro5.api.callback
@Pyro5.api.oneway
def on_phase_changed(self, new_phase: str, time_remaining: int):
    socketio.emit('phase_changed', {'phase': new_phase, 'time': time_remaining})
```

---

## Data Flow: Key Scenarios

### Scenario A: Player Joins Game

```
Browser                Bridge (Flask-SocketIO)         GameServer
  |                           |                            |
  |--emit('join', {name})---->|                            |
  |                    [handler thread]                    |
  |                    player_id = uuid4()                 |
  |                    sid_map[request.sid] = player_id    |
  |                    player_map[player_id] = request.sid |
  |                           |---join_game(id,name)------>|
  |                           |           [RLock acquired] |
  |                           |           _state.add_player|
  |                           |           [RLock released] |
  |                           |<--return OK----------------|
  |                           |                            |
  |          [BridgeCallbackReceiver receives from GameServer via @oneway CB]
  |                           |<--on_player_joined(id,name,all_players)--[CB]
  |                    socketio.emit('player_joined', ..., to=room_id)
  |<--event:player_joined-----|  [broadcast to all in room]
```

### Scenario B: Turn Phase Change (Server-Initiated)

```
GameServer (timer thread)     BridgeCallbackReceiver    Browser(s)
  |                                  |                     |
  [threading.Timer fires]            |                     |
  with self._lock:                   |                     |
    _advance_phase(HINT→GUESS)       |                     |
  for cb in _callbacks.values():     |                     |
    cb.on_phase_changed('GUESS',30)--|                     |
    [oneway: returns immediately]    |                     |
                                [CB thread in Bridge]      |
                                socketio.emit('phase_changed',
                                  {'phase':'GUESS','time':30})
                                                     |<----|
                                                  [all browsers update UI]
```

### Scenario C: Private Exchange (Hint Swap Between Two Players)

```
Browser-A          Bridge                GameServer          Bridge           Browser-B
  |                  |                       |                 |                 |
  |--emit('request_exchange', {to:B})        |                 |                 |
  |                  |--request_exchange(A,B)→|                 |                 |
  |                  |                  with lock:              |                 |
  |                  |                  record pending exchange |                 |
  |                  |                  cb[B].on_exchange_request(A)→|            |
  |                  |                                          | socketio.emit(  |
  |                  |                                          | 'exchange_req') |
  |                  |                                          |-------→→→→→→→→-|
  |                  |                                          |   [B sees modal]|
  |                  |                                          |                 |
  |                  |                    |←--accept_exchange(B,A)---------------|
  |                  |                  with lock:              |                 |
  |                  |                  swap hints in _state    |                 |
  |                  |                  cb[A].on_private_hint(hint_B)→|           |
  |                  |                  cb[B].on_private_hint(hint_A)→|           |
  |←--'private_hint'-(hint_B)-----------|                       |                |
  |                  |                                           |←-'private_hint'(hint_A)
  |                  |                  broadcast on_exchange_done(A,B) to all   |
  |  [all players see "A↔B exchanged" without hint content]                      |
```

### Scenario D: Spy Attempt

```
Browser-Spy       Bridge               GameServer           Bridge          Browser-Target
  |                 |                      |                  |                   |
  |--emit('spy',{target:T})               |                  |                   |
  |                 |--attempt_spy(S,T)--->|                  |                   |
  |                 |               with lock:                |                   |
  |                 |               roll = random() < 0.30    |                   |
  |                 |               if discovered:            |                   |
  |                 |                 _state.deduct(S, -10)   |                   |
  |                 |                 cb[S].on_spy_result(discovered=True)→|      |
  |                 |                 cb[T].on_spy_discovered(spy=S)→|            |
  |←-'spy_result'(discovered=True)---|                        |                   |
  |  [Spy sees penalty modal]         |                        |←-'spy_discovered' |
  |                 |               if not discovered:         |   [Target notified]
  |                 |                 cb[S].on_spy_result(hint=T_hint)→|           |
  |←-'spy_result'(hint=T_hint)--------|                       |                   |
  |  [Spy sees stolen hint privately]  |                       |                   |
```

---

## Threading / Concurrency Model

### Thread Map (Bridge Process)

```
Bridge Process threads:
  [Main thread]             — Flask-SocketIO startup, SocketIO.run()
  [SocketIO worker pool]    — One thread per active WS event handler
  [Pyro5 callback daemon]   — threading.Thread(target=daemon.requestLoop, daemon=True)
                              Receives incoming Pyro5 callback calls from GameServer
```

### Thread Map (GameServer Process)

```
GameServer Process threads:
  [Main thread]             — daemon.requestLoop() (Pyro5 threaded server)
  [Pyro5 thread pool]       — One thread per connected proxy (Bridge has 1 persistent proxy)
  [Phase timer threads]     — threading.Timer per phase (fire once, then replaced)
```

### Thread Safety Rules

1. All GameServer state mutations happen inside `with self._lock` (RLock).
2. GameServer's `_callbacks` dict (mapping player_id → BridgeCallbackReceiver proxy) is also protected by `self._lock`. Add/remove callbacks only under the lock.
3. Phase timers are created inside the lock, but fire outside it. Timer callback must re-acquire lock before touching state.
4. In the Bridge, `socketio.emit()` and `socketio.send()` (the context-free versions on the `socketio` object, not Flask's `emit()`) are safe to call from any thread, including the Pyro5 callback daemon thread.
5. The Bridge session map (`sid → player_id`, `player_id → sid`) is accessed from both SocketIO handler threads and potentially from the Pyro5 callback thread. Protect with a `threading.Lock`.

```python
# Bridge session management
class SessionRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._sid_to_player: dict[str, str] = {}
        self._player_to_sid: dict[str, str] = {}

    def register(self, sid: str, player_id: str):
        with self._lock:
            self._sid_to_player[sid] = player_id
            self._player_to_sid[player_id] = sid

    def remove_by_sid(self, sid: str) -> str | None:
        with self._lock:
            player_id = self._sid_to_player.pop(sid, None)
            if player_id:
                self._player_to_sid.pop(player_id, None)
            return player_id

    def sid_for(self, player_id: str) -> str | None:
        with self._lock:
            return self._player_to_sid.get(player_id)
```

### Phase Timer Pattern (GameServer)

```python
def _start_phase_timer(self, duration: int):
    # Called inside self._lock
    if self._phase_timer:
        self._phase_timer.cancel()
    self._phase_timer = threading.Timer(duration, self._on_timer_fired)
    self._phase_timer.daemon = True
    self._phase_timer.start()

def _on_timer_fired(self):
    # Timer fires outside lock — must re-acquire
    with self._lock:
        self._advance_phase()
        self._broadcast_phase_change()
```

---

## Session / State Management

### Session Identity

- Browser connects → Bridge assigns a `player_id` (UUID4) → stores in `SessionRegistry`.
- `player_id` is sent back to the browser as an acknowledgement to the `join` event.
- Browser stores `player_id` in `localStorage` for reconnection.
- All subsequent browser events include `player_id` OR the Bridge derives it from `request.sid` via `SessionRegistry`.

### Game Room / SocketIO Room

- The Bridge creates a single SocketIO room per game (room name = `game_id`, also a UUID).
- On `join`, Bridge calls `join_room(game_id)` so all players receive broadcast events.
- Private events (spy result, private hint) are emitted with `to=SessionRegistry.sid_for(player_id)` rather than to the room.

### Callback Registration (GameServer Side)

- When Bridge registers with GameServer, it creates a BridgeCallbackReceiver object, starts its Pyro5 daemon in a background thread, and passes the object's URI to GameServer:

```python
# bridge/main.py startup
cb_receiver = BridgeCallbackReceiver(socketio, session_registry)
cb_daemon = Pyro5.api.Daemon()
cb_uri = cb_daemon.register(cb_receiver, objectId="bridge.callback")

# Start callback-receiving daemon in background thread
threading.Thread(target=cb_daemon.requestLoop, daemon=True).start()

# Register URI with Name Server so GameServer can look it up,
# OR pass it directly as a string to GameServer.set_callback_receiver(cb_uri)
```

- GameServer stores one BridgeCallbackReceiver proxy (the Bridge is a single process). All callbacks go through that one proxy.
- On disconnect of all players / game end, GameServer releases the proxy.

### Reconnection

- Browser reconnects with stored `player_id` via a `reconnect` Socket.IO event.
- Bridge re-maps new `sid` to existing `player_id` in SessionRegistry.
- Bridge calls `GameServer.get_state(player_id)` to fetch current game state snapshot.
- Bridge emits `state_restore` event to the reconnecting browser with full state.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Shared Proxy Across SocketIO Handler Threads

**What:** Using a module-level `game_proxy = Pyro5.api.Proxy(...)` shared by all Flask-SocketIO event handlers.

**Why bad:** Pyro5 proxies are not thread-safe. Concurrent calls from the SocketIO thread pool will corrupt the proxy's internal socket state, causing `AttributeError` or silent data mixing.

**Instead:** Create a proxy per call (with-block) or use `threading.local()` with `_pyroClaimOwnership()`.

### Anti-Pattern 2: Synchronous Callbacks + State Reads = Circular Deadlock

**What:** GameServer fires a synchronous (non-oneway) callback to Bridge, Bridge handler calls back into GameServer to read additional state, GameServer is blocked waiting for the callback to return.

**Why bad:** Pyro5 docs explicitly warn: "A→B→C→A has potential to deadlock." The GameServer daemon thread waiting for callback return is the same thread that would handle Bridge's re-entry call.

**Instead:** Mark all server→bridge callbacks `@oneway`. Bridge reads any extra state it needs by making a separate RPC call after emitting the WebSocket event, or GameServer packs all needed data into the callback payload.

### Anti-Pattern 3: Calling socketio.emit() with the Context-Aware emit()

**What:** Inside `BridgeCallbackReceiver` (which runs in the Pyro5 daemon thread, not a Flask request context), calling the context-aware `from flask_socketio import emit` function.

**Why bad:** This raises `RuntimeError: Working outside of request context`.

**Instead:** Always use `socketio.emit(...)` (the method on the SocketIO instance) when emitting from outside a Socket.IO event handler.

### Anti-Pattern 4: Storing Game State in the Bridge

**What:** Caching game state in Bridge memory to avoid RPC roundtrips.

**Why bad:** Bridge and GameServer state diverge on reconnect, phase transitions, or any missed event. Creates a consistency nightmare.

**Instead:** GameServer is the single source of truth. Bridge is stateless regarding game logic (only the sid↔player_id map is acceptable Bridge-local state).

---

## Suggested Build Order

Dependencies flow: Name Server → GameServer skeleton → Bridge skeleton → Integration → Game mechanics → Frontend.

### Stage 1: Infrastructure Skeleton (do first, everything depends on this)

1. Start Pyro5 Name Server (`pyro5 nameserver`)
2. `GameServer` class: empty, registered, requestLoop running — just `ping()` works
3. `Bridge`: Flask-SocketIO app starts, connects to GameServer via Proxy, `ping()` round-trips
4. Validate: `python bridge.py` → `curl localhost:5000/ping` → calls Pyro5 → returns

### Stage 2: Callback Pipeline (do before any game logic)

1. `BridgeCallbackReceiver`: one method `on_test(msg)` → `socketio.emit('test', msg)`
2. Daemon for receiver starts in background thread in Bridge process
3. `GameServer.set_callback_receiver(uri)` → stores proxy → calls `on_test("hello")`
4. Validate: Browser connects, receives `test` event pushed from GameServer without browser requesting it

This stage de-risks the hardest integration point early.

### Stage 3: Player Session and Lobby

1. `join_game` / `leave_game` on GameServer (with RLock)
2. `on_player_joined` / `on_player_left` callbacks
3. Bridge session registry (sid↔player_id)
4. Browser: connect, enter name, see lobby populate in real-time

### Stage 4: Phase Machine + Timer

1. `GameState` with phases: LOBBY → HINT → GUESS → EXCHANGE → SPY → SCORING → (repeat / END)
2. `threading.Timer` per phase in GameServer
3. `on_phase_changed(phase, time_remaining)` callback
4. Browser: timer countdown UI, phase panel switches

### Stage 5: Game Mechanics (in phase order)

5a. HINT phase: `submit_hint`, `on_hint_broadcast` callback, image distribution
5b. GUESS phase: `submit_guess`, WordNet arbitration, `on_guess_result` callback
5c. EXCHANGE phase: `request_exchange` → `accept_exchange`, private/public callbacks
5d. SPY phase: `attempt_spy`, probability roll, `on_spy_result` / `on_spy_discovered`
5e. SCORING phase: `on_scores_updated`, leaderboard

### Stage 6: Chat

1. `send_chat` on GameServer (broadcast to all via callback)
2. Browser: chat panel separate from game actions panel (UX risk: keep UI separation crisp)

### Stage 7: Reconnection + End-of-Game

1. `reconnect` event on Bridge, state restore flow
2. Voting to continue / end (`submit_vote`, `on_game_ended`)
3. Final results screen

---

## Scalability Considerations

This is a 2–4 player academic demo. Scalability is not a primary concern, but avoid decisions that would make the code fragile even at small scale.

| Concern | At 2–4 players (target) | Notes |
|---------|------------------------|-------|
| Pyro5 thread pool | Default THREADPOOL_SIZE (4) is sufficient | Bridge uses 1 persistent callback proxy + short-lived call proxies |
| Timer accuracy | `threading.Timer` drifts slightly under GIL pressure | Acceptable; display client-side countdown for visual smoothness |
| Proxy reconnect cost | Cheap at this scale | Per-call proxy pattern has no measurable cost for ≤4 players |
| WebSocket concurrency | Flask-SocketIO threading mode handles ≤10 simultaneous connections trivially | No need for eventlet/gevent |
| RLock contention | Minimal — all game events serialized through one lock | No bottleneck at 4 players |

---

## Sources

- Pyro5 official docs — client callbacks: https://pyro5.readthedocs.io/en/stable/clientcode.html
- Pyro5 official docs — server concurrency: https://pyro5.readthedocs.io/en/stable/servercode.html
- Pyro5 official docs — tips & tricks (deadlock, proxy release): https://pyro5.readthedocs.io/en/stable/tipstricks.html
- Flask-SocketIO docs — getting started (rooms, sid, background emit): https://flask-socketio.readthedocs.io/en/latest/getting_started.html
- Flask-SocketIO — eventlet retirement discussion: https://github.com/miguelgrinberg/Flask-SocketIO/discussions/2037
- Pyro5 — proxy thread safety ("One single thread 'owns' a proxy"): https://pyro5.readthedocs.io/en/latest/clientcode.html
- Context7 /irmen/pyro5 — daemon threading, oneway, instance modes (HIGH confidence)
