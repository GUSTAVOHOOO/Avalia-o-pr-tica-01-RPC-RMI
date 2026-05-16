---
phase: 07-reconnection-end-of-game
plan: "04"
subsystem: frontend
tags: [wave-2, frontend, react, typescript, postgame, chat, socket-io]
dependency_graph:
  requires:
    - "07-02"  # server RPC methods (send_chat, submit_vote, _start_vote, _resolve_vote)
    - "07-03"  # bridge handlers + GameScreen reconnect/navigate wiring
  provides:
    - frontend/src/components/ChatPanel.tsx (D-04 visual separation, chat input/submit/messages)
    - frontend/src/components/ChatPanel.css (chat-panel__* CSS classes)
    - frontend/src/pages/PostGame.tsx (podium, per-turn table, 30s vote, game_ended/game_restarting handlers)
    - frontend/src/pages/PostGame.css (postgame__* CSS classes)
    - frontend/src/App.tsx (/postgame/:roomCode route)
    - frontend/src/pages/GameScreen.tsx (ChatPanel rendered below game actions)
  affects:
    - All players see PostGame after last turn
    - Chat panel visually separated from game action inputs in GameScreen
tech_stack:
  added: []
  patterns:
    - "Two-path score arrival: game_ended populates finalScores; vote_started path renders loading state"
    - "userScrolled ref guard: auto-scroll only fires when user is at bottom of chat"
    - "redirectIntervalRef for 3s countdown before navigate('/') on game truly ended"
    - "voteBarColor() pure function mapping secondsLeft thresholds to CSS color values"
    - "myVoteSubmitted client guard (defense-in-depth) + server deduplication in submit_vote()"
key_files:
  created:
    - frontend/src/components/ChatPanel.tsx
    - frontend/src/components/ChatPanel.css
    - frontend/src/pages/PostGame.tsx
    - frontend/src/pages/PostGame.css
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/GameScreen.tsx
decisions:
  - "ChatPanel placed as fixed panel below the game action area (not a tab) — satisfies CHAT-03 without hiding chat behind tab click"
  - "PostGame initializes finalScores=[] and renders 'Calculando pontuação…' until game_ended arrives (handles vote_started navigation path)"
  - "redirectCountdown state drives '3…2…1' display then navigate('/') via setInterval in game_ended handler"
  - "voteBarColor() uses 3-threshold color progression: accent (#6366f1) >10s, warning (#eab308) <=10s, destructive (#ef4444) <=5s"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-16"
  tasks_completed: 2
  tasks_total: 3
  files_created: 4
  files_modified: 2
---

# Phase 7 Plan 04: Frontend Vertical Slice Summary

**One-liner:** ChatPanel component with D-04 muted-gray visual separation + PostGame screen with podium/per-turn-table/30s-vote + /postgame/:roomCode route completing the end-to-end post-game loop.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ChatPanel.tsx and wire into GameScreen.tsx | 44b8acf | ChatPanel.tsx, ChatPanel.css, GameScreen.tsx |
| 2 | Create PostGame.tsx and add /postgame route in App.tsx | f24ee54 | PostGame.tsx, PostGame.css, App.tsx |

## What Was Built

### Task 1 — ChatPanel component + GameScreen wire-up

**New `frontend/src/components/ChatPanel.tsx`:**
- Props interface: `messages: ChatMessage[]`, `myPlayerId: string`, `onSend: (msg: string) => void`, `disabled?: boolean`
- Internal state: `chatInput` (useState), `messagesEndRef` (useRef for auto-scroll), `userScrolledRef` (tracks manual scroll to prevent overriding reading position)
- `handleSend()`: calls `onSend(chatInput.trim())`, clears input, resets `userScrolledRef` to false (next append will auto-scroll)
- `onKeyDown`: submits on Enter (not Shift+Enter)
- Empty state: "Nenhuma mensagem ainda. Seja o primeiro!" when `messages.length === 0`
- Message time formatted as HH:MM from Unix timestamp
- D-04 constraints applied: label "Mensagem de chat", submit "Enviar mensagem", left-border `#6b7280`

**New `frontend/src/components/ChatPanel.css`:**
- `.chat-panel`: left border `3px solid #6b7280` (muted gray — NOT a phase accent color)
- `.chat-panel__input`: border `#4b5563` (distinct from game action inputs which use `#2d3148`)
- `.chat-panel__submit`: accent background `#6366f1`, labeled "Enviar mensagem"
- `.chat-panel__messages`: `overflow-y: auto`, `max-height: 240px`

**Modified `frontend/src/pages/GameScreen.tsx`:**
- Added `import ChatPanel from '../components/ChatPanel'`
- Added `sendChatMessage(msg: string)` function: `socket.emit('send_chat', { message: msg }, () => undefined)`
- Rendered `<ChatPanel messages={chatMessages} myPlayerId={myPlayerId} onSend={sendChatMessage} />` below game action area

### Task 2 — PostGame.tsx + /postgame route

**New `frontend/src/pages/PostGame.tsx`:**
- Interfaces: `ScoreEntry`, `TurnScoreEntry`, `VoteStartedPayload`, `VoteUpdatePayload`
- Two-path score data arrival: PostGame initializes `finalScores=[]` (renders "Calculando pontuação…"); `game_ended` event populates sorted `finalScores` and `turnHistory` when it arrives
- Handlers: `vote_started` (start countdown interval), `vote_update` (update yes/votes counts), `game_restarting` (clear interval, set result, navigate to /game/:roomCode after 1.5s), `game_ended` (populate scores, set result, 3s countdown then navigate to /)
- Vote bar: `voteBarColor()` maps `secondsLeft` to accent/warning/destructive; inline `style.width` = `(secondsLeft/30 * 100)%` with CSS `transition: width 1s linear`
- `submitVote(continueGame)`: guarded by `myVoteSubmitted` state; emits `submit_vote`
- Per-turn table: columns = Jogador + Turno 1...N + Total; builds from `turnHistory` and `playerIds` derived from `finalScores`
- Result banners: "restarting" shows green-bordered banner; "ended" shows accent-bordered banner + redirect countdown

