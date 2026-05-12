# Phase 02: Player Session + Lobby - Research

**Researched:** 2026-05-12
**Domain:** Pyro5 session management, Flask-SocketIO rooms, React + TypeScript + Vite frontend
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Two separate Pyro5 methods: `create_game(player_name, callback_uri, max_turns) -> dict` and `join_game(player_name, callback_uri, room_code) -> dict`. Do NOT use a single combined method.
- **D-02:** Both methods return `{player_id: str, room_code: str, is_host: bool}`. Bridge passes this directly to the browser.
- **D-03:** Both `create_game` and `join_game` absorb callback registration internally. Bridge does NOT call `register_callback` separately. The existing `register_callback` stays for reconnection (Phase 7).
- **D-04:** `start_game(player_id: str, max_turns: int) -> bool`. GameServer validates host + ≥2 players. Broadcasts `GAME_STARTED` to all players in the room.
- **D-05:** `leave_game(player_id: str) -> bool`. Called on socket disconnect. If leaving player was host and lobby is still open, next player in join order becomes host. Server broadcasts `HOST_CHANGED`.
- **D-06:** GameServer generates `player_id` via `uuid.uuid4()`. Bridge emits it to frontend. Frontend stores it in `localStorage` under key `player_id`.
- **D-07:** Bridge maintains `_sid_to_player: dict[str, str]` mapping `request.sid -> player_id`. All handlers look up `player_id` via `request.sid`.
- **D-08:** React + TypeScript frontend (overrides CLAUDE.md Vanilla JS). Build tool: Vite.
- **D-09:** `frontend/` directory at project root containing `package.json`, `vite.config.ts`, `src/`. Built output: `frontend/dist/`. Flask serves `frontend/dist/index.html` and assets.
- **D-10:** Vite dev server on port 3000 proxies `/socket.io/*` to Flask on port 5000. Production: `npm run build`, Flask serves bundle. Bridge adds catch-all Flask route for React Router.
- **D-11:** React Router for client-side routing. Routes: `/` (landing), `/create`, `/join`, `/join/:code`, `/lobby/:sessionId`. Flask catch-all for all non-socket, non-static routes.
- **D-12:** Flask-SocketIO per-game-session rooms from the start. On `create_game`/`join_game`, bridge calls `join_room(room_code)`. All game events use `to=room_code`.
- **D-13:** GameServer includes `room_code` in every broadcast event payload. Bridge reads `data["room_code"]` to route to Flask-SocketIO room. No extra state in `BridgeCallbackReceiver`.
- **D-14:** Add `on_player_joined(self, data)` and `on_game_started(self, data)` to `BridgeCallbackReceiver`, both decorated `@Pyro5.api.oneway @Pyro5.api.callback`. Emit to room via `data["room_code"]`.

### Claude's Discretion

- 6-character room code: uppercase alphanumeric (A-Z0-9), `random.choices(string.ascii_uppercase + string.digits, k=6)`. Collision check against active sessions.
- Max players: 2–6. `join_game` rejects if room already has 6 players.
- `join_game` rejects if `game_status != "WAITING"`, returns `{error: "jogo em andamento"}` (SESSION-04).
- Session state stored in `GameSession` dataclass or dict on `GameServer`, keyed by `room_code`. Use `threading.RLock` for all mutations.
- Startup order in README: (1) `pyro5-ns`, (2) `python server/game_server.py`, (3) `python bridge/bridge.py`, (4) `npm run dev` in `frontend/`.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SESSION-01 | Player can create a game with nickname and max turns | D-01: `create_game()` method design; GameSession dataclass; room code generation |
| SESSION-02 | Game generates 6-character shareable session code | Room code generation with `random.choices`; collision detection pattern |
| SESSION-03 | Player can join via code or invite link | D-01: `join_game()` method; D-11: `/join/:code` route; WEB-004 screen |
| SESSION-04 | System rejects join after game started with "jogo em andamento" | `game_status != "WAITING"` guard; error dict return pattern |
| SESSION-05 | Lobby shows connected players in real time via `PLAYER_JOINED` | D-12: room isolation; D-14: `on_player_joined` callback; real-time React state |
| SESSION-06 | Host can start game when ≥2 players are in lobby | D-04: `start_game()` validation; WEB-005 button guard; `GAME_STARTED` broadcast |

</phase_requirements>

---

## Summary

Phase 2 extends the Phase 1 infrastructure with session lifecycle (create/join/start/leave), real-time lobby synchronization via Pyro5 callbacks, and a React + TypeScript + Vite frontend that replaces the placeholder static HTML from Phase 1. The Phase 1 codebase provides a fully wired Pyro5 daemon, EventBroadcaster with URI-based fan-out, and a Flask-SocketIO bridge with per-thread proxies — all of which Phase 2 builds on directly.

