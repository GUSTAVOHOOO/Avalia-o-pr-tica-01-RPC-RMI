---
phase: 01-rpc-infrastructure-callback-pipeline
plan: "01"
subsystem: infra
tags: [pyro5, flask-socketio, pytest, python3.11, venv]

# Dependency graph
requires: []
provides:
  - Python 3.11 venv with Pyro5==5.16, Flask-SocketIO==5.6.1, simple-websocket, pytest installed
  - requirements.txt with pinned dependency manifest
  - config.py at project root with NS_HOST, GAME_SERVER_PORT=9091, BRIDGE_PORT=5000, GAME_SERVER_NAME
  - server/, bridge/, client/, tests/ Python packages (each with __init__.py)
  - pytest.ini with testpaths=tests
  - tests/test_unit.py with 4 stub tests (test_ping, test_register_callback, test_broadcast_delivery, test_per_thread_proxy)
affects: [01-02, 01-03, 01-04]

# Tech tracking
tech-stack:
  added: [Pyro5==5.16, Flask==3.1.3, flask-socketio==5.6.1, simple-websocket==1.1.0, pytest==9.0.3, serpent==1.42]
  patterns:
    - "config.py at root imported by all processes as `import config`"
    - "venv from python3.11 — never use bare python3 (resolves to 3.8.20 via mise)"
    - "pytest stubs use pytest.skip('not implemented yet') until plan implements them"

key-files:
  created:
    - requirements.txt
    - .gitignore
    - config.py
    - pytest.ini
    - server/__init__.py
    - bridge/__init__.py
    - client/__init__.py
    - tests/__init__.py
    - tests/test_unit.py
  modified: []

key-decisions:
  - "Used python3.11 -m venv (not python3) — avoids 3.8.20 mise default which may have edge-case issues with Pyro5 docs 'supported on 3.9+'"
  - "NS_HOST reads from PYRO_NS_HOST env var with default 127.0.0.1 — satisfies D-02, avoids UDP broadcast issue on demo day"
  - "4 test stubs all call pytest.skip('not implemented yet') — allows pytest suite to collect and run cleanly before implementation"

patterns-established:
  - "Pattern: all processes import config as `import config` (not relative import) — config.py lives at project root"
  - "Pattern: venv/bin/python and venv/bin/pytest for all commands — never bare python3"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06]

# Metrics
duration: 1min
completed: 2026-05-12
---

# Phase 01 Plan 01: Bootstrap — venv, dependencies, directory structure, config, and pytest stubs

**Python 3.11 venv with Pyro5==5.16 and Flask-SocketIO==5.6.1 installed, project directory layout created, config.py with shared constants, and 4 pytest stubs collecting clean**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-12T14:30:25Z
- **Completed:** 2026-05-12T14:32:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Python 3.11.2 venv created and all 5 pinned packages (Pyro5==5.16, Flask, flask-socketio==5.6.1, simple-websocket, pytest) install and import without error
- Project directory structure (server/, bridge/, client/, tests/) established as Python packages
- config.py exports NS_HOST (env-configurable), GAME_SERVER_PORT=9091, BRIDGE_PORT=5000, GAME_SERVER_NAME="game.server" — single source of truth for all processes
- pytest collects 4 stub tests (test_ping, test_register_callback, test_broadcast_delivery, test_per_thread_proxy) and exits 0 with 4 skipped

## Task Commits

Each task was committed atomically:

1. **Task 1: Create venv, install dependencies, write requirements.txt** - `26e9805` (chore)
2. **Task 2: Create directory structure, config.py, and pytest.ini** - `6767b66` (feat)

**Plan metadata:** (TBD — added in final commit)

## Files Created/Modified

- `requirements.txt` — Pinned dependency manifest (Pyro5==5.16 first line)
- `.gitignore` — Ignores venv/, __pycache__/, .pytest_cache/
- `config.py` — Shared constants: NS_HOST (from PYRO_NS_HOST env, default 127.0.0.1), GAME_SERVER_PORT=9091, BRIDGE_PORT=5000, GAME_SERVER_NAME="game.server"
- `pytest.ini` — testpaths=tests, python_files=test_*.py, python_functions=test_*
- `server/__init__.py` — Empty package init
- `bridge/__init__.py` — Empty package init
- `client/__init__.py` — Empty package init
- `tests/__init__.py` — Empty package init
- `tests/test_unit.py` — 4 stub tests with pytest.skip("not implemented yet") for Plans 02/03

## Decisions Made

- Used `python3.11 -m venv venv` explicitly (not `python3`) — avoids Python 3.8.20 that mise installs as default on this machine; Pyro5 5.16 docs say "supported on 3.9+", so 3.11 is safer
- NS_HOST reads from `PYRO_NS_HOST` environment variable with default `127.0.0.1` — satisfies D-02 from CONTEXT.md; avoids UDP broadcast issue on demo day (D-01)
- Test stubs use `pytest.skip("not implemented yet")` rather than `raise NotImplementedError` — pytest.skip is cleaner (marks as skipped rather than errored) and allows the suite to run without confusion

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- venv, packages, directory structure, and config.py are all ready for Plans 02 and 03
- Plans 02/03 can immediately import config and use venv/bin/python
- Test stubs in tests/test_unit.py are ready to be filled with real in-process Pyro5 daemon tests
- No blockers

---
*Phase: 01-rpc-infrastructure-callback-pipeline*
*Completed: 2026-05-12*
