# Phase 7: Reconnection + End-of-Game — Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 7 (5 modified, 2 new)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `bridge/bridge.py` | middleware/service | event-driven, request-response | `bridge/bridge.py` (existing) | self (modification) |
| `server/game_server.py` | service | request-response, event-driven | `server/game_server.py` (existing) | self (modification) |
| `server/event_broadcaster.py` | service | event-driven | `server/event_broadcaster.py` (existing) | self (modification) |
| `frontend/src/pages/GameScreen.tsx` | component/page | event-driven, request-response | `frontend/src/pages/GameScreen.tsx` (existing) | self (modification) |
| `frontend/src/App.tsx` | config/router | request-response | `frontend/src/App.tsx` (existing) | self (modification) |
| `frontend/src/pages/PostGame.tsx` | component/page | request-response, event-driven | `frontend/src/pages/GameScreen.tsx` | role-match |
| `frontend/src/components/ChatPanel.tsx` | component | event-driven | `frontend/src/components/CountdownDisplay.tsx` | role-match |

---

## Pattern Assignments

### `bridge/bridge.py` — modifications (middleware, event-driven + request-response)

**Analog:** `bridge/bridge.py` (self, lines 557–570 for `handle_disconnect`; lines 343–386 for handler pattern; lines 42–237 for `BridgeCallbackReceiver`)

#### Imports pattern (lines 1–16, 20–25) — no new imports needed

```python
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Pyro5.api
import Pyro5.errors
from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, join_room

import config
```

#### Existing module-level state to extend (lines 261–269)

```python
# Existing:
_sid_to_player: dict = {}
_player_to_sid: dict = {}
_sid_lock = threading.Lock()
_cb_uri = ""

# ADD for D-01 grace period:
_pending_leaves: dict = {}          # sid -> (threading.Timer, player_id)
_pending_leaves_lock = threading.Lock()
```

#### Grace-period disconnect pattern — REPLACES lines 557–570

**Copy from:** `bridge/bridge.py:404–425` (start_game pattern — SID lookup + proxy call + error path); `server/turn_machine.py:193–195` (threading.Timer pattern)

```python
@socketio.on("disconnect")
def handle_disconnect(reason):
    with _sid_lock:
        player_id = _sid_to_player.pop(request.sid, None)
        if player_id:
            _player_to_sid.pop(player_id, None)
    sid = request.sid
    if player_id:
        def do_leave():
            with _pending_leaves_lock:
                _pending_leaves.pop(sid, None)
            try:
                proxy = get_game_server_proxy()
                proxy.leave_game(player_id)
                print(f"[BRIDGE] disconnect: player {player_id} left (reason: {reason})", flush=True)
            except Exception as exc:
                print(f"[BRIDGE] leave_game failed for {player_id}: {exc}", flush=True)
        t = threading.Timer(5.0, do_leave)
        t.daemon = True
        with _pending_leaves_lock:
            _pending_leaves[sid] = (t, player_id)
        t.start()
```

#### Reconnect handler — new @socketio.on handler

**Copy from:** `bridge/bridge.py:366–386` (`handle_join_game` — SID registration + join_room + proxy call pattern)

```python
@socketio.on("reconnect_game")
def handle_reconnect_game(data):
    player_id = (data or {}).get("player_id", "")
    room_code = (data or {}).get("room_code", "")
    if not player_id or not room_code:
        return {"error": "missing fields"}
    # Cancel any pending leave for this player_id (keyed by old SID)
    with _pending_leaves_lock:
        for old_sid, (timer, pid) in list(_pending_leaves.items()):
            if pid == player_id:
                timer.cancel()
                del _pending_leaves[old_sid]
                break
    # Re-register new SID mapping
    with _sid_lock:
        _sid_to_player[request.sid] = player_id
        _player_to_sid[player_id] = request.sid
    join_room(room_code)
    proxy = get_game_server_proxy()
    result = proxy.reconnect_player(player_id, room_code, _cb_uri)
    print(f"[BRIDGE] reconnect_game: player {player_id} reconnected to room {room_code}", flush=True)
    return result
```

#### send_chat handler — new @socketio.on handler

**Copy from:** `bridge/bridge.py:428–438` (`handle_submit_hint` — SID-to-player_id lookup + proxy forwarding pattern)

