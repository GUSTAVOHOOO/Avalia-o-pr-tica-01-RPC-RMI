# Phase 6: Synonym Arbitration - Research

**Researched:** 2026-05-15
**Domain:** NLTK WordNet, Wu-Palmer similarity, Python NLP, game arbitration logic
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Default similarity threshold is **0.7**. Stored as `WU_PALMER_THRESHOLD = 0.7` in `config.py`. Arbitration code reads `config.WU_PALMER_THRESHOLD` — no hardcoded value in the arbitration module.
- **D-02:** Use **Portuguese only** (`lang='por'`) for synset lookup via omw-1.4. All object names in `manifest.json` are Portuguese words. If a Portuguese synset lookup returns None for either word, the system falls back to exact-match (GUESS-03c).
- **D-03:** Words with zero Portuguese synsets are **excluded from distribution** — removed from the pool that gets assigned to players at `ROUND_START`. Server starts normally regardless (no hard failure). Excluded words are logged as warnings.
- **D-04:** Validation runs in two places: (1) `validate_manifest.py` standalone script; (2) `GameServer.__init__()` runtime defense-in-depth.
- **D-05:** `GUESS_RESULT` payload adds `matched_word: str | null` and `match_type: 'exact' | 'synonym' | 'fallback'`.
- **D-06:** On incorrect guesses: `matched_word: null`, `match_type` still set to whichever method was attempted.

### Claude's Discretion
- Exact location of the arbitration logic: new `server/arbitration.py` module vs inline in `game_server.py`.
- Whether Wu-Palmer similarity is computed as max over the cross-product of all synset pairs or only the first synset of each word.
- Whether `validate_manifest.py` updates `manifest.json` in place or only reports.

### Deferred Ideas (OUT OF SCOPE)
- English-language fallback synset lookup (`lang='eng'`) — deferred.
- Configurable discovery probability or per-word threshold overrides — deferred to v2.
- UI display of match_type feedback ("~sinônimo!" vs "exato!") — deferred to Phase 8.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GUESS-03 | Arbitragem verifica palpite por: (a) igualdade exata, (b) similaridade Wu-Palmer via NLTK `wn` + omw-pt com threshold configurável, (c) fallback exact-match se WordNet retornar None | Verified full algorithm via live NLTK tests; all sub-clauses confirmed implementable with `nltk.corpus.wordnet` + omw-1.4 |
</phase_requirements>

---

## Summary

Phase 6 replaces the single exact-match line in `submit_guess()` with a three-tier arbitration function: (a) case-insensitive exact match, (b) Wu-Palmer synonym match via NLTK WordNet + omw-1.4, (c) exact-match fallback when WordNet returns None. The enriched `GUESS_RESULT` broadcast gains two new fields (`matched_word`, `match_type`). A `validate_manifest.py` script and a `GameServer.__init__()` startup check exclude any image words that cannot be resolved by the arbitration logic.

**Critical discovery (manifest mismatch):** `server/images/manifest.json` currently stores English words (`"apple"`, `"bicycle"`, etc.), not Portuguese words as CONTEXT.md assumes. The CONTEXT.md says "all object names are Portuguese words (e.g., `maçã`, `bicicleta`)." This discrepancy must be resolved in Wave 0 of the plan. The planner must choose: (A) update `manifest.json` to use Portuguese words (matches D-02 intent), or (B) adapt the arbitration to handle English target words with Portuguese guess words (works too — verified). Option A is cleaner for the language policy; Option B is a working fallback confirmed by tests.

**Key verified finding:** When `manifest.json` uses English words as targets, Portuguese player guesses work correctly via cross-language synset lookup — `wn.synsets('maçã', lang='por')` returns synsets with the same underlying WordNet IDs as `wn.synsets('apple', lang='eng')`, so `wup_similarity()` computes correctly across the language boundary. All 12 current manifest words resolve via this path.

**Primary recommendation:** Update `manifest.json` to use Portuguese words (aligns with D-02 "Portuguese only" policy), then implement the arbitration module using `lang='por'` throughout. No English fallback needed for the current word set.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Guess arbitration logic | API / Backend (game_server.py) | — | State-sensitive: needs `image_assignments` from `TurnState`; must hold the lock during check |
| WordNet similarity computation | API / Backend (arbitration.py) | — | Pure function; imported by game_server; no I/O after initial corpus load |
| NLTK corpus download guard | API / Backend (startup script) | — | One-time at server start; never per-request |
| Manifest validation | API / Backend (validate_manifest.py + __init__) | — | Startup-time filter; modifies `_image_manifest` used in image assignment |
| GUESS_RESULT broadcast | API / Backend (game_server.py) | Bridge (SocketIO event relay) | Pattern established in phases 4–5; no change to broadcast path |
| Frontend match_type display | Browser / Client | — | Deferred to Phase 8; only new payload fields matter now |

