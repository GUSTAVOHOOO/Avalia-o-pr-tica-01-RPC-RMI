# Phase 2: Player Session + Lobby - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Players can create a room (getting back a 6-character code), share that code, join the room with a nickname, see each other in the lobby list in real time via Pyro5 callback push, and the host can start the game when ≥2 players are present.

Requirements in scope: SESSION-01, SESSION-02, SESSION-03, SESSION-04, SESSION-05, SESSION-06, SESSION-07

</domain>

<decisions>
## Implementation Decisions

### Session API (GameServer)
- **D-01:** Two separate Pyro5 methods: `create_game(player_name: str, callback_uri: str, max_turns: int) -> dict` and `join_game(player_name: str, callback_uri: str, room_code: str) -> dict`. Do NOT use a single combined method. Mirrors SESSION-01 (create) and SESSION-03 (join) exactly and makes validation straightforward.
- **D-02:** Both methods return a full dict: `{player_id: str, room_code: str, is_host: bool}`. Bridge passes this directly to the browser in one shot — no second round-trip.
- **D-03:** Both `create_game` and `join_game` absorb callback registration internally (equivalent to calling `register_callback` themselves). The bridge does NOT call `register_callback` separately for new players. The existing `register_callback` method stays on GameServer for reconnection use (Phase 7 / INFRA-08).
- **D-04:** `start_game(player_id: str, max_turns: int) -> bool` is a separate method. GameServer validates that the caller is the host and that ≥2 players are present; returns `False` (or raises) otherwise. After starting, broadcasts `GAME_STARTED` event to all players in the room.
- **D-05:** `leave_game(player_id: str) -> bool` must be called when a socket disconnects. SESSION-07: if the leaving player was the host and the lobby is still open (game not started), the next player in join order becomes the new host — server broadcasts `HOST_CHANGED` event.

### Player Identity
- **D-06:** GameServer generates `player_id` using `uuid.uuid4()` inside `create_game` / `join_game` and returns it. The bridge stores the received `player_id` in the player dict response, emits it to the frontend, and the frontend stores it in `localStorage` under key `player_id` (foundations for INFRA-08 reconnect in Phase 7).
- **D-07:** Bridge maintains a module-level dict `_sid_to_player: dict[str, str]` mapping `socket.request.sid → player_id`. Populated on successful `create_game` / `join_game`, cleared on Socket.IO `disconnect` event. All subsequent socket event handlers (e.g., `start_game`) look up `player_id` via `request.sid` from this dict.

### Frontend Stack
- **D-08:** React + TypeScript frontend. This overrides the CLAUDE.md Vanilla JS recommendation — user's explicit choice. Build tool: Vite.
- **D-09:** Project layout: `frontend/` directory at the project root containing `package.json`, `vite.config.ts`, `src/`. Built output goes to `frontend/dist/`. Flask serves `frontend/dist/index.html` and assets as static files.
- **D-10:** Dev workflow: Vite dev server on port 3000 proxies `/socket.io/*` to Flask on port 5000 (via `vite.config.ts` `server.proxy`). Production: `npm run build` in `frontend/`, then Flask serves the bundle. `bridge/bridge.py` must add a catch-all Flask route that serves `frontend/dist/index.html` for React Router to handle client-side routing.
- **D-11:** React Router is used for client-side routing. Routes match UI.md: `/` (landing), `/create`, `/join`, `/join/:code`, `/lobby/:sessionId`. Flask catch-all delivers `index.html` for all non-socket, non-static routes.

### Socket.IO Room Isolation
- **D-12:** Flask-SocketIO per-game-session rooms from the start. On successful `create_game` / `join_game`, the bridge calls `join_room(room_code)` for that socket. All game event emissions use `to=room_code`: `socketio.emit("player_joined", data, to=data["room_code"])`.
- **D-13:** GameServer includes `room_code` in every broadcast event payload (e.g., `{"room_code": "ABC123", "player": {...}}`). Bridge reads `data["room_code"]` to route to the correct Flask-SocketIO room. No extra state needed in `BridgeCallbackReceiver`.

### BridgeCallbackReceiver Extensions
- **D-14:** Add `on_player_joined(self, data: dict)` and `on_game_started(self, data: dict)` methods to `BridgeCallbackReceiver`, both decorated `@Pyro5.api.oneway @Pyro5.api.callback`. They emit to the correct room via `data["room_code"]`. EventBroadcaster calls the appropriate callback method for each event type.

