---
phase: 1
slug: rpc-infrastructure-callback-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-12
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.2.1 (python3.11 env) |
| **Config file** | `pytest.ini` — Wave 0 creates |
| **Quick run command** | `venv/bin/pytest tests/ -x -q` |
| **Full suite command** | `venv/bin/pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `venv/bin/pytest tests/ -x -q`
- **After every plan wave:** Run `venv/bin/pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| venv-setup | 01 | 0 | INFRA-01..06 | — | N/A | smoke | `venv/bin/python -c "import Pyro5; import flask_socketio"` | ❌ W0 | ⬜ pending |
| ping-rpc | 01 | 1 | INFRA-01 | — | N/A | unit | `venv/bin/pytest tests/test_unit.py::test_ping -x` | ❌ W0 | ⬜ pending |
| register-callback | 01 | 1 | INFRA-02 | — | N/A | unit | `venv/bin/pytest tests/test_unit.py::test_register_callback -x` | ❌ W0 | ⬜ pending |
| broadcast-delivery | 01 | 1 | INFRA-03 | — | N/A | unit | `venv/bin/pytest tests/test_unit.py::test_broadcast_delivery -x` | ❌ W0 | ⬜ pending |
| per-thread-proxy | 01 | 1 | INFRA-05 | — | N/A | unit | `venv/bin/pytest tests/test_unit.py::test_per_thread_proxy -x` | ❌ W0 | ⬜ pending |
| bridge-start | 01 | 2 | INFRA-04 | — | `async_mode='threading'` in log | smoke/manual | 3-terminal startup; log check | ❌ W0 | ⬜ pending |
| ns-discovery | 01 | 2 | INFRA-06 | — | N/A | smoke/manual | `venv/bin/python client/test_client.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `venv/` — created from `python3.11 -m venv venv`
- [ ] `venv/bin/pip install Pyro5==5.16 Flask flask-socketio==5.6.1 simple-websocket pytest`
- [ ] `requirements.txt` — pinned versions
- [ ] `pytest.ini` — `testpaths = tests`, `python_files = test_*.py`
- [ ] `tests/__init__.py` — package init
- [ ] `tests/test_unit.py` — stubs for INFRA-01, INFRA-02, INFRA-03, INFRA-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bridge starts with `async_mode='threading'` confirmed in startup log | INFRA-04 | Requires 3 running processes; not easily automated in pytest | Start NS + GameServer + Bridge; check bridge stdout for `async_mode=threading` |
| Server-pushed callback arrives at CLI client without client requesting it | INFRA-03 (3-terminal) | Requires 3 OS processes and manual observation | Run 3-terminal smoke test: NS + GameServer + `test_client.py`; observe `[PUSH RECEIVED]` in client output |
| test_client.py discovers game.server via NS (no hardcoded URI) | INFRA-06 | End-to-end cross-process; not feasible in unit test | Run `venv/bin/python client/test_client.py`; verify no hardcoded URIs in source |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