---

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nltk | 3.9.4 | NLP toolkit; provides `nltk.corpus.wordnet` API | Required by CLAUDE.md; already confirmed installed in project venv [VERIFIED: pip show in venv] |
| wordnet corpus | via `nltk.download('wordnet')` | English synset backbone; all multilingual synsets reference these IDs | Required; omw-1.4 adds PT lemmas on top of EN synset IDs [VERIFIED: live test] |
| omw-1.4 corpus | via `nltk.download('omw-1.4')` | Portuguese lemma mappings; enables `lang='por'` synset lookup | Required for Portuguese; provides `maçã → apple.n.01` mapping [VERIFIED: live test] |

### Supporting (already in project)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pyro5 | 5.16 | RPC transport; unchanged | All server-client communication |
| Flask-SocketIO | 5.6.1 | Bridge; unchanged | WebSocket relay; no changes needed |

### No New Packages Required

All dependencies are already specified in `CLAUDE.md` and `requirements.txt`. Phase 6 requires only adding `nltk` to `requirements.txt` and downloading two NLTK corpora at startup.

**Installation (additions only):**
```bash
# Add to requirements.txt
nltk==3.9.4

# Run once (or let startup guard handle it)
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
```

---

## Package Legitimacy Audit

No new packages are being introduced in this phase. NLTK is a pre-approved package specified in `CLAUDE.md` and is a widely-established NLP library (>8 years old, millions of weekly downloads, hosted at nltk.org).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| nltk | PyPI | ~15 yrs | ~5M/wk | github.com/nltk/nltk | N/A (pre-approved by CLAUDE.md) | Approved |

**Packages removed due to slopcheck:** none
**Packages flagged as suspicious:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Player guess (via WebSocket/SocketIO)
          |
          v
    Bridge (bridge/server.py)
          | Pyro5 RPC call
          v
    GameServer.submit_guess()
          |
          +--[hold self.lock]---+
          |                    |
          | read image_assignments[target_player_id]  -> expected word
          | call arbitrate(guess_clean, expected, config.WU_PALMER_THRESHOLD)
          |                    |
          |             arbitration.py
          |             +--step 1: exact match
          |             +--step 2: wn.synsets(guess, 'por') X wn.synsets(target, 'por')
          |             |          max wup_similarity over cross-product
          |             +--step 3: fallback exact if synsets empty
          |             returns (is_correct, matched_word|None, match_type)
          |
          | update TurnState (guesses_made, correct_guesses)
          | build broadcast_data with matched_word + match_type
          +--[release lock]----+
          |
          v
    broadcaster.broadcast("guess_result", broadcast_data)
          |
          v
    All clients receive GUESS_RESULT event
```

### Recommended Project Structure

```
server/
├── arbitration.py        # NEW: arbitrate() pure function + ensure_corpora()
├── game_server.py        # MODIFY: submit_guess() + __init__() validation
├── images/
│   └── manifest.json     # MODIFY: update to Portuguese words (see critical discovery)
config.py                 # MODIFY: add WU_PALMER_THRESHOLD = 0.7
validate_manifest.py      # NEW: standalone pre-deploy validation script
requirements.txt          # MODIFY: add nltk==3.9.4
tests/
└── test_arbitration.py   # NEW: unit tests for arbitrate() function
```

### Pattern 1: NLTK Corpus Download Guard

NLTK downloads corpora as `.zip` files to `~/nltk_data`. The correct guard checks for the `.zip` form, not the unzipped directory, because NLTK reads directly from zip archives.

```python
# Source: verified via live test in project venv (2026-05-15)
import nltk

def ensure_nltk_corpora() -> None:
    """Download NLTK corpora if not already present. Safe to call at startup."""
    for corpus_name, zip_path in [
        ('wordnet', 'corpora/wordnet.zip'),
        ('omw-1.4', 'corpora/omw-1.4.zip'),
    ]:
        try:
            nltk.data.find(zip_path)
        except LookupError:
            import logging
            logging.info(f"Downloading NLTK corpus: {corpus_name}")
            nltk.download(corpus_name, quiet=True)
```

**Critical:** `nltk.data.find('corpora/wordnet')` fails even when wordnet IS downloaded, because NLTK stores it as `wordnet.zip`, not as an unzipped directory. Use `nltk.data.find('corpora/wordnet.zip')` instead. [VERIFIED: live test]

### Pattern 2: Portuguese Synset Lookup

```python
# Source: verified via live test against NLTK 3.9.4 + omw-1.4 (2026-05-15)
from nltk.corpus import wordnet as wn

