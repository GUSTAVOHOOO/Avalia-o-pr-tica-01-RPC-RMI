---
phase: 02
slug: player-session-lobby
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-12
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pytest.ini` (existing: `testpaths = tests`) |
| **Quick run command** | `venv/bin/python -m pytest tests/test_session.py -x -q` |
| **Full suite command** | `venv/bin/python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `venv/bin/python -m pytest tests/test_session.py -x -q`
- **After every plan wave:** Run `venv/bin/python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-*-create | TBD | 1 | SESSION-01 | — | `create_game()` returns `{player_id, room_code, is_host=True}` | unit | `venv/bin/python -m pytest tests/test_session.py::test_create_game -x` | ❌ W0 | ⬜ pending |
| 02-*-room-code | TBD | 1 | SESSION-02 | — | Room code is 6 uppercase alphanumeric; unique per call | unit | `venv/bin/python -m pytest tests/test_session.py::test_room_code_format -x` | ❌ W0 | ⬜ pending |
| 02-*-join | TBD | 1 | SESSION-03 | — | `join_game()` returns `{player_id, room_code, is_host=False}` for valid room | unit | `venv/bin/python -m pytest tests/test_session.py::test_join_game -x` | ❌ W0 | ⬜ pending |
| 02-*-join-reject | TBD | 1 | SESSION-04 | EoP | `join_game()` returns `{"error": "jogo em andamento"}` when status != WAITING | unit | `venv/bin/python -m pytest tests/test_session.py::test_join_rejected_if_started -x` | ❌ W0 | ⬜ pending |
| 02-*-broadcast | TBD | 1 | SESSION-05 | — | `join_game()` triggers `PLAYER_JOINED` broadcast to registered callback | unit | `venv/bin/python -m pytest tests/test_session.py::test_player_joined_broadcast -x` | ❌ W0 | ⬜ pending |
| 02-*-start | TBD | 1 | SESSION-06 | EoP | `start_game()` returns True iff caller is host and ≥2 players | unit | `venv/bin/python -m pytest tests/test_session.py::test_start_game_validation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_session.py` — stubs for SESSION-01 through SESSION-06 (6 tests)
- [ ] No new `conftest.py` needed — existing `tests/__init__.py` is sufficient

*Existing pytest infrastructure from Phase 1 covers all remaining infrastructure needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-time lobby update in two browser windows | SESSION-05 | Requires live Socket.IO + two browser sessions | Open `http://localhost:3000`, create game in Window A, join with room code in Window B, verify both lobbies show both players without refresh |
| Host-only "Iniciar Jogo" visibility | SESSION-06 | Requires visual inspection of React UI | Log in as non-host; confirm button is absent or disabled; log in as host with ≥2 players; confirm button is visible and enabled |
| Vite dev proxy WebSocket upgrade | SESSION-05 | Requires live dev server with both processes | Start Flask on 5000 + Vite on 3000; confirm `/socket.io` connections upgrade to `ws://` (check Network tab — should show 101 Switching Protocols) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
