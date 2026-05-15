# Phase 7: Reconnection + End-of-Game — Research

**Researched:** 2026-05-15
**Domain:** Pyro5 session state, Flask-SocketIO disconnect grace period, post-game flow, chat broadcast, play-again vote
**Confidence:** HIGH (all findings grounded in existing codebase inspection or locked decisions in CONTEXT.md)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Bridge uses a grace period (~5s) before calling `leave_game()` on Socket.IO disconnect. If the player reconnects within the window (providing their UUID from localStorage), the pending leave is cancelled and their callback re-registered.
- **D-02:** Client emits a new `reconnect_game` Socket.IO event with `{player_id, room_code}` on reconnect. Bridge checks if the UUID is still active (player did not time out), re-registers their callback URI, and returns the current game state.
- **D-03:** Reconnect state delivery reuses the existing `get_player_view(room_code, player_id)` — no new data structure.
- **D-04:** Chat input uses different colors + explicit labels to achieve "radical visual separation" (CHAT-03/04): chat input labeled "Mensagem de chat" in a secondary color (gray/blue); game action inputs labeled explicitly and styled in primary color.
- **D-06:** Vote counting semantics — Claude's discretion. Planner should define the exact majority rule.
- **D-07:** When the game truly ends (vote closes with no majority to continue, or majority votes stop): post-game screen stays visible briefly, then all players are redirected to the landing page. Session is deleted on the server.
- **D-08:** When callbacks fail 3 consecutive times for a player, they are removed from the active callback list. Server broadcasts a PLAYER_LEFT event with the player's name.
- SESSION-07 (host transfer on lobby disconnect) is already fully implemented in `leave_game()` — no new work needed.

### Claude's Discretion

- Chat placement within the game screen (tab vs. fixed panel) — must satisfy UI-04 and CHAT-03/04; specific layout is planner's call.
- Exact vote counting semantics (strict majority vs. active-voter majority) — planner's call as long as abstentions don't accidentally enable continuation with very few votes.
- Whether the grace-period timer in the bridge uses `threading.Timer` or a per-SID dict with timestamp checks — planner's call.

### Deferred Ideas (OUT OF SCOPE)

- Reconnection notification banner (UI-09 "amber: reconnecting, red: offline") — deferred to Phase 8 UI Polish.
- Spectator mode — v2.
- Persistent game history — v2.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-07 | Jogador desconectado identificado por falha de callback e removido da lista de callbacks ativos | EventBroadcaster already tracks failures; add consecutive-failure counter and back-call into GameServer |
| INFRA-08 | Cliente web armazena UUID de sessão em localStorage; ao recarregar chama `get_game_state()` para restaurar estado | localStorage pattern already used for `player_id`; `get_player_view()` already returns full client state |
| SESSION-07 | Se host desconecta no lobby, próximo jogador assume como host | Already implemented in `leave_game()` — verify only, no new code |
| POSTGAME-01 | Após último turno exibe tela de resultados com pódio (top 3) e tabela de pontos por turno | `game_ended` event already fires; needs new PostGame React page consuming accumulated_scores |
| POSTGAME-02 | Sistema inicia votação "continuar com novos objetos?" com timer de 30s | New server-side vote state + `start_vote()` RPC + `VOTE_STARTED` broadcast |
| POSTGAME-03 | Se maioria vota continuar: servidor distribui novas imagens e jogo reinicia no turno 1 | Reuse `_assign_images_for_turn()` + reset TurnMachine; broadcast `GAME_RESTARTING` |
| POSTGAME-04 | Se maioria vota encerrar (ou timer expira sem maioria): partida encerrada | Broadcast `GAME_ENDED` + `session.status = 'ENDED'` + delete session |
| CHAT-01 | Jogador pode enviar mensagem de chat via `send_chat(player_id, message)` a qualquer momento | New `@expose` method on GameServer; `broadcaster.broadcast()` fan-out |
| CHAT-02 | Mensagens de chat são broadcast para todos via `on_chat_message` callback | New `on_chat_message` on BridgeCallbackReceiver; emits `chat_message` Socket.IO event |
| CHAT-03 | Chat é visualmente e funcionalmente separado das ações de jogo | Separate React panel/tab with distinct CSS class; confirmed by D-04 |
| CHAT-04 | Interface não permite confundir campo de chat com campo de dica ou palpite | Confirmed by D-04: distinct color + label + submit button |
</phase_requirements>