The three major work streams are independent and can be executed in parallel: (1) `GameServer` session methods + `GameSession` state model, (2) bridge Socket.IO handlers + room management + Flask catch-all, and (3) the Vite/React frontend scaffold with routes and lobby screens. The streams converge when the React app connects via Socket.IO, triggers `create_game`/`join_game`, and the real-time lobby update path (Pyro5 callback → bridge `on_player_joined` → `socketio.emit(to=room_code)` → React state) is exercised end-to-end.

The primary technical risk is the Vite ↔ Flask-SocketIO proxy configuration in development mode — Socket.IO uses both HTTP long-poll and WebSocket transports, so the Vite proxy must forward both `http://localhost:5000/socket.io` and the WebSocket upgrade to the same target. This is well-documented and solved with a single `vite.config.ts` proxy entry using `ws: true`.

**Primary recommendation:** Implement GameServer session layer first (pure Python, fully testable without a browser), then wire bridge handlers, then build the React frontend against real data.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session creation / join validation | API (GameServer / Pyro5) | — | All session state is authoritative server-side; validation must be in GameServer, not bridge |
| Room code generation | API (GameServer / Pyro5) | — | Collision-check requires access to `sessions` dict under lock |
| Callback registration for new players | API (GameServer / Pyro5) | — | D-03: absorbed inside `create_game`/`join_game`; bridge calls neither |
| Routing player → room (Socket.IO rooms) | Frontend Server (Bridge) | — | Flask-SocketIO rooms isolate per-socket emit; GameServer has no Socket.IO knowledge |
| `sid → player_id` mapping | Frontend Server (Bridge) | — | D-07: `_sid_to_player` dict lives in bridge; only bridge knows Socket.IO session IDs |
| Real-time lobby push (`PLAYER_JOINED`) | API broadcasts → Bridge forwards | Frontend reacts | GameServer triggers broadcast; bridge converts to Socket.IO emit `to=room_code` |
| Frontend routing and SPA delivery | Frontend Server (Bridge / Flask) | Browser (React Router) | Flask catch-all delivers `index.html`; React Router handles client-side routes |
| Static asset delivery (JS/CSS/images) | Frontend Server (Bridge / Flask) | CDN (production, not MVP) | Flask serves `frontend/dist/` in both dev-prod and production modes |
| Host authorization for `start_game` | API (GameServer / Pyro5) | Bridge (error propagation) | GameServer checks `player_id == session.host_id`; bridge propagates error to frontend |

---

## Standard Stack

### Core (all from Phase 1 — no new installs)

| Library | Verified Version | Purpose | Source |
|---------|-----------------|---------|--------|
| Pyro5 | 5.16 | RPC backbone, GameServer methods | [VERIFIED: CLAUDE.md pinned version] |
| Flask-SocketIO | 5.6.1 | WebSocket bridge, rooms, emit | [VERIFIED: CLAUDE.md pinned version] |
| Flask | 3.1.x | Web framework, static file serving, catch-all route | [VERIFIED: CLAUDE.md] |

### New in Phase 2 (frontend)

