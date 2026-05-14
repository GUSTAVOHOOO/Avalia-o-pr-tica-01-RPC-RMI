---
phase: 05-exchange-spy-mechanics
plan: "02"
subsystem: server
tags:
  - turn-state
  - exchange-record
  - spy-phase
  - tdd
  - phase-5

dependency_graph:
  requires:
    - 05-01
  provides:
    - ExchangeRecord dataclass importable from server.turn_state
    - TurnState with 4 new Phase 5 fields (exchanges, completed_exchanges, exchange_participants, spy_attempts)
    - _compute_next() EXCHANGE_PHASE conditional branch (D-06)
    - SPY_PHASE PHASE_CHANGED payload with spy_targets list
  affects:
    - server/turn_state.py
    - server/turn_machine.py
    - tests/test_turn_state.py
    - tests/test_exchange.py
    - tests/test_turn_machine.py

tech_stack:
  added: []
  patterns:
    - TDD red-green cycle (test before implementation)
    - dataclasses.dataclass with Optional fields for ExchangeRecord
    - default_factory pattern for new TurnState set/list/dict fields
    - Conditional _compute_next() branch before PHASE_SEQUENCE index lookup
    - spy_targets injected into broadcast_data inside lock (analogous to hints in GUESS_PHASE)

key_files:
  created: []
  modified:
    - server/turn_state.py
    - server/turn_machine.py
    - tests/test_turn_state.py
    - tests/test_exchange.py
    - tests/test_turn_machine.py

decisions:
  - ExchangeRecord co-located in turn_state.py (not separate file) per Claude Discretion
  - spy_targets list (not count) in SPY_PHASE PHASE_CHANGED payload per Claude Discretion
  - test_turn_machine.py tests updated to inject fake completed_exchanges before EXCHANGE_PHASE advance so full PHASE_SEQUENCE (including SPY_PHASE) can be exercised in existing cycle tests

metrics:
  duration: "25 min"
  completed_date: "2026-05-14"
  tasks_completed: 2
  files_modified: 5
---

# Phase 5 Plan 02: Data Layer Extension — ExchangeRecord + SPY_PHASE Skip Summary

**One-liner:** ExchangeRecord dataclass with 5 fields added to turn_state.py; 4 new TurnState fields for Phase 5 exchange/spy state; _compute_next() conditionally skips SPY_PHASE when no exchanges completed (D-06); spy_targets injected into PHASE_CHANGED broadcast for SPY_PHASE.

## What Was Built

### Task 1: ExchangeRecord dataclass and TurnState fields (server/turn_state.py)

Added `from typing import Optional` import and the `ExchangeRecord` dataclass before `TurnState`:

```python
@dataclasses.dataclass
class ExchangeRecord:
    """Tracks one 1-on-1 private hint exchange within a turn."""
    requester_id: str
    target_id: str
    status: str = "pending"
    requester_hint: Optional[str] = None
    target_hint: Optional[str] = None
```

Added 4 new fields to `TurnState` after `image_assignments`:
- `exchanges: dict` — exchange_id → ExchangeRecord (D-03)
- `completed_exchanges: list` — ordered list of completed exchange_ids, spy target list (D-03)
- `exchange_participants: set` — player_ids that used their exchange slot (EXCHANGE-06)
- `spy_attempts: set` — player_ids that used their spy slot (SPY-05)

### Task 2: SPY_PHASE skip logic and spy_targets broadcast (server/turn_machine.py)

Added conditional branch to `_compute_next()` before PHASE_SEQUENCE index lookup:

```python
if current_phase == "EXCHANGE_PHASE":
    ts = self.current_turn_state
    if ts is None or not ts.completed_exchanges:
        return "SCORING_PHASE"
    return "SPY_PHASE"
```

Added spy_targets injection in `_advance_to()`:

```python
if phase == "SPY_PHASE" and self.current_turn_state is not None:
    broadcast_data["spy_targets"] = list(self.current_turn_state.completed_exchanges)
```

## Test Results

- `python -m pytest tests/test_exchange.py -x -q` → 2 passed, 13 skipped, 0 failed
- `python -m pytest tests/test_turn_state.py -q` → 19 passed, 0 failed
- `python -m pytest tests/ -q` → 40 passed, 13 skipped, 0 failed

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 7258ede | test | RED — import ExchangeRecord + 4 test functions for new fields |
| 1e1bce1 | feat | GREEN — ExchangeRecord dataclass + 4 new TurnState fields |
| d18f6a5 | test | RED — D-06 stub tests converted to failing assertions |
| a0aecbe | feat | GREEN — _compute_next EXCHANGE_PHASE branch + spy_targets broadcast |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_turn_machine.py Phase 4 tests broken by Phase 5 SPY_PHASE skip logic**
- **Found during:** Task 2 GREEN phase — running full test suite
- **Issue:** `test_phase_cycle` and `test_game_ended_after_last_turn` assumed EXCHANGE_PHASE always advances to SPY_PHASE. With D-06 logic, EXCHANGE_PHASE skips SPY_PHASE when `current_turn_state` is None or `completed_exchanges` is empty. Both tests used a TurnMachine without a TurnState, so `ts is None` triggered the skip.
- **Fix:** Updated both tests to advance to EXCHANGE_PHASE first, then inject `current_turn_state.completed_exchanges.append("fake-exid")` so the subsequent advance goes to SPY_PHASE as expected. Also corrected off-by-one error in advance call count (`test_game_ended_after_last_turn` was missing the TURN_END → GAME_ENDED advance).
- **Files modified:** tests/test_turn_machine.py
- **Commit:** a0aecbe (included in the same feat commit)

## Known Stubs

None — all new fields and methods are fully implemented. The 13 skipped tests in test_exchange.py are intentional stubs for Plans 03 and 04.

## Threat Surface Scan

No new network endpoints or auth paths introduced. Changes are pure in-process Python data layer additions. T-05-01 (exchange_participants set mutation under lock) and T-05-02 (None guard in _compute_next) are both mitigated by this plan as designed.

## Self-Check: PASSED

- server/turn_state.py contains ExchangeRecord class: FOUND
- server/turn_machine.py contains `completed_exchanges` branch: FOUND
- server/turn_machine.py contains `spy_targets` injection: FOUND
- Commits 7258ede, 1e1bce1, d18f6a5, a0aecbe: FOUND in git log
