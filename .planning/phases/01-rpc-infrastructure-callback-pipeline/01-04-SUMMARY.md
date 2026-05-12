---
phase: 01-rpc-infrastructure-callback-pipeline
plan: "04"
subsystem: infra
tags: [flask-socketio, bridge, threading, pyro5, callbacks, per-thread-proxy]

# Dependency graph
requires:
  - phase: 01-03
    provides: GameServer with broadcast_test() @oneway, register_callback(), test_client.py smoke artifact

provides:
  - bridge/bridge.py with Flask-SocketIO app (async_mode='threading'), BridgeCallbackReceiver (@expose/@callback/@oneway), per-thread Pyro5 proxy via threading.local(), and startup retry loop (0.5s / 10s)
  - test_per_thread_proxy verifying threading.local() isolation (two threads return different proxy id() values)
  - Full end-to-end callback pipeline proven: GameServer @oneway broadcast_test() → BridgeCallbackReceiver.on_test_event() → socketio.emit('game_event', data)
  - Phase 1 success criteria 1–5 all verified via 3-terminal smoke test

affects:
  - Phase 2 (Player Session + Lobby) — bridge is the Socket.IO entry point for all browser clients; BridgeCallbackReceiver pattern is the template for all future push callbacks
  - All future phases relying on GameServer → Browser event delivery

# Tech tracking
tech-stack:
  added:
    - Flask-SocketIO 5.6.1 (async_mode='threading')
    - Flask 3.x (web framework underlying bridge)
    - simple-websocket (WebSocket transport for threading mode)
  patterns:
    - BridgeCallbackReceiver: @Pyro5.api.expose class with @oneway @callback on_test_event() calling socketio.emit() cross-thread
    - Per-thread Pyro5 proxy: threading.local() at module level; get_game_server_proxy() creates one Proxy per thread, never shared
    - Startup retry loop: 20 attempts × 0.5s = 10s window; locate_ns(host=config.NS_HOST) + ping() + register_callback()
    - Pyro5 callback daemon in background thread (daemon=True) so Flask-SocketIO request loop is not blocked
    - sys.path.insert(0, project_root) in game_server.py, bridge/bridge.py, client/test_client.py for portable imports

key-files:
  created:
    - bridge/bridge.py — Flask-SocketIO bridge: SocketIO(async_mode='threading'), BridgeCallbackReceiver, get_game_server_proxy(), connect_to_game_server(), handle_ping()
  modified:
    - tests/test_unit.py — test_per_thread_proxy stub replaced with real threading.local() isolation test; 4 passed 0 skipped
    - server/game_server.py — sys.path.insert(0, project_root) added for portable `import config`
    - client/test_client.py — sys.path.insert(0, project_root) added; on_test_event try/except with flush=True

key-decisions:
  - "BridgeCallbackReceiver stores URIs (not Proxy objects); creates fresh Proxy per broadcast() call — Pyro5 proxies are not thread-safe across threads (C2 pitfall)"
  - "allow_unsafe_werkzeug=True added to socketio.run() — required for Flask dev server under newer Werkzeug"
  - "All binds (Pyro5 daemon + Flask/SocketIO) to 127.0.0.1 loopback — never 0.0.0.0 in Phase 1 (T-01-09 mitigation)"

patterns-established:
  - "Pattern: Per-thread Pyro5 proxy — threading.local() at module level; get_game_server_proxy() checks and populates _thread_local.proxy; never share a proxy across threads"
  - "Pattern: BridgeCallbackReceiver — @Pyro5.api.expose class; on_test_event() decorated @oneway then @callback; calls socketio.emit() directly (safe in threading mode)"
  - "Pattern: Startup retry — locate_ns(host=...) + Proxy lookup + ping() in a loop; max 20 attempts at 0.5s intervals; sys.exit(1) on exhaustion"

requirements-completed: [INFRA-04, INFRA-05]

# Metrics
duration: manual execution (multi-session with human checkpoint)
completed: 2026-05-12
---

# Phase 01 Plan 04: Flask-SocketIO Bridge Summary

**Flask-SocketIO bridge with BridgeCallbackReceiver and per-thread Pyro5 proxy proves end-to-end callback pipeline: GameServer @oneway push → BridgeCallbackReceiver → socketio.emit() to browser clients**

## Performance

- **Duration:** Multi-session (human checkpoint at Task 3)
- **Started:** 2026-05-12
- **Completed:** 2026-05-12
- **Tasks:** 3 (Task 1: bridge.py, Task 2: test_per_thread_proxy, Task 3: smoke test checkpoint)
- **Files modified:** 4

## Accomplishments