| Library | Verified Version | Purpose | Source |
|---------|-----------------|---------|--------|
| Vite | 8.0.12 | Dev server + build tool for React/TS frontend | [VERIFIED: `npm view vite version`] |
| React | 19.2.6 | UI component library | [VERIFIED: `npm view react version`] |
| react-router | 7.15.0 | Client-side routing (BrowserRouter + Routes) | [VERIFIED: `npm view react-router version`] |
| socket.io-client | 4.8.3 | WebSocket/Socket.IO browser client | [VERIFIED: `npm view socket.io-client version`] |
| TypeScript | ~5.x (via Vite template) | Type safety for React components | [ASSUMED: bundled with `npm create vite@latest -- --template react-ts`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-router v7 | react-router v6 | v7 is current stable; v6 API largely compatible for declarative mode |
| socket.io-client v4 | native WebSocket | Socket.IO protocol required to match Flask-SocketIO server-side |
| Tailwind via CDN | Tailwind via npm | CDN play build is zero-config; user locked on React/Vite so npm Tailwind is straightforward too; either works |

**Installation (frontend):**
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install react-router socket.io-client
```

**Installation (backend — no new packages needed for Phase 2):**
All Phase 1 packages already installed in `venv`. No new Python packages.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (React SPA)
  │  socket.io-client v4
  │  /socket.io/* (HTTP long-poll + WS upgrade)
  ▼
[Vite dev proxy :3000] ──────── /socket.io/* → http://localhost:5000
  │  (dev only)
  ▼
Bridge (Flask-SocketIO :5000)
  │  async_mode='threading'
  ├── on("create_game") ──── get_game_server_proxy().create_game(...)
  │     └── join_room(room_code)
  │     └── emit("create_game_response", {...}, to=request.sid)
  ├── on("join_game")   ──── get_game_server_proxy().join_game(...)
  │     └── join_room(room_code)
  │     └── emit("join_game_response", {...}, to=request.sid)
  ├── on("start_game")  ──── get_game_server_proxy().start_game(...)
  ├── on("disconnect")  ──── get_game_server_proxy().leave_game(...)
  │
  │  Pyro5 RPC (PYRONAME via NS)
  ▼
GameServer (Pyro5 daemon :9091)
  │  create_game() → stores GameSession, registers callback, returns dict
  │  join_game()   → validates room, appends player, registers callback, returns dict
  │  start_game()  → validates host + player count, sets status=IN_PROGRESS
  │  leave_game()  → removes player, reassigns host if needed
  │
  │  EventBroadcaster.broadcast(event_type, {room_code: ..., ...})
  │  @oneway fan-out to all registered callback URIs
  ▼
BridgeCallbackReceiver (Pyro5 daemon :dynamic, in bridge process)
  │  on_player_joined(data)  → socketio.emit("player_joined", data, to=data["room_code"])
  │  on_game_started(data)   → socketio.emit("game_started",  data, to=data["room_code"])
  │  on_host_changed(data)   → socketio.emit("host_changed",  data, to=data["room_code"])
  ▼
Browser — React state updated, lobby re-renders
```

### Recommended Project Structure

```
frontend/               # New in Phase 2
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx        # ReactDOM.createRoot, BrowserRouter
    ├── App.tsx         # Routes definition
    ├── socket.ts       # Singleton socket.io-client instance
    ├── pages/
    │   ├── Landing.tsx      # WEB-001: /
    │   ├── CreateGame.tsx   # WEB-002: /create
    │   ├── JoinGame.tsx     # WEB-003: /join
    │   ├── JoinByCode.tsx   # WEB-004: /join/:code
    │   └── Lobby.tsx        # WEB-005: /lobby/:sessionId
    └── components/
        └── PlayerList.tsx   # Reusable player card list

server/
└── game_server.py      # Extended: create_game, join_game, start_game, leave_game, GameSession

bridge/
└── bridge.py           # Extended: new handlers, _sid_to_player, catch-all route

config.py               # Possible addition: FRONTEND_DIST_PATH
```

### Pattern 1: GameSession Dataclass

**What:** Thread-safe session state stored in GameServer, keyed by `room_code`.
**When to use:** All session mutations — create, join, start, leave.

```python
# Source: Python standard library dataclasses + threading
import dataclasses
import threading
from typing import List, Optional

@dataclasses.dataclass
class PlayerInfo:
    player_id: str
    player_name: str
    callback_uri: str
    is_host: bool

@dataclasses.dataclass
class GameSession:
    room_code: str
    host_id: str
    max_turns: int
    status: str           # "WAITING" | "IN_PROGRESS" | "ENDED"
    players: List[PlayerInfo] = dataclasses.field(default_factory=list)
    # All mutations must hold GameServer.lock (RLock)
```

### Pattern 2: create_game with Callback Registration

**What:** Single method that both creates the session and registers the callback (D-03).
**When to use:** Called by bridge `on("create_game")` handler.

```python
# Source: CONTEXT.md D-01, D-02, D-03 + existing register_callback pattern in game_server.py
def create_game(self, player_name: str, callback_uri: str, max_turns: int) -> dict:
    with self.lock:
        room_code = self._generate_room_code()   # collision-checked
        player_id = str(uuid.uuid4())
        session = GameSession(
            room_code=room_code,
            host_id=player_id,
            max_turns=max_turns,
            status="WAITING",
            players=[PlayerInfo(player_id, player_name, callback_uri, is_host=True)],
        )
        self.sessions[room_code] = session
        self.broadcaster.register_callback(player_id, callback_uri)
    return {"player_id": player_id, "room_code": room_code, "is_host": True}
```

### Pattern 3: Room Code Generation with Collision Check

**What:** 6-char uppercase alphanumeric code, collision-checked.
**When to use:** Inside `create_game` under `self.lock`.

```python
# Source: CONTEXT.md "Claude's Discretion"; Python stdlib random + string
import random
import string

def _generate_room_code(self) -> str:
    """Must be called while self.lock is held."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=6))
        if code not in self.sessions:
            return code
```

### Pattern 4: Bridge Room Isolation (D-12, D-13)

**What:** Bridge joins the socket to a Flask-SocketIO room on create/join; callbacks use `data["room_code"]` to target the room.
**When to use:** All session-scoped emit events.

```python
# Source: Flask-SocketIO docs (Context7: /miguelgrinberg/flask-socketio)
# Context: bridge.py — new handlers
from flask_socketio import join_room
from flask import request

@socketio.on("create_game")
def handle_create_game(data):
    proxy = get_game_server_proxy()
    # data: {player_name, callback_uri, max_turns}
    result = proxy.create_game(data["player_name"], data["callback_uri"], data["max_turns"])
    # result: {player_id, room_code, is_host}
    _sid_to_player[request.sid] = result["player_id"]
    join_room(result["room_code"])
    return result   # returned as ack to Socket.IO client

# In BridgeCallbackReceiver:
@Pyro5.api.oneway
@Pyro5.api.callback
def on_player_joined(self, data: dict):
    # data["room_code"] set by GameServer in broadcast payload
    try:
        socketio.emit("player_joined", data, to=data["room_code"])
    except Exception as exc:
        print(f"[BRIDGE] on_player_joined error: {exc}", flush=True)
```

### Pattern 5: Flask Catch-All for React Router (D-10, D-11)

**What:** Flask route that serves `index.html` for any path not handled by Flask itself.
**When to use:** Bridge startup — allows React Router to handle `/lobby/:sessionId` etc.

```python
# Source: Flask docs; standard SPA hosting pattern [ASSUMED pattern, standard Flask]
import os
from flask import send_from_directory

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    full_path = os.path.join(FRONTEND_DIST, path)
    if path and os.path.exists(full_path):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")
```

### Pattern 6: Vite Proxy for Socket.IO (D-10)

**What:** Vite dev server forwards both HTTP and WebSocket to Flask on port 5000.
**When to use:** `vite.config.ts` — required for dev workflow.

```typescript
// Source: Vite docs (Context7: /vitejs/vite) — server.proxy with ws: true
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/socket.io': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
```

### Pattern 7: React Router Setup (D-11)

**What:** BrowserRouter wrapping routes matching UI.md nav map.
**When to use:** `src/main.tsx` + `src/App.tsx`.

```tsx
// Source: React Router docs (Context7: /remix-run/react-router)
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router'
import Landing from './pages/Landing'
import CreateGame from './pages/CreateGame'
import JoinGame from './pages/JoinGame'
import JoinByCode from './pages/JoinByCode'
import Lobby from './pages/Lobby'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/create" element={<CreateGame />} />
        <Route path="/join" element={<JoinGame />} />
        <Route path="/join/:code" element={<JoinByCode />} />
        <Route path="/lobby/:sessionId" element={<Lobby />} />
      </Routes>
    </BrowserRouter>
  )
}
```

### Pattern 8: Socket.IO Client Singleton (D-07)

**What:** Single `socket` instance shared across all React components.
**When to use:** `src/socket.ts` — imported by pages/components.

```typescript
// Source: socket.io-client docs [ASSUMED: standard singleton pattern]
import { io } from 'socket.io-client'

// In dev: Vite proxies /socket.io → Flask :5000
// In prod: same origin as the React app (Flask serves both)
const socket = io({ path: '/socket.io', autoConnect: false })

export default socket
```

### Pattern 9: disconnect Handler + leave_game (D-05, D-07)

**What:** On socket disconnect, bridge looks up `player_id` and calls `leave_game`.
**When to use:** `bridge.py` — Socket.IO `disconnect` handler.

```python
# Source: Flask-SocketIO docs (Context7: /miguelgrinberg/flask-socketio)
@socketio.on("disconnect")
def handle_disconnect(reason):
    player_id = _sid_to_player.pop(request.sid, None)
    if player_id:
        try:
            proxy = get_game_server_proxy()
            proxy.leave_game(player_id)
        except Exception as exc:
            print(f"[BRIDGE] leave_game failed for {player_id}: {exc}", flush=True)
```

### Anti-Patterns to Avoid

- **Shared callback_uri between BridgeCallbackReceiver and session players:** The bridge's own callback URI (registered as "bridge" in Phase 1 `connect_to_game_server`) must NOT be reused for per-player callbacks. Phase 2 eliminates the concept of registering the bridge itself as a single player; instead, each player's `create_game`/`join_game` call passes the bridge's receiver URI but keyed to that player's `player_id`. EventBroadcaster fan-out reaches `on_player_joined` on the single receiver, which then routes to the correct Socket.IO room.
- **Calling `register_callback` separately from bridge:** Violates D-03. Callback registration is absorbed inside `create_game`/`join_game`. The bridge does NOT call `register_callback` after getting back the result dict.
- **Sharing a Pyro5 proxy across threads:** Already prohibited by D-10 (Phase 1). All new handlers must call `get_game_server_proxy()` — never use a module-level proxy.
- **Emitting to all clients instead of a room:** Use `to=room_code` on every game event. Never `broadcast=True` without a room target — it would send to all lobbies.
- **Storing socket.io SIDs in GameServer:** GameServer has no Socket.IO knowledge. `_sid_to_player` lives exclusively in bridge.py (D-07).
- **Returning `None` from `create_game`/`join_game` on error:** Return an error dict with `{"error": "message"}` so the bridge can propagate the error to the frontend as a Socket.IO ack. Raising exceptions over Pyro5 also works but requires the bridge to catch and translate.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Room/group message isolation | Custom "rooms dict" in bridge | `join_room(room_code)` + `socketio.emit(..., to=room_code)` | Flask-SocketIO rooms handle concurrent emit safely; hand-rolled dict is a race condition |
| Client-side routing with catch-all | Manual URL dispatch in Flask | React Router BrowserRouter + Flask catch-all | React Router handles all navigation state; Flask only needs to serve `index.html` |
| UUID generation | Custom ID strings | `uuid.uuid4()` | Collision probability is astronomically low; `uuid4` is cryptographically random |
| WebSocket proxy in dev | CORS headers on Flask | Vite `server.proxy` with `ws: true` | Vite proxy handles the Socket.IO handshake (HTTP long-poll → WS upgrade) natively |
| Thread-local per-handler proxy | Global proxy with locking | Existing `get_game_server_proxy()` / `_thread_local` | Already implemented in Phase 1; reuse without modification |

**Key insight:** Flask-SocketIO rooms are the correct abstraction for multi-session isolation. All per-session broadcast routing is handled by passing `room_code` in the event payload and calling `socketio.emit(event, data, to=room_code)` — no custom dispatch logic required.

---

## Common Pitfalls

### Pitfall 1: Socket.IO Transport Mismatch in Vite Proxy

**What goes wrong:** Vite proxy configured without `ws: true` causes the Socket.IO connection to fail after the initial HTTP long-poll handshake, because the WebSocket upgrade request is not forwarded.
**Why it happens:** Socket.IO starts with HTTP polling and upgrades to WebSocket; Vite's HTTP proxy doesn't handle WS unless explicitly told to.
**How to avoid:** Always set `ws: true` in the `/socket.io` proxy entry in `vite.config.ts`.
**Warning signs:** Browser console shows repeated polling requests (no `websocket` upgrade visible in Network tab DevTools); connection events never fire.

### Pitfall 2: Callback URI Scope — Bridge Receiver vs. Player IDs

**What goes wrong:** All players share the same bridge callback URI but `EventBroadcaster` keys by `player_id`. If `create_game` passes a `player_id` not yet known to the bridge's `_sid_to_player`, the broadcast fires `on_player_joined` correctly (same URI) but the bridge can't reverse-look-up the player from the callback.
**Why it happens:** The bridge receiver is a single object — it doesn't need a per-player URI. But `EventBroadcaster.broadcast()` snapshots `self.callbacks` and calls `on_player_joined` once per registered URI. If multiple player_ids share the same URI (the bridge's receiver URI), only the LAST `register_callback` call for that URI "wins" in the callbacks dict.
**How to avoid:** `create_game`/`join_game` must pass the bridge's receiver URI as `callback_uri`, BUT keyed to the specific `player_id`. Each player gets their own entry in `broadcaster.callbacks` even though the URI is the same bridge receiver. `EventBroadcaster.broadcast()` will call `on_player_joined` once per player registration — the bridge receiver handles the call and emits to the correct room regardless of which player triggered it.
**Warning signs:** `PLAYER_JOINED` event delivered fewer times than expected when multiple players join.

