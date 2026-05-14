# Phase 5: Exchange + Spy Mechanics - Research

**Researched:** 2026-05-14
**Domain:** Pyro5 RPC game mechanics — private exchange state machine, probabilistic spy resolution, targeted event delivery
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** EXCHANGE_PHASE and SPY_PHASE are two separate sequential phases with independent timers. No change to `PHASE_SEQUENCE` in `turn_machine.py`.
- **D-02:** Spy targets are completed exchanges only — both players accepted AND both submitted their private hint word before EXCHANGE_PHASE ended.
- **D-03:** Exchange state lives in new fields on `TurnState` in `server/turn_state.py`. New fields: `exchanges: dict[str, ExchangeRecord]`, `completed_exchanges: list[str]`, `exchange_participants: set[str]`, `spy_attempts: set[str]`.
- **D-04:** `exchange_id = str(uuid.uuid4())[:8]` — 8-char truncated UUID.
- **D-05:** When EXCHANGE_PHASE timer fires, incomplete exchanges are dropped silently — no cancellation broadcast.
- **D-06:** If `completed_exchanges` is empty when EXCHANGE_PHASE ends, TurnMachine jumps directly to SCORING_PHASE, skipping SPY_PHASE.
- **D-07:** Phase 5 is backend + bridge only. No new frontend panels (deferred to Phase 8, UI-06).

### Claude's Discretion

- `ExchangeRecord` placement: co-located in `turn_state.py` vs. separate `exchange_record.py`.
- `attempt_spy()` probability: `random.random() < 0.3` vs. `random.choices()`.
- `PHASE_CHANGED` to SPY_PHASE payload: include `spy_targets: [exchange_id, ...]` list vs. `spy_target_count: N`.

### Deferred Ideas (OUT OF SCOPE)

- Spy success bonus (+5pts) — v2.
- Exchange/spy UI action panels in GameScreen — Phase 8 (UI-06).
- Configurable spy probability by host — v2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXCHANGE-01 | During EXCHANGE_PHASE player requests private exchange via `request_exchange(player_id, target_player)`, returns exchange_id | Covered by new RPC method pattern matching `submit_hint()`; `ExchangeRecord` state on `TurnState`; phase guard checks `current_phase == "EXCHANGE_PHASE"` |
| EXCHANGE-02 | Receiver gets private notification; can accept/reject via `respond_exchange(player_id, exchange_id, accept)` | Covered by targeted delivery via `broadcaster.send_to_player()` (already exists); `ExchangeRecord.status` transitions |
| EXCHANGE-03 | If accepted, both submit private hint via `submit_exchange_hint(player_id, exchange_id, hint_word)` — can be true or false | Covered by `ExchangeRecord.requester_hint` / `target_hint` fields; completion detection when both set |
| EXCHANGE-04 | Server broadcasts public `EXCHANGE_COMPLETED` without revealing hint content | Covered by `broadcaster.broadcast()` with payload containing only IDs, not hint words |
| EXCHANGE-05 | Private hints delivered only to the two participants via targeted event | Covered by `broadcaster.send_to_player()` called twice — once per participant |
| EXCHANGE-06 | Each player can participate in at most one exchange per turn | Covered by `exchange_participants: set[str]` guard on `TurnState` |
| SPY-01 | During SPY_PHASE player attempts to spy on a completed exchange via `attempt_spy(player_id, exchange_id)` | Covered by new RPC method; phase guard checks `current_phase == "SPY_PHASE"` |
| SPY-02 | 30% discovery probability; if discovered: spy loses 10pts, public `SPY_DISCOVERED` broadcast with spy name | Covered by `random.random() < 0.3`; score delta applied to `session.accumulated_scores`; `broadcaster.broadcast()` |
| SPY-03 | If not discovered: spy receives both private hints silently, no public event | Covered by two `broadcaster.send_to_player()` calls; no public broadcast in this branch |
| SPY-04 | Player cannot spy on exchanges they participated in | Covered by checking `spy_id not in (exchange.requester_id, exchange.target_id)` |
| SPY-05 | Each player can spy on at most one exchange per turn | Covered by `spy_attempts: set[str]` guard on `TurnState` |
</phase_requirements>

---

## Summary

Phase 5 is a pure server + bridge extension — no new infrastructure, no new frameworks, no new external dependencies. The entire phase extends three existing files (`turn_state.py`, `turn_machine.py`, `game_server.py`) and adds handlers to the bridge (`bridge.py`). Every pattern required already exists in the codebase and was validated in Phases 1–4.

The key domain insight is that **exchange state is a small state machine within a phase**: `pending → accepted|rejected` and `accepted → completed` (when both hints submitted). The server is the sole authority on state transitions. The bridge never validates or filters — it passes calls through to the game server and routes push events to the correct Socket.IO targets (room broadcast vs. targeted SID emit).