---

## Summary

Phase 7 delivers four independent feature clusters on top of an already-mature codebase (Phases 1–6 complete): (1) session reconnection via localStorage UUID + grace-period disconnect handling, (2) graceful player removal when callbacks repeatedly fail (PLAYER_LEFT broadcast), (3) post-game podium + play-again vote, and (4) in-game chat. All server-side patterns (RLock, broadcast-outside-lock, threading.Timer, per-thread proxy) are already established. No new libraries are required — every feature maps to extensions of existing files.

The reconnect flow (D-01 / D-02) is the most architecturally sensitive piece: modifying `handle_disconnect()` in `bridge.py` to defer `leave_game()` by 5 seconds, and adding a new `reconnect_game` Socket.IO handler that cancels the pending timer. `get_player_view()` already returns the full client state needed by D-03.

The post-game vote introduces a small new piece of server state (vote dict + timer) that follows exactly the same `threading.Timer` + generation-counter pattern used by `TurnMachine`. Chat is the simplest feature: one new RPC method, one new callback handler, one new frontend component.

**Primary recommendation:** Implement in four focused waves — (1) callback failure tracking + PLAYER_LEFT, (2) reconnect grace period, (3) post-game flow + vote, (4) chat + frontend integration — so each wave is independently testable.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Callback failure tracking (INFRA-07) | API / Backend (`EventBroadcaster`) | — | Broadcaster owns the callback list; it is the only place where individual delivery failures are observable |
| Session reconnect state delivery (INFRA-08) | API / Backend (`GameServer.get_player_view`) | Bridge (Socket.IO room re-join) | Server is authoritative for session state; bridge translates the reconnect event and re-registers callback URI |
| Grace period timer (D-01) | Bridge (Flask-SocketIO process) | — | Bridge owns Socket.IO lifecycle (connect/disconnect); timer lives here, not in GameServer |
| UUID persistence (INFRA-08 client side) | Browser / Client (localStorage) | — | UUIDs are written to localStorage by the join/create flows already; reconnect reads from the same key |
| Chat fan-out (CHAT-01/02) | API / Backend (`GameServer.send_chat` + `EventBroadcaster`) | Bridge (`on_chat_message` → Socket.IO emit) | Same broadcast pattern as all other events |
| Chat UI separation (CHAT-03/04) | Browser / Client (React component) | — | Visual separation is a frontend concern; no backend change needed |
| Post-game podium data (POSTGAME-01) | API / Backend (`GameSession.accumulated_scores` + per-turn deltas) | Bridge + Client | Score data already in server; client needs a new page to render it |
| Play-again vote (POSTGAME-02/03/04) | API / Backend (new vote state in `GameSession`) | Bridge + Client | Vote counting and timer are server-authoritative to prevent split-brain |
| Session deletion on game end (D-07) | API / Backend (`GameServer`) | — | Server owns session lifecycle |
| HOST_CHANGED on lobby disconnect (SESSION-07) | API / Backend (`leave_game()`) | Bridge (already routes `host_changed`) | Already implemented — verified in `game_server.py:897–952` and `bridge.py:80–90` |

---

## Standard Stack

### Core (no new libraries)

All work in this phase uses the already-installed stack. No `pip install` needed.

| Component | Version | Purpose |
|-----------|---------|---------|
| Pyro5 | 5.16 | RPC backbone — `send_chat`, `reconnect_player`, `submit_vote` RPCs |
| Flask-SocketIO | 5.6.1 | Socket.IO event routing — `reconnect_game`, `chat_message` events |
| threading.Timer | stdlib | Grace-period timer (D-01), vote 30s countdown (POSTGAME-02) |
| React + TypeScript | (existing) | New PostGame page, Chat panel component |

### Supporting (already installed)

| Component | Purpose |
|-----------|---------|
| `threading.Lock` / `RLock` | Vote state protection (same pattern as GameSession.lock) |
| `time.monotonic()` | Vote timer deadline tracking (same as TurnMachine) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `threading.Timer` for grace period | Per-SID timestamp dict polled by a background thread | Timer is simpler, already proven in TurnMachine; timestamp dict avoids object creation per disconnect but adds polling complexity |
| Strict >50% majority rule | Any-yes-over-no excluding abstentions | Strict majority is safer for small player counts (2 players): prevents a 1-yes / 1-abstention from triggering restart |

