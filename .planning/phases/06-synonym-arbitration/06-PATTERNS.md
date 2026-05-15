# Phase 6: Synonym Arbitration - Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 6
**Analogs found:** 5 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `server/arbitration.py` | utility | transform | `server/turn_machine.py` (pure functions `_calculate_score_deltas`) | role-match |
| `server/game_server.py` | service | request-response | self (lines 537–572 `submit_guess()`) | exact — modify in place |
| `config.py` | config | — | self (lines 31–39, `PHASE_DURATIONS` block) | exact — add constant |
| `validate_manifest.py` | utility | file-I/O | `server/game_server.py` lines 92–94 (manifest load pattern) | partial-match |
| `requirements.txt` | config | — | self (lines 1–5) | exact — add line |
| `tests/test_arbitration.py` | test | transform | `tests/test_exchange.py` + `tests/test_scoring.py` | role-match |

---

## Pattern Assignments

### `server/arbitration.py` (utility, transform)

**Analog:** `server/turn_machine.py`

**Imports pattern** (`server/turn_machine.py` lines 1–20):
```python
"""TurnMachine — server-side finite state machine for game phase progression.
...
"""

import logging
import threading
import time
from typing import Optional

import config
from server.turn_state import TurnState

logger = logging.getLogger(__name__)
```

Copy the module-level docstring style (triple-quoted, one-line purpose then blank line then detail). Use `import logging` at module top. For `arbitration.py`, the logger line becomes:
```python
logger = logging.getLogger(__name__)
```

**Core pure-function pattern** (`server/turn_machine.py` lines 35–71):
```python
def _calculate_score_deltas(turn_state) -> dict:
    """Calculate per-player score deltas for the current turn."""
    deltas = {player_id: 0 for player_id in turn_state.player_ids}
    ...
    return deltas
```

The project convention for pure helper functions is: module-private prefix `_`, typed return, single docstring line. Copy this style for `_max_wup_similarity()`.

**Config reference pattern** (`server/turn_machine.py`):
```python
import config
# usage:
config.PHASE_DURATIONS[phase]
```

`arbitration.py` does NOT read config directly — it receives `threshold` as a parameter. But if needed, callers import `config` and pass `config.WU_PALMER_THRESHOLD` (see game_server.py pattern below).

---

### `server/game_server.py` (service, request-response) — modify `submit_guess()` and `__init__()`

**Analog:** self — lines 537–572 (`submit_guess()`) and lines 87–95 (`__init__()`)

**Imports pattern** (`server/game_server.py` lines 10–29):
```python
import dataclasses
import json
import os
import random
import string
import sys
import threading
import uuid
from typing import List, Optional

import Pyro5.api

import config
from server.event_broadcaster import EventBroadcaster
from server.turn_machine import TurnMachine, _calculate_score_deltas
from server.turn_state import ExchangeRecord
```

Add after the existing `from server.turn_state import ExchangeRecord` line:
```python
from server.arbitration import arbitrate, ensure_nltk_corpora
```

**`__init__()` startup pattern** (`server/game_server.py` lines 87–95):
```python
def __init__(self):
    self.lock = threading.RLock()
    self.broadcaster = EventBroadcaster()
    self.sessions: dict = {}
    self._player_to_room: dict = {}
    manifest_path = os.path.join(os.path.dirname(__file__), "images", "manifest.json")
    with open(manifest_path, encoding="utf-8") as manifest_file:
        self._image_manifest: dict = json.load(manifest_file)
    self._used_images_this_game: dict = {}
```

After `self._image_manifest` is assigned, add:
```python
    ensure_nltk_corpora()
    # Warm up corpus to avoid lazy-load I/O inside the lock on first guess
    from nltk.corpus import wordnet as wn
    wn.synsets('teste', lang='por')
    self._image_manifest = self._validate_manifest_words()
```