The only genuinely new behavior is the conditional `_compute_next()` branch (D-06, skip SPY_PHASE when no completed exchanges) and the probabilistic spy resolution (`random.random() < 0.3`). Both are 5-line additions to existing methods. The score penalty for a discovered spy follows the exact same pattern as `_accumulate_scores()` — mutate `session.accumulated_scores` under the lock, then `broadcaster.broadcast()` after the lock exits.

**Primary recommendation:** Implement in four sequential waves: (1) `ExchangeRecord` dataclass + new `TurnState` fields, (2) `_compute_next()` SPY_PHASE skip logic, (3) four new `GameServer` RPC methods, (4) bridge push methods and Socket.IO action handlers.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Exchange request/response lifecycle | API/Backend (GameServer) | — | All game state lives in GameServer under RLock; exchange state follows same pattern as hints/guesses |
| Private hint submission and completion detection | API/Backend (GameServer) | — | Completion requires knowing both requester_hint and target_hint are set; only server has full state |
| Public exchange broadcast (EXCHANGE_COMPLETED) | API/Backend → EventBroadcaster | Bridge (forward) | Pattern established by Phase 4: server calls broadcaster, which calls bridge on_* method, which socketio.emit to room |
| Private event delivery (exchange hints, spy success) | API/Backend → EventBroadcaster.send_to_player | Bridge (SID lookup) | `send_to_player()` already implemented; bridge's `on_*` checks `target_player_id` in payload, emits to SID |
| SPY_PHASE auto-skip logic | API/Backend (TurnMachine._compute_next) | — | TurnMachine is sole owner of phase sequencing; the condition checks turn_state data it already holds |
| Spy probability resolution | API/Backend (GameServer.attempt_spy) | — | Must be server-side; client cannot be trusted with probability resolution |
| Score penalty application (spy discovered) | API/Backend (GameServer) | — | Follows `_accumulate_scores()` pattern — mutate accumulated_scores under lock |
| Routing push events to correct clients | Bridge (BridgeCallbackReceiver) | — | Bridge holds `_player_to_sid` map; server knows nothing about Socket.IO SIDs |

---

## Standard Stack

### Core (verified in codebase — no new installs required)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| Pyro5 | 5.16 | RPC backbone, @expose, @oneway, @callback decorators | Already installed; all patterns confirmed in Phases 1–4 [VERIFIED: codebase] |
| Flask-SocketIO | 5.6.1 | Bridge WebSocket server, `socketio.emit()` targeted delivery | Already installed; `async_mode='threading'` confirmed [VERIFIED: codebase] |
| Python `uuid` | stdlib | `str(uuid.uuid4())[:8]` for exchange_id (D-04) | Already used for player_id generation in `game_server.py` [VERIFIED: codebase] |
| Python `random` | stdlib | `random.random() < 0.3` for spy probability | Already imported in `game_server.py` [VERIFIED: codebase] |
| Python `dataclasses` | stdlib | `@dataclasses.dataclass` for `ExchangeRecord` | Already used for `TurnState`, `PlayerInfo`, `GameSession` [VERIFIED: codebase] |
| Python `typing` | stdlib | `Optional[str]` for nullable hint fields | Already used in `turn_machine.py` [VERIFIED: codebase] |

**No new packages to install. Phase 5 uses only the existing venv.**

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (Player A)                Bridge Process              GameServer Process
    |                                  |                              |
    |--[socket: request_exchange]----->|                              |
    |                                  |--[RPC: request_exchange()]-->|
    |                                  |                              | [acquire lock]
    |                                  |                              | ExchangeRecord created (status=pending)
    |                                  |                              | exchange_participants.add(requester_id)
    |                                  |                              | [release lock]
    |                                  |<--[return: {ok,exchange_id}]-|
    |<--[ack: {ok, exchange_id}]--------|                              |
    |                                  |                              |
    |                  [broadcaster.send_to_player(target_id, "exchange_requested", ...)]
    |                                  |<--[Pyro5 @oneway callback]---|
    |                  [SID lookup for target_id]                      |
    |                [socketio.emit("exchange_requested", data, to=target_sid)]
    |                                  |                              |
Browser (Player B)                    |                              |
    |<--[socket: exchange_requested]---|                              |
    |                                  |                              |
    |--[socket: respond_exchange]----->|                              |
    |                                  |--[RPC: respond_exchange()]-->|
    |                                  |                              | status → accepted|rejected
    |                                  |                              | [release lock]
    |<--[ack: {ok}]---------------------|                              |
    |                                  |                              |
    |  [if accepted: both submit submit_exchange_hint() via socket]   |
    |                                  |--[RPC: submit_exchange_hint()]-->|
    |                                  |                              | requester_hint or target_hint set
    |                                  |                              | [if both set: status→completed]
    |                                  |                              | completed_exchanges.append(exchange_id)
    |                                  |                              | [release lock]
    |                                  |                              |
    |  [broadcaster.broadcast("exchange_completed", public_data)]     |
    |<--[socket: exchange_completed]---|                              |
    |                                  |                              |
    |  [broadcaster.send_to_player(requester_id, "exchange_hints", ...)]
    |  [broadcaster.send_to_player(target_id, "exchange_hints", ...)] |
    |<--[socket: exchange_hints (private)]------------------------------|
