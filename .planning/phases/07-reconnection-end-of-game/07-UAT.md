---
status: complete
phase: 07-reconnection-end-of-game
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md]
started: 2026-05-16T00:00:00Z
updated: 2026-05-16T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. In-Game Chat Panel
expected: Open the game screen during an active game. A chat panel is visible below the game action area. It has a gray left border (not a game accent color), a text input labeled "Mensagem de chat", and a submit button labeled "Enviar mensagem". When no messages exist the panel shows "Nenhuma mensagem ainda. Seja o primeiro!". Type a message and submit — all connected players see it appear in the chat list in real time, with sender name and timestamp (HH:MM).
result: pass

### 2. Browser Reload Reconnection
expected: With 2+ players in an active game, reload Player A's browser tab. Player A briefly sees a reconnecting state, then the game screen restores fully (same image, same turn phase) within ~5 seconds. Player A remains in the player list on both screens. No error or blank screen occurs. The bridge terminal logs a line like "[BRIDGE] reconnect_game: player ... reconnected to room ...".
result: pass

### 3. Grace-Period Disconnect
expected: With 2+ players in an active game, close Player A's tab and reopen it within 5 seconds. Player B does NOT see a "player left" notification at any point during this sequence. Then close Player A's tab and wait more than 5 seconds without reconnecting — Player B sees a "player left" toast notification appear (bottom-right corner, red left border).
result: pass

### 4. Post-Game Navigation
expected: Play through all turns of a game (or use a 1-turn quick game). When the final turn scoring completes, all players are automatically navigated to /postgame/:roomCode without manual action. The post-game screen loads and shows a podium with player rankings (at least 1st place visible).
result: pass

### 5. Per-Turn Score Table
expected: On the post-game screen, there is a score breakdown table. Columns include: player name, one column per turn (Turno 1, Turno 2, …), and a Total column. Each cell shows that player's points for that turn. All players who participated appear as rows.
result: pass

### 6. Post-Game Vote Bar
expected: On the post-game screen, a 30-second vote countdown timer/bar is visible. The bar starts at full width and shrinks over 30 seconds. The bar color changes: purple/accent (#6366f1) when >10s remain, yellow/warning (#eab308) at ≤10s, and red/destructive (#ef4444) at ≤5s. Two vote buttons are visible ("Continuar com novos objetos" / "Encerrar jogo" or similar).
result: pass
note: "Initially failed (TurnMachine game_ended broadcast before _start_vote caused nav without vote state). Fixed by filtering game_ended in GameScreen.handleGameEnded — only navigate on events with final_scores."

### 7. Vote Restart Path
expected: On the post-game screen, click "Continuar com novos objetos" on enough clients to reach majority (e.g., both players click it). All players navigate to /game/:roomCode and the game restarts with new images and a fresh turn counter. No manual refresh needed.
result: pass

### 8. Vote End Path
expected: On the post-game screen, either let the 30-second timer expire without reaching majority, OR have the majority vote "Encerrar jogo" (no). A "game ended" result banner appears. A 10-second countdown ("10… 9… 8…") is displayed. When the countdown reaches 0, all players navigate to the home page (/).
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
blocked: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Post-game screen shows a 30-second vote countdown bar and two vote buttons before the game-ended state"
  status: failed
  reason: "User reported: pós-jogo vai direto para 'Partida encerrada. Obrigado por jogar! Redirecionando em 6...' sem mostrar a barra de votação de 30s nem os botões de voto"
  severity: major
  test: 6
  root_cause: |
    TurnMachine.broadcaster.broadcast("game_ended", ...) fires BEFORE calling on_game_ended()
    (turn_machine.py:211). Since on_game_ended is wired to _start_vote() in Phase 7, the
    sequence is: (1) game_ended broadcast → GameScreen.handleGameEnded → navigate to PostGame
    WITHOUT vote state, (2) _start_vote() broadcasts vote_started → arrives after GameScreen
    unmounts → no handler registered → event lost. PostGame mounts with navState.voteActive=false,
    vote UI never shows. 30s later _resolve_vote broadcasts game_ended with final_scores →
    PostGame shows "Partida encerrada".
  artifacts:
    - path: "server/turn_machine.py"
      issue: "line 211: broadcasts game_ended before calling on_game_ended(), ordering breaks Phase 7 vote flow"
    - path: "frontend/src/pages/GameScreen.tsx"
      issue: "handleGameEnded (line 242) navigates to PostGame without vote state when it should ignore TurnMachine's intermediate game_ended"
  missing:
    - "GameScreen.handleGameEnded must ignore game_ended events without final_scores (TurnMachine intermediate) and only navigate on post-vote game_ended (has final_scores)"
    - "OR: TurnMachine must not broadcast game_ended when _start_vote() is the on_game_ended callback"
  debug_session: ""