**Core `submit_guess()` replacement pattern** (`server/game_server.py` lines 537–572):
```python
def submit_guess(self, player_id: str, target_player_id: str, guess_word: str) -> dict:
    """Submit one guess for another player's object."""
    broadcast_data = None
    is_correct = False

    with self.lock:
        # ... guard checks (lines 542–558, unchanged) ...
        guess_clean = str(guess_word).strip()[:50]
        expected = str(turn_state.image_assignments.get(target_player_id, ""))
        # BEFORE (line 560): is_correct = guess_clean.lower() == expected.strip().lower()
        # AFTER:
        is_correct, matched_word, match_type = arbitrate(
            guess_clean, expected, config.WU_PALMER_THRESHOLD
        )
        turn_state.guesses_made[player_id] = target_player_id
        if is_correct:
            turn_state.correct_guesses.append(player_id)
        broadcast_data = {
            "room_code": room_code,
            "guesser_id": player_id,
            "target_player_id": target_player_id,
            "is_correct": is_correct,
            "matched_word": matched_word,   # NEW — D-05
            "match_type": match_type,       # NEW — D-05
        }

    self.broadcaster.broadcast("guess_result", broadcast_data)
    return {"ok": True, "is_correct": is_correct}
```

**Return dict pattern** (`server/game_server.py` general):
```python
# Success:
return {"ok": True, "is_correct": is_correct}
# Failure (guard checks):
return {"error": "session_not_found"}
```

No change to error returns. `matched_word` and `match_type` go into the broadcast payload, not the return dict.

---

### `config.py` (config) — add `WU_PALMER_THRESHOLD`

**Analog:** self — lines 31–39

**Existing constant block pattern** (`config.py` lines 31–39):
```python
# Per-phase timer durations in seconds (D-04). Tune here; never in game logic.
PHASE_DURATIONS = {
    "ROUND_START":    5,
    "HINT_PHASE":    60,
    ...
}
```

Copy the inline comment convention: `# Short description (D-XX).` followed immediately by the constant. Add after `PHASE_DURATIONS`:
```python
# Wu-Palmer similarity threshold for synonym arbitration (D-01).
# 0.7 accepts near-synonyms (e.g., banana ~ apple = 0.82); tune here, never in arbitration.py.
WU_PALMER_THRESHOLD = 0.7
```

---

### `validate_manifest.py` (utility, file-I/O)

**Closest analog:** `server/game_server.py` lines 92–94 (manifest load) + `server/turn_machine.py` (pure-Python module, no Pyro5 dependency)

No direct standalone-script analog exists in the project. Use `game_server.py`'s manifest load as the I/O pattern and `turn_machine.py`'s module header as the doc style.

**Manifest load pattern** (`server/game_server.py` lines 92–94):
```python
manifest_path = os.path.join(os.path.dirname(__file__), "images", "manifest.json")
with open(manifest_path, encoding="utf-8") as manifest_file:
    self._image_manifest: dict = json.load(manifest_file)
```

For `validate_manifest.py` at project root, adjust `__file__` reference:
```python
import os, json
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "server", "images", "manifest.json")
with open(MANIFEST_PATH, encoding="utf-8") as f:
    manifest = json.load(f)
```

**Script exit pattern** (project convention — no existing analog; use stdlib):
```python
import sys
if excluded:
    sys.exit(1)   # Non-zero for CI
```

**Logging/print pattern** — `validate_manifest.py` uses `print()` (human-readable report), not `logging`, since it is a standalone CLI tool. Contrast with `game_server.py` which uses `logging.warning()`.

---

### `requirements.txt` (config) — add `nltk==3.9.4`

**Analog:** self — lines 1–5

**Existing format** (`requirements.txt` lines 1–5):
```
Pyro5==5.16
Flask==3.1.3
flask-socketio==5.6.1
simple-websocket==1.1.0
pytest
```

Pattern: pinned `Package==version` one per line; `pytest` is unpinned (test-only). Add:
```
nltk==3.9.4
```

Place after `simple-websocket` (runtime deps together) and before `pytest`.

---

### `tests/test_arbitration.py` (test, transform)

**Analog:** `tests/test_exchange.py` (pure-unit tests, FakeBroadcaster, direct server instantiation) and `tests/test_scoring.py` (pure-function unit tests, no Pyro5 daemon, no fixtures)

**Module header pattern** (`tests/test_exchange.py` lines 1–5, `tests/test_scoring.py` lines 1–4):
```python
"""Unit tests for Phase 5 exchange and spy mechanics."""

import pytest
from server.game_server import GameServer
```

```python
"""Unit tests for Phase 4 scoring behavior."""

from server.turn_machine import _calculate_score_deltas
```