```

### SPY_PHASE Skip Decision Flow

```
EXCHANGE_PHASE timer fires
       |
       v
_compute_next("EXCHANGE_PHASE")
       |
       v
[with self.lock]
  len(current_turn_state.completed_exchanges) == 0?
       |
      YES --> return "SCORING_PHASE"
       |
       NO --> return "SPY_PHASE"
```

### ExchangeRecord State Machine

```
[created]
    |
    v
status = "pending"
    |
    +--[respond_exchange(accept=False)]--> status = "rejected"  (terminal)
    |
    +--[respond_exchange(accept=True)]---> status = "accepted"
                                              |
                                              v
                              [submit_exchange_hint() called for both]
                                              |
                              both requester_hint and target_hint set?
                                              |
                                             YES --> status = "completed"
                                              |      completed_exchanges.append(id)
                                              |      broadcast EXCHANGE_COMPLETED
                                              |      send private hints to both
                                              |
                                             NO  --> stay "accepted" (timer drops it silently)
```

### Recommended Project Structure (additions only)

```
server/
├── turn_state.py      # Add ExchangeRecord dataclass + new TurnState fields
├── turn_machine.py    # Modify _compute_next() — 8-line addition
└── game_server.py     # Add 4 new @Pyro5.api.expose RPC methods

bridge/
└── bridge.py          # Add 4 BridgeCallbackReceiver.on_* push methods
                       # Add 4 @socketio.on() action handlers

tests/
└── test_exchange.py   # New test file — all EXCHANGE-xx and SPY-xx tests
```

### Pattern 1: ExchangeRecord dataclass (co-located in turn_state.py)

**What:** A frozen-field dataclass co-located with `TurnState` — no separate file needed (Claude's Discretion).
**When to use:** State that has 2–5 fields, belongs to one domain, and is only ever instantiated in one place.

```python
# Source: existing codebase pattern (TurnState in server/turn_state.py)
import dataclasses
from typing import Optional

@dataclasses.dataclass
class ExchangeRecord:
    """Tracks one 1-on-1 private hint exchange within a turn."""
    requester_id: str
    target_id: str
    status: str = "pending"           # "pending" | "accepted" | "rejected" | "completed"
    requester_hint: Optional[str] = None
    target_hint: Optional[str] = None
```

### Pattern 2: TurnState new fields (follow existing default_factory pattern)

```python
# Source: existing codebase — TurnState in server/turn_state.py
@dataclasses.dataclass
class TurnState:
    turn_number: int
    player_ids: list
    hints_submitted: dict = dataclasses.field(default_factory=dict)
    guesses_made: dict = dataclasses.field(default_factory=dict)
    correct_guesses: list = dataclasses.field(default_factory=list)
    image_assignments: dict = dataclasses.field(default_factory=dict)
    # --- Phase 5 additions ---
    exchanges: dict = dataclasses.field(default_factory=dict)              # exchange_id -> ExchangeRecord
    completed_exchanges: list = dataclasses.field(default_factory=list)    # ordered list of exchange_ids
    exchange_participants: set = dataclasses.field(default_factory=set)    # player_ids that used their slot
    spy_attempts: set = dataclasses.field(default_factory=set)             # player_ids that used their spy slot
```

### Pattern 3: _compute_next() conditional branch

**What:** Conditional return when transitioning out of EXCHANGE_PHASE.
**Where:** `server/turn_machine.py` — `_compute_next()` method.

```python
# Source: existing codebase pattern — _compute_next() in turn_machine.py
def _compute_next(self, current_phase: str) -> str:
    with self.lock:
        if current_phase == "TURN_END":
            if self.current_turn >= self.max_turns:
                return "GAME_ENDED"
            self.current_turn += 1
            return "HINT_PHASE"
        # Phase 5 addition: skip SPY_PHASE if no completed exchanges (D-06)
        if current_phase == "EXCHANGE_PHASE":
            ts = self.current_turn_state
            if ts is None or not ts.completed_exchanges:
                return "SCORING_PHASE"
            return "SPY_PHASE"
        idx = PHASE_SEQUENCE.index(current_phase)
        return PHASE_SEQUENCE[idx + 1]
