---
phase: 01-rpc-infrastructure-callback-pipeline
reviewed: 2026-05-12T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - bridge/bridge.py
  - bridge/__init__.py
  - client/test_client.py
  - client/__init__.py
  - config.py
  - pytest.ini
  - requirements.txt
  - server/__init__.py
  - server/event_broadcaster.py
  - server/game_server.py
  - tests/__init__.py
  - tests/test_unit.py
  - .gitignore
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed the full RPC infrastructure layer: Pyro5 game server, event broadcaster, Flask-SocketIO bridge, CLI test client, and unit tests. The overall architecture is sound and follows the documented design decisions from CLAUDE.md (threading mode, per-thread proxies, loopback binding). However, two critical issues require fixing before this code ships: a hardcoded Flask secret key that will be reused across deployments and a race condition in `test_broadcast_delivery` that makes the test inherently flaky. Five warnings cover logic correctness and robustness gaps, and three info items cover code quality.

---

## Critical Issues

### CR-01: Hardcoded Flask SECRET_KEY

**File:** `bridge/bridge.py:32`
**Issue:** `app.config["SECRET_KEY"] = "dev-secret"` is a static string committed to source control. Flask uses SECRET_KEY to sign session cookies and CSRF tokens. Even for an academic project, if this bridge is ever exposed beyond 127.0.0.1 (which it currently is — port 5000 is accessible to the host via Werkzeug), any attacker who reads the repo can forge signed cookies. The value `"dev-secret"` is maximally guessable.
**Fix:** Read the key from an environment variable with no default (fail-closed) or generate a random fallback only for development:
```python
import secrets
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
```
If a static dev default is acceptable, at minimum document the risk and gate it on `DEBUG` mode:
```python
if os.environ.get("FLASK_ENV") == "production":
    app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]  # raises KeyError if missing
else:
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-not-for-prod")
```

---

### CR-02: Race condition in `test_broadcast_delivery` — `time.sleep(0.2)` is not a reliable synchronization primitive

**File:** `tests/test_unit.py:115`
**Issue:** The test calls `server.broadcaster.broadcast(...)` which creates a Pyro5 proxy, dials the loopback, and calls `on_test_event` on the receiver daemon — all synchronously in the calling thread. `broadcast()` does **not** use a background thread; it blocks until each `method(data)` call returns. The `time.sleep(0.2)` therefore appears to be based on a false assumption that the call is asynchronous.

However, the callback receiver's `on_test_event` is **not** decorated `@oneway` in the test (unlike `TestCallback` in `client/test_client.py`). Without `@oneway`, the call IS synchronous from the broadcaster's perspective, meaning `receiver.received` should already be populated when `broadcast()` returns. The `sleep` adds 200 ms of unnecessary wait, and the test would also spuriously pass even if delivery failed silently (the assert fires 200 ms later regardless of whether the payload arrived).

