---
phase: 07-reconnection-end-of-game
plan: "03"
subsystem: bridge+frontend
tags: [reconnection, grace-period, chat, vote, gamescreen, socket-io]
dependency_graph:
  requires: ["07-01"]
  provides: ["bridge grace-period disconnect (D-01)", "reconnect_game handler (D-02)", "send_chat+submit_vote handlers", "5 BridgeCallbackReceiver push methods", "GameScreen reconnect-on-mount", "navigate to /postgame on game_ended"]
  affects: ["bridge/bridge.py", "frontend/src/pages/GameScreen.tsx", "frontend/src/pages/GameScreen.css"]
tech_stack:
  added: []
  patterns:
    - "threading.Timer with daemon=True keyed by SID for grace-period disconnect (D-01)"
    - "Cancel pending leave by scanning player_id; SID is key to avoid player_id key collisions (Pitfall 1)"
    - "reconnect_game conditional: emit reconnect_game if localStorage has player_id, else join_room"
    - "navigate() replacing setGameEnded(true) for game_ended and vote_started events"
key_files:
  modified:
    - bridge/bridge.py
    - frontend/src/pages/GameScreen.tsx
    - frontend/src/pages/GameScreen.css
decisions:
  - "_pending_leaves keyed by SID (not player_id) to correctly handle race between new SID reconnect and old SID timer (Pitfall 1 in RESEARCH.md)"
  - "GameScreen always emits reconnect_game when localStorage has player_id; falls back to join_room only if player_id absent — covers both fresh join and reload scenarios"
  - "handleGameEnded now calls navigate(/postgame/:roomCode) directly; setGameEnded(true) is no longer called from that path"
metrics:
  duration_minutes: 15
  completed_date: "2026-05-16"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 3
---

# Phase 7 Plan 03: Bridge + GameScreen Vertical Slice Summary

**One-liner:** Bridge grace-period disconnect with 5s timer, reconnect/chat/vote Socket.IO handlers, 5 new callback push methods, and GameScreen reconnect-on-mount + /postgame navigation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Bridge grace-period disconnect, reconnect handler, new handlers, callback methods | ac6abea | bridge/bridge.py |
| 2 | GameScreen reconnect-on-mount, navigation, chat + player_left handlers | cc288f6 | frontend/src/pages/GameScreen.tsx, GameScreen.css |

## What Was Built

### Task 1 — bridge/bridge.py

**GROUP A — Module-level state:**
- Added `_pending_leaves: dict = {}` (maps `sid -> (threading.Timer, player_id)`) and `_pending_leaves_lock = threading.Lock()` after `_cb_uri`.

**GROUP B — Grace-period disconnect (replaces immediate leave_game):**
- `handle_disconnect` now captures `request.sid` before lock release, then starts a `threading.Timer(5.0, do_leave)` if a `player_id` was found. The `do_leave` closure calls `proxy.leave_game(player_id)` after 5 seconds. Timer stored in `_pending_leaves[sid]`.

**GROUP C — New Socket.IO handlers:**
- `handle_reconnect_game(data)`: scans `_pending_leaves` by `player_id` to cancel any pending timer, re-registers SID mapping under `_sid_lock`, calls `join_room(room_code)`, then calls `proxy.reconnect_player(player_id, room_code, _cb_uri)` and returns the player view.
- `handle_send_chat(data)`: SID → player_id lookup + `proxy.send_chat(player_id, message)`.
- `handle_submit_vote(data)`: SID → player_id lookup + `proxy.submit_vote(player_id, continue_game)`.

**GROUP D — New BridgeCallbackReceiver methods (appended after `on_spy_success`):**
- `on_chat_message`: emits `chat_message` to `data["room_code"]`.
- `on_player_left`: emits `player_left` to `data["room_code"]`.
- `on_vote_started`: emits `vote_started` to `data["room_code"]`.
- `on_vote_update`: emits `vote_update` to `data["room_code"]`.
- `on_game_restarting`: emits `game_restarting` to `data["room_code"]`.

All methods follow the `@Pyro5.api.oneway @Pyro5.api.callback` + `try/except` pattern.