```

### Pattern 4: RPC method template (request_exchange)

**What:** New @Pyro5.api.expose method following the lock-then-broadcast-outside pattern.
**Source:** Verified against `submit_hint()` and `submit_guess()` in `server/game_server.py`.

```python
# Source: existing codebase — submit_hint() pattern in game_server.py
def request_exchange(self, player_id: str, target_player_id: str) -> dict:
    broadcast_data = None

    with self.lock:
        room_code = self._player_to_room.get(player_id)
        session = self.sessions.get(room_code) if room_code else None
        if session is None or session.turn_machine is None:
            return {"error": "session_not_found"}
        turn_machine = session.turn_machine
        if turn_machine.current_phase != "EXCHANGE_PHASE":
            return {"error": "invalid_phase"}
        turn_state = turn_machine.current_turn_state
        if turn_state is None:
            return {"error": "turn_not_started"}
        if player_id == target_player_id:
            return {"error": "cannot_exchange_with_self"}
        if player_id in turn_state.exchange_participants:
            return {"error": "already_used_exchange"}
        if target_player_id in turn_state.exchange_participants:
            return {"error": "target_already_exchanging"}
        # Validate target is in session
        player_ids_in_session = {p.player_id for p in session.players}
        if target_player_id not in player_ids_in_session:
            return {"error": "target_not_found"}

        exchange_id = str(uuid.uuid4())[:8]
        record = ExchangeRecord(requester_id=player_id, target_id=target_player_id)
        turn_state.exchanges[exchange_id] = record
        turn_state.exchange_participants.add(player_id)
        turn_state.exchange_participants.add(target_player_id)

        # Private notification payload to target only
        broadcast_data = {
            "target_player_id": target_player_id,
            "room_code": room_code,
            "exchange_id": exchange_id,
            "requester_id": player_id,
        }

    # send_to_player OUTSIDE the lock
    self.broadcaster.send_to_player(
        target_player_id, "exchange_requested", broadcast_data
    )
    return {"ok": True, "exchange_id": exchange_id}
```

### Pattern 5: Spy probability resolution (attempt_spy)

**What:** `random.random() < 0.3` for 30% discovery probability. Apply score penalty under lock, broadcast outside.

```python
# Source: existing codebase — _accumulate_scores() pattern in game_server.py
# random already imported in game_server.py
import random

def attempt_spy(self, player_id: str, exchange_id: str) -> dict:
    discovered_data = None
    success_data = None
    player_name = None

    with self.lock:
        room_code = self._player_to_room.get(player_id)
        session = self.sessions.get(room_code) if room_code else None
        if session is None or session.turn_machine is None:
            return {"error": "session_not_found"}
        turn_machine = session.turn_machine
        if turn_machine.current_phase != "SPY_PHASE":
            return {"error": "invalid_phase"}
        turn_state = turn_machine.current_turn_state
        if turn_state is None:
            return {"error": "turn_not_started"}
        if player_id in turn_state.spy_attempts:
            return {"error": "already_used_spy"}
        if exchange_id not in turn_state.completed_exchanges:
            return {"error": "exchange_not_found"}
        record = turn_state.exchanges[exchange_id]
        if player_id in (record.requester_id, record.target_id):
            return {"error": "cannot_spy_own_exchange"}   # SPY-04

        turn_state.spy_attempts.add(player_id)
        player_name = next(
            (p.player_name for p in session.players if p.player_id == player_id), player_id
        )

        if random.random() < 0.3:   # 30% discovery
            session.accumulated_scores[player_id] = (
                session.accumulated_scores.get(player_id, 0) - 10
            )
            discovered_data = {
                "room_code": room_code,
                "spy_id": player_id,
                "spy_name": player_name,
                "exchange_id": exchange_id,
                "penalty": -10,
            }
        else:
            success_data = {
                "target_player_id": player_id,
                "room_code": room_code,
                "exchange_id": exchange_id,
                "hints": [
                    {"from_player_id": record.requester_id, "hint_word": record.requester_hint},
                    {"from_player_id": record.target_id, "hint_word": record.target_hint},
                ],
            }

    # Broadcast OUTSIDE the lock
    if discovered_data:
        self.broadcaster.broadcast("spy_discovered", discovered_data)
        return {"ok": True, "discovered": True}
    else:
        self.broadcaster.send_to_player(player_id, "spy_success", success_data)
        return {"ok": True, "discovered": False}
```

### Pattern 6: BridgeCallbackReceiver push method (targeted private delivery)

**What:** Private events use `target_player_id` in payload + SID lookup, following the `on_object_assigned` pattern.
**Source:** Verified in `bridge/bridge.py` — `on_object_assigned()` method.

```python
# Source: existing codebase — on_object_assigned() in bridge/bridge.py
@Pyro5.api.oneway
@Pyro5.api.callback
def on_exchange_requested(self, data: dict):
    """Private notification to exchange target; uses SID lookup."""
    target_player_id = data.get("target_player_id")
    with _sid_lock:
        sid = _player_to_sid.get(target_player_id)
    if not sid:
        print(f"[BRIDGE] SID not found for exchange target {target_player_id}", flush=True)
        return
    try:
        socketio.emit("exchange_requested", data, to=sid)
        print(f"[BRIDGE] exchange_requested -> sid={sid}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_exchange_requested: {exc}", flush=True)