---

## Package Legitimacy Audit

> No new packages are installed in this phase. All dependencies are already in `requirements.txt`.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
[Browser A]                    [Bridge Process]               [GameServer Process]
    |                               |                               |
    | -- Socket.IO disconnect -->   |                               |
    |                        [threading.Timer(5s)]                  |
    |                               |                               |
    | -- reconnect_game{uuid} -->   |                               |
    |                        cancel timer                           |
    |                        re-register SID mapping                |
    |                        --- reconnect_player RPC ----------->  |
    |                               |          update callback URI  |
    |                        <-- get_player_view() response ------  |
    | <-- join_room ack + state --- |                               |
    |                               |                               |
    | -- send_chat{msg} ----------> |                               |
    |                         -- send_chat RPC ------------------>  |
    |                               |               broadcast() --> [EventBroadcaster]
    |                               | <-- on_chat_message callback--|
    | <-- chat_message event ------ |                               |
    |                               |                               |
    | [GAME_ENDED received]         |                               |
    | [PostGame page renders]       |                               |
    | -- submit_vote{yes} --------> |                               |
    |                         -- submit_vote RPC ---------------->  |
    |                               |  [vote timer / tally logic]  |
    |                               | <-- GAME_RESTARTING or ------|
    |                               |     GAME_ENDED broadcast      |
    | <-- game_restarting event --- |                               |
    |  (navigate back to game)      |                               |
```

### Recommended Project Structure (additions only)

```
server/
├── game_server.py         # + send_chat(), reconnect_player(), start_vote(), submit_vote()
├── event_broadcaster.py   # + consecutive_failures counter per player_id; PLAYER_LEFT back-call
frontend/src/
├── pages/
│   ├── GameScreen.tsx     # + reconnect_game emit on mount; + chat panel; + game_restarting handler
│   └── PostGame.tsx       # NEW: podium, per-turn table, vote section with timer bar
├── components/
│   └── ChatPanel.tsx      # NEW: chat input + message list; visually separated
bridge/
└── bridge.py              # + handle_disconnect grace period; + @socketio.on('reconnect_game');
                           # + on_chat_message, on_player_left, on_vote_started,
                           #   on_vote_update, on_game_restarting BridgeCallbackReceiver methods
```

### Pattern 1: Grace-Period Disconnect (D-01)

**What:** When Socket.IO disconnects, bridge starts a 5s `threading.Timer` instead of calling `leave_game()` immediately. If `reconnect_game` arrives before the timer fires, it is cancelled.
**When to use:** Every `handle_disconnect()` invocation.

```python
# Source: existing bridge.py pattern (threading.Timer used by TurnMachine)
_pending_leaves: dict = {}   # sid -> threading.Timer
_pending_leaves_lock = threading.Lock()

@socketio.on("disconnect")
def handle_disconnect(reason):
    with _sid_lock:
        player_id = _sid_to_player.pop(request.sid, None)
        if player_id:
            _player_to_sid.pop(player_id, None)
    sid = request.sid
    if player_id:
        def do_leave():
            with _pending_leaves_lock:
                _pending_leaves.pop(sid, None)
            try:
                proxy = get_game_server_proxy()
                proxy.leave_game(player_id)
            except Exception as exc:
                print(f"[BRIDGE] leave_game failed for {player_id}: {exc}", flush=True)
        t = threading.Timer(5.0, do_leave)
        with _pending_leaves_lock:
            _pending_leaves[sid] = (t, player_id)
        t.start()
```

### Pattern 2: Reconnect Handler (D-02)

**What:** Client emits `reconnect_game` with `{player_id, room_code}`. Bridge cancels pending leave timer (if any old SID is found), re-registers SID mapping, calls server-side `reconnect_player()` RPC.

```python
# Source: D-02 locked decision + existing _sid_to_player/_player_to_sid pattern
@socketio.on("reconnect_game")
def handle_reconnect_game(data):
    player_id = data.get("player_id", "")
    room_code = data.get("room_code", "")
    if not player_id or not room_code:
        return {"error": "missing fields"}
    # Cancel any pending leave for this player_id
    with _pending_leaves_lock:
        for sid, (timer, pid) in list(_pending_leaves.items()):
            if pid == player_id:
                timer.cancel()
                del _pending_leaves[sid]
                break
    # Re-register SID mapping
    with _sid_lock:
        _sid_to_player[request.sid] = player_id
        _player_to_sid[player_id] = request.sid
    join_room(room_code)
    # Re-register callback URI on server
    proxy = get_game_server_proxy()
    result = proxy.reconnect_player(player_id, room_code, _cb_uri)
    return result
