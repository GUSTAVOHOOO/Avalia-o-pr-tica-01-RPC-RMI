# Project Research Summary

**Project:** Jogo de Adivinhação Multijogador — RPC/Pyro5 (CC5SDT / UTFPR 2026-1)
**Domain:** Turn-based multiplayer word/image guessing game with distributed RPC backend
**Researched:** 2026-05-12
**Confidence:** HIGH (Pyro5/Flask-SocketIO stack), MEDIUM (Portuguese WordNet coverage)

---

## Executive Summary

This is a browser-based multiplayer party game where the core evaluation criterion is the correct use of Pyro5 RPC with bidirectional callbacks — not the quality of the UI. The recommended architecture uses three OS processes: a Pyro5 Name Server, a GameServer daemon holding all authoritative state, and a Flask-SocketIO bridge that translates between Pyro5 callbacks and browser WebSocket events. This three-process model is the only topology that avoids the async/sync mismatch that would arise from using FastAPI or aiohttp, and it maps directly onto the course's intent to demonstrate distributed object communication.

The single most important build constraint is: **the callback pipeline must be proven before any game logic is written.** Stage 2 of the architecture (running the BridgeCallbackReceiver daemon in the bridge process, registering it with the GameServer, and verifying a browser receives a server-pushed event without requesting it) de-risks the hardest integration point in the entire stack. Every game mechanic — phase transitions, scoring broadcasts, spy notifications, private hint delivery — depends on this pipeline. If this is built last or assumed to work, it will break during the demo.

The top three project killers, by likelihood and severity: (1) the Pyro5 callback deadlock from circular call chains or shared proxies across Flask-SocketIO handler threads; (2) Flask-SocketIO started with `async_mode='eventlet'` instead of `'threading'`, which monkey-patches stdlib sockets and silently corrupts Pyro5's blocking network calls; and (3) UI scope creep consuming development time before the RPC backend is validated — the course grades the distributed systems logic, not the CSS. Address all three in the first week.

---

## Key Findings

### Recommended Stack

The stack is fully pinned and verified against official sources. Pyro5 5.16 (Python 3.10+ required — 3.8 and 3.9 were dropped) is the required RPC framework. Flask-SocketIO 5.6.1 with `async_mode='threading'` is the correct bridge technology because it shares Pyro5's synchronous threading model; eventlet is deprecated per Flask-SocketIO's own documentation and gevent adds a C-extension with no benefit at this scale. The frontend is vanilla HTML/JS with the Socket.IO 4.x CDN client — no build pipeline, no npm, no React. NLTK + omw-1.4 handles synonym arbitration (fallback: the `wn` library with `own-pt:1.0.0` if Portuguese coverage is sparse). Images are served as Flask static files at `/images/<filename>`; raw image bytes must never be passed through Pyro5 (serpent encodes them as a base64 dict, not bytes).

**Core technologies:**
- **Pyro5 5.16**: RPC backbone, game server, bidirectional callbacks — required by course, latest stable
- **Flask-SocketIO 5.6.1 (threading mode)**: Bridge WebSocket to Pyro5 — only async mode that does not conflict with Pyro5's blocking sockets
- **simple-websocket**: WebSocket transport for Flask-SocketIO threading mode — required alongside Flask-SocketIO
- **NLTK + omw-1.4**: Synonym-aware guess arbitration in Portuguese — fallback to `wn` + own-pt if coverage fails
- **Pillow 12.1.0**: Image loading and format conversion — used for static image set preprocessing
- **socket.io-client 4.x (CDN)**: Browser WebSocket client — must match Flask-SocketIO server protocol version
- **serpent** (auto-installed with Pyro5): Default serializer — works for primitives and dicts; never pass custom class instances or raw bytes

### Expected Features

**Must have (table stakes):**
- Room code / lobby + player list + host-controlled start — players will not find each other without this
- Per-phase countdown timer with color feedback (green to yellow to red) — absence causes stalled games
- Automatic phase transitions on timer expiry — manual transitions leave games permanently stuck
- Real-time scoreboard with per-round delta — players need persistent context of who's winning
- "Whose turn / what phase" persistent indicator — party games collapse without this
- Reconnection + state restoration via `get_game_state()` RPC + localStorage player token — loss-on-refresh is a known UX failure
- Chat separated from game actions — confirmed as highest UX risk in PROJECT.md; must be distinct panels with distinct RPC paths
- Post-game results screen with winner + play-again vote

