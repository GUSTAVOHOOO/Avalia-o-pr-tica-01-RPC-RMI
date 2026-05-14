# Phase 5: Exchange + Spy Mechanics - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Players can request and complete private 1-on-1 hint exchanges during EXCHANGE_PHASE, and attempt to spy on completed exchanges during the subsequent SPY_PHASE. A completed exchange means both players accepted and submitted their private hint word — only participants see the exchanged words. Spying has a 30% discovery probability: caught spies receive a public broadcast and lose 10 points; undetected spies silently receive both private words. If no exchanges completed during EXCHANGE_PHASE, SPY_PHASE is skipped automatically. Phase 5 delivers the server RPC layer and bridge handlers only — no new frontend action panels (those are Phase 8).

Requirements in scope: EXCHANGE-01, EXCHANGE-02, EXCHANGE-03, EXCHANGE-04, EXCHANGE-05, EXCHANGE-06, SPY-01, SPY-02, SPY-03, SPY-04, SPY-05

</domain>

<decisions>
## Implementation Decisions

### EXCHANGE/SPY Phase Sequencing
- **D-01:** Keep EXCHANGE_PHASE and SPY_PHASE as two separate sequential phases with independent timers. No change to `PHASE_SEQUENCE` in `turn_machine.py`. The "simultaneous" wording in SPY-01 in REQUIREMENTS.md is intentionally overridden by this decision — sequential is simpler and avoids coordinating spy attempts against in-progress exchanges.
- **D-02:** Spy targets are **completed exchanges only** — exchanges where both players accepted and both hint words were submitted before EXCHANGE_PHASE ended. Rejected, pending, or partially-complete exchanges never appear in the SPY_PHASE target list.

### Exchange State & Lifecycle
- **D-03:** Exchange state lives in **new fields on `TurnState`** in `server/turn_state.py`. Follow the same pattern as `hints_submitted` and `guesses_made` — pure Python data, no Pyro5 import, discarded at turn end. New fields:
  - `exchanges: dict[str, ExchangeRecord]` — maps `exchange_id` → `ExchangeRecord` dataclass (fields: `requester_id`, `target_id`, `status` in `{"pending","accepted","rejected","completed"}`, `requester_hint`, `target_hint`)
  - `completed_exchanges: list[str]` — ordered list of `exchange_id`s that reached `status="completed"` during EXCHANGE_PHASE; used as spy target list in SPY_PHASE
  - `exchange_participants: set[str]` — tracks which player_ids have used their one exchange slot (EXCHANGE-06)
  - `spy_attempts: set[str]` — tracks which player_ids have used their one spy slot (SPY-05)
- **D-04:** `exchange_id` is generated with `str(uuid.uuid4())[:8]` — short, unique within a turn, consistent with the room code generation pattern already in the codebase.
- **D-05:** When EXCHANGE_PHASE timer fires, **incomplete exchanges are dropped silently** — no cancellation broadcast. Partially-submitted or pending exchanges that did not reach `status="completed"` before the timer are simply ignored. Keeps the phase transition callback simple.

### SPY_PHASE Auto-Skip
- **D-06:** If `completed_exchanges` is empty when EXCHANGE_PHASE ends, TurnMachine jumps **directly to SCORING_PHASE**, skipping SPY_PHASE entirely. Add conditional logic to `_compute_next()`: when transitioning from `EXCHANGE_PHASE`, check `turn_machine.current_turn_state.completed_exchanges`; if empty, return `"SCORING_PHASE"` instead of `"SPY_PHASE"`.

### Frontend Scope
- **D-07:** Phase 5 is **backend + bridge only**. The existing GameScreen already shows phase name + countdown during EXCHANGE_PHASE and SPY_PHASE (from Phase 3 infrastructure). No new inline action panels are added in this phase. Exchange/spy UI panels are Phase 8 work (UI-06). Bridge handlers must emit all events so Phase 8 has a complete event surface to build on.

### Claude's Discretion
- ExchangeRecord implementation: a `@dataclasses.dataclass` in `turn_state.py` (co-located with TurnState) vs a separate `exchange_record.py` file — leave to planner.
- Whether `attempt_spy()` during SPY_PHASE uses Python's `random.random() < 0.3` or `random.choices()` for the 30% probability — implementation detail, leave to planner.
- PHASE_CHANGED broadcast payload for SPY_PHASE: whether to include `spy_targets: [list of exchange_ids]` or `spy_target_count: N` — leave to planner, but the list of IDs is more useful for future UI.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §EXCHANGE-01 through EXCHANGE-06 — Exchange request, response, hint submission, public broadcast, private delivery, one-exchange-per-turn rule
- `.planning/REQUIREMENTS.md` §SPY-01 through SPY-05 — Spy attempt, 30% discovery probability, -10pt penalty, silent success delivery, no self-spy, one-spy-per-turn rule
- `.planning/ROADMAP.md` §Phase 5 — 4 success criteria that must all be TRUE for phase completion

### Architecture
- `.planning/PROJECT.md` §Architecture Decision — Bridge WebSocket diagram; broadcast path GameServer → EventBroadcaster → BridgeCallbackReceiver → socketio.emit()
- `.planning/PROJECT.md` §Key Decisions — locked decisions (@oneway, RLock, per-thread proxies, targeted delivery pattern)

