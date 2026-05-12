# Phase 2: Player Session + Lobby - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-12
**Phase:** 02-player-session-lobby
**Areas discussed:** Session API contract, Player identity origin, Frontend HTML structure, Socket.IO room isolation

---

## Session API Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Separate methods | `create_game` and `join_game` as distinct Pyro5 methods with clear signatures | ✓ |
| Single join_game | One method that auto-creates if no room_code given; matches PRD signature | |

**User's choice:** Separate methods

**Q: Return type for create/join?**

| Option | Description | Selected |
|--------|-------------|----------|
| Full player dict | `{player_id, room_code, is_host}` returned by both methods | ✓ |
| Minimal strings | `create_game` returns `room_code`, `join_game` returns `player_id` only | |

**User's choice:** Full player dict

**Q: Callback registration absorption?**

| Option | Description | Selected |
|--------|-------------|----------|
| Absorb internally | create/join register the callback in the same RPC call | ✓ |
| Keep separate | Bridge calls register_callback after create/join | |

**User's choice:** Absorb — create/join do the callback registration

---

## Player Identity Origin

| Option | Description | Selected |
|--------|-------------|----------|
| GameServer generates UUID | Server calls uuid.uuid4(), returns player_id in response; frontend stores in localStorage | ✓ |
| Frontend generates UUID | Browser generates UUID before connecting and sends it in the payload | |

**User's choice:** GameServer generates it on create/join

**Q: Bridge sid→player_id mapping?**

| Option | Description | Selected |
|--------|-------------|----------|
| Bridge dict: sid→player_id | Module-level `_sid_to_player` dict, populated on join, cleared on disconnect | ✓ |
| Frontend sends player_id with every event | player_id in every socket event payload, no server-side mapping | |

**User's choice:** Bridge maintains a dict: socket_sid → player_id

---

## Frontend HTML Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Multiple Flask-served HTML files | Flask templates for each route; Vanilla JS per page | |
| Single HTML + JS routing | One index.html with client-side section switching | |
| React + TypeScript | User's original plan; Vite build; overrides CLAUDE.md Vanilla JS recommendation | ✓ |

**User's choice:** React + TypeScript (free-text response overriding the presented options)

**Notes:** User stated initial plan was React + TypeScript with a scalable but non-overengineered structure. UI.md routes serve as a base but are not immutable — navigation adjustments allowed if they improve UX or simplify flows.

**Q: Dev server proxy vs. serve bundle only?**

| Option | Description | Selected |
|--------|-------------|----------|
| Vite dev server proxies /socket.io to Flask | Two servers in dev; production: build to frontend/dist/ | ✓ |
| Flask serves React bundle only | Always rebuild before testing | |

**Q: Frontend directory?**

| Option | Description | Selected |
|--------|-------------|----------|
| frontend/ at project root | package.json, vite.config.ts, src/ at root level | ✓ |
| Inside bridge/frontend/ | Co-located with the bridge that serves it | |

---

## Socket.IO Room Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| Per-game-session rooms from start | join_room(room_code) on connect; emit with to=room_code | ✓ |
| Broadcast to all for now | socketio.emit to all sockets; refactor later | |

**User's choice:** Per-game-session rooms from the start

**Q: How does bridge know which room to emit to?**

| Option | Description | Selected |
|--------|-------------|----------|
| GameServer includes room_code in every event payload | Bridge reads data["room_code"] | ✓ |
| Bridge maintains callback_uri → room_code mapping | Extra BridgeCallbackReceiver state | |

---

## Claude's Discretion

- 6-character room code format (uppercase alphanumeric A-Z0-9)
- Max 6 players per session (per PROJECT.md)
- `GameSession` dataclass or dict keyed by room_code on GameServer
- `leave_game` called on socket disconnect (SESSION-07 host handoff)
- Collision checking for room codes

## Deferred Ideas

None — discussion stayed within phase scope.