More critically: if the test environment is slow and Pyro5 I/O does happen to be deferred (e.g., the daemon requestLoop hasn't called `on_test_event` yet), 0.2 s may not be enough, making the test flaky on loaded CI. Use an event to synchronize properly:
```python
received_event = threading.Event()

@Pyro5.api.expose
class TestCallbackReceiver:
    def __init__(self):
        self.received = []

    def on_test_event(self, data):
        self.received.append(data)
        received_event.set()

# After broadcast:
assert received_event.wait(timeout=5), "on_test_event not called within 5s"
```

---

## Warnings

### WR-01: `connect_to_game_server` silently succeeds even when `register_callback` fails

**File:** `bridge/bridge.py:127`
**Issue:** The function calls `proxy.register_callback("bridge", cb_uri)` but never inspects the return value. `register_callback` returns `True` on success. If the call raises an exception it is caught and retried — but if it returns a falsy value or the implementation changes to signal failure via return value, the bridge will believe it is registered when it is not, silently losing all callbacks. The retry loop exits on the first non-raising attempt, even if registration was logically incomplete.
**Fix:** Assert or check the return value:
```python
ok = proxy.register_callback("bridge", cb_uri)
if not ok:
    raise RuntimeError("register_callback returned falsy — treating as failure")
```

---

### WR-02: `EventBroadcaster.broadcast` removes failed callbacks after transient errors

**File:** `server/event_broadcaster.py:59-67`
**Issue:** Any exception during a callback call — including transient ones (momentary network hiccup, Pyro5 timeout, serialization error) — permanently removes the player from `self.callbacks`. For a game server this means a player who experiences a brief disconnection is silently deregistered and receives no further events. There is no reconnection window or backoff.

This is a logic correctness issue because the game requires real-time delivery to 2–4 players; silent permanent deregistration on the first error breaks game continuity without any feedback to the game loop.
**Fix:** At minimum, log a warning and distinguish between `ConnectionClosedError` (permanent) and transient errors. For now, use a failed-count threshold or always log that a player was dropped:
```python
except Exception as e:
    print(f"[EventBroadcaster] Callback failed for {player_id}: {e}", flush=True)
    # Only remove on connection-level errors, not all exceptions
    if isinstance(e, (Pyro5.errors.ConnectionClosedError, Pyro5.errors.CommunicationError)):
        failed.append(player_id)
    # else: leave registered; next broadcast will retry
```

---

### WR-03: `get_game_server_proxy` reuses a proxy indefinitely without handling broken connections

**File:** `bridge/bridge.py:97-101`
**Issue:** The per-thread proxy stored in `_thread_local.proxy` is created once and cached forever. If the GameServer restarts or the Pyro5 connection is broken, all subsequent calls from that thread will raise `CommunicationError` and the proxy is never replaced. Flask-SocketIO handler threads are long-lived (thread pool), so a broken proxy permanently disables that thread's ability to reach the server.
**Fix:** Catch `Pyro5.errors.CommunicationError` (or any `PyroError`) in the handler and clear the cached proxy to force reconnection:
```python
def get_game_server_proxy() -> Pyro5.api.Proxy:
    if not hasattr(_thread_local, "proxy"):
        _thread_local.proxy = Pyro5.api.Proxy(
            f"PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}"
        )
    return _thread_local.proxy

# In handlers:
try:
    proxy = get_game_server_proxy()
    result = proxy.ping()
except Pyro5.errors.PyroError:
    _thread_local.proxy = None  # force re-create on next call
    raise
```

---

### WR-04: `GameServer.__main__` continues silently when NS registration fails

**File:** `server/game_server.py:82-85`
**Issue:** If `ns.register(...)` fails, the server prints a warning but continues running. Any bridge or client using `PYRONAME:game.server@...` lookup will get a `NamingError` and fail to connect — but the server appears healthy from its own console. This is a correctness issue in the startup contract: the server is not reachable via the expected discovery mechanism.

For an academic demo where NS failure is unrecoverable (there is no alternative discovery path), the correct behavior is to exit with an error:
```python
try:
    ns = Pyro5.api.locate_ns(host=config.NS_HOST)
    ns.register(config.GAME_SERVER_NAME, uri)
    print(f"GameServer ready at {uri}")
except Exception as e:
    print(f"FATAL: could not register with Name Server: {e}", file=sys.stderr)
    daemon.shutdown()
    sys.exit(1)
```

---

### WR-05: `requirements.txt` pins critical packages inconsistently — `Flask` and `simple-websocket` are unpinned

**File:** `requirements.txt:2,4`
**Issue:** `Pyro5==5.16` and `flask-socketio==5.6.1` are pinned, but `Flask` and `simple-websocket` have no version constraint. Flask 3.x introduced breaking API changes from 2.x. `simple-websocket` is a hard dependency of Flask-SocketIO's threading mode; an incompatible version silently breaks the WebSocket transport. CLAUDE.md explicitly specifies `Flask 3.1.x`.
**Fix:**
```
Flask==3.1.0
simple-websocket>=0.9.0
```

---

## Info

### IN-01: `cors_allowed_origins="*"` in SocketIO constructor

**File:** `bridge/bridge.py:33`
**Issue:** CORS is open to all origins. Since the bridge binds to `127.0.0.1`, the practical attack surface is limited to the local machine. However, if the bind address ever changes to `0.0.0.0`, this setting enables cross-origin WebSocket connections from any website. Worth tightening to an explicit origin even for dev.
**Fix:** Set to `"http://127.0.0.1:5000"` or read from config to make the restriction explicit and auditable.

---

### IN-02: `test_register_callback` verifies internal state by accessing `server.broadcaster.callbacks` directly

**File:** `tests/test_unit.py:74-75`
**Issue:** The test acquires `server.broadcaster.lock` and reads `server.broadcaster.callbacks` directly, coupling the test to the internal implementation of `EventBroadcaster`. If `callbacks` is renamed or the storage mechanism changes, the test breaks even if the public contract still holds. The overwrite behavior can be verified via an observable effect (attempting to call the callback) rather than inspecting private state.
**Fix:** Verify via behavior, e.g., by registering a real callback receiver and confirming only the second URI receives events. If direct inspection is unavoidable, expose a `get_registered_players()` method.

---

### IN-03: `pytest.ini` missing `addopts` for verbosity and no timeout configured

**File:** `pytest.ini:1-6`
**Issue:** The test suite starts real Pyro5 daemons in background threads. If a daemon hangs (e.g., port conflict, requestLoop bug), pytest will block indefinitely. There is no per-test timeout configured. Additionally, there is no `-v` or `--tb=short` in `addopts` to make CI output readable.
**Fix:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
# Install pytest-timeout and add:
# timeout = 30
```

---

_Reviewed: 2026-05-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
