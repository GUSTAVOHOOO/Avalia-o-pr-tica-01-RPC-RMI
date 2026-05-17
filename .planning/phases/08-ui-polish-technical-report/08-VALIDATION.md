---
phase: 8
slug: ui-polish-technical-report
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-16
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) — no frontend test framework configured |
| **Config file** | `pytest.ini` (project root) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green + PDF build must succeed
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 08-01-01 | 01 | 1 | REPORT-01–04 | PDF builds from Makefile without errors | build smoke | `make -C docs pdf && test -f docs/relatorio.pdf` | ⬜ pending |
| 08-02-xx | 02 | 1 | UI-05 | Timer color changes do not cause JS errors | Manual visual | n/a | ⬜ pending |
| 08-03-xx | 03 | 1 | UI-06, UI-09 | PhaseModal closes only on phase change (no backdrop dismiss) | Manual visual | n/a | ⬜ pending |
| 08-04-xx | 04 | 2 | UI-01–04, UI-10 | No console errors on any screen | Manual visual | n/a | ⬜ pending |
| 08-05-xx | 05 | 2 | UI-07, UI-08 | Score delta animates and removes; podium renders | Manual visual | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/Makefile` — target `pdf` that compiles the report using pandoc; target `clean` that removes build artifacts (relatorio.pdf)

*Existing backend test infrastructure (tests/) covers server logic and does not need modification in this phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Timer color: green >10s, amber ≤10s, red ≤5s | UI-05 | No frontend test framework | Watch CountdownDisplay during a live game turn; observe color transitions |
| Phase modals appear on PHASE_CHANGED | UI-06 | No frontend test framework | Play through a full turn; confirm each modal appears and is the only action input visible |
| ReconnectionBanner amber→red states | UI-09 | Requires network interruption | Disconnect network while in GameScreen; verify amber banner appears immediately, then red after 3s |
| No chat/action input confusion | UI-10 | Requires fresh user perspective | Usability check: ask someone unfamiliar with the app to identify the hint vs. chat inputs |
| Screen polish — no console errors | UI-01–04, UI-08 | Visual QA | Open browser devtools on each screen; confirm zero console errors |
| Score delta animation | UI-07 | Visual timing | Observe SCORING_PHASE: delta floats up and fades in 1.5s, then is removed from DOM |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (docs/Makefile)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