```

### Pattern 3: Consecutive Callback Failure Counter (D-08)

**What:** `EventBroadcaster.broadcast()` already logs permanent failures and removes the entry. Extend it to count consecutive transient failures (3 → treat as permanent). Call back into `GameServer` to broadcast PLAYER_LEFT.

```python
# Source: existing event_broadcaster.py — permanent-failure removal at line 81
# Extension: add self.failure_counts dict and threshold check

# In EventBroadcaster.__init__:
self.failure_counts = {}   # player_id -> consecutive failure count

# In broadcast(), transient-failure branch:
self.failure_counts[player_id] = self.failure_counts.get(player_id, 0) + 1
if self.failure_counts[player_id] >= 3:
    failed.append(player_id)   # trigger removal + PLAYER_LEFT

# Reset on successful delivery:
self.failure_counts.pop(player_id, None)
```

The PLAYER_LEFT broadcast must be triggered by `GameServer` (which holds the player-name lookup), not by `EventBroadcaster` directly — keep the broadcaster decoupled. Pass a `on_player_failed` callback to `EventBroadcaster.__init__`, or have `broadcast()` return the list of failed player_ids for GameServer to process.

### Pattern 4: Vote State (POSTGAME-02/03/04)

**What:** After last TURN_END, GameServer starts a 30s vote. Follows same `threading.Timer` + generation-counter pattern as `TurnMachine._advance_to()`.

```python
# Source: existing TurnMachine pattern (turn_machine.py:114)
# Vote state held in GameSession (or a lightweight VoteRecord dataclass)
@dataclasses.dataclass
class VoteRecord:
    votes: dict          # player_id -> True (continue) | False (stop)
    timer: threading.Timer | None
    generation: int      # stale-timer guard
```

Majority rule (recommendation for D-06 discretion): **strict majority** = `yes_count > total_connected_players / 2`. With 2 players, this means both must vote yes. Timer expiry counts as implicit "no" from abstaining players, so the tally runs on the current `yes_count` vs. `total_connected_players`.

### Pattern 5: Chat (CHAT-01/02)

**What:** Simple fan-out, no state. No turn-phase gating — available "a qualquer momento da partida" (CHAT-01).

```python
# Source: existing broadcaster.broadcast() pattern
@Pyro5.api.expose
def send_chat(self, player_id: str, message: str) -> dict:
    with self.lock:
        room_code = self._player_to_room.get(player_id)
        player_name = next(
            (p.player_name for s in self.sessions.values()
             for p in s.players if p.player_id == player_id), None
        )
    if room_code is None or player_name is None:
        return {"error": "player not in session"}
    import time
    self.broadcaster.broadcast("chat_message", {
        "player_id": player_id,
        "player_name": player_name,
        "message": message[:200],   # length cap
        "timestamp": time.time(),
        "room_code": room_code,
    })
    return {"ok": True}
