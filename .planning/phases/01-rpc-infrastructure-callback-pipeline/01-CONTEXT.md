# Phase 1: RPC Infrastructure + Callback Pipeline - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Three OS processes (Pyro5 Name Server, GameServer, Flask-SocketIO Bridge) running and communicating; a server-pushed Pyro5 callback arrives at a CLI test client without the client having polled or requested it. No game mechanics, no player sessions, no HTML/CSS — pure RPC infrastructure proof.

Requirements in scope: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06

</domain>

<decisions>
## Implementation Decisions

### Name Server Discovery
- **D-01:** Always start NS with `pyro5-ns --host 127.0.0.1`. All `locate_ns()` calls pass `host` from config to avoid UDP broadcast (which may be blocked by firewall/VPN on demo day).
- **D-02:** NS host is read from env var `PYRO_NS_HOST` with default `'127.0.0.1'` — defined once in `config.py`, imported everywhere. This satisfies INFRA-06 (no hardcoded URIs in clients) without adding complex branching.

### Bridge Startup Coupling
- **D-03:** Bridge polls the Name Server + GameServer lookup for ~10 seconds (0.5s sleep between attempts) before giving up with a clear error message. This forgives the race condition when a developer launches 3 terminals in quick succession.

### Smoke Test Format
- **D-04:** Hybrid approach — manual 3-terminal procedure (`test_client.py` CLI script) proves the callback push end-to-end; automated `pytest` unit tests run a real in-process Pyro5 daemon in a thread and validate `ping()`, `register_callback()`, and broadcast delivery without requiring the full 3-terminal setup.
- **D-05:** Unit tests use a real in-process Pyro5 daemon (not mocks) to validate actual RPC serialization and callback wiring.

### Project File Layout
- **D-06:** Structured subdirectories: `server/` (game_server.py, event_broadcaster.py), `bridge/` (bridge.py), `client/` (test_client.py), `tests/` (test_unit.py). Each subdirectory is a Python package with `__init__.py`.
- **D-07:** `config.py` lives at the project root — imported by both `server/` and `bridge/` as `import config`. Contains `NS_HOST`, `GAME_SERVER_PORT` (9091), `BRIDGE_PORT` (5000), and any other shared constants.

### Pre-Locked Decisions (from initialization — do not re-litigate)
- **D-08:** Flask-SocketIO must use `async_mode='threading'` — hardcoded, never rely on defaults.
- **D-09:** All Pyro5 broadcast methods on GameServer (those that call EventBroadcaster) must be `@oneway` to prevent callback deadlock.
- **D-10:** Pyro5 proxies in Bridge are per-thread via `threading.local()` — never shared across threads.

### Claude's Discretion
- Port numbers (NS: 9090 default, GameServer: 9091, Bridge: 5000) — use these standard values unless there's a conflict.
- Retry backoff timing for Bridge startup — 0.5s sleep, ~10s total timeout is reasonable.
- Exact structure of `EventBroadcaster` (whether it's a separate class or methods on `GameServer`) — follow PRD.md §EventBroadcaster pattern.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `PRD.md` — Full product requirements including EventBroadcaster pattern (line ~799), callback registration model, GameServer API shape, and Phase 1 infrastructure requirements (INFRA-01 through INFRA-06)
- `.planning/REQUIREMENTS.md` — Traceability table; INFRA-01 through INFRA-06 are the Phase 1 requirements

### Architecture
- `.planning/PROJECT.md` §Architecture Decision — Bridge WebSocket diagram (Browser ↔ WebSocket Bridge ↔ Pyro5 Daemon)
- `.planning/PROJECT.md` §Key Decisions — locked decisions including `async_mode='threading'`, `@oneway`, per-thread proxies, images via Flask static

### Roadmap / Success Criteria
- `.planning/ROADMAP.md` §Phase 1 — 5 success criteria that must all be TRUE for phase completion

### Technology References (from CLAUDE.md)
- `CLAUDE.md` §Key Pyro5 Patterns — patterns 1–4 (single-instance server, bridge callback object, Name Server usage, `@oneway` for fire-and-forget)
- `CLAUDE.md` §Version Summary — pinned versions: Pyro5==5.16, Flask-SocketIO==5.6.1, Flask 3.1.x

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — fresh project. Phase 1 creates the foundation.

### Established Patterns
- PRD.md lines ~799–820 contain a reference implementation sketch of `EventBroadcaster` with `callbacks` dict and `broadcast()` method. Use this as the design reference.
- PRD.md lines ~411–420 show the `join_game` / `register_callback` API signatures that Phase 2 will build on — Phase 1 should create `register_callback(player_id, callback_uri)` with this exact signature to avoid Phase 2 refactoring.

### Integration Points
- `config.py` (root) → imported by `server/game_server.py` and `bridge/bridge.py`
- `server/event_broadcaster.py` → imported and used by `server/game_server.py`
- `bridge/bridge.py` → creates a `BridgeCallbackReceiver` Pyro5 object, registers it with GameServer, routes incoming callback events to `socketio.emit()`

</code_context>

<specifics>
## Specific Ideas

- The `test_client.py` in `client/` should be a minimal CLI script: discovers GameServer via NS, registers a callback receiver, waits for a push event, prints it, and exits. This is the Phase 1 demo artifact.
- Startup sequence in README: (1) `pyro5-ns --host 127.0.0.1`, (2) `python server/game_server.py`, (3) `python bridge/bridge.py`, (4) `python client/test_client.py`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-rpc-infrastructure-callback-pipeline*
*Context gathered: 2026-05-12*
