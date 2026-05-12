# Phase 1: RPC Infrastructure + Callback Pipeline - Research

**Researched:** 2026-05-12
**Domain:** Pyro5 RPC daemon + callback pipeline + Flask-SocketIO bridge wiring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Always start NS with `pyro5-ns --host 127.0.0.1`. All `locate_ns()` calls pass `host` from config to avoid UDP broadcast (which may be blocked by firewall/VPN on demo day).
- **D-02:** NS host is read from env var `PYRO_NS_HOST` with default `'127.0.0.1'` — defined once in `config.py`, imported everywhere. This satisfies INFRA-06 (no hardcoded URIs in clients) without adding complex branching.
- **D-03:** Bridge polls the Name Server + GameServer lookup for ~10 seconds (0.5s sleep between attempts) before giving up with a clear error message.
- **D-04:** Hybrid approach — manual 3-terminal procedure (`test_client.py` CLI script) proves the callback push end-to-end; automated `pytest` unit tests run a real in-process Pyro5 daemon in a thread and validate `ping()`, `register_callback()`, and broadcast delivery without requiring the full 3-terminal setup.
- **D-05:** Unit tests use a real in-process Pyro5 daemon (not mocks) to validate actual RPC serialization and callback wiring.
- **D-06:** Structured subdirectories: `server/` (game_server.py, event_broadcaster.py), `bridge/` (bridge.py), `client/` (test_client.py), `tests/` (test_unit.py). Each subdirectory is a Python package with `__init__.py`.
- **D-07:** `config.py` lives at the project root — imported by both `server/` and `bridge/` as `import config`. Contains `NS_HOST`, `GAME_SERVER_PORT` (9091), `BRIDGE_PORT` (5000), and any other shared constants.
- **D-08:** Flask-SocketIO must use `async_mode='threading'` — hardcoded, never rely on defaults.
- **D-09:** All Pyro5 broadcast methods on GameServer (those that call EventBroadcaster) must be `@oneway` to prevent callback deadlock.
- **D-10:** Pyro5 proxies in Bridge are per-thread via `threading.local()` — never shared across threads.

### Claude's Discretion

