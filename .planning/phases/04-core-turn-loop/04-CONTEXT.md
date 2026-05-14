# Phase 4: Core Turn Loop - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

A full, playable turn is possible: each player receives a unique object image at ROUND_START, submits a one-word hint during HINT_PHASE (revealed to all only when GUESS_PHASE starts), submits one guess against one other player's object during GUESS_PHASE, and scores are calculated and broadcast during SCORING_PHASE. The React frontend gains inline action panels that appear per phase. Exact-match guessing only (synonym arbitration is Phase 6).

Requirements in scope: HINT-01, HINT-02, HINT-03, HINT-04, GUESS-01, GUESS-02, GUESS-04, GUESS-05, IMAGE-01, IMAGE-02, IMAGE-03, SCORE-01, SCORE-02, SCORE-03, SCORE-04, SCORE-05

</domain>

<decisions>
## Implementation Decisions

### Turn State Structure
- **D-01:** Per-turn game data lives in a new `TurnState` dataclass in `server/turn_state.py`. `TurnMachine` holds `self.current_turn_state: TurnState`. Keeps phase-machine concerns (timing, generation counter) separate from game-data concerns (hints, guesses, scores).
- **D-02:** `TurnMachine` creates a fresh `TurnState(turn_number, player_ids)` when it transitions into `HINT_PHASE` (both at game start and at each new turn). Previous turn state is discarded at that moment.
- **D-03:** `TurnState` fields:
  - `hints_submitted: dict[str, str]` — maps player_id → hint word (empty string if not submitted before timer)
  - `guesses_made: dict[str, str]` — maps guesser_id → target_player_id (one per guesser, enforces GUESS-05)
  - `correct_guesses: list[str]` — ordered list of guesser_ids who guessed correctly, in arrival order (for tiered scoring)
  - `image_assignments: dict[str, str]` — maps player_id → object_name for this turn (canonical answer for guess arbitration)

### Hint Phase Behavior
- **D-04:** Hints are **blind** during HINT_PHASE. `HINT_RECEIVED` broadcast tells all players that a player submitted a hint (sealed envelope) — it does NOT include the hint word.
- **D-05:** `HINT_RECEIVED` payload includes `hints_count` (how many submitted so far) and `total_players` so the UI can show "2/4 hints received" without revealing who submitted.
- **D-06:** When TurnMachine transitions to `GUESS_PHASE`, the `PHASE_CHANGED` broadcast payload includes the full `hints_submitted` dict — all hints revealed at once as the phase starts. No separate `HINTS_REVEALED` event needed.
- **D-07:** If a player does not submit before the HINT_PHASE timer expires, their entry in `hints_submitted` is set to `""` (empty string). No penalty. (HINT-03)
- **D-08:** HINT_PHASE auto-advances when all players have submitted (`hints_count == total_players`) OR the timer expires. (HINT-04)

### Guess Attempt Policy
- **D-09:** **One attempt total per turn.** A player submits one word against one target (GUESS-05). Once `guesses_made[player_id]` is set, any further `submit_guess()` call from that player returns `{"error": "already_guessed"}`. The bridge/UI disables the guess input after first submission.
- **D-10:** `submit_guess()` rejects self-targeting: if `player_id == target_player`, returns `{"error": "cannot_guess_own_object"}`. Frontend should also hide the player's own entry from the target dropdown.
- **D-11:** A player can pass their turn with `skip_guess(player_id)` (GUESS-02) — sets `guesses_made[player_id] = None` to mark the slot as used without recording a target.

### Image Bank
- **D-12:** Images live in `server/images/` (or `static/images/` accessible via Flask). A `server/images/manifest.json` maps `{filename: object_name}`, e.g., `{"apple.jpg": "apple", "bicycle.png": "bicycle"}`. Server loads this at startup.
- **D-13:** At `ROUND_START` (or when HINT_PHASE starts), the server randomly picks one unique image per player (shuffle without replacement from available pool) and records the assignment in `TurnState.image_assignments`. An `OBJECT_ASSIGNED` event is sent to each player privately (targeted Socket.IO emit, not broadcast) containing the Flask static image URL and the object name. (IMAGE-02)
- **D-14:** Images are served as Flask static files. The Pyro5 layer never transmits image bytes. (IMAGE-03)