```

### Anti-Patterns to Avoid

- **Broadcasting inside the lock:** All `broadcaster.broadcast()` and `broadcaster.send_to_player()` calls MUST happen after `with self.lock:` exits. Violation causes deadlock when the Pyro5 callback I/O path re-enters the same lock. Pattern is established and tested in Phases 1–4.
- **Modifying accumulated_scores outside the lock:** The spy penalty (-10pts) mutates `session.accumulated_scores`. This mutation MUST happen inside `with self.lock:`. Only the subsequent broadcast is outside.
- **Sharing Pyro5 proxies across threads:** Bridge's `get_game_server_proxy()` already prevents this via `threading.local()`. No new proxy code needed.
- **Accepting exchange actions outside EXCHANGE_PHASE:** The phase guard (`turn_machine.current_phase != "EXCHANGE_PHASE"`) must appear in every exchange RPC method. Spy methods check for `"SPY_PHASE"` equivalently.
- **Adding exchange_participants without holding lock:** `turn_state.exchange_participants.add()` must run inside `with self.lock:`. Python sets are not thread-safe without the lock.
- **Allowing both players to "use" the exchange slot at request time vs. completion:** The CONTEXT.md decision is to reserve both slots at request time (`exchange_participants.add(requester_id)` and `exchange_participants.add(target_player_id)` in `request_exchange()`). This prevents a player from sending multiple requests while one is pending. The planner must preserve this.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Targeted Socket.IO delivery | Custom routing table or SID filter | `socketio.emit(event, data, to=sid)` | Already implemented; `_player_to_sid` map maintained in bridge [VERIFIED: codebase] |
| Per-player-per-turn enforcement | Custom counter or flag | `set` field on `TurnState` + membership check | Pattern established by `guesses_made` dict in Phase 4; sets are simpler for binary membership |
| Thread-safe state mutation | Fine-grained per-field locks | Reuse `GameServer.lock` (RLock) for all TurnState mutations | All GameServer methods share a single RLock; adding per-exchange locks would risk deadlock |
| Probability resolution | Client-side random or server-side cache | `random.random() < 0.3` per call | Server is authoritative; standard Python stdlib; stateless per spy attempt |

**Key insight:** Every mechanism needed for Phase 5 is already implemented in the codebase. The task is additive — new fields, new methods, new push handlers — not replacement or refactoring.

---

## Common Pitfalls

### Pitfall 1: Broadcasting inside the RLock (deadlock)
**What goes wrong:** `broadcaster.broadcast()` or `broadcaster.send_to_player()` called while holding `self.lock` causes deadlock when the Pyro5 callback delivery triggers a re-entrant call back into the server.
**Why it happens:** All broadcast methods do network I/O (creating a Pyro5 Proxy, calling a method on `BridgeCallbackReceiver`). If the bridge's callback handler tries to call back into GameServer (even indirectly), the RLock blocks forever.
**How to avoid:** Snapshot all data needed for broadcast inside the lock, then exit `with self.lock:`, then call `broadcaster.*` outside. Every existing GameServer method follows this pattern.
**Warning signs:** Server hangs during EXCHANGE_COMPLETED broadcast; timeout errors in bridge logs.

### Pitfall 2: exchange_participants set reserved too late
**What goes wrong:** If both `requester_id` and `target_id` are only added to `exchange_participants` after the exchange completes (not at request time), a player can send two simultaneous requests before either resolves.
**Why it happens:** Naively checking "did they complete an exchange?" misses the in-flight state.
**How to avoid:** Reserve both slots immediately in `request_exchange()` before returning. This is the decision from CONTEXT.md D-03 — the set exists for this exact purpose.
**Warning signs:** Two `EXCHANGE_COMPLETED` broadcasts for the same player pair in one turn.

### Pitfall 3: SPY_PHASE skip reads stale turn_state
**What goes wrong:** `_compute_next()` reads `self.current_turn_state.completed_exchanges` but `current_turn_state` could be `None` if EXCHANGE_PHASE started before HINT_PHASE created it (unlikely but guarded against in existing code).
**Why it happens:** `current_turn_state` is created in `_advance_to("HINT_PHASE")`. By EXCHANGE_PHASE it is always set. However the None-check is cheap insurance.
**How to avoid:** `if ts is None or not ts.completed_exchanges: return "SCORING_PHASE"`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'completed_exchanges'` in server logs.

### Pitfall 4: Spy on non-completed exchange
**What goes wrong:** During SPY_PHASE, `attempt_spy()` is called with an exchange_id that was rejected or never completed. The record exists in `turn_state.exchanges` but is NOT in `turn_state.completed_exchanges`.
**Why it happens:** Client could construct an exchange_id from network observation or UI state.
**How to avoid:** Guard `if exchange_id not in turn_state.completed_exchanges: return {"error": "exchange_not_found"}`. Do not check `turn_state.exchanges` directly for spy eligibility.
**Warning signs:** Spy success on a rejected exchange.

