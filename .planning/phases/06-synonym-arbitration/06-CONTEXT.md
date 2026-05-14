# Phase 6: Synonym Arbitration - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the case-insensitive exact-match arbitration in `submit_guess()` (currently at `server/game_server.py:562`) with Portuguese WordNet synonym matching using NLTK `wn` + omw-1.4. A correct guess now also accepts synonyms and near-matches above a Wu-Palmer similarity threshold. Exact-match remains as permanent fallback when WordNet returns None. A standalone `validate_manifest.py` script and a `GameServer.__init__()` check exclude image words with zero Portuguese synsets from distribution at server startup. No new frontend action panels — the enriched `GUESS_RESULT` payload (`matched_word`, `match_type`) is the only client-visible change.

Requirements in scope: GUESS-03

</domain>

<decisions>
## Implementation Decisions

### Wu-Palmer Threshold
- **D-01:** Default similarity threshold is **0.7**. Stored as `WU_PALMER_THRESHOLD = 0.7` in `config.py` (consistent with how other tunables like spy probability are stored). Arbitration code reads `config.WU_PALMER_THRESHOLD` — no hardcoded value in the arbitration module itself.

### Language Strategy
- **D-02:** Use **Portuguese only** (`lang='por'`) for synset lookup via omw-1.4. All object names in `manifest.json` are Portuguese words (e.g., `maçã`, `bicicleta`, `carro`). If a Portuguese synset lookup returns None for either word, the system falls back to exact-match (GUESS-03c).

### Startup Validation Policy
- **D-03:** Words with zero Portuguese synsets are **excluded from distribution** — removed from the pool that gets assigned to players at `ROUND_START`. Server starts normally regardless (no hard failure). Excluded words are logged as warnings.
- **D-04:** Validation runs in two places for defense in depth:
  1. **`validate_manifest.py`** — standalone script for pre-deploy / CI checking, producing a human-readable report of which words are excluded and why.
  2. **`GameServer.__init__()`** — re-runs validation at server startup so the live word pool is always self-consistent even if the script wasn't run separately.

### GUESS_RESULT Payload
- **D-05:** `GUESS_RESULT` payload adds two new fields:
  - `matched_word: str | null` — the **canonical object word** (the correct answer) when the guess is correct; `null` when incorrect.
  - `match_type: 'exact' | 'synonym' | 'fallback'` — how the match was scored. `'exact'` for case-insensitive string match, `'synonym'` for WordNet Wu-Palmer match, `'fallback'` for exact-match used because WordNet returned None.
- **D-06:** On incorrect guesses: `matched_word: null`, `match_type` still set to whichever method was attempted (so the UI can show appropriate feedback).

### Claude's Discretion
- Exact location of the arbitration logic: new `server/arbitration.py` module vs inline in `game_server.py` — leave to planner (a separate module is cleaner but either is valid at this scale).
- Whether Wu-Palmer similarity is computed as `synset_a.wup_similarity(synset_b)` over the cross-product of all synset pairs (taking the max) or only the first synset of each word — leave to planner, but max over all pairs is more correct.
- Whether `validate_manifest.py` updates `manifest.json` in place (removing excluded words) or only reports — leave to planner; reporting-only is safer for development.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §GUESS-03 — Full arbitration spec: (a) exact equality, (b) Wu-Palmer via NLTK `wn` + omw-pt with configurable threshold, (c) fallback exact-match when WordNet returns None
- `.planning/ROADMAP.md` §Phase 6 — 3 success criteria that must all be TRUE for phase completion (startup validation, synonym match returns correct result + matched_word, WordNet-None fallback)

### Architecture
- `.planning/PROJECT.md` §Key Decisions — locked decisions (RLock, per-thread proxies, broadcast pattern)
- `CLAUDE.md` §Synonym Arbitration — NLTK 3.9.x, wordnet corpus, omw-1.4 corpus; install: `nltk.download('wordnet')`, `nltk.download('omw-1.4')`

### Prior Phase Decisions
- `.planning/phases/04-core-turn-loop/04-CONTEXT.md` — D-12 (manifest.json structure: `{filename: object_name}`), D-13 (`image_assignments: dict[player_id → object_name]` is the canonical answer for arbitration), D-10 (phase 4 used exact-match; phase 6 replaces it)
- `.planning/phases/05-exchange-spy-mechanics/05-CONTEXT.md` — for broadcast pattern reference (broadcast outside lock)

### Technology
- `CLAUDE.md` §Key Pyro5 Patterns — patterns 1–4

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/game_server.py:537–572` — `submit_guess()` method; Phase 6 replaces the single exact-match line (`is_correct = guess_clean.lower() == expected.strip().lower()`) with a call to the arbitration function. Also needs to populate `matched_word` and `match_type` in `broadcast_data`.
- `server/images/manifest.json` — `{filename: object_name}` map; validation script reads this to build the valid word pool.
- `config.py` — add `WU_PALMER_THRESHOLD = 0.7`; planner should follow the existing constant pattern in this file.

### Established Patterns
- Broadcast outside the lock — all `broadcaster.broadcast()` calls happen after `with self.lock:` exits. Phase 6 does not change this.
- Return dicts from `@Pyro5.api.expose` methods: `{"ok": True, ...}` on success, `{"error": "reason"}` on failure.
- NLTK corpora downloaded once at server startup (or in a setup script); not downloaded per-request.

### Integration Points
- `server/game_server.py`: Replace the exact-match line in `submit_guess()` with an arbitration call; add `matched_word` and `match_type` to `broadcast_data`.
- New `server/arbitration.py` (or inline): `arbitrate(guess: str, target: str, threshold: float) -> tuple[bool, str | None, str]` returning `(is_correct, matched_word, match_type)`.
- New `validate_manifest.py` (project root or `server/`): loads manifest, runs synset lookup for each `object_name` with `lang='por'`, logs and returns excluded words.
- `GameServer.__init__()`: call validation, build `self._valid_words: set[str]` (or filtered manifest dict) for use in image assignment.

</code_context>

<specifics>
## Specific Ideas

- Arbitration function signature: `arbitrate(guess: str, target: str, threshold: float) -> tuple[bool, str | None, str]` — returns `(is_correct, matched_word_or_None, match_type)`.
- `match_type` values: `'exact'` when `guess.lower() == target.lower()`, `'synonym'` when Wu-Palmer ≥ threshold, `'fallback'` when WordNet returned None and exact-match was used as fallback.
- `matched_word` when correct: the canonical object word (value from `image_assignments[target_player_id]`), not the guess word.
- Startup log format for excluded words: `WARNING: 'palavra' has no Portuguese synsets in omw-1.4 — excluded from distribution`.
- NLTK download guard: check `nltk.data.find('corpora/wordnet')` and `nltk.data.find('corpora/omw-1.4')` before `nltk.download()`; avoids re-downloading on every server start.

</specifics>

<deferred>
## Deferred Ideas

- English-language fallback synset lookup (`lang='eng'`) — deferred; manifest.json uses Portuguese words, so Portuguese-only is sufficient.
- Configurable discovery probability or per-word threshold overrides — deferred to v2.
- UI display of match_type feedback ("~sinônimo!" vs "exato!") — deferred to Phase 8 (UI polish).

</deferred>

---

*Phase: 6-synonym-arbitration*
*Context gathered: 2026-05-14*