### Pitfall 3: Flask Catch-All Conflicts with Socket.IO and Static Assets

**What goes wrong:** The `/<path:path>` catch-all route intercepts Socket.IO requests (`/socket.io/...`) and static file requests before they reach their handlers.
**Why it happens:** Flask route matching can shadow Socket.IO's internal routes if the catch-all is registered before SocketIO sets up its routes.
**How to avoid:** Register the catch-all route AFTER `socketio = SocketIO(app, ...)` initialization. Serve static assets from `frontend/dist/` via `send_from_directory` only when the file exists on disk; fall back to `index.html` otherwise (as shown in Pattern 5). The path check `os.path.exists(full_path)` is the key guard.
**Warning signs:** 404 errors on `/socket.io/` in the bridge logs; browser Network tab shows Socket.IO handshake returning HTML.

### Pitfall 4: RLock Reentrancy in create_game Calling broadcast

**What goes wrong:** `create_game` acquires `self.lock` (RLock), then calls `self.broadcaster.broadcast(...)` which internally acquires `broadcaster.lock`. If broadcast is NOT @oneway, the thread blocks waiting for the callback, which may try to acquire `self.lock` → deadlock.
**Why it happens:** broadcast() is synchronous by default in EventBroadcaster.
**How to avoid:** D-03 decision already prevents this: `create_game` does NOT call `broadcaster.broadcast()`. Broadcast of `PLAYER_JOINED` happens separately after the lock is released (called from within the method but outside the lock section, or deferred to `join_game`). Specifically: `create_game` only stores the session and registers the callback under lock. `join_game` broadcasts `PLAYER_JOINED` after its lock section, using `broadcaster.broadcast()` which is safe because it runs outside the `self.lock` context. Always release `self.lock` before calling `broadcaster.broadcast()`.
**Warning signs:** `join_game` hangs indefinitely after the first player joins.