### Scoring
- **D-15:** Scoring is calculated when TurnMachine enters `SCORING_PHASE`. The server reads `TurnState.correct_guesses` (ordered arrival list) and `TurnState.image_assignments` to apply tiered rules (SCORE-01 through SCORE-03). Result is broadcast via `SCORE_UPDATED` with a per-player breakdown (turn delta + running total). (SCORE-04)
- **D-16:** Accumulated scores are stored in `GameSession` (dict player_id → total points). `get_scores()` returns these at any time. (SCORE-05)

### Frontend Scope
- **D-17:** Action inputs appear **inline in GameScreen** — the existing `/game/:roomCode` route from Phase 3. Phase-specific panels render conditionally based on current phase:
  - `HINT_PHASE`: text field for hint word + submit button + "N/M hints received" counter
  - `GUESS_PHASE`: revealed hints displayed as chips; target dropdown (excluding self) + word field + submit button
  - `SCORING_PHASE`: score panel showing turn delta per player + running total
  - Other phases: only the existing phase name + countdown from Phase 3
- **D-18:** No modal overlays in Phase 4 — that's Phase 8 (UI-06). Inline conditional rendering only.
- **D-19:** Score panel is inline within GameScreen. No separate `/score` route. Phase 8 adds delta animation (UI-07).

### Claude's Discretion
- Image assignment timing: whether `OBJECT_ASSIGNED` fires at the start of `ROUND_START` phase or at the start of `HINT_PHASE` — leave to planner. Either works as long as images arrive before HINT_PHASE input appears.
- Exact guess arbitration in Phase 4: case-insensitive exact match (strip whitespace, lowercase both sides). Phase 6 replaces this with WordNet. Leave implementation detail to planner.
- How many starter images to include in the image bank — leave to planner; minimum 8 (enough for 2 turns with 4 players without repeats).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §HINT-01 through HINT-04 — Hint submission rules, empty hint handling, auto-advance
- `.planning/REQUIREMENTS.md` §GUESS-01, GUESS-02, GUESS-04, GUESS-05 — Guess submission, skip, result broadcast, one-object-per-turn rule
- `.planning/REQUIREMENTS.md` §IMAGE-01 through IMAGE-03 — Image bank structure, distribution via static URL, no Pyro5 bytes
- `.planning/REQUIREMENTS.md` §SCORE-01 through SCORE-05 — Tiered scoring rules and broadcast
- `.planning/ROADMAP.md` §Phase 4 — 5 success criteria that must all be TRUE for phase completion

### Architecture
- `.planning/PROJECT.md` §Architecture Decision — Bridge WebSocket diagram; all broadcast paths go GameServer → EventBroadcaster → BridgeCallbackReceiver → socketio.emit()
- `.planning/PROJECT.md` §Key Decisions — locked decisions (@oneway, RLock, per-thread proxies, images via Flask static)

### Prior Phase Decisions
- `.planning/phases/03-phase-machine-timer/03-CONTEXT.md` — D-01/D-02 (TurnMachine structure), D-03 (broadcaster dependency injection), D-06 (TURN_END → HINT_PHASE from turn 2), D-08 (TurnMachine owns current_turn), phase sequence and config.PHASE_DURATIONS
- `.planning/phases/01-rpc-infrastructure-callback-pipeline/01-CONTEXT.md` — D-08 (@oneway), D-09 (broadcast methods must be @oneway), D-10 (per-thread proxy)
- `.planning/phases/02-player-session-lobby/02-CONTEXT.md` — D-12/D-13 (room-based Socket.IO routing via room_code in payload), D-14 (BridgeCallbackReceiver extension pattern)

