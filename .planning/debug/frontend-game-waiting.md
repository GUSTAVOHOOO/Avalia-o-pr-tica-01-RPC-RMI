---
status: resolved
trigger: "Frontend fica em 'Aguardando acao do servidor' enquanto o jogo avanca no Docker"
created: 2026-05-14
updated: 2026-05-14
---

## Symptoms

- Docker compose services are running healthy.
- Bridge logs show `phase_changed` events progressing through game phases.
- Game screen body still displays a generic waiting message.
- A browser joining `/game/:roomCode` after a phase broadcast can remain on `Conectando...` until the next phase event.

## Current Focus

- hypothesis: GameScreen renders a placeholder for every non-null phase, and bridge `join_room` does not return current session phase state.
- test: Build frontend and run focused backend/session tests after patch.
- expecting: Re-entering a game page receives the current phase immediately, and the UI shows phase-specific status.
- next_action: Rebuild Docker containers when it is acceptable to reset the current in-memory game session.

## Evidence

- 2026-05-14: `docker compose logs bridge` shows phase broadcasts reaching room `1QYJM2`.
- 2026-05-14: `frontend/src/pages/GameScreen.tsx` renders `Aguardando acao do servidor...` for all active phases.
- 2026-05-14: Browser opened directly at `/game/1QYJM2` showed `Conectando...` with no console errors.

## Resolution

- root_cause: The game was progressing server-side, but the React game body was still a placeholder for every active phase. Re-entering the game screen also missed current phase state because `join_room` only joined the Socket.IO room and returned no snapshot.
- fix: `GameServer.get_session()` now includes current phase state when available; `bridge.join_room` returns that snapshot; `GameScreen` applies the snapshot and renders phase-specific status text.
- verification: `npm run build` passed; `python -m pytest tests/test_session.py tests/test_turn_machine.py` passed.
- files_changed: `server/game_server.py`, `bridge/bridge.py`, `frontend/src/pages/GameScreen.tsx`, `frontend/src/pages/GameScreen.css`
