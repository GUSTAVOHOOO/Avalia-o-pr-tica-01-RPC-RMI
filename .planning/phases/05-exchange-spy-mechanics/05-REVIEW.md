---
phase: 05
status: findings
critical: 2
warning: 3
info: 1
---

## Summary

Reviewed 7 files added or changed in Phase 5 (exchange + spy mechanics): `server/turn_state.py`, `server/turn_machine.py`, `server/game_server.py`, `bridge/bridge.py`, `tests/test_exchange.py`, `tests/test_turn_machine.py`, `tests/test_turn_state.py`.

The core architecture decisions are sound: player identity is resolved from the SID map in all new bridge handlers, spy probability is computed server-side inside the lock, and private hints are never included in public broadcasts. The RLock broadcast-outside-lock discipline is followed in all four new RPC methods.

Two critical bugs were found: a player identity spoofing vulnerability in the bridge's `join_room` reconnect handler, and a slot-leak in `respond_exchange` that permanently locks two players out of exchanges when a request is rejected. Three warnings cover a `_compute_next` crash path, a data race in scoring, and a session-invalidating secret key pattern.

---

## Findings

| # | Severity | File | Line | Finding | Recommendation |
|---|----------|------|------|---------|----------------|
| F-01 | **CRITICAL** | `bridge/bridge.py` | 541–552 | `handle_join_room` accepts `player_id` directly from the client payload and writes it into `_sid_to_player` / `_player_to_sid` without server-side verification. Any connected client can claim any `player_id` by sending `{room_code: "X", player_id: "victim-uuid"}`, then all subsequent game actions (hint submission, spy attempts) will execute as that player. | Resolve `player_id` from `_sid_to_player[request.sid]` (same as every other handler). Only call `get_player_view` if a SID mapping already exists. Remove the branch that writes client-supplied `player_id` into the map. |
| F-02 | **CRITICAL** | `server/game_server.py` | 647–683 | `respond_exchange` with `accept=False` sets the record status to `"rejected"` but never removes `player_id` (requester) or `target_player_id` from `turn_state.exchange_participants`. Both slots were reserved at request time (line 633–634). After a rejection, neither player can initiate or receive any further exchange this turn — the per-turn exchange slot is permanently consumed even though no exchange occurred. | On rejection, remove both `record.requester_id` and `record.target_id` from `turn_state.exchange_participants` before returning. |
| F-03 | **WARNING** | `server/turn_machine.py` | 250–251 | `_compute_next` falls through to `PHASE_SEQUENCE.index(current_phase)` for any phase not explicitly handled. If `advance_phase_manual()` is called while `current_phase` is `"WAITING"` (before `start()`) or `"GAME_ENDED"` (after the game ends), `list.index()` raises `ValueError`. If the phase is `"TURN_END"` and it somehow reaches the fallthrough (currently it does not, but the ordering makes it fragile), `PHASE_SEQUENCE[idx + 1]` raises `IndexError` since TURN_END is the last element. | Add an explicit guard: `if current_phase not in PHASE_SEQUENCE: return current_phase` (or raise a logged error and return a safe default). The existing test suite does not exercise `advance_phase_manual()` in `WAITING` state, so this is reachable in practice. |
| F-04 | **WARNING** | `server/game_server.py` | 391–393 | `_accumulate_scores` mutates `turn_state.guesses_made` (adding `None` entries for non-guessing players) outside `self.lock`. `turn_state` is shared mutable state. Although `_accumulate_scores` is called from `_on_scoring_phase` which fires after the lock is released in `TurnMachine._advance_to`, other concurrent RPC calls (`submit_guess`, `skip_guess`) also read/write `turn_state.guesses_made` under `self.lock`. The mutation on lines 391–393 is unsynchronized. | Move the `guesses_made` backfill loop inside the `with self.lock:` block that follows on line 396, or acquire `GameServer.lock` around lines 391–393 explicitly. |
| F-05 | **WARNING** | `bridge/bridge.py` | 32 | `app.config["SECRET_KEY"]` falls back to `os.urandom(24).hex()` when `FLASK_SECRET_KEY` is not set. This generates a new random key on every bridge process restart, which invalidates all existing Flask-SocketIO sessions. Players in the middle of a game will be silently disconnected and unable to reconnect after any bridge restart. For a demo/academic setting this is low-risk, but it is a correctness issue for any multi-restart scenario. | Document that `FLASK_SECRET_KEY` must be set in the environment, or derive a stable key from a config file / fixed seed specific to the deployment. |
| F-06 | **INFO** | `tests/test_exchange.py` | 300–308 | `test_spy_one_per_turn` calls `attempt_spy` twice on the same `exchange_id`. After the first call (which may succeed or discover), the second call should always return `already_used_spy`. However, if the first call randomly results in `discovered=True`, the score penalty has already been applied. The test does not fix `random.random`, so on ~30% of runs the first call also applies a -10 score penalty as a side-effect — the test asserts only the second call's error string, which is correct. This is not a bug in production code, but the test fixture is imprecise and could mask a future regression if score state is also asserted. | Pin `random.random` to a fixed value (as done in `test_spy_success_private`) to make the test deterministic and independent of the discovery roll. |

---

## Verdict

Ship-blocking: **F-01** (player identity spoofing via `join_room`) and **F-02** (exchange slot never freed on rejection) must be fixed before this can be considered functional. F-01 is a security vulnerability — a client can impersonate any player. F-02 means any rejected exchange request permanently breaks the exchange mechanic for both players for the rest of the turn.

F-03 and F-04 are defects that will surface in edge-case operation. F-05 is a deployment correctness issue. F-06 is a test quality improvement.