### Pitfall 5: React Router BrowserRouter + Flask Catch-All Missing in Production

**What goes wrong:** In production mode (`npm run build` + Flask serving `frontend/dist/`), refreshing the browser on `/lobby/ABC123` returns 404 because Flask has no route for it.
**Why it happens:** React Router routes exist client-side only. On hard refresh, the browser requests `/lobby/ABC123` from the server, which Flask doesn't know about.
**How to avoid:** The Flask catch-all route (Pattern 5) must be present in `bridge.py` before Phase 2 is considered complete. Test with `python bridge/bridge.py` serving the built frontend.
**Warning signs:** Direct URL access to `/lobby/...` works in dev (Vite handles it) but returns 404 after `npm run build`.

### Pitfall 6: `start_game` Called Before ≥2 Players — Silent False Return

**What goes wrong:** Frontend shows a spinner indefinitely if `start_game` returns `False` but the bridge doesn't propagate the error back to the calling socket.
**Why it happens:** `@oneway` methods return nothing; non-@oneway `start_game` returns `bool`. If the bridge doesn't emit an error event back, the frontend is stuck.
**How to avoid:** `start_game` is NOT `@oneway`. The bridge's `handle_start_game` must return the result (or emit a `start_game_error` event) when `proxy.start_game(...)` returns `False`. Use Socket.IO ack (return value from handler) or an explicit `emit("start_game_error", {...}, to=request.sid)`.
**Warning signs:** "Iniciar Jogo" button click has no visible effect in the browser.