### Technology
- `CLAUDE.md` §Key Pyro5 Patterns — patterns 1–4; images must never be serialized through Pyro5

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/turn_machine.py` — `TurnMachine` class with `_advance_to()`, `_compute_next()`, generation counter, RLock. Phase 4 extends this by having `_advance_to()` create a new `TurnState` on HINT_PHASE entry and pass `hints_submitted` in the GUESS_PHASE transition payload.
- `server/game_server.py` — `GameServer` class with `self.lock` (RLock), `self.broadcaster`, `self.sessions`. Phase 4 adds `submit_hint()`, `submit_guess()`, `skip_guess()` RPC methods, and extends `GameSession` with `accumulated_scores: dict`.
- `server/event_broadcaster.py` — `EventBroadcaster.broadcast(event_type, data)` for fan-out. New methods also use targeted delivery: bridge routes to a single player by adding `target_player_id` in payload alongside `room_code`.
- `bridge/bridge.py` — `BridgeCallbackReceiver` extension pattern (Phase 3 added `on_phase_changed`, `on_game_ended`). Phase 4 adds `on_hint_received`, `on_guess_result`, `on_score_updated`, `on_object_assigned`.
- `frontend/src/pages/GameScreen.tsx` — existing phase+countdown display. Phase 4 adds conditional action panels based on current phase state.
- `config.py` — `PHASE_DURATIONS` already has HINT_PHASE, GUESS_PHASE, SCORING_PHASE.

### Established Patterns
- All broadcast-triggering methods on `GameServer` must be `@Pyro5.api.oneway` (INFRA-03) or call broadcaster after releasing the lock.
- `BridgeCallbackReceiver` methods use `@Pyro5.api.oneway @Pyro5.api.callback` — all new `on_*` methods follow this pattern.
- Room routing: every broadcast payload includes `"room_code"` for bridge routing to the correct Socket.IO room.
- Targeted (private) delivery: bridge checks for `target_player_id` in payload and uses `socketio.emit(event, data, to=sid)` instead of `to=room_code`.
- Broadcast OUTSIDE the lock — timer callbacks and RPC methods must release RLock before calling `broadcaster.broadcast()`.

### Integration Points
- `server/turn_machine.py`: `_advance_to(HINT_PHASE)` → create `TurnState`, trigger `OBJECT_ASSIGNED` private events. `_advance_to(GUESS_PHASE)` → include `hints_submitted` in PHASE_CHANGED payload. `_advance_to(SCORING_PHASE)` → calculate scores, broadcast `SCORE_UPDATED`.
- `server/game_server.py`: New RPC methods `submit_hint(player_id, hint_word)`, `submit_guess(player_id, target_player, guess_word)`, `skip_guess(player_id)`.
- `server/images/`: New directory with `manifest.json` and image files. Loaded at `GameServer.__init__()`.
- `bridge/bridge.py`: New `BridgeCallbackReceiver` methods + bridge Socket.IO handlers for `submit_hint`, `submit_guess`, `skip_guess`.
- `frontend/src/pages/GameScreen.tsx`: Add phase-specific action panels. Listen for `hint_received`, `guess_result`, `score_updated`, `object_assigned` events.

</code_context>

<specifics>
## Specific Ideas

- `HINT_RECEIVED` payload: `{room_code, hints_count, total_players}` — no hint word, no submitter name during HINT_PHASE (sealed envelope pattern).
- `PHASE_CHANGED` to GUESS_PHASE payload: extend existing structure with `hints: {player_id: hint_word, ...}` dict.
- `OBJECT_ASSIGNED` payload (private, per-player): `{image_url: "/static/images/apple.jpg", object_name: "apple"}`.
- `GUESS_RESULT` payload: `{guesser_id, target_player_id, is_correct, room_code}`.
- `SCORE_UPDATED` payload: `{room_code, turn_number, scores: [{player_id, player_name, turn_delta, total}]}`.
- Case-insensitive exact match for guess arbitration: `guess.strip().lower() == object_name.strip().lower()`.

</specifics>

<deferred>
## Deferred Ideas

- Modal overlays per phase (HINT modal, GUESS modal, etc.) — deferred to Phase 8 per UI-06 in REQUIREMENTS.md.
- Synonym arbitration (GUESS-03) — deferred to Phase 6.
- "Who submitted" vs "how many submitted" visibility toggle — Phase 4 shows count only (no names). Could revisit in Phase 8 polish.

</deferred>

---

*Phase: 4-core-turn-loop*
*Context gathered: 2026-05-14*