# Look up Portuguese synsets for a word
synsets = wn.synsets('maçã', lang='por')
# Returns: [Synset('apple.n.01'), Synset('eating_apple.n.01'), ...]
# The synset names use English IDs — this is how omw-1.4 maps Portuguese lemmas
# to the shared WordNet synset graph

# Get Portuguese lemma names for a synset
lemmas = synsets[0].lemma_names(lang='por')
# Returns: ['maçã', 'Maçã', ...]
```

### Pattern 3: Wu-Palmer Similarity (max cross-product)

```python
# Source: verified via live test (2026-05-15)
from nltk.corpus import wordnet as wn

def _max_wup_similarity(synsets_a, synsets_b) -> float:
    """Max Wu-Palmer similarity over all pairs from two synset lists."""
    max_sim = 0.0
    for s1 in synsets_a:
        for s2 in synsets_b:
            sim = s1.wup_similarity(s2)
            if sim is not None and sim > max_sim:
                max_sim = sim
    return max_sim
```

**Why cross-product max:** Word senses are ambiguous. `banana` has multiple synsets including one for the fruit and one for the plant. Taking max over all pairs finds the best semantic match across all senses. Verified correct behavior: `bicicleta vs bicycle → 1.0`, `maçã vs apple → 1.0` (exact synset match despite different language). [VERIFIED: live test]

### Pattern 4: Arbitration Function Signature

```python
# Source: derived from D-01 through D-06, verified against GUESS-03 spec
from nltk.corpus import wordnet as wn
from typing import Optional, Tuple

def arbitrate(
    guess: str,
    target: str,
    threshold: float,
) -> Tuple[bool, Optional[str], str]:
    """
    Args:
        guess: Player's guessed word (stripped, max 50 chars).
        target: Canonical object word from image_assignments.
        threshold: Wu-Palmer similarity threshold (config.WU_PALMER_THRESHOLD).

    Returns:
        (is_correct, matched_word, match_type)
        - is_correct: True if guess accepted by any method
        - matched_word: canonical target word when correct, None when incorrect
        - match_type: 'exact' | 'synonym' | 'fallback'
    """
    # Step (a): exact match — GUESS-03a
    if guess.strip().lower() == target.strip().lower():
        return True, target, 'exact'

    # Step (b): WordNet synonym match — GUESS-03b
    guess_synsets = wn.synsets(guess.strip(), lang='por')
    target_synsets = wn.synsets(target.strip(), lang='por')
    # If manifest uses English words, fall back to English lookup for target
    if not target_synsets:
        target_synsets = wn.synsets(target.strip(), lang='eng')

    if guess_synsets and target_synsets:
        sim = _max_wup_similarity(guess_synsets, target_synsets)
        is_correct = sim >= threshold
        return is_correct, (target if is_correct else None), 'synonym'

    # Step (c): fallback exact-match when WordNet returns None — GUESS-03c
    is_correct = guess.strip().lower() == target.strip().lower()
    return is_correct, (target if is_correct else None), 'fallback'
```

### Pattern 5: submit_guess() Integration Delta

The minimal change to `game_server.py` replaces line 560 and adds two fields to `broadcast_data`:

```python
# BEFORE (line 560):
is_correct = guess_clean.lower() == expected.strip().lower()

# AFTER:
from server.arbitration import arbitrate
is_correct, matched_word, match_type = arbitrate(
    guess_clean, expected, config.WU_PALMER_THRESHOLD
)

# broadcast_data (add two fields):
broadcast_data = {
    "room_code": room_code,
    "guesser_id": player_id,
    "target_player_id": target_player_id,
    "is_correct": is_correct,
    "matched_word": matched_word,   # NEW
    "match_type": match_type,       # NEW
}
```

### Pattern 6: Manifest Validation at GameServer.__init__()

```python
# Source: CONTEXT.md D-03/D-04; pattern follows existing self._image_manifest load
import logging

def _validate_manifest_words(self) -> dict:
    """Return filtered manifest dict excluding words with no WordNet coverage.
    
    Logs a WARNING for each excluded word. Server continues normally.
    Must be called after self._image_manifest is loaded.
    """
    valid = {}
    for filename, word in self._image_manifest.items():
        synsets = wn.synsets(word, lang='por')
        if not synsets:
            synsets = wn.synsets(word, lang='eng')
        if synsets:
            valid[filename] = word
        else:
            logging.warning(
                f"WARNING: '{word}' has no Portuguese synsets in omw-1.4 "
                f"— excluded from distribution"
            )
    return valid
