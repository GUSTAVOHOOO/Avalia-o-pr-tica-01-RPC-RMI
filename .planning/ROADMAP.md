# Roadmap: Jogo de Adivinhação Multijogador — RPC/Pyro5

## Overview

Eight phases built inside-out: core Pyro5 callback infrastructure first, then lobby, phase machine, the full turn loop, advanced mechanics (exchange + spy), synonym arbitration, reconnection + post-game, and finally UI polish + the academic report. Every phase produces a runnable, verifiable artifact. No HTML/CSS work until Phase 1 proves server-pushed callbacks arrive at a Python CLI client without the client requesting them.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: RPC Infrastructure + Callback Pipeline** - Three processes running; server-pushed Pyro5 callback arrives at CLI client without client requesting it (completed 2026-05-12)
- [x] **Phase 2: Player Session + Lobby** - Players create rooms, join via code, lobby list updates in real time, host starts game (completed 2026-05-13)
- [ ] **Phase 3: Phase Machine + Timer** - Full HINT→GUESS→EXCHANGE→SPY→SCORING cycle with auto-timeout transitions
- [ ] **Phase 4: Core Turn Loop** - One complete playable turn: image assigned, hints submitted, guesses scored, scoreboard updated
- [ ] **Phase 5: Exchange + Spy Mechanics** - Private hint exchanges and espionage with public discovery notifications
- [ ] **Phase 6: Synonym Arbitration** - Portuguese WordNet synonym matching replaces exact-match-only guessing
- [ ] **Phase 7: Reconnection + End-of-Game** - State restoration on reconnect, post-game podium, play-again vote, chat
- [ ] **Phase 8: UI Polish + Technical Report** - Polished web UI across all screens and complete academic report

## Phase Details

### Phase 1: RPC Infrastructure + Callback Pipeline
**Goal**: Three OS processes (Name Server, GameServer, Bridge) run and communicate; a server-pushed Pyro5 callback arrives at a CLI client without the client having requested it
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06
**Success Criteria** (what must be TRUE):
  1. Running `pyro5-ns --host 127.0.0.1` followed by the GameServer and Bridge start scripts brings all three processes up without errors and GameServer registers itself under `game.server` in the Name Server
  2. A CLI test client discovers `game.server` via the Name Server (no hardcoded URI), calls `ping()`, and receives a response — confirming round-trip RPC works
  3. A 3-terminal smoke test (Name Server + GameServer + CLI client) shows a server-initiated event arriving at the CLI client as a Pyro5 callback without the client having polled or requested it — the BridgeCallbackReceiver daemon is running and registered
  4. Flask-SocketIO bridge starts with `async_mode='threading'` confirmed in startup log; each handler thread creates its own Pyro5 proxy (verified by logging proxy id per thread)
  5. Sending a test broadcast from the GameServer causes the event to appear in the bridge's Socket.IO emit log, confirming the full callback pipeline: GameServer `@oneway` → BridgeCallbackReceiver → `socketio.emit()`
**Plans:** 4/4 plans complete

Plans:
- [x] 01-01-PLAN.md — Project scaffold: venv (python3.11), pip install, requirements.txt, config.py, directory structure, pytest.ini, test stubs
- [x] 01-02-PLAN.md — Core RPC layer: GameServer (@expose, ping, register_callback), EventBroadcaster, unit tests for INFRA-01/02/03
- [x] 01-03-PLAN.md — Callback pipeline: broadcast_test() @oneway on GameServer, CLI test_client.py demo artifact
- [x] 01-04-PLAN.md — Flask-SocketIO bridge: BridgeCallbackReceiver, per-thread proxy, startup retry, test_per_thread_proxy, 3-terminal smoke test checkpoint

