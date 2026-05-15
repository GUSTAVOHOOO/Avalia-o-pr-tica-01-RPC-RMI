---
phase: 6
slug: synonym-arbitration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-15
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` |
| **Quick run command** | `venv/bin/python -m pytest tests/test_arbitration.py -x -q` |
| **Full suite command** | `venv/bin/python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `venv/bin/python -m pytest tests/test_arbitration.py -x -q`
- **After every plan wave:** Run `venv/bin/python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | GUESS-03 | — | N/A | unit | `pytest tests/test_arbitration.py -x -q` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | GUESS-03a | — | N/A | unit | `pytest tests/test_arbitration.py::test_exact_match_case_insensitive -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | GUESS-03b | — | N/A | unit | `pytest tests/test_arbitration.py::test_synonym_pt_guess_en_target -x` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 1 | GUESS-03c | — | N/A | unit | `pytest tests/test_arbitration.py::test_fallback_when_no_synsets -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 1 | D-05 | — | N/A | integration | `pytest tests/test_arbitration.py::test_matched_word_is_target_not_guess -x` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 1 | D-06 | — | N/A | unit | `pytest tests/test_arbitration.py::test_match_type_on_incorrect_guess -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_arbitration.py` — stubs for GUESS-03a, 03b, 03c, D-05, D-06
- [ ] `nltk==3.9.4` added to `requirements.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Server startup excludes words with zero Portuguese synsets | D-03, D-04 | Requires running full server with manifest | Start server, observe logs for `WARNING: '<word>' has no Portuguese synsets` |
| validate_manifest.py report output | D-04 | CLI script | Run `python validate_manifest.py`, verify excluded words listed with reason |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