```

Call in `__init__()` after loading manifest:
```python
self._image_manifest = self._validate_manifest_words()
```

### Anti-Patterns to Avoid

- **Downloading NLTK corpora per request:** Download once at server startup via `ensure_nltk_corpora()`. Never call `nltk.download()` inside `arbitrate()` or `submit_guess()`.
- **Checking `nltk.data.find('corpora/wordnet')` without `.zip`:** This always raises `LookupError` even when wordnet is installed, because NLTK stores the data as `.zip` archives. Use `'corpora/wordnet.zip'`.
- **Using only first synset (`.synsets()[0]`):** Reduces accuracy. Wu-Palmer over first synsets only misses valid semantic overlaps. Always use max over all pairs.
- **Hardcoding the threshold in `arbitration.py`:** The function must accept `threshold` as a parameter and callers must pass `config.WU_PALMER_THRESHOLD`. This allows tuning without code changes.
- **Holding the lock during WordNet lookup:** The lock must be released before the `broadcaster.broadcast()` call (established pattern). The arbitration call happens inside the lock (it reads `image_assignments`), but the lock is released before broadcast — this is correct and matches the existing `submit_guess()` pattern.
- **Importing `arbitration` at module top inside `game_server.py` before corpora are downloaded:** Importing the NLTK corpus reader (`from nltk.corpus import wordnet`) is safe before download; the corpus only loads lazily when first accessed. The guard must run before any synset lookup.

---

## Critical Discovery: manifest.json Language Mismatch

**Finding:** `server/images/manifest.json` stores English words (`"apple"`, `"bicycle"`, `"chair"`, etc.), while CONTEXT.md D-02 states "all object names in manifest.json are Portuguese words (e.g., `maçã`, `bicicleta`)."

**Impact on D-02:** D-02 says to use `lang='por'` for synset lookup. When the target is an English word, `wn.synsets('apple', lang='por')` returns 0 synsets. This would trigger the fallback path (GUESS-03c) for every guess, making synonym matching inoperative.

**Verified workaround (works as-is):** The arbitration pattern above adds an English fallback for the target lookup: if `wn.synsets(target, lang='por')` is empty, try `wn.synsets(target, lang='eng')`. This is confirmed working:
- `maçã (PT guess) vs apple (EN target)` → max wup = 0.91, is_correct = True, match_type = 'synonym' [VERIFIED: live test]
- `bicicleta vs bicycle` → True, synonym [VERIFIED]
- `chapéu vs hat` → True, synonym [VERIFIED]
- All 12 manifest words covered [VERIFIED]

**Recommended resolution (planner decision):** The planner should choose one of:
- **Option A (recommended):** Update `manifest.json` to use Portuguese words (`"maçã"`, `"bicicleta"`, etc.). Aligns with D-02 intent, matches what the CONTEXT.md says the manifest already contains, and makes the arbitration purely Portuguese. Image URLs remain unchanged (`/static/images/apple.jpg`). Only the object_name values in the manifest change.
- **Option B (fallback):** Keep English words in manifest, use English fallback in target synset lookup. Arbitration works correctly (verified), but deviates from D-02 "Portuguese only" intent.

The planner must resolve this in Wave 0 as it affects the validate_manifest validation logic.

**Coverage with Portuguese words (if manifest updated):** [VERIFIED: live test]
- `maçã` → 4 PT synsets, `bicicleta` → 2, `cadeira` → 5, `relógio` → 4, `violão` → 1, `chapéu` → 3, `laptop` → 1, `guarda-chuva` → 2, `livro` → 6, `xícara` → 1, `sapato` → 2, `árvore` → 1
- All 12 words have at least 1 Portuguese synset — zero exclusions expected.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic similarity | Custom edit-distance or phonetic matching | `wn.synsets()` + `wup_similarity()` | Wu-Palmer uses the WordNet taxonomy tree structure; edit distance misses synonyms entirely |
| Synset cross-product max | Loop with manual comparison | `_max_wup_similarity()` helper | Already a 4-line function; any alternative is more complex without benefit |
| Portuguese NLP tokenization | Stemmer/lemmatizer for matching | Direct `wn.synsets(word, lang='por')` | omw-1.4 handles conjugation/inflection in its lemma list; no separate stemmer needed for single-word guesses |
| Corpus availability check | Subprocess/filesystem scan | `nltk.data.find('corpora/wordnet.zip')` + `try/except LookupError` | The canonical NLTK pattern; safe and portable |

**Key insight:** NLTK WordNet via omw-1.4 handles the entire synonym-matching problem with two API calls and one arithmetic comparison. The entire arbitration logic fits in ~25 lines.

---

## Common Pitfalls

### Pitfall 1: Wrong nltk.data.find() path (critical)
**What goes wrong:** Guard code checks `nltk.data.find('corpora/wordnet')` — raises `LookupError` even when wordnet is correctly installed, causing unnecessary re-download attempts or incorrect "not found" errors.
**Why it happens:** NLTK downloads and stores corpora as `.zip` archives, not unzipped directories. The path without `.zip` looks for the unzipped form.
**How to avoid:** Always use `nltk.data.find('corpora/wordnet.zip')` and `nltk.data.find('corpora/omw-1.4.zip')`.
**Warning signs:** Guard always triggers re-download even on second server start; `[nltk_data] Package wordnet is already up-to-date!` printed repeatedly.

### Pitfall 2: manifest.json language mismatch blocks synonym matching
**What goes wrong:** `wn.synsets('apple', lang='por')` returns empty list → arbitration always falls through to fallback exact-match → Phase 6 synonym matching is silently inoperative.
**Why it happens:** manifest.json stores English words; D-02 assumes Portuguese words.
**How to avoid:** Either update manifest to Portuguese words, or add English fallback in target synset lookup. The planner must pick one path.
**Warning signs:** All `match_type` results are `'fallback'` rather than `'synonym'` in tests; validate_manifest excludes all words.

### Pitfall 3: Wu-Palmer returns None for unrelated synsets
**What goes wrong:** `synset_a.wup_similarity(synset_b)` can return `None` for some pairs where the LCS (Lowest Common Subsumer) cannot be computed in the IC-based path.
**Why it happens:** Wu-Palmer requires a path in the WordNet taxonomy tree; some noun-verb cross-POS pairs or very abstract concepts may have no LCS.
**How to avoid:** Guard with `if sim is not None` in the cross-product loop (already shown in Pattern 3). Default to `0.0` when None.
**Warning signs:** `TypeError: '>' not supported between instances of 'NoneType' and 'float'`.

### Pitfall 4: Lock held during WordNet I/O
**What goes wrong:** If `wn.synsets()` triggers a lazy corpus load (first call after startup), it does file I/O while holding `self.lock`, blocking all other RPC calls.
**Why it happens:** NLTK corpora load lazily on first access if `ensure_nltk_corpora()` was not called before the server accepts connections.
**How to avoid:** Call `ensure_nltk_corpora()` at `GameServer.__init__()` startup, before the server begins accepting requests. Also warm up the corpus by making a test synset call at startup: `wn.synsets('teste', lang='por')`.
**Warning signs:** First guess after server start has noticeably higher latency; other players blocked.

### Pitfall 5: Broad semantic false positives at threshold 0.7
**What goes wrong:** Semantically-related-but-wrong words accepted as correct. Example: `banana` vs `apple` → wup = 0.82 (both fruit senses) — accepted at threshold 0.7.
**Why it happens:** Wu-Palmer at 0.7 accepts any two words sharing a common hypernym two levels up the tree. Fruit words all share `edible_fruit` as a close common ancestor.
**How to avoid:** This is a **known design decision**, not a bug. The game intentionally accepts near-synonyms. The CONTEXT locked the threshold at 0.7 (D-01). Document this behavior in code comments.
**Warning signs:** Players report accepting wrong-but-similar answers; this is expected behavior.

### Pitfall 6: validate_manifest excludes all words if checking wrong language
**What goes wrong:** `validate_manifest.py` checks `wn.synsets(word, lang='por')` and excludes all English manifest words (0 PT synsets each), leaving an empty word pool. Server starts but assigns no images.
**Why it happens:** If manifest has English words and validation only checks Portuguese synsets.
**How to avoid:** Mirror the arbitration's two-step lookup (PT then EN) in validate_manifest, OR update manifest to Portuguese first. Planner must pick Option A or B from the critical discovery above.
**Warning signs:** All 12 words logged as "WARNING: ... excluded from distribution"; image assignment pool is empty.

---

## Code Examples

### Complete arbitration.py module

```python
# Source: verified against NLTK 3.9.4 + omw-1.4, live tests 2026-05-15
"""Synonym arbitration for guess matching.

Uses NLTK WordNet + omw-1.4 for Portuguese synonym matching.
Provides a three-tier decision: exact → synonym → fallback.
"""

