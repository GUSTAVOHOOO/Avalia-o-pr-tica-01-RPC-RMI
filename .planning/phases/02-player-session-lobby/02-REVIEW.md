---
phase: 02-player-session-lobby
reviewed: 2026-05-12T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - bridge/bridge.py
  - frontend/index.html
  - frontend/package.json
  - frontend/src/App.tsx
  - frontend/src/components/PlayerListItem.tsx
  - frontend/src/main.tsx
  - frontend/src/pages/CreateGame.tsx
  - frontend/src/pages/JoinByCode.tsx
  - frontend/src/pages/JoinGame.tsx
  - frontend/src/pages/Landing.tsx
  - frontend/src/pages/Lobby.tsx
  - frontend/src/socket.ts
  - frontend/tsconfig.json
  - frontend/vite.config.ts
  - server/game_server.py
  - tests/test_session.py
findings:
  critical: 5
  warning: 6
  info: 3
  total: 14
status: fixed
fixed_at: 2026-05-12T00:00:00Z
fixed_commits: [8613f35, 3df76b8, d385fae]
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Phase 2 delivers session creation, lobby management, and the bridge between the Pyro5 game server and the React frontend. The server-side locking strategy is correct and the per-thread proxy pattern is properly applied. However, several correctness bugs exist that would cause visible failures in a live session: the Lobby component never loads the initial player list, the host-changed handler identifies the new host incorrectly, the `_sid_to_player` map is mutated without a lock from the callback thread, the `start_game` handler ignores the server's own `max_turns` and instead sends a client-supplied value without validation, and path-traversal is possible via the Flask static-file route. Additional warnings cover socket state leaks, a missing ack timeout, and an input length mismatch between client and server.

---

## Critical Issues

### CR-01: Lobby component never populates the player list on mount

**File:** `frontend/src/pages/Lobby.tsx:26`

**Issue:** `players` is initialised as an empty array and is only updated when a `player_joined` Socket.IO event arrives after mount. For the host (who just created the game) and for any player who joins before the Lobby component renders (e.g. a page refresh), the list stays empty for the entire session. There is no RPC call on mount to fetch the current player list for the room. The server holds the authoritative `players` list but the frontend never queries it on load.

**Fix:** Add a `get_lobby` (or reuse existing session data) RPC call via a Socket.IO `get_players` event on mount, and seed `setPlayers` from the response. A minimal approach:

```typescript
// In useEffect (before registering listeners)
socket.emit('get_players', { room_code: sessionId }, (data: { players: Player[] }) => {
  if (data?.players) setPlayers(data.players)
})
```

And add a corresponding `handle_get_players` handler in `bridge/bridge.py` that calls a `get_session` method on the game server.

---

### CR-02: `handleHostChanged` identifies the new host by name instead of ID — always wrong after a rename or shared name

**File:** `frontend/src/pages/Lobby.tsx:52-61`

**Issue:** The callback logic attempts to detect whether the current player is the new host by matching `data.new_host_name` against `player_name` values in the local `players` array, then comparing the found `player_id` to `playerId`:

```typescript
const newIsHost = players.find((p) => p.player_name === newHostName)?.player_id === playerId
```

Two concrete failure modes:
1. The `host_changed` broadcast payload from the server (assembled in `game_server.py:343`) does **not** include a `new_host_name` field — it includes `new_host_id`. `data.new_host_name` is always `undefined`, so `newHostName` is always `'desconhecido'`, the lookup always fails, and no player is ever correctly recognised as the new host. `localStorage.setItem('is_host', 'true')` is never called.
2. Even if a `new_host_name` field were added, two players with identical names would produce the wrong result.

**Fix:** Use `new_host_id` from the broadcast payload, which is the field the server actually sends:

```typescript
const handleHostChanged = useCallback((data: { new_host_id: string; players: Player[] }) => {
  if (data.players) setPlayers(data.players)
  const newIsHost = data.new_host_id === playerId
  if (newIsHost) {
    localStorage.setItem('is_host', 'true')
    addToast('Você é o novo host!', 'info')
  } else {
    const newHostPlayer = data.players?.find((p) => p.player_id === data.new_host_id)
    addToast(`Novo host: ${newHostPlayer?.player_name ?? 'desconhecido'}`, 'info')
  }
}, [playerId])
```