### Phase 2: Player Session + Lobby
**Goal**: Players can create a room, share a 6-character code, join the room, see each other in the lobby list in real time, and the host can start the game
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: SESSION-01, SESSION-02, SESSION-03, SESSION-04, SESSION-05, SESSION-06
**Success Criteria** (what must be TRUE):
  1. Player A creates a partida with a nickname and turn count; server returns a 6-character room code and the game is discoverable by code
  2. Player B joins using the room code and a different nickname; both Player A's and Player B's browser lobbies immediately show both players (real-time via `PLAYER_JOINED` callback, no page refresh)
  3. Attempting to join a room where the game is already in progress returns the message "jogo em andamento" and the player is not added
  4. The "Iniciar Jogo" button is visible and enabled only for the host and only when at least 2 players are in the lobby; clicking it transitions the server state and all clients receive the transition event
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — GameServer session layer: GameSession/PlayerInfo dataclasses, create_game, join_game, start_game, leave_game, 6 unit tests (SESSION-01 to SESSION-06)
- [x] 02-02-PLAN.md — Bridge + React frontend: session Socket.IO handlers, room isolation, BridgeCallbackReceiver extensions, Vite+React+TS scaffold, all 5 lobby-flow pages, 4-terminal smoke test checkpoint
**UI hint**: yes

### Phase 3: Phase Machine + Timer
**Goal**: The server drives a full WAITING → ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END cycle with per-phase timers that fire automatically
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: TURN-01, TURN-02, TURN-03, TURN-04
**Success Criteria** (what must be TRUE):
  1. After game start, each phase transition is broadcast to all connected clients via `PHASE_CHANGED` event with the new phase name and remaining seconds — no client action required
  2. Letting the timer expire on any phase advances the game to the next phase automatically; a log entry shows the generation counter prevented any double-advance
  3. Manually advancing a phase (test RPC call) cancels the current timer; the old timer does not fire after the phase has already moved on
  4. A full cycle from ROUND_START through TURN_END completes without deadlock or silent freeze when tested with two connected browser sessions
**Plans**: TBD

### Phase 4: Core Turn Loop
**Goal**: A full, playable turn is possible: each player receives a unique object image, submits a one-word hint visible to all, guesses another player's object, scores are calculated and broadcast, and the scoreboard updates
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: HINT-01, HINT-02, HINT-03, HINT-04, GUESS-01, GUESS-02, GUESS-04, GUESS-05, IMAGE-01, IMAGE-02, IMAGE-03, SCORE-01, SCORE-02, SCORE-03, SCORE-04, SCORE-05
**Success Criteria** (what must be TRUE):
  1. At ROUND_START each player's browser receives an `OBJECT_ASSIGNED` event containing a Flask static image URL (never raw bytes); the image renders in the player's secret panel
  2. A player submitting a hint causes `HINT_RECEIVED` to broadcast to all clients; a player who does not submit before timer expiry receives an empty string hint with no penalty
  3. A player submitting a correct exact-match guess receives `GUESS_RESULT` with `is_correct: true`; the same player cannot guess the same target again in the same turn (`GUESS-05`)
  4. At SCORING_PHASE the server calculates and broadcasts `SCORE_UPDATED` with a per-player breakdown following the tiered scoring rules (SCORE-01 through SCORE-03); `get_scores()` returns the same accumulated totals
  5. Completing two consecutive turns with two players produces correct cumulative scores with no race conditions observed in server logs
**Plans**: TBD
**UI hint**: yes

### Phase 5: Exchange + Spy Mechanics
**Goal**: Players can request and complete private hint exchanges during EXCHANGE_PHASE, and attempt to spy on active exchanges during SPY_PHASE, with correct probability, point penalty, and notification behavior
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: EXCHANGE-01, EXCHANGE-02, EXCHANGE-03, EXCHANGE-04, EXCHANGE-05, EXCHANGE-06, SPY-01, SPY-02, SPY-03, SPY-04, SPY-05
**Success Criteria** (what must be TRUE):
  1. Player A requests an exchange with Player B; Player B receives a private notification; Player B accepts; both players submit a private hint word; server broadcasts a public `EXCHANGE_COMPLETED` event that does not contain the hint content; only the two participants receive the private hints via a targeted Socket.IO emit
  2. A player attempting a second exchange in the same turn receives an error; a player attempting to spy on their own exchange is rejected
  3. Over 30 repeated spy attempts in test, approximately 30% result in `SPY_DISCOVERED` broadcast with the spy's name and -10 point penalty applied; the remaining ~70% deliver the two private hints silently to the spy with no public event
  4. Player B rejects an exchange request; no private hints are exchanged and no public `EXCHANGE_COMPLETED` is broadcast