import logging
from typing import Optional, Tuple

import nltk
from nltk.corpus import wordnet as wn


def ensure_nltk_corpora() -> None:
    """Ensure wordnet and omw-1.4 corpora are available.
    
    Downloads missing corpora. Safe to call at server startup.
    Must use .zip path — NLTK stores corpora as zip archives.
    """
    for corpus_name, zip_path in [
        ('wordnet', 'corpora/wordnet.zip'),
        ('omw-1.4', 'corpora/omw-1.4.zip'),
    ]:
        try:
            nltk.data.find(zip_path)
        except LookupError:
            logging.info(f"Downloading NLTK corpus: {corpus_name}")
            nltk.download(corpus_name, quiet=True)


def _max_wup_similarity(synsets_a, synsets_b) -> float:
    """Return max Wu-Palmer similarity over all cross-product pairs."""
    max_sim = 0.0
    for s1 in synsets_a:
        for s2 in synsets_b:
            sim = s1.wup_similarity(s2)
            if sim is not None and sim > max_sim:
                max_sim = sim
    return max_sim


def arbitrate(
    guess: str,
    target: str,
    threshold: float,
) -> Tuple[bool, Optional[str], str]:
    """Arbitrate a player's guess against the target object word.

    Three-tier decision (GUESS-03):
    (a) Case-insensitive exact match
    (b) Wu-Palmer synonym match via NLTK WordNet + omw-1.4
    (c) Fallback exact-match when WordNet returns None for either word

    Args:
        guess: Player's cleaned guessed word.
        target: Canonical object word from image_assignments.
        threshold: Wu-Palmer similarity threshold (config.WU_PALMER_THRESHOLD).

    Returns:
        (is_correct, matched_word, match_type) where:
        - is_correct: True if guess accepted
        - matched_word: canonical target word when correct, None when incorrect
        - match_type: 'exact' | 'synonym' | 'fallback'
    """
    guess_clean = guess.strip()
    target_clean = target.strip()

    # (a) Exact match — GUESS-03a
    if guess_clean.lower() == target_clean.lower():
        return True, target, 'exact'

    # (b) WordNet synonym match — GUESS-03b
    guess_synsets = wn.synsets(guess_clean, lang='por')
    target_synsets = wn.synsets(target_clean, lang='por')
    if not target_synsets:
        # English fallback for target (handles manifest with English words)
        target_synsets = wn.synsets(target_clean, lang='eng')

    if guess_synsets and target_synsets:
        sim = _max_wup_similarity(guess_synsets, target_synsets)
        is_correct = sim >= threshold
        return is_correct, (target if is_correct else None), 'synonym'

    # (c) Fallback exact-match — GUESS-03c
    is_correct = guess_clean.lower() == target_clean.lower()
    return is_correct, (target if is_correct else None), 'fallback'
