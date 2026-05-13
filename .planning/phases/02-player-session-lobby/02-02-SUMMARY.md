---
phase: 02-player-session-lobby
plan: "02"
subsystem: bridge, frontend
tags: [flask-socketio, react, typescript, vite, socket.io, pyro5, lobby]

requires:
  - phase: 02-01
    provides: GameServer session methods (create_game, join_game, start_game, leave_game)
  - phase: 01-rpc-infrastructure-callback-pipeline
    provides: EventBroadcaster, BridgeCallbackReceiver base, get_game_server_proxy()

provides:
  - bridge/bridge.py session Socket.IO handlers (create_game, join_game, start_game, disconnect)
  - BridgeCallbackReceiver.on_player_joined, on_game_started, on_host_changed via Pyro5 callbacks
  - Flask catch-all SPA route serving frontend/dist
  - React+TypeScript Vite frontend with 5 lobby-flow pages (Landing, CreateGame, JoinGame, JoinByCode, Lobby)
  - Real-time player_joined broadcast received by all lobby members without page refresh
  - Room isolation via Flask-SocketIO join_room + _sid_to_player mapping

affects: [03-game-loop, 04-hints-guesses, UI-SPEC]

tech-stack:
  added:
    - vite@8.0.12
    - react@19.2.6
    - react-dom@19.2.6
    - react-router@7.15.0
    - socket.io-client@4.8.3
    - typescript@~5.x
    - "@vitejs/plugin-react@^6.0.1"
    - tailwindcss@^3.x
  patterns:
    - _sid_to_player dict maps socket sid → player_id (T-02-07: prevents client-supplied fake IDs)
    - BridgeCallbackReceiver callback methods use socketio.emit(to=room_code) for room isolation
    - Socket.io-client singleton with autoConnect: false (explicit connect in page components)
    - Vite proxy /socket.io → http://localhost:5000 with ws: true for dev-mode WebSocket upgrade

key-files:
  created:
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/tsconfig.json
    - frontend/index.html
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/socket.ts
    - frontend/src/pages/Landing.tsx
    - frontend/src/pages/CreateGame.tsx
    - frontend/src/pages/JoinGame.tsx
    - frontend/src/pages/JoinByCode.tsx
    - frontend/src/pages/Lobby.tsx
    - frontend/src/components/PlayerListItem.tsx
  modified:
    - bridge/bridge.py (session handlers, room isolation, catch-all route, 3 new callback methods)

key-decisions:
  - "@vitejs/plugin-react upgraded to ^6.0.1 — v4.x only supports Vite ≤7; Vite 8 requires v6"
  - "global _cb_uri removed from __main__ scope — global statement only valid inside functions; module-level assignment sufficient"
  - "_cb_uri declared as plain string (no type annotation) to avoid annotated name conflict with module-level assignment"
  - "Room isolation via Flask-SocketIO join_room per T-02-09 — events never broadcast globally"

patterns-established:
  - "Bridge room isolation: join_room(room_code) in create_game/join_game handlers; socketio.emit uses to=room_code"
  - "Sid tracking: _sid_to_player[request.sid] = player_id on join; .pop(request.sid, None) on disconnect"
  - "Flask catch-all: two @app.route decorators on serve_spa() function, after all socketio.on handlers"
  - "Frontend localStorage: player_id, room_code, is_host, max_turns persisted for lobby state on refresh"

deviations:
  - "@vitejs/plugin-react bumped from planned ^4.5.2 to ^6.0.1 — blocking incompatibility with Vite 8"
  - "global _cb_uri declaration removed as bugfix — Python SyntaxError at module scope"

self-check: PASSED
---

## What Was Built

Extended bridge.py with complete session Socket.IO handlers and three new BridgeCallbackReceiver callback methods. Scaffolded a full React+TypeScript Vite frontend with 5 lobby-flow pages connected via a socket.io-client singleton.

## Verification Results

All 4 automated E2E scenarios passed via python-socketio SimpleClient:
- Cenário 1: create_game returns valid room_code (6-char [A-Z0-9]) and is_host=True ✓
- Cenário 2: player_joined broadcast received by host without page refresh (real-time callback) ✓
- Cenário 3: join after game started returns {"error": "jogo em andamento"} ✓
- Cenário 4: non-host start_game returns success=False; host returns success=True ✓
- npm run build exits 0 with no TypeScript errors; frontend/dist/index.html generated ✓

## Issues Encountered

1. `@vitejs/plugin-react` version conflict — planned ^4.5.2 incompatible with Vite 8; upgraded to ^6.0.1 (non-breaking, same API)
2. `global _cb_uri` inside `if __name__ == "__main__":` raised SyntaxError — removed declaration since module-level variable needs no global statement
