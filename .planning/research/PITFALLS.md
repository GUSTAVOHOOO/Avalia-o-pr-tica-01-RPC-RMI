# Domain Pitfalls

**Domain:** Pyro5 RPC multiplayer game with WebSocket bridge
**Project:** Jogo de Adivinhação Multijogador (CC5SDT / UTFPR 2026-1)
**Researched:** 2026-05-12
**Confidence:** HIGH for Pyro5 pitfalls (official docs verified), MEDIUM for WordNet/Portuguese, MEDIUM for scope management

---

## Critical Pitfalls

Mistakes that cause rewrites, deadlocks, or submission failures.

---

### Pitfall C1: Pyro5 Callback Deadlock — Circular Call on the Same Daemon

**What goes wrong:**
The server calls a registered callback on the bridge client. The bridge client's Pyro daemon is the same process that originally called into the server. If the bridge receives the callback while still executing a server method (i.e., the server calls back into the same proxy chain before the first call returns), the thread pool blocks waiting on itself and the whole system freezes silently.

The classic pattern that triggers this: `Browser → Bridge → GameServer.join_game()`, and inside `join_game()` the server fires `callback.on_player_joined()` back to the bridge, which then tries to forward it as a WebSocket event — but if the bridge is using the same Pyro proxy inside the callback handler that is already in flight, deadlock occurs.

**Why it happens:**
Pyro5 proxies have a single-ownership threading model. One proxy object cannot be shared between threads. If the bridge registers a callback and the callback fires on a different thread than the one that owns the proxy, the response is silently dropped or the call hangs. Additionally, circular call chains (A → B → A) deadlock multiplex-mode servers because the selector is blocked on the first call and cannot dispatch the re-entrant callback.

**Consequences:**
- Server and bridge silently freeze with no exception
- `threading.Timer` phases never fire; game gets stuck
- Hard to reproduce because it is timing-dependent

**Prevention:**
1. Run the Pyro5 daemon in **threaded** server mode (the default), NOT multiplex mode. Multiplex mode is single-threaded and will deadlock on any re-entrant callback.
2. Give each callback a **separate daemon** running in its own background thread. Never share the server-side GameServer proxy between threads in the bridge — create one proxy per thread or use `_pyroClaimOwnership()` when handing off.
3. Set `Pyro5.configure.COMMTIMEOUT = 10` on both server and bridge. This causes a `TimeoutError` instead of an infinite hang, making the deadlock visible immediately.
4. Annotate all broadcast methods on the server with `@Pyro5.server.oneway` so the server does not block waiting for callback acknowledgment from clients. Fire-and-forget callbacks break the circular wait.

**Warning signs:**
- Game goes silent after the first player joins but no exception appears
- CPU usage drops to zero (all threads waiting on sockets)
- Works with one player, breaks with two — classic re-entrant callback symptom

**Phase:** Core RPC / Backend (Phase 1 — before any game mechanics)

**Severity: HIGH**

---

### Pitfall C2: Pyro5 Proxy Shared Across Threads in the Bridge

**What goes wrong:**
The bridge creates one `Pyro5.Proxy` for the GameServer and stores it as a module-level or class-level variable. Flask-SocketIO event handlers run in separate threads. Multiple simultaneous WebSocket events (two players submitting hints at the same time) both call methods on the same proxy object from different threads. Pyro5 detects this and raises `PyroError: proxy is owned by a different thread` — or silently corrupts the connection's data stream.

**Why it happens:**
Pyro5 enforces per-thread proxy ownership strictly. The proxy object wraps a network socket; concurrent writes corrupt the serialized message framing.

**Consequences:**
- Intermittent `PyroError` exceptions that only appear under concurrent load
- Works fine in single-player testing, breaks when evaluators test with 3 players

**Prevention:**
Use a `threading.local()` store in the bridge so each Flask-SocketIO handler thread gets its own proxy instance. Alternatively, use a `queue.Queue` to serialize all GameServer calls through a single dedicated proxy thread.