```python
@socketio.on("send_chat")
def handle_send_chat(data):
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "sessao nao encontrada"}
    proxy = get_game_server_proxy()
    result = proxy.send_chat(player_id, (data or {}).get("message", ""))
    return result
```

#### submit_vote handler — new @socketio.on handler

**Copy from:** `bridge/bridge.py:428–438` (same SID-lookup + proxy-call pattern)

```python
@socketio.on("submit_vote")
def handle_submit_vote(data):
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "sessao nao encontrada"}
    proxy = get_game_server_proxy()
    result = proxy.submit_vote(player_id, bool((data or {}).get("continue_game", False)))
    return result
```

#### New BridgeCallbackReceiver methods — append to class (lines 42–237)

**Copy from:** `bridge/bridge.py:84–92` (`on_host_changed` — room-broadcast pattern) and `bridge/bridge.py:104–112` (`on_game_ended`)

```python
@Pyro5.api.oneway
@Pyro5.api.callback
def on_chat_message(self, data: dict):
    try:
        socketio.emit("chat_message", data, to=data["room_code"])
        print(f"[BRIDGE] chat_message emitted to room {data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_chat_message: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_player_left(self, data: dict):
    try:
        socketio.emit("player_left", data, to=data["room_code"])
        print(f"[BRIDGE] player_left emitted player={data.get('player_name')} room={data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_player_left: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_vote_started(self, data: dict):
    try:
        socketio.emit("vote_started", data, to=data["room_code"])
        print(f"[BRIDGE] vote_started emitted to room {data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_vote_started: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_vote_update(self, data: dict):
    try:
        socketio.emit("vote_update", data, to=data["room_code"])
        print(f"[BRIDGE] vote_update emitted to room {data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_vote_update: {exc}", flush=True)

@Pyro5.api.oneway
@Pyro5.api.callback
def on_game_restarting(self, data: dict):
    try:
        socketio.emit("game_restarting", data, to=data["room_code"])
        print(f"[BRIDGE] game_restarting emitted to room {data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_game_restarting: {exc}", flush=True)
```

---

### `server/event_broadcaster.py` — modifications (service, event-driven)

**Analog:** `server/event_broadcaster.py` (self — lines 20–84)

#### Existing `__init__` and `broadcast()` to extend

**Copy from:** `server/event_broadcaster.py:20–22` (`__init__` — add `failure_counts` alongside `callbacks`) and lines 55–84 (broadcast iteration — extend transient failure branch)

```python
# In __init__, add after self.lock = threading.Lock():
self.failure_counts: dict = {}   # player_id -> consecutive failure count

# In broadcast(), permanent-failure branch (lines 71–75) — replace:
except (ConnectionRefusedError, OSError) as e:
    print(f"[EventBroadcaster] Permanent callback failure for {player_id}: {e}", flush=True)
    failed.append(player_id)

# In broadcast(), transient-failure branch (lines 76–80) — replace:
except Exception as e:
    count = self.failure_counts.get(player_id, 0) + 1
    self.failure_counts[player_id] = count
    print(f"[EventBroadcaster] Transient callback error for {player_id} (count={count}): {e}", flush=True)
    if count >= 3:
        failed.append(player_id)

# On successful delivery, reset consecutive counter — add after method() call succeeds:
self.failure_counts.pop(player_id, None)

# broadcast() must return the list of failed player_ids so GameServer can
# process PLAYER_LEFT after releasing its own lock. Change return type:
# return failed   (add at end of broadcast() after cleanup block)
```

---

### `server/game_server.py` — modifications (service, request-response + event-driven)

**Analog:** `server/game_server.py` (self — multiple methods)

#### `GameSession` dataclass — add fields (lines 47–77)

**Copy from:** `server/game_server.py:47–62` (GameSession dataclass field pattern)

```python
# Add to GameSession after accumulated_scores field:
turn_score_history: list = dataclasses.field(default_factory=list)
# Each entry: {"turn": int, "scores": {player_id: delta}}
# Appended in on_scoring_phase callback.

vote_record: object = dataclasses.field(default=None, repr=False)
# Set to a VoteRecord dataclass when start_vote() is called; cleared on restart/end.
```

#### `VoteRecord` dataclass — new, add near `GameSession`

**Copy from:** `server/turn_machine.py:98–104` (TurnMachine threading.Timer + generation counter pattern)

