---
phase: 01-rpc-infrastructure-callback-pipeline
verified: 2026-05-12T00:00:00Z
status: human_needed
score: 13/13 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run 3-terminal smoke test: Terminal 1 — venv/bin/pyro5-ns --host 127.0.0.1; Terminal 2 — venv/bin/python server/game_server.py; Terminal 3 — venv/bin/python bridge/bridge.py"
    expected: "Bridge terminal prints '[BRIDGE] Callback receiver URI: PYRO:...', '[BRIDGE] Connected to GameServer and registered callback.', and Flask-SocketIO log shows 'async_mode=threading'"
    why_human: "Bridge startup requires NS + GameServer both running; cannot verify end-to-end socketio.emit() delivery without a live multi-process setup"
  - test: "While NS + GameServer + Bridge are running, execute: venv/bin/python -c \"import Pyro5.api, config; with Pyro5.api.Proxy(f'PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}') as s: s.broadcast_test('hello')\"; observe Bridge terminal"
    expected: "Bridge terminal prints '[BRIDGE] game_event emitted: {\"message\": \"hello\", \"source\": \"broadcast_test\"}'"
    why_human: "Requires live multi-process stack running to observe cross-process callback delivery"
  - test: "With NS + GameServer running, execute: venv/bin/python client/test_client.py; then in another terminal call broadcast_test('hi') within 10 seconds"
    expected: "test_client.py terminal prints '[PUSH RECEIVED] {...}' and exits with 'Done. Received 1 push event(s).'"
    why_human: "CLI smoke test requires interactive multi-terminal coordination to trigger the push event within the 10-second window"
---

# Phase 01: RPC Infrastructure + Callback Pipeline Verification Report

