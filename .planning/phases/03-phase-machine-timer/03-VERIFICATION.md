---
phase: 03-phase-machine-timer
verified: 2026-05-14T16:00:00Z
status: human_needed
score: 10/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "4-terminal smoke test: run Name Server, GameServer, Bridge, open two browser tabs; create game in Tab A, join in Tab B, start game, verify phase transitions"
    expected: "Both tabs navigate to /game/:roomCode; PhaseHeader shows 'Início' badge with countdown 5s; after 5s badge changes to 'DICA' with 60s countdown; cycle continues automatically through all 7 phases; after last turn both tabs show 'Jogo encerrado' body text"
    why_human: "End-to-end real-time behavior across two browser sessions requires running all four processes; cannot verify socket event delivery, badge rendering, or visual phase transitions programmatically"
  - test: "Verify no stale timer fires during normal operation"
    expected: "Server logs show 'Stale timer suppressed' does NOT appear during a clean automatic run"
    why_human: "Log-line inspection during live run required"
  - test: "Manual advance_phase() via Pyro5 test client during HINT_PHASE"
    expected: "Browser immediately transitions to PALPITE; original 60s timer does NOT fire a second transition 60 seconds later"
    why_human: "Requires live Pyro5 RPC call during a running game session, then waiting 60s to confirm no spurious second transition"
---

# Phase 03: Phase Machine + Timer Verification Report

**Phase Goal:** Implement the turn state machine with phase timers (TurnMachine), wire it into GameServer, extend the bridge with phase-change callbacks, and build the minimal GameScreen UI — delivering a fully automated turn cycle visible in two simultaneous browser sessions.
**Verified:** 2026-05-14T16:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | TurnMachine advances through ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END in order | VERIFIED | `test_phase_cycle` PASSED; PHASE_SEQUENCE constant in `server/turn_machine.py` lines 23-31; test asserts `phases == PHASE_SEQUENCE` exactly |
| 2  | A threading.Timer fires automatically and calls _advance_to after N seconds without any external call | VERIFIED | `test_timer_auto_advance` PASSED; `_timer_handle = threading.Timer(duration, _timer_callback)` at line 128 in `turn_machine.py`; test confirms 2+ events in 0.3s with 0.05s durations |
| 3  | Each advance calls broadcaster.broadcast('phase_changed', {...}) with phase, remaining_seconds, current_turn, max_turns, room_code | VERIFIED | Lines 132-138 build broadcast_data with all 5 keys; line 147 calls `self.broadcaster.broadcast("phase_changed", broadcast_data)` — outside the `with self.lock` block |
| 4  | A stale timer that fires after manual advance is a no-op because _generation has incremented | VERIFIED | `test_generation_counter` PASSED; lines 87-95 in `turn_machine.py` log stale timer and return without broadcasting |
| 5  | After last TURN_END, broadcaster.broadcast('game_ended', {...}) is called and no more phase_changed events emitted | VERIFIED | `test_game_ended_after_last_turn` PASSED; `_compute_next` returns "GAME_ENDED" when `current_turn >= max_turns`; `_advance_to("GAME_ENDED")` calls `broadcast("game_ended", ...)` on line 142 |
| 6  | start_game() creates a TurnMachine for the session, calls turn_machine.start() AFTER broadcasting game_started | VERIFIED | `game_server.py` lines 317-331: TurnMachine created inside lock, `broadcaster.broadcast("game_started", ...)` called first (line 330), then `target_session.turn_machine.start()` (line 331) |
| 7  | advance_phase(player_id) RPC method on GameServer delegates to session.turn_machine.advance_phase_manual() | VERIFIED | `game_server.py` lines 334-359: `advance_phase()` method present, NOT `@oneway`, acquires lock to get `tm` reference, then calls `tm.advance_phase_manual()` outside lock |
| 8  | BridgeCallbackReceiver.on_phase_changed() emits phase_changed Socket.IO event to the correct room | VERIFIED | `bridge/bridge.py` lines 94-102: `on_phase_changed` with `@Pyro5.api.oneway` + `@Pyro5.api.callback`; calls `socketio.emit("phase_changed", data, to=data["room_code"])` |
| 9  | BridgeCallbackReceiver.on_game_ended() emits game_ended Socket.IO event to the correct room | VERIFIED | `bridge/bridge.py` lines 104-112: `on_game_ended` with same decorator pattern; calls `socketio.emit("game_ended", data, to=data["room_code"])` |
| 10 | session.status is set to 'ENDED' when TurnMachine broadcasts game_ended (D-07) | VERIFIED | `game_server.py` lines 271-280: `_set_session_ended()` acquires lock and sets `session.status = "ENDED"`; `start_game()` passes `on_game_ended=lambda: self._set_session_ended(room_code_for_cb)` to TurnMachine; `turn_machine.py` line 144-145 calls `self._on_game_ended()` after `broadcast("game_ended", ...)` with lock released |
| 11 | A full ROUND_START → TURN_END cycle completes without deadlock in two browser sessions | UNCERTAIN | Code structure verified: broadcast-outside-lock pattern correctly implemented; all `broadcaster.broadcast()` calls outside `with self.lock` block; no nested lock acquisition path. Actual 2-browser deadlock-free execution requires human smoke test |

