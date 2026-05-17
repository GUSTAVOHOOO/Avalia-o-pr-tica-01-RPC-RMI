# Phase 8: UI Polish + Technical Report — Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 15 new/modified files
**Analogs found:** 13 / 15

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/components/PhaseModal.tsx` | component | request-response | `frontend/src/pages/GameScreen.tsx` `renderPhasePanel()` (lines 327–501) | role-match — same phase variants, same socket emits |
| `frontend/src/components/PhaseModal.css` | config | — | `frontend/src/pages/GameScreen.css` (panel card pattern) | role-match |
| `frontend/src/components/ReconnectionBanner.tsx` | component | event-driven | `frontend/src/pages/PostGame.tsx` (useRef + setInterval + socket.on cleanup pattern, lines 58–101) | partial-match — same useRef timer idiom, different events |
| `frontend/src/components/ReconnectionBanner.css` | config | — | `frontend/src/pages/GameScreen.css` `.player-left-toast` (lines 289–305) | partial-match — same fixed-position pattern |
| `frontend/src/components/ScoreDeltaToast.tsx` | component | event-driven | `frontend/src/pages/GameScreen.tsx` `.player-left-toast` (lines 506–510) + `PostGame.tsx` voteBarColor (lines 30–34) | partial-match |
| `frontend/src/components/CountdownDisplay.tsx` | component | transform | `frontend/src/pages/PostGame.tsx` `voteBarColor()` (lines 30–34) | exact — identical 3-threshold color derivation pattern |
| `frontend/src/pages/GameScreen.tsx` | page | event-driven | self — refactor existing code | self-refactor |
| `frontend/src/pages/GameScreen.css` | config | — | self — extend existing file | self-extend |
| `frontend/src/pages/Landing.tsx` | page | request-response | self — CSS polish only | self-polish |
| `frontend/src/pages/CreateGame.tsx` | page | request-response | `frontend/src/pages/JoinByCode.tsx` | role-match |
| `frontend/src/pages/JoinByCode.tsx` | page | request-response | `frontend/src/pages/CreateGame.tsx` | role-match |
| `frontend/src/pages/Lobby.tsx` | page | event-driven | self — CSS polish only | self-polish |
| `frontend/src/pages/PostGame.tsx` | page | event-driven | self — CSS polish only | self-polish |
| `docs/relatorio.md` | utility | — | none | no-analog |
| `docs/Makefile` | config | — | none | no-analog |

---

## Pattern Assignments

### `frontend/src/components/PhaseModal.tsx` (component, request-response)

**Analog:** `frontend/src/pages/GameScreen.tsx` lines 327–501 (`renderPhasePanel()` switch)

**Imports pattern** — copy from GameScreen.tsx lines 1–7:
```typescript
import socket from '../socket'
import PhaseBadge from './PhaseBadge'
import './PhaseModal.css'
```

**Props interface** — defined in 08-RESEARCH.md Pattern 1. Key types to copy from GameScreen.tsx lines 9–68:
```typescript
// Reuse these exact interface shapes from GameScreen.tsx:
interface Player { player_id: string; player_name: string; is_host: boolean }
interface ScoreEntry { player_id: string; player_name: string; turn_delta: number; total: number }

// New interface added in PhaseModal.tsx:
interface ExchangeRequest { exchange_id: string; requester_id: string }
```

**Core pattern — overlay wrapper** (position:fixed overlay, no backdrop-close):
```typescript
// PhaseModal renders null when phase is not one of the 4 action phases
const ACTION_PHASES = ['HINT_PHASE', 'GUESS_PHASE', 'EXCHANGE_PHASE', 'SPY_PHASE']
if (!ACTION_PHASES.includes(phase)) return null

