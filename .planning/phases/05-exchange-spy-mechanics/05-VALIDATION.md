---
phase: 5
slug: exchange-spy-mechanics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | pytest.ini (project root) |
| **Quick run command** | `python -m pytest tests/test_exchange.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_exchange.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | EXCHANGE-01 through SPY-05, D-06 | — | N/A (test stubs) | unit | `python -m pytest tests/test_exchange.py -x -q` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | EXCHANGE-01 | T-5-access | Phase guard blocks wrong-phase calls | unit | `python -m pytest tests/test_exchange.py::test_request_exchange tests/test_exchange.py::test_request_exchange_wrong_phase -x` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 1 | EXCHANGE-02 | T-5-access | Status guard blocks double-response | unit | `python -m pytest tests/test_exchange.py::test_respond_exchange_accept tests/test_exchange.py::test_respond_exchange_reject -x` | ❌ W0 | ⬜ pending |
| 5-02-03 | 02 | 1 | EXCHANGE-03 | T-5-tamper | `record.status != "accepted"` guard | unit | `python -m pytest tests/test_exchange.py::test_submit_exchange_hint_completes -x` | ❌ W0 | ⬜ pending |
| 5-02-04 | 02 | 1 | EXCHANGE-04, EXCHANGE-05 | — | Broadcast contains no hint content | unit | `python -m pytest tests/test_exchange.py::test_exchange_completed_payload tests/test_exchange.py::test_private_hints_delivered -x` | ❌ W0 | ⬜ pending |
| 5-02-05 | 02 | 1 | EXCHANGE-06 | — | One exchange per player per turn enforced | unit | `python -m pytest tests/test_exchange.py::test_exchange_one_per_turn -x` | ❌ W0 | ⬜ pending |
| 5-02-06 | 02 | 1 | D-06 | — | SPY_PHASE skipped when no completed exchanges | unit | `python -m pytest tests/test_exchange.py::test_spy_phase_skipped_when_no_exchanges tests/test_exchange.py::test_spy_phase_entered_when_exchange_exists -x` | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 2 | SPY-01 | T-5-access | Phase guard blocks spy in wrong phase | unit | `python -m pytest tests/test_exchange.py::test_spy_wrong_phase -x` | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 2 | SPY-02 | T-5-elevate | ~30% discovery rate over 100 calls | unit (statistical) | `python -m pytest tests/test_exchange.py::test_spy_discovery_probability -x` | ❌ W0 | ⬜ pending |
| 5-03-03 | 03 | 2 | SPY-03 | — | Silent success: no public broadcast | unit | `python -m pytest tests/test_exchange.py::test_spy_success_private -x` | ❌ W0 | ⬜ pending |
| 5-03-04 | 03 | 2 | SPY-04, SPY-05 | T-5-access | Self-spy and double-spy rejected | unit | `python -m pytest tests/test_exchange.py::test_spy_own_exchange_rejected tests/test_exchange.py::test_spy_one_per_turn -x` | ❌ W0 | ⬜ pending |
| 5-04-01 | 04 | 3 | All | — | 4-terminal smoke test: full exchange + spy flow | manual | 4-terminal smoke test (see Manual-Only below) | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_exchange.py` — 15 test stubs covering EXCHANGE-01 through SPY-05 + D-06 (use `pytest.skip` pattern from prior phases)
- [ ] `FakeBroadcaster` — import from `tests/test_turn_state.py` or duplicate inline (no new conftest needed)

*Existing `pytest.ini` and venv cover all infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full exchange + spy lifecycle with 2 real browsers | EXCHANGE-01 through SPY-05 | Requires real Socket.IO connections; bridge targeted delivery and SID routing cannot be unit-tested | Start 4 terminals (NS, GameServer, Bridge, test_client); open 2 browser tabs; complete exchange flow; attempt spy; verify public/private event routing in browser console |
| SPY_PHASE auto-skip visible in browser | D-06 | Requires full game cycle reaching EXCHANGE_PHASE with no exchange initiated | Play a full turn without initiating any exchange; verify `PHASE_CHANGED` skips directly to SCORING_PHASE in browser DevTools |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
