---
phase: 08-ui-polish-technical-report
plan: "02"
subsystem: frontend/components
tags: [ui, timer, reconnection, css-animation, accessibility]
dependency_graph:
  requires: []
  provides: [CountdownDisplay-timerColor, ReconnectionBanner, GameScreen-phase8-css]
  affects: [frontend/src/pages/GameScreen.tsx]
tech_stack:
  added: []
  patterns: [useRef-timer, socket-event-listener, css-keyframes]
key_files:
  created:
    - frontend/src/components/ReconnectionBanner.tsx
    - frontend/src/components/ReconnectionBanner.css
  modified:
    - frontend/src/components/CountdownDisplay.tsx
    - frontend/src/pages/GameScreen.css
decisions:
  - "Timer cleared before setting new one in handleDisconnect to prevent amber→red firing after reconnect (T-08-02-02 mitigation)"
  - "ReconnectionBanner uses socket singleton import; useEffect deps empty because socket is stable singleton"
  - "GameScreen.css extensions appended under clearly delimited '─── Phase 8 additions' comment block"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-17"
  tasks: 2
  files: 4
requirements:
  - UI-05
  - UI-09
---

# Phase 08 Plan 02: CountdownDisplay Color Logic + ReconnectionBanner Summary

**One-liner:** 3-color timer (green/amber/red) with smooth CSS transition and amber→red reconnection banner using useRef timer to prevent accumulation.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add timerColor to CountdownDisplay.tsx (UI-05, D-12) | 4d4a3d4 | frontend/src/components/CountdownDisplay.tsx |
| 2 | Create ReconnectionBanner.tsx + .css + extend GameScreen.css (UI-09, D-15, D-16) | 2adac28 | frontend/src/components/ReconnectionBanner.tsx, ReconnectionBanner.css, frontend/src/pages/GameScreen.css |

## What Was Built

**Task 1 — CountdownDisplay timerColor (UI-05):**
Added `timerColor(seconds: number): string` above the component. Returns `#ef4444` (red) when `seconds <= 5`, `#eab308` (amber) when `seconds <= 10`, and `#22c55e` (green) otherwise. Replaced the static `color: '#f1f5f9'` in the `<span>` style with `color: timerColor(seconds)` and added `transition: 'color 0.3s ease'` for smooth state transitions. Shape mirrors `voteBarColor()` in PostGame.tsx.

**Task 2 — ReconnectionBanner (UI-09):**
Created `ReconnectionBanner.tsx` implementing the amber-immediate → red-after-3s → hidden-on-reconnect state machine:
- `bannerState` is `'hidden' | 'amber' | 'red'`
- `bannerTimerRef` holds the 3-second timer; always cleared before setting new timer (prevents T-08-02-02 accumulation on rapid disconnect/reconnect cycles)
- Listens to `socket.on('disconnect')` and `socket.on('connect')` on the stable socket singleton
- Returns `null` when hidden so there is no DOM presence
- Renders with `role="alert"` and `aria-live="assertive"` for screen reader accessibility
- Copywriting: amber="Reconectando...", red="Offline — verifique sua conexão" (exact strings from UI-SPEC)

Created `ReconnectionBanner.css`: fixed top bar (position: fixed, top: 0, z-index: 100) with background-color transition. Amber state = `#92400e` background / `#fef3c7` text. Red state = `#7f1d1d` background / `#fee2e2` text.

Extended `GameScreen.css` with a clearly delimited Phase 8 block containing:
- `@keyframes slideInFromBottom` (opacity + translateY(24px) → 0)
- `@keyframes slideUpFade` (0%/70%/100% stops for toast exit animation)
- `.score-delta-toast` (position: absolute, animation: slideUpFade 1.5s ease-out forwards)
- `.game-screen--banner-visible { padding-top: 40px }` (pushes content below the fixed banner)
- `.panel-btn-primary:hover:not(:disabled)` and `.panel-btn-skip:hover:not(:disabled)` opacity tweaks

## Verification

All automated checks passed:
- `grep -q "timerColor" frontend/src/components/CountdownDisplay.tsx` — PASS
- `test -f frontend/src/components/ReconnectionBanner.tsx` — PASS
- `test -f frontend/src/components/ReconnectionBanner.css` — PASS
- `grep -q "slideInFromBottom" frontend/src/pages/GameScreen.css` — PASS
- `python -m pytest tests/ -x -q` — 78 passed

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. Components are complete and ready for integration. GameScreen.tsx integration occurs in Plan 08-05 (Wave 2).

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. ReconnectionBanner reads only socket connection state (boolean event, no user input). Timer accumulation threat (T-08-02-02) mitigated by always clearing before setting.

## Self-Check: PASSED

- frontend/src/components/CountdownDisplay.tsx — FOUND, contains timerColor
- frontend/src/components/ReconnectionBanner.tsx — FOUND, contains bannerTimerRef
- frontend/src/components/ReconnectionBanner.css — FOUND, contains reconnection-banner--amber
- frontend/src/pages/GameScreen.css — FOUND, contains slideInFromBottom and game-screen--banner-visible
- Commit 4d4a3d4 — FOUND (feat(08-02): add timerColor to CountdownDisplay)
- Commit 2adac28 — FOUND (feat(08-02): create ReconnectionBanner and extend GameScreen.css)