return (
  <div className="phase-modal-overlay">
    <div className="phase-modal-surface">
      <div className="phase-modal-header">
        <PhaseBadge phase={phase} />
        <h2 className="phase-modal-title">{PHASE_TITLES[phase]}</h2>
      </div>
      {phase === 'HINT_PHASE' && <HintVariant {...} />}
      {phase === 'GUESS_PHASE' && <GuessVariant {...} />}
      {phase === 'EXCHANGE_PHASE' && <ExchangeVariant {...} />}
      {phase === 'SPY_PHASE' && <SpyVariant {...} />}
    </div>
  </div>
)
```

**Input + button pattern** — copy directly from GameScreen.tsx lines 337–358 (HINT inline) and 391–431 (GUESS inline). These exact blocks move inside PhaseModal variants with zero logic change:
```typescript
// HINT variant — copied from GameScreen.tsx lines 337–358:
<label className="panel-field">
  <span className="panel-label-text">Dica</span>
  <input
    type="text"
    maxLength={30}
    value={hintInput}
    onChange={(e) => onHintChange(e.target.value)}
    disabled={hintSubmitted}
    placeholder="Uma palavra..."
    className="panel-input"
  />
</label>
<button
  type="button"
  onClick={onHintSubmit}
  disabled={!hintInput.trim() || hintSubmitted || !/^\S+$/.test(hintInput)}
  className="panel-btn-primary"
>
  {hintSubmitted ? 'Dica enviada' : 'Enviar dica'}
</button>
```

**EXCHANGE variant role detection** — flag `myExchangeId !== null` distinguishes requester from recipient (see 08-RESEARCH.md Pitfall 3):
```typescript
// Inside ExchangeVariant:
const isRequester = myExchangeId !== null
if (isRequester) {
  // Show status: pending/accepted/waiting for partner hint
} else if (exchangeRequest !== null) {
  // Show Aceitar / Recusar buttons
}
```

**SPY variant destructive button pattern** — copy `.panel-btn-skip` CSS class from GameScreen.css line 209 (outline-red style):
```typescript
<button className="panel-btn-skip" onClick={onSpyAttempt} disabled={spyAttempted}>
  Espiar
</button>
// Inline risk warning above button (NOT a dialog):
<p className="phase-modal-risk-text">
  Atenção: se descoberto, você perde 10 pontos. Deseja continuar?
</p>
```

**Validation — HINT no-spaces check** (security: V5 input validation per 08-RESEARCH.md):
```typescript
// Client-side guard before submit (server also validates):
disabled={!hintInput.trim() || hintSubmitted || /\s/.test(hintInput)}
```

---

### `frontend/src/components/PhaseModal.css` (config)

**Analog:** `frontend/src/pages/GameScreen.css` panel card pattern (lines 98–123) + `frontend/src/components/ChatPanel.css` card structure (lines 3–12)

**Overlay and surface** — add as new classes, do not repeat `.phase-panel`:
```css
/* Overlay */
.phase-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Surface card — matches #1a1d27 card pattern from GameScreen.css line 101 */
.phase-modal-surface {
  background-color: #1a1d27;
  border: 1px solid #2d3148;
  border-radius: 12px;
  padding: 24px;
  max-width: 480px;
  width: 100%;
  animation: slideInFromBottom 250ms ease-out;
}

