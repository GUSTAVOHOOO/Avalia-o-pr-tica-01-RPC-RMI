---
phase: 06-synonym-arbitration
plan: "03"
subsystem: arbitration-integration
tags: [nltk, wordnet, omw-1.4, game-server, submit-guess, guess-result, wu-palmer, corpus-warmup]

dependency_graph:
  requires:
    - phase: "06-02"
      provides: "server/arbitration.py with arbitrate(), ensure_nltk_corpora(); 8 passing tests; validate_manifest.py"
    - phase: "06-01"
      provides: "WU_PALMER_THRESHOLD in config.py, Portuguese manifest, nltk==3.9.4"
  provides:
    - "server/game_server.py wired: submit_guess() calls arbitrate(), GUESS_RESULT enriched with matched_word + match_type"
    - "GameServer.__init__() with corpus guard, warmup, and _validate_manifest_words()"
  affects:
    - "bridge/server.py (already relays GUESS_RESULT broadcast — matched_word and match_type are transparently forwarded)"
    - "client frontend (can now display match_type and matched_word in UI)"

tech-stack:
  added: []
  patterns:
    - "Corpus warmup in __init__() before server accepts connections (wn.synsets pre-call outside the lock)"
    - "Manifest validation at startup: log WARNING for words with zero Portuguese synsets, exclude from pool (D-03/D-04)"
    - "arbitrate() called inside with self.lock — corpus is pre-warmed so no lazy I/O occurs during lock hold (T-06-06)"
    - "broadcast_data enriched inside lock, broadcaster.broadcast() called outside lock (broadcast-outside-lock pattern)"

key-files:
  created: []
  modified:
    - server/game_server.py

key-decisions:
  - "matched_word and match_type added only to broadcast_data, not to the submit_guess() return dict — return dict stays {ok: True, is_correct: bool} per existing contract"
  - "wn import kept local inside __init__() and _validate_manifest_words() to avoid module-level import order issues with Pyro5"
  - "_validate_manifest_words() logs using stdlib logging.warning() (not logger = getLogger) to match existing game_server.py style"

requirements-completed:
  - GUESS-03

duration: ~10min
completed: 2026-05-15
---

# Phase 06 Plan 03: Arbitration Wired into GameServer Summary

**arbitrate() wired into submit_guess() with corpus warmup and manifest validation in GameServer.__init__(), GUESS_RESULT broadcast enriched with matched_word and match_type.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-15T17:00:00Z
- **Completed:** 2026-05-15T17:10:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `GameServer.__init__()` now calls `ensure_nltk_corpora()`, warms up the Portuguese WordNet corpus with `wn.synsets('teste', lang='por')`, and filters `self._image_manifest` via `_validate_manifest_words()`
- `_validate_manifest_words()` method added: filters manifest to words with Portuguese omw-1.4 coverage; logs WARNING for exclusions (D-03/D-04); all 12 manifest words pass at runtime
- `submit_guess()` replaces single exact-match line with `arbitrate(guess_clean, expected, config.WU_PALMER_THRESHOLD)` returning `(is_correct, matched_word, match_type)`
- `GUESS_RESULT` broadcast payload enriched with `matched_word` (D-05) and `match_type` (D-06)
- Full pytest suite: 60 passing, 1 pre-existing failure in `test_turn_state.py` (unrelated to this plan, not introduced here)

## Task Commits

1. **Tasks 1+2: arbitration wired into game_server** — `2deb77e` (feat)

## Files Created/Modified

- `/home/spacko/projects/faculdade/sd-rpc-av-1/server/game_server.py` — 34 lines added: import, __init__() corpus guard + warmup + manifest validation call, _validate_manifest_words() method, submit_guess() arbitrate() call, GUESS_RESULT payload enrichment

## Decisions Made

**matched_word/match_type in broadcast only:**
- Per plan spec, these fields go into `broadcast_data` (sent to all players via Pyro5 callbacks), NOT into the `submit_guess()` return dict. The return dict `{"ok": True, "is_correct": is_correct}` is unchanged — the bridge already reads this for immediate caller response.

**wn import kept local, not at module level:**
- `from nltk.corpus import wordnet as wn` is placed inside `__init__()` and `_validate_manifest_words()` rather than at module level. This avoids potential import-order issues at Pyro5 daemon startup and keeps the NLTK dependency isolated to the two methods that need it.

**_validate_manifest_words() uses stdlib logging.warning():**
- The method uses `import logging; logging.warning(...)` matching the warning-level log style used elsewhere in the server for startup diagnostics, rather than the `logger = getLogger(__name__)` pattern (which would require a module-level logger that doesn't currently exist in game_server.py).

## Deviations from Plan

None — plan executed exactly as written. The plan's Task 1 included both the import addition and the `_validate_manifest_words()` method (CHANGE 1, 2, and 3). Both tasks completed cleanly with no unexpected issues.

## Verification Results

```
grep -n "ensure_nltk_corpora|_validate_manifest_words|from server.arbitration" server/game_server.py
30:from server.arbitration import arbitrate, ensure_nltk_corpora
99:        ensure_nltk_corpora()
104:        self._image_manifest = self._validate_manifest_words()
106:    def _validate_manifest_words(self) -> dict:

grep -n "arbitrate|matched_word|match_type" server/game_server.py
30:from server.arbitration import arbitrate, ensure_nltk_corpora
589:            is_correct, matched_word, match_type = arbitrate(
600:                "matched_word": matched_word,
601:                "match_type": match_type,

pytest tests/ -q
1 failed, 60 passed in 6.27s
(pre-existing failure: tests/test_turn_state.py::test_get_player_view_returns_current_object_assignment — unrelated to Phase 06)
```

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. `matched_word` is the canonical target word — already revealed when `is_correct=True`, no new information disclosure (T-06-07 accepted per threat model). Corpus warmup at startup mitigates T-06-06 (DoS via WordNet lazy-load inside lock).

## Self-Check

- [x] `server/game_server.py` modified — verified
- [x] Commit `2deb77e` exists — verified via git log
- [x] `from server.arbitration import arbitrate, ensure_nltk_corpora` present — line 30
- [x] `ensure_nltk_corpora()` in `__init__()` — line 99
- [x] `self._validate_manifest_words()` in `__init__()` — line 104
- [x] `def _validate_manifest_words(self)` method defined — line 106
- [x] `arbitrate(` in `submit_guess()` — line 589
- [x] `matched_word` in broadcast_data — line 600
- [x] `match_type` in broadcast_data — line 601
- [x] pytest: 60 passing, same 1 pre-existing failure

## Self-Check: PASSED

---
*Phase: 06-synonym-arbitration*
*Plan: 03 (Wave 2 — final wave)*
*Completed: 2026-05-15*
