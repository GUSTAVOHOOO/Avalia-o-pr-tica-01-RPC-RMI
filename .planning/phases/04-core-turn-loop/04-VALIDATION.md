---
phase: 4
slug: core-turn-loop
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, pytest.ini at root) |
| **Config file** | `pytest.ini` (`testpaths = tests`) |
| **Quick run command** | `python -m pytest tests/test_turn_state.py tests/test_scoring.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_turn_state.py tests/test_scoring.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-W0-turn-state | W0 | 0 | HINT-01..04, GUESS-01/02/04/05, IMAGE-01/02, SCORE-04/05 | — | N/A | unit | `pytest tests/test_turn_state.py -x` | ❌ W0 | ⬜ pending |
| 04-W0-scoring | W0 | 0 | SCORE-01, SCORE-02, SCORE-03 | — | N/A | unit | `pytest tests/test_scoring.py -x` | ❌ W0 | ⬜ pending |
| 04-submit-hint | — | 1 | HINT-01 | T-4-01 | player_id from sid, not client payload | unit | `pytest tests/test_turn_state.py::test_submit_hint tests/test_turn_state.py::test_submit_hint_duplicate -x` | ❌ W0 | ⬜ pending |
| 04-hint-received-payload | — | 1 | HINT-02 | — | No hint word in broadcast | unit | `pytest tests/test_turn_state.py::test_hint_received_payload -x` | ❌ W0 | ⬜ pending |
| 04-hint-empty-timer | — | 1 | HINT-03 | — | N/A | unit | `pytest tests/test_turn_state.py::test_hint_empty_on_timer -x` | ❌ W0 | ⬜ pending |
| 04-hint-auto-advance | — | 1 | HINT-04 | — | N/A | unit | `pytest tests/test_turn_state.py::test_all_hints_auto_advance -x` | ❌ W0 | ⬜ pending |
| 04-submit-guess | — | 1 | GUESS-01 | T-4-02 | guess_word stripped/capped ≤50 chars | unit | `pytest tests/test_turn_state.py::test_submit_guess_correct -x` | ❌ W0 | ⬜ pending |
| 04-skip-guess | — | 1 | GUESS-02 | — | N/A | unit | `pytest tests/test_turn_state.py::test_skip_guess -x` | ❌ W0 | ⬜ pending |
| 04-guess-result-broadcast | — | 1 | GUESS-04 | — | N/A | unit | `pytest tests/test_turn_state.py::test_guess_result_broadcast -x` | ❌ W0 | ⬜ pending |
| 04-one-guess-per-turn | — | 1 | GUESS-05 | T-4-03 | Reject self-target | unit | `pytest tests/test_turn_state.py::test_guess_one_per_turn -x` | ❌ W0 | ⬜ pending |
| 04-tiered-scoring | — | 2 | SCORE-01 | — | N/A | unit | `pytest tests/test_scoring.py::test_tiered_guessers -x` | ❌ W0 | ⬜ pending |
| 04-solo-bonus | — | 2 | SCORE-02 | — | N/A | unit | `pytest tests/test_scoring.py::test_solo_bonus -x` | ❌ W0 | ⬜ pending |
| 04-owner-scoring | — | 2 | SCORE-03 | — | N/A | unit | `pytest tests/test_scoring.py::test_owner_scoring -x` | ❌ W0 | ⬜ pending |
| 04-score-updated-payload | — | 2 | SCORE-04 | — | N/A | unit | `pytest tests/test_scoring.py::test_score_updated_payload -x` | ❌ W0 | ⬜ pending |
| 04-get-scores | — | 2 | SCORE-05 | — | N/A | unit | `pytest tests/test_turn_state.py::test_get_scores -x` | ❌ W0 | ⬜ pending |
| 04-image-manifest-load | — | 1 | IMAGE-01 | — | N/A | unit | `pytest tests/test_turn_state.py::test_image_manifest_load -x` | ❌ W0 | ⬜ pending |
| 04-object-assigned-payload | — | 1 | IMAGE-02 | — | N/A | unit | `pytest tests/test_turn_state.py::test_object_assigned_payload -x` | ❌ W0 | ⬜ pending |
| 04-flask-static-route | — | 1 | IMAGE-03 | T-4-04 | send_from_directory prevents path traversal | smoke | manual 4-terminal test | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_turn_state.py` — stubs for HINT-01..04, GUESS-01/02/04/05, IMAGE-01/02, SCORE-04/05
- [ ] `tests/test_scoring.py` — stubs for SCORE-01, SCORE-02, SCORE-03 (pure function, no Pyro5 needed)
- [ ] `server/images/` — directory with ≥8 sample images and `manifest.json`

*(Existing `tests/test_turn_machine.py` and `tests/test_session.py` cover Phases 1–3 and remain unchanged.)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/static/images/<file>` returns 200 | IMAGE-03 | Requires running Flask server | Start 4-terminal setup; open browser to Flask static URL; verify image loads |
| Two consecutive turns produce correct cumulative scores, no race conditions | SCORE-05 | Requires 2 connected browser sessions running full turn cycle | Run smoke test with 2 browser tabs; complete 2 full turns; verify scores in UI |

---

## Threat Model

| ID | Pattern | STRIDE | Mitigation |
|----|---------|--------|------------|
| T-4-01 | Player submitting hint for another player's slot | Spoofing | `player_id` resolved from `_sid_to_player[request.sid]` in bridge — never trusted from client payload |
| T-4-02 | Hint/guess word injection (long string, special chars) | Tampering | `hint_word.strip()[:50]`, `guess_word.strip()[:50]`; compare lowercased |
| T-4-03 | Player guessing their own object | Tampering | `submit_guess()` rejects self-targeting (D-10 in CONTEXT.md) |
| T-4-04 | Image path traversal via manifest filename | Tampering | `send_from_directory` built-in protection; filenames are server-controlled, not client-supplied |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