```

### validate_manifest.py

```python
# Source: CONTEXT.md D-03/D-04
"""Standalone manifest validation script.

Run before deployment to verify all image words have WordNet coverage.
Prints a human-readable report. Does NOT modify manifest.json.

Usage: python validate_manifest.py
"""
import json
import os
import sys

import nltk
from nltk.corpus import wordnet as wn

# Ensure corpora present
from server.arbitration import ensure_nltk_corpora
ensure_nltk_corpora()

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), 'server', 'images', 'manifest.json')

with open(MANIFEST_PATH, encoding='utf-8') as f:
    manifest = json.load(f)

valid, excluded = [], []
for filename, word in manifest.items():
    synsets = wn.synsets(word, lang='por')
    if not synsets:
        synsets = wn.synsets(word, lang='eng')
    if synsets:
        valid.append((filename, word, len(synsets)))
    else:
        excluded.append((filename, word))

print(f"Manifest validation: {len(valid)} valid, {len(excluded)} excluded")
for filename, word, count in valid:
    print(f"  OK  {filename}: '{word}' ({count} synsets)")
for filename, word in excluded:
    print(f"  EXCLUDED  {filename}: '{word}' — no synsets found")

if excluded:
    sys.exit(1)  # Non-zero for CI integration
```

### Test file structure (test_arbitration.py)

```python
# Source: follows existing test pattern from tests/test_session.py, tests/test_exchange.py
"""Unit tests for arbitration module (GUESS-03 coverage)."""
import pytest
from server.arbitration import arbitrate, ensure_nltk_corpora

# Ensure corpora available before tests
ensure_nltk_corpora()

THRESHOLD = 0.7

def test_exact_match():
    ok, word, typ = arbitrate('apple', 'apple', THRESHOLD)
    assert ok is True and typ == 'exact' and word == 'apple'

def test_exact_match_case_insensitive():
    ok, _, typ = arbitrate('APPLE', 'apple', THRESHOLD)
    assert ok is True and typ == 'exact'

def test_synonym_pt_guess_en_target():
    """Portuguese guess against English target word (current manifest format)."""
    ok, word, typ = arbitrate('maçã', 'apple', THRESHOLD)
    assert ok is True and typ == 'synonym' and word == 'apple'

def test_synonym_wrong_guess():
    ok, word, typ = arbitrate('cachorro', 'apple', THRESHOLD)
    assert ok is False and word is None

def test_fallback_when_no_synsets():
    """Unknown word triggers fallback path."""
    ok, word, typ = arbitrate('xyzzy', 'xyzzy', THRESHOLD)
    assert ok is True and typ == 'fallback'

def test_match_type_on_incorrect_guess():
    """D-06: match_type is set even on incorrect guesses."""
    ok, word, typ = arbitrate('cachorro', 'apple', THRESHOLD)
    assert ok is False and word is None and typ in ('exact', 'synonym', 'fallback')