### Prior Phase Decisions
- `.planning/phases/04-core-turn-loop/04-CONTEXT.md` — D-01/D-03 (TurnState structure and fields), D-13 (targeted private delivery via `target_player_id` in payload), D-18 (no modal overlays until Phase 8), broadcast outside RLock pattern
- `.planning/phases/01-rpc-infrastructure-callback-pipeline/01-CONTEXT.md` — D-08 (@oneway), D-09 (broadcast @oneway), D-10 (per-thread proxy)
- `.planning/phases/02-player-session-lobby/02-CONTEXT.md` — D-12/D-13 (room-based Socket.IO routing), D-14 (BridgeCallbackReceiver extension pattern)

### Technology
- `CLAUDE.md` §Key Pyro5 Patterns — patterns 1–4

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/turn_state.py` — `TurnState` dataclass; Phase 5 adds `exchanges`, `completed_exchanges`, `exchange_participants`, `spy_attempts` fields following the same `dataclasses.field(default_factory=...)` pattern.
- `server/turn_machine.py` — `_compute_next()` needs a new branch: when `current_phase == "EXCHANGE_PHASE"`, check `self.current_turn_state.completed_exchanges` to decide between `"SPY_PHASE"` and `"SCORING_PHASE"`. `_advance_to()` needs no structural changes — spy/exchange logic lives in RPC methods on GameServer.
- `server/game_server.py` — Add 4 new `@Pyro5.api.expose` RPC methods: `request_exchange()`, `respond_exchange()`, `submit_exchange_hint()`, `attempt_spy()`. Follow the same lock-then-broadcast-outside pattern as `submit_hint()` and `submit_guess()`.
- `server/event_broadcaster.py` — `broadcast(event_type, data)` already supports targeted delivery via `target_player_id` key in payload. No changes needed.
- `bridge/bridge.py` — Add `on_exchange_requested`, `on_exchange_responded`, `on_exchange_completed`, `on_spy_discovered` to `BridgeCallbackReceiver` (all `@Pyro5.api.oneway @Pyro5.api.callback`). Add Socket.IO handlers for `request_exchange`, `respond_exchange`, `submit_exchange_hint`, `attempt_spy`.

### Established Patterns
- All broadcast-triggering methods on `GameServer` must be `@Pyro5.api.expose` (not `@oneway`) to return error dicts to the bridge caller.
- `BridgeCallbackReceiver` push methods use `@Pyro5.api.oneway @Pyro5.api.callback` — all new `on_*` push methods follow this pattern.
- Targeted (private) delivery: bridge checks for `target_player_id` in payload and uses `socketio.emit(event, data, to=sid)` instead of `to=room_code`. Phase 5 uses this for: exchange request notification (requester → target), private hint delivery to exchange participants, private spy success delivery.
- Broadcast OUTSIDE the lock — all `broadcaster.broadcast()` calls happen after `with self.lock:` block exits.
- Per-player-per-turn enforcement: check a `set` field on TurnState before allowing the action, return `{"error": "already_used"}` if the player's ID is already in the set.

### Integration Points
- `server/turn_state.py`: Add `ExchangeRecord` dataclass and new TurnState fields.
- `server/turn_machine.py`: Modify `_compute_next()` to skip SPY_PHASE when `completed_exchanges` is empty.
- `server/game_server.py`: Add `request_exchange()`, `respond_exchange()`, `submit_exchange_hint()`, `attempt_spy()` RPC methods.
- `bridge/bridge.py`: Add `BridgeCallbackReceiver` push methods + Socket.IO action handlers for all 4 new RPC methods.

</code_context>

<specifics>
## Specific Ideas

- `ExchangeRecord` fields: `requester_id: str`, `target_id: str`, `status: str` (one of `"pending"`, `"accepted"`, `"rejected"`, `"completed"`), `requester_hint: Optional[str]`, `target_hint: Optional[str]`.
- `request_exchange()` response: `{"ok": True, "exchange_id": "<8-char-uuid>"}` — bridge forwards this back to the requesting client.
- `EXCHANGE_REQUESTED` event payload (private to target): `{room_code, exchange_id, requester_id}`.
- `EXCHANGE_COMPLETED` broadcast payload (public, no hint content): `{room_code, exchange_id, requester_id, target_id}`.
- Private hint delivery event (to both participants): `{room_code, exchange_id, from_player_id, hint_word}` — sent twice, once for each participant's hint, targeted to each recipient.
- `SPY_DISCOVERED` broadcast payload: `{room_code, spy_id, spy_name, exchange_id, penalty: -10}`.
- Private spy success payload (to spy only): `{room_code, exchange_id, hints: [{from_player_id, hint_word}, {from_player_id, hint_word}]}`.
- `PHASE_CHANGED` to SPY_PHASE payload: extend existing structure with `spy_targets: [exchange_id, ...]` list.

</specifics>

<deferred>
## Deferred Ideas

- Spy success bonus (+5pts) — deferred to v2 per REQUIREMENTS.md v2 list.
- Exchange/spy inline action panels in GameScreen — deferred to Phase 8 (UI-06).
- Configurable spy probability by host — deferred to v2.

</deferred>

---

*Phase: 5-exchange-spy-mechanics*
*Context gathered: 2026-05-14*
