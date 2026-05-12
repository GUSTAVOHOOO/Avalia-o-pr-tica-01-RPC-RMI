---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: ready_to_plan
stopped_at: "Completed 01-04: Flask-SocketIO bridge + BridgeCallbackReceiver + per-thread proxy + pipeline verified"
last_updated: "2026-05-12T18:31:18.289Z"
last_activity: 2026-05-12
progress:
  total_phases: 8
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-12)

**Core value:** Demonstrar arquitetura distribuída event-driven funcional: servidor Pyro5 com callbacks push para todos os clientes, mecânicas de jogo completas e interface web reagindo em tempo real com 2–4 jogadores simultâneos
**Current focus:** Phase 01 — RPC Infrastructure + Callback Pipeline

## Current Position

Phase: 2
Plan: Not started
Status: Ready to plan
Last activity: 2026-05-12

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 4
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-rpc-infrastructure-callback-pipeline P01 | 2 | 2 tasks | 9 files |
| Phase 01-rpc-infrastructure-callback-pipeline P04 | multi-session | 3 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Flask-SocketIO must use `async_mode='threading'` — hardcoded, never rely on defaults (C5 pitfall)
- [Init]: All Pyro5 broadcast methods on GameServer must be `@oneway` — prevents callback deadlock (C1 pitfall)
- [Init]: No HTML/CSS work until Phase 1 3-terminal smoke test passes (M4 pitfall — research constraint)
- [Init]: Pyro5 proxies in Bridge are per-thread via `threading.local()` — never shared (C2 pitfall)
- [Init]: Images served as Flask static file URLs — never raw bytes through Pyro5 serialization (C4 pitfall)
- [Phase ?]: python3.11 -m venv (not python3) to avoid mise's Python 3.8.20 default — Pyro5 5.16 supported on 3.9+
- [Phase ?]: NS_HOST reads from PYRO_NS_HOST env var (default 127.0.0.1) — satisfies D-02, avoids UDP broadcast issue on demo day
- [Phase ?]: pytest stubs use pytest.skip rather than NotImplementedError — cleaner skipped status in CI
- [01-03]: broadcast_test() @oneway prevents deadlock when callback receivers registered (D-09)
- [01-03]: test_client.py uses PYRONAME with explicit @NS_HOST to avoid UDP broadcast (D-01)
- [Phase ?]: BridgeCallbackReceiver stores URIs (not Proxy objects) — creates fresh Proxy per broadcast() call; Pyro5 proxies not thread-safe across threads (C2 pitfall)
- [Phase ?]: allow_unsafe_werkzeug=True required in socketio.run() for Flask-SocketIO dev server under newer Werkzeug
- [Phase ?]: All network binds to 127.0.0.1 loopback in Phase 1 — never 0.0.0.0 (T-01-09 mitigated)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 6 research flag]: Portuguese WordNet coverage for the specific image word set is unvalidated. Build a startup validation script before implementing arbitration. If >20% of game words return zero synsets, swap words — not library.
- [Demo risk]: Name Server UDP broadcast may be blocked by firewall/VPN on demo day. Decide at Phase 1: use `--host 127.0.0.1` + `locate_ns(host="127.0.0.1")` or hardcode direct URI `PYRO:game.server@localhost:9091`.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v2 | Configurable spy probability by host | Deferred | Init |
| v2 | Spy success bonus (+5pts) | Deferred | Init |
| v2 | Spectator mode | Deferred | Init |
| v2 | Persistent game history | Deferred | Init |
| v2 | Timer configurable per phase by host | Deferred | Init |
| v2 | Generic 404 screen | Deferred | Init |
| v2 | Authentication / cross-session accounts | Deferred | Init |
| v2 | Multiple languages | Deferred | Init |

## Session Continuity

Last session: 2026-05-12T18:31:18.270Z
Stopped at: Completed 01-04: Flask-SocketIO bridge + BridgeCallbackReceiver + per-thread proxy + pipeline verified
Resume file: None
