---
phase: 07-reconnection-end-of-game
plan: "02"
subsystem: server
tags: [wave-1, server, pyro5, rpc, reconnect, vote, chat, infra]
dependency_graph:
  requires:
    - "07-01"  # Wave 0 test stubs
  provides:
    - server/event_broadcaster.py (failure_counts, broadcast returns list[str])
    - server/game_server.py (VoteRecord, turn_score_history, reconnect_player, send_chat, _start_vote, submit_vote, _resolve_vote, _remove_failed_players)
  affects:
    - Wave 1 plans 07-03, 07-04 (bridge and frontend depend on these RPC methods existing)
tech_stack:
  added: []
  patterns:
    - broadcast-outside-lock (all new GameServer methods)
    - generation-counter stale-timer guard for VoteRecord (same as TurnMachine._generation)
    - consecutive-failure-count threshold (D-08: 3 transient failures → player removal)
    - unittest.mock.patch for EventBroadcaster tests without real Pyro5 daemons
    - in-process Pyro5 daemon pattern for reconnect tests (same as test_session.py)
key_files:
  created: []
  modified:
    - server/event_broadcaster.py
    - server/game_server.py
    - tests/test_event_broadcaster.py
    - tests/test_reconnect.py
    - tests/test_postgame.py
    - tests/test_chat.py
    - tests/test_session.py
decisions:
  - "VoteRecord generation starts at 1 (not 0) so the zero-value sentinel in the stale-timer guard is unambiguous — same convention as TurnMachine"
  - "broadcast() return type changed from None to list[str]; all 9 prior callers in game_server.py updated atomically in the same commit to prevent partial-update state"
  - "on_game_ended in start_game() wired to _start_vote() instead of _set_session_ended() — post-game vote is the sole path out of the last turn; _resolve_vote() sets session.status=ENDED directly"
  - "test_vote_majority_yes_restarts seeds VoteRecord directly rather than calling _start_vote() to avoid 30s timer dependency in tests"
  - "send_chat uses inline import time as _time per project pattern for optional imports"
metrics:
  duration: "~45 minutes"
  completed: "2026-05-16"
  tasks_completed: 3
  files_created: 0
  files_modified: 7
---

# Phase 7 Plan 02: Server-Side Vertical Slice Summary

**One-liner:** EventBroadcaster consecutive-failure counter + 6 new GameServer RPC methods (reconnect, chat, vote lifecycle) with all 17 Wave 0 test stubs green.

## What Was Built

Server-side vertical slice for Phase 7. All bridge and frontend plans in Wave 1 depend on these RPC methods existing and being tested.

### Task 1: EventBroadcaster — failure_counts + broadcast returns list

Extended `server/event_broadcaster.py`:
- Added `self.failure_counts: dict` tracking consecutive transient failures per player_id
- Transient `Exception` branch increments the counter; resets to 0 on successful delivery
- After 3 consecutive transient failures, player_id is appended to the `failed` list (D-08 threshold)
- `broadcast()` now returns `list[str]` of failed player_ids (previously returned `None` implicitly)
- All 9 callers in `game_server.py` updated to capture return value and call `_remove_failed_players()`

### Task 2a: Data Model + Failure Removal + Reconnect + Chat

Extended `server/game_server.py`:
- Added `VoteRecord` dataclass (votes dict, generation int, timer field)
- Extended `GameSession` with `turn_score_history: list` and `vote_record: object`
- Added `_remove_failed_players()`: per-player under lock; broadcasts `player_left` after lock exits
- Added `reconnect_player()`: validates `_player_to_room[player_id] == room_code`, re-registers callback, returns `get_player_view()`
- Added `send_chat()`: truncates to 200 chars (T-07-02-03), broadcasts 5-key `chat_message` payload
- Updated `_accumulate_scores()` to append `{"turn": int, "scores": dict}` to `turn_score_history`
- Wired `on_game_ended` in `start_game()` to `_start_vote()` instead of `_set_session_ended()`

### Task 2b: Vote Lifecycle

Added to `server/game_server.py`:
- `_start_vote()`: creates `VoteRecord(generation=1)`, schedules 30s daemon `threading.Timer`, broadcasts `vote_started`
- `submit_vote()`: validates player, deduplicates (returns `{"ok": True, "duplicate": True}`), early-resolves when all players voted
- `_resolve_vote()`: stale-timer guard via generation counter; majority yes → `game_restarting` + TurnMachine rebuild; no majority → `game_ended` with `final_scores` and `turn_score_history`

## Test Results

| Test File | Tests | Result |
|-----------|-------|--------|
| tests/test_event_broadcaster.py | 3 | 3 PASSED |
| tests/test_reconnect.py | 3 | 3 PASSED |
| tests/test_chat.py | 4 | 4 PASSED |
| tests/test_session.py::test_host_transfer_on_leave | 1 | 1 PASSED |
| tests/test_postgame.py | 6 | 6 PASSED |
| **Phase 7 plan 02 total** | **17** | **17 PASSED** |
| Full suite | 78 | 78 PASSED, 0 SKIPPED |

## Verification Checks

```
# All 17 Phase 7 stubs green
python -m pytest tests/test_session.py::test_host_transfer_on_leave tests/test_event_broadcaster.py tests/test_reconnect.py tests/test_postgame.py tests/test_chat.py -v
→ 17 passed

# No regressions
python -m pytest tests/ -x -q
→ 78 passed in 7.64s

# No bare broadcast() calls with discarded return values
grep -n "broadcaster\.broadcast" server/game_server.py | grep -v "_remove_failed_players"
→ All 16 lines show "failed = self.broadcaster.broadcast(...)"

# All expected identifiers present
grep "def reconnect_player\|def send_chat\|def submit_vote\|def _start_vote\|def _resolve_vote\|def _remove_failed_players\|failure_counts\|turn_score_history\|VoteRecord" server/game_server.py server/event_broadcaster.py
→ All found
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all 17 Phase 7 test stubs are now replaced with real assertions.

## Threat Surface Scan

All mitigations from the plan's `<threat_model>` are implemented:

| Threat ID | Mitigation | Location |
|-----------|-----------|---------|
| T-07-02-01 | `reconnect_player()` validates `_player_to_room.get(player_id) == room_code` | game_server.py:1039 |
| T-07-02-02 | `submit_vote()` checks `player_id in vote.votes` before counting | game_server.py:1175 |
| T-07-02-03 | `send_chat()` truncates message to 200 chars via `str(message)[:200]` | game_server.py:1101 |
| T-07-02-04 | All broadcaster.broadcast() calls after `self.lock` exits | all new methods |
| T-07-02-05 | Timers are daemon threads; accepted disposition | N/A |

## Self-Check: PASSED

- server/event_broadcaster.py: EXISTS, has `failure_counts` and `return failed`
- server/game_server.py: EXISTS, has VoteRecord, turn_score_history, all 6 new methods
- tests/test_event_broadcaster.py: EXISTS, 3 PASSED
- tests/test_reconnect.py: EXISTS, 3 PASSED
- tests/test_postgame.py: EXISTS, 6 PASSED
- tests/test_chat.py: EXISTS, 4 PASSED
- tests/test_session.py::test_host_transfer_on_leave: PASSED
- Commit 8f75a0c: feat(07-02): extend EventBroadcaster — FOUND
- Commit 7648f25: feat(07-02): add VoteRecord, GameSession fields — FOUND
- Commit 3744c8a: feat(07-02): implement vote lifecycle — FOUND