For `test_arbitration.py`:
```python
"""Unit tests for arbitration module (GUESS-03 coverage)."""

import pytest
from server.arbitration import arbitrate, ensure_nltk_corpora
```

**Pure-function test pattern** (`tests/test_scoring.py` lines 7–17):
```python
def test_tiered_guessers():
    """SCORE-01: tiered guesser points are 20, 15, 10, then minimum 5."""
    ts = TurnState(turn_number=1, player_ids=["p1", "p2", "p3", "p4"])
    ts.correct_guesses = ["p1", "p2", "p3", "p4"]

    deltas = _calculate_score_deltas(ts)

    assert deltas["p1"] == 20, f"1st correct should get 20pts, got {deltas['p1']}"
```

Pattern: one assert cluster per test, f-string in assert message, requirement ID in docstring. Copy this style for each `test_arbitration.py` test function.

**Module-level setup pattern** (no existing analog — `test_scoring.py` and `test_exchange.py` need no corpus):
```python
# Ensure corpora available before any test runs (once per pytest session)
ensure_nltk_corpora()

THRESHOLD = 0.7
```

Place corpus guard at module top, after imports, before first test function.

**FakeBroadcaster pattern** (`tests/test_exchange.py` lines 9–24) — not needed for `test_arbitration.py` since `arbitrate()` is a pure function. Do not include FakeBroadcaster.

---

## Shared Patterns

### Config constant consumption
**Source:** `config.py` + `server/turn_machine.py` usage
**Apply to:** `server/game_server.py` (caller of `arbitrate()`), `server/arbitration.py` (does NOT import config directly)
```python
# In game_server.py — pass threshold from config to the pure function:
import config
is_correct, matched_word, match_type = arbitrate(
    guess_clean, expected, config.WU_PALMER_THRESHOLD
)
```

### Manifest load (json + os.path)
**Source:** `server/game_server.py` lines 92–94
**Apply to:** `validate_manifest.py` (standalone script; adjust dirname path)
```python
manifest_path = os.path.join(os.path.dirname(__file__), "images", "manifest.json")
with open(manifest_path, encoding="utf-8") as manifest_file:
    self._image_manifest: dict = json.load(manifest_file)
```

### Broadcast outside lock
**Source:** `server/game_server.py` lines 569–572
**Apply to:** `server/game_server.py` `submit_guess()` — no change; arbitration call happens inside lock (reads `image_assignments`); `broadcaster.broadcast()` remains after `with self.lock:` exits.
```python
    # broadcast_data built inside lock, broadcast OUTSIDE:
    self.broadcaster.broadcast("guess_result", broadcast_data)
    return {"ok": True, "is_correct": is_correct}
```

### Return dict shape
**Source:** `server/game_server.py` — all `@expose` methods
**Apply to:** `server/game_server.py` `submit_guess()` return (unchanged); `arbitrate()` returns a tuple, not a dict — this is correct for a private utility.
```python
# Success return from @expose method:
return {"ok": True, "is_correct": is_correct}
# Error guard:
return {"error": "session_not_found"}
```

### Module docstring style
**Source:** `server/turn_machine.py` lines 1–10
**Apply to:** `server/arbitration.py`
```python
"""Synonym arbitration for guess matching.

Uses NLTK WordNet + omw-1.4 for Portuguese synonym matching.
Provides a three-tier decision: exact → synonym → fallback.
"""
```

### Logging setup
**Source:** `server/turn_machine.py` line 20
**Apply to:** `server/arbitration.py` (module logger), `server/game_server.py` `_validate_manifest_words()` (uses `logging.warning()`)
```python
logger = logging.getLogger(__name__)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `validate_manifest.py` | utility | file-I/O | No standalone CLI script exists in project; closest partial analog is manifest load in `game_server.__init__()`. Planner should use RESEARCH.md Pattern 6 + the manifest load excerpt above. |

---

## Metadata

**Analog search scope:** `server/`, `tests/`, `config.py`, `requirements.txt`
**Files scanned:** `server/game_server.py`, `server/turn_machine.py`, `server/turn_state.py`, `tests/test_session.py`, `tests/test_exchange.py`, `tests/test_scoring.py`, `tests/test_turn_machine.py`, `config.py`, `requirements.txt`, `pytest.ini`
**Pattern extraction date:** 2026-05-15
