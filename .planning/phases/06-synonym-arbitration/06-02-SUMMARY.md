---
phase: 06-synonym-arbitration
plan: "02"
subsystem: arbitration
tags: [nltk, wordnet, omw-1.4, synonym-matching, wu-palmer, pytest, python]

dependency_graph:
  requires:
    - phase: "06-01"
      provides: "Portuguese manifest, WU_PALMER_THRESHOLD config, nltk==3.9.4 dep, test stubs"
  provides:
    - "server/arbitration.py with arbitrate(), ensure_nltk_corpora(), _max_wup_similarity()"
    - "8 passing pytest tests covering GUESS-03a/b/c, D-05, D-06"
    - "validate_manifest.py standalone CLI — 12 valid PT words, exits 0"
  affects:
    - "server/game_server.py (plan 06-03: wire arbitrate() into submit_guess())"
    - "bridge/server.py (plan 06-03: relay matched_word + match_type in GUESS_RESULT)"

tech-stack:
  added: []
  patterns:
    - "Pure-function arbitration module — threshold passed as parameter, no config import"
    - "ensure_nltk_corpora() with .zip guard path (corpora/wordnet.zip, corpora/omw-1.4.zip)"
    - "_max_wup_similarity() max cross-product Wu-Palmer over all synset pairs"
    - "validate_manifest.py: sys.path.insert to import from server/, print() for CLI output, sys.exit(1) for CI"

key-files:
  created:
    - server/arbitration.py
    - validate_manifest.py
  modified:
    - tests/test_arbitration.py

key-decisions:
  - "test_synonym_pt_guess_pt_target uses xícara vs copo (wup=0.875) — verified live, confirmed above 0.7 threshold"
  - "test_fallback_when_no_synsets uses xyzzy vs abcde (two distinct unknown words, no synsets) — forces step (c)"
  - "test_wup_threshold_boundary uses real word pairs: xícara/copo for above-threshold, cachorro/maçã for below"
  - "arbitration.py strictly Portuguese-only (lang='por') — no English fallback needed since manifest was updated in 06-01"

patterns-established:
  - "Pattern: module-private _max_wup_similarity() with None guard before comparison"
  - "Pattern: arbitrate() returns (bool, str|None, str) tuple — match_type always set per D-06"

requirements-completed:
  - GUESS-03

duration: ~15min
completed: 2026-05-15
---

# Phase 06 Plan 02: Core Arbitration Module Summary

**Three-tier arbitration (exact/synonym/fallback) in server/arbitration.py with 8 passing tests and validate_manifest.py reporting 12 valid Portuguese words.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-15T16:30:00Z
- **Completed:** 2026-05-15T16:45:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `server/arbitration.py` implemented with three-tier decision: exact match → Wu-Palmer synonym via omw-1.4 → fallback exact
- All 8 test stubs in `tests/test_arbitration.py` filled in and passing
- `validate_manifest.py` confirms all 12 Portuguese manifest words have omw-1.4 synsets (exits 0)

## Task Commits

1. **Tasks 1+2: arbitrate(), test suite, validate_manifest** — `88bc579` (feat)

## Files Created/Modified

- `/home/spacko/projects/faculdade/sd-rpc-av-1/server/arbitration.py` — ensure_nltk_corpora(), _max_wup_similarity(), arbitrate() pure function
- `/home/spacko/projects/faculdade/sd-rpc-av-1/validate_manifest.py` — standalone CLI, 12 valid words, sys.exit(1) on exclusions
- `/home/spacko/projects/faculdade/sd-rpc-av-1/tests/test_arbitration.py` — 8 tests covering all three tiers and D-05/D-06 contracts

## Decisions Made

**Test pair for synonym tier (test_synonym_pt_guess_pt_target):**
- Chose `xícara` vs `copo` (cup vs glass/goblet) — wup_similarity=0.875, verified live in project venv. Both have Portuguese synsets via omw-1.4. Clear semantic relationship (drinking containers) that sits comfortably above the 0.7 threshold.

**Test pair for threshold boundary (test_wup_threshold_boundary):**
- Above threshold: `xícara` vs `copo` (wup=0.875 > 0.7) — accepted
- Below threshold: `cachorro` vs `maçã` (wup=0.545 < 0.7) — rejected
- These pairs are reused from other tests for consistency and because they have confirmed similarity values.

**Test for fallback tier (test_fallback_when_no_synsets):**
- Used `xyzzy` vs `abcde` — two distinct strings with zero Portuguese synsets. Different strings so step (a) exact match does not fire; no synsets so step (b) synonym match is skipped; reaches step (c) fallback which returns ok=False for non-identical strings.

**arbitration.py strictly Portuguese-only:**
- No English language fallback in arbitrate() since Plan 06-01 updated manifest.json to Portuguese words (Option A). The RESEARCH.md code example had an English fallback but Plan 06-02 contract specifies lang='por' only. This is cleaner and matches D-02 "Portuguese only" intent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_fallback_when_no_synsets initial implementation returned 'exact' not 'fallback'**
- **Found during:** Task 1 test run
- **Issue:** Original stub body used `arbitrate('xyzzy', 'xyzzy', THRESHOLD)` — identical strings trigger step (a) exact match before reaching fallback, so `match_type` was `'exact'` not `'fallback'`
- **Fix:** Changed to `arbitrate('xyzzy', 'abcde', THRESHOLD)` — distinct unknown words with no synsets, forces step (c) fallback path
- **Files modified:** tests/test_arbitration.py
- **Committed in:** 88bc579

**2. [Rule 1 - Bug] test_wup_threshold_boundary initial implementation same issue with xyzzy**
- **Found during:** Task 1 test run (same run as above)
- **Issue:** Used `arbitrate('xyzzy', 'xyzzy', 0.7)` expecting 'fallback' but got 'exact' (same root cause)
- **Fix:** Rewrote test_wup_threshold_boundary to use real confirmed word pairs (xícara/copo and cachorro/maçã) instead of unknown-word boundary demonstration
- **Files modified:** tests/test_arbitration.py
- **Committed in:** 88bc579

---

**Total deviations:** 2 auto-fixed (Rule 1 — test assertion bugs from initial design)
**Impact on plan:** Both fixes corrected test assertion logic to match actual arbitrate() behavior. No change to implementation.

## Issues Encountered

The test stubs originally tried to test the fallback path with identical unknown words (`xyzzy` vs `xyzzy`). The exact-match step fires first for identical strings regardless of synset availability, so those tests returned `'exact'` not `'fallback'`. Corrected by using distinct unknown words for fallback test and real confirmed word pairs for the threshold test.

## User Setup Required

None — all required corpora (wordnet, omw-1.4) are downloaded automatically by `ensure_nltk_corpora()` at server startup. No manual steps needed.

## Next Phase Readiness

- `server/arbitration.py` is production-ready: pure function, typed, tested
- Plan 06-03 can wire `arbitrate()` into `game_server.py` `submit_guess()` immediately
- `validate_manifest.py` can be run by developers/CI to verify Portuguese manifest coverage

---
*Phase: 06-synonym-arbitration*
*Completed: 2026-05-15*
