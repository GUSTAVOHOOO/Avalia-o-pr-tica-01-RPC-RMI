---
phase: "05-exchange-spy-mechanics"
plan: "03"
subsystem: "server"
tags: ["rpc", "game-mechanics", "exchange", "spy", "pyro5", "tdd"]
dependency_graph:
  requires: ["05-02"]
  provides: ["request_exchange-rpc", "respond_exchange-rpc", "submit_exchange_hint-rpc", "attempt_spy-rpc"]
  affects: ["05-04"]
tech_stack:
  added: []
  patterns: ["lock-then-broadcast-outside", "snapshot-inside-lock", "set-membership-guard"]
key_files:
  created: []
  modified:
    - "server/game_server.py"
    - "tests/test_exchange.py"
decisions:
  - "ExchangeRecord imported from server.turn_state (already added in plan 02)"
  - "Both exchange slots reserved at request_exchange() time, not at accept time (Pitfall 2 / CONTEXT.md D-03)"
  - "Spy probability resolved server-side with random.random() < 0.3 — client cannot influence outcome"
  - "Score penalty for spy discovery applied inside the RLock before broadcast exits lock"
  - "EXCHANGE_COMPLETED broadcast contains no hint content (T-05-06 / EXCHANGE-04)"
  - "Private hints delivered via send_to_player after lock exit (Pitfall 1)"
metrics:
  duration: "~20 min"
  completed_date: "2026-05-14"
  tasks_completed: 2
  files_modified: 2
requirements:
  - EXCHANGE-01
  - EXCHANGE-02
  - EXCHANGE-03
  - EXCHANGE-04
  - EXCHANGE-05
  - EXCHANGE-06
  - SPY-01
  - SPY-02
  - SPY-03
  - SPY-04
  - SPY-05
---

# Phase 5 Plan 03: Exchange + Spy RPC Methods Summary

**One-liner:** Four Pyro5 RPC methods implementing exchange lifecycle (request → respond → submit hint → completed) and spy resolution (30% probability, score penalty, private/public broadcast) with lock-then-broadcast-outside pattern throughout.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | request_exchange() + respond_exchange() + 5 tests | ff7f40f | server/game_server.py, tests/test_exchange.py |
| 2 | submit_exchange_hint() + attempt_spy() + 8 tests | 5e284ca | server/game_server.py, tests/test_exchange.py |

## What Was Built

### Task 1: request_exchange() and respond_exchange()

Added `ExchangeRecord` import from `server.turn_state` to `server/game_server.py` (plan 02 had already defined the dataclass).

**request_exchange(player_id, target_player_id) → dict**
- Phase guard: EXCHANGE_PHASE only
- Self-exchange guard: cannot_exchange_with_self
- Slot reservation: both requester and target added to `exchange_participants` immediately (Pitfall 2 — prevents in-flight double-requests)
- Target validation against `session.players` set
- Creates `ExchangeRecord(status="pending")` in `turn_state.exchanges`
- Sends private `exchange_requested` event to target via `send_to_player` outside the lock
- Returns `{ok: True, exchange_id: <8-char UUID>}`

**respond_exchange(player_id, exchange_id, accept) → dict**
- Phase guard: EXCHANGE_PHASE only
- Target-only guard: only record.target_id may respond
- Status guard: only pending exchanges can be responded to (Pitfall 6)
- Sets status to "accepted" or "rejected"
- No broadcast (target already notified via exchange_requested)

### Task 2: submit_exchange_hint() and attempt_spy()

**submit_exchange_hint(player_id, exchange_id, hint_word) → dict**
- Phase guard: EXCHANGE_PHASE only
- Accepted-status guard: exchange must be accepted before hints are submitted
- Participant-role check: requester or target only
- Duplicate-submission guard per role (already_submitted)
- Completion detection inside lock: when both hints present → status="completed", append to `completed_exchanges`, snapshot broadcast and private delivery data (Pitfall 5 — no race condition)
- After lock: broadcasts `exchange_completed` (no hint content — EXCHANGE-04/T-05-06); sends `exchange_hints` private event to each participant (EXCHANGE-05)

**attempt_spy(player_id, exchange_id) → dict**
- Phase guard: SPY_PHASE only
- One-per-turn guard: `spy_attempts` set membership check (SPY-05)
- Target validation: `exchange_id in turn_state.completed_exchanges` — NOT `turn_state.exchanges` dict (D-02, Pitfall 4)
- Self-spy guard: player cannot spy on own exchange (SPY-04)
- Probability: `random.random() < 0.3` resolved server-side under the lock
- Discovery (30%): deducts 10pts from `accumulated_scores` under lock, broadcasts `spy_discovered` with spy_name and penalty after lock
- Success (70%): sends `spy_success` private event to spy with both hints, no public broadcast (SPY-03)

## Test Results

```
tests/test_exchange.py: 15 passed, 0 failed, 0 skipped
tests/ (full suite): 53 passed, 0 failed
```

All 11 exchange/spy requirement tests pass (EXCHANGE-01 through SPY-05).
2 D-06 tests (already passing from plan 02) continue to pass.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all 4 RPC methods are fully implemented. No placeholder return values or TODO markers.

## Threat Flags

No new security surface introduced beyond what the plan's threat model covers. All mitigations from STRIDE register applied:
- T-05-02: target_player_id validated against session.players inside lock
- T-05-04: record.status != "accepted" guard in submit_exchange_hint()
- T-05-05: spy_attempts set blocks second attempt; probability resolved server-side
- T-05-06: broadcast_data for exchange_completed contains no hint words
- T-05-07: player_id in (requester_id, target_id) guard
- T-05-08: completed_exchanges membership check (not exchanges dict)

## Self-Check: PASSED

- server/game_server.py: FOUND (modified)
- tests/test_exchange.py: FOUND (modified)
- commit ff7f40f: FOUND (git log confirmed)
- commit 5e284ca: FOUND (git log confirmed)
- 53 tests passing: CONFIRMED
