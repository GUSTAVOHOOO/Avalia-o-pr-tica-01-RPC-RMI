# Phase 7: Reconnection + End-of-Game - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-15
**Phase:** 07-reconnection-end-of-game
**Areas discussed:** Reconnection architecture, Chat UI placement, Play-again vote rules, Player disconnect feedback

---

## Reconnection Architecture

### Q1: Bridge behavior on Socket.IO disconnect

| Option | Description | Selected |
|--------|-------------|----------|
| Grace period | Bridge waits ~5s before calling leave_game(); cancel if player reconnects | ✓ |
| Never auto-leave | Stop calling leave_game() on disconnect entirely; removal via callback failure only | |
| You decide | Leave to planner/implementer | |

**User's choice:** Grace period (~5s before leave_game())
**Notes:** Minimal server changes; bridge uses threading.Timer per SID

---

### Q2: How bridge identifies a returning player

| Option | Description | Selected |
|--------|-------------|----------|
| New 'reconnect_game' Socket.IO event | Client emits {player_id, room_code}; bridge routes to reconnect flow | ✓ |
| Reuse existing join event with flag | Same event, is_reconnect: true + player_id | |
| You decide | Leave to planner | |

**User's choice:** New `reconnect_game` event
**Notes:** Cleaner separation from new-player join flow

---

### Q3: State delivered on reconnect

| Option | Description | Selected |
|--------|-------------|----------|
| Full snapshot via get_player_view() | Reuses existing method — phase, scores, hints, image assignment | ✓ |
| New minimal reconnect payload | Only changed state since disconnect; requires per-player state tracking | |
| You decide | Leave to planner | |

**User's choice:** Reuse `get_player_view()`
**Notes:** No new data structures needed; existing method already returns everything

---

## Chat UI Placement

### Q1: Chat location in game screen

| Option | Description | Selected |
|--------|-------------|----------|
| Tab alongside scores/events | Chat as 3rd tab per UI-04 spec | |
| Fixed side panel | Always visible, permanent strip | |
| You decide | Leave to planner/implementer | ✓ |

**User's choice:** You decide
**Notes:** Must satisfy UI-04 "placar/eventos/chat em tabs" and CHAT-03/04 separation

---

### Q2: Visual separation treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Different colors + explicit labels | Chat input: "Mensagem de chat" in secondary color; game inputs in primary color | ✓ |
| Completely separate screen zones | Physical divider with "Chat" header section | |
| You decide | Leave to implementer | |

**User's choice:** Different colors + explicit labels
**Notes:** Minimum viable separation; CHAT-04 requires no confusion between chat and action fields

---

## Play-Again Vote Rules

### Q1: What counts as majority

| Option | Description | Selected |
|--------|-------------|----------|
| Strict majority: >50% explicit yes | Abstentions = implicit no; tie → game ends | |
| Any yes > no (abstentions excluded) | 1 yes + 0 no could continue | |
| You decide | Leave vote counting to planner | ✓ |

**User's choice:** You decide
**Notes:** Planner must ensure abstentions can't accidentally continue the game with very few votes

---

### Q2: Game-over navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Show final screen, then redirect to landing | Post-game stays briefly, then all redirect; session deleted | ✓ |
| Show final screen indefinitely | Players navigate away manually | |
| You decide | Leave to implementer | |

**User's choice:** Final screen → redirect to landing page; session deleted on server

---

## Player Disconnect Feedback

### Q1: What remaining players see on mid-game removal

| Option | Description | Selected |
|--------|-------------|----------|
| Broadcast PLAYER_LEFT event | Toast notification "Jogador X saiu da partida" | ✓ |
| Silent removal | No notification | |
| You decide | Leave to planner | |

**User's choice:** PLAYER_LEFT broadcast with player name

---

### Q2: Failure threshold for INFRA-07

| Option | Description | Selected |
|--------|-------------|----------|
| 3 consecutive failures | Matches grace period; filters momentary hiccups | ✓ |
| 1 failure | More aggressive; fast cleanup | |
| You decide | Leave to planner | |

**User's choice:** 3 consecutive callback failures

---

## Claude's Discretion

- Chat placement within game screen (tab vs. panel) — must satisfy UI-04 + CHAT-03/04
- Exact vote counting semantics — strict majority vs. active-voter majority
- Grace period timer implementation (threading.Timer per SID vs. timestamp dict)

## Deferred Ideas

- Reconnection banner (UI-09: amber/red visual states) — styling deferred to Phase 8 UI Polish
- Spectator mode — v2
- Persistent game history — v2