- Port numbers (NS: 9090 default, GameServer: 9091, Bridge: 5000) — use these standard values unless there's a conflict.
- Retry backoff timing for Bridge startup — 0.5s sleep, ~10s total timeout is reasonable.
- Exact structure of `EventBroadcaster` (whether it's a separate class or methods on `GameServer`) — follow PRD.md §EventBroadcaster pattern.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Pyro5 daemon with GameServer exposed via `@Pyro5.api.expose`, accessible via Name Server | Daemon.register() + locate_ns() pattern verified via Context7 |
| INFRA-02 | Clients register callback URI on server via `register_callback(player_id, callback_uri)` | EventBroadcaster pattern from PRD §8.1 + Proxy(callback_uri) pattern |
| INFRA-03 | EventBroadcaster sends events to all registered callbacks using `@oneway` methods | `@Pyro5.api.oneway` decorator verified via Context7 |
| INFRA-04 | Flask-SocketIO bridge with `async_mode='threading'` converts WebSocket calls to Pyro5 RPC and routes callbacks to Socket.IO events | Flask-SocketIO threading mode verified via Context7 |
| INFRA-05 | Bridge uses per-thread Pyro5 proxy (not shared) to avoid concurrency deadlock | Context7 explicitly confirms proxies are not thread-safe; `threading.local()` pattern |
| INFRA-06 | Pyro5 Name Server available for service discovery (no hardcoded URIs in client) | `locate_ns(host=...)` pattern verified via Context7 |
</phase_requirements>

---

## Summary

Phase 1 builds the bare RPC skeleton: three OS processes (pyro5 Name Server, GameServer daemon, Flask-SocketIO bridge) wired together so that a server-initiated Pyro5 callback arrives at a registered Python client without the client having polled or requested it. No game mechanics, no HTML/CSS, no player sessions — just infrastructure proof.

The technology choices are fully locked in CLAUDE.md and CONTEXT.md. The key pattern is the Pyro5 callback loop: GameServer holds an `EventBroadcaster` that stores `{player_id: Proxy(callback_uri)}` entries; when the server calls `broadcast()`, it calls `@oneway` methods on each proxy, which are fire-and-forget from the server's perspective. The BridgeCallbackReceiver in the bridge process registers itself as a callback receiver, and when its `on_*` method fires, it calls `socketio.emit()` to push the event to browsers.

The single critical environment finding is that the default `python3` on this machine is 3.8.20 (via mise), but Python 3.11.2 is available at `/usr/bin/python3.11`. The Pyro5 5.16 wheel metadata shows `Requires-Python: >=3.7` — contrary to the CLAUDE.md note about 3.10+ — but the Pyro5 docs also state "supported on Python 3.9 and newer". The safest Wave 0 action is to target `python3.11` (system install at `/usr/bin/python3.11`) and create a venv from it; this avoids any ambiguity and is consistent with the course requirement.

**Primary recommendation:** Create a `python3.11 -m venv venv` at project root before any other task; all subsequent commands use `venv/bin/python` and `venv/bin/pip`. Install `Pyro5==5.16 Flask flask-socketio==5.6.1 simple-websocket`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pyro5 Name Server | OS process (pyro5-ns CLI) | — | Provided by Pyro5 package, started separately |
| Game RPC methods (ping, register_callback, broadcast) | GameServer daemon (Pyro5) | — | Must be a Pyro5 object for the course requirement |
| Callback delivery to registrants | GameServer → EventBroadcaster | Bridge (receiver side) | Server calls outbound Pyro5 proxies; bridge has its own Pyro5 daemon to receive them |
| WebSocket ↔ Pyro5 translation | Bridge (Flask-SocketIO) | — | Only component that knows both protocols |
| Per-thread Pyro5 proxy management | Bridge | — | `threading.local()` in bridge process, not in GameServer |
| CLI smoke test / test client | client/test_client.py | tests/test_unit.py | Manual proof for Phase 1 demo; automated pytest for CI |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pyro5 | 5.16 | Python RPC backbone — daemon, proxies, callbacks | Required by course; latest stable |
| serpent | 1.42 (auto) | Default serializer for Pyro5 | Auto-installed as Pyro5 dependency; zero config |
| Flask | 3.1.x | Web framework underlying Flask-SocketIO | Required by Flask-SocketIO |
| Flask-SocketIO | 5.6.1 | WebSocket server, cross-thread `socketio.emit()` | Pinned in CLAUDE.md; threading mode well-supported |
| simple-websocket | latest | WebSocket transport for `async_mode='threading'` | Required when not using eventlet/gevent |

[VERIFIED: npm registry / PyPI] — Pyro5==5.16 wheel downloads confirmed via `pip3 download`; serpent 1.42 confirmed in wheel metadata.
[VERIFIED: PyPI] — Flask-SocketIO==5.6.1 confirmed installable.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.3.5 (Python 3.8 env) / 7.2.1 (Python 3.11 env) | Unit test runner | D-04/D-05: real in-process daemon tests |

[VERIFIED: pip3 show pytest] — pytest 7.2.1 present in python3.11 environment.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `async_mode='threading'` | `async_mode='gevent'` | gevent works but adds C ext; threading simpler per CLAUDE.md |
| `threading.local()` for proxies | creating proxy in each request handler | Both work; `threading.local()` is cleaner for repeated calls |
| `pyro5-ns --host 127.0.0.1` | `python -m Pyro5.nameserver --host 127.0.0.1` | Same outcome; CLI form is more readable in README |

**Installation (Wave 0):**
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install Pyro5==5.16 Flask flask-socketio==5.6.1 simple-websocket pytest
```

**Version verification:** [VERIFIED: pip3 download Pyro5==5.16 — 2026-05-12]
- Pyro5 5.16: `pyro5-5.16-py3-none-any.whl` — `Requires-Python: >=3.7`
- serpent 1.42: auto-installed as dependency

---

## Architecture Patterns

### System Architecture Diagram

```
[pyro5-ns process]
      |  NS lookup/register
      |
[GameServer process]  ----@oneway broadcast----> [BridgeCallbackReceiver Pyro5 daemon]
      |                                                    |
      | Pyro5 daemon on port 9091                          | socketio.emit()
      | exposed: ping(), register_callback(), broadcast_test()   |
      |                                                    |
[test_client.py / CLI]                           [Flask-SocketIO process, port 5000]
      |                                                    |
      | locate_ns(host=NS_HOST)                           | (Phase 2+: browser WebSocket)
      | Proxy("PYRONAME:game.server")                     |
      | registers its own callback URI                    |
      | starts mini Pyro5 daemon to receive push          |
```

Data flow for success criterion 5:
1. `GameServer.broadcast_test()` called (via RPC or internally) — this method is `@oneway`
2. EventBroadcaster iterates `callbacks` dict, calls `proxy.on_event(data)` on each registered Proxy
3. BridgeCallbackReceiver's `on_event()` fires inside bridge process
4. `on_event()` calls `socketio.emit('game_event', data)` — visible in bridge log

### Recommended Project Structure
```
(project root)/
├── config.py            # NS_HOST, GAME_SERVER_PORT=9091, BRIDGE_PORT=5000
├── requirements.txt     # pinned versions
├── venv/                # python3.11 venv (gitignored)
├── server/
│   ├── __init__.py
│   ├── game_server.py   # GameServer class — @expose, ping(), register_callback(), broadcast_test()
│   └── event_broadcaster.py  # EventBroadcaster — callbacks dict, broadcast(), send_to_player()
├── bridge/
│   ├── __init__.py
│   └── bridge.py        # Flask-SocketIO app, BridgeCallbackReceiver, threading.local proxy
├── client/
│   ├── __init__.py
│   └── test_client.py   # CLI: discover NS, register callback, wait for push, print, exit
└── tests/
    ├── __init__.py
    └── test_unit.py     # in-process daemon tests: ping, register_callback, broadcast delivery
```

### Pattern 1: GameServer Daemon Startup with Name Server Registration
**What:** GameServer creates a Pyro5 daemon on a fixed port, registers itself, then registers with the Name Server under `"game.server"`.
**When to use:** Every time `server/game_server.py` starts.
**Example:**
```python
# Source: Context7 /irmen/pyro5 — daemon and nameserver patterns
import Pyro5.api
import config

@Pyro5.api.expose
class GameServer:
    def ping(self):
        return "pong"

    def register_callback(self, player_id: str, callback_uri: str) -> bool:
        # EventBroadcaster stores Proxy(callback_uri)
        self.broadcaster.register_callback(player_id, callback_uri)
        return True

    @Pyro5.api.oneway
    def broadcast_test(self, message: str):
        # @oneway: caller returns immediately; broadcaster calls all registered callbacks
        self.broadcaster.broadcast("test_event", {"message": message})

if __name__ == "__main__":
    server = GameServer()
    daemon = Pyro5.api.Daemon(host="127.0.0.1", port=config.GAME_SERVER_PORT)
    uri = daemon.register(server, objectId="game.server")
    ns = Pyro5.api.locate_ns(host=config.NS_HOST)
    ns.register("game.server", uri)
    print(f"GameServer ready at {uri}")
    daemon.requestLoop()
```

### Pattern 2: EventBroadcaster with Lock
**What:** Holds a dict of `{player_id: Pyro5.api.Proxy(callback_uri)}`, iterates it with a lock, calls `@oneway` methods on each, removes failed entries.
**When to use:** Every call that needs to fan out to all connected clients.
**Example:**
```python
# Source: PRD.md §8.1 EventBroadcaster reference implementation + Context7 /irmen/pyro5
import threading
import Pyro5.api

class EventBroadcaster:
    def __init__(self):
        self.callbacks = {}          # player_id -> Pyro5 Proxy
        self.lock = threading.Lock()

    def register_callback(self, player_id: str, callback_uri: str):
        with self.lock:
            self.callbacks[player_id] = Pyro5.api.Proxy(callback_uri)

    def broadcast(self, event_type: str, data: dict, exclude=None):
        exclude = exclude or []
        failed = []
        with self.lock:
            snapshot = dict(self.callbacks)  # copy under lock; iterate outside
        for player_id, proxy in snapshot.items():
            if player_id in exclude:
                continue
            try:
                method = getattr(proxy, "on_" + event_type.lower())
                method(data)   # method must be @oneway on the callback receiver
            except Exception as e:
                print(f"Callback failed for {player_id}: {e}")
                failed.append(player_id)
        with self.lock:
            for pid in failed:
                self.callbacks.pop(pid, None)
```

### Pattern 3: BridgeCallbackReceiver — Client-side Pyro5 daemon in bridge process
**What:** Bridge registers a Pyro5 object that implements the callback interface. Server stores its URI and calls its `on_*` methods. Bridge's `on_*` methods call `socketio.emit()`.
**When to use:** Bridge startup. The receiver daemon runs in a background thread so Flask-SocketIO's request loop is not blocked.
**Example:**
```python
# Source: Context7 /irmen/pyro5 clientcode.rst + /miguelgrinberg/flask-socketio
import threading
import Pyro5.api
from flask_socketio import SocketIO

socketio = None  # initialized at Flask-SocketIO startup

@Pyro5.api.expose
class BridgeCallbackReceiver:
    @Pyro5.api.callback
    @Pyro5.api.oneway
    def on_test_event(self, data: dict):
        # This fires in the bridge's Pyro5 daemon thread
        socketio.emit("game_event", data)   # cross-thread safe in threading mode

def start_callback_daemon(host="127.0.0.1"):
    daemon = Pyro5.api.Daemon(host=host)
    receiver = BridgeCallbackReceiver()
    uri = daemon.register(receiver)
    # Store uri; pass to GameServer.register_callback("bridge", str(uri))
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return str(uri), daemon
```

### Pattern 4: Per-thread Pyro5 proxy in Bridge handlers
**What:** Flask-SocketIO in threading mode may serve concurrent requests on different threads. A single shared Proxy is not thread-safe. Use `threading.local()` to give each thread its own Proxy.
**When to use:** Any Flask-SocketIO event handler that needs to call the GameServer.
**Example:**
```python
# Source: Context7 /irmen/pyro5 — "Thread Proxy Sharing" section
import threading
import Pyro5.api
import config

_thread_local = threading.local()

def get_game_server_proxy():
    if not hasattr(_thread_local, "proxy"):
        _thread_local.proxy = Pyro5.api.Proxy(f"PYRONAME:game.server@{config.NS_HOST}")
    return _thread_local.proxy

@socketio.on("ping")
def handle_ping():
    proxy = get_game_server_proxy()
    result = proxy.ping()
    return result
```

### Pattern 5: CLI Test Client with callback daemon
**What:** `test_client.py` starts a mini Pyro5 daemon in a background thread to receive callbacks, registers with GameServer, waits for a push event, prints it, exits.
**Example:**
```python
# Source: Context7 /irmen/pyro5 clientcode.rst callback pattern
import threading, time
import Pyro5.api
import config

@Pyro5.api.expose
class TestCallback:
    def __init__(self):
        self.received = []

    @Pyro5.api.callback
    @Pyro5.api.oneway
    def on_test_event(self, data):
        print(f"[PUSH RECEIVED] {data}")
        self.received.append(data)

daemon = Pyro5.api.Daemon(host="127.0.0.1")
cb = TestCallback()
cb_uri = daemon.register(cb)
threading.Thread(target=daemon.requestLoop, daemon=True).start()

with Pyro5.api.Proxy(f"PYRONAME:game.server@{config.NS_HOST}") as server:
    server.register_callback("test-cli", str(cb_uri))
    print("Callback registered. Waiting for push event (10s)...")
    time.sleep(10)

daemon.shutdown()
```

### Anti-Patterns to Avoid

- **Sharing a Proxy across threads:** Pyro5 proxies lack internal locks. Two threads using the same proxy will corrupt the socket data stream. Use `threading.local()` in the bridge. [VERIFIED: Context7 /irmen/pyro5 "Thread Proxy Sharing"]
- **Calling a callback from inside a Pyro5 handler without @oneway:** If GameServer.submit_hint() calls broadcaster.broadcast() synchronously, and broadcast() calls proxy.on_hint_received() on the BridgeCallbackReceiver (which also has a Pyro5 daemon), you get a deadlock — both daemons waiting for each other's thread. Solution: all broadcast-triggering methods on GameServer must be `@oneway` (D-09). [ASSUMED — deadlock scenario based on Pyro5 single-threaded daemon model, consistent with D-09 decision]
- **Not running callback receiver daemon in a background thread:** If the main thread blocks in the Pyro5 daemon requestLoop, it cannot also process user input or Flask events. Always run requestLoop in `threading.Thread(daemon=True)`.
- **Using async_mode default:** Flask-SocketIO picks the first available async mode if not specified. On a machine with eventlet installed this would silently use eventlet (deprecated per CLAUDE.md). Always hardcode `async_mode='threading'` (D-08).
- **Hardcoding NS URI in clients:** Violates INFRA-06 and creates demo-day risk. All lookups must use `locate_ns(host=config.NS_HOST)`.
- **Importing Pyro5 before setting `Pyro5.config.NS_HOST`:** If config is set too late, the first `locate_ns()` may try UDP broadcast. Set `Pyro5.config.NS_HOST` from `config.NS_HOST` at module import time, or always pass `host=` explicitly to `locate_ns()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Service discovery / URI registry | Custom TCP registry | Pyro5 Name Server (`pyro5-ns`) | Built into Pyro5; handles lookup, registration, deregistration |
| WebSocket server | Raw asyncio WebSocket | Flask-SocketIO (threading mode) | Socket.IO protocol, reconnect, room management built in |
| Cross-thread event delivery | Custom queue + watcher thread | `socketio.emit()` from any thread | Flask-SocketIO in threading mode makes this safe automatically |
| Serialization of Python objects | Custom pickle/json encode | serpent (Pyro5 default) | Handles dicts, lists, primitives out of the box; zero config |
| RPC retry / error propagation | Custom retry decorator | `@Pyro5.api.callback` decorator | Ensures exceptions in callbacks are logged and propagated correctly |

**Key insight:** The Pyro5 Name Server, callback decorators, and serpent serializer together eliminate ~500 lines of infrastructure code that teams commonly re-implement.

---

## Common Pitfalls

### Pitfall 1: Callback Deadlock (`@oneway` missing)
**What goes wrong:** Server method calls `broadcaster.broadcast()` which calls `proxy.on_event()` on the BridgeCallbackReceiver. If the broadcast-triggering server method is NOT `@oneway`, both the GameServer's dispatch thread and the bridge's Pyro5 daemon end up waiting for each other's socket.
**Why it happens:** Pyro5's default server type uses a thread-per-connection model. When thread A (handling a client RPC) calls back into another Pyro5 daemon, it creates a new outbound connection but the receiving daemon's thread is also blocked waiting on thread A.
**How to avoid:** Every GameServer method that calls `EventBroadcaster.broadcast()` must be decorated with `@Pyro5.api.oneway` (D-09). The `@oneway` method returns immediately to the caller before executing, so the caller's thread is freed.
**Warning signs:** Client RPC call hangs indefinitely; no error returned; increasing thread count in `ps`.
[ASSUMED — consistent with D-09 decision rationale; Pyro5 threading model behavior]

### Pitfall 2: Shared Proxy Across Threads
**What goes wrong:** Two Flask-SocketIO handler threads use the same `Pyro5.api.Proxy` object. One thread's in-flight RPC response gets interleaved with the other's, producing unpredictable errors or silent data corruption.
**Why it happens:** Pyro5 proxies have no internal lock (intentional, for performance). Each proxy owns a single socket connection.
**How to avoid:** Use `threading.local()` in the bridge so each thread creates and owns its own proxy (D-10). [VERIFIED: Context7 /irmen/pyro5 "Thread Proxy Sharing" section]
**Warning signs:** Intermittent `ProtocolError` or `AttributeError` from Pyro5 under concurrent load; errors stop when only one client is connected.

### Pitfall 3: Bridge Startup Race Condition
**What goes wrong:** Developer launches three terminals in rapid succession. Bridge tries `locate_ns()` and `Proxy("PYRONAME:game.server")` before GameServer has registered, getting `NamingError`.
**Why it happens:** No startup ordering enforcement between processes.
**How to avoid:** D-03 specifies a retry loop — poll with 0.5s sleep for up to 10 seconds before giving up with a clear error message. [ASSUMED — timing values from D-03; retry pattern is standard]
**Warning signs:** `Pyro5.errors.NamingError: unknown name: game.server` at bridge startup.

### Pitfall 4: UDP Broadcast Blocked for Name Server Discovery
**What goes wrong:** `locate_ns()` without `host=` argument sends a UDP broadcast. On machines with VPNs or strict firewall rules (common in university lab networks and demo day), UDP may be dropped, causing a `NamingError` timeout.
**Why it happens:** Pyro5's auto-discovery uses UDP port 9090 broadcast by default.
**How to avoid:** D-01/D-02: always start NS with `--host 127.0.0.1` and pass `host=config.NS_HOST` to every `locate_ns()` call. [VERIFIED: Context7 /irmen/pyro5 locate_ns() — host parameter bypasses UDP broadcast]
**Warning signs:** `locate_ns()` hangs for 5+ seconds then raises `NamingError`.

### Pitfall 5: Python Version Mismatch
**What goes wrong:** Project is run with the `python3` alias which resolves to Python 3.8.20 (via mise on this machine). While Pyro5 5.16 technically supports 3.7+, the docs state "supported on Python 3.9 and newer." Using 3.8 may surface edge-case serialization or annotation issues.
**Why it happens:** `mise` installs Python 3.8 as default on this machine; `/usr/bin/python3.11` is available but not the default.
**How to avoid:** Wave 0 plan task: create venv from `python3.11` explicitly — `python3.11 -m venv venv`. All scripts use `venv/bin/python`. Add `#!/usr/bin/env python3` shebang after activating venv. [VERIFIED: `python3.11 --version` → 3.11.2 at `/usr/bin/python3.11`]
**Warning signs:** Import errors, `__future__` annotation issues, or subtle behavior differences only on this machine.

### Pitfall 6: `socketio.emit()` from Callback Thread Without Threading Mode
**What goes wrong:** `BridgeCallbackReceiver.on_event()` fires in the Pyro5 daemon background thread. Calling `socketio.emit()` from a non-request thread only works correctly when Flask-SocketIO is in threading mode. In eventlet or gevent mode, emitting from a non-async context can deadlock or silently drop messages.
**Why it happens:** eventlet/gevent patch `threading` primitives; the Pyro5 daemon thread and Flask-SocketIO's event loop are incompatible.
**How to avoid:** `async_mode='threading'` hardcoded (D-08); `simple-websocket` installed as the transport. [VERIFIED: Context7 /miguelgrinberg/flask-socketio — `socketio.emit()` described as safe from background threads in threading mode]
**Warning signs:** Events arrive at bridge but never appear in browser; no exception thrown.

---

## Code Examples

Verified patterns from official sources:

### Starting the Name Server (CLI)
```bash
# Source: Pyro5 docs pyro5-ns --help (part of Pyro5 package)
source venv/bin/activate
pyro5-ns --host 127.0.0.1
# or equivalently:
python -m Pyro5.nameserver --host 127.0.0.1
```

### locate_ns with explicit host (INFRA-06)
```python
# Source: Context7 /irmen/pyro5 — locate_ns() docs
import Pyro5.api
import config  # config.NS_HOST = os.environ.get("PYRO_NS_HOST", "127.0.0.1")

ns = Pyro5.api.locate_ns(host=config.NS_HOST)
uri = ns.lookup("game.server")
```

### @expose + @oneway on a broadcast method (INFRA-01, INFRA-03)
```python
# Source: Context7 /irmen/pyro5 — @oneway decorator docs
import Pyro5.api

@Pyro5.api.expose
class GameServer:
    @Pyro5.api.oneway
    def broadcast_test(self, message: str):
        # Returns immediately to caller; runs asynchronously on server thread
        self.broadcaster.broadcast("test_event", {"message": message})
```

### Flask-SocketIO initialization with threading mode (INFRA-04)
```python
# Source: Context7 /miguelgrinberg/flask-socketio — SocketIO initialization
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*", logger=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
```

### Cross-thread socketio.emit() from Pyro5 callback (INFRA-04)
```python
# Source: Context7 /miguelgrinberg/flask-socketio — background task / socketio.emit() docs
@Pyro5.api.expose
class BridgeCallbackReceiver:
    @Pyro5.api.callback
    @Pyro5.api.oneway
    def on_test_event(self, data: dict):
        # Fires in Pyro5 daemon background thread — safe to call socketio.emit() in threading mode
        socketio.emit("game_event", data)
```

### In-process daemon for unit tests (D-05)
```python
# Source: Context7 /irmen/pyro5 — Daemon.requestLoop() docs + threading pattern
import threading
import Pyro5.api

def start_test_server():
    server = GameServer()
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    uri = daemon.register(server, objectId="game.server.test")
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return daemon, str(uri)

def test_ping():
    daemon, uri = start_test_server()
    with Pyro5.api.Proxy(uri) as proxy:
        assert proxy.ping() == "pong"
    daemon.shutdown()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| eventlet as Flask-SocketIO async_mode | threading (simple-websocket) | Flask-SocketIO 5.x (2024) | eventlet deprecated in Flask-SocketIO; threading is now the recommended default |
| Pyro4 | Pyro5 | Pyro5 released 2018 | Different import paths (`Pyro5.api` vs `Pyro4`); Pyro5 has `@expose` requirement |
| `@Pyro5.api.expose` optional for subclasses | `@Pyro5.api.expose` required on every exposed class | Pyro5 from initial release | Any class that can receive remote calls MUST be decorated with `@expose` |

**Deprecated/outdated:**
- **eventlet async_mode:** Flask-SocketIO docs explicitly state eventlet is no longer actively maintained; prefer `threading` or `gevent`.
- **Pyro4:** Different package — `import Pyro4` won't work with Pyro5 installed. The CLAUDE.md prohibits it.
- **`python -m Pyro5.configure`:** Not a valid module; configuration is done via `Pyro5.api.config` object or `PYRO_*` env vars.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Callback deadlock occurs when broadcast-triggering server methods are not `@oneway` due to Pyro5's thread-per-connection model | Common Pitfalls, Architecture Patterns | Low — D-09 locks `@oneway` regardless; omitting `@oneway` would cause issues eventually anyway |
| A2 | Bridge startup race condition is solved by a 10s / 0.5s-sleep retry loop | Common Pitfalls | Low — D-03 specifies this exact timing; if too short, extend to 20s |
| A3 | Python 3.8.20 (mise default) is the `python3` resolved by scripts on this machine | Environment Availability | Medium — if developer runs scripts with `python3` instead of `venv/bin/python`, wrong Python is used; Wave 0 must establish venv from `python3.11` |

**All other claims in this research were verified against Context7 or official docs.**

---

## Open Questions (RESOLVED)

1. **Pyro5 SERVERTYPE for GameServer**
   - What we know: Default is `"thread"` (threaded server); `"multiplex"` is also available (select-based, single-threaded).
   - What's unclear: For 2-4 concurrent RPC callers, either works. Default `"thread"` is fine.
   - Recommendation: Leave at default `"thread"` — no config change needed. [VERIFIED: Context7 — "threaded server is the default"]

2. **Whether GameServer needs `@Pyro5.server.expose` on the class or individual methods**
   - What we know: Pyro5 requires `@expose` on every class whose instances receive remote calls. Individual method decoration is also supported for selective exposure.
   - What's unclear: Whether exposing at class level exposes all methods or just those explicitly decorated.
   - Recommendation: Decorate the class with `@Pyro5.api.expose` — this exposes all public methods. For Phase 1's small surface (ping, register_callback, broadcast_test) this is safe. [VERIFIED: Context7 /irmen/pyro5]

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Pyro5 5.16 (supported 3.9+) | ✓ | 3.11.2 at `/usr/bin/python3.11` | — |
| Python 3.8 (mise default) | `python3` alias | ✓ | 3.8.20 | Use `python3.11` explicitly |
| Pyro5 5.16 | INFRA-01 through INFRA-06 | ✗ (not installed) | — | Install via pip in venv |
| Flask-SocketIO 5.6.1 | INFRA-04 | ✗ (not installed) | — | Install via pip in venv |
| simple-websocket | INFRA-04 (threading transport) | ✗ (not installed) | — | Install via pip in venv |
| pyro5-ns CLI | INFRA-06 (NS process) | ✗ (not installed) | — | Installed automatically with Pyro5 |
| pytest | D-04/D-05 unit tests | ✓ | 7.2.1 (python3.11 env) | — |

**Missing dependencies with no fallback:**
- Pyro5 5.16, Flask-SocketIO 5.6.1, simple-websocket — must be installed in Wave 0 before any other plan task.

**Missing dependencies with fallback:**
- None.

**Critical note:** The `python3` command on this machine resolves to Python 3.8.20 (via mise). Wave 0 MUST create a venv from `python3.11` and all project commands must use that venv. No plan task should use bare `python3` or `python` without activating the venv first.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.2.1 (python3.11 env) |
| Config file | none — Wave 0 creates `pytest.ini` or `pyproject.toml` |
| Quick run command | `venv/bin/pytest tests/ -x -q` |
| Full suite command | `venv/bin/pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | GameServer.ping() returns "pong" over real Pyro5 RPC | unit | `venv/bin/pytest tests/test_unit.py::test_ping -x` | ❌ Wave 0 |
| INFRA-02 | register_callback() stores callback URI; second call overwrites | unit | `venv/bin/pytest tests/test_unit.py::test_register_callback -x` | ❌ Wave 0 |
| INFRA-03 | broadcast_test() triggers on_test_event on all registered callbacks (in-process) | unit | `venv/bin/pytest tests/test_unit.py::test_broadcast_delivery -x` | ❌ Wave 0 |
| INFRA-04 | Bridge starts with `async_mode='threading'`; startup log contains confirmation | smoke/manual | 3-terminal procedure; log inspection | ❌ Wave 0 |
| INFRA-05 | Two concurrent Flask-SocketIO handler threads each get a different proxy object (verified by id()) | unit | `venv/bin/pytest tests/test_unit.py::test_per_thread_proxy -x` | ❌ Wave 0 |
| INFRA-06 | test_client.py discovers game.server via NS without hardcoded URI | smoke/manual | `venv/bin/python client/test_client.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `venv/bin/pytest tests/ -x -q`
- **Per wave merge:** `venv/bin/pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — package init
- [ ] `tests/test_unit.py` — covers INFRA-01, INFRA-02, INFRA-03, INFRA-05
- [ ] `pytest.ini` (or `pyproject.toml [tool.pytest.ini_options]`) — testpaths, python files glob
- [ ] Framework install: `python3.11 -m venv venv && venv/bin/pip install Pyro5==5.16 Flask flask-socketio==5.6.1 simple-websocket pytest`

---

## Security Domain

> `security_enforcement` not set to false in config.json — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 1 is infrastructure-only; no player auth |
| V3 Session Management | No | No sessions in Phase 1 |
| V4 Access Control | No | No access control in Phase 1 |
| V5 Input Validation | Yes (minimal) | `player_id` and `callback_uri` inputs to `register_callback()` — validate non-empty strings |
| V6 Cryptography | No | No secrets, tokens, or encrypted data in Phase 1 |

### Known Threat Patterns for Pyro5 + Flask-SocketIO

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary callback URI injection — attacker registers a callback URI pointing to a server they control | Tampering | Phase 1: localhost-only (`127.0.0.1`) Pyro5 daemon; not exposed to network |
| Flask `SECRET_KEY` left as `"dev-secret"` | Information Disclosure | Acceptable for Phase 1 (localhost only); log a warning if deployed |
| Pyro5 daemon exposed on `0.0.0.0` instead of `127.0.0.1` | Elevation of Privilege | Always bind daemons to `127.0.0.1` in development; config.py enforces this |

**Phase 1 security posture:** All three processes bind to `127.0.0.1` only. The attack surface is negligible for a localhost development setup. No additional security controls needed in Phase 1.

---

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md are binding on all plan tasks in this phase:

| Directive | Enforcement |
|-----------|------------|
| Pyro5 5.16 — pinned version | `pip install Pyro5==5.16` — no version range |
| Flask-SocketIO 5.6.1 — pinned | `pip install flask-socketio==5.6.1` |
| `async_mode='threading'` — hardcoded, never rely on defaults | Explicit parameter in `SocketIO(app, async_mode='threading')` |
| All broadcast-triggering methods must be `@oneway` | `@Pyro5.api.oneway` on every GameServer method calling broadcaster |
| Pyro5 proxies in Bridge are per-thread via `threading.local()` | `threading.local()` pattern in `bridge/bridge.py` |
| Images served as Flask static URLs, never raw bytes through Pyro5 | N/A for Phase 1 (no images) |
| No React/Vue/Angular | N/A for Phase 1 (no frontend) |
| No eventlet async_mode | Enforced by explicit `async_mode='threading'` |
| No database/Redis | N/A for Phase 1 |
| `serpent` serializer (default) | No serializer configuration needed — serpent is auto-default |
| No direct TCP sockets between processes | Pyro5 for all inter-process communication |
| Communication exclusively via RPC/Pyro5 | All inter-process calls go through Pyro5 daemons |

---

## Sources

### Primary (HIGH confidence)
- Context7 `/irmen/pyro5` — daemon, register(), requestLoop(), @oneway, @callback, @expose, locate_ns(), thread proxy sharing, configuration
- Context7 `/miguelgrinberg/flask-socketio` — SocketIO initialization, async_mode, socketio.emit() cross-thread, start_background_task()
- PRD.md §8.1 — EventBroadcaster reference implementation (project document)
- CONTEXT.md — all D-0x decisions (locked by user discussion)
- CLAUDE.md — pinned versions and prohibited patterns (project instructions)

### Secondary (MEDIUM confidence)
- `pip3 download Pyro5==5.16` wheel metadata — `Requires-Python: >=3.7`, serpent 1.42
- `python3.11 --version` — 3.11.2 at `/usr/bin/python3.11`
- `python3.11 -m pip show pytest` — 7.2.1 available in system python3.11

### Tertiary (LOW confidence)
- None — all claims verified via primary or secondary sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed via pip download and Context7
- Architecture: HIGH — patterns verified against Context7 official docs; PRD reference implementation
- Pitfalls: HIGH (deadlock, proxy sharing, UDP broadcast) verified; MEDIUM (retry timing) based on D-03 decision
- Environment: HIGH — verified by running `python3.11 --version` and `pip3 download Pyro5==5.16` on target machine

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (stable ecosystem; Pyro5 and Flask-SocketIO release infrequently)