def test_matched_word_is_target_not_guess():
    """D-05: matched_word returns the canonical target, not the guess."""
    ok, word, typ = arbitrate('maçã', 'apple', THRESHOLD)
    assert word == 'apple'  # canonical target
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `guess_clean.lower() == expected.strip().lower()` | `arbitrate()` with 3-tier decision | Phase 6 | Players can guess in Portuguese; synonyms accepted |
| No GUESS_RESULT enrichment | `matched_word` + `match_type` in broadcast | Phase 6 | Frontend can show "synonym matched" vs exact feedback (deferred display to Phase 8) |
| All manifest words in distribution pool | Only WordNet-covered words in pool | Phase 6 | Startup filters out words that arbitration cannot handle |

**Deprecated/outdated:**
- Single `is_correct = guess_clean.lower() == expected.strip().lower()` line at `game_server.py:560`: replaced entirely by `arbitrate()` call.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | NLTK 3.9.4 `wn.synsets(word, lang='por')` using omw-1.4 corpus is the API the project uses (per CLAUDE.md: "NLTK 3.9.x + `nltk.download('wordnet')` + `nltk.download('omw-1.4')`") | Standard Stack | Low — CLAUDE.md explicitly lists this; verified live |
| A2 | All 12 current manifest words (English) have WordNet EN synsets with PT lemma coverage | Critical Discovery section | Low — verified live via `has_coverage` check for all 12 |
| A3 | `validate_manifest.py` is reporting-only (does NOT modify manifest.json) | Planner discretion | Low — safer for development; planner can change |
| A4 | `arbitration.py` is a separate module (not inline in game_server.py) | Architecture section | Low — planner discretion per CONTEXT.md |
| A5 | Wu-Palmer false positives at 0.7 (banana ~ apple = 0.82) are acceptable per game design | Common Pitfalls | Low — threshold locked at D-01; behavior is documented |

---

## Open Questions (RESOLVED)

1. **Manifest language resolution (BLOCKING)**
   - What we know: manifest.json has English words; CONTEXT.md says Portuguese; arbitration works either way (verified).
   - What's unclear: Does the planner want to update manifest to Portuguese (Option A) or adapt arbitration to handle English targets (Option B)?
   - Recommendation: Option A (update manifest to Portuguese words). This aligns with D-02 "Portuguese only" intent and is a simple manifest.json update. The Portuguese-to-English image filename mapping is unchanged (`maçã → apple.jpg`).
   - **RESOLVED: Option A chosen in Plan 06-01 Task 1 — manifest.json values updated to Portuguese words (maçã, bicicleta, cadeira, etc.), image filenames (keys) unchanged.**

2. **validate_manifest exit code for CI**
   - What we know: CONTEXT.md doesn't specify; script should produce human-readable report.
   - What's unclear: Should the script exit non-zero when exclusions exist (CI-friendly) or always exit 0?
   - Recommendation: Exit non-zero on any exclusion (validates manifest integrity); log warnings regardless.
   - **RESOLVED: Plan 06-02 Task 2 uses `sys.exit(1)` when any word is excluded — CI-friendly.**

3. **violão vs guitarra coverage**
   - What we know: `violão` (Portuguese for guitar in Brazilian usage) → 1 PT synset `guitar.n.01`; `guitarra` → includes `electric_guitar.n.01` + `guitar.n.01`.
   - What's unclear: Which Portuguese word is most natural for the game context?
   - Recommendation: Use `violão` in manifest (more common Brazilian Portuguese term for acoustic guitar). Either works with the arbitration.
   - **RESOLVED: Plan 06-01 Task 1 uses `violão` in the Portuguese manifest mapping.**

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11.2 (venv) | arbitration.py, server startup | Yes | 3.11.2 | — |
| nltk | WordNet synset API | Yes (installed in session) | 3.9.4 | — |
| wordnet corpus | `wn.synsets()` | Yes (downloaded in session) | NLTK bundled | Re-download at startup via guard |
| omw-1.4 corpus | `lang='por'` lookups | Yes (downloaded in session) | NLTK bundled | Re-download at startup via guard |
| Pyro5 5.16 | RPC transport (unchanged) | Yes | 5.16 | — |
| Flask-SocketIO 5.6.1 | Bridge (unchanged) | Yes | 5.6.1 | — |

**Missing dependencies with no fallback:** None.