**Plans**: TBD

### Phase 6: Synonym Arbitration
**Goal**: Guess arbitration accepts Portuguese synonyms and near-matches via `wn` + own-pt, with exact-match as permanent fallback, and the image word set is validated against WordNet at server startup
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: GUESS-03
**Success Criteria** (what must be TRUE):
  1. At server startup a validation script runs against the full image word list; any word with zero synsets in `wn` + own-pt is logged and excluded from distribution, ensuring no silent arbitration failure at runtime
  2. A guess that is a WordNet synonym or meets the Wu-Palmer threshold for the target word returns `GUESS_RESULT` with `is_correct: true` and `matched_word` populated; a clearly wrong guess returns `is_correct: false`
  3. When `wn` returns `None` for either word, the system falls back to exact-match comparison and does not crash or silently accept the guess
**Plans**: TBD

### Phase 7: Reconnection + End-of-Game
**Goal**: A player who reloads the page can restore their session using a stored UUID; post-game shows a final podium with per-turn scores; a play-again vote either restarts or ends the game; chat works throughout the session
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: INFRA-07, INFRA-08, SESSION-07, POSTGAME-01, POSTGAME-02, POSTGAME-03, POSTGAME-04, CHAT-01, CHAT-02, CHAT-03, CHAT-04
**Success Criteria** (what must be TRUE):
  1. A player who reloads the browser tab during an active game has their UUID read from localStorage, calls `get_game_state()`, and receives the current game state; they rejoin the correct Socket.IO room and receive subsequent callbacks without being treated as a new player
  2. If the host disconnects in the lobby, the next player in join order is automatically promoted to host and can start the game
  3. A player whose callback repeatedly fails is removed from the active callback list; other players continue to receive events uninterrupted
  4. After the last turn, all players see a results screen with a podium (top 3) and a per-turn score table; a 30-second play-again vote completes correctly (majority → new round with new images; no majority or majority-no → game ends)
  5. Chat messages sent via `send_chat()` are broadcast to all players via `on_chat_message`; the chat input is in a visually distinct panel, separate from all game action inputs, with distinct labels and submit buttons
**Plans**: TBD
**UI hint**: yes

### Phase 8: UI Polish + Technical Report
**Goal**: The web interface is complete and polished across all screens; the academic report is written with diagrams, screenshots, installation instructions, and RPC justification
**Mode:** mvp
**Depends on**: Phase 7
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10, REPORT-01, REPORT-02, REPORT-03, REPORT-04
**Success Criteria** (what must be TRUE):
  1. Landing page, create-room screen, lobby, main game screen, and results screen all load correctly and display their content without console errors; the invite link code is copyable to clipboard
  2. The phase timer renders with three color states: green (>10s remaining), yellow (≤10s), red (≤5s); transitions are visible to the player without page reload
  3. A player presented with the game screen cannot mistake the chat input for the hint or guess input; the two zones use distinct colors, labels, and submit buttons, and a usability check with a fresh user confirms zero chat/action confusion
  4. The reconnection banner appears (amber) when Socket.IO loses connection and turns red if offline for more than a few seconds; it disappears automatically on reconnect
  5. The technical report contains: (a) a Pyro5 introduction with technology comparison and justification, (b) an architecture diagram showing the three-process model, (c) at least two RPC sequence diagrams (callback registration and game event delivery), (d) screenshots of the running application, and (e) complete installation and execution instructions
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. RPC Infrastructure + Callback Pipeline | 4/4 | Complete   | 2026-05-12 |
| 2. Player Session + Lobby | 2/2 | Complete   | 2026-05-13 |
| 3. Phase Machine + Timer | 0/TBD | Not started | - |
| 4. Core Turn Loop | 0/TBD | Not started | - |
| 5. Exchange + Spy Mechanics | 0/TBD | Not started | - |
| 6. Synonym Arbitration | 0/TBD | Not started | - |
| 7. Reconnection + End-of-Game | 0/TBD | Not started | - |
| 8. UI Polish + Technical Report | 0/TBD | Not started | - |