```python
@dataclasses.dataclass
class VoteRecord:
    votes: dict = dataclasses.field(default_factory=dict)  # player_id -> bool
    generation: int = 0
    timer: object = dataclasses.field(default=None, repr=False)
```

#### `reconnect_player()` — new RPC method

**Copy from:** `server/game_server.py:231–290` (`join_game` — lock pattern, player lookup, broadcaster.register_callback, return dict) and `server/game_server.py:321–357` (`get_player_view` — tail call for state return)

```python
@Pyro5.api.expose
def reconnect_player(self, player_id: str, room_code: str, callback_uri: str) -> dict:
    """Re-register callback URI for a player already in the session (D-02)."""
    with self.lock:
        room = self._player_to_room.get(player_id)
        if room != room_code:
            return {"error": "player not in session"}
        session = self.sessions.get(room_code)
        if session is None:
            return {"error": "session not found"}
        for p in session.players:
            if p.player_id == player_id:
                p.callback_uri = callback_uri
                break
    self.broadcaster.register_callback(player_id, callback_uri)
    return self.get_player_view(room_code, player_id)
```

#### `send_chat()` — new RPC method

**Copy from:** `server/game_server.py:519–565` (`submit_hint` — lock-acquire-then-broadcast-outside pattern); `server/game_server.py:897–950` (lock → snapshot data → release → broadcast)

```python
@Pyro5.api.expose
def send_chat(self, player_id: str, message: str) -> dict:
    """Broadcast a chat message to all players (CHAT-01)."""
    import time as _time
    with self.lock:
        room_code = self._player_to_room.get(player_id)
        player_name = None
        if room_code:
            session = self.sessions.get(room_code)
            if session:
                for p in session.players:
                    if p.player_id == player_id:
                        player_name = p.player_name
                        break
    if room_code is None or player_name is None:
        return {"error": "player not in session"}
    self.broadcaster.broadcast("chat_message", {
        "player_id": player_id,
        "player_name": player_name,
        "message": str(message)[:200],
        "timestamp": _time.time(),
        "room_code": room_code,
    })
    return {"ok": True}
```

#### `start_vote()` — new internal method called after last TURN_END

**Copy from:** `server/turn_machine.py:185–195` (threading.Timer + generation counter pattern); `server/game_server.py:897–950` (lock → snapshot → release → broadcast)

```python
def _start_vote(self, room_code: str):
    """Start the 30s play-again vote after the last turn (POSTGAME-02)."""
    import time as _time
    with self.lock:
        session = self.sessions.get(room_code)
        if session is None:
            return
        if session.vote_record is not None:
            return  # vote already running
        vote = VoteRecord(generation=1)
        session.vote_record = vote
        gen_snapshot = vote.generation
        player_count = len(session.players)
        broadcast_data = {
            "room_code": room_code,
            "duration_seconds": 30,
            "player_count": player_count,
        }
    # Schedule timer OUTSIDE lock — follows TurnMachine pattern
    def _on_vote_timeout():
        self._resolve_vote(room_code, gen_snapshot)
    t = threading.Timer(30.0, _on_vote_timeout)
    t.daemon = True
    with self.lock:
        session = self.sessions.get(room_code)
        if session and session.vote_record and session.vote_record.generation == gen_snapshot:
            session.vote_record.timer = t
    t.start()
    self.broadcaster.broadcast("vote_started", broadcast_data)
```

#### `submit_vote()` — new RPC method

**Copy from:** `server/game_server.py:570–608` (`submit_guess` — validation + lock + broadcast-outside pattern)

```python
@Pyro5.api.expose
def submit_vote(self, player_id: str, continue_game: bool) -> dict:
    """Record a player's play-again vote (POSTGAME-03/04)."""
    resolve_now = False
    gen_snapshot = None
    room_code_snap = None
    with self.lock:
        room_code = self._player_to_room.get(player_id)
        if not room_code:
            return {"error": "player not in session"}
        session = self.sessions.get(room_code)
        if session is None or session.vote_record is None:
            return {"error": "no vote in progress"}
        vote = session.vote_record
        if player_id in vote.votes:
            return {"ok": True, "duplicate": True}
        vote.votes[player_id] = continue_game
        total = len(session.players)
        yes_count = sum(1 for v in vote.votes.values() if v)
        # Early resolution: all players have voted
        if len(vote.votes) >= total:
            resolve_now = True
            gen_snapshot = vote.generation
            room_code_snap = room_code
        broadcast_data = {
            "room_code": room_code,
            "yes_count": yes_count,
            "votes_cast": len(vote.votes),
            "total": total,
        }
    self.broadcaster.broadcast("vote_update", broadcast_data)
    if resolve_now:
        self._resolve_vote(room_code_snap, gen_snapshot)
    return {"ok": True}
```

