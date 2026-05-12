---
phase: 01-rpc-infrastructure-callback-pipeline
plan: "03"
subsystem: infra
tags: [pyro5, rpc, oneway, callback, test-client, smoke-test]

requires:
  - phase: 01-02
    provides: GameServer, EventBroadcaster, in-process Pyro5 test daemon pattern

provides:
  - GameServer.broadcast_test() @oneway method
  - client/test_client.py CLI smoke test (3-terminal demo artifact)

affects: [01-04, bridge, client, demo-day]

tech-stack:
  added: []
  patterns:
    - "@Pyro5.api.oneway on server broadcast methods — caller returns immediately, no deadlock"
    - "Callback receiver in TestCallback: @expose class, @oneway @callback on handler method"
    - "PYRONAME:game.server@{NS_HOST} with explicit host in URI — avoids UDP broadcast (D-01)"

key-files:
  created:
    - client/test_client.py
  modified:
    - server/game_server.py

key-decisions:
  - "broadcast_test() uses @oneway — required by D-09 to prevent deadlock when callback receivers are registered"
  - "test_client.py uses f-string PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST} — no hardcoded URI"
  - "Callback daemon binds to 127.0.0.1 — loopback only, satisfies T-01-07 mitigation"

requirements-completed: [INFRA-02, INFRA-03, INFRA-06]

duration: ~2min
completed: 2026-05-12
---

# Phase 01 Plan 03: broadcast_test() @oneway + test_client.py smoke test Summary

**broadcast_test() @oneway added to GameServer; test_client.py CLI demo script discovers GameServer via NS, registers callback, waits for push event, prints [PUSH RECEIVED]**

## Performance

- **Duration:** ~2 min
- **Completed:** 2026-05-12
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- `GameServer.broadcast_test(message)` added with `@Pyro5.api.oneway` — fires `broadcaster.broadcast("test_event", ...)` without blocking caller
- `client/test_client.py` written as standalone CLI demo script:
  - `TestCallback` class `@expose` with `on_test_event()` decorated `@oneway @callback`
  - Discovers game server via `PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}` (no hardcoded URI)
  - Starts callback daemon on loopback (127.0.0.1), registers with GameServer
  - Waits 10 seconds for pushed events; exits 1 with warning if none received
- All 3 unit tests remain green (1 skipped for Plan 04 — unchanged)

## Task Commits

1. **Task 1: Add broadcast_test() @oneway to GameServer** — `6941327` (feat)
2. **Task 2: Write client/test_client.py CLI smoke test** — `6d22f2b` (feat)

## Files Created/Modified

- `server/game_server.py` — Added `broadcast_test()` with `@Pyro5.api.oneway`
- `client/test_client.py` — Full CLI smoke test: TestCallback, daemon setup, NS lookup, register, wait, exit logic

## Decisions Made

- `broadcast_test()` must be `@oneway` (D-09): without it, calling it while any callback is registered deadlocks the server handler thread
- PYRONAME URI includes `@{config.NS_HOST}` to avoid UDP broadcast per D-01; using bare `PYRONAME:game.server` would fail on networks where UDP multicast is filtered
- Callback daemon binds to `127.0.0.1` per T-01-07 — callback receiver must not be reachable outside loopback in Phase 1

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — test_client.py is a complete runnable demo; broadcast_test() is fully wired to EventBroadcaster.

## Threat Flags

None — all threat model mitigations applied: T-01-07 (callback daemon binds to 127.0.0.1).

## Self-Check: PASSED

- `server/game_server.py` exists and contains `@Pyro5.api.oneway` (count: 1)
- `client/test_client.py` exists, parses without errors, contains PYRONAME lookup with @{config.NS_HOST}
- Commits `6941327` and `6d22f2b` exist
- `venv/bin/pytest tests/ -x -q` — 3 passed, 1 skipped, exit 0

---
*Phase: 01-rpc-infrastructure-callback-pipeline*
*Completed: 2026-05-12*