**Phase Goal:** RPC Infrastructure + Callback Pipeline — prove Pyro5 RPC works end-to-end: GameServer reachable via NS, callbacks delivered push from server to client, Flask-SocketIO bridge forwards events to browser, full pipeline verified.
**Verified:** 2026-05-12
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | GameServer.ping() returns 'pong' over real in-process Pyro5 RPC | VERIFIED | test_ping PASSED (pytest run, 4 passed 0 skipped) |
| 2  | register_callback stores URI; second call overwrites; empty arg raises error | VERIFIED | test_register_callback PASSED; code validates non-empty strings, raises ValueError propagated as PyroError |
| 3  | EventBroadcaster.broadcast() iterates all registered callbacks and calls on_event_type(data) | VERIFIED | test_broadcast_delivery PASSED; receiver.received == [{"msg": "hello"}] confirmed |
| 4  | EventBroadcaster stores URIs not Proxy objects; creates fresh Proxy per broadcast call | VERIFIED | event_broadcaster.py line 21: callbacks dict is player_id -> uri str; broadcast() calls Pyro5.api.Proxy(uri) inside iteration |
| 5  | GameServer.broadcast_test() is decorated with @Pyro5.api.oneway | VERIFIED | game_server.py line 58: @Pyro5.api.oneway on broadcast_test(); grep confirmed count=1 |
| 6  | GameServer accessible via Name Server lookup under 'game.server' | VERIFIED | game_server.py __main__ calls locate_ns(host=config.NS_HOST) and ns.register(config.GAME_SERVER_NAME, uri); GAME_SERVER_NAME="game.server" in config.py |
| 7  | Bridge starts with SocketIO(app, async_mode='threading') | VERIFIED | bridge.py line 33: socketio = SocketIO(app, async_mode="threading", ...) literal string confirmed |
| 8  | BridgeCallbackReceiver is @Pyro5.api.expose with on_test_event() calling socketio.emit() | VERIFIED | bridge.py lines 42-61: class decorated @expose; on_test_event() calls socketio.emit("game_event", data) |
| 9  | Bridge's Pyro5 callback daemon runs in background thread (daemon=True) | VERIFIED | bridge.py lines 75-79: threading.Thread(target=daemon.requestLoop, daemon=True) |
| 10 | Per-thread proxy via threading.local() — two threads get different id() values | VERIFIED | test_per_thread_proxy PASSED; bridge.py lines 88-101: _thread_local = threading.local(); get_game_server_proxy() pattern confirmed |
| 11 | Bridge startup retries locate_ns() + game.server lookup up to 10 seconds | VERIFIED | bridge.py lines 108-139: max_attempts=20, sleep_interval=0.5; locate_ns(host=config.NS_HOST) in retry loop |
| 12 | No hardcoded IP:port for game.server in test_client.py or bridge.py | VERIFIED | test_client.py uses f"PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}"; bridge.py same pattern; grep found no bare PYRONAME:game.server without NS_HOST |
| 13 | All 4 unit tests pass: test_ping, test_register_callback, test_broadcast_delivery, test_per_thread_proxy | VERIFIED | pytest output: 4 passed, 0 skipped, 0 failed in 1.01s on Python 3.11.2 |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config.py` | Shared constants: NS_HOST, GAME_SERVER_PORT=9091, BRIDGE_PORT=5000, GAME_SERVER_NAME | VERIFIED | All 4 constants present; NS_HOST reads from PYRO_NS_HOST env var |
| `requirements.txt` | Pinned dependency manifest with Pyro5==5.16 | VERIFIED | Line 1: Pyro5==5.16; also Flask, flask-socketio==5.6.1, simple-websocket, pytest |
| `pytest.ini` | pytest configuration with testpaths=tests | VERIFIED | testpaths = tests, python_files = test_*.py, python_functions = test_* |
| `server/game_server.py` | GameServer @expose with ping(), register_callback(), broadcast_test() @oneway | VERIFIED | @Pyro5.api.expose on class; all 3 methods present; __main__ binds 127.0.0.1:9091 |
| `server/event_broadcaster.py` | EventBroadcaster with lock-protected callbacks, broadcast(), send_to_player() | VERIFIED | threading.Lock; URI storage pattern; snapshot-outside-lock; failed entry removal |
| `bridge/bridge.py` | Flask-SocketIO async_mode='threading', BridgeCallbackReceiver, per-thread proxy, retry startup | VERIFIED | All components present; syntax OK; 0 occurrences of 0.0.0.0 |
| `client/test_client.py` | CLI smoke test: NS lookup, callback daemon, register, wait, exit logic | VERIFIED | TestCallback @expose; PYRONAME lookup with @{config.NS_HOST}; daemon on 127.0.0.1 |
| `tests/test_unit.py` | 4 real in-process Pyro5 daemon tests (no mocks) | VERIFIED | All 4 tests use actual Pyro5.api.Daemon + requestLoop pattern; no pytest.skip remaining |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| config.py | server/game_server.py, bridge/bridge.py, client/test_client.py | sys.path.insert + import config | WIRED | All three entry points use sys.path.insert(0, project_root) then import config |
| server/game_server.py | server/event_broadcaster.py | self.broadcaster = EventBroadcaster() | WIRED | game_server.py imports EventBroadcaster; __init__ assigns self.broadcaster |
| tests/test_unit.py | server/game_server.py | Pyro5.api.Proxy(uri).ping() | WIRED | test_ping, test_register_callback, test_broadcast_delivery all use real daemon + Proxy |
| bridge/bridge.py BridgeCallbackReceiver.on_test_event() | socketio.emit('game_event', data) | cross-thread emit in threading mode | WIRED | bridge.py line 56: socketio.emit("game_event", data) inside on_test_event |
| bridge/bridge.py get_game_server_proxy() | threading.local() | _thread_local.proxy | WIRED | _thread_local definition + usage confirmed; 3 occurrences of _thread_local |
| bridge/bridge.py startup | GameServer via Name Server | retry loop with locate_ns(host=config.NS_HOST) | WIRED | connect_to_game_server() calls locate_ns(host=config.NS_HOST) in retry loop |
| client/test_client.py | Pyro5 Name Server | locate_ns implicit in PYRONAME proxy | WIRED | f"PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}" in Proxy constructor |
| GameServer.broadcast_test() | EventBroadcaster.broadcast() | self.broadcaster.broadcast("test_event", ...) | WIRED | game_server.py line 69 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| bridge/bridge.py on_test_event | data (dict) | GameServer.broadcast_test() → EventBroadcaster.broadcast() → Proxy.on_test_event() | Yes — Pyro5 RPC call chain from live game_server | FLOWING |
| tests/test_unit.py test_broadcast_delivery | receiver.received | server.broadcaster.broadcast("test_event", {"msg": "hello"}) | Yes — real in-process Pyro5 daemon delivery | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| GameServer.ping() returns 'pong' over Pyro5 RPC | venv/bin/pytest tests/test_unit.py::test_ping -x -v | PASSED | PASS |
| register_callback stores URI and overwrites | venv/bin/pytest tests/test_unit.py::test_register_callback -x -v | PASSED | PASS |
| broadcast() delivers to callback receiver | venv/bin/pytest tests/test_unit.py::test_broadcast_delivery -x -v | PASSED | PASS |
| threading.local() gives different proxy per thread | venv/bin/pytest tests/test_unit.py::test_per_thread_proxy -x -v | PASSED | PASS |
| bridge.py parses without syntax error | venv/bin/python -c "import ast; ast.parse(open('bridge/bridge.py').read())" | OK | PASS |
| Full suite: 4 passed 0 skipped | venv/bin/pytest tests/ -x -v | 4 passed in 1.01s | PASS |

### Probe Execution

No probe scripts found (`scripts/*/tests/probe-*.sh` absent). Step 7c: SKIPPED — no conventional probe scripts defined for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | 01-01, 01-02 | Pyro5 daemon with GameServer @expose, accessible via NS | SATISFIED | GameServer @expose confirmed; __main__ registers with NS; test_ping passes |
| INFRA-02 | 01-01, 01-02 | register_callback(player_id, callback_uri) for push events | SATISFIED | register_callback in GameServer and EventBroadcaster; test_register_callback passes |
| INFRA-03 | 01-01, 01-02, 01-03 | EventBroadcaster sends events via @oneway broadcast methods | SATISFIED | broadcast() confirmed; broadcast_test() @oneway; test_broadcast_delivery passes |
| INFRA-04 | 01-01, 01-04 | Bridge Flask-SocketIO async_mode='threading', WebSocket→Pyro5→Socket.IO | SATISFIED | bridge.py SocketIO(app, async_mode="threading"); BridgeCallbackReceiver.on_test_event() → socketio.emit() |
| INFRA-05 | 01-01, 01-04 | Bridge uses per-thread Pyro5 proxy (no shared proxy) | SATISFIED | _thread_local + get_game_server_proxy() confirmed; test_per_thread_proxy passes |
| INFRA-06 | 01-01, 01-02, 01-03 | Pyro5 NS available for service discovery; no hardcoded client URIs | SATISFIED | All clients use PYRONAME:{name}@{NS_HOST}; no hardcoded game.server IP:port |

All 6 phase requirement IDs accounted for. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX markers found | — | — |
| — | — | No stub implementations (return null / return [] / empty handlers) found | — | — |
| — | — | No 0.0.0.0 bind addresses in any file | — | — |

No blockers detected. No warning-level anti-patterns found.

### Human Verification Required

#### 1. Bridge Startup — NS + GameServer Connected

**Test:** Run 3 terminals simultaneously: (1) `venv/bin/pyro5-ns --host 127.0.0.1`, (2) `venv/bin/python server/game_server.py`, (3) `venv/bin/python bridge/bridge.py`

**Expected:** Bridge terminal prints:
- `[BRIDGE] Callback receiver URI: PYRO:obj-...`
- `[BRIDGE] Connected to GameServer and registered callback.`
- Flask-SocketIO startup log includes `async_mode=threading`

**Why human:** Bridge startup requires all three processes live simultaneously. The 10-second retry loop and cross-process callback registration cannot be verified with grep/AST checks alone.

#### 2. End-to-End Broadcast Push — GameServer to Bridge socketio.emit()

**Test:** While the 3-terminal stack is running, execute in a 4th terminal:
```
venv/bin/python -c "
import Pyro5.api, config
with Pyro5.api.Proxy(f'PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}') as s:
    s.broadcast_test('hello from test')
print('broadcast_test called')
"
```

**Expected:** Bridge terminal prints `[BRIDGE] game_event emitted: {'message': 'hello from test', 'source': 'broadcast_test'}`

**Why human:** Requires live multi-process Pyro5 stack. The @oneway delivery path from GameServer through EventBroadcaster to BridgeCallbackReceiver.on_test_event() → socketio.emit() cannot be traced without running processes.

#### 3. CLI Smoke Test — test_client.py Receives Push

**Test:** With NS + GameServer running, run `venv/bin/python client/test_client.py` and within 10 seconds call `broadcast_test('hi')` from another terminal.

**Expected:** test_client.py prints `[PUSH RECEIVED] {'message': 'hi', 'source': 'broadcast_test'}` and exits with `Done. Received 1 push event(s).`

**Why human:** Requires coordinated multi-terminal execution within a time window; cannot be automated without a test harness that starts all processes.

### Gaps Summary

No gaps found. All 13 observable truths are VERIFIED in the codebase. All 6 requirement IDs (INFRA-01 through INFRA-06) are SATISFIED. All 8 required artifacts exist, are substantive, and are correctly wired. No debt markers, no stubs, no orphaned code.

The 3 human verification items are the multi-process integration checks that require a live system. The automated unit test suite (4 tests, 4 passed, 0 skipped) covers all in-process behaviors. The multi-terminal smoke test was approved by the developer during Plan 04 execution (checkpoint task documented in 01-04-SUMMARY.md), but re-verification of the live pipeline is requested as it cannot be confirmed programmatically.

---

_Verified: 2026-05-12_
_Verifier: Claude (gsd-verifier)_
