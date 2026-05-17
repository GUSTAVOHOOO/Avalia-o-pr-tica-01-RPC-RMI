---
phase: 7
slug: reconnection-end-of-game
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-15
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 0 | INFRA-07 | — | N/A | unit | `pytest tests/test_event_broadcaster.py -x -q` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | INFRA-07 | — | Failure counter resets on success | unit | `pytest tests/test_event_broadcaster.py -x -q` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | INFRA-08 | — | N/A | unit | `pytest tests/test_reconnect.py -x -q` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | SESSION-07 | — | N/A | integration | manual smoke test | ✅ | ⬜ pending |
| 07-02-01 | 02 | 2 | POSTGAME-01 | — | N/A | unit | `pytest tests/test_postgame.py -x -q` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 2 | POSTGAME-02 | — | N/A | unit | `pytest tests/test_postgame.py -x -q` | ❌ W0 | ⬜ pending |
| 07-02-03 | 02 | 2 | POSTGAME-03 | — | Vote timer fires at 30s | unit | `pytest tests/test_postgame.py -x -q` | ❌ W0 | ⬜ pending |
| 07-02-04 | 02 | 2 | POSTGAME-04 | — | Majority → restart; no majority → end | unit | `pytest tests/test_postgame.py -x -q` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | CHAT-01 | — | N/A | unit | `pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 07-03-02 | 03 | 2 | CHAT-02 | — | N/A | unit | `pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 07-03-03 | 03 | 3 | CHAT-03 | — | Chat not confusable with hint/guess | manual | Browser visual check | N/A | ⬜ pending |
| 07-03-04 | 03 | 3 | CHAT-04 | — | Distinct labels + submit buttons | manual | Browser visual check | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_event_broadcaster.py` — stubs for INFRA-07 (failure counter, PLAYER_LEFT broadcast)
- [ ] `tests/test_reconnect.py` — stubs for INFRA-08 (grace period, reconnect_player RPC)
- [ ] `tests/test_postgame.py` — stubs for POSTGAME-01 to 04 (podium, vote, restart/end)
- [ ] `tests/test_chat.py` — stubs for CHAT-01 to 02 (send_chat, on_chat_message callback)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chat input visually distinct from hint/guess | CHAT-03/04 | Requires browser visual inspection | Open game screen, confirm chat panel is separate color/label from hint/guess inputs |
| Reconnect flow restores game state in browser | INFRA-08 | Requires multi-tab E2E interaction | Open game in tab A, reload tab A mid-game, confirm state restored without new join |
| Play-again vote timer counts down visibly | POSTGAME-03 | Timer animation requires browser | After game ends, confirm 30s countdown bar is visible to all players |
| SESSION-07 host transfer on lobby disconnect | SESSION-07 | Multi-player interaction | Player A (host) closes browser in lobby; Player B is promoted and can start game |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
