# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-12)

**Core value:** Demonstrar arquitetura distribuída event-driven funcional: servidor Pyro5 com callbacks push para todos os clientes, mecânicas de jogo completas e interface web reagindo em tempo real com 2–4 jogadores simultâneos
**Current focus:** Phase 1 — RPC Infrastructure + Callback Pipeline

## Current Position

Phase: 1 of 8 (RPC Infrastructure + Callback Pipeline)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-05-12 — Roadmap created; all 69 v1 requirements mapped across 8 phases

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Flask-SocketIO must use `async_mode='threading'` — hardcoded, never rely on defaults (C5 pitfall)
- [Init]: All Pyro5 broadcast methods on GameServer must be `@oneway` — prevents callback deadlock (C1 pitfall)
- [Init]: No HTML/CSS work until Phase 1 3-terminal smoke test passes (M4 pitfall — research constraint)
- [Init]: Pyro5 proxies in Bridge are per-thread via `threading.local()` — never shared (C2 pitfall)
- [Init]: Images served as Flask static file URLs — never raw bytes through Pyro5 serialization (C4 pitfall)

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

Last session: 2026-05-12
Stopped at: Roadmap + STATE.md initialized; REQUIREMENTS.md traceability updated; ready to plan Phase 1
Resume file: None