### Pitfall 5: Double-completion of an exchange
**What goes wrong:** Both players call `submit_exchange_hint()` concurrently; both threads see the other hint as `None` and neither triggers the completion logic.
**Why it happens:** Race condition without the lock. With the lock, the second thread sees the first hint already set.
**How to avoid:** All reads and writes of `ExchangeRecord.requester_hint` / `target_hint` and the `completed_exchanges.append()` must happen inside `with self.lock:`. The RLock guarantees sequential execution.
**Warning signs:** Exchange never reaches `status="completed"` even though both players submitted.

### Pitfall 6: respond_exchange for a non-pending exchange
**What goes wrong:** Player B accepts an exchange that was already accepted (or rejected) by a concurrent call. The exchange status is double-set.
**Why it happens:** Without a status guard, `respond_exchange()` blindly overwrites status.
**How to avoid:** Guard `if record.status != "pending": return {"error": "exchange_not_pending"}` inside the lock.
**Warning signs:** `status` becoming `"accepted"` when it was already `"rejected"`.

---

## Code Examples

### submit_exchange_hint: completion detection under lock

```python
# Source: existing codebase pattern — submit_guess() in game_server.py
def submit_exchange_hint(self, player_id: str, exchange_id: str, hint_word: str) -> dict:
    broadcast_data = None
    private_deliveries = []  # list of (player_id, event_type, data) tuples

    with self.lock:
        # ... phase and exchange validation ...
        record = turn_state.exchanges.get(exchange_id)
        if record is None or record.status != "accepted":
            return {"error": "exchange_not_accepted"}
        if player_id == record.requester_id:
            if record.requester_hint is not None:
                return {"error": "already_submitted"}
            record.requester_hint = str(hint_word).strip()[:50]
        elif player_id == record.target_id:
            if record.target_hint is not None:
                return {"error": "already_submitted"}
            record.target_hint = str(hint_word).strip()[:50]
        else:
            return {"error": "not_participant"}

        # Check for completion
        if record.requester_hint is not None and record.target_hint is not None:
            record.status = "completed"
            turn_state.completed_exchanges.append(exchange_id)
            broadcast_data = {
                "room_code": room_code,
                "exchange_id": exchange_id,
                "requester_id": record.requester_id,
                "target_id": record.target_id,
            }
            private_deliveries = [
                (record.requester_id, "exchange_hints", {
                    "target_player_id": record.requester_id,
                    "room_code": room_code,
                    "exchange_id": exchange_id,
                    "from_player_id": record.target_id,
                    "hint_word": record.target_hint,
                }),
                (record.target_id, "exchange_hints", {
                    "target_player_id": record.target_id,
                    "room_code": room_code,
                    "exchange_id": exchange_id,
                    "from_player_id": record.requester_id,
                    "hint_word": record.requester_hint,
                }),
            ]

    # All broadcasts OUTSIDE the lock
    if broadcast_data:
        self.broadcaster.broadcast("exchange_completed", broadcast_data)
    for target_id, event_type, data in private_deliveries:
        self.broadcaster.send_to_player(target_id, event_type, data)
    return {"ok": True}
```

### PHASE_CHANGED for SPY_PHASE with spy_targets list (Claude's Discretion recommendation)

Recommendation: include `spy_targets: [exchange_id, ...]` list in the `PHASE_CHANGED` payload when advancing to SPY_PHASE. This is the more useful option for Phase 8 UI. The `spy_targets` list is appended to `broadcast_data` in `_advance_to()` before the broadcast, following the existing `"hints"` key pattern for GUESS_PHASE.

```python
# Source: existing codebase — _advance_to() in turn_machine.py, GUESS_PHASE branch
# Add this to the EXCHANGE_PHASE -> SPY_PHASE transition in _advance_to():
if phase == "SPY_PHASE" and self.current_turn_state is not None:
    broadcast_data["spy_targets"] = list(self.current_turn_state.completed_exchanges)
```

### Bridge Socket.IO handler template (respond_exchange)

