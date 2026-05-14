# Phase 3: Phase Machine + Timer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 3-phase-machine-timer
**Areas discussed:** Phase machine structure, Timer durations, Multi-turn loop, Frontend scope

---

## Phase Machine Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Separate TurnMachine class | New class in server/turn_machine.py; GameSession holds an instance; easier to test in isolation | ✓ |
| Methods on GameServer | Add _advance_phase, _start_timer directly to GameServer — simpler, no new indirection | |

**User's choice:** Separate TurnMachine class in `server/turn_machine.py`

| Option | Description | Selected |
|--------|-------------|----------|
| server/turn_machine.py | New file, follows established pattern of one-concern-per-module | ✓ |
| Inside server/game_server.py | Keeps everything in one file; grows large as phases add mechanics | |

**User's choice:** `server/turn_machine.py` (new file)

| Option | Description | Selected |
|--------|-------------|----------|
| TurnMachine receives broadcaster in __init__ | Dependency injection; TurnMachine calls broadcast directly; no back-reference to GameServer | ✓ |
| TurnMachine calls a callback function | GameServer passes on_phase_changed callback; controls all RPC state but adds indirection | |

**User's choice:** TurnMachine receives EventBroadcaster in `__init__`

---

## Timer Durations

| Option | Description | Selected |
|--------|-------------|----------|
| PHASE_DURATIONS dict in config.py | Follows NS_HOST/BRIDGE_PORT pattern — one place to tune | ✓ |
| Constants inside TurnMachine class | Co-located with logic but requires editing turn_machine.py to tune | |

**User's choice:** `PHASE_DURATIONS` dict in `config.py`

| Option | Description | Selected |
|--------|-------------|----------|
| 60s action phases, 30s transitions | HINT/GUESS: 60s, EXCHANGE: 45s, SPY: 30s, SCORING: 15s | ✓ |
| 30s flat for all phases | Simple, fast, but tight for players | |
| Custom values | User-specified per-phase seconds | |

**User's choice:** 60s for action phases, shorter for transitions

| Option | Description | Selected |
|--------|-------------|----------|
| Short: ROUND_START 5s, TURN_END 5s | Enough for UI to display transition; Phase 4 uses these moments | ✓ |
| 10s each | More breathing room for animation/image load | |
| Immediate (0s) | Server-side markers only; advance as fast as possible | |

**User's choice:** ROUND_START 5s, TURN_END 5s

**Final durations:** `{"ROUND_START": 5, "HINT_PHASE": 60, "GUESS_PHASE": 60, "EXCHANGE_PHASE": 45, "SPY_PHASE": 30, "SCORING_PHASE": 15, "TURN_END": 5}`

---

## Multi-Turn Loop

| Option | Description | Selected |
|--------|-------------|----------|
| Go directly to HINT_PHASE for turn 2+ | ROUND_START once at start; subsequent turns skip to HINT_PHASE | ✓ |
| Go back to ROUND_START every turn | Consistent state machine; extra 5s pause between every turn | |

**User's choice:** HINT_PHASE directly for turns 2+ (ROUND_START is game-start only)

| Option | Description | Selected |
|--------|-------------|----------|
| Broadcast GAME_ENDED + set status ENDED | Simple; Phase 7 wires frontend to GAME_ENDED | ✓ |
| Broadcast PHASE_CHANGED with phase='GAME_OVER' | Consistent event type but overloads PHASE_CHANGED | |

**User's choice:** `GAME_ENDED` event + `session.status = "ENDED"`

| Option | Description | Selected |
|--------|-------------|----------|
| TurnMachine owns current_turn | Starts at 1, increments at TURN_END; max_turns passed at construction | ✓ |
| GameSession owns current_turn | All session state in one place; TurnMachine reads/writes through reference | |

**User's choice:** TurnMachine owns `current_turn`

---

## Frontend Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: phase indicator only | New /game/:roomCode route with phase name + countdown; SC-4 requires two browser sessions | ✓ |
| Pure backend + pytest only | Zero frontend changes; SC-4 verified via server logs only | |

**User's choice:** Minimal phase indicator at `/game/:roomCode`

| Option | Description | Selected |
|--------|-------------|----------|
| New /game/:roomCode route | Navigate after game_started; placeholder for Phase 4 full game screen | ✓ |
| Inline on lobby screen | Lobby transforms in-place; mixes lobby and game state | |

**User's choice:** New `/game/:roomCode` route

| Option | Description | Selected |
|--------|-------------|----------|
| Phase name + countdown only | Current phase, seconds remaining. Phase 4 adds panels and action inputs | ✓ |
| Phase name + countdown + color states | Also implement green/yellow/red timer (UI-05); less work in Phase 8 | |

**User's choice:** Phase name + countdown only (color states deferred to Phase 8)

---

## Claude's Discretion

- Generation counter: `_generation: int` on TurnMachine, incremented each advance; timer callbacks check before firing
- State machine order: WAITING → ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END
- `advance_phase(player_id)` exposed as a test/operator RPC call on GameServer for success-criteria smoke test
- TurnMachine uses `threading.RLock` (matching GameServer.lock pattern)
- Timer cancellation: hold active `threading.Timer` handle, call `.cancel()` on manual advance

## Deferred Ideas

- Timer color states (green/yellow/red) on countdown — deferred to Phase 8 (UI-05)
- Per-game configurable timer durations — deferred to v2
- Authorization on `advance_phase` (host-only enforcement) — defer to later phase