- bridge/bridge.py fully implemented with Flask-SocketIO (async_mode='threading'), BridgeCallbackReceiver, per-thread proxy via threading.local(), and 10-second startup retry loop
- test_per_thread_proxy implemented and passing — verifies threading.local() isolation: two threads get different Proxy id() values
- Full 3-terminal smoke test approved: NS + GameServer + Bridge running; broadcast_test() call delivers event to bridge log as "[BRIDGE] game_event emitted: {...}"
- Full pytest suite passes: 4 passed, 0 skipped, 0 failed — all Phase 1 unit test requirements met
- Phase 1 success criteria 1–5 all verified end-to-end

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement bridge/bridge.py** - `33f5d25` (feat)
2. **Task 2: test_per_thread_proxy + full suite** - `9fb4a7a` (test)
3. **Fix: smoke test issues** - `6c8770b` (fix — post-checkpoint corrections applied by orchestrator)

## Files Created/Modified

- `bridge/bridge.py` — Flask-SocketIO bridge application; BridgeCallbackReceiver with on_test_event() → socketio.emit(); get_game_server_proxy() with threading.local(); connect_to_game_server() retry loop; handle_ping() SocketIO event handler
- `tests/test_unit.py` — test_per_thread_proxy stub replaced with real threading.local() isolation test using two threads and a Barrier; all 4 tests pass
- `server/game_server.py` — sys.path.insert(0, project_root) added for portable `import config` without PYTHONPATH
- `client/test_client.py` — sys.path.insert(0, project_root) added; on_test_event wrapped in try/except with flush=True

## Decisions Made

- **BridgeCallbackReceiver stores URIs, not Proxy objects** — Pyro5 proxies are not thread-safe when shared across threads (C2 pitfall). Receiver stores the string URI and creates a fresh Proxy inside each broadcast() call.
- **allow_unsafe_werkzeug=True** — required for Flask dev server under newer Werkzeug versions; added to socketio.run() so the bridge starts cleanly.
- **All network binds to 127.0.0.1** — Pyro5 callback daemon and Flask/SocketIO both bind to loopback only (T-01-09 mitigated); never 0.0.0.0 in Phase 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] EventBroadcaster stores URIs instead of Proxy objects**
- **Found during:** Task 1 post-smoke-test (fix commit 6c8770b)
- **Issue:** Original implementation stored Proxy objects in EventBroadcaster; Pyro5 proxies are not thread-safe when called from multiple threads — violates C2 pitfall documented in research
- **Fix:** Changed EventBroadcaster to store callback URIs (strings); creates fresh Proxy(uri) inside each broadcast() call
- **Files modified:** server/game_server.py, bridge/bridge.py
- **Verification:** Smoke test passes; bridge log shows correct delivery
- **Committed in:** 6c8770b

**2. [Rule 3 - Blocking] sys.path.insert added to entry point scripts**
- **Found during:** Task 1 smoke test
- **Issue:** `import config` failed in game_server.py, bridge/bridge.py, and test_client.py when run without PYTHONPATH set; project root not on sys.path by default
- **Fix:** Added `sys.path.insert(0, project_root)` at top of each affected file using `os.path.dirname(os.path.abspath(__file__))`-based root resolution
- **Files modified:** server/game_server.py, bridge/bridge.py, client/test_client.py
- **Verification:** All three scripts import config cleanly; pytest suite passes
- **Committed in:** 6c8770b

**3. [Rule 3 - Blocking] allow_unsafe_werkzeug=True added to socketio.run()**
- **Found during:** Task 1 smoke test (bridge startup)
- **Issue:** Newer Werkzeug refuses to run as development server without explicit opt-in; bridge crashed on startup with RuntimeError
- **Fix:** Added `allow_unsafe_werkzeug=True` to `socketio.run(app, ...)` call
- **Files modified:** bridge/bridge.py
- **Verification:** Bridge starts cleanly and prints Flask-SocketIO startup log
- **Committed in:** 6c8770b

---

**Total deviations:** 3 auto-fixed (1 Rule 1 bug, 2 Rule 3 blocking)
**Impact on plan:** All fixes necessary for correct thread-safe operation and working startup. No scope creep.

## Issues Encountered

- Pyro5 proxy thread-safety: the original EventBroadcaster design passed Proxy objects at callback registration time. Post-smoke-test investigation revealed this violates the C2 pitfall (shared proxy across threads). Fixed by switching to URI storage + fresh-proxy-per-call pattern.
- Werkzeug dev-server guard: added `allow_unsafe_werkzeug=True` — standard workaround for Flask-SocketIO in development; documented in Flask-SocketIO deployment guide.

## User Setup Required

None - no external service configuration required. All processes run locally on 127.0.0.1.

## Next Phase Readiness

- Full Pyro5 RPC infrastructure is proven end-to-end: NS + GameServer + Bridge + socketio.emit() pipeline all operational
- Phase 2 (Player Session + Lobby) can begin: bridge.py is the correct extension point for new SocketIO event handlers; BridgeCallbackReceiver is the template for all future push callbacks
- No blockers from Phase 1

---
*Phase: 01-rpc-infrastructure-callback-pipeline*
*Completed: 2026-05-12*
