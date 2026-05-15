---
phase: 06-synonym-arbitration
plan: "01"
subsystem: arbitration-infrastructure
tags: [manifest, nltk, config, test-stubs, wave-0]
dependency_graph:
  requires: []
  provides:
    - WU_PALMER_THRESHOLD constant in config.py
    - Portuguese object names in manifest.json
    - nltk==3.9.4 pinned in requirements.txt
    - pytest stub harness for GUESS-03 (tests/test_arbitration.py)
  affects:
    - server/arbitration.py (plan 06-02 will implement)
    - server/game_server.py (reads manifest at startup)
tech_stack:
  added:
    - nltk==3.9.4
  patterns:
    - try/except ImportError + pytest.skip(allow_module_level=True) for not-yet-implemented modules
key_files:
  modified:
    - server/images/manifest.json
    - config.py
    - requirements.txt
  created:
    - tests/test_arbitration.py
decisions:
  - "D-02 (Option A): manifest.json values translated to Portuguese — arbitration operates on Portuguese words end-to-end"
  - "WU_PALMER_THRESHOLD = 0.7 placed in config.py per D-01 — never hardcoded in arbitration.py"
  - "Module-level ImportError skip used so test file is green (1 skipped) even before server/arbitration.py exists"
metrics:
  duration: "~10 min"
  completed_date: "2026-05-15"
  tasks_completed: 2
  files_changed: 4
---

# Phase 06 Plan 01: Infrastructure Wave 0 Summary

**One-liner:** Portuguese manifest + WU_PALMER_THRESHOLD config + nltk pin + GUESS-03 pytest stubs — baseline for TDD arbitration implementation.

## What Was Built

### Task 1: Manifest, Config, Requirements

- **server/images/manifest.json**: All 12 object values translated from English to Portuguese. Keys (image filenames) unchanged. Values: maçã, bicicleta, cadeira, relógio, violão, chapéu, laptop, guarda-chuva, livro, xícara, sapato, árvore.
- **config.py**: Added `WU_PALMER_THRESHOLD = 0.7` after the `PHASE_DURATIONS` block, with two-line comment explaining the threshold semantics and where to tune it.
- **requirements.txt**: Added `nltk==3.9.4` between `simple-websocket==1.1.0` and `pytest`, maintaining the runtime-before-test-only ordering convention.

### Task 2: Test Stubs

- **tests/test_arbitration.py**: 8 pytest stub functions covering GUESS-03a (exact match, case-insensitive), GUESS-03b (synonym via omw-1.4, wrong guess, threshold boundary), GUESS-03c (fallback for unknown words), D-05 (matched_word is canonical target), D-06 (match_type on incorrect guess).
- Module-level `try/except ImportError` guard: if `server.arbitration` does not exist, the entire file skips at collection time (`allow_module_level=True`). This keeps the suite green until Plan 06-02 creates the implementation.

## Commit

- `ce867c7` — feat(06-01): infrastructure — Portuguese manifest, NLTK dep, WuPalmer config, test stubs

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| WU_PALMER_THRESHOLD | `grep -c "WU_PALMER_THRESHOLD" config.py` | 1 |
| nltk pinned | `grep "nltk==3.9.4" requirements.txt` | nltk==3.9.4 |
| Portuguese manifest | `grep "maçã" server/images/manifest.json` | found |
| config import | `python -c "import config; assert config.WU_PALMER_THRESHOLD == 0.7"` | exits 0 |
| manifest JSON | `python -c "import json; m = json.load(open(...)); assert 'maçã' in m.values()"` | exits 0 |
| pytest stubs | `venv/bin/python -m pytest tests/test_arbitration.py -v` | 1 skipped (module-level), 0 errors |
| full suite | `venv/bin/python -m pytest tests/ -q` | 1 failed (pre-existing), 52 passed, 1 skipped — no new failures |

## Deviations from Plan

None — plan executed exactly as written.

The plan specified "8 items skipped" in the verify step, but the actual behavior is "1 skipped" at the module level (the entire file skips when `server.arbitration` is absent). This is the correct behavior given the `allow_module_level=True` pattern specified in the task's action block — the module skip is equivalent to 8 individual skips at collection time. No fix needed; the suite is green.

## Known Stubs

| File | Stub | Reason |
|------|------|--------|
| tests/test_arbitration.py | All 8 test functions call `pytest.skip("not implemented")` | Intentional: RED phase for TDD. Plan 06-02 implements `server/arbitration.py` and fills these in. |

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. manifest.json is a local file read at startup with UTF-8 encoding already enforced in game_server.py.

## Self-Check

- [x] `server/images/manifest.json` exists and contains Portuguese values
- [x] `config.py` contains `WU_PALMER_THRESHOLD = 0.7`
- [x] `requirements.txt` contains `nltk==3.9.4`
- [x] `tests/test_arbitration.py` exists (44 lines)
- [x] Commit `ce867c7` exists in git log
- [x] Full test suite: no new failures

## Self-Check: PASSED
