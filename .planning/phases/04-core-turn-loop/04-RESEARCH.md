# Phase 4: Core Turn Loop - Research

**Researched:** 2026-05-14
**Domain:** Game turn mechanics — TurnState, hint/guess RPC methods, image bank, tiered scoring, React phase panels
**Confidence:** HIGH (all findings verified against the live codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Per-turn game data lives in a new `TurnState` dataclass in `server/turn_state.py`. `TurnMachine` holds `self.current_turn_state: TurnState`.
- **D-02:** `TurnMachine` creates a fresh `TurnState(turn_number, player_ids)` when it transitions into `HINT_PHASE`. Previous turn state is discarded.
- **D-03:** `TurnState` fields: `hints_submitted: dict[str, str]`, `guesses_made: dict[str, str]`, `correct_guesses: list[str]`, `image_assignments: dict[str, str]`.
- **D-04:** Hints are blind during HINT_PHASE. `HINT_RECEIVED` does NOT include the hint word.
- **D-05:** `HINT_RECEIVED` payload includes `hints_count` and `total_players`.
- **D-06:** PHASE_CHANGED to GUESS_PHASE includes full `hints_submitted` dict — revealed all at once.
- **D-07:** Player who does not submit before HINT_PHASE timer gets empty string — no penalty.
- **D-08:** HINT_PHASE auto-advances when all players submitted OR timer expires.
- **D-09:** One attempt total per turn. Second `submit_guess()` call returns `{"error": "already_guessed"}`.
- **D-10:** `submit_guess()` rejects self-targeting with `{"error": "cannot_guess_own_object"}`.
- **D-11:** `skip_guess(player_id)` sets `guesses_made[player_id] = None`.
- **D-12:** Images live in `server/images/` with `manifest.json` mapping `{filename: object_name}`. Server loads at startup.
- **D-13:** `OBJECT_ASSIGNED` sent privately per player (targeted Socket.IO emit) with Flask static image URL and object name.
- **D-14:** Images served as Flask static files. Pyro5 never transmits image bytes.
- **D-15:** Scoring calculated at SCORING_PHASE entry. Broadcast via `SCORE_UPDATED`.
- **D-16:** Accumulated scores stored in `GameSession` as `accumulated_scores: dict[str, int]`.
- **D-17:** Action inputs appear inline in GameScreen — no modal overlays.
- **D-18:** No modal overlays in Phase 4 — deferred to Phase 8.
- **D-19:** Score panel is inline within GameScreen. No separate `/score` route.

### Claude's Discretion

- Image assignment timing: whether `OBJECT_ASSIGNED` fires at `ROUND_START` or `HINT_PHASE` start — planner decides. Either works as long as images arrive before HINT_PHASE input appears.
- Exact guess arbitration in Phase 4: case-insensitive exact match (`guess.strip().lower() == object_name.strip().lower()`). Phase 6 replaces with WordNet.
- How many starter images to include — minimum 8 (enough for 2 turns with 4 players without repeats).

### Deferred Ideas (OUT OF SCOPE)

- Modal overlays per phase — deferred to Phase 8 (UI-06).
- Synonym arbitration (GUESS-03) — deferred to Phase 6.
- "Who submitted" visibility toggle — Phase 4 shows count only.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HINT-01 | Each player submits exactly one word via `submit_hint(player_id, hint_word)` | New RPC method on GameServer; guards against double-submit using `hints_submitted` dict |
| HINT-02 | Server broadcasts `HINT_RECEIVED` to all clients when any hint arrives | `EventBroadcaster.broadcast()` existing fan-out; new BridgeCallbackReceiver.on_hint_received |
| HINT-03 | Player who doesn't submit before timer gets empty string automatically | TurnMachine HINT_PHASE timer callback fills missing entries with `""` before transition |
| HINT-04 | Phase auto-advances when all players submitted OR timer expires | Both paths call `_advance_to("GUESS_PHASE")`; all-submitted path triggers immediately |
| GUESS-01 | Player submits guess via `submit_guess(player_id, target_player, guess)` | New RPC method; case-insensitive exact match against `image_assignments[target_player]` |
| GUESS-02 | Player can skip via `skip_guess(player_id)` | New RPC method; sets `guesses_made[player_id] = None` |
| GUESS-04 | Result broadcast via `GUESS_RESULT` with `is_correct: bool` | `broadcaster.broadcast()` after lock release; new BridgeCallbackReceiver.on_guess_result |
| GUESS-05 | One object attempt per turn per player | `guesses_made[player_id]` check at start of submit_guess; returns error if already set |
| IMAGE-01 | Server has image bank with filename→object_name mapping | `server/images/` directory + `manifest.json`; loaded once at GameServer.__init__() |
| IMAGE-02 | Server distributes unique image per player via `OBJECT_ASSIGNED` with Flask static URL | `broadcaster.send_to_player()` already exists; targeted per-player private delivery |
| IMAGE-03 | Images served as Flask static files, never via Pyro5 serialization | Flask static route already serves frontend; extend with `server/images/` static path |
| SCORE-01 | Tiered scoring: 1st +20, 2nd +15, 3rd +10, rest max(20-(N-1)*5, 5) | Computed from `correct_guesses` ordered list at SCORING_PHASE entry |
| SCORE-02 | Solo correct guesser gets +10 bonus | Special case: `len(correct_guesses) == 1` adds bonus |
| SCORE-03 | Object owner scoring: tiered based on how many guessed correctly | Computed from `len(correct_guesses)` against owner's player_id |
| SCORE-04 | Scores broadcast via `SCORE_UPDATED` with per-player breakdown | `broadcaster.broadcast("score_updated", ...)` at SCORING_PHASE entry |
| SCORE-05 | `get_scores(player_id)` returns accumulated totals at any time | New RPC method reading `GameSession.accumulated_scores` |

</phase_requirements>

---

## Summary

Phase 4 adds the game's data layer on top of the phase machine built in Phase 3. The core pattern is already established: `TurnMachine._advance_to()` is the single transition point — Phase 4 hooks into it to create `TurnState`, fire private image assignments, reveal hints, and calculate scores. `GameServer` gains three new RPC methods (`submit_hint`, `submit_guess`, `skip_guess`) and one query method (`get_scores`), all following the existing lock/broadcast-outside-lock pattern. `BridgeCallbackReceiver` gains four new `@oneway @callback` methods. `GameScreen.tsx` gains conditional action panels per phase.

The main complexity concentration is in `TurnMachine._advance_to()` — it must perform different side effects on different phase transitions (create TurnState on HINT_PHASE, add hints dict to PHASE_CHANGED payload on GUESS_PHASE, calculate and broadcast scores on SCORING_PHASE). This is a single method that currently builds a flat broadcast_data dict; it must be extended carefully without breaking the generation-counter / lock-outside-broadcast ordering.

**Primary recommendation:** Implement in layers — TurnState dataclass first (pure Python, no deps), then image bank + assignment logic, then hint/guess RPC methods, then scoring, then bridge/frontend. Each layer is independently testable before the next.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TurnState creation and mutation | API/Backend (GameServer + TurnMachine) | — | State is authoritative on server; clients receive deltas via events |
| Hint submission and blind broadcast | API/Backend (GameServer) | Bridge (relay only) | Business rule (blind during HINT_PHASE) enforced server-side |
| Hint revelation at GUESS_PHASE start | API/Backend (TurnMachine) | Frontend (display) | Reveal timing is server-controlled via PHASE_CHANGED payload extension |
| Guess arbitration | API/Backend (GameServer) | — | Correctness logic must be server-side to prevent client spoofing |
| Image bank management | API/Backend (GameServer + Flask static) | — | Server owns assignments; Flask serves bytes |
| Private image delivery | API/Backend (EventBroadcaster.send_to_player) | Bridge (route to SID) | Must be targeted per-player, not broadcast |
| Tiered score calculation | API/Backend (TurnMachine at SCORING_PHASE) | — | Needs `correct_guesses` ordered list only available on server |
| Score accumulation | API/Backend (GameSession.accumulated_scores) | — | Persistent within session lifetime on server |
| Phase action panels (UI) | Frontend (GameScreen.tsx) | — | Conditional rendering based on `currentPhase` state |
| Image display | Frontend (Browser) | CDN/Static (Flask) | Flask serves image bytes; browser renders |

---

## Standard Stack

### Core (already installed — no new packages needed for Phase 4 MVP)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pyro5 | 5.16 | RPC backbone — new methods added to existing exposed class | Required by course; already in use |
| Flask-SocketIO | 5.6.1 | WebSocket bridge — new handlers for submit_hint/submit_guess | Already running in threading mode |
| Flask | 3.1.3 | Serves image static files via `send_from_directory` | Already serving React SPA |
| React + TypeScript | Vite scaffold (existing) | Frontend phase panels | Already running |

**No new Python packages required.** Image serving uses Flask's existing `send_from_directory`. Scoring uses Python stdlib only.

### Image Bank

- **Format:** JPEG or PNG files in `server/images/`. Any common format Flask can serve.
- **Manifest:** `server/images/manifest.json` — plain JSON dict `{"filename.jpg": "objectname"}`.
- **Minimum pool:** 8 images (supports 2 turns × 4 players with no repeats per turn). Recommend 16+ for realistic play. [VERIFIED: D-12 from CONTEXT.md]

### Verification

Current installed versions confirmed by codebase inspection:
- `requirements.txt` pins: `Pyro5==5.16`, `Flask==3.1.3`, `flask-socketio==5.6.1`, `simple-websocket==1.1.0` [VERIFIED: requirements.txt]

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (Player A)                Browser (Player B)
     |                                  |
  submit_hint ──► WebSocket ──►   Bridge (Flask-SocketIO, threading)
                                        |
                               get_game_server_proxy()  [per-thread]
                                        |
                               Pyro5 RPC call: submit_hint(player_id, word)
                                        |
                               GameServer.submit_hint()
                                  │  acquire self.lock
                                  │  TurnState.hints_submitted[player_id] = word
                                  │  check if hints_count == total_players
                                  │  release self.lock
                                  │
                               broadcaster.broadcast("hint_received", {...})
                                  │
                               EventBroadcaster iterates callbacks
                                  ├─► Proxy(bridge_cb_uri).on_hint_received(data)
                                        │
                               BridgeCallbackReceiver.on_hint_received()
                                  └─► socketio.emit("hint_received", data, to=room_code)
                                        │
                               Browser A + Browser B receive "hint_received"
                               {hints_count: 1, total_players: 2}  [no hint word]

[GUESS_PHASE starts → PHASE_CHANGED payload includes hints dict → all hints revealed]

[SCORING_PHASE: TurnMachine._advance_to() calculates scores → SCORE_UPDATED broadcast]
```

### Recommended Project Structure

```
server/
├── turn_state.py        # NEW — TurnState dataclass (D-01 to D-03)
├── turn_machine.py      # EXTEND — _advance_to() hooks for HINT/GUESS/SCORING phases
├── game_server.py       # EXTEND — submit_hint(), submit_guess(), skip_guess(), get_scores()
├── event_broadcaster.py # UNCHANGED — send_to_player() already exists for private delivery
└── images/              # NEW — image bank
    ├── manifest.json    # NEW — {"apple.jpg": "apple", ...}
    ├── apple.jpg        # NEW — sample images (minimum 8)
    └── ...

bridge/
└── bridge.py            # EXTEND — 3 new Socket.IO handlers + 4 new BridgeCallbackReceiver methods

frontend/src/pages/
└── GameScreen.tsx       # EXTEND — add phase-conditional panels inline
```

### Pattern 1: TurnState dataclass (pure Python, no Pyro5 dependency)

```python
# Source: design from CONTEXT.md D-03, consistent with existing GameSession pattern
import dataclasses
from typing import Optional

@dataclasses.dataclass
class TurnState:
    turn_number: int
    player_ids: list  # ordered list for turn structure
    hints_submitted: dict = dataclasses.field(default_factory=dict)   # player_id → hint word (str)
    guesses_made: dict = dataclasses.field(default_factory=dict)      # guesser_id → target_player_id | None
    correct_guesses: list = dataclasses.field(default_factory=list)   # ordered by arrival
    image_assignments: dict = dataclasses.field(default_factory=dict) # player_id → object_name

    def all_hints_submitted(self) -> bool:
        return len(self.hints_submitted) >= len(self.player_ids)
```

[VERIFIED: Matches D-03 exactly]

### Pattern 2: Extending `_advance_to()` with phase-specific side effects

The critical insight: `_advance_to()` currently builds `broadcast_data` inside the lock. The pattern for Phase 4 is to:
1. Add phase-specific state mutations INSIDE the lock (e.g., create TurnState, compute scores).
2. Add phase-specific data to `broadcast_data` INSIDE the lock (e.g., hints dict for GUESS_PHASE).
3. Call `broadcaster.send_to_player()` / `broadcaster.broadcast()` OUTSIDE the lock (unchanged).

```python
# Source: [VERIFIED: turn_machine.py _advance_to() structure]
# Inside the `with self.lock:` block, add phase-specific logic:

if phase == "HINT_PHASE":
    player_ids = [...]  # from GameServer callback or passed at construction
    self.current_turn_state = TurnState(self.current_turn, player_ids)
    # trigger: image assignments (private events — after lock release)

elif phase == "GUESS_PHASE":
    # Fill empty hints for players who didn't submit
    for pid in self.current_turn_state.player_ids:
        if pid not in self.current_turn_state.hints_submitted:
            self.current_turn_state.hints_submitted[pid] = ""
    # Add hints to PHASE_CHANGED payload (D-06)
    broadcast_data["hints"] = dict(self.current_turn_state.hints_submitted)

elif phase == "SCORING_PHASE":
    score_deltas = _calculate_scores(self.current_turn_state, ...)  # pure function
    # update GameSession.accumulated_scores — needs back-reference or callback
    broadcast_data_for_scores = {...}  # capture for outside-lock broadcast
```

**Key decision for planner:** TurnMachine needs player_ids to create TurnState. Options:
1. Pass player_ids list to `TurnMachine.__init__()` from `start_game()`.
2. Inject via a `get_players_callback` callable (like `on_game_ended`).
3. Pass via a `set_player_ids(ids)` method called before `start()`.

Option 1 is simplest and consistent with existing pattern (room_code, max_turns both passed at construction). [ASSUMED: Option 1 is cleaner — planner should confirm]

### Pattern 3: Private image delivery using existing `send_to_player`

`EventBroadcaster.send_to_player()` already exists and is designed for this exact use case. [VERIFIED: event_broadcaster.py lines 82–98]

```python
# Source: [VERIFIED: event_broadcaster.py]
# Called OUTSIDE the lock after TurnState.image_assignments is populated:
for player_id, object_name in turn_state.image_assignments.items():
    filename = [k for k, v in image_manifest.items() if v == object_name][0]
    broadcaster.send_to_player(player_id, "object_assigned", {
        "image_url": f"/static/images/{filename}",
        "object_name": object_name,
    })
```

**BridgeCallbackReceiver routing for private events:**
The bridge must route `object_assigned` to a specific SID (not room). The established pattern uses `target_player_id` in payload. The bridge checks for it:

```python
# Source: [VERIFIED: 04-CONTEXT.md established patterns]
@Pyro5.api.oneway
@Pyro5.api.callback
def on_object_assigned(self, data: dict):
    target_player_id = data.get("target_player_id")
    if target_player_id:
        with _sid_lock:
            sid = _player_to_sid.get(target_player_id)  # NEED reverse map — see Pitfall 1
        if sid:
            socketio.emit("object_assigned", data, to=sid)
    # fallback: if no SID found, silently drop (player disconnected)
```

### Pattern 4: Flask static serving for images

The bridge already has `send_from_directory` for the React SPA. Images need a dedicated static route:

```python
# Source: [VERIFIED: bridge.py existing pattern]
@app.route("/static/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "..", "server", "images"),
        filename
    )
```

This route must be registered BEFORE the catch-all SPA route (already the case for non-`/static/images/` paths, but verify ordering). [VERIFIED: bridge.py catch-all is at bottom]

### Pattern 5: Scoring calculation as a pure function

Scoring logic is pure: given `correct_guesses` (ordered list) and `image_assignments` (to identify owner), compute deltas.

```python
# Source: REQUIREMENTS.md SCORE-01 to SCORE-03, 04-CONTEXT.md D-15
def _calculate_score_deltas(turn_state: TurnState) -> dict:
    """Returns {player_id: delta_points} for this turn."""
    deltas = {pid: 0 for pid in turn_state.player_ids}

    n = len(turn_state.correct_guesses)

    # Guesser scoring (SCORE-01)
    for i, guesser_id in enumerate(turn_state.correct_guesses):
        position = i + 1  # 1-based
        if position == 1:
            pts = 20
        elif position == 2:
            pts = 15
        elif position == 3:
            pts = 10
        else:
            pts = max(20 - (position - 1) * 5, 5)
        deltas[guesser_id] = deltas.get(guesser_id, 0) + pts

    # Solo bonus (SCORE-02)
    if n == 1:
        deltas[turn_state.correct_guesses[0]] += 10

    # Owner scoring (SCORE-03)
    for object_player_id in set(turn_state.image_assignments.keys()):
        guessers_for_owner = [
            g for g in turn_state.correct_guesses
            if turn_state.guesses_made.get(g) == object_player_id
        ]
        n_correct = len(guessers_for_owner)
        total_guessers = len([
            g for g, t in turn_state.guesses_made.items() if t == object_player_id
        ])
        if total_guessers == 0 or n_correct == 0:
            owner_pts = 0
        elif n_correct == total_guessers:
            owner_pts = -10  # all guessed correctly
        else:
            owner_pts = max(15 - (n_correct - 1) * 5, 0)
        deltas[object_player_id] = deltas.get(object_player_id, 0) + owner_pts

    return deltas
```

[ASSUMED: SCORE-03 rule interpretation: "todos acertaram" means every guesser who targeted this owner guessed correctly — planner should verify against REQUIREMENTS.md exact wording]

### Pattern 6: Frontend phase-conditional panels (React)

GameScreen already has `currentPhase` state. Phase 4 adds conditional JSX blocks:

```tsx
// Source: [VERIFIED: GameScreen.tsx structure]
// Add inside the body area, below the phase header:
{currentPhase === 'HINT_PHASE' && (
  <HintPanel
    myHintSubmitted={myHintSubmitted}
    hintsCount={hintsCount}
    totalPlayers={totalPlayers}
    onSubmit={(word) => socket.emit('submit_hint', { hint_word: word })}
  />
)}
{currentPhase === 'GUESS_PHASE' && (
  <GuessPanel
    hints={hints}             // dict {player_id: hint_word} from PHASE_CHANGED
    players={players}         // list from prior state
    myPlayerId={myPlayerId}
    myGuessSubmitted={myGuessSubmitted}
    onSubmit={(target, word) => socket.emit('submit_guess', { target_player_id: target, guess_word: word })}
    onSkip={() => socket.emit('skip_guess', {})}
  />
)}
{currentPhase === 'SCORING_PHASE' && (
  <ScorePanel scores={scores} />  // scores from SCORE_UPDATED event
)}
```

### Anti-Patterns to Avoid

- **Broadcast inside lock:** `broadcaster.broadcast()` and `broadcaster.send_to_player()` do network I/O — calling them while holding `self.lock` deadlocks when the callback receiver is registered in the same process. [VERIFIED: existing code comments everywhere]
- **Sharing Pyro5 proxies across threads:** Each Flask-SocketIO handler thread creates its own proxy via `get_game_server_proxy()`. Never pass a proxy to another thread. [VERIFIED: bridge.py threading.local pattern]
- **Transmitting image bytes through Pyro5:** Serpent serializer is inefficient for binary data; Flask static serving is already in place. [VERIFIED: CLAUDE.md + PROJECT.md key decisions]
- **Self-join loops in EventBroadcaster.broadcast():** When TurnMachine calls `broadcaster.broadcast()`, it reaches the BridgeCallbackReceiver synchronously in the same call stack. Avoid any calls back into GameServer from within a broadcast handler.
- **TurnState mutation after lock release:** All reads/writes to `TurnState` fields must happen inside `GameServer.lock` (or `TurnMachine.lock` for the transition logic). Never read `current_turn_state` from a handler thread without the lock.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Private per-player event delivery | Custom routing map | `EventBroadcaster.send_to_player()` (already exists) | Already handles URI lookup, proxy creation, and failure cleanup |
| Thread-safe state mutation | Custom lock wrapper | `threading.RLock` (already used everywhere) | RLock supports re-entrant acquisition from same thread |
| Image file serving | Custom HTTP handler | Flask `send_from_directory` (already used for SPA) | Path-traversal protection built in |
| JSON manifest parsing | Custom parser | `json.load()` stdlib | No edge cases for a 20-entry manifest |
| Scoring formula | Custom accumulator class | Standalone pure function + dict accumulation | Stateless function is easier to unit-test in isolation |

---

## Common Pitfalls

### Pitfall 1: No reverse `_player_to_sid` map for private delivery

**What goes wrong:** `on_object_assigned` in BridgeCallbackReceiver receives a `target_player_id` but the bridge only has `_sid_to_player` (forward map). There is no `_player_to_sid` reverse map in the current bridge code.

**Why it happens:** Phase 1–3 only needed room-level broadcasts (`to=room_code`). Targeted SID delivery is new in Phase 4.

**How to avoid:** Add a `_player_to_sid: dict` alongside `_sid_to_player`. Populate both on `create_game` / `join_game`. Remove entry on `disconnect`. Protect with the same `_sid_lock`.

**Warning signs:** `on_object_assigned` logs "player SID not found" for every player — image never appears in browser.

[VERIFIED: bridge.py only has `_sid_to_player`, not the reverse]

### Pitfall 2: TurnState created before player_ids are available to TurnMachine

**What goes wrong:** `TurnMachine.__init__` currently receives `room_code`, `max_turns`, `broadcaster`, `on_game_ended`. It does NOT have access to the player list. Creating TurnState at HINT_PHASE entry requires knowing which players are in the session.

**Why it happens:** TurnMachine was designed to be independent of session data.

**How to avoid:** Pass player_ids to TurnMachine at construction (`player_ids: list` parameter) — set by `start_game()` which already has access to the session's player list. Alternatively, inject a `get_player_ids` callable.

**Warning signs:** `TurnState(turn_number, [])` creates TurnState with empty player list — all_hints_submitted() returns True immediately, HINT_PHASE advances with zero hints.

[VERIFIED: turn_machine.py TurnMachine.__init__ signature — no player_ids parameter]

### Pitfall 3: Image assignment pool exhaustion across turns

**What goes wrong:** If the image pool is naively shuffled the same way each turn (using same random seed or global state), players could get the same object two turns in a row.

**Why it happens:** `random.sample` / `random.shuffle` without exclusion of prior assignments.

**How to avoid:** Track `used_images_this_game: set` in `GameSession`. At each HINT_PHASE, sample from `available = all_images - used_images_this_game`. Reset set only if exhausted (wrap-around).

**Warning signs:** With 8 images and 4 players across 3 turns, pool is exhausted by turn 3 — handle wrap gracefully.

[VERIFIED: D-12 from CONTEXT.md; no existing pool management code]

### Pitfall 4: HINT_PHASE auto-advance race condition

**What goes wrong:** The last player's `submit_hint()` RPC call and the HINT_PHASE timer firing simultaneously both call `_advance_to("GUESS_PHASE")`. This could result in two GUESS_PHASE broadcasts.

**Why it happens:** Two code paths trigger the same transition.

**How to avoid:** The generation counter in TurnMachine already handles timer-vs-manual races. For the submit_hint path: after setting the hint, check `all_hints_submitted()` inside the same lock block. If true, call `turn_machine._advance_to("GUESS_PHASE")` (not `from_timer=True`). The generation increment in `_advance_to` will make the subsequent timer callback a no-op.

**Warning signs:** Two `phase_changed` events with `phase: "GUESS_PHASE"` visible in bridge logs.

[VERIFIED: TurnMachine generation counter mechanism — applies to any advance path]

### Pitfall 5: SCORING_PHASE needs GameSession access from TurnMachine

**What goes wrong:** Scoring requires updating `GameSession.accumulated_scores` (D-16), but TurnMachine only has a reference to `broadcaster`, not to `GameSession`.

**Why it happens:** TurnMachine was designed without game-data dependencies.

**How to avoid:** Two options:
  1. Add an `on_scoring_phase` callback to TurnMachine (like `on_game_ended`) that receives `score_deltas` dict — GameServer accumulates scores in this callback.
  2. Calculate scores in TurnMachine but only broadcast; GameServer listens via callback and updates `accumulated_scores`.

Option 1 is consistent with the existing `on_game_ended` callback pattern. [VERIFIED: turn_machine.py on_game_ended pattern, line 51]

### Pitfall 6: Flask static image route conflicts with React SPA catch-all

**What goes wrong:** Adding `/static/images/<path>` after the SPA catch-all route `/<path:path>` makes the image route unreachable — Flask matches catch-all first.

**Why it happens:** Flask route registration order matters; catch-all `/<path:path>` is registered last in the current bridge.py, but must stay last.

**How to avoid:** Register the `/static/images/<path:filename>` route BEFORE the catch-all. In bridge.py, add it in the existing routes section. [VERIFIED: bridge.py — catch-all is at bottom, will stay last if new route added before it]

### Pitfall 7: `guesses_made` key ambiguity for skip vs. no-action

**What goes wrong:** A player who explicitly skips (`guesses_made[pid] = None`) vs. a player who never acted before GUESS_PHASE timer fires — both result in None/missing. At scoring time, iterating `guesses_made` might miss players who never submitted.

**How to avoid:** At SCORING_PHASE entry, fill all players not in `guesses_made` with `None` (same as skip). This mirrors the HINT_PHASE empty-string fill for missing hints. [VERIFIED: CONTEXT.md D-11]

---

## Code Examples

### TurnState creation inside _advance_to (verified pattern)

```python
# Source: [VERIFIED: turn_machine.py _advance_to structure + CONTEXT.md D-02]
# Inside `with self.lock:` block in TurnMachine._advance_to():

if phase == "HINT_PHASE":
    self.current_turn_state = TurnState(
        turn_number=self.current_turn,
        player_ids=list(self.player_ids),  # player_ids stored at __init__
    )
    # Build list of (player_id, object_name) for private delivery — AFTER lock exit
    image_assignments_snapshot = dict(self.current_turn_state.image_assignments)
```

### GameServer.submit_hint() — full RPC method shape

```python
# Source: [VERIFIED: GameServer pattern from game_server.py + CONTEXT.md D-04/D-08]
def submit_hint(self, player_id: str, hint_word: str) -> dict:
    should_advance = False
    broadcast_data = None

    with self.lock:
        room_code = self._player_to_room.get(player_id)
        session = self.sessions.get(room_code) if room_code else None
        if session is None or session.turn_machine is None:
            return {"error": "no_active_session"}

        ts = session.turn_machine.current_turn_state
        if ts is None:
            return {"error": "no_turn_state"}
        if session.turn_machine.current_phase != "HINT_PHASE":
            return {"error": "not_hint_phase"}
        if player_id in ts.hints_submitted:
            return {"error": "already_submitted"}

        hint_clean = str(hint_word).strip()[:50]  # length guard
        ts.hints_submitted[player_id] = hint_clean

        broadcast_data = {
            "room_code": room_code,
            "hints_count": len(ts.hints_submitted),
            "total_players": len(ts.player_ids),
        }
        if ts.all_hints_submitted():
            should_advance = True

    # Outside lock:
    self.broadcaster.broadcast("hint_received", broadcast_data)
    if should_advance:
        session.turn_machine._advance_to("GUESS_PHASE")

    return {"ok": True}
```

### Bridge: reverse SID map addition

```python
# Source: [VERIFIED: bridge.py _sid_to_player pattern]
# Add alongside existing _sid_to_player:
_player_to_sid: dict = {}  # player_id → request.sid (reverse map for private delivery)

# In handle_create_game and handle_join_game, after setting _sid_to_player:
with _sid_lock:
    _sid_to_player[request.sid] = result["player_id"]
    _player_to_sid[result["player_id"]] = request.sid  # ADD THIS

# In handle_disconnect:
with _sid_lock:
    player_id = _sid_to_player.pop(request.sid, None)
    if player_id:
        _player_to_sid.pop(player_id, None)  # ADD THIS
```

### Frontend: listening for new events in GameScreen

```tsx
// Source: [VERIFIED: GameScreen.tsx useEffect pattern]
// Add inside the useEffect cleanup block:
socket.on('object_assigned', handleObjectAssigned)
socket.on('hint_received', handleHintReceived)
socket.on('guess_result', handleGuessResult)
socket.on('score_updated', handleScoreUpdated)

return () => {
  socket.off('object_assigned', handleObjectAssigned)
  socket.off('hint_received', handleHintReceived)
  socket.off('guess_result', handleGuessResult)
  socket.off('score_updated', handleScoreUpdated)
  // ... existing cleanup
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase machine with no game data | TurnState dataclass added to TurnMachine | Phase 4 (this phase) | TurnMachine now owns both timing AND current turn data |
| Broadcast-only events | Mix of broadcast + targeted private events | Phase 4 (this phase) | Bridge needs reverse SID map for targeted delivery |
| No score accumulation | `accumulated_scores` dict on GameSession | Phase 4 (this phase) | GameSession grows: add field + get_scores() RPC |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Player_ids best passed to TurnMachine at construction (Option 1) | Architecture Patterns / Pitfall 2 | Minor — alternative is callback injection; either works |
| A2 | SCORE-03 "todos acertaram" means all targeters of this owner guessed correctly (not all players in game) | Code Examples (scoring function) | Scoring would be wrong for multi-object scenarios |
| A3 | Image files can be JPEG/PNG — no restriction on format beyond Flask static serving | Standard Stack | Non-issue: Flask's send_from_directory handles both |
| A4 | `on_scoring_phase` callback is the right pattern for GameSession score accumulation | Pitfall 5 | Could instead pass GameSession reference to TurnMachine, but that couples layers |

---

## Open Questions

1. **SCORE-03 tie-breaker for owner: "all guessed" means all-in-game or all-who-targeted?**
   - What we know: REQUIREMENTS.md says "se todos acertaram: -10 pts"
   - What's unclear: "todos" = all players in game, or all who targeted this owner?
   - Recommendation: Planner reads REQUIREMENTS.md SCORE-03 verbatim and implements literally; safe assumption is "all who targeted this owner" given other rules reference N guessers.

2. **Image assignment timing: ROUND_START vs HINT_PHASE start?**
   - What we know: CONTEXT.md explicitly leaves this to the planner.
   - Recommendation: Assign at ROUND_START (5s phase). Players see their image during the "Round starting..." pause before hint input appears. This avoids showing blank secret panel when HINT_PHASE opens.

3. **Should TurnMachine._advance_to be called directly from submit_hint, or via a method on TurnMachine?**
   - What we know: `advance_phase_manual()` exists for test use. Direct `_advance_to()` call would work.
   - Recommendation: Add a `advance_to_guess_phase()` public method on TurnMachine that is the "all hints submitted" fast-path. Keeps the call clean and avoids exposing the internal `_advance_to` signature to callers outside TurnMachine.

---

## Environment Availability

Step 2.6: Verifying existing environment for Phase 4.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 (venv) | All server code | ✓ | 3.11 | — |
| Pyro5 | RPC methods | ✓ | 5.16 | — |
| Flask-SocketIO | Bridge handlers | ✓ | 5.6.1 | — |
| `server/images/` directory | IMAGE-01 | ✗ | — | Must create in Wave 0 |
| Image files (JPEG/PNG) | IMAGE-02 | ✗ | — | Must add ≥8 images in Wave 0 |
| `manifest.json` | IMAGE-01 | ✗ | — | Must create in Wave 0 |

**Missing dependencies with no fallback:**
- `server/images/` directory — must be created before image assignment code can run.

**Missing dependencies with fallback:**
- None — all code dependencies are present.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no version pin in requirements.txt) |
| Config file | `pytest.ini` (root, `testpaths = tests`) |
| Quick run command | `python -m pytest tests/test_turn_state.py tests/test_scoring.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HINT-01 | submit_hint stores hint in TurnState | unit | `pytest tests/test_turn_state.py::test_submit_hint -x` | ❌ Wave 0 |
| HINT-01 | submit_hint rejects double-submit | unit | `pytest tests/test_turn_state.py::test_submit_hint_duplicate -x` | ❌ Wave 0 |
| HINT-02 | HINT_RECEIVED broadcast has hints_count, no hint word | unit | `pytest tests/test_turn_state.py::test_hint_received_payload -x` | ❌ Wave 0 |
| HINT-03 | Empty string inserted for non-submitters at GUESS_PHASE | unit | `pytest tests/test_turn_state.py::test_hint_empty_on_timer -x` | ❌ Wave 0 |
| HINT-04 | All-submitted triggers GUESS_PHASE advance | unit | `pytest tests/test_turn_state.py::test_all_hints_auto_advance -x` | ❌ Wave 0 |
| GUESS-01 | submit_guess records correct/incorrect result | unit | `pytest tests/test_turn_state.py::test_submit_guess_correct -x` | ❌ Wave 0 |
| GUESS-02 | skip_guess sets guesses_made to None | unit | `pytest tests/test_turn_state.py::test_skip_guess -x` | ❌ Wave 0 |
| GUESS-04 | GUESS_RESULT broadcast includes is_correct | unit | `pytest tests/test_turn_state.py::test_guess_result_broadcast -x` | ❌ Wave 0 |
| GUESS-05 | Second submit_guess returns already_guessed error | unit | `pytest tests/test_turn_state.py::test_guess_one_per_turn -x` | ❌ Wave 0 |
| SCORE-01 | Tiered guesser points: 1st=20, 2nd=15, 3rd=10, rest formula | unit | `pytest tests/test_scoring.py::test_tiered_guessers -x` | ❌ Wave 0 |
| SCORE-02 | Solo correct guesser gets +10 bonus | unit | `pytest tests/test_scoring.py::test_solo_bonus -x` | ❌ Wave 0 |
| SCORE-03 | Owner scoring formula for N correct guessers | unit | `pytest tests/test_scoring.py::test_owner_scoring -x` | ❌ Wave 0 |
| SCORE-04 | SCORE_UPDATED broadcast has per-player breakdown | unit | `pytest tests/test_scoring.py::test_score_updated_payload -x` | ❌ Wave 0 |
| SCORE-05 | get_scores() returns accumulated totals | unit | `pytest tests/test_turn_state.py::test_get_scores -x` | ❌ Wave 0 |
| IMAGE-01 | manifest.json loaded at server startup | unit | `pytest tests/test_turn_state.py::test_image_manifest_load -x` | ❌ Wave 0 |
| IMAGE-02 | OBJECT_ASSIGNED payload has image_url and object_name | unit | `pytest tests/test_turn_state.py::test_object_assigned_payload -x` | ❌ Wave 0 |
| IMAGE-03 | /static/images/<file> returns 200 (Flask static route) | smoke | manual 4-terminal test | — |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_turn_state.py tests/test_scoring.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_turn_state.py` — covers HINT-01 through HINT-04, GUESS-01/02/04/05, IMAGE-01/02, SCORE-04/05
- [ ] `tests/test_scoring.py` — covers SCORE-01, SCORE-02, SCORE-03 (pure function, no Pyro5 needed)
- [ ] `server/images/` directory with ≥8 sample images and `manifest.json`

*(Existing `tests/test_turn_machine.py` and `tests/test_session.py` cover Phases 1–3 and remain unchanged.)*

---

## Security Domain

Phase 4 is academic / localhost-only. No new external attack surface beyond what Phases 1–3 established. Noting applicable controls:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in scope |
| V3 Session Management | no | player_id from localStorage (Phase 2 established) |
| V4 Access Control | yes | submit_hint / submit_guess must validate player_id is in the session and in the correct phase |
| V5 Input Validation | yes | hint_word and guess_word must be stripped and length-capped server-side |
| V6 Cryptography | no | No secrets in this phase |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Player submitting hint for another player's slot | Spoofing | `player_id` resolved from `_sid_to_player[request.sid]` server-side in bridge — never trusted from client payload |
| Guess word injection (very long string, special chars) | Tampering | `hint_word.strip()[:50]` length cap; `guess_word.strip()[:50]` — compare lowercased |
| Player guessing their own object | Tampering | `submit_guess()` rejects self-targeting (D-10) |
| Image path traversal via manifest filename | Tampering | `send_from_directory` built-in protection; manifest filenames are controlled by the server, not clients |

---

## Sources

### Primary (HIGH confidence)
- `server/turn_machine.py` — verified `_advance_to()`, generation counter, lock/broadcast-outside-lock pattern
- `server/game_server.py` — verified GameSession, RLock usage, broadcast pattern, on_game_ended callback injection
- `server/event_broadcaster.py` — verified `send_to_player()` existence and signature
- `bridge/bridge.py` — verified `_sid_to_player` (one-way only), BridgeCallbackReceiver extension pattern, Flask routes order
- `frontend/src/pages/GameScreen.tsx` — verified socket event listener pattern, currentPhase state
- `04-CONTEXT.md` — all locked decisions (D-01 through D-19) verified

### Secondary (MEDIUM confidence)
- `REQUIREMENTS.md` — SCORE-01 through SCORE-03 formulas; HINT/GUESS requirements

### Tertiary (LOW confidence — ASSUMED)
- None: all claims verified against live code or CONTEXT.md locked decisions.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all existing, verified in requirements.txt
- Architecture: HIGH — all patterns traced to live code
- Pitfalls: HIGH for Pitfalls 1, 2, 6 (verified gaps in current code); MEDIUM for Pitfalls 3, 4, 5 (design risks, not current bugs)
- Scoring formula: MEDIUM — REQUIREMENTS.md text read; one interpretation noted as ASSUMED

**Research date:** 2026-05-14
**Valid until:** End of Phase 4 execution (code is the source of truth — no external dependencies to drift)