---

### CR-03: `_sid_to_player` dict mutated from callback thread without lock — data race

**File:** `bridge/bridge.py:118,208,230,263`

**Issue:** `_sid_to_player` is a plain `dict` shared across all Flask-SocketIO handler threads. In `async_mode='threading'`, each Socket.IO event fires in a separate thread from a thread pool. The `handle_create_game`, `handle_join_game`, and `handle_disconnect` handlers all read and write `_sid_to_player` concurrently with no synchronisation. Python's GIL protects individual bytecode instructions, but compound read-modify-write operations (`_sid_to_player[key] = value` and `_sid_to_player.pop(key, None)`) are not atomic when interleaved with iteration. A disconnect event arriving concurrently with a join event can raise `RuntimeError: dictionary changed size during iteration` or silently drop an entry.

**Fix:** Protect the dict with a `threading.Lock`:

```python
_sid_lock = threading.Lock()

# In handle_create_game / handle_join_game:
with _sid_lock:
    _sid_to_player[request.sid] = result["player_id"]

# In handle_disconnect:
with _sid_lock:
    player_id = _sid_to_player.pop(request.sid, None)
```

---

### CR-04: `handle_start_game` sends client-supplied `max_turns` to server without validation

**File:** `bridge/bridge.py:249`

**Issue:** The `start_game` handler reads `max_turns` from the client's Socket.IO payload and forwards it directly to `proxy.start_game(player_id, max_turns)`:

```python
max_turns = int(data.get("max_turns", 5))
success = proxy.start_game(player_id, max_turns)
```

The server's `start_game` method (game_server.py:250) accepts `max_turns` as an argument described as "stored in session; this value is accepted as an override." This means a non-host client can send `{"max_turns": 9999}` via the `start_game` WebSocket event and override the host's original game configuration — bypassing the `{3, 5, 7, 10}` constraint that `create_game` enforces. The server does not re-validate `max_turns` inside `start_game`.

**Fix:** Either:
- Remove the `max_turns` parameter from `start_game` entirely and use the value already stored in the `GameSession` (set at `create_game` time), or
- Add the same `{3, 5, 7, 10}` guard inside `game_server.py:start_game()` and do not trust the client value.

---

### CR-05: Path traversal vulnerability in `serve_spa` Flask route

**File:** `bridge/bridge.py:283`

**Issue:** The catch-all route constructs a filesystem path by joining `FRONTEND_DIST_PATH` with the URL `path` parameter and checks for file existence before calling `send_from_directory`:

```python
full_path = os.path.join(config.FRONTEND_DIST_PATH, path)
if path and os.path.exists(full_path):
    return send_from_directory(config.FRONTEND_DIST_PATH, path)
```

`send_from_directory` does internally guard against path traversal, but the `os.path.exists(full_path)` check is performed with the raw, un-sanitised `path`. An attacker on the local network (the server binds to 127.0.0.1 only, which limits exposure but does not eliminate it) sending `GET /../../config.py` would cause `os.path.join` to produce a path outside `FRONTEND_DIST_PATH`. The `os.path.exists` call itself is harmless, but it probes the filesystem with user-controlled paths, leaking whether files exist. Additionally, if `send_from_directory`'s guard is ever bypassed or the Flask version changes, this becomes a direct file disclosure.

**Fix:** Remove the manual `os.path.exists` check entirely. `send_from_directory` already handles the "file not found" case by raising a 404, which the fallback to `index.html` should be wrapping instead:

```python
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    if path:
        try:
            return send_from_directory(config.FRONTEND_DIST_PATH, path)
        except Exception:
            pass
    return send_from_directory(config.FRONTEND_DIST_PATH, "index.html")
```

---

## Warnings

### WR-01: Socket not disconnected on error in `CreateGame` / `JoinGame` / `JoinByCode` — leaked connection

**File:** `frontend/src/pages/CreateGame.tsx:21`, `frontend/src/pages/JoinGame.tsx:19`, `frontend/src/pages/JoinByCode.tsx:19`