```

### Pattern 6: Play-Again Restart (POSTGAME-03)

**What:** If majority votes continue, call `_assign_images_for_turn()` (already exists) and reset TurnMachine by creating a new one on the same session.

Key subtlety: `_used_images_this_game` accumulates across turns; do NOT clear it on restart unless you explicitly want to allow image repetition. The restart should be treated as "new game round" — clear `_used_images_this_game[room_code]` to allow a fresh image pool for the replay, or let natural depletion handling in `_assign_images_for_turn()` manage it.

Broadcast `GAME_RESTARTING` (before image assignments fire) so the client navigates back to the game screen before `ROUND_START` arrives.

### Anti-Patterns to Avoid

- **Calling `leave_game()` from `EventBroadcaster.broadcast()`**: The broadcaster does not hold `GameServer.lock` so a re-entrant call back into GameServer could deadlock if broadcast was called from inside the lock. Always trigger removal via a callback/return-value that GameServer processes after releasing its lock.
- **Sharing one threading.Timer per player_id across reconnect attempts**: Each new disconnect should start a fresh Timer identified by the current Socket.IO SID, not the player_id — so a duplicate disconnect event for an old SID does not cancel the new player's active session.
- **Emitting Socket.IO events from inside `with self.lock:`**: Established anti-pattern; all `broadcaster.broadcast()` calls after lock exit (same as all prior phases).
- **Trusting client-provided player_id without server-side validation**: `reconnect_player()` should verify the player_id still exists in the session before re-registering the callback.
- **Vote arithmetic on a fixed snapshot of player count**: Connected player count can change during the vote window (another player disconnects). Evaluate majority against the count of players **at vote-close time**, not at vote-start time.
- **Not resetting vote state after restart**: `GameSession` must clear the vote record before a new round begins so a stale vote does not affect subsequent end-of-game.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stale-timer double-fire on vote | Custom flag variable | Generation counter (same pattern as TurnMachine) | Already proven; avoids race without a lock-heavy workaround |
| UUID uniqueness | Custom UUID generator | `uuid.uuid4()` already used in Phase 2 create_game | Already in codebase; nothing to add |
| Thread-safe broadcast from vote timer thread | Explicit locking of broadcaster | Follow existing broadcast-outside-lock pattern | Pattern established Phase 1; deviation causes deadlocks |
| Per-turn score storage for podium table | New DB or file | `GameSession.accumulated_scores` already accumulates; add per-turn delta list alongside | Server already has the data; just add a per-turn list to the session |

**Key insight:** Every new feature in this phase is a thin extension of patterns that already exist in `game_server.py`, `event_broadcaster.py`, and `bridge.py`. No architectural invention is required.

---

## Runtime State Inventory

> This is NOT a rename/refactor phase. Omit.

---

## Common Pitfalls

### Pitfall 1: Grace-Period Timer Keyed by SID, Not player_id
**What goes wrong:** If you key `_pending_leaves` by `player_id`, a player who disconnects and reconnects very quickly (two SIDs in rapid succession) may have the second SID cancel the first timer correctly — but if the first SID timer fires after the second SID is established, it calls `leave_game()` and removes a player who has already reconnected.
**Why it happens:** SID lifecycle is independent of player_id; one player_id can have multiple SID lifecycles.
**How to avoid:** Key the pending-leave dict by SID, not player_id. When cancelling on reconnect, search for the player_id across all pending entries and cancel any found.
**Warning signs:** Player disappears from session immediately after successful reconnect.

### Pitfall 2: PLAYER_LEFT Broadcast Inside the Lock
**What goes wrong:** `EventBroadcaster.broadcast()` is called from `GameServer` code that already holds `self.lock`. If the PLAYER_LEFT broadcast triggers a callback that calls back into `GameServer`, deadlock occurs.
**Why it happens:** RLock is re-entrant within the same thread, but the callback executes in the broadcaster's thread — a different thread — which will block trying to acquire the already-held lock.
**How to avoid:** All broadcasts must happen AFTER `with self.lock:` exits. Collect the list of failed player_ids during broadcast, return them to GameServer, then GameServer processes removal + PLAYER_LEFT in sequence after releasing its own lock.
**Warning signs:** Server freezes on first player disconnect.

### Pitfall 3: Reconnect Racing with Pending Leave Timer
**What goes wrong:** Timer fires at exactly T+5s; simultaneously the client emits `reconnect_game`. `do_leave()` runs and removes the player just as `handle_reconnect_game()` is re-adding them.
**Why it happens:** Threading races between the timer thread and the Socket.IO handler thread.
**How to avoid:** `handle_reconnect_game()` must cancel the timer AND remove the pending entry before calling `reconnect_player()`. Use `_pending_leaves_lock` to protect both reads and writes atomically.
**Warning signs:** Intermittent "player not found" errors in reconnect logs.

### Pitfall 4: Vote Tally Using Stale Player Count
**What goes wrong:** Vote started with 4 players; one disconnects at T+2s; at T+30s timer fires and sees `yes_count=2`, `total=4` → 50% → not a majority → game ends even though 2 out of 3 connected players voted yes.
**Why it happens:** Vote record snapshot the player count at start, not at evaluation time.
**How to avoid:** At vote-close time, query the current `session.players` list length (under lock) and use that as the denominator.
**Warning signs:** Play-again vote results differ from user expectation during testing with disconnected players.

### Pitfall 5: `game_restarting` Socket.IO Event Arriving Before `ROUND_START`
**What goes wrong:** Client receives `ROUND_START` phase change while still on PostGame screen; the phase handler fires but the game screen is not mounted, so React state is lost.
**Why it happens:** Server broadcasts `GAME_RESTARTING` then immediately re-starts `TurnMachine.start()` which fires `ROUND_START` in its first `_advance_to()` call (5s timer for ROUND_START). If `GAME_RESTARTING` and `ROUND_START` arrive within the ROUND_START duration (5s), the client may not have navigated yet.
**How to avoid:** Client must navigate to `/game/:roomCode` upon receiving `game_restarting` event, BEFORE any phase_changed events arrive. The existing ROUND_START 5s window is the safety margin. Ensure navigation happens synchronously in the `game_restarting` handler.
**Warning signs:** Black game screen after play-again vote; phase panel renders without image.

### Pitfall 6: Chat message without room_code in payload
**What goes wrong:** `on_chat_message` callback in bridge tries to emit `to=data["room_code"]` but `room_code` is missing from payload.
**Why it happens:** `send_chat()` RPC constructs payload before `broadcaster.broadcast()` — easy to forget to include `room_code`.
**How to avoid:** Always include `room_code` in every broadcast payload. Chat event payload must include: `{player_id, player_name, message, timestamp, room_code}`.
**Warning signs:** KeyError in bridge callback handler; chat message not delivered.

---

## Code Examples

### Verified Patterns From Codebase

#### reconnect_player server-side skeleton
```python
# Source: existing game_server.py patterns (register_callback + get_player_view)
@Pyro5.api.expose
def reconnect_player(self, player_id: str, room_code: str, callback_uri: str) -> dict:
    """Re-register callback URI for a player already in the session."""
    with self.lock:
        room = self._player_to_room.get(player_id)
        if room != room_code:
            return {"error": "player not in session"}
        session = self.sessions.get(room_code)
        if session is None:
            return {"error": "session not found"}
        # Update callback URI (player reconnected with a new bridge SID)
        for p in session.players:
            if p.player_id == player_id:
                p.callback_uri = callback_uri
                break
    self.broadcaster.register_callback(player_id, callback_uri)
    # Return full client state (D-03 — reuse get_player_view)
    return self.get_player_view(room_code, player_id)