### Task 2 — frontend/src/pages/GameScreen.tsx + GameScreen.css

**Imports:** Added `useNavigate` to the `react-router` import.

**New interfaces:** `ChatMessage { player_id, player_name, message, timestamp }` and `VoteStartedPayload { room_code, duration_seconds, player_count }`.

**New state:** `chatMessages: ChatMessage[]`, `playerLeftMsg: string | null`, `navigate = useNavigate()`.

**Reconnect-or-join on mount:**
- Checks `localStorage.getItem('player_id')` — if present, emits `reconnect_game`; else emits `join_room`. Both use the same `handleReconnectOrJoin` ack callback. On `status === 'ENDED'` the ack now navigates to `/postgame/:roomCode` instead of setting `gameEnded`.

**handleGameEnded:** Replaced `setGameEnded(true)` with `navigate(\`/postgame/${roomCode}\`)`.

**New handlers registered in useEffect:**
- `handlePlayerLeft`: filters `players` state, sets `playerLeftMsg` for 4s toast.
- `handleGameRestarting`: navigates to `/game/${roomCode}` for GameScreen re-mount.
- `handleChatMessage`: appends to `chatMessages` state.
- `handleVoteStarted`: navigates to `/postgame/${roomCode}`.

All 4 handlers registered with `socket.on` and unregistered in cleanup `socket.off`.

**CSS:** Added `.player-left-toast` (fixed bottom-right, `background: #1a1d27`, `border-left: 3px solid #ef4444`, `z-index: 50`, `padding: 12px 16px`, `max-width: 300px`) and `.player-left-toast__text` (14px, `color: #e2e8f0`).

## Checkpoint Reached

**Type:** human-verify (gate: blocking)

**Task 3 is a checkpoint requiring 4-terminal smoke test.** The executor stopped here as required by the plan.

### Checkpoint — How to Verify

Start all 4 processes: `pyro5-ns`, game server, bridge, and open the React app.

1. Create a game with Player A. Join with Player B. Start the game. Confirm the game screen loads.
2. While the game is running, RELOAD Player A's browser tab.
3. Expected: Player A sees "Reconectando…" briefly, then the game screen restores (same phase, same image) within 5 seconds. Player B sees no "player left" notification (grace period absorbed the disconnect).
4. Verify in the bridge terminal log: `[BRIDGE] reconnect_game: player ... reconnected to room ...`
5. Verify Player A is still in the player list on both screens after reconnect.

**Resume signal:** Type "approved" if reconnect works, or describe what failed.

## Deviations from Plan

None — plan executed exactly as written. All 9 new identifiers present in bridge.py, TypeScript compilation exits 0.

## Known Stubs

None. All implementations are wired: handlers forward to real RPC methods (defined in plan 07-02), callback methods emit to real Socket.IO rooms.

Note: `reconnect_player`, `send_chat`, `submit_vote` RPCs are defined in `server/game_server.py` (plan 07-02). If plan 07-02 is not yet executed, these bridge handlers will get RPC errors at runtime — that is expected for the parallel wave execution model.

## Threat Surface Scan

No new network endpoints or auth paths beyond what the threat model in the plan already covers:

| Flag | File | Description |
|------|------|-------------|
| threat_flag: input-validation | bridge/bridge.py | handle_reconnect_game accepts client-supplied player_id from localStorage; validated server-side by reconnect_player() which checks _player_to_room |

## Self-Check: PASSED

- bridge/bridge.py exists: FOUND
- frontend/src/pages/GameScreen.tsx exists: FOUND
- frontend/src/pages/GameScreen.css exists: FOUND
- commit ac6abea: FOUND (feat(07-03): bridge grace-period)
- commit cc288f6: FOUND (feat(07-03): GameScreen reconnect-on-mount)
- `bridge import ok` from `python -c "import bridge.bridge"`: PASSED
- `npx tsc --noEmit` exits 0: PASSED
- 9 identifiers in bridge.py: FOUND
- handleGameEnded no longer calls setGameEnded(true): CONFIRMED
