---
phase: 01-rpc-infrastructure-callback-pipeline
plan: "02"
subsystem: infra
tags: [pyro5, rpc, gameserver, eventbroadcaster, threading, callbacks]

requires:
  - phase: 01-01
    provides: venv, config.py, directory structure, pytest stubs

provides:
  - GameServer @Pyro5.api.expose class with ping() and register_callback()
  - EventBroadcaster with thread-safe broadcast() and send_to_player()
  - Three passing real in-process Pyro5 daemon unit tests (test_ping, test_register_callback, test_broadcast_delivery)

affects: [01-03, 01-04, bridge, client]

tech-stack:
  added: []
  patterns:
    - Pyro5 in-process daemon for tests (Daemon in background thread, no Name Server needed)
    - Snapshot-outside-lock pattern in EventBroadcaster.broadcast() to prevent deadlock
    - threading.RLock for GameServer and EventBroadcaster shared state

key-files:
  created:
    - server/event_broadcaster.py
    - server/game_server.py
  modified:
    - tests/test_unit.py

key-decisions:
  - "broadcast() snapshots callbacks dict outside lock before iterating — prevents deadlock if callback proxy call is slow"
  - "Failed callback entries removed during broadcast iteration (cleanup-on-fail pattern)"
  - "GameServer bind address hardcoded to 127.0.0.1:9091 in __main__ — never 0.0.0.0"
  - "register_callback raises ValueError for empty/non-string args — propagates over RPC as Pyro5 error"

patterns-established:
  - "Pattern 1 — In-process Pyro5 test daemon: Daemon(host='127.0.0.1') + register + Thread(target=daemon.requestLoop, daemon=True)"
  - "Pattern 2 — EventBroadcaster lock discipline: acquire lock only to read/write callbacks dict, never while holding a proxy"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03, INFRA-06]

duration: ~15min
completed: 2026-05-12
---

# Plan 01-02: GameServer + EventBroadcaster Summary

**GameServer @expose with ping/register_callback and thread-safe EventBroadcaster; three in-process Pyro5 RPC tests go from skipped to green**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-05-12
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `EventBroadcaster`: callbacks dict with RLock, snapshot-outside-lock `broadcast()`, `send_to_player()`, failed-entry removal
- `GameServer`: `@Pyro5.api.expose`, `ping()` returning `"pong"`, `register_callback()` with non-empty validation, delegates to EventBroadcaster; `__main__` binds to `127.0.0.1:9091` and registers with NS
- `tests/test_unit.py`: `test_ping`, `test_register_callback`, `test_broadcast_delivery` replaced stubs with real in-process daemon tests — all three pass

## Task Commits

1. **Task 1: Implement EventBroadcaster and GameServer core** — `29cd318` (feat)
2. *(SUMMARY.md not committed in original session — recovered)*

## Files Created/Modified
- `server/event_broadcaster.py` — EventBroadcaster: callbacks dict, lock, broadcast(), send_to_player()
- `server/game_server.py` — GameServer: @expose, ping(), register_callback(), __main__ startup
- `tests/test_unit.py` — Replaced stubs for INFRA-01/02/03 with real in-process Pyro5 tests

## Decisions Made
- `broadcast()` snapshots `list(callbacks.items())` outside the lock before iterating to prevent deadlock when a slow proxy call is made while holding the lock
- Failed callback proxies removed from the dict during broadcast rather than accumulating
- `register_callback` validates both args as non-empty strings; empty args propagate as `ValueError` / `PyroError` over RPC

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
Session hit usage limit before SUMMARY.md was committed. Implementation was fully complete (3 tests passing, 1 skipped for Plan 04). SUMMARY.md written manually during resume.

## Next Phase Readiness
- GameServer and EventBroadcaster are ready; Plan 03 can add `broadcast_test()` @oneway and write `test_client.py`
- `test_per_thread_proxy` remains skipped — implemented in Plan 04

---
*Phase: 01-rpc-infrastructure-callback-pipeline*
*Completed: 2026-05-12*
