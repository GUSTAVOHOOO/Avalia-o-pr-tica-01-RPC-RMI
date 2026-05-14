---
phase: 3
slug: phase-machine-timer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` (Wave 0 installs if missing) |
| **Quick run command** | `python -m pytest tests/test_turn_machine.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_turn_machine.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TURN-01 | — | Phase transitions are deterministic and ordered | unit | `python -m pytest tests/test_turn_machine.py::test_phase_cycle -xq` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | TURN-02 | — | Timer fires advance after TTL; generation counter prevents double-advance | unit | `python -m pytest tests/test_turn_machine.py::test_timer_auto_advance -xq` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | TURN-03 | — | Manual advance cancels current timer; stale timer is a no-op | unit | `python -m pytest tests/test_turn_machine.py::test_manual_advance_cancels_timer -xq` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | TURN-04 | — | Concurrent timer callbacks do not double-advance | unit | `python -m pytest tests/test_turn_machine.py::test_generation_counter -xq` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | TURN-01 | — | on_phase_changed and on_game_ended present in BridgeCallbackReceiver with correct decorators | structural (AST) | `python -c "import ast, pathlib; src=pathlib.Path('bridge/bridge.py').read_text(); tree=ast.parse(src); methods=[n.name for node in ast.walk(tree) if isinstance(node,ast.ClassDef) and node.name=='BridgeCallbackReceiver' for n in ast.walk(node) if isinstance(n,ast.FunctionDef)]; assert 'on_phase_changed' in methods and 'on_game_ended' in methods, f'missing: {methods}'; print('OK')"` | ✅ in-plan | ⬜ pending |
| 03-03-01 | 03 | 3 | TURN-01 | — | Frontend PhaseBadge renders phase name from PHASE_CHANGED event | manual | See manual verifications below | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Note on 03-02-01:** The broadcast integration behaviour (PHASE_CHANGED payload shape, routing to room) is covered by the Plan 03-03 end-to-end smoke test checkpoint. The structural AST check above is the automated gate for this layer; no separate `tests/test_broadcast.py` is required.

---

## Wave 0 Requirements

- [ ] `tests/test_turn_machine.py` — stubs for TURN-01, TURN-02, TURN-03, TURN-04
- [ ] `tests/conftest.py` — shared fixtures (mock EventBroadcaster)
- [ ] `pytest` — install if not present: `pip install pytest`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full ROUND_START→TURN_END cycle completes in two browser sessions | TURN-01 | Requires two live browser connections | Open two tabs, start game, observe all phase transitions broadcast and timer countdowns update |
| No deadlock or silent freeze during full cycle | TURN-01 | Deadlock is not detectable by unit tests | Run full cycle with debug logging; confirm all 7 phase transitions logged within expected time |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