#### `_resolve_vote()` — new internal method

**Copy from:** `server/turn_machine.py:133–142` (stale-timer generation check); `server/game_server.py:370–403` (`_assign_images_for_turn` — lock → assignments → release → private sends)

```python
def _resolve_vote(self, room_code: str, expected_generation: int):
    """Tally vote and either restart or end the game (POSTGAME-03/04)."""
    broadcast_restart = None
    broadcast_ended = None
    with self.lock:
        session = self.sessions.get(room_code)
        if session is None or session.vote_record is None:
            return
        vote = session.vote_record
        if vote.generation != expected_generation:
            return  # stale timer guard (same as TurnMachine TURN-04)
        if vote.timer is not None:
            vote.timer.cancel()
        total = len(session.players)
        yes_count = sum(1 for v in vote.votes.values() if v)
        majority = yes_count > total / 2
        session.vote_record = None  # clear vote state
        if majority:
            session.status = "IN_PROGRESS"
            self._used_images_this_game.pop(room_code, None)  # fresh image pool
            broadcast_restart = {"room_code": room_code}
        else:
            session.status = "ENDED"
            broadcast_ended = {
                "room_code": room_code,
                "final_scores": list(session.accumulated_scores.items()),
                "turn_score_history": list(session.turn_score_history),
            }
    if broadcast_restart:
        self.broadcaster.broadcast("game_restarting", broadcast_restart)
        self._assign_images_for_turn(room_code)
        # Rebuild TurnMachine for new game round
        with self.lock:
            session = self.sessions.get(room_code)
            if session:
                player_ids = [p.player_id for p in session.players]
                session.accumulated_scores.clear()
                session.turn_score_history.clear()
                session.turn_machine = TurnMachine(
                    room_code=room_code,
                    max_turns=session.max_turns,
                    broadcaster=self.broadcaster,
                    player_ids=player_ids,
                    on_game_ended=lambda: self._set_session_ended(room_code),
                    on_round_start=lambda: None,
                    on_hint_phase_start=lambda: self._assign_images_for_turn(room_code) or {},
                    on_scoring_phase=lambda ts: self._on_scoring_phase(room_code, ts),
                )
        with self.lock:
            session = self.sessions.get(room_code)
            if session and session.turn_machine:
                tm = session.turn_machine
        tm.start()
    elif broadcast_ended:
        self.broadcaster.broadcast("game_ended", broadcast_ended)
        with self.lock:
            self.sessions.pop(room_code, None)
```

#### `leave_game()` modification — handle PLAYER_LEFT from EventBroadcaster failures (D-08)

**Copy from:** `server/game_server.py:897–952` (existing `leave_game` — broadcast outside lock); `server/event_broadcaster.py:40–84` (broadcast return value extended to return `failed` list)

The key change: `leave_game()` is the single code path for player removal. No direct coupling to `EventBroadcaster` needed if `broadcast()` returns `failed` list. GameServer processes removal via a new `_remove_failed_players()` method:

```python
def _remove_failed_players(self, failed_player_ids: list):
    """Called after broadcast() returns failed list — removes players and broadcasts PLAYER_LEFT.

    Must be called OUTSIDE any GameServer lock (called after broadcaster.broadcast()).
    """
    for player_id in failed_player_ids:
        player_name_snap = None
        room_code_snap = None
        with self.lock:
            room_code = self._player_to_room.pop(player_id, None)
            if room_code is None:
                continue
            session = self.sessions.get(room_code)
            if session is None:
                continue
            for p in session.players:
                if p.player_id == player_id:
                    player_name_snap = p.player_name
                    break
            session.players = [p for p in session.players if p.player_id != player_id]
            self.broadcaster.unregister_callback(player_id)
            room_code_snap = room_code
        if player_name_snap and room_code_snap:
            self.broadcaster.broadcast("player_left", {
                "player_id": player_id,
                "player_name": player_name_snap,
                "room_code": room_code_snap,
            })
```

---

### `frontend/src/pages/GameScreen.tsx` — modifications (component/page, event-driven)