**Should have (differentiators worth 1-2 for demo quality):**
- Bluff mechanics in EXCHANGE phase — just omit server-side validation; UI surfaces "hint sent, cannot be verified"
- "Spy detected" public broadcast — one extra event, high social payoff for near-zero implementation cost
- Turn summary popup (per-SCORING phase) — clarifies what happened; high signal for evaluators
- Configurable turn count at room creation — already in PROJECT.md, near-zero cost

**Defer (scope risks for a 2-person semester team):**
- Reconnection / state restore — build last; highest risk feature, tackle only after core loop is stable
- Host auto-promotion on disconnect — document the limitation instead
- Spectator mode, persistent accounts, custom image upload, sound, AI players, mobile polish — all explicitly out of scope

### Architecture Approach

Three processes on a single machine. The Pyro5 Name Server runs on port 9090. The GameServer daemon runs on port 9091, holds all authoritative state under a single RLock, uses `instance_mode=single`, and fires callbacks via `@oneway` decorated methods to avoid blocking its own timer threads. The Flask-SocketIO Bridge runs on port 5000, hosts both the HTTP/WebSocket server and a BridgeCallbackReceiver Pyro5 daemon in a background thread; the BridgeCallbackReceiver calls `socketio.emit()` (the instance method, not the context-aware Flask import) when callbacks arrive from the GameServer. Pyro5 proxies in the bridge must never be shared across Flask-SocketIO handler threads — each handler creates its own proxy via a with-block or a `threading.local()` store.

**Major components:**
1. **Pyro5 Name Server (process 1)** — service discovery; maps `"game.server"` and `"game.bridge_callback"` to URIs
2. **GameServer (process 2)** — all game logic, authoritative state, phase timers, scoring, spy RNG; communicates outbound only via `@oneway` callbacks to the bridge
3. **Flask-SocketIO Bridge (process 3)** — two responsibilities in one process: (a) WebSocket session management and event routing to/from browsers; (b) BridgeCallbackReceiver daemon that receives Pyro5 callbacks and calls `socketio.emit()` thread-safely

### Critical Pitfalls

**TOP 3 PROJECT KILLERS — address in week 1:**

1. **Pyro5 callback deadlock (C1 + C2)** — circular call chains (GameServer to Bridge to GameServer) deadlock synchronous proxies; shared proxies across Flask-SocketIO handler threads corrupt the connection stream. Prevention: mark all GameServer broadcast methods `@oneway`; set `Pyro5.configure.COMMTIMEOUT = 10` to surface hangs as exceptions instead of silent freezes; use `threading.local()` proxy-per-thread in the bridge. Warning sign: game goes silent after first player joins, CPU drops to zero.