**Issue:** All three pages call `socket.connect()` before emitting. When the server returns an error response (e.g. "sala nao encontrada"), `setError(...)` is called but `socket.disconnect()` is not. The socket remains connected, consuming server resources and triggering a spurious `disconnect` event with `leave_game` RPC if the user navigates away — even though no session was actually joined. If the user retries by pressing the button again, `socket.connect()` is called on an already-connected socket (no-op, but misleading), and now two competing callbacks might be registered for the same `join_game` ack event in some socket.io-client versions.

**Fix:** Call `socket.disconnect()` in the error path of each callback:

```typescript
(response) => {
  setLoading(false)
  if (response.error) {
    socket.disconnect()   // add this
    setError(String(response.error))
    return
  }
  // ...
}
```

---

### WR-02: `socket.emit('start_game', ...)` in Lobby sends no ack callback — errors are silently swallowed

**File:** `frontend/src/pages/Lobby.tsx:94`

**Issue:** `handleStartGame` sets `gameStarting = true` and emits `start_game`, but never passes an acknowledgement callback. If the server returns `{"success": false}` (non-host, insufficient players) or the bridge emits `start_game_error` on the socket, the `gameStarting` spinner stays on forever because `setGameStarting(false)` is only called inside `handleGameStarted`. A rejected start leaves the host's UI stuck in "Distribuindo imagens..." with no feedback.

**Fix:** Add an ack callback to reset state on failure:

```typescript
socket.emit('start_game', { player_id: playerId, max_turns: maxTurns }, (resp: { success: boolean; error?: string }) => {
  if (!resp.success) {
    setGameStarting(false)
    addToast(resp.error ?? 'Não foi possível iniciar o jogo.', 'error')
  }
})
```

---

### WR-03: `EventBroadcaster.broadcast` silently removes callback entries on transient network errors

**File:** `server/event_broadcaster.py:62-67`

**Issue:** Any exception during a callback delivery (including transient Pyro5 `CommunicationError` or a temporary DNS issue) causes the player's callback URI to be permanently removed from `self.callbacks`. The next event will skip that player entirely. For this project the callback URI is only re-registered on `create_game`/`join_game`, so a single dropped callback causes the player to stop receiving all future server pushes for the remainder of the session, with no visible error to the user.

**Fix:** Distinguish permanent failures (e.g. `Pyro5.errors.CommunicationError` during a connection-refused) from transient ones, or at minimum log at a higher severity and do not remove the entry unless it fails a configurable number of consecutive times. For the academic scope a simpler approach is acceptable: catch only `ConnectionRefusedError` / `OSError` as permanent and let other exceptions (timeout) be retried on next broadcast.

---

### WR-04: Player name length mismatch between client (`maxLength=20`) and server (`max 50`)

**File:** `frontend/src/pages/CreateGame.tsx:83`, `frontend/src/pages/JoinGame.tsx:119`, `frontend/src/pages/JoinByCode.tsx:116` vs `server/game_server.py:161`

**Issue:** All three input fields use `maxLength={20}`, but the server validates `len(player_name) > 50` and raises `ValueError` for names exceeding 50 characters. A name between 21 and 50 characters can only be submitted programmatically (bypassing the HTML attribute), but any player who does so will be accepted by the server while the UI would have blocked them. More importantly, if the validation was intended to be 20 characters, the server is wrong; if it was intended to be 50, the inputs are wrong. The mismatch means the boundaries are not consistently enforced and the behaviour under bypass is undefined from the client's perspective (the bridge will propagate the `ValueError` as an unhandled exception rather than a clean `{"error": ...}` response).

**Fix:** Align both to the same value. If 20 is the product decision, update `game_server.py:161` to `len(player_name) > 20`. If 50, update all three `maxLength` attributes. Also wrap the `ValueError` from input validation in `create_game`/`join_game` as a returned `{"error": str}` dict rather than letting it propagate as a Pyro5 exception.

---

### WR-05: `leave_game` does not unregister the player's callback from `EventBroadcaster`

**File:** `server/game_server.py:294-353`