**Note:** NLTK and its corpora are not in `requirements.txt` yet. The venv install done during research confirms they install correctly under Python 3.11.2. Add `nltk==3.9.4` to `requirements.txt` as part of Wave 0.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pytest.ini present) |
| Config file | `/home/spacko/projects/faculdade/sd-rpc-av-1/pytest.ini` |
| Quick run command | `venv/bin/python -m pytest tests/test_arbitration.py -x -q` |
| Full suite command | `venv/bin/python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUESS-03a | Exact match (case-insensitive) accepted | unit | `pytest tests/test_arbitration.py::test_exact_match_case_insensitive -x` | No — Wave 0 |
| GUESS-03b | Wu-Palmer synonym accepted above threshold | unit | `pytest tests/test_arbitration.py::test_synonym_pt_guess_en_target -x` | No — Wave 0 |
| GUESS-03c | Fallback exact-match when WordNet returns None | unit | `pytest tests/test_arbitration.py::test_fallback_when_no_synsets -x` | No — Wave 0 |
| D-05 | matched_word and match_type in GUESS_RESULT | integration | `pytest tests/test_arbitration.py::test_matched_word_is_target_not_guess -x` | No — Wave 0 |
| D-06 | match_type set on incorrect guesses | unit | `pytest tests/test_arbitration.py::test_match_type_on_incorrect_guess -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `venv/bin/python -m pytest tests/test_arbitration.py -x -q`
- **Per wave merge:** `venv/bin/python -m pytest tests/ -q`
- **Phase gate:** Full suite green (currently 53/53 passing) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_arbitration.py` — covers GUESS-03a, 03b, 03c, D-05, D-06
- [ ] `nltk==3.9.4` in `requirements.txt`

---

## Security Domain

Security enforcement is not explicitly disabled in `config.json`. The following ASVS categories apply:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | `guess_clean = str(guess_word).strip()[:50]` already in `submit_guess()` — unchanged; arbitration receives pre-cleaned input |
| V2 Authentication | No | No new auth surface |
| V3 Session Management | No | No session changes |
| V4 Access Control | No | No new access control surface |
| V6 Cryptography | No | No crypto |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed Unicode in guess input causing WordNet crash | Tampering | Input already stripped/limited to 50 chars; NLTK handles unicode gracefully (verified with `maçã`) |
| NLTK corpus download from untrusted source | Tampering | NLTK downloads from `nltk.org` over HTTPS; no user-controlled download path |
| Arbitrary word injection to exhaust synset computation | DoS | Max 50 chars per guess (existing guard); cross-product bounded: max ~15 synsets × 15 synsets = 225 comparisons per guess — negligible |

---

## Sources

### Primary (HIGH confidence)
- Live NLTK tests in project venv (Python 3.11.2, NLTK 3.9.4, wordnet + omw-1.4) — 2026-05-15 — all `wn.synsets()`, `wup_similarity()`, and guard pattern calls [VERIFIED: live test]
- `server/game_server.py:537-572` — existing `submit_guess()` implementation read directly [VERIFIED: codebase]
- `server/images/manifest.json` — existing manifest content read directly [VERIFIED: codebase]
- `config.py` — existing constant patterns [VERIFIED: codebase]
- `.planning/phases/06-synonym-arbitration/06-CONTEXT.md` — locked decisions D-01 through D-06 [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- NLTK WordNet HOWTO — `https://www.nltk.org/howto/wordnet.html` — `wup_similarity()` API and `lang=` parameter [CITED]
- omw-1.4 Portuguese coverage — language code `'por'` confirmed via live lookup [VERIFIED: live test]

### Tertiary (LOW confidence)
- Wu-Palmer theoretical properties (semantic similarity for taxonomy-based matching) — training knowledge [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — NLTK version and corpus names verified live in project venv
- Architecture: HIGH — exact API calls verified; manifest mismatch identified and workarounds confirmed
- Pitfalls: HIGH — all pitfalls confirmed via live tests (`.zip` guard, cross-language lookup, false positives)

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (NLTK API is stable; omw-1.4 does not update frequently)

---

## Project Constraints (from CLAUDE.md)

The following directives from `CLAUDE.md` apply to this phase and must be honored:

| Directive | Impact on Phase 6 |
|-----------|-------------------|
| Pyro5 broadcast methods must be `@oneway` | No new broadcast methods; existing `guess_result` broadcast path unchanged |
| Pyro5 proxies per-thread via `threading.local()` | No new Pyro5 proxy usage in this phase |
| Images served as Flask static URLs, never via Pyro5 | Not relevant to arbitration |
| `async_mode='threading'` in Flask-SocketIO | No change to bridge |
| NLTK 3.9.x + `nltk.download('wordnet')` + `nltk.download('omw-1.4')` | Confirmed: NLTK 3.9.4 installed, both corpora downloadable |
| No database, no Redis | Not relevant |
| No React/build pipeline | No frontend changes in this phase |
| Return dicts `{"ok": True, ...}` or `{"error": "reason"}` from `@expose` methods | `submit_guess()` return format unchanged; arbitration result embedded in broadcast, not return |
| GSD workflow before file changes | Confirmed: operating within GSD research phase |