### Claude's Discretion
- 6-character room code format: uppercase alphanumeric (A-Z0-9), generated with `random.choices` + `string.ascii_uppercase + string.digits`. Collision check against active sessions.
- Max players: 2–6 per PROJECT.md; `join_game` rejects if the room already has 6 players.
- `join_game` rejects if `game_status != "WAITING"` and returns an error dict `{error: "jogo em andamento"}` (SESSION-04).
- Session state stored in a `GameSession` dataclass or dict on `GameServer`, keyed by `room_code`. Use `threading.RLock` (already present) for all session mutations.
- Startup order in README: (1) `pyro5-ns`, (2) `python server/game_server.py`, (3) `python bridge/bridge.py`, (4) `npm run dev` in `frontend/`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §SESSION-01 through SESSION-07 — Full session management requirements with acceptance criteria
- `PRD.md` §6 (DEFINICAO DAS CHAMADAS RPC) — `join_game`, `start_game`, `leave_game`, `register_callback`, `get_game_state` API signatures (lines ~411–470)
- `PRD.md` §6.2 — `GameCallback` interface: `on_player_joined`, `on_game_started` callback method signatures (lines ~480–540)

### UI / Frontend
- `UI.md` §3 (Mapa de Navegação) — route map `/`, `/create`, `/join`, `/join/:code`, `/lobby/:sessionId`
- `UI.md` §4 Fluxos 1 and 2 — create-and-join flow and invite-link flow user journeys
- `UI.md` §5–6 — WEB-001 (Landing), WEB-002 (Criar Partida), WEB-003 (Entrar), WEB-004 (Entrada via Convite), WEB-005 (Lobby) screen specs

### Architecture
- `.planning/PROJECT.md` §Architecture Decision — Bridge WebSocket diagram (Browser ↔ WebSocket Bridge ↔ Pyro5 Daemon)
- `.planning/PROJECT.md` §Key Decisions — locked infrastructure decisions (threading mode, @oneway, per-thread proxies)
- `.planning/phases/01-rpc-infrastructure-callback-pipeline/01-CONTEXT.md` §decisions — D-01 through D-10 from Phase 1 (NS discovery, bridge startup coupling, per-thread proxy pattern, file layout)

### Roadmap / Success Criteria
- `.planning/ROADMAP.md` §Phase 2 — 4 success criteria that must all be TRUE for phase completion

### Technology (from CLAUDE.md)
- `CLAUDE.md` §Key Pyro5 Patterns — patterns 1–4 (single-instance server, bridge callback, NS usage, @oneway)
- `CLAUDE.md` §Version Summary — pinned versions: Pyro5==5.16, Flask-SocketIO==5.6.1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/game_server.py` — `GameServer` class with `__init__`, `lock` (RLock), `broadcaster` (EventBroadcaster). Phase 2 adds `create_game`, `join_game`, `start_game`, `leave_game` methods to this same class.
- `server/event_broadcaster.py` — `EventBroadcaster.broadcast(event_type, data)` and `send_to_player`. Phase 2 uses `broadcast()` for `PLAYER_JOINED` and `GAME_STARTED` events.
- `bridge/bridge.py` — `BridgeCallbackReceiver`, `get_game_server_proxy()` (per-thread), `_thread_local`, `socketio`. Phase 2 extends receiver with new callback methods and adds new Socket.IO event handlers.
- `config.py` — `NS_HOST`, `GAME_SERVER_PORT`, `BRIDGE_PORT`. Phase 2 may add `FRONTEND_DIST_PATH` constant.

### Established Patterns
- All Pyro5 broadcast methods on GameServer must be `@oneway` (D-09 Phase 1) — `start_game` if it triggers a broadcast must call broadcaster separately.
- Per-thread proxy via `_thread_local` — all new Socket.IO handlers must use `get_game_server_proxy()`.
- BridgeCallbackReceiver methods use `@Pyro5.api.oneway @Pyro5.api.callback` decorators — new callback methods follow this pattern.
- GameServer uses `self.lock` (RLock) for all state mutations — all new methods must acquire this lock.

### Integration Points
- `bridge.py` gets new Socket.IO handlers: `@socketio.on("create_game")`, `@socketio.on("join_game")`, `@socketio.on("start_game")`, `@socketio.on("disconnect")`
- `bridge.py` gets a Flask catch-all route to serve `frontend/dist/index.html` for React Router
- `game_server.py` gets session state (a dict or dataclass) and new session management methods
- `BridgeCallbackReceiver` gets `on_player_joined` and `on_game_started` — both must look up `room_code` from `data` to emit to the correct Flask-SocketIO room

</code_context>

<specifics>
## Specific Ideas

- UI.md routes should be followed as the structural reference, but minor navigation or flow adjustments are allowed if they improve usability or simplify the experience.
- React + TypeScript was explicitly chosen over Vanilla JS; UI.md screens (WEB-001 to WEB-005) are the design spec for the lobby flow.
- Vite proxy configuration in `vite.config.ts` must forward `/socket.io` to `http://localhost:5000` to avoid CORS issues during development.
- 6-character uppercase room code should be displayed prominently in the lobby and be copy-to-clipboard friendly.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-player-session-lobby*
*Context gathered: 2026-05-12*
