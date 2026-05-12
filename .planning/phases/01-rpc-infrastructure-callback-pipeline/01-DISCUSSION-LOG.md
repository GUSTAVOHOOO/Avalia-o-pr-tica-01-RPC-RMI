# Phase 1: RPC Infrastructure + Callback Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-12
**Phase:** 01-rpc-infrastructure-callback-pipeline
**Areas discussed:** Name Server discovery, Bridge startup coupling, Smoke test format, Project file layout

---

## Name Server Discovery

| Option | Description | Selected |
|--------|-------------|----------|
| --host 127.0.0.1 always | pyro5-ns --host 127.0.0.1; all locate_ns() pass host='127.0.0.1'. No UDP broadcast. | ✓ |
| Env var fallback | Try locate_ns() first; read PYRO_NS_HOST env var on failure. | |
| Direct URI, skip NS | Fixed PYRO:game.server@127.0.0.1:9091. Violates INFRA-06. | |

**User's choice:** `--host 127.0.0.1` always

**Follow-up — NS address configuration:**

| Option | Description | Selected |
|--------|-------------|----------|
| Constant in config module | NS_HOST = '127.0.0.1' in config.py | |
| Env var with 127.0.0.1 default | os.getenv('PYRO_NS_HOST', '127.0.0.1') | ✓ |

**User's choice:** Env var with `127.0.0.1` default in `config.py`

**Notes:** Motivation is demo reliability — UDP broadcast may be blocked by firewall/VPN at the academic evaluation. Env var default keeps it flexible without extra branching in application code.

---

## Bridge Startup Coupling

| Option | Description | Selected |
|--------|-------------|----------|
| Retry with backoff | Poll NS + GameServer lookup ~10s, 0.5s sleep. Forgives startup race. | ✓ |
| Fail fast with clear error | Single attempt; print "Start GameServer first" and exit. | |
| Lazy connect on first request | Flask starts immediately; first WebSocket message triggers NS lookup. | |

**User's choice:** Retry with backoff

**Notes:** Practical choice for 3-terminal manual startup sequence where processes start seconds apart.

---

## Smoke Test Format

| Option | Description | Selected |
|--------|-------------|----------|
| Manual script + README | test_client.py CLI + 3-terminal README procedure. | |
| Automated pytest with subprocess | pytest spawns all 3 processes. Complex for Phase 1. | |
| Hybrid: manual smoke + automated unit tests | Manual for callback demo; automated pytest for unit tests. | ✓ |

**User's choice:** Hybrid

**Follow-up — unit test strategy:**

| Option | Description | Selected |
|--------|-------------|----------|
| Real in-process Pyro5 daemon | Daemon in thread inside test. Validates actual RPC wiring. | ✓ |
| Mock Pyro5 calls | unittest.mock. Fast but doesn't validate serialization. | |

**User's choice:** Real in-process Pyro5 daemon

**Notes:** Tests must prove actual Pyro5 wiring. The STATE.md research flag warns not to use mocks for this layer.

---

## Project File Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Structured subdirectories | server/, bridge/, client/, tests/ dirs. | ✓ |
| Flat at root | All .py files at root. | |
| Single src/ package | src/ with __init__.py. | |

**User's choice:** Structured subdirectories

**Follow-up — package type:**

| Option | Description | Selected |
|--------|-------------|----------|
| Plain directories, no __init__.py | Run scripts directly: python server/game_server.py | |
| Python packages with __init__.py | Enables cross-module imports | ✓ |

**User's choice:** Python packages with `__init__.py`

**Follow-up — shared config location:**

| Option | Description | Selected |
|--------|-------------|----------|
| config.py at project root | import config from server/ and bridge/ | ✓ |
| config.py inside shared/ package | shared/config.py with __init__.py | |

**User's choice:** `config.py` at project root

**Notes:** Python packages enable `from server.event_broadcaster import EventBroadcaster` in game_server.py — useful as the project grows. Root-level config.py avoids circular import risks.

---

## Claude's Discretion

- Port numbers: NS 9090 (Pyro5 default), GameServer 9091, Bridge 5000
- Retry backoff timing: 0.5s sleep, ~10s total timeout
- `EventBroadcaster` as separate class vs methods on `GameServer` — follow PRD.md §EventBroadcaster sketch

## Deferred Ideas

None raised during discussion.
