# Phase 6: Synonym Arbitration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 6-synonym-arbitration
**Areas discussed:** Wu-Palmer threshold, Language strategy, Startup validation policy, matched_word payload

---

## Wu-Palmer Threshold

| Option | Description | Selected |
|--------|-------------|----------|
| 0.8 (strict) | Only very close synonyms; lower false-positive rate | |
| 0.7 (balanced) | Catches clear synonyms and near-equivalents; recommended starting point | ✓ |
| 0.6 (permissive) | Broader matching; useful if Portuguese WordNet coverage is sparse | |

**User's choice:** 0.7 (balanced)

**Follow-up — Expose in config.py?**

| Option | Description | Selected |
|--------|-------------|----------|
| WU_PALMER_THRESHOLD in config.py | Consistent with other tunables; no code change to tune | ✓ |
| Hardcode 0.7 in arbitration module | Simpler but requires code change to tune | |

**User's choice:** Yes — store in config.py

**Notes:** No special rationale given; 0.7 is the standard recommendation for WordNet similarity in quiz/game contexts.

---

## Language Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Portuguese only (lang='por') | Uses omw-1.4; matches game language; falls back to exact-match if no synsets | ✓ |
| English + Portuguese | Try English first (better coverage), then Portuguese | |
| Both simultaneously (union) | Broader coverage, more permissive | |

**User's choice:** Portuguese only (lang='por')

**Follow-up — Object name language in manifest.json?**

| Option | Description | Selected |
|--------|-------------|----------|
| Portuguese (maçã, bicicleta, carro…) | Consistent with lang='por' | ✓ |
| English (apple, bicycle, car…) | Would cause lang='por' to find no synsets for canonical words | |
| Mixed | Startup validation becomes critical | |

**User's choice:** Portuguese

**Notes:** Object names are Portuguese, so Portuguese-only lookup is coherent. No need for English fallback.

---

## Startup Validation Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude from distribution | Word removed from assignment pool; server starts normally | ✓ |
| Keep but flag as exact-match-only | Word stays in pool; risks players never winning via synonym | |
| Crash/refuse to start | Hard failure forces manifest fix before deploy | |

**User's choice:** Exclude from distribution (as specified in ROADMAP success criterion 1)

**Follow-up — Where does validation run?**

| Option | Description | Selected |
|--------|-------------|----------|
| GameServer.__init__() only, warn but always start | Minimal; single location | |
| Separate validate_manifest.py + GameServer.__init__() | Defense in depth; standalone script for CI | ✓ |
| Leave placement to planner | Document requirement only | |

**User's choice:** Separate validate_manifest.py + GameServer.__init__()

**Notes:** Matches ROADMAP's mention of "a validation script runs against the full image word list."

---

## matched_word Payload

| Option | Description | Selected |
|--------|-------------|----------|
| The guess word itself | Simplest; frontend already has it | |
| The canonical object word (the answer) | Reveals correct answer on correct guess; useful for display | ✓ |
| null for exact, synonym for WordNet match | Differentiates how match was scored | |

**User's choice:** The canonical object word (the answer)

**Follow-up — Add match_type field?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — match_type: 'exact' \| 'synonym' \| 'fallback' | Low cost now; enables Phase 8 UI differentiation | ✓ |
| No — is_correct: bool is enough | Simpler payload | |

**User's choice:** Yes — add match_type

**Notes:** Phase 8 UI can show "~sinônimo!" vs "exato!" based on match_type without additional server calls.

---

## Claude's Discretion

- Arbitration logic placement: `server/arbitration.py` vs inline in `game_server.py`
- Whether Wu-Palmer is computed over cross-product of all synset pairs (max) or first synset of each word
- Whether `validate_manifest.py` updates manifest in place or reports only

## Deferred Ideas

- English-language fallback synset lookup — not needed since manifest uses Portuguese words
- Configurable per-word threshold overrides — deferred to v2
- UI display of match_type ("~sinônimo!" vs "exato!") — deferred to Phase 8