```python
# Source: existing codebase — handle_submit_hint() in bridge/bridge.py
@socketio.on("respond_exchange")
def handle_respond_exchange(data):
    """Forward exchange acceptance/rejection to GameServer."""
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "sessao nao encontrada"}
    proxy = get_game_server_proxy()
    result = proxy.respond_exchange(
        player_id,
        (data or {}).get("exchange_id", ""),
        bool((data or {}).get("accept", False)),
    )
    print(f"[BRIDGE] respond_exchange from player {player_id} -> {result}", flush=True)
    return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual UUID formatting | `str(uuid.uuid4())[:8]` | Phase 2 (room code pattern) | Consistent with room code generation style [VERIFIED: codebase] |
| Separate score update call | Inline `accumulated_scores` mutation + broadcast | Phase 4 | Spy penalty follows same inline pattern — no separate scoring method needed |

**No deprecated approaches in scope for Phase 5.** All patterns are the current established codebase standard.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `exchange_participants` reserves both requester and target slots at request time (not at accept or complete time) | Architecture Patterns, Pattern 4, Pitfall 2 | If wrong: race condition allowing double-requests; fix would require changing slot reservation logic |
| A2 | `spy_targets` list (vs. count) is preferred for SPY_PHASE `PHASE_CHANGED` payload (Claude's Discretion) | Code Examples | If wrong (Phase 8 prefers count): payload change is backward-incompatible; low risk since no UI yet |
| A3 | Score penalty for spy discovery is applied immediately in `attempt_spy()` under the lock (not deferred to SCORING_PHASE) | Code Examples, Pattern 5 | If wrong: scores visible via `get_scores()` would be stale until SCORING_PHASE; semantically acceptable alternative |

---

## Open Questions

1. **Double-hint semantics for exchange participants**
   - What we know: `submit_exchange_hint()` lets each participant submit "one word — can be true or false" (EXCHANGE-03).
   - What's unclear: REQUIREMENTS.md does not specify what happens if a participant also submitted a public hint in HINT_PHASE. The exchange hint is a separate field, so no conflict in data model.
   - Recommendation: Treat them as independent. No cross-validation needed.

2. **exchange_participants blocks target before they respond**
   - What we know: Adding `target_player_id` to `exchange_participants` at request time means the target cannot initiate their own exchange with anyone else — even if they reject the incoming request.
   - What's unclear: Is this the intended semantic, or should rejection restore the target's exchange slot?
   - Recommendation: The CONTEXT.md D-03 defines the field without specifying slot-restoration on rejection. Implement without restoration for MVP (simpler, one turn is short). A well-scoped follow-up issue can relax this.

3. **SPY_PHASE `spy_targets` payload when phase is entered manually via `advance_phase()`**
   - What we know: `advance_phase_manual()` calls `_advance_to(next_phase)` which calls `_compute_next()`. For a test/operator advance from EXCHANGE_PHASE with no completed exchanges, it would skip SPY_PHASE and go to SCORING_PHASE.
   - What's unclear: If the operator manually advances INTO SPY_PHASE directly (bypassing the conditional), `spy_targets` would be empty.
   - Recommendation: This is a test-only edge case. Operator manual advance behavior is not validated by Phase 5 success criteria. No special handling needed.

---

## Environment Availability

All Phase 5 dependencies are stdlib or already-installed packages. No new tools required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 venv | All code | Yes | 3.11 | — |
| Pyro5 | GameServer RPC, BridgeCallbackReceiver | Yes | 5.16 | — |
| Flask-SocketIO | Bridge handlers, socketio.emit() | Yes | 5.6.1 | — |
| pytest | Test suite | Yes | 8.3.5 | — |
| `uuid` (stdlib) | exchange_id generation | Yes | stdlib | — |
| `random` (stdlib) | spy probability | Yes | stdlib | — |
| `dataclasses` (stdlib) | ExchangeRecord | Yes | stdlib | — |

**No missing dependencies.**

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | pytest.ini (exists in project root) |
| Quick run command | `python -m pytest tests/test_exchange.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXCHANGE-01 | `request_exchange()` returns `{ok, exchange_id}`; creates ExchangeRecord in turn_state | unit | `python -m pytest tests/test_exchange.py::test_request_exchange -x` | No — Wave 0 |
| EXCHANGE-01 | `request_exchange()` in wrong phase returns `invalid_phase` | unit | `python -m pytest tests/test_exchange.py::test_request_exchange_wrong_phase -x` | No — Wave 0 |
| EXCHANGE-02 | `respond_exchange(accept=True)` transitions status to accepted | unit | `python -m pytest tests/test_exchange.py::test_respond_exchange_accept -x` | No — Wave 0 |
| EXCHANGE-02 | `respond_exchange(accept=False)` transitions status to rejected | unit | `python -m pytest tests/test_exchange.py::test_respond_exchange_reject -x` | No — Wave 0 |
| EXCHANGE-03 | `submit_exchange_hint()` by both parties sets status to completed | unit | `python -m pytest tests/test_exchange.py::test_submit_exchange_hint_completes -x` | No — Wave 0 |
| EXCHANGE-04 | `EXCHANGE_COMPLETED` broadcast contains no hint content | unit | `python -m pytest tests/test_exchange.py::test_exchange_completed_payload -x` | No — Wave 0 |
| EXCHANGE-05 | Private hints delivered to both participants after completion | unit | `python -m pytest tests/test_exchange.py::test_private_hints_delivered -x` | No — Wave 0 |
| EXCHANGE-06 | Second `request_exchange()` from same player returns `already_used_exchange` | unit | `python -m pytest tests/test_exchange.py::test_exchange_one_per_turn -x` | No — Wave 0 |
| SPY-01 | `attempt_spy()` in EXCHANGE_PHASE returns `invalid_phase` | unit | `python -m pytest tests/test_exchange.py::test_spy_wrong_phase -x` | No — Wave 0 |
| SPY-02 | Over 100 calls, approximately 30% result in `discovered: True` + score penalty | unit (statistical) | `python -m pytest tests/test_exchange.py::test_spy_discovery_probability -x` | No — Wave 0 |
| SPY-03 | Undetected spy receives both hints silently; no public broadcast | unit | `python -m pytest tests/test_exchange.py::test_spy_success_private -x` | No — Wave 0 |
| SPY-04 | Exchange participant attempting spy returns `cannot_spy_own_exchange` | unit | `python -m pytest tests/test_exchange.py::test_spy_own_exchange_rejected -x` | No — Wave 0 |
| SPY-05 | Second `attempt_spy()` from same player returns `already_used_spy` | unit | `python -m pytest tests/test_exchange.py::test_spy_one_per_turn -x` | No — Wave 0 |
| D-06 | `_compute_next("EXCHANGE_PHASE")` with empty `completed_exchanges` returns `"SCORING_PHASE"` | unit | `python -m pytest tests/test_exchange.py::test_spy_phase_skipped_when_no_exchanges -x` | No — Wave 0 |
| D-06 | `_compute_next("EXCHANGE_PHASE")` with one completed exchange returns `"SPY_PHASE"` | unit | `python -m pytest tests/test_exchange.py::test_spy_phase_entered_when_exchange_exists -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_exchange.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green (currently 34 tests) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_exchange.py` — covers all 15 test cases above (EXCHANGE-01 through SPY-05 + D-06)
- [ ] `FakeBroadcaster` helper can be imported from `tests/test_turn_state.py` or duplicated inline (no `conftest.py` needed — existing tests use module-level helpers)