**Analog:** `frontend/src/pages/GameScreen.tsx` (self — lines 1–244)

#### Reconnect logic on mount — modify `useEffect` (lines 137–244)

**Copy from:** `frontend/src/pages/GameScreen.tsx:173–202` (existing `socket.emit('join_room', ...)` + callback with `applyPhase`)

Replace the `socket.emit('join_room', ...)` block at line 173 with a conditional reconnect check:

```typescript
// At the top of the useEffect, before socket.emit:
const storedPlayerId = localStorage.getItem('player_id') ?? ''

const handleReconnect = (data: JoinRoomPayload) => {
  if (data?.error) { setConnectionError(String(data.error)); return }
  setConnectionError(null)
  if (data?.players) {
    setPlayers(data.players)
    localStorage.setItem('players', JSON.stringify(data.players))
    setTotalPlayers(data.players.length)
  }
  if (data?.object_assignment) setMyObjectAssignment(data.object_assignment)
  if (data?.status === 'ENDED') { setGameEnded(true); return }
  if (data?.phase) {
    applyPhase({
      phase: data.phase,
      remaining_seconds: data.remaining_seconds ?? 0,
      current_turn: data.current_turn ?? 1,
      max_turns: data.max_turns ?? 1,
      room_code: roomCode ?? '',
    })
  }
}

if (storedPlayerId && roomCode) {
  socket.emit('reconnect_game', { player_id: storedPlayerId, room_code: roomCode }, handleReconnect)
} else {
  socket.emit('join_room', { room_code: roomCode, player_id: myPlayerId }, handleReconnect)
}
```

#### New event handlers to register in `useEffect`

**Copy from:** `frontend/src/pages/GameScreen.tsx:204–230` (handlePhaseChanged / handleGameEnded listener registration pattern)

```typescript
// Add to useEffect socket.on block:
const handlePlayerLeft = (data: { player_id: string; player_name: string }) => {
  addToast(`${data.player_name} saiu da partida`)
  setPlayers((prev) => prev.filter((p) => p.player_id !== data.player_id))
}
const handleGameRestarting = () => {
  navigate(`/game/${roomCode}`)  // re-mount with fresh state
}
const handleChatMessage = (data: ChatMessage) => {
  setChatMessages((prev) => [...prev, data])
}
const handleVoteStarted = (data: VoteStartedPayload) => {
  // navigate to PostGame, which renders vote UI
  navigate(`/postgame/${roomCode}`)
}

socket.on('player_left', handlePlayerLeft)
socket.on('game_restarting', handleGameRestarting)
socket.on('chat_message', handleChatMessage)
socket.on('vote_started', handleVoteStarted)

// Cleanup:
socket.off('player_left', handlePlayerLeft)
socket.off('game_restarting', handleGameRestarting)
socket.off('chat_message', handleChatMessage)
socket.off('vote_started', handleVoteStarted)
```

#### game_ended handler — replace static setGameEnded with navigation

**Copy from:** `frontend/src/pages/Lobby.tsx:46–54` (handleGameStarted — navigate pattern)

```typescript
// Replace handleGameEnded (lines 217–223):
const handleGameEnded = (_data: object) => {
  if (intervalRef.current) {
    clearInterval(intervalRef.current)
    intervalRef.current = null
  }
  navigate(`/postgame/${roomCode}`)
}
```

---

### `frontend/src/App.tsx` — modification (config/router)

**Analog:** `frontend/src/App.tsx` (self — lines 1–22)

#### Add PostGame route

**Copy from:** `frontend/src/App.tsx:1–22` (existing import + Route pattern)

```typescript
import PostGame from './pages/PostGame'

// Add route inside <Routes>:
<Route path="/postgame/:roomCode" element={<PostGame />} />
```

---

### `frontend/src/pages/PostGame.tsx` — NEW (component/page, request-response + event-driven)

**Analog:** `frontend/src/pages/GameScreen.tsx` (role-match — page with socket listeners, useParams, useNavigate, useEffect lifecycle)

#### Imports pattern — copy from GameScreen.tsx lines 1–6

```typescript
import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import socket from '../socket'
```

#### Interface definitions — copy structure from GameScreen.tsx lines 8–60

