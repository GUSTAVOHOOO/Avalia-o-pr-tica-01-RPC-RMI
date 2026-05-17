---
phase: 08-ui-polish-technical-report
plan: "06"
subsystem: frontend/pages, frontend/components
tags: [ui, css-hover, accessibility, copywriting, postgame, chat]
dependency_graph:
  requires: [08-02]
  provides: [Landing-hover, PlayerListItem-hover, PostGame-podium-hover, PostGame-row-highlight, ChatPanel-copy]
  affects:
    - frontend/src/pages/Landing.tsx
    - frontend/src/pages/pages.css
    - frontend/src/components/PlayerListItem.tsx
    - frontend/src/pages/PostGame.css
    - frontend/src/pages/PostGame.tsx
    - frontend/src/components/ChatPanel.tsx
    - frontend/src/components/ChatPanel.css
tech_stack:
  added: []
  patterns: [css-hover-not-disabled, tailwind-hover, postgame-row-highlight]
key_files:
  created: []
  modified:
    - frontend/src/pages/Landing.tsx
    - frontend/src/pages/pages.css
    - frontend/src/components/PlayerListItem.tsx
    - frontend/src/pages/PostGame.css
    - frontend/src/pages/PostGame.tsx
    - frontend/src/components/ChatPanel.tsx
    - frontend/src/components/ChatPanel.css
decisions:
  - "PlayerListItem hover uses transition-colors (not transition-opacity) for cleaner bg-color interpolation on dark theme"
  - "pages.css uses :hover:not(:disabled) guard — prevents hover effect on loading/disabled form states"
  - "ChatPanel label-text span text changed to 'Chat' (not replaced with h3) to avoid altering DOM structure and layout"
  - "PostGame.css transition appended to existing .postgame__podium-card rule via new Phase 8 block — existing rules untouched"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-17"
  tasks: 2
  files: 7
requirements:
  - UI-01
  - UI-02
  - UI-03
  - UI-08
  - UI-10
---

# Phase 08 Plan 06: Non-GameScreen Screens + ChatPanel Polish Summary

**One-liner:** CSS-only hover states and focus guards for Landing/forms/Lobby, podium card lift effect for PostGame, and "Chat" heading + "Mensagem..." placeholder copy fix for ChatPanel (no behavioral changes).

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Polish Landing, pages.css hover states, PlayerListItem hover | eb05f12 | Landing.tsx, pages.css, PlayerListItem.tsx |
| 2 | PostGame podium hover + row highlight + ChatPanel copy (UI-08, UI-10) | 97c6c52 | PostGame.css, PostGame.tsx, ChatPanel.tsx, ChatPanel.css |

## What Was Built

**Task 1 — Landing, pages.css, PlayerListItem:**

Landing.tsx: Feature cards (`<div className="rounded-lg p-4 ...">`) received `transition-opacity hover:opacity-90 cursor-default`. Primary CTA already had `hover:opacity-90`; `active:scale-[0.99]` added for press feedback. Secondary join input and both CTA buttons already had `hover:opacity-90` — no duplication added.

pages.css: Two new rules added in a clearly delimited Phase 8 block:
- `.page-submit-btn:hover:not(:disabled) { opacity: 0.9; }` — covers CreateGame and JoinByCode submit buttons via the shared `page-submit-btn` class.
- `.page-input:hover:not(:disabled) { border-color: #6366f1; }` — accent border preview on input hover; consistent with focus ring color.

Note: the existing `.page-input:focus { border-color: #6366f1; outline: none; }` overrides global focus ring for page-input elements with its own deliberate accent border-color treatment. This is correct per design intent (replaces default browser ring with styled accent border) — no change required.

PlayerListItem.tsx: Wrapper div class updated from `transition-opacity duration-200` to `transition-colors hover:bg-[#0f1117] cursor-default`. Uses `transition-colors` for smooth background interpolation; `cursor-default` prevents text-cursor on non-interactive rows.

**Task 2 — PostGame polish + ChatPanel copy:**