```python
# Bridge pattern — one proxy per thread
_thread_local = threading.local()

def get_game_proxy():
    if not hasattr(_thread_local, 'proxy'):
        _thread_local.proxy = Pyro5.api.Proxy("PYRONAME:game.server")
    return _thread_local.proxy
```

**Warning signs:**
- `PyroError: proxy is owned by a different thread` in logs
- Only fails when two events arrive within milliseconds of each other

**Phase:** Core RPC / Backend (Phase 1)

**Severity: HIGH**

---

### Pitfall C3: Pyro5 Serpent Serialization — Custom Objects Silently Become Dicts

**What goes wrong:**
You define a `GameState` dataclass or `Player` class and return it from a GameServer method. On the receiving end (the bridge), instead of a `Player` object you get a plain Python `dict` like `{'name': 'Alice', 'score': 0, '__class__': 'Player'}`. Code that calls `.name` on it raises `AttributeError`. This is not an error in Pyro5 — it is by design — but beginners consistently hit it as a mysterious bug.

**Why it happens:**
Serpent (Pyro5's default serializer) serializes custom class instances into dicts for security. It does NOT deserialize them back into class instances unless you explicitly register converter hooks. The dict contains `__class__` as a key but is not the original object.

**Consequences:**
- `AttributeError` on the bridge side when accessing object fields
- Breaks all code that type-checks or uses class methods on returned objects

**Prevention:**
Option A (recommended for academic project): Never return custom class instances from Pyro5 methods. Return plain dicts, lists, and primitives only. This is simpler and more explicit.

Option B (if you need typed objects): Register converters:
```python
Pyro5.api.register_class_to_dict(Player, lambda obj: {'name': obj.name, 'score': obj.score})
Pyro5.api.register_dict_to_class('Player', lambda classname, d: Player(**d))
```

**Warning signs:**
- `AttributeError: 'dict' object has no attribute 'score'` on the bridge side
- Data is present in the dict, just not as the expected type

**Phase:** Core RPC / Backend (Phase 1)

**Severity: HIGH**

---

### Pitfall C4: Serpent Bytes — Binary Data Returns a Dict, Not Bytes

**What goes wrong:**
Any method that returns `bytes` (e.g., reading image file contents for the secret object images) will arrive on the receiver as `{'data': '<base64 string>', 'encoding': 'base64'}` instead of raw bytes. Code that tries to do `len(result)` or `result.decode()` raises `AttributeError` or `TypeError`.

**Why it happens:**
Serpent is a text-based serializer and must encode binary data. The base64 dict is its wire format for bytes.

**Consequences:**
- Image distribution over RPC silently corrupts; browsers receive JSON objects instead of image data

**Prevention:**
For the image distribution use case, return image URLs or filenames (strings) rather than raw bytes over Pyro5. If raw bytes must be transferred, either:
- Call `serpent.tobytes(result)` on the receiver side to decode the dict
- Set `Pyro5.configure.SERPENT_BYTES_REPR = True` before the server starts (requires serpent >= 1.40)

**Warning signs:**
- Image-related `AttributeError: 'dict' object has no attribute 'decode'`
- Response has keys `data` and `encoding` instead of being a bytes value

**Phase:** Core RPC / Backend (Phase 1), hits again during Image Distribution feature

**Severity: MEDIUM** (avoidable by design if images are served via URLs)

---

### Pitfall C5: Flask-SocketIO Async Mode Conflict with Pyro5 Blocking Calls

**What goes wrong:**
Flask-SocketIO started with `async_mode='eventlet'` or `async_mode='gevent'` monkey-patches the socket module. Pyro5 uses standard blocking sockets. After monkey-patching, Pyro5's internal socket calls behave differently — timeouts may be ignored, connections hang, or the eventlet scheduler starves because Pyro5's blocking DNS/socket calls do not yield cooperatively.

**Why it happens:**
Eventlet and gevent work by replacing standard library socket calls with cooperative green-thread versions. Any library that does blocking I/O without `yield` points (including Pyro5) blocks the entire event loop.

**Consequences:**
- WebSocket events queue up but never fire while a Pyro5 call is in progress
- Server appears to work but callbacks arrive seconds late
- Race conditions in phase timers become much more likely

**Prevention:**
Use `async_mode='threading'` for Flask-SocketIO. This is the safe choice for this project because it does not monkey-patch the socket module, runs each event in a proper OS thread, and is fully compatible with Pyro5's blocking network calls.

```python
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')
```

**Warning signs:**
- Pyro5 calls complete but SocketIO events are delayed by 1–5 seconds
- Game works locally but breaks when tested on different machine (latency amplifies the problem)
- Any import of `eventlet` or `gevent` at the top of the bridge file

**Phase:** Bridge implementation (Phase 1/2 boundary)

**Severity: HIGH**

---

### Pitfall C6: Pyro5 Callback Client Daemon Not Running — Callbacks Silently Dropped

**What goes wrong:**
The bridge registers a callback object with the GameServer (`server.register_callback(bridge_callback_proxy)`). But the bridge never starts a Pyro5 daemon to serve incoming calls on the callback object. The server tries to call the callback URI, gets a connection refused, logs an exception, and moves on. The bridge never receives any game events.

**Why it happens:**
Registering a callback means the server needs to make outbound Pyro5 connections back to the client process. The client must be running a daemon and listening on a port, just like a server. Beginners assume registration is enough; it is not.

**Consequences:**
- Zero WebSocket events reach the browser; game state never updates
- Server logs show `ConnectionRefusedError` on every broadcast
- Appears as if callbacks "don't work" when the real issue is no listener

**Prevention:**
```python
# Bridge must start its own daemon for callback objects
callback_daemon = Pyro5.api.Daemon()
callback_obj = GameEventBridge(socketio)
callback_uri = callback_daemon.register(callback_obj)

# Run daemon in background thread
t = threading.Thread(target=callback_daemon.requestLoop, daemon=True)
t.start()

# Then register with game server
game_server.register_callback(callback_uri)
```

**Warning signs:**
- Bridge connects and registers successfully, but no events arrive
- Server logs show `ConnectionRefusedError` or `CommunicationError` during broadcast
- `netstat` shows no listening port on the bridge process

**Phase:** Core RPC / Backend (Phase 1)

**Severity: HIGH**

---

## Moderate Pitfalls

---

### Pitfall M1: Timer Race Condition — Double Phase Transition

**What goes wrong:**
Each game phase has a `threading.Timer` that fires at the end of the phase. A player submits all responses early, triggering a manual phase transition. The timer then fires after the manual transition has already advanced the phase. The server transitions the same game twice: e.g., GUESS → EXCHANGE fires once on last submission, then the timer fires again and transitions EXCHANGE → SPY prematurely, skipping an entire phase.

**Why it happens:**
`threading.Timer.cancel()` only prevents the callback from firing if the timer has not already started executing. There is a race window: the phase-end method calls `timer.cancel()` but the timer function has already been dispatched to a thread and is mid-execution.

**Consequences:**
- Phases skip unexpectedly under fast play
- Scoring phase fires before all players have guessed
- Intermittent; hard to reproduce without concurrent load

**Prevention:**
Use a generation counter (epoch/version number) alongside the timer. The timer callback checks whether the current generation matches the generation it was created with before executing any transition.

```python
self._phase_generation = 0

def _start_phase_timer(self, timeout, next_phase):
    gen = self._phase_generation
    def _on_timeout():
        with self._lock:
            if self._phase_generation == gen:  # still same phase
                self._advance_phase(next_phase)
    t = threading.Timer(timeout, _on_timeout)
    t.daemon = True
    t.start()
    return t

def _advance_phase(self, next_phase):
    # Always increment generation when advancing, inside the lock
    self._phase_generation += 1
    self._current_phase = next_phase
    # ... broadcast
```

**Warning signs:**
- Phase transitions visible in logs firing twice for the same game
- Scoring calculated with zero guesses (scoring fired before guesses submitted)
- Only fails when multiple players act rapidly near timer expiry

**Phase:** Game mechanics (Phase 2)

**Severity: MEDIUM**

---

### Pitfall M2: RLock Held During Pyro5 Callback — Self-Deadlock

**What goes wrong:**
The GameServer acquires `self._lock` to protect game state, then broadcasts events to all registered callbacks while still holding the lock. A callback call is a network operation that blocks until the remote client processes it. If any client is slow (or the bridge is busy), the lock is held for the entire duration. Any other RPC call from another player that also needs `self._lock` blocks. If the timer thread also needs the lock, three-way contention builds up.

**Why it happens:**
Developers see the Pyro5 docs recommend `RLock` for thread-safety and add it everywhere, including around callback dispatch. The lock scope is too wide.

**Consequences:**
- Server becomes single-threaded in practice even with a threadpool daemon
- Timer fires but cannot acquire lock → phase stuck

**Prevention:**
Release the lock before broadcasting callbacks. Capture the snapshot of callback list and relevant state, release the lock, then iterate and call callbacks.

```python
with self._lock:
    callbacks = list(self._callbacks)  # snapshot
    event_data = self._build_event(...)
# Lock released — now safe to do I/O

for cb in callbacks:
    try:
        cb.on_event(event_data)
    except Exception:
        # handle dead callback
        pass
```

**Warning signs:**
- Server handles first few events fine, then slows down exponentially as player count grows
- Thread dump shows all GameServer threads waiting on the same lock
- Latency increases linearly with number of connected players

**Phase:** Core RPC / Backend (Phase 1) and Game Mechanics (Phase 2)

**Severity: MEDIUM**

---

### Pitfall M3: Portuguese WordNet — NLTK's Built-in Support Is Sparse

**What goes wrong:**
The project plans to use WordNet synonyms for guess arbitration ("close enough" matching). NLTK ships a Portuguese wordnet, but the lexical coverage is significantly smaller than the English one. Common everyday words used in a guessing game (e.g., "sofá", "cadeira", "mochila") may have zero synsets or only one synset with no synonyms, causing the arbitration system to always return "not a match" even for obviously correct guesses.

**Why it happens:**
NLTK's Portuguese data is based on a projection of English WordNet. The synset count is approximately 43,000–52,000 entries depending on the dataset used, but synonym relationships between colloquial Brazilian Portuguese words are sparse.

**Evidence:**
- NLTK's built-in OWN-PT data has been described as "few lemmas and synsets" relative to what Brazilian Portuguese speakers expect (GitHub issue #134 on openWordnet-PT).
- The `wn` library (not NLTK) with the `own-pt:1.0.0` dataset provides 52,670 synsets — better than NLTK's bundled version but still incomplete for colloquial words.

**Consequences:**
- Guess arbitration rejects valid synonyms → players lose points unfairly
- Evaluators notice the arbitration "doesn't work" for common Portuguese words
- Temptation to expand the word list manually, which becomes a time sink

**Prevention:**
Use the `wn` library instead of NLTK's wordnet module. Install the own-pt dataset:
```bash
pip install wn
python -m wn download own-pt:1.0.0
```

Provide a fallback: if `wn` returns no synsets, fall back to exact string match (lowercased, stripped). This ensures common words still score correctly even when WordNet has no data.

Also restrict the object image set to words with known good WordNet coverage. Pre-validate all game words against the wordnet at startup; exclude any that return zero synsets.

**Warning signs:**
- Test run: `wn.words('cadeira', pos='n', lang='pt')` returns empty list
- Playtest where correct answers ("sofa" for "sofá") are rejected
- Arbitration always returns False during local testing

**Phase:** Game Mechanics — guess arbitration (Phase 2)

**Severity: MEDIUM**

---

### Pitfall M4: Scope Creep — Web UI Consumes All Development Time

**What goes wrong:**
The project requirements list 10+ distinct UI screens, modals, and visual states. A 2-person team starts building the React/HTML interface before the Pyro5 backend is proven, spending the majority of their time on responsive layout, modal animations, timer color changes, and mobile compatibility. When the deadline approaches, the core RPC mechanics (callbacks, phase transitions, scoring) are incomplete or untested with real concurrency.

**Why it happens:**
UI work produces immediately visible results and feels productive. Backend distributed systems bugs require deliberate testing with multiple terminal sessions and are less satisfying to fix. The UI task list is long and concrete; backend bugs are discovered late.

**Consequences:**
- Beautiful interface, broken backend — evaluators test the RPC logic, not the CSS
- `register_callback`, `EventBroadcaster`, and thread-safety are graded; the lobby gradient is not
- Last-week crunch to get callbacks working with no time to fix race conditions

**Prevention:**
Establish a hard rule: **no UI work until the Pyro5 callback loop works end-to-end with 2 players in a terminal client.** Build a dumb CLI test client (20 lines of Python) that registers callbacks, simulates a player, and verifies events arrive. Only after this is verified in a 3-terminal test (server + 2 CLI clients) should the bridge and UI be started.

Time allocation recommendation for a 2-person team:
- 40% backend (Pyro5 daemon, game state, callbacks, threading)
- 30% bridge (WebSocket ↔ Pyro5 translation)
- 20% UI (only the screens needed to demo: lobby, game, results)
- 10% report

**Warning signs:**
- More than 3 days on UI before a CLI callback test exists
- CSS files larger than game logic files
- "We'll fix the callbacks later" said at any point

**Phase:** All phases — apply rule from day one

**Severity: HIGH** (most common academic project failure mode)

---

### Pitfall M5: Name Server Discovery Failure in Demo Environment

**What goes wrong:**
The Pyro5 Name Server is started on the developer's machine. The bridge and the server both assume Name Server is reachable at the default broadcast address. On the evaluator's network, or when running all processes on different network interfaces (common on laptops with both Wi-Fi and loopback), the broadcast-based Name Server discovery fails silently and the bridge gets `NamingError: name not found`.

**Why it happens:**
`Pyro5.api.locate_ns()` uses a UDP broadcast that can be blocked by OS firewall rules or VPN software. It also only searches the local subnet by default.

**Consequences:**
- Demo fails entirely because the bridge cannot find the GameServer
- Works perfectly in development, fails in front of the professor

**Prevention:**
Always start the Name Server with an explicit host and pass it explicitly in the bridge and server:
```python
# Start Name Server on explicit loopback
pyro5-ns --host 127.0.0.1

# Connect to it explicitly (no broadcast)
ns = Pyro5.api.locate_ns(host="127.0.0.1")
```

Alternatively, use direct URI lookup instead of Name Server for the bridge-to-server connection. For an academic demo on localhost, a hardcoded URI (`PYRO:game.server@localhost:9090`) is simpler and more reliable than broadcast discovery.

**Warning signs:**
- `NamingError` or `CommunicationError: cannot connect to name server` in logs
- Works on developer's machine, fails when demoing on a different laptop or network

**Phase:** Core RPC / Backend (Phase 1 — test on multiple machines before final demo)

**Severity: MEDIUM**

---

## Minor Pitfalls

---

### Pitfall L1: `@expose` Missing — Method Not Callable Remotely

**What goes wrong:**
A new method is added to `GameServer` but the `@Pyro5.api.expose` decorator is forgotten. The client receives `AttributeError: remote object does not have attribute 'new_method'`. Beginners search for bugs in the proxy code and networking when the fix is a single decorator line.

**Prevention:**
Establish a code review habit: every GameServer method added must be checked for `@expose`. Use `@Pyro5.api.expose` on the class level to expose all methods at once if security is not a concern for this academic project.

**Phase:** Any — ongoing

**Severity: LOW** (easy to fix once identified)

---

### Pitfall L2: Pyro5 Threadpool Exhaustion with Idle Proxies

**What goes wrong:**
Each connected proxy (from the bridge to the server) holds a thread in the server's thread pool. The default `THREADPOOL_SIZE` is 40. With 4 players, the bridge holds 4 proxies, and if each callback also holds a proxy for reverse calls, the pool fills. Adding the timer thread and broadcast threads, the pool can exhaust during load testing.

**Prevention:**
Either increase `THREADPOOL_SIZE` or switch the server to multiplex mode for the initial connection handling (note: multiplex mode has other limitations — see Pitfall C1). For this project's scale (2–6 players), the default pool is sufficient if proxies are released promptly and callbacks use `@oneway`.

**Phase:** Game Mechanics (Phase 2)

**Severity: LOW** at 2–6 player scale

---

### Pitfall L3: `threading.Timer` Is Not Cancelable After It Fires

**What goes wrong:**
`timer.cancel()` does nothing if the timer has already executed. Code that calls `cancel()` in the next-phase handler assumes the timer was stopped, but the timer already ran. Related to Pitfall M1 but specifically: the `cancel()` call itself does not raise an exception when called on an already-fired timer, so the bug is silent.

**Prevention:**
Always check `timer.is_alive()` before assuming `cancel()` had effect. Use the generation counter pattern from Pitfall M1 as the authoritative guard, not `cancel()`.

**Phase:** Game Mechanics (Phase 2)

**Severity: LOW** (causes M1 but is separately fixable)

---

### Pitfall L4: Flask Development Server Not Suitable for WebSocket

**What goes wrong:**
`app.run(debug=True)` starts Flask's built-in Werkzeug development server, which does not support WebSocket upgrades. Using `socketio.run(app, debug=True)` is required to get Flask-SocketIO's WebSocket support. Easy mistake when following generic Flask tutorials.

**Prevention:**
Always use `socketio.run(app, ...)` to start the server, never `app.run(...)`.

**Phase:** Bridge (Phase 1/2)

**Severity: LOW** (obvious error, immediately visible)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Pyro5 daemon setup | C6: Callback daemon not started | Start bridge daemon before registering callback |
| First multi-player test | C1: Circular call deadlock | Use `@oneway` on broadcast; set `COMMTIMEOUT` |
| Bridge proxy usage | C2: Proxy shared across threads | `threading.local()` proxy per thread |
| Any method returning Python objects | C3: Custom class becomes dict | Return plain dicts only |
| Image distribution over RPC | C4: Bytes become base64 dict | Serve images via URL, not bytes |
| Bridge startup | C5: Eventlet monkey-patching | Use `async_mode='threading'` |
| Phase timer logic | M1: Double transition | Generation counter in timer callbacks |
| Broadcast while holding lock | M2: RLock held during I/O | Snapshot, release lock, then broadcast |
| Guess arbitration (Portuguese) | M3: WordNet sparse for pt-BR | Use `wn` + own-pt + exact-match fallback |
| Sprint planning | M4: UI scope creep | CLI callback test before any UI work |
| Demo day | M5: Name Server broadcast fail | Hardcode localhost URI or explicit NS host |

---

## Sources

- Pyro5 Tips & Tricks (official): https://pyro5.readthedocs.io/en/latest/tipstricks.html
- Pyro5 Server Code — Threading Modes: https://pyro5.readthedocs.io/en/latest/servercode.html
- Pyro5 Client Code — Callbacks: https://pyro5.readthedocs.io/en/latest/clientcode.html
- Pyro4 Tips (circular deadlock, COMMTIMEOUT pattern — applies to Pyro5): https://pyro4.readthedocs.io/en/stable/tipstricks.html
- Flask-SocketIO Background Thread Threading: https://github.com/miguelgrinberg/Flask-SocketIO/issues/876
- Flask-SocketIO Async Mode Discussion: https://github.com/miguelgrinberg/Flask-SocketIO/discussions/1601
- OpenWordnet-PT NLTK Issue (coverage gaps): https://github.com/own-pt/openWordnet-PT/issues/134
- wn Python library (modern Portuguese wordnet): https://pypi.org/project/wn/
- Serpent bytes serialization issue: https://github.com/irmen/Serpent/issues/38