2. **Flask-SocketIO async mode conflict (C5)** — starting the bridge with `async_mode='eventlet'` (or the default, which may select eventlet) monkey-patches stdlib sockets and silently breaks Pyro5's blocking network calls. Callbacks arrive seconds late or not at all. Prevention: explicitly set `socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')` — hardcode this, never rely on defaults.

3. **UI scope creep before callback pipeline is proven (M4)** — the most common academic project failure mode. Beautiful UI, broken RPC logic, discovered in the final week. Prevention: hard rule — no HTML/CSS work until a 3-terminal test (Name Server + GameServer + CLI client) shows server-pushed callbacks arriving at a Python client without the client requesting them.

**Additional important pitfalls:**

4. **Callback daemon not started in bridge (C6)** — registering a callback object with GameServer does nothing if the bridge never starts a Pyro5 daemon to receive incoming calls on it. The GameServer gets `ConnectionRefusedError` on every broadcast; zero events reach the browser. Prevention: start `callback_daemon.requestLoop()` in a background thread before calling `game_server.register_callback(uri)`.

5. **Serpent serializes custom classes as dicts (C3)** — returning a `Player` or `GameState` dataclass from a Pyro5 method produces a plain dict on the receiving end. `AttributeError: 'dict' object has no attribute 'score'` appears in the bridge. Prevention: return only plain dicts, lists, and primitives from all Pyro5 methods — enforce this as a team convention from the start.

6. **Name Server broadcast fails at demo time (M5)** — `locate_ns()` uses UDP broadcast, which is blocked by OS firewalls and VPNs. Works on the dev machine, fails in front of the professor. Prevention: always start the Name Server with `pyro5-ns --host 127.0.0.1` and connect with `locate_ns(host="127.0.0.1")`. Or skip the Name Server entirely for demo: hardcode `PYRO:game.server@localhost:9091`.

7. **Portuguese WordNet sparse coverage (M3)** — NLTK's bundled OMW-PT may return zero synsets for common Brazilian Portuguese nouns (sofa, cadeira, mochila), causing the arbitration system to silently reject valid guesses. Prevention: use the `wn` library with `own-pt:1.0.0`; validate all game image words against the wordnet at startup and exclude any with zero synsets; always implement exact-match as a fallback.

---

## Implications for Roadmap

The feature dependency chain and the architecture build order converge on the same conclusion: the game cannot be built top-down (UI first) or bottom-up (all features, then integration). It must be built inside-out — core RPC infrastructure first, then the callback pipeline as a distinct validation milestone, then game state, then mechanics, then UI.

### Phase 1: RPC Infrastructure + Callback Pipeline

**Rationale:** Every other phase depends on the Pyro5 daemon, the bridge, and the callback pipeline working correctly. This is the highest-risk integration surface and the most common source of late-project failures. Must be proven with a terminal-only test before any other work starts.
**Delivers:** Three processes running (Name Server, GameServer skeleton, Bridge skeleton); `ping()` round-trip confirmed; BridgeCallbackReceiver daemon running; browser receives a server-pushed event without requesting it (the callback loop end-to-end test).
**Addresses (features):** None yet — this is infrastructure only.
**Avoids:** C1 (deadlock), C2 (shared proxy), C5 (async mode), C6 (daemon not started), M4 (UI scope creep).
**Research flag:** Standard patterns — Pyro5 official docs and chatbox example cover this exactly. No additional research needed.

### Phase 2: Player Session + Lobby

**Rationale:** The lobby loop is a prerequisite for everything game-related. Player identity (UUID token in localStorage), the session registry (sid to player_id map), room creation, join flow, and host-controlled start are all required before the phase machine can be built.
**Delivers:** Working lobby: create room, share code, players join, player list updates in real-time, host clicks start.
**Implements:** SessionRegistry, `join_game` / `leave_game` RPCs, `on_player_joined` / `on_player_left` callbacks, Socket.IO room management.
**Addresses (features):** Room code, player list, host-controlled start, minimum 2-player enforcement.
**Avoids:** M5 (test Name Server discovery before committing to the pattern).
**Research flag:** Standard patterns — well-documented Socket.IO room and session management.

### Phase 3: Phase Machine + Timer

**Rationale:** The phase machine is the backbone of the game. No mechanic (hints, guesses, exchange, spy, scoring) can be implemented until the state machine transitions reliably and timers fire and cancel correctly. This is identified in FEATURES.md as "the backbone" and in ARCHITECTURE.md as Stage 4.
**Delivers:** Full phase cycle (LOBBY to HINT to GUESS to EXCHANGE to SPY to SCORING to repeat) with server-side threading.Timer per phase; automatic timeout transitions; `on_phase_changed` callback updating all browser UIs.
**Implements:** `GameState` dataclass (internal server-only), `_start_phase_timer` / `_advance_phase` with generation counter, `on_phase_changed` callback.
**Addresses (features):** Per-phase countdown timer, automatic phase transitions, "whose turn / what phase" indicator.
**Avoids:** M1 (double transition — use generation counter from day one), M2 (release lock before broadcasting callbacks).
**Research flag:** Standard patterns — threading.Timer + generation counter is documented.

### Phase 4: Core Turn Loop (one working turn, exact match only)

**Rationale:** Build one complete turn end-to-end with the simplest possible mechanics before adding complexity. Exact-match guessing, image distribution via URL (not bytes), hint submission, and the SCORING broadcast. Validates the full data flow from browser to Bridge to GameServer to callback to browser.
**Delivers:** Playable (if limited) game: image assigned, player submits hint, players guess (exact match), scores updated, scoreboard visible.
**Implements:** `submit_hint`, `submit_guess` (exact match), image URL distribution via Flask static route, `on_hint_broadcast`, `on_guess_result`, `on_scores_updated`.
**Addresses (features):** Phase-specific action RPCs, real-time scoreboard, end-of-round score delta.
**Avoids:** C3 (return plain dicts only — enforce this here), C4 (images as URLs, never bytes).
**Research flag:** Standard patterns.

### Phase 5: EXCHANGE + SPY Mechanics

**Rationale:** Both mechanics slot into the existing phase machine without changing its structure. EXCHANGE is low-risk (just RPC call + private callback to two players + public notification to all). SPY is a server-side `random()` roll with two outcome branches. Implement these together since they share the same "private event to specific player" pattern.
**Delivers:** Full phase cycle with all four game mechanics active. Private hint delivery, bluff mechanic (no server validation needed), spy success/fail with public shame notification.
**Implements:** `request_exchange`, `accept_exchange`, `attempt_spy`, `on_exchange_request`, `on_private_hint`, `on_spy_result`, `on_spy_discovered`.
**Addresses (features):** Bluff mechanics, espionage risk/reward, spy-detected public notification.
**Avoids:** C1 (private events to specific SID, not broadcast — verify `socketio.emit(event, data, to=sid)` pattern works from callback thread).
**Research flag:** Standard patterns — private Socket.IO emit is documented.

### Phase 6: Synonym Arbitration (wn + own-pt)

**Rationale:** Isolated feature with independent risk. Build after the core guess flow works with exact match. If wordnet integration fails or takes longer than expected, the game is still playable with exact match as fallback — exact match can be the demo fallback if needed.
**Delivers:** `submit_guess` accepts synonyms ("car" scores for "automobile"); `on_guess_result` returns `{accepted, matched_word, similarity_score}` for inline browser feedback.
**Implements:** `is_synonym_or_match(guess, target)` using `wn` + own-pt with exact-match fallback; startup validation of all image words against wordnet.
**Addresses (features):** Synonym-aware arbitration differentiator.
**Avoids:** M3 (validate words at startup, not at runtime; have exact-match fallback always active).
**Research flag:** Needs validation — run `wn.words(word, pos='n', lang='pt')` on the full image word list before committing to this approach. If more than 20% of words return empty, change the word set.

### Phase 7: Reconnection + End-of-Game

**Rationale:** Highest-risk feature (ghost player matching, state restoration, edge cases). Deliberately deferred until the core game loop is stable. Build last to avoid it destabilizing earlier phases during development.
**Delivers:** Player reconnect with stored UUID token restores game state; end-of-game vote screen with final podium; "play again" resets server state.
**Implements:** `reconnect` Socket.IO event, `get_game_state(player_id)` RPC, `state_restore` browser event, `submit_vote`, `on_game_ended`.
**Addresses (features):** Reconnection/state restoration (table stakes), post-game results screen.
**Avoids:** Ghost player bug (new sid, same player_id — re-map in SessionRegistry, do not create new player).
**Research flag:** Moderate complexity — allocate 2x the testing time vs. other phases. Run the reconnect scenario with 3 browser tabs simultaneously.

### Phase 8: Chat + UI Polish

**Rationale:** Chat is independent of game state (its own RPC path, its own UI panel). Build last because it has zero dependencies on game mechanics and zero risk of breaking anything above it. UI polish is done here too — not before.
**Delivers:** Separate chat panel that cannot be mistaken for a game action input; final UI pass for the demo.
**Implements:** `send_chat`, `on_chat_message` callback, two-panel browser layout, clipboard copy for room code.
**Addresses (features):** Chat separation (confirmed UX risk), copy-to-clipboard invite.
**Avoids:** The chat/guess confusion UX failure mode — distinct panels, distinct labels, distinct submit buttons.
**Research flag:** Standard patterns — no research needed.

### Phase Ordering Rationale

- Phases 1-3 are infrastructure and cannot be reordered. Phase 1 (callback pipeline) is a hard prerequisite for Phase 2 (lobby) because the lobby's player-joined event is delivered via callback. Phase 2 (lobby) is a prerequisite for Phase 3 (phase machine) because the phase machine starts when the host triggers game start from the lobby.
- Phase 4 (core turn loop) must precede Phase 5 (exchange + spy) because EXCHANGE and SPY are variations on Phase 4's event patterns, not independent features.
- Phase 6 (wordnet) is isolated and could be done in parallel with Phase 5 by splitting the team, but the risk of wordnet coverage failure makes it safer to build after the core mechanic works with exact match.
- Phase 7 (reconnection) is deliberately last — it is the most edge-case-heavy feature and can destabilize state management if built while other things are still changing.
- The build order from FEATURES.md and ARCHITECTURE.md agree exactly — lobby, phase machine, core mechanics, reconnection is the dependency chain in both documents independently.

### Research Flags

**Phases needing validation during execution:**
- **Phase 6 (synonym arbitration):** Run a startup validation script on the full image word list before the implementation milestone. If `wn` returns sparse results for the chosen words, swap words — not libraries.
- **Phase 7 (reconnection):** Not a research gap but a testing gap — allocate 2x the testing time vs. other phases.

**Phases with standard patterns (no additional research needed):**
- Phase 1: Pyro5 chatbox example covers the callback daemon pattern exactly.
- Phases 2, 3, 4, 5, 8: All patterns documented in official Pyro5 and Flask-SocketIO docs.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via Context7 and official PyPI pages. Flask-SocketIO 5.6.1 confirmed Feb 2026. Pyro5 5.16 confirmed Dec 2025. |
| Features | HIGH | Feature list cross-validated against skribbl.io analysis, Codenames, netgames.io patterns. PRD decisions confirmed as correct by research. |
| Architecture | HIGH | Three-process topology validated against official Pyro5 docs + chatbox example. Threading rules confirmed via Pyro5 proxy thread-safety docs. |
| Pitfalls | HIGH (Pyro5), MEDIUM (Portuguese WordNet) | C1-C6 all trace to official docs or confirmed GitHub issues. M3 (WordNet coverage) needs runtime validation on the target word set. |

**Overall confidence:** HIGH

### Gaps to Address

- **Portuguese WordNet coverage for the specific image word set:** Cannot be confirmed without running the actual game words against `wn` + own-pt. Mitigation: build a 10-line validation script in Phase 6 before implementing arbitration. Have an exact-match-only fallback mode ready.
- **NLTK vs. `wn` library choice:** Research recommends `wn` + own-pt over NLTK's bundled OMW-PT for Brazilian Portuguese. Resolve at Phase 6 start by running the validation script with both and picking whichever covers more of the image word set.
- **Name Server vs. direct URI for demo:** Decide the approach at Phase 1 and document it; do not leave it as a last-minute discovery on demo day. Recommended: hardcode `--host 127.0.0.1` for the Name Server, or use direct URI `PYRO:game.server@localhost:9091`.
- **Timer visual smoothness:** Server-side `threading.Timer` drifts slightly under GIL pressure. Decide at Phase 3 whether to implement client-side countdown (tick client-side, re-sync on `phase_changed` events) for visual smoothness.

---

## Sources

### Primary (HIGH confidence)
- Pyro5 5.16 official docs — callback patterns, proxy thread safety, oneway, instance modes: https://pyro5.readthedocs.io/en/latest/
- Pyro5 chatbox example (reference implementation for callback daemon): https://github.com/irmen/Pyro5/tree/master/examples/chatbox
- Flask-SocketIO 5.6.1 docs — threading mode, background emit, eventlet retirement: https://flask-socketio.readthedocs.io/en/latest/
- Flask-SocketIO eventlet retirement discussion (GitHub #2037, 2026): https://github.com/miguelgrinberg/Flask-SocketIO/discussions/2037
- Pyro5 proxy thread safety ("One single thread 'owns' a proxy"): https://pyro5.readthedocs.io/en/latest/clientcode.html

### Secondary (MEDIUM confidence)
- OpenWordnet-PT coverage gaps (GitHub issue #134): https://github.com/own-pt/openWordnet-PT/issues/134
- `wn` Python library with own-pt:1.0.0 (52,670 synsets for PT): https://pypi.org/project/wn/
- NLTK omw-1.4 Portuguese support (lang='por'): https://www.nltk.org/howto/wordnet.html
- Multiplayer reconnection best practices: https://www.getgud.io/blog/how-to-successfully-create-a-reconnect-ability-in-multiplayer-games/
- skribbl.io design analysis (table stakes validation): https://mechanicsofmagic.com/2024/04/23/critical-play-skribbl-io-22/

### Tertiary (LOW confidence)
- Alpine.js as optional frontend upgrade (CDN, no build step): community sources, not validated for this specific Socket.IO + Flask-SocketIO combination

---
*Research completed: 2026-05-12*
*Ready for roadmap: yes*