```typescript
interface ScoreEntry {
  player_id: string
  player_name: string
  total: number
}

interface TurnScoreEntry {
  turn: number
  scores: Record<string, number>  // player_id -> delta
}

interface VoteStartedPayload {
  room_code: string
  duration_seconds: number
  player_count: number
}

interface VoteUpdatePayload {
  room_code: string
  yes_count: number
  votes_cast: number
  total: number
}
```

#### Component structure — copy from GameScreen.tsx lines 113–136 (state declarations)

```typescript
export default function PostGame() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const navigate = useNavigate()
  const myPlayerId = localStorage.getItem('player_id') ?? ''

  const [finalScores, setFinalScores] = useState<ScoreEntry[]>([])
  const [turnHistory, setTurnHistory] = useState<TurnScoreEntry[]>([])
  const [voteActive, setVoteActive] = useState(false)
  const [voteSecondsLeft, setVoteSecondsLeft] = useState(30)
  const [myVoteSubmitted, setMyVoteSubmitted] = useState(false)
  const [yesCount, setYesCount] = useState(0)
  const [votesCast, setVotesCast] = useState(0)
  const [totalPlayers, setTotalPlayers] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
```

#### useEffect lifecycle — copy from GameScreen.tsx lines 137–244 (socket connect + on + cleanup pattern)

```typescript
  useEffect(() => {
    if (!socket.connected) socket.connect()

    // Receive final scores from game_ended event data passed via router state,
    // or subscribe to vote_started if navigated before game_ended fires.
    const handleVoteStarted = (data: VoteStartedPayload) => {
      setVoteActive(true)
      setVoteSecondsLeft(data.duration_seconds)
      setTotalPlayers(data.player_count)
      let secs = data.duration_seconds
      intervalRef.current = setInterval(() => {
        secs = Math.max(0, secs - 1)
        setVoteSecondsLeft(secs)
        if (secs === 0 && intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }, 1000)
    }
    const handleVoteUpdate = (data: VoteUpdatePayload) => {
      setYesCount(data.yes_count)
      setVotesCast(data.votes_cast)
      setTotalPlayers(data.total)
    }
    const handleGameRestarting = () => navigate(`/game/${roomCode}`)
    const handleGameEnded = (data: { final_scores?: ScoreEntry[]; turn_score_history?: TurnScoreEntry[] }) => {
      if (data.final_scores) setFinalScores(data.final_scores)
      if (data.turn_score_history) setTurnHistory(data.turn_score_history)
      setVoteActive(false)
    }

    socket.on('vote_started', handleVoteStarted)
    socket.on('vote_update', handleVoteUpdate)
    socket.on('game_restarting', handleGameRestarting)
    socket.on('game_ended', handleGameEnded)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      socket.off('vote_started', handleVoteStarted)
      socket.off('vote_update', handleVoteUpdate)
      socket.off('game_restarting', handleGameRestarting)
      socket.off('game_ended', handleGameEnded)
    }
  }, [roomCode, navigate])
```

#### Vote submission — copy from GameScreen.tsx lines 250–267 (submitHint/skipGuess pattern)

```typescript
  function submitVote(continueGame: boolean) {
    if (myVoteSubmitted) return
    socket.emit('submit_vote', { continue_game: continueGame }, () => undefined)
    setMyVoteSubmitted(true)
  }
```

---

### `frontend/src/components/ChatPanel.tsx` — NEW (component, event-driven)

**Analog:** `frontend/src/components/CountdownDisplay.tsx` (role-match — pure presentational component with props); `frontend/src/pages/GameScreen.tsx:269–360` (phase panel JSX structure for input+button pattern)

#### Component structure — copy from CountdownDisplay.tsx (props interface + default export)

```typescript
import { useRef, useEffect } from 'react'

interface ChatMessage {
  player_id: string
  player_name: string
  message: string
  timestamp: number
}

interface ChatPanelProps {
  messages: ChatMessage[]
  myPlayerId: string
  onSend: (message: string) => void
  disabled?: boolean
}

export default function ChatPanel({ messages, myPlayerId, onSend, disabled }: ChatPanelProps) {
  // ...
}
```

#### Input + submit pattern — copy from GameScreen.tsx lines 279–302 (HINT_PHASE label/input/button)

The critical D-04 constraint: use visually distinct CSS class (`chat-panel--input`) vs. game action inputs (`panel-input`). Label must read "Mensagem de chat" explicitly.