**Issue:** When a player leaves, their entry is removed from the `GameSession.players` list and `session.host_id` is updated if needed. However, `self.broadcaster.callbacks` is never cleaned up in `leave_game`. The departed player's callback URI remains registered in the broadcaster. On the next broadcast (e.g. another player joining), `EventBroadcaster.broadcast` will attempt to deliver to the departed player, fail (their browser is disconnected), print an error, and then remove the entry — but this causes every subsequent broadcast to produce a spurious failed delivery and log noise until the cleanup happens.

**Fix:** Add `self.broadcaster.callbacks.pop(player_id, None)` (or a dedicated `unregister_callback` method) inside the `leave_game` lock block, immediately after removing the player from `session.players`:

```python
target_session.players = [p for p in target_session.players if p.player_id != player_id]
self.broadcaster.unregister_callback(player_id)   # add this
```

---

### WR-06: `start_game` O(n×m) linear scan through all sessions and players — no player-to-session index

**File:** `server/game_server.py:268-276` (also `leave_game:313-321`)

**Issue:** Both `start_game` and `leave_game` find a player's session by iterating over every session and every player in each session. With a small player count (2–4) this is functionally fine today, but the same pattern is also used in `leave_game`, which is called on every disconnect. If many sessions accumulate (e.g. lingering "IN_PROGRESS" sessions that never call `leave_game` for all players), this scan grows unboundedly. More critically, a logic error exists: there is no index from `player_id → session`, so if the same `player_id` UUID somehow appears in two sessions (impossible with UUIDs in practice, but the code would silently use whichever session happens to be iterated first).

**Fix:** Maintain a `_player_to_room: dict[str, str]` (player_id → room_code) that is updated in `create_game`, `join_game`, and `leave_game`. Replace the linear scans with O(1) lookups. This is a straightforward refactor:

```python
self._player_to_room: dict = {}   # in __init__

# in create_game (inside lock):
self._player_to_room[player_id] = room_code

# in join_game (inside lock):
self._player_to_room[player_id] = room_code

# in leave_game (inside lock):
room_code = self._player_to_room.pop(player_id, None)
if room_code is None:
    return False
session = self.sessions.get(room_code)
```

---

## Info

### IN-01: Module-level `toastCounter` is a mutable singleton — shared across HMR reloads in dev

**File:** `frontend/src/pages/Lobby.tsx:20`

**Issue:** `let toastCounter = 0` is declared at module scope. In production this is fine (single page load). In Vite HMR during development, module-level state survives hot reloads, so the counter will keep incrementing across component remounts, making toast IDs non-sequential in dev. This is a minor dev-experience issue only.

**Fix:** Use `useRef` inside the component for a cleaner pattern: `const toastCounterRef = useRef(0)` and increment with `++toastCounterRef.current`.

---

### IN-02: `JoinGame` link on Landing page navigates to `/join` but `App.tsx` defines that route as a full form

**File:** `frontend/src/pages/Landing.tsx` — no direct link to `/join` exists; the Landing page only navigates via code to `/join/:code`. However `App.tsx:6` imports `JoinGame` for the `/join` route, which has no pre-filled code. This route is never linked from the UI — there is no "browse open sessions" button. The `/join` route is dead code from a navigation perspective.

**Fix:** Either add a "Entrar por Código" button on the Landing page that navigates to `/join`, or remove the `/join` route and the `JoinGame.tsx` page if the Landing page's inline code form (which routes to `/join/:code`) is the intended entry point.

---

### IN-03: `FLASK_SECRET_KEY` falls back to a random value on every restart — invalidates all existing sessions

**File:** `bridge/bridge.py:32`

**Issue:** `os.urandom(24).hex()` is called at module load time. Every bridge restart generates a new secret key, invalidating any Flask session cookies from the previous run. For this project sessions are managed via Socket.IO (not Flask cookies), so the impact is low. However, the comment is misleading: if any Flask-signed cookies are ever added, this will silently break them on restart.

**Fix:** Document the intentional rotation behaviour in a comment, or set a fixed dev-mode key in a `.env` file (keeping it out of version control). For production use a stable secret set via the `FLASK_SECRET_KEY` environment variable.

---

_Reviewed: 2026-05-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