**Score:** 10/11 truths verified (1 requires human confirmation)

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/turn_machine.py` | TurnMachine class with start(), advance_phase_manual(), remaining_seconds; PHASE_SEQUENCE exported | VERIFIED | File exists (192 lines); exports `TurnMachine` and `PHASE_SEQUENCE`; no Pyro5 import; all three public methods present |
| `tests/test_turn_machine.py` | 5 unit tests covering TURN-01 through TURN-04 | VERIFIED | 5 tests present and all PASSED: test_phase_cycle, test_timer_auto_advance, test_manual_advance_cancels_timer, test_generation_counter, test_game_ended_after_last_turn |
| `config.py` | PHASE_DURATIONS dict with 7 entries | VERIFIED | `config.py` lines 24-32: PHASE_DURATIONS with ROUND_START=5, HINT_PHASE=60, GUESS_PHASE=60, EXCHANGE_PHASE=45, SPY_PHASE=30, SCORING_PHASE=15, TURN_END=5 |
| `server/game_server.py` | TurnMachine import; GameSession.turn_machine field; _set_session_ended(); advance_phase() | VERIFIED | All present: import on line 28; `turn_machine` field on line 56; `_set_session_ended()` at lines 271-280; `advance_phase()` at lines 334-359 |
| `bridge/bridge.py` | on_phase_changed and on_game_ended on BridgeCallbackReceiver | VERIFIED | Both methods present lines 94-112 with correct `@Pyro5.api.oneway` + `@Pyro5.api.callback` decorator pair |
| `frontend/src/pages/GameScreen.tsx` | GameScreen component at /game/:roomCode route | VERIFIED | File exists (163 lines); default export `GameScreen`; uses `useParams<{ roomCode: string }>()`; socket lifecycle complete |
| `frontend/src/components/PhaseBadge.tsx` | Pill badge with phase label and color | VERIFIED | File exists (48 lines); PHASE_LABELS and PHASE_COLORS records; aria-label; renders label string with inline styles |
| `frontend/src/components/CountdownDisplay.tsx` | Large countdown number display (28px/600) | VERIFIED | File exists (18 lines); 28px fontSize, fontWeight 600, aria-live="polite", renders "{seconds}s" |
| `frontend/src/App.tsx` | Route /game/:roomCode added | VERIFIED | Line 19: `<Route path="/game/:roomCode" element={<GameScreen />} />`; GameScreen imported on line 7 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `TurnMachine._advance_to()` | `EventBroadcaster.broadcast()` | `self.broadcaster.broadcast()` after `with self.lock` block exits | WIRED | Confirmed: lines 141-147 in `turn_machine.py` are outside the `with self.lock:` block ending at line 138 |
| `TurnMachine._timer_callback closure` | `TurnMachine._generation` | `gen_snapshot` captured before timer creation; checked in `_advance_to(from_timer=True)` | WIRED | Line 103: `gen_snapshot = self._generation`; line 125: passed as `expected_generation=gen_snapshot`; lines 89-95: mismatch check |
| `game_server.py start_game()` | `TurnMachine.start()` | `target_session.turn_machine.start()` called after `broadcaster.broadcast("game_started", ...)` | WIRED | Line 331: `target_session.turn_machine.start()` appears after line 330: `self.broadcaster.broadcast("game_started", broadcast_data)` |
| `bridge/bridge.py BridgeCallbackReceiver.on_phase_changed` | `socketio.emit('phase_changed', data, to=data['room_code'])` | `@Pyro5.api.oneway @Pyro5.api.callback` | WIRED | Line 99: `socketio.emit("phase_changed", data, to=data["room_code"])` inside `on_phase_changed` |
| `GameScreen.tsx useEffect` | `socket.on('phase_changed', handlePhaseChanged)` | `socket.emit('join_room', { room_code: roomCode })` on mount | WIRED | Lines 29, 56, 64: join_room on mount; `socket.on` and `socket.off` for phase_changed |
| `GameScreen.tsx setInterval` | `setRemainingSeconds(secs - 1)` | `intervalRef.current = setInterval(() => ..., 1000)` | WIRED | Lines 42-45: `setInterval` at 1000ms; closure decrements `secs` and calls `setRemainingSeconds(secs)` |
| `bridge/bridge.py handle_join_room` | `join_room(room_code)` | `@socketio.on("join_room")` handler | WIRED | Lines 301-314: handler present; calls Flask-SocketIO `join_room(room_code)` so GameScreen clients receive room-scoped events |
| `game_server.py _set_session_ended()` via `on_game_ended` lambda | `session.status = "ENDED"` | Lambda closure in `start_game()` passed as `on_game_ended` to TurnMachine | WIRED | Lines 316-322 in `game_server.py`; `turn_machine.py` line 144-145 calls `self._on_game_ended()` after game_ended broadcast |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `GameScreen.tsx` | `currentPhase`, `remainingSeconds`, `currentTurn`, `maxTurns` | `phase_changed` Socket.IO event from bridge | Yes — data originates from TurnMachine's `_advance_to()` which reads `config.PHASE_DURATIONS` and live `current_turn` state | FLOWING |
| `PhaseBadge.tsx` | `phase` prop | Passed from `GameScreen.tsx` `currentPhase` state | Yes — state set from `data.phase` in `handlePhaseChanged` callback | FLOWING |
| `CountdownDisplay.tsx` | `seconds` prop | Passed from `GameScreen.tsx` `remainingSeconds` state | Yes — initially set from `data.remaining_seconds`, then decremented by local `setInterval` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| TurnMachine imports cleanly (no Pyro5 dependency) | `python -c "from server.turn_machine import TurnMachine, PHASE_SEQUENCE; print('OK')"` | OK | PASS |
| PHASE_DURATIONS has 7 entries with correct values | `python -c "import config; assert len(config.PHASE_DURATIONS)==7; assert config.PHASE_DURATIONS['HINT_PHASE']==60; print('OK')"` | OK | PASS |
| GameServer imports with TurnMachine, advance_phase present | `python -c "from server.game_server import GameServer; gs=GameServer(); assert 'advance_phase' in dir(gs); print('OK')"` | OK | PASS |
| All 5 unit tests pass | `python -m pytest tests/test_turn_machine.py -v` | 5 passed in 0.95s | PASS |
| Full test suite passes | `python -m pytest tests/ -q` | 15 passed in 3.34s | PASS |
| Frontend builds with 0 TypeScript errors | `cd frontend && npm run build` | `built in 611ms`, 0 errors | PASS |

### Probe Execution

No probe scripts found at `scripts/*/tests/probe-*.sh`. Not a migration/tooling phase — skipped per Step 7c rule.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TURN-01 | 03-01, 03-02, 03-03 | Server controls state machine: WAITING → ROUND_START → HINT_PHASE → GUESS_PHASE → EXCHANGE_PHASE → SPY_PHASE → SCORING_PHASE → TURN_END | PARTIALLY SATISFIED | Phase sequence ROUND_START through TURN_END implemented and tested. DISTRIBUTING phase from REQUIREMENTS.md TURN-01 definition is absent from implementation — Phase 03 CONTEXT.md (Claude's Discretion) explicitly scoped it out; Phase 04 will add image distribution at the TURN_END→HINT_PHASE transition. ROADMAP Phase 3 success criteria do not mention DISTRIBUTING. |
| TURN-02 | 03-01 | Each phase has configurable timer (30-60s) managed by threading.Timer; auto-advances on expiry | SATISFIED | `test_timer_auto_advance` PASSED; `config.PHASE_DURATIONS` with 7 entries; `threading.Timer` in `_advance_to()` line 128 |
| TURN-03 | 03-01, 03-03 | Phase transition sends PHASE_CHANGED broadcast to all clients | SATISFIED | `broadcast("phase_changed", broadcast_data)` line 147; bridge `on_phase_changed` forwards via `socketio.emit`; GameScreen listens and re-renders |
| TURN-04 | 03-01 | Timer uses generation counter to avoid stale timer race condition | SATISFIED | `_generation` counter incremented on every advance; `test_generation_counter` PASSED; stale check lines 87-95 |

**Note on TURN-01 and DISTRIBUTING:** REQUIREMENTS.md v1 TURN-01 includes a DISTRIBUTING phase. The Phase 03 context document deliberately excluded it, the ROADMAP Phase 3 success criteria do not reference it, and the PLAN frontmatter maps TURN-01 as satisfied without DISTRIBUTING. This is a known partial satisfaction — the DISTRIBUTING step will be wired in Phase 04 when image assignment is implemented. The REQUIREMENTS.md traceability table keeps TURN-01 as "Pending", which is correct.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | No TBD/FIXME/XXX markers; no return null stubs; no placeholder text in rendered paths | — | — |

No debt markers or stub patterns detected in any phase-modified file.

### Human Verification Required

#### 1. Full End-to-End Smoke Test (Two Browser Sessions)

**Test:** Run 4 terminals from project root with venv activated:
- Terminal 1: `pyro5-ns --host 127.0.0.1`
- Terminal 2: `python server/game_server.py`
- Terminal 3: `python bridge/bridge.py`
- Open TWO browser tabs at http://127.0.0.1:5000

Tab A: Create game (any nickname, 3 turns). Tab B: Join using room code from Tab A. Tab A: Click "Iniciar Jogo".

**Expected:** Both tabs navigate to `/game/:roomCode`; PhaseHeader appears with badge showing "Início" and countdown "5s"; after 5 seconds badge changes to "DICA" with countdown "60s" — no page reload; phase transitions continue automatically; after 3 full turns both tabs show "Jogo encerrado. Aguardando tela de resultados..."

**Why human:** Real-time Socket.IO event delivery, React rendering, and cross-browser phase synchronization cannot be verified programmatically without running the full process stack.

#### 2. No-Deadlock Confirmation

**Test:** During the smoke test above, confirm the full cycle (all phases across all 3 turns) completes without the server freezing, the bridge stopping to emit events, or either browser tab becoming unresponsive.

**Expected:** Continuous phase_changed events logged in Terminal 3 bridge output; no silent freeze; no Python traceback in any terminal.

**Why human:** Deadlock manifests at runtime under actual threading conditions; static analysis cannot rule it out completely (though the broadcast-outside-lock pattern is correctly implemented).

#### 3. Manual Advance Cancels Timer (Generation Counter Confirmation)

**Test:** While a game is in HINT_PHASE (60s timer running), run in Terminal 4:
```python
import Pyro5.api, config
with Pyro5.api.Proxy(f'PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}') as p:
    result = p.advance_phase(None)
    print('advance_phase returned:', result)
```
Wait 60+ seconds after the manual advance.

**Expected:** Browser immediately transitions to "PALPITE"; `advance_phase` returns `True`; the original HINT_PHASE 60s timer does NOT fire a second transition after 60 seconds. Server logs should show "Stale timer suppressed" during normal auto-advance flow but NOT after a clean manual advance.

**Why human:** Requires live Pyro5 connection and 60-second observation window.

### Gaps Summary

No BLOCKER gaps were found. All must-have truths are either VERIFIED by code inspection and passing tests, or UNCERTAIN pending live smoke test (which is expected for an end-to-end real-time behavior).

The smoke test checkpoint in Plan 03-03 Task 2 is explicitly marked as a `gate: blocking` human-verify step in the plan — this was known at planning time and is the expected path to phase completion.

The DISTRIBUTING phase absence in TURN-01 is a deliberate Phase 03 scoping decision documented in CONTEXT.md; it does not block the Phase 03 goal as defined in ROADMAP.md.

---

_Verified: 2026-05-14T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
