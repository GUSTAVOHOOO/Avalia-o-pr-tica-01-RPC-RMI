---
phase: 02-player-session-lobby
fixed_at: 2026-05-12T00:00:00Z
review_path: .planning/phases/02-player-session-lobby/02-REVIEW.md
iteration: 1
findings_in_scope: 11
fixed: 11
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-05-12
**Source review:** `.planning/phases/02-player-session-lobby/02-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 11
- Fixed: 11
- Skipped: 0

## Fixed Issues

### CR-01: Lobby component never populates the player list on mount

**Files modified:** `bridge/bridge.py`, `frontend/src/pages/Lobby.tsx`
**Commit:** 8613f35 (bridge), d385fae (frontend)
**Applied fix:**
- Added `handle_get_players` Socket.IO handler in `bridge/bridge.py` that calls `proxy.get_session(room_code)` on the game server.
- Added `get_session(room_code: str) -> dict` method to `GameServer` that returns `{"players": session.get_player_dicts()}` under lock.
- Added `socket.emit('get_players', { room_code: sessionId }, callback)` call in `Lobby.tsx` `useEffect` before registering event listeners; seeds `setPlayers` from the response.

---

### CR-02: `handleHostChanged` identifies new host by name instead of ID

**Files modified:** `frontend/src/pages/Lobby.tsx`
**Commit:** d385fae
**Applied fix:** Rewrote `handleHostChanged` to accept `{ new_host_id: string; players: Player[] }` and compare `data.new_host_id === playerId` directly. The player list is updated from `data.players`. The old code compared against `data.new_host_name` (which the server never sends) causing the host to never be correctly recognized.

---

### CR-03: `_sid_to_player` dict mutated without lock — data race

**Files modified:** `bridge/bridge.py`
**Commit:** 8613f35
**Applied fix:** Added `_sid_lock = threading.Lock()` at module level. All read and write operations on `_sid_to_player` (`handle_create_game`, `handle_join_game`, `handle_start_game`, `handle_disconnect`) are now wrapped in `with _sid_lock:` blocks.

---

### CR-04: `handle_start_game` forwards unvalidated client-supplied `max_turns`

**Files modified:** `bridge/bridge.py`, `server/game_server.py`, `frontend/src/pages/Lobby.tsx`, `tests/test_session.py`
**Commit:** 8613f35 (bridge/server), d385fae (frontend)
**Applied fix:**
- Removed `max_turns` parameter from `GameServer.start_game()`; the session's stored `max_turns` (set at `create_game` time) is used instead.
- Removed `max_turns` from the bridge `handle_start_game` call to `proxy.start_game(player_id)`.
- Removed `max_turns` from the `socket.emit('start_game', ...)` payload in `Lobby.tsx`.
- Updated `tests/test_session.py` to call `proxy.start_game(player_id)` without the second argument.

---

### CR-05: Path traversal in Flask SPA catch-all route

**Files modified:** `bridge/bridge.py`
**Commit:** 8613f35
**Applied fix:** Removed the `os.path.exists(full_path)` check that probed the filesystem with unsanitised user input. Replaced the route with a try/except that calls `send_from_directory` directly and falls back to `index.html` on any exception — relying on `send_from_directory`'s built-in path-traversal guard.

---

### WR-01: Socket not disconnected on error in CreateGame/JoinGame/JoinByCode

**Files modified:** `frontend/src/pages/CreateGame.tsx`, `frontend/src/pages/JoinGame.tsx`, `frontend/src/pages/JoinByCode.tsx`
**Commit:** d385fae
**Applied fix:** Added `socket.disconnect()` immediately before `setError(...)` in the error branch of each page's ack callback.

---

### WR-02: `start_game` emit in Lobby has no ack callback

**Files modified:** `frontend/src/pages/Lobby.tsx`
**Commit:** d385fae
**Applied fix:** Added ack callback `(resp: { success: boolean; error?: string }) => { ... }` to the `socket.emit('start_game', ...)` call. On failure, calls `setGameStarting(false)` and `addToast(resp.error ?? 'Não foi possível iniciar o jogo.', 'error')` so the spinner is never stuck.

---

### WR-03: EventBroadcaster silently removes callbacks on transient errors

**Files modified:** `server/event_broadcaster.py`
**Commit:** 3df76b8
**Applied fix:** Split the `except Exception` block into two: `except (ConnectionRefusedError, OSError)` for permanent failures (added to `failed` list, entry removed) and `except Exception` for transient failures (logged but entry kept). This prevents a single timeout from permanently dropping a player from future broadcasts.

---

### WR-04: Player name length mismatch (client maxLength=20, server limit=50)

**Files modified:** `server/game_server.py`
**Commit:** 3df76b8
**Applied fix:** Changed the server-side validation in both `create_game` and `join_game` from `len(player_name) > 50` to `len(player_name) > 20`, aligning with the `maxLength={20}` already present in all three frontend input fields.

---

### WR-05: `leave_game` does not unregister player callback from EventBroadcaster

**Files modified:** `server/event_broadcaster.py`, `server/game_server.py`
**Commit:** 3df76b8
**Applied fix:**
- Added `unregister_callback(player_id: str)` method to `EventBroadcaster` that calls `self.callbacks.pop(player_id, None)` under lock.
- Called `self.broadcaster.unregister_callback(player_id)` inside the `leave_game` lock block immediately after removing the player from `session.players`.

---

### WR-06: O(n×m) linear scan in start_game/leave_game — no player-to-session index

**Files modified:** `server/game_server.py`
**Commit:** 3df76b8
**Applied fix:**
- Added `self._player_to_room: dict = {}` (player_id → room_code) to `GameServer.__init__`.
- Updated `create_game` and `join_game` to set `self._player_to_room[player_id] = room_code` inside the lock block.
- Replaced the nested loop in `start_game` with `room_code = self._player_to_room.get(player_id)` O(1) lookup.
- Replaced the nested loop in `leave_game` with `room_code = self._player_to_room.pop(player_id, None)` O(1) lookup; if `None`, returns `False` immediately.

---

## Skipped Issues

None — all findings were fixed.

---

## Verification

**Python tests:** `10 passed in 2.39s` (all tests pass after fixes)
**Frontend build:** `tsc -b && vite build` succeeded — `✓ built in 649ms`, no TypeScript errors.

---

_Fixed: 2026-05-12_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