```tsx
<section className="chat-panel" aria-label="Chat">
  <h3 className="chat-panel__title" style={{ color: '#94a3b8' }}>Chat</h3>
  <div className="chat-panel__messages" ref={messagesEndRef}>
    {messages.map((msg, i) => (
      <div key={i} className={`chat-message ${msg.player_id === myPlayerId ? 'chat-message--mine' : ''}`}>
        <span className="chat-message__author">{msg.player_name}</span>
        <span className="chat-message__text">{msg.message}</span>
      </div>
    ))}
  </div>
  <label className="chat-panel__field">
    <span className="chat-panel__label-text" style={{ color: '#94a3b8' }}>Mensagem de chat</span>
    <input
      type="text"
      maxLength={200}
      value={chatInput}
      onChange={(e) => setChatInput(e.target.value)}
      disabled={disabled}
      aria-label="Mensagem de chat"
      placeholder="Digite uma mensagem..."
      className="chat-panel__input"   /* DISTINCT class from panel-input */
    />
  </label>
  <button
    type="button"
    onClick={handleSend}
    disabled={!chatInput.trim() || disabled}
    className="chat-panel__btn"       /* DISTINCT class from panel-btn-primary */
  >
    Enviar
  </button>
</section>
```

---

## Shared Patterns

### RLock + broadcast-outside-lock (all server modifications)

**Source:** `server/game_server.py:897–952` (`leave_game`) and `server/turn_machine.py:133–209` (`_advance_to`)
**Apply to:** All new `game_server.py` methods: `reconnect_player`, `send_chat`, `_start_vote`, `submit_vote`, `_resolve_vote`, `_remove_failed_players`

Pattern:
1. Enter `with self.lock:` — read/mutate state, snapshot broadcast payload
2. Exit lock block
3. Call `self.broadcaster.broadcast(...)` or `self.broadcaster.send_to_player(...)` AFTER lock exits

### Return dict from @Pyro5.api.expose methods

**Source:** `server/game_server.py:231–290`, `server/game_server.py:570–608`
**Apply to:** All new exposed methods: `reconnect_player`, `send_chat`, `submit_vote`

Pattern: Return `{"ok": True, ...}` on success; `{"error": "reason"}` on failure. Never raise exceptions from RPC methods (they get serialized and lost on the wire for non-builtin exception types).

### threading.Timer + generation counter (stale-timer guard)

**Source:** `server/turn_machine.py:98–103` (generation field), `server/turn_machine.py:133–142` (stale-timer guard), `server/turn_machine.py:185–195` (timer creation + daemon=True)
**Apply to:** Grace-period timers in `bridge/bridge.py` (keyed by SID); vote timer in `_start_vote` / `_resolve_vote`

### Socket.IO listener registration + cleanup

**Source:** `frontend/src/pages/GameScreen.tsx:204–244`
**Apply to:** `PostGame.tsx` useEffect, `GameScreen.tsx` new handlers

Pattern:
```typescript
socket.on('event_name', handler)
return () => { socket.off('event_name', handler) }
```
Always unregister in cleanup function to prevent duplicate listeners on remount.

### localStorage persistence

**Source:** `frontend/src/pages/GameScreen.tsx:115`, `frontend/src/pages/Lobby.tsx:32–33`
**Apply to:** `PostGame.tsx` (read `player_id` and `players` from localStorage)

Pattern:
```typescript
const myPlayerId = localStorage.getItem('player_id') ?? ''
```

### useNavigate for programmatic navigation

**Source:** `frontend/src/pages/Lobby.tsx:23`, `frontend/src/pages/Lobby.tsx:46–54` (handleGameStarted navigate)
**Apply to:** `GameScreen.tsx` (game_ended → navigate to /postgame/:roomCode), `PostGame.tsx` (game_restarting → navigate to /game/:roomCode; game truly ended → navigate to /)

### Per-thread Pyro5 proxy

**Source:** `bridge/bridge.py:279–289` (`get_game_server_proxy`)
**Apply to:** All new `@socketio.on` handlers in bridge.py

Pattern: Always call `proxy = get_game_server_proxy()` — never create a Proxy inline, never share across handler threads.

---

## No Analog Found

All files for Phase 7 are either modifications to existing files or have strong analogs within the codebase. No files require pattern invention from external references.

---

## Metadata

**Analog search scope:** `bridge/`, `server/`, `frontend/src/`, `tests/`
**Files scanned:** 12 source files + 5 test files
**Pattern extraction date:** 2026-05-15