/* Header row: PhaseBadge + title */
.phase-modal-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.phase-modal-title {
  color: #f1f5f9;
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

/* Risk warning text for SPY variant */
.phase-modal-risk-text {
  color: #ef4444;
  font-size: 14px;
  margin: 0 0 8px 0;
}
```

**Keyframe — add to `GameScreen.css` or `index.css`** (not inline):
```css
@keyframes slideInFromBottom {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

**Reuse existing classes** — PhaseModal variants must use these GameScreen.css classes without redefining them:
- `.panel-field`, `.panel-label-text`, `.panel-input`, `.panel-btn-primary`, `.panel-btn-primary--flex`, `.panel-btn-skip`, `.panel-btn-row`, `.hint-chips`, `.hint-chip`, `.hint-chip--mine`, `.hint-chip--empty`

---

### `frontend/src/components/ReconnectionBanner.tsx` (component, event-driven)

**Analog:** `frontend/src/pages/PostGame.tsx` lines 58–101 (useRef timer + setInterval cleanup) and `frontend/src/pages/GameScreen.tsx` lines 154–297 (useEffect socket.on/off cleanup pattern)

**Imports pattern:**
```typescript
import { useEffect, useRef, useState } from 'react'
import socket from '../socket'
import './ReconnectionBanner.css'
```

**Core pattern — useRef timer + socket events** (copy shape from 08-RESEARCH.md Pattern 2):
```typescript
// State
const [bannerState, setBannerState] = useState<'hidden' | 'amber' | 'red'>('hidden')
const bannerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

// useEffect — identical cleanup shape as GameScreen.tsx lines 281–296
useEffect(() => {
  const handleDisconnect = () => {
    if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current)  // guard: Pitfall 2
    setBannerState('amber')
    bannerTimerRef.current = setTimeout(() => setBannerState('red'), 3000)
  }
  const handleConnect = () => {
    if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current)
    setBannerState('hidden')
  }
  socket.on('disconnect', handleDisconnect)
  socket.on('connect', handleConnect)
  return () => {
    socket.off('disconnect', handleDisconnect)
    socket.off('connect', handleConnect)
    if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current)
  }
}, [])  // empty deps — socket is a stable singleton from socket.ts

// Render
if (bannerState === 'hidden') return null
return (
  <div
    className={`reconnection-banner reconnection-banner--${bannerState}`}
    role="alert"
    aria-live="assertive"
  >
    {bannerState === 'amber' ? 'Reconectando...' : 'Offline — verifique sua conexão'}
  </div>
)
```

**Integration in GameScreen.tsx** — add near top of `<div className="game-screen">`:
```typescript
// Add import at top:
import ReconnectionBanner from '../components/ReconnectionBanner'

// Add inside game-screen wrapper, before header:
<ReconnectionBanner />
// Also add conditional padding-top when banner visible — use class on game-screen div:
// tracked via same bannerState, or lifted into GameScreen state
```

---

### `frontend/src/components/ReconnectionBanner.css` (config)

**Analog:** `frontend/src/pages/GameScreen.css` `.player-left-toast` (lines 289–305) — same `position: fixed` pattern, different placement (top vs bottom-right)

```css
/* Full-width fixed sticky top bar — does NOT push page content */
.reconnection-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  min-height: 40px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  transition: background-color 0.5s ease;
}

/* Amber: 0–3s offline — matches #92400e from UI-SPEC Color section */
.reconnection-banner--amber {
  background-color: #92400e;
  color: #fef3c7;
}

/* Red: >3s offline */
.reconnection-banner--red {
  background-color: #7f1d1d;
  color: #fee2e2;
}
```

**GameScreen padding-top** — add to GameScreen.css:
```css
/* Applied when ReconnectionBanner is visible (conditional class or CSS var) */
.game-screen--banner-visible {
  padding-top: 40px;
}
```

---

### `frontend/src/components/ScoreDeltaToast.tsx` (component, event-driven)

**Analog:** `frontend/src/pages/GameScreen.tsx` `.player-left-toast` (lines 506–510, GameScreen.css lines 289–305) for the fixed-position toast shape; `frontend/src/pages/PostGame.tsx` `voteBarColor()` (lines 30–34) for the color derivation.

**Imports pattern:**
```typescript
import './ScoreDeltaToast.css'
```

**Props + render** (removed from DOM via onAnimationEnd per 08-RESEARCH.md Pattern 3):
```typescript
interface ScoreDeltaToastProps {
  id: string
  delta: number
  playerName: string
  onDone: (id: string) => void
}

export default function ScoreDeltaToast({ id, delta, playerName, onDone }: ScoreDeltaToastProps) {
  const color = delta > 0 ? '#22c55e' : delta < 0 ? '#ef4444' : '#6b7280'
  const label = delta > 0 ? `+${delta}` : `${delta}`

  return (
    <div
      className="score-delta-toast"
      style={{ color }}
      aria-label={`${playerName}: ${label} pontos`}
      onAnimationEnd={() => onDone(id)}
    >
      {label}
    </div>
  )
}
```

**State in GameScreen.tsx** — add alongside `scores` state (line 149):
```typescript
interface DeltaToast { id: string; playerName: string; delta: number }
const [deltaToasts, setDeltaToasts] = useState<DeltaToast[]>([])

// Replace line 241 handleScoreUpdated:
const handleScoreUpdated = (data: ScoreUpdatedPayload) => {
  setScores(data.scores)
  const newToasts = data.scores
    .filter((s) => s.turn_delta !== 0)
    .map((s) => ({
      id: `${s.player_id}-${Date.now()}`,
      playerName: s.player_name,
      delta: s.turn_delta,
    }))
  setDeltaToasts((prev) => [...prev, ...newToasts])
}

const removeToast = (id: string) =>
  setDeltaToasts((prev) => prev.filter((t) => t.id !== id))
```

**Render toasts** — wrap scoring section in relative container:
```typescript
// In the SCORING_PHASE branch of renderPhasePanel (GameScreen.tsx line 461):
<section className="phase-panel phase-panel--scoring" style={{ position: 'relative' }}>
  {deltaToasts.map((t) => (
    <ScoreDeltaToast key={t.id} {...t} onDone={removeToast} />
  ))}
  {/* ...existing score-list content... */}
</section>
```

**CSS** — add to GameScreen.css:
```css
.score-delta-toast {
  position: absolute;
  top: 8px;
  right: 16px;
  animation: slideUpFade 1.5s ease-out forwards;
  font-size: 20px;
  font-weight: 600;
  pointer-events: none;
  z-index: 10;
}

@keyframes slideUpFade {
  0%   { opacity: 1; transform: translateY(0); }
  70%  { opacity: 1; transform: translateY(-24px); }
  100% { opacity: 0; transform: translateY(-32px); }
}
```

---

### `frontend/src/components/CountdownDisplay.tsx` (component, transform — REFINE)

**Analog:** `frontend/src/pages/PostGame.tsx` `voteBarColor()` (lines 30–34) — exact same 3-threshold pattern

**Current file** (`frontend/src/components/CountdownDisplay.tsx`, all 18 lines) — only lines 6–16 change:

**Before (lines 6–16):**
```typescript
export default function CountdownDisplay({ seconds }: CountdownDisplayProps) {
  return (
    <span
      style={{
        fontSize: '28px',
        fontWeight: 600,
        color: '#f1f5f9',     // ← static color, replace this
      }}
      aria-live="polite"
    >
      {seconds}s
    </span>
  )
}
```

**After — add `timerColor` helper before the component, update style:**
```typescript
// Add above the component (copy pattern from PostGame.tsx voteBarColor, lines 30–34):
function timerColor(seconds: number): string {
  if (seconds <= 5) return '#ef4444'   // red
  if (seconds <= 10) return '#eab308'  // amber
  return '#22c55e'                     // green
}

export default function CountdownDisplay({ seconds }: CountdownDisplayProps) {
  return (
    <span
      style={{
        fontSize: '28px',
        fontWeight: 600,
        color: timerColor(seconds),
        transition: 'color 0.3s ease',
      }}
      aria-live="polite"
    >
      {seconds}s
    </span>
  )
}
```

---

### `frontend/src/pages/GameScreen.tsx` (page, event-driven — REFACTOR)

**Self-refactor.** Key surgery points with exact line references:

**1. Remove inline phase panels** — delete `renderPhasePanel()` function (lines 326–501) and replace its call (line 541) with `<PhaseModal ... />`.

**2. Add new state variables** — insert after line 151 (`const [chatMessages...`):
```typescript
// Exchange/SPY state (per 08-RESEARCH.md Pattern 5)
const [exchangeRequest, setExchangeRequest] = useState<ExchangeRequest | null>(null)
const [myExchangeId, setMyExchangeId] = useState<string | null>(null)
const [exchangeStatus, setExchangeStatus] = useState<string | null>(null)
const [exchangeHintInput, setExchangeHintInput] = useState('')
const [exchangeHintSubmitted, setExchangeHintSubmitted] = useState(false)
const [selectedSpyTarget, setSelectedSpyTarget] = useState('')
const [spyTargets, setSpyTargets] = useState<string[]>([])
const [spyAttempted, setSpyAttempted] = useState(false)
// Delta toasts
const [deltaToasts, setDeltaToasts] = useState<DeltaToast[]>([])
// Banner
const [bannerVisible, setBannerVisible] = useState(false)
```

**3. Extend `applyPhase` HINT_PHASE reset** — after line 178 (`setScores([])`):
```typescript
// Reset exchange/spy state on new turn:
setExchangeRequest(null)
setMyExchangeId(null)
setExchangeStatus(null)
setExchangeHintInput('')
setExchangeHintSubmitted(false)
setSelectedSpyTarget('')
setSpyAttempted(false)
setDeltaToasts([])
```

**4. Register new socket handlers** — after line 278 (`socket.on('vote_started'...)`):
```typescript
// Exchange/SPY handlers (events documented in 08-RESEARCH.md Pattern 5):
socket.on('exchange_requested', (data) => {
  setExchangeRequest({ exchange_id: data.exchange_id, requester_id: data.requester_id })
})
socket.on('exchange_hints', () => {
  setExchangeHintSubmitted(true)
})
socket.on('spy_success', () => {
  setSpyAttempted(true)
})
socket.on('spy_discovered', () => {
  setSpyAttempted(true)
})
```

**5. Add socket emitters** — after `skipGuess()` (line 320):
```typescript
function respondExchange(accept: boolean) {
  if (!exchangeRequest) return
  socket.emit('respond_exchange', { exchange_id: exchangeRequest.exchange_id, accept }, () => undefined)
  if (!accept) setExchangeRequest(null)
  else setExchangeStatus('accepted')
}

function submitExchangeHint() {
  if (!exchangeRequest || exchangeHintSubmitted) return
  socket.emit('submit_exchange_hint', { exchange_id: exchangeRequest.exchange_id, hint_word: exchangeHintInput }, () => undefined)
  setExchangeHintSubmitted(true)
}

function requestExchange(targetPlayerId: string) {
  socket.emit('request_exchange', { target_player_id: targetPlayerId }, (resp: { ok: boolean; exchange_id?: string }) => {
    if (resp.ok && resp.exchange_id) setMyExchangeId(resp.exchange_id)
  })
}

function attemptSpy() {
  if (!selectedSpyTarget || spyAttempted) return
  socket.emit('attempt_spy', { exchange_id: selectedSpyTarget }, () => undefined)
  setSpyAttempted(true)
}
```

**6. PhaseModal integration** — replace `renderPhasePanel()` call (line 541):
```typescript
// Replace: {renderPhasePanel()}
// With:
<PhaseModal
  phase={currentPhase}
  players={players}
  myPlayerId={myPlayerId}
  hintInput={hintInput}
  onHintChange={setHintInput}
  onHintSubmit={submitHint}
  hintSubmitted={myHintSubmitted}
  hintsCount={hintsCount}
  totalPlayers={totalPlayers}
  hints={hints}
  guessTarget={guessTarget}
  onGuessTargetChange={setGuessTarget}
  guessInput={guessInput}
  onGuessInputChange={setGuessInput}
  onGuessSubmit={submitGuess}
  onGuessSkip={skipGuess}
  guessSubmitted={myGuessSubmitted}
  guessIsCorrect={guessIsCorrect}
  exchangeRequest={exchangeRequest}
  myExchangeId={myExchangeId}
  exchangeStatus={exchangeStatus}
  exchangeHintInput={exchangeHintInput}
  onExchangeHintChange={setExchangeHintInput}
  onExchangeAccept={() => respondExchange(true)}
  onExchangeDecline={() => respondExchange(false)}
  onExchangeHintSubmit={submitExchangeHint}
  exchangeHintSubmitted={exchangeHintSubmitted}
  spyTargets={spyTargets}
  selectedSpyTarget={selectedSpyTarget}
  onSpyTargetSelect={setSelectedSpyTarget}
  onSpyAttempt={attemptSpy}
  spyAttempted={spyAttempted}
/>
```

---

### `frontend/src/pages/GameScreen.css` (config — EXTEND)

**Self-extend.** Add these sections after the existing content (after line 306):

```css
/* ─── New Phase 8 additions ──────────────────────────────────────────────── */

/* Entry animation for phase modal */
@keyframes slideInFromBottom {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Score delta float-up toast animation */
@keyframes slideUpFade {
  0%   { opacity: 1; transform: translateY(0); }
  70%  { opacity: 1; transform: translateY(-24px); }
  100% { opacity: 0; transform: translateY(-32px); }
}

.score-delta-toast {
  position: absolute;
  top: 8px;
  right: 16px;
  animation: slideUpFade 1.5s ease-out forwards;
  font-size: 20px;
  font-weight: 600;
  pointer-events: none;
  z-index: 10;
}

/* Shift content down when ReconnectionBanner is visible */
.game-screen--banner-visible {
  padding-top: 40px;
}

/* Hover states on primary buttons (polish UI-07) */
.panel-btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}
.panel-btn-skip:hover:not(:disabled) {
  opacity: 0.85;
}
```

---

### `frontend/src/pages/Landing.tsx` (page — CSS POLISH)

**Self-polish.** Key additions using Tailwind classes already on the page:

**Feature cards hover** — current cards (lines 54–68) use `rounded-lg p-4` with static background. Add hover via Tailwind `hover:` prefix:
```typescript
// Before (line 57):
className="rounded-lg p-4"
// After:
className="rounded-lg p-4 transition-opacity hover:opacity-90 cursor-default"
```

**Primary CTA** — already has `hover:opacity-90` (line 74). Verify `active:opacity-80` is also present.

**Secondary input focus** — current input (lines 90–104) uses border `#2d3148`. Add hover border class via `style`:
```typescript
// Add onFocus/onBlur OR rely on the global *:focus-visible rule in index.css
// index.css line 12-14 already covers focus ring globally — no change needed
```

---

### `frontend/src/pages/Lobby.tsx` (page — CSS POLISH)

**Analog for player list hover:** `frontend/src/components/ChatPanel.css` `.chat-panel__message` pattern (lines 37–46) — border-bottom rows with hover.

**PlayerListItem hover** — the component `frontend/src/components/PlayerListItem.tsx` renders player rows. Add hover state in its CSS or via Tailwind:
```typescript
// In PlayerListItem: add hover class
className="... hover:bg-[#0f1117] transition-colors cursor-default"
```

**Toast auto-remove** — Lobby.tsx already uses `setTimeout` (line 38) + filter pattern. Do not change — it is not `onAnimationEnd` but the pattern is isolated to short-lived toasts.

---

### `frontend/src/pages/PostGame.tsx` (page — CSS POLISH)

**Self-polish.** Analog: existing `.score-row--mine` pattern (GameScreen.css line 255) for row highlight.

**Podium card hover** — cards rendered at line 221, class `postgame__podium-card`. Add to PostGame.css:
```css
.postgame__podium-card {
  transition: transform 0.15s ease;
}
.postgame__podium-card:hover {
  transform: translateY(-2px);
}
```

**Table row highlight for current player** — match the `.score-row--mine` pattern from GameScreen.css line 255. In PostGame.tsx tbody rows (line 252):
```typescript
<tr
  key={pid}
  className={pid === myPlayerId ? 'postgame__table-row--mine' : ''}
>
```
Add CSS:
```css
.postgame__table-row--mine td {
  background-color: #1a1d27;
}
```

---

### `frontend/src/components/ChatPanel.tsx` (component — COPY POLISH)

**Self-polish.** Two string changes per 08-UI-SPEC.md Copywriting Contract:

- Line 87: `<span className="chat-panel__label-text">Mensagem de chat</span>` → remove this hidden label (keep aria-label on input)
- Line 96: `placeholder="Mensagem de chat…"` → `placeholder="Mensagem..."`
- The `aria-label` on line 95 stays: `aria-label="Mensagem de chat"` (accessibility)
- Line 106: "Enviar mensagem" is already correct — no change.

---

### `docs/relatorio.md` (utility — NO ANALOG)

**No existing analog.** File is a new Markdown document. Structure per 08-CONTEXT.md D-06:

```markdown
---
title: "Jogo de Adivinhação Multijogador via RPC/Pyro5"
author: "Gabriel Spacko — UTFPR Campus Santa Helena — CC5SDT 2026-1"
date: \today
lang: pt-BR
---

# 1. Introdução — Pyro5 e RPC Distribuído
(comparativo Java RMI / gRPC / RPyC / Pyro5; justificativa da escolha)

# 2. Arquitetura do Sistema
![Diagrama de componentes](diagrams/arquitetura.png)
(texto explicando 3 processos: Name Server, GameServer, Bridge)

## 2.1 Registro de Callback
![Sequência de registro](diagrams/seq-callback.png)

## 2.2 Entrega de Evento de Jogo
![Sequência de evento](diagrams/seq-game-event.png)

# 3. Demonstração da Aplicação
(capturas de tela das telas; trechos de código relevantes)

# 4. Instalação e Execução
(3 terminais: pyro5 ns, python server/game_server.py, python bridge/bridge.py + npm run dev)
```

---

### `docs/Makefile` (config — NO ANALOG)

**No existing analog.** Pattern from 08-RESEARCH.md Pattern 6:

```makefile
PANDOC   = pandoc
MMDC     = ./node_modules/.bin/mmdc
PUPPETEER_CFG = puppeteer-config.json

.PHONY: pdf diagrams clean

pdf: diagrams relatorio.pdf

diagrams:
	$(MMDC) --puppeteerConfigFile $(PUPPETEER_CFG) -i diagrams/arquitetura.mmd    -o diagrams/arquitetura.png    -b transparent
	$(MMDC) --puppeteerConfigFile $(PUPPETEER_CFG) -i diagrams/seq-callback.mmd   -o diagrams/seq-callback.png   -b transparent
	$(MMDC) --puppeteerConfigFile $(PUPPETEER_CFG) -i diagrams/seq-game-event.mmd -o diagrams/seq-game-event.png -b transparent

relatorio.pdf: relatorio.md diagrams/arquitetura.png diagrams/seq-callback.png diagrams/seq-game-event.png
	$(PANDOC) relatorio.md \
	  -o relatorio.pdf \
	  --pdf-engine=xelatex \
	  -V geometry:margin=2cm \
	  -V fontsize=11pt \
	  -V lang=pt-BR \
	  --highlight-style=tango

clean:
	rm -f relatorio.pdf diagrams/*.png
```

`puppeteer-config.json` content (Pitfall 6 in 08-RESEARCH.md):
```json
{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }
```

---

## Shared Patterns

### Socket event registration + cleanup
**Source:** `frontend/src/pages/GameScreen.tsx` lines 270–296
**Apply to:** `ReconnectionBanner.tsx`, any new component that listens to socket events
```typescript
// Canonical pattern: register inside useEffect, return cleanup
useEffect(() => {
  const handleX = (data: T) => { /* ... */ }
  socket.on('event_name', handleX)
  return () => {
    socket.off('event_name', handleX)
  }
}, [])  // socket is stable singleton — empty deps OK
```

### useRef timer (no timer accumulation)
**Source:** `frontend/src/pages/PostGame.tsx` lines 58–101
**Apply to:** `ReconnectionBanner.tsx`
```typescript
const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
// Always clear before setting:
if (timerRef.current) clearTimeout(timerRef.current)
timerRef.current = setTimeout(() => { /* ... */ }, 3000)
// Clear in cleanup:
return () => { if (timerRef.current) clearTimeout(timerRef.current) }
```

### Card surface (dark panel)
**Source:** `frontend/src/pages/GameScreen.css` lines 99–107
**Apply to:** `PhaseModal.css` surface
```css
background-color: #1a1d27;
border: 1px solid #2d3148;
border-radius: 12px;
padding: 16px;
```

### Primary button (accessible, min-height 44px)
**Source:** `frontend/src/pages/GameScreen.css` lines 185–204
**Apply to:** PhaseModal variant buttons — reuse `.panel-btn-primary` class unchanged
```css
.panel-btn-primary { background-color: #6366f1; min-height: 44px; border-radius: 8px; }
.panel-btn-primary:disabled { opacity: 0.75; cursor: not-allowed; }
```

### Outline-destructive button (skip/spy)
**Source:** `frontend/src/pages/GameScreen.css` lines 209–222
**Apply to:** PhaseModal SPY "Espiar" button, EXCHANGE "Recusar" button — reuse `.panel-btn-skip` class unchanged
```css
.panel-btn-skip { border: 1px solid #ef4444; color: #ef4444; background: transparent; }
```

### 3-threshold color derivation
**Source:** `frontend/src/pages/PostGame.tsx` `voteBarColor()` lines 30–34
**Apply to:** `CountdownDisplay.tsx` `timerColor()` — identical structure, different thresholds/colors
```typescript
function voteBarColor(secondsLeft: number): string {
  if (secondsLeft <= 5) return '#ef4444'
  if (secondsLeft <= 10) return '#eab308'
  return '#6366f1'
}
// CountdownDisplay copies same shape with '#22c55e' for the green state
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/relatorio.md` | utility | — | First Markdown report in the project; no existing docs/ directory |
| `docs/Makefile` | config | — | No Makefile in the project; pandoc/mmdc pipeline is entirely new |

---

## Metadata

**Analog search scope:** `frontend/src/components/`, `frontend/src/pages/`, `frontend/src/`
**Files scanned:** 14 source files read directly
**Pattern extraction date:** 2026-05-16