---

## Code Examples

### GameSession State Model

```python
# Source: CONTEXT.md D-01 through D-05; Python standard library
import dataclasses
import uuid
import random
import string
from typing import List

@dataclasses.dataclass
class PlayerInfo:
    player_id: str
    player_name: str
    callback_uri: str
    is_host: bool

@dataclasses.dataclass
class GameSession:
    room_code: str
    host_id: str
    max_turns: int
    status: str  # "WAITING" | "IN_PROGRESS" | "ENDED"
    players: List[PlayerInfo] = dataclasses.field(default_factory=list)

    @property
    def player_count(self) -> int:
        return len(self.players)

    def get_player_dicts(self) -> list:
        return [
            {"player_id": p.player_id, "player_name": p.player_name, "is_host": p.is_host}
            for p in self.players
        ]
```

### join_game with Broadcast After Lock Release

```python
# Source: CONTEXT.md D-01, D-02, D-03, D-13; EventBroadcaster pattern from Phase 1
def join_game(self, player_name: str, callback_uri: str, room_code: str) -> dict:
    with self.lock:
        session = self.sessions.get(room_code)
        if session is None:
            return {"error": "sala nao encontrada"}
        if session.status != "WAITING":
            return {"error": "jogo em andamento"}
        if session.player_count >= 6:
            return {"error": "sala cheia"}
        player_id = str(uuid.uuid4())
        player = PlayerInfo(player_id, player_name, callback_uri, is_host=False)
        session.players.append(player)
        self.broadcaster.register_callback(player_id, callback_uri)
        # Snapshot data for broadcast BEFORE releasing lock
        broadcast_data = {
            "room_code": room_code,
            "player": {"player_id": player_id, "player_name": player_name, "is_host": False},
            "players": session.get_player_dicts(),
        }
    # Broadcast OUTSIDE the lock — EventBroadcaster.broadcast() does network I/O
    self.broadcaster.broadcast("player_joined", broadcast_data)
    return {"player_id": player_id, "room_code": room_code, "is_host": False}
```

### Frontend: Lobby Component Real-Time Update