---

## Security Domain

> security_enforcement not set to false in config — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in scope; player_id resolved from SID map in bridge |
| V3 Session Management | Partial | `_sid_to_player` map validated on every handler call; player not found → `{"error": "sessao nao encontrada"}` |
| V4 Access Control | Yes | Phase guard (EXCHANGE_PHASE / SPY_PHASE), self-spy guard (SPY-04), participant guard |
| V5 Input Validation | Yes | `hint_word` stripped and capped at 50 chars (same as existing); `exchange_id` validated against turn_state dict |
| V6 Cryptography | No | No cryptographic operations |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Player spoofing target_player_id to intercept exchanges | Spoofing | Server resolves caller from SID (`_sid_to_player`); `target_player_id` in payload is server-authoritative |
| Replaying exchange_id across turns | Repudiation | `turn_state.exchanges` is reset with each new `TurnState` on HINT_PHASE; old exchange_ids are invalid |
| Forcing spy result via repeated calls | Elevation of Privilege | `spy_attempts` set blocks second attempt per turn; probability resolved server-side only |
| Submitting exchange hint before acceptance | Tampering | `record.status != "accepted"` guard in `submit_exchange_hint()` |

---

## Sources

### Primary (HIGH confidence)

- `server/turn_state.py` — TurnState dataclass pattern, `dataclasses.field(default_factory=...)` [VERIFIED: codebase]
- `server/turn_machine.py` — `_compute_next()` structure, lock-then-broadcast-outside pattern, PHASE_SEQUENCE [VERIFIED: codebase]
- `server/game_server.py` — `submit_hint()`, `submit_guess()`, `_accumulate_scores()` RPC method patterns; `broadcaster.send_to_player()` [VERIFIED: codebase]
- `server/event_broadcaster.py` — `send_to_player()` signature, `broadcast()` fan-out with exclude [VERIFIED: codebase]
- `bridge/bridge.py` — `on_object_assigned()` SID lookup pattern, `@Pyro5.api.oneway @Pyro5.api.callback` decorator stack, per-thread proxy [VERIFIED: codebase]
- `config.py` — `PHASE_DURATIONS["EXCHANGE_PHASE"]=45`, `PHASE_DURATIONS["SPY_PHASE"]=30` [VERIFIED: codebase]
- `.planning/phases/05-exchange-spy-mechanics/05-CONTEXT.md` — all locked decisions D-01 through D-07 [VERIFIED: planning artifact]
- `tests/test_turn_state.py` — `FakeBroadcaster`, `_server_with_turn_state()` helper pattern [VERIFIED: codebase]

### Secondary (MEDIUM confidence)

- CLAUDE.md §Key Pyro5 Patterns — patterns 1–4 confirm per-thread proxy, @oneway, broadcast pattern [CITED: CLAUDE.md]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing project dependencies; verified by codebase inspection
- Architecture patterns: HIGH — all patterns extracted directly from working Phases 1–4 codebase
- Pitfalls: HIGH — derived from existing pitfall documentation in CLAUDE.md + direct code reading of lock/broadcast ordering in all existing methods

**Research date:** 2026-05-14
**Valid until:** 2026-06-14 (30 days — stable stack, no upstream library changes anticipated)
