---
phase: 07-reconnection-end-of-game
plan: "01"
subsystem: test-scaffold
tags: [wave-0, tdd, stubs, pytest]
dependency_graph:
  requires: []
  provides:
    - tests/test_event_broadcaster.py
    - tests/test_reconnect.py
    - tests/test_postgame.py
    - tests/test_chat.py
    - tests/test_session.py::test_host_transfer_on_leave
  affects:
    - Wave 1 plans (07-02, 07-03) inherit these stubs and replace pytest.skip with real assertions
tech_stack:
  added: []
  patterns:
    - pytest.skip stubs with rationale strings (Wave 0 Nyquist compliance pattern)
    - _start_daemon helper from test_session.py imported into test_reconnect.py
key_files:
  created:
    - tests/test_event_broadcaster.py
    - tests/test_reconnect.py
    - tests/test_postgame.py
    - tests/test_chat.py
  modified:
    - tests/test_session.py
decisions:
  - "pytest.skip used over NotImplementedError for Wave 0 stubs — produces cleaner SKIPPED status in CI (established in Phase 2)"
  - "test_reconnect.py includes _start_daemon helper for consistency with test_session.py pattern even though stubs do not yet use it"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-16"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
---

# Phase 7 Plan 01: Test Scaffold (Wave 0) Summary

**One-liner:** 17 pytest.skip stubs across 5 test files providing named targets for all Phase 7 server-side behaviors before implementation begins.

## What Was Built

Wave 0 test scaffold for Phase 7 (Reconnection + End-of-Game). All 17 stubs skip cleanly — the full test suite runs 61 passed, 17 skipped, zero failures.

### Files Created

| File | Stubs | Requirements |
|------|-------|-------------|
| `tests/test_event_broadcaster.py` | 3 | INFRA-07 (D-08 failure counter, reset on success, PLAYER_LEFT broadcast) |
| `tests/test_reconnect.py` | 3 | INFRA-08 (get_player_view shape, unknown UUID, callback URI update) |
| `tests/test_postgame.py` | 6 | POSTGAME-01 to 04 (turn history, vote started, majority restart, no-majority end, timer expiry, duplicate vote guard) |
| `tests/test_chat.py` | 4 | CHAT-01/02 (send_chat ok, broadcast payload, length cap, unknown player) |

### Files Modified

| File | Change |
|------|--------|
| `tests/test_session.py` | Appended `test_host_transfer_on_leave` stub (SESSION-07); added `pytest` import; updated module docstring coverage list |

## Stub Coverage by Requirement

| Requirement | Test Stub | File |
|-------------|-----------|------|
| INFRA-07 | `test_consecutive_failure_counter` | test_event_broadcaster.py |
| INFRA-07 | `test_failure_resets_on_success` | test_event_broadcaster.py |
| INFRA-07 | `test_player_left_broadcast_on_failure` | test_event_broadcaster.py |
| INFRA-08 | `test_reconnect_player_returns_player_view` | test_reconnect.py |
| INFRA-08 | `test_reconnect_player_unknown_uuid` | test_reconnect.py |
| INFRA-08 | `test_reconnect_player_updates_callback_uri` | test_reconnect.py |
| SESSION-07 | `test_host_transfer_on_leave` | test_session.py |
| POSTGAME-01 | `test_turn_score_history_appended` | test_postgame.py |
| POSTGAME-02 | `test_vote_started_broadcast` | test_postgame.py |
| POSTGAME-03 | `test_vote_majority_yes_restarts` | test_postgame.py |
| POSTGAME-04 | `test_vote_no_majority_ends_game` | test_postgame.py |
| POSTGAME-04 | `test_vote_timer_expiry_ends_game` | test_postgame.py |
| POSTGAME-03/04 | `test_duplicate_vote_ignored` | test_postgame.py |
| CHAT-01 | `test_send_chat_returns_ok` | test_chat.py |
| CHAT-02 | `test_send_chat_broadcasts_payload` | test_chat.py |
| CHAT-01 | `test_send_chat_message_length_cap` | test_chat.py |
| CHAT-01 | `test_send_chat_unknown_player` | test_chat.py |

## Verification

```
python -m pytest tests/ -x -q
61 passed, 17 skipped in 6.42s
```

All new stubs appear as SKIPPED. All prior tests continue to pass. Zero FAILED or ERROR entries.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

All 17 test functions are intentional Wave 0 stubs. Each carries the rationale string `"stub — implemented by plan 07-02"`. They will be replaced with real assertions by plans 07-02 and 07-03 in Wave 1.

## Threat Flags

None — this plan creates test files only. No network endpoints, auth paths, file access patterns, or schema changes were introduced.

## Self-Check: PASSED

- tests/test_event_broadcaster.py: EXISTS (3 stubs, all SKIPPED)
- tests/test_reconnect.py: EXISTS (3 stubs, all SKIPPED)
- tests/test_postgame.py: EXISTS (6 stubs, all SKIPPED)
- tests/test_chat.py: EXISTS (4 stubs, all SKIPPED)
- tests/test_session.py::test_host_transfer_on_leave: EXISTS (1 stub, SKIPPED)
- Commit 6a7addd: test(07-01): add Wave 0 stubs for INFRA-07, INFRA-08, SESSION-07 — FOUND
- Commit bb653a5: test(07-01): add Wave 0 stubs for POSTGAME-01 to 04 and CHAT-01/02 — FOUND