```

#### Per-turn score history (enables POSTGAME-01 table)
```python
# Source: existing GameSession dataclass (game_server.py:54)
# Add to GameSession:
turn_score_history: list = dataclasses.field(default_factory=list)
# Each entry: {"turn": N, "scores": {player_id: delta}}
# Appended in the on_scoring_phase hook, already called by TurnMachine
```

#### vote state dataclass
```python
# Source: threading.Timer pattern (turn_machine.py:86)
@dataclasses.dataclass
class VoteRecord:
    votes: dict = dataclasses.field(default_factory=dict)  # player_id -> bool
    generation: int = 0
    timer: object = dataclasses.field(default=None, repr=False)
```

#### BridgeCallbackReceiver extensions (chat + player_left + vote events)
```python
# Source: existing BridgeCallbackReceiver pattern (bridge.py:42)
@Pyro5.api.oneway
@Pyro5.api.callback
def on_chat_message(self, data: dict):
    try:
        socketio.emit("chat_message", data, to=data["room_code"])
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_chat_message: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_player_left(self, data: dict):
    try:
        socketio.emit("player_left", data, to=data["room_code"])
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_player_left: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_vote_started(self, data: dict):
    try:
        socketio.emit("vote_started", data, to=data["room_code"])
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_vote_started: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_vote_update(self, data: dict):
    try:
        socketio.emit("vote_update", data, to=data["room_code"])
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_vote_update: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_game_restarting(self, data: dict):
    try:
        socketio.emit("game_restarting", data, to=data["room_code"])
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_game_restarting: {exc}", flush=True)
```

#### Client reconnect logic (TypeScript)
```typescript
// Source: CONTEXT.md D-02 + existing socket.ts pattern
// In GameScreen.tsx useEffect, before join_room emit:
const storedPlayerId = localStorage.getItem('player_id')
const storedRoomCode = roomCode   // from useParams