**New `frontend/src/pages/PostGame.css`:**
- All `.postgame__*` CSS classes per UI-SPEC
- `.postgame__podium-card--first`: `border-top: 3px solid #22c55e`, `padding-top: 32px`
- `.postgame__vote-bar`: `height: 8px`, `border-radius: 4px`, `transition: width 1s linear, background-color 0.5s ease`

**Modified `frontend/src/App.tsx`:**
- Added `import PostGame from './pages/PostGame'`
- Added `<Route path="/postgame/:roomCode" element={<PostGame />} />`

## Test Results

| Test File | Tests | Result |
|-----------|-------|--------|
| tests/test_chat.py | 4 | 4 PASSED |
| tests/test_postgame.py | 6 | 6 PASSED |
| Full suite | 78 | 78 PASSED |

TypeScript: `npx tsc --noEmit` exits 0 (no errors)

## Checkpoint

**Task 3 is a `checkpoint:human-verify` (gate: blocking).** Execution stopped here as required. The checkpoint requires a 4-scenario manual smoke test:

1. Chat separation: label "Mensagem de chat", button "Enviar mensagem", gray left border, real-time delivery
2. Post-game screen: podium, per-turn table, 30s vote bar
3. Vote restart path: both click "Continuar com novos objetos" → navigate back to /game/:roomCode
4. Vote end path (timer expiry): banner + redirect countdown → navigate to /

## Deviations from Plan

None — plan executed exactly as written. All required CSS class names, copy strings, and identifiers are present per UI-SPEC.

## Known Stubs

None. All Socket.IO events are wired to handlers that produce visible state changes. All server-side RPCs (send_chat, submit_vote, _start_vote, _resolve_vote) are implemented in plan 07-02.

## Threat Surface Scan

All mitigations from the plan's `<threat_model>` are implemented:

| Threat ID | Mitigation | Location |
|-----------|-----------|---------|
| T-07-04-01 | `myVoteSubmitted` state guards double-click; server deduplicates in `submit_vote()` | PostGame.tsx:153, game_server.py |
| T-07-04-03 | `userScrolledRef` tracks manual scroll; auto-scroll only fires when at bottom | ChatPanel.tsx:36-40 |
| T-07-04-04 | `player_name` rendered from server payload (set at join time, validated server-side) | PostGame.tsx, ChatPanel.tsx |

T-07-04-02 accepted disposition: final_scores contains no PII beyond player names/scores.

## Self-Check: PASSED

- frontend/src/components/ChatPanel.tsx: EXISTS
- frontend/src/components/ChatPanel.css: EXISTS
- frontend/src/pages/PostGame.tsx: EXISTS
- frontend/src/pages/PostGame.css: EXISTS
- frontend/src/App.tsx: modified — PostGame route present
- frontend/src/pages/GameScreen.tsx: modified — ChatPanel imported and rendered
- Commit 44b8acf: feat(07-04): create ChatPanel component — FOUND
- Commit f24ee54: feat(07-04): create PostGame screen — FOUND
- TypeScript compiles: 0 errors
- Full test suite: 78/78 PASSED

## Post-Checkpoint Bug Fixes (commit 1005669)

Two bugs reported by user during manual smoke test:

### Bug 1 — vote_started event lost on navigation

**Root cause:** `GameScreen.tsx` called `navigate('/postgame/:roomCode')` in response to the `vote_started` socket event. `PostGame.tsx` registered its `socket.on('vote_started', ...)` listener inside a `useEffect` that runs after mount. Since navigation was triggered by the same event, `PostGame` mounted after the event had already fired — the listener never received it, `voteActive` stayed `false`, and the vote UI never appeared.

**Fix:**
- `GameScreen.tsx`: pass vote data via React Router navigate state: `navigate('/postgame/${roomCode}', { state: { voteActive: true, durationSeconds: data.duration_seconds, playerCount: data.player_count } })`
- `PostGame.tsx`: add `useLocation()`, read `navState` from `location.state`, initialize `voteActive`/`voteSecondsLeft`/`totalPlayers` from navState so the vote UI shows immediately on mount
- `PostGame.tsx`: add a mount-time `useEffect` (runs once, `[]` deps) that starts the countdown interval immediately if `navState.voteActive` is true; stores timer in `intervalRef.current` so the reconnect-path `handleVoteStarted` can clear it before starting a new one

### Bug 2 — 3-second redirect countdown too short to read final scores

**Root cause:** The `game_ended` handler started a 3s interval before navigating to `/`. This was not enough time for players to read the podium and score table.

**Fix:** Changed `let count = 3` to `let count = 10` and initial `setRedirectCountdown` value from `3` to `10` in the `game_ended` handler. Also updated initial `useState` for `redirectCountdown` from `3` to `10`.

### Decisions

- `barWidth` calculation (`voteSecondsLeft / 30`) remains correct: `voteSecondsLeft` is initialized from `navState?.durationSeconds ?? 30`, which matches the server's 30s duration.
- Existing `handleVoteStarted` socket listener kept as fallback for reconnect scenarios where PostGame is loaded directly without navigation state.
- Mount-time `useEffect` deps array is `[]` (intentional) — `navState` is captured from closure at mount time and is stable.

### Post-fix verification

- `npx tsc --noEmit`: 0 errors
- `pytest tests/test_postgame.py tests/test_chat.py`: 10/10 PASSED