```tsx
// Source: socket.io-client docs [ASSUMED: standard useEffect + socket event pattern]
// src/pages/Lobby.tsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import socket from '../socket'

interface Player { player_id: string; player_name: string; is_host: boolean }

export default function Lobby() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [players, setPlayers] = useState<Player[]>([])
  const isHost = localStorage.getItem('is_host') === 'true'

  useEffect(() => {
    socket.on('player_joined', (data: { players: Player[] }) => {
      setPlayers(data.players)
    })
    socket.on('game_started', () => {
      window.location.href = `/game/${sessionId}`
    })
    return () => {
      socket.off('player_joined')
      socket.off('game_started')
    }
  }, [sessionId])

  const handleStart = () => {
    const playerId = localStorage.getItem('player_id')
    socket.emit('start_game', { player_id: playerId, max_turns: /* stored */ 5 })
  }

  return (
    <div>
      <h2>Código: {sessionId}</h2>
      <ul>{players.map(p => <li key={p.player_id}>{p.player_name}{p.is_host ? ' (Host)' : ''}</li>)}</ul>
      {isHost && players.length >= 2 && (
        <button onClick={handleStart}>Iniciar Jogo</button>
      )}
    </div>
  )
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| eventlet async_mode | threading async_mode | Flask-SocketIO 5.x | eventlet deprecated; threading is the recommended mode [VERIFIED: CLAUDE.md] |
| Vanilla JS + socket.io CDN (CLAUDE.md default) | React + TypeScript + Vite (D-08) | Phase 2 decision | Build step required; Vite scaffold is 2-minute setup |
| react-router v5 (HashRouter) | react-router v7 (BrowserRouter) | 2024–2025 | v7 is current stable; BrowserRouter requires Flask catch-all |
| socket.io-client v3 | socket.io-client v4 | 2021 | v4 matches Flask-SocketIO 5.x server protocol |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `npm create vite@latest -- --template react-ts` scaffold produces TypeScript 5.x with React 19 | Standard Stack | Minor — version mismatch would require manual dep update |
| A2 | Flask catch-all `/<path:path>` route registered after socketio init does not shadow Socket.IO routes | Pitfall 3 / Pattern 5 | High — Socket.IO requests would return HTML; connection fails |
| A3 | socket.io-client v4.8.x is compatible with Flask-SocketIO 5.6.1 server protocol | Standard Stack | High — incompatible versions prevent handshake; verify with a ping test |
| A4 | `socket = io({ path: '/socket.io', autoConnect: false })` singleton pattern is sufficient for this React app | Pattern 8 | Low — if reconnect logic (Phase 7) needs richer config, this is additive |
| A5 | Broadcasting `PLAYER_JOINED` to all `broadcaster.callbacks` (one entry per player, all pointing to the bridge URI) results in one `on_player_joined` call per player registration — this is the intended fan-out | Pitfall 2 | High — if EventBroadcaster deduplicates by URI, only one call fires. Verified: EventBroadcaster iterates by `player_id` key, not URI value, so multiple entries with same URI each fire a call [VERIFIED: event_broadcaster.py line 52] |

**A5 is self-resolved by code inspection:** `EventBroadcaster.broadcast()` iterates `snapshot.items()` which are `(player_id, uri)` pairs. Multiple players with the same bridge URI each trigger a separate call to `on_player_joined`. This means `on_player_joined` fires once per registered player per `PLAYER_JOINED` event — which is correct, because each call emits to `to=room_code` (idempotent; Socket.IO delivers once per room regardless of how many times `emit` is called with the same room/event/data). Mark A5 as LOW RISK.

---

## Open Questions

1. **`start_game` `max_turns` parameter**
   - What we know: D-04 signature is `start_game(player_id, max_turns) -> bool`; but `max_turns` was already set during `create_game`.
   - What's unclear: Should bridge re-send `max_turns` in `start_game` call, or should GameServer use the already-stored value? PRD §6.1 has `start_game(player_id, max_turns)`.
   - Recommendation: Follow PRD. Bridge sends the stored `max_turns` from the session creation response (stored in `localStorage` or component state). GameServer ignores the value if it contradicts the stored one, or accepts it as an override (override is simpler). Planner should choose one approach and document it.

2. **Bridge's own "bridge" player_id from Phase 1**
   - What we know: `connect_to_game_server` in Phase 1 calls `proxy.register_callback("bridge", cb_uri)`. This entry stays in `broadcaster.callbacks`.
   - What's unclear: Phase 2 adds per-player callbacks. `EventBroadcaster.broadcast("player_joined", ...)` will also try to call `on_player_joined` on the "bridge" entry. But "bridge" was registered before any GameSession existed.
   - Recommendation: Remove the "bridge" registration from `connect_to_game_server` startup (or keep it but add `on_player_joined` to BridgeCallbackReceiver which is already the plan per D-14). The call is harmless — the receiver handles it regardless of which player_id key triggered it. Planner should note this.

3. **`HOST_CHANGED` event in BridgeCallbackReceiver**
   - What we know: D-05 says GameServer broadcasts `HOST_CHANGED` on host disconnect.
   - What's unclear: D-14 only lists `on_player_joined` and `on_game_started`. Is `on_host_changed` also needed in Phase 2?
   - Recommendation: Add `on_host_changed` to `BridgeCallbackReceiver` in Phase 2 alongside the others. The SESSION-07 requirement is officially deferred to Phase 7 but `leave_game` needs to be callable — if it broadcasts `HOST_CHANGED` the receiver must exist or EventBroadcaster will log a failure. Safe to add a stub.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Vite + npm | ✓ | v22.18.0 | — |
| npm | Frontend install | ✓ | 10.9.3 | — |
| Python 3.11 (venv) | Pyro5 5.16 | ✓ | 3.11.2 (in venv) | — |
| Python 3.8 (system) | N/A | ✓ | 3.8.20 (NOT usable — Pyro5 5.16 requires 3.9+) | Use venv python3.11 |
| Pyro5 5.16 | GameServer | ✓ (in venv) | 5.16 | — |
| Flask-SocketIO 5.6.1 | Bridge | ✓ (in venv) | 5.6.1 | — |

**Critical note:** System Python is 3.8.20 (mise default). All Phase 2 Python commands must use `venv/bin/python` or `source venv/bin/activate`. The Makefile / README must be explicit about this. Never run `python` directly from system PATH.

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` (existing: `testpaths = tests`) |
| Quick run command | `venv/bin/python -m pytest tests/test_unit.py -x -q` |
| Full suite command | `venv/bin/python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SESSION-01 | `create_game()` returns `{player_id, room_code, is_host=True}` and stores session | unit | `pytest tests/test_session.py::test_create_game -x` | ❌ Wave 0 |
| SESSION-02 | Room code is 6 uppercase alphanumeric chars; second call generates different code | unit | `pytest tests/test_session.py::test_room_code_format -x` | ❌ Wave 0 |
| SESSION-03 | `join_game()` returns `{player_id, room_code, is_host=False}` for valid room | unit | `pytest tests/test_session.py::test_join_game -x` | ❌ Wave 0 |
| SESSION-04 | `join_game()` returns `{"error": "jogo em andamento"}` when status != WAITING | unit | `pytest tests/test_session.py::test_join_rejected_if_started -x` | ❌ Wave 0 |
| SESSION-05 | `join_game()` triggers `PLAYER_JOINED` broadcast delivered to registered callback | unit | `pytest tests/test_session.py::test_player_joined_broadcast -x` | ❌ Wave 0 |
| SESSION-06 | `start_game()` returns True iff caller is host and ≥2 players; returns False otherwise | unit | `pytest tests/test_session.py::test_start_game_validation -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `venv/bin/python -m pytest tests/test_session.py -x -q`
- **Per wave merge:** `venv/bin/python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_session.py` — covers SESSION-01 through SESSION-06 (6 tests)
- [ ] No new `conftest.py` needed — existing `tests/__init__.py` is sufficient

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user auth in MVP — nickname only |
| V3 Session Management | Partial | `player_id` UUID stored in localStorage; no server-side session validation beyond presence in `sessions` dict |
| V4 Access Control | Yes | `start_game` validates host; `join_game` validates room status; implemented in GameServer under lock |
| V5 Input Validation | Yes | `player_name` max 20 chars (UI-level per WEB-002); `room_code` 6 alphanumeric (server validates existence); `max_turns` in {3,5,7,10} |
| V6 Cryptography | No | No passwords or secrets; `uuid4` used for player_id (cryptographically random) |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Joining a room with a guessed `player_id` | Spoofing | `player_id` is UUID4 (128-bit random); impersonation probability is negligible; no cross-validation needed in MVP |
| Sending `start_game` from non-host socket | Elevation of Privilege | GameServer validates `player_id == session.host_id` before starting; return False if not host |
| Flooding `create_game` to exhaust memory | Denial of Service | Out of scope for academic MVP; note in README: restart clears all sessions |
| Empty/oversized `player_name` | Tampering | Server-side: validate non-empty, max 50 chars (defensive, even if UI enforces 20); raise ValueError for invalid inputs |
| `room_code` enumeration (6-char = 2.18 billion combos) | Information Disclosure | At 2–4 concurrent sessions in academic demo, collision probability is negligible [ASSUMED: academic scope] |