if (storedPlayerId && storedRoomCode) {
  socket.emit('reconnect_game', { player_id: storedPlayerId, room_code: storedRoomCode },
    (data: GameState) => {
      if (data?.error) { /* show error */ return }
      // Apply restored state same as join_room callback
      applyRestoredState(data)
    })
} else {
  socket.emit('join_room', { room_code: roomCode, player_id: myPlayerId }, ...)
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `handle_disconnect()` immediately calls `leave_game()` | Grace-period timer (D-01): 5s delay | Phase 7 | Enables reconnect without losing session |
| `EventBroadcaster` removes on first permanent failure only | 3 consecutive failure threshold (D-08) | Phase 7 | Avoids removing players on transient network hiccups |
| `game_ended` → client shows static "Jogo encerrado" | `game_ended` → PostGame screen with podium + vote | Phase 7 | Completes the game loop |

**Deprecated/outdated:**
- `GameScreen.tsx` `gameEnded` state renders a static string — replace with navigation to PostGame route.
- `EventBroadcaster` has no failure counter — add in this phase.

---

## Open Questions

1. **Per-turn score history storage**
   - What we know: `GameSession.accumulated_scores` holds cumulative totals. `TurnMachine.on_scoring_phase` callback fires with deltas.
   - What's unclear: Whether to add `turn_score_history` to `GameSession` or derive it from repeated `SCORE_UPDATED` events stored client-side.
   - Recommendation: Store per-turn deltas server-side in `GameSession.turn_score_history` (append in the scoring hook). This makes `get_player_view()` able to return the full history on reconnect, and the PostGame page can request it via a single RPC call without needing to replay events.

2. **Vote majority with 2 players**
   - What we know: Strict majority with 2 players = both must vote yes.
   - What's unclear: If one player disconnects during the vote, the 30s timer will fire. Should a single "yes" from the remaining player restart the game?
   - Recommendation: Evaluate majority against `len(session.players)` at vote-close time. If 1 player remains and voted yes → 1/1 = 100% → game restarts. This is simpler and feels natural.

3. **PostGame route**
   - What we know: `App.tsx` has `/game/:roomCode`; `game_ended` currently shows a static message inside `GameScreen.tsx`.
   - What's unclear: Whether PostGame should be a separate `/postgame/:roomCode` route or a state within `GameScreen.tsx`.
   - Recommendation: New route `/postgame/:roomCode` → cleaner component boundaries, avoids inflating `GameScreen.tsx`. `game_ended` handler navigates via `useNavigate`. On `game_restarting`, navigate back to `/game/:roomCode`.

---

## Environment Availability

> No new external dependencies. All tools confirmed present in Phases 1–6.

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Python 3.11 venv | All server code | confirmed | Used in all prior phases |
| Pyro5 5.16 | RPC layer | confirmed | In requirements.txt |
| Flask-SocketIO 5.6.1 | Bridge | confirmed | In requirements.txt |
| React + Vite (existing) | Frontend | confirmed | Used in all prior phases |
| pytest | Tests | confirmed | In requirements.txt |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` (existing at project root) |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-07 | 3 consecutive callback failures removes player + broadcasts PLAYER_LEFT | unit | `pytest tests/test_unit.py::test_player_removed_on_callback_failure -x` | ❌ Wave 0 |
| INFRA-08 | `reconnect_player()` returns get_player_view() payload | unit | `pytest tests/test_session.py::test_reconnect_player -x` | ❌ Wave 0 |
| SESSION-07 | `leave_game()` host transfer already works | unit | `pytest tests/test_session.py::test_host_transfer_on_leave -x` | ✅ (verify existing) |
| POSTGAME-01 | per-turn history stored in session | unit | `pytest tests/test_scoring.py::test_per_turn_history -x` | ❌ Wave 0 |
| POSTGAME-02 | `start_vote()` broadcasts VOTE_STARTED, sets 30s timer | unit | `pytest tests/test_unit.py::test_vote_started -x` | ❌ Wave 0 |
| POSTGAME-03 | majority yes → GAME_RESTARTING + new image assignments | unit | `pytest tests/test_unit.py::test_vote_majority_restart -x` | ❌ Wave 0 |
| POSTGAME-04 | timer expiry without majority → GAME_ENDED | unit | `pytest tests/test_unit.py::test_vote_timeout_ends_game -x` | ❌ Wave 0 |
| CHAT-01 | `send_chat()` returns ok, triggers broadcast | unit | `pytest tests/test_unit.py::test_send_chat -x` | ❌ Wave 0 |
| CHAT-02 | chat broadcast includes room_code, player_name, message | unit | `pytest tests/test_unit.py::test_chat_broadcast_payload -x` | ❌ Wave 0 |
| CHAT-03/04 | Visual separation | manual | — | manual only |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_unit.py` — add stubs for INFRA-07, POSTGAME-02, POSTGAME-03, POSTGAME-04, CHAT-01, CHAT-02 (file exists, add stubs)
- [ ] `tests/test_session.py` — add stub `test_reconnect_player` (file exists)
- [ ] `tests/test_scoring.py` — add stub `test_per_turn_history` (file exists)

---

## Security Domain

> `security_enforcement` is not explicitly set to false in config.json — treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Session UUID is not a credential — no auth scope |
| V3 Session Management | yes | UUID from localStorage must be validated server-side before re-registering callback; reject unknown UUIDs |
| V4 Access Control | yes | `send_chat` and `submit_vote` must verify player_id belongs to the session |
| V5 Input Validation | yes | Chat message length cap (200 chars); player_id and room_code are non-empty strings |
| V6 Cryptography | no | UUIDs are session identifiers, not secrets; no crypto needed at this scope |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| UUID spoofing — client claims another player's UUID to hijack session | Spoofing | `reconnect_player()` must check UUID exists in server session before re-registering callback. UUID is uuid4 (128-bit random) — not predictable in practice |
| Vote stuffing — client submits multiple votes | Tampering | `submit_vote()` checks `player_id in vote_record.votes` before counting; second submission is ignored |
| Chat spam | Denial of service | Length cap (200 chars) + no rate-limit needed at 2–4 player scale |
| Orphaned grace-period timers if bridge crashes | Denial of service | Timers are daemon threads; bridge restart clears all state; GameServer retains player in session until timer fires or until next broadcast failure triggers removal |

---

## Sources

### Primary (HIGH confidence — codebase inspection)

- `bridge/bridge.py:557–570` — current `handle_disconnect()` implementation, confirmed location for grace period change
- `bridge/bridge.py:80–90` — confirmed `on_host_changed` route, SESSION-07 already wired
- `server/game_server.py:321–357` — `get_player_view()` confirmed returns phase, scores, image assignment, player list
- `server/game_server.py:897–952` — `leave_game()` confirmed handles host transfer + HOST_CHANGED broadcast
- `server/event_broadcaster.py:40–84` — confirmed broadcast pattern; permanent vs. transient failure distinction at lines 71–79
- `server/turn_machine.py:114–195` — `threading.Timer` + generation counter pattern confirmed
- `frontend/src/pages/GameScreen.tsx:137–244` — confirmed current reconnect state (join_room emit, no reconnect_game event)
- `frontend/src/socket.ts` — confirmed singleton socket pattern
- `.planning/config.json` — `nyquist_validation: true`, `commit_docs: true`

### Secondary (HIGH confidence — locked decisions)

- `.planning/phases/07-reconnection-end-of-game/07-CONTEXT.md` — all D-0x decisions, canonical refs
- `.planning/REQUIREMENTS.md` — INFRA-07, INFRA-08, SESSION-07, POSTGAME-01–04, CHAT-01–04

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Per-turn score history is not currently stored in `GameSession` (only accumulated totals are) | Code Examples | If history is already stored somewhere, the Wave 0 schema addition is redundant — low risk |
| A2 | `test_session.py::test_host_transfer_on_leave` already covers SESSION-07 | Validation Architecture | If the test does not exist, Wave 0 needs to add it — low risk |
| A3 | The PostGame screen should be a new `/postgame/:roomCode` route rather than a state in GameScreen | Open Questions | If planner chooses same-route state approach, component boundary changes but logic is identical |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all verified in existing codebase
- Architecture: HIGH — all patterns verified in existing code files
- Pitfalls: HIGH — derived from direct inspection of threading patterns used in prior phases
- Vote semantics: MEDIUM — D-06 is Claude's discretion; recommendation made but planner should confirm

**Research date:** 2026-05-15
**Valid until:** Phase 8 start (stable codebase, no fast-moving external dependencies)