PostGame.css: Phase 8 polish block appended after all existing rules:
- `.postgame__podium-card { transition: transform 0.15s ease; }` — prepended to existing card to enable hover animation.
- `.postgame__podium-card:hover { transform: translateY(-2px); }` — lifts card 2px on hover.
- `.postgame__table-row--mine td { background-color: #1a1d27; }` — highlights all cells in current player's row.

PostGame.tsx: `<tr key={pid}>` updated to `<tr key={pid} className={pid === myPlayerId ? 'postgame__table-row--mine' : ''}>`. `myPlayerId` is already in scope from `localStorage.getItem('player_id') ?? ''`.

ChatPanel.tsx: Two string changes only:
1. `<span className="chat-panel__label-text">Mensagem de chat</span>` → text changed to `"Chat"` (span retained; DOM structure unchanged).
2. `placeholder="Mensagem de chat…"` → `placeholder="Mensagem..."` (per UI-SPEC Copywriting Contract).
3. `aria-label="Mensagem de chat"` left unchanged (accessibility label is intentionally more descriptive than placeholder).
4. Submit button "Enviar mensagem" verified unchanged.

ChatPanel.css: Added `font-weight: 600` to `.chat-panel__label-text` so the "Chat" heading visually reads as a heading rather than a plain label hint.

## Verification

All automated checks passed:
- `grep -q "hover:opacity-90" frontend/src/pages/Landing.tsx` — PASS
- `grep -q "hover" frontend/src/components/PlayerListItem.tsx` — PASS
- `grep -q "page-submit-btn:hover" frontend/src/pages/pages.css` — PASS
- `grep -q "postgame__podium-card:hover" frontend/src/pages/PostGame.css` — PASS
- `grep -q "postgame__table-row--mine" frontend/src/pages/PostGame.css` — PASS
- `grep -q "postgame__table-row--mine" frontend/src/pages/PostGame.tsx` — PASS
- `grep -q "Mensagem\.\.\." frontend/src/components/ChatPanel.tsx` — PASS
- `python -m pytest tests/ -x -q` — 78 passed

## Deviations from Plan

None - plan executed exactly as written. The plan noted `page-field__input` as the class name for the input hover rule, but the actual class in the codebase is `page-input` (consistent with all input usages in CreateGame.tsx and JoinByCode.tsx). Rule written as `.page-input:hover:not(:disabled)` to match actual class.

## Known Stubs

None. All changes are complete polish — hover states, CSS transitions, and copy strings are fully wired with no placeholder values.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. All changes are CSS class additions and string replacements in TSX files. Player names in PostGame table rows are rendered as JSX text nodes (`{playerNamesById[pid]}`), confirming T-08-06-01 (XSS) remains mitigated by React's default HTML entity escaping. Chat messages in ChatPanel render as `{msg.message}` JSX text nodes — T-08-06-02 remains mitigated.

## Self-Check: PASSED

- frontend/src/pages/Landing.tsx — FOUND, contains `hover:opacity-90 cursor-default` on feature cards
- frontend/src/pages/pages.css — FOUND, contains `page-submit-btn:hover:not(:disabled)` and `page-input:hover:not(:disabled)`
- frontend/src/components/PlayerListItem.tsx — FOUND, contains `hover:bg-[#0f1117]`
- frontend/src/pages/PostGame.css — FOUND, contains `postgame__podium-card:hover` and `postgame__table-row--mine`
- frontend/src/pages/PostGame.tsx — FOUND, contains `postgame__table-row--mine` className expression
- frontend/src/components/ChatPanel.tsx — FOUND, contains `"Mensagem..."` placeholder and `"Chat"` label
- frontend/src/components/ChatPanel.css — FOUND, contains `font-weight: 600` on `chat-panel__label-text`
- Commit eb05f12 — FOUND (feat(08-06): polish Landing, pages.css hover states, PlayerListItem hover)
- Commit 97c6c52 — FOUND (feat(08-06): polish PostGame podium hover, player row highlight, ChatPanel copy)