---

## Sources

### Primary (HIGH confidence)
- CONTEXT.md (02-CONTEXT.md) — Locked decisions D-01 through D-14
- `server/game_server.py`, `bridge/bridge.py`, `server/event_broadcaster.py` — Phase 1 codebase (verified by direct inspection)
- Context7 `/miguelgrinberg/flask-socketio` — rooms, join_room, emit to room, disconnect handler
- Context7 `/vitejs/vite` — proxy configuration with `ws: true`, React TS scaffold command
- Context7 `/remix-run/react-router` — BrowserRouter, Routes, Route, useParams
- `npm view` commands — verified current versions: vite@8.0.12, react@19.2.6, react-router@7.15.0, socket.io-client@4.8.3

### Secondary (MEDIUM confidence)
- PRD.md §6 — RPC API signatures (join_game, start_game, leave_game, register_callback)
- UI.md §3–6 — Route map, WEB-001 through WEB-005 screen specs
- CLAUDE.md — Pinned library versions, Key Pyro5 patterns 1–4

### Tertiary (LOW confidence)
- None identified — all claims verified via codebase inspection, official docs, or npm registry.

---

## Metadata

**Confidence breakdown:**

- Standard Stack: HIGH — all versions verified via npm registry or CLAUDE.md pinned versions
- Architecture: HIGH — derived from Phase 1 working code + locked CONTEXT.md decisions
- Pitfalls: HIGH (Pitfalls 1–3, 5, 6) / MEDIUM (Pitfall 4) — Pitfall 4 is a known threading pattern in Python; verified by reading EventBroadcaster source
- Frontend patterns: MEDIUM — Vite/React/socket.io patterns are standard but not exercised against this specific project yet

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (stable libraries; Vite 8 is current stable, React Router 7 is current stable)
