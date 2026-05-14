---
phase: 05-exchange-spy-mechanics
plan: "04"
subsystem: bridge
tags: [bridge, socketio, pyro5, exchange, spy, push-events, routing]
dependency_graph:
  requires: [05-03]
  provides: [exchange-bridge-handlers, spy-bridge-handlers]
  affects: [bridge/bridge.py]
tech_stack:
  added: []
  patterns:
    - Private SID delivery via _player_to_sid lookup (on_exchange_requested, on_exchange_hints, on_spy_success)
    - Room broadcast via data["room_code"] (on_exchange_completed, on_spy_discovered)
    - Socket.IO handler SID-to-player resolution (handle_request_exchange, handle_respond_exchange, handle_submit_exchange_hint, handle_attempt_spy)
key_files:
  created: []
  modified:
    - bridge/bridge.py
decisions:
  - "SID lookup uses _player_to_sid.get(target_player_id) inside _sid_lock for all private deliveries"
  - "player_id always resolved from _sid_to_player[request.sid] in handlers, never from client payload (T-05-09)"
  - "on_exchange_hints follows private delivery pattern — called twice by EventBroadcaster, once per participant"
  - "on_exchange_completed and on_spy_discovered use room broadcast pattern (data['room_code'])"
  - "respond_exchange handler casts accept payload to bool() to prevent truthy-string exploit"
metrics:
  duration_minutes: 15
  completed_date: "2026-05-14T22:59:26Z"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 1
---

# Phase 5 Plan 04: Bridge Exchange+Spy Handlers Summary

Wave 3 bridge layer wired: 5 `BridgeCallbackReceiver.on_*` push methods + 4 `@socketio.on()` action handlers enabling full exchange and spy flows between browsers and the Pyro5 GameServer.

## What Was Built

**5 BridgeCallbackReceiver push methods** (commit `695e073`):

| Method | Pattern | Routing |
|--------|---------|---------|
| `on_exchange_requested` | Private SID | target player only |
| `on_exchange_completed` | Room broadcast | all players in room |
| `on_exchange_hints` | Private SID | one participant (called twice) |
| `on_spy_discovered` | Room broadcast | all players in room |
| `on_spy_success` | Private SID | spy only |

**4 Socket.IO action handlers** (commit `59a562b`):

| Handler | Event | RPC Call |
|---------|-------|----------|
| `handle_request_exchange` | `request_exchange` | `proxy.request_exchange(player_id, target_player_id)` |
| `handle_respond_exchange` | `respond_exchange` | `proxy.respond_exchange(player_id, exchange_id, bool(accept))` |
| `handle_submit_exchange_hint` | `submit_exchange_hint` | `proxy.submit_exchange_hint(player_id, exchange_id, hint_word)` |
| `handle_attempt_spy` | `attempt_spy` | `proxy.attempt_spy(player_id, exchange_id)` |

## Verification Results

- `python -c "import bridge.bridge"` — exits 0, no import errors
- `python -m pytest tests/ -q` — 53 passed, 0 failures (all prior tests green)
- All 5 `on_*` methods confirmed with correct decorator stacks (`@Pyro5.api.oneway`, `@Pyro5.api.callback`)
- All 4 handlers confirmed with `_sid_to_player.get(request.sid)` inside `with _sid_lock:`

## Checkpoint Status

Task 3 is a `checkpoint:human-verify` gate — requires 4-terminal smoke test (NS + GameServer + Bridge + browser) to confirm end-to-end exchange and spy flows. This checkpoint is blocking and awaits human approval.

## Deviations from Plan

None — plan executed exactly as written. All patterns followed the established `on_object_assigned` (private SID) and `on_hint_received` (room broadcast) references.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced beyond what is documented in the plan's `<threat_model>`. Mitigations applied:

- T-05-09: `handle_request_exchange` resolves caller from `_sid_to_player[SID]`, never from payload
- T-05-10: `on_exchange_hints` emits `to=sid` (individual SID), never to room
- T-05-11: `on_spy_success` emits `to=sid` (spy's SID only), no room broadcast
- T-05-12: `handle_attempt_spy` passes `exchange_id` through; server validates against `completed_exchanges`

## Self-Check: PASSED

- `bridge/bridge.py` exists and imports cleanly
- Commit `695e073` (Task 1) — verified in git log
- Commit `59a562b` (Task 2) — verified in git log
- 53 tests pass, 0 failures
