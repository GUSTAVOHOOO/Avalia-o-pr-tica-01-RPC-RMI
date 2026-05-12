# Phase 2: Player Session + Lobby - Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 13 new/modified files
**Analogs found:** 9 / 13 (4 frontend files have no codebase analog — first React/TS in project)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `server/game_server.py` (extend) | service | CRUD + event-driven | `server/game_server.py` itself (Phase 1) | self |
| `server/event_broadcaster.py` (no change) | service | event-driven | self | reference only |
| `bridge/bridge.py` (extend) | middleware | request-response + event-driven | `bridge/bridge.py` itself (Phase 1) | self |
| `config.py` (possible extend) | config | — | `config.py` itself (Phase 1) | self |
| `tests/test_session.py` (new) | test | CRUD | `tests/test_unit.py` | role-match |
| `frontend/vite.config.ts` (new) | config | — | none in codebase | no analog |
| `frontend/src/main.tsx` (new) | config/entry | — | none in codebase | no analog |
| `frontend/src/App.tsx` (new) | component | request-response | none in codebase | no analog |
| `frontend/src/socket.ts` (new) | utility | event-driven | none in codebase | no analog |
| `frontend/src/pages/Landing.tsx` (new) | component | request-response | none in codebase | no analog |
| `frontend/src/pages/CreateGame.tsx` (new) | component | request-response | none in codebase | no analog |
| `frontend/src/pages/JoinGame.tsx` (new) | component | request-response | none in codebase | no analog |
| `frontend/src/pages/Lobby.tsx` (new) | component | event-driven | none in codebase | no analog |

---

## Pattern Assignments

### `server/game_server.py` — New methods: `create_game`, `join_game`, `start_game`, `leave_game`, `_generate_room_code` + `GameSession`/`PlayerInfo` dataclasses

**Analog:** `server/game_server.py` (Phase 1 self)

**Imports pattern** (lines 1–22):
```python
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Pyro5.api

import config
from server.event_broadcaster import EventBroadcaster
```
Phase 2 adds: `import uuid`, `import random`, `import string`, `import dataclasses`, `from typing import List`

**Class declaration + `__init__` pattern** (lines 24–31):
```python
@Pyro5.api.expose
class GameServer:
    """Exposed Pyro5 server object.  All public methods are callable via RPC."""

    def __init__(self):
        self.lock = threading.RLock()
        self.broadcaster = EventBroadcaster()
```
Phase 2 adds `self.sessions: dict[str, GameSession] = {}` inside `__init__`.

**Input validation pattern** (lines 50–53):
```python
if not isinstance(player_id, str) or not player_id:
    raise ValueError("player_id and callback_uri must be non-empty strings")
if not isinstance(callback_uri, str) or not callback_uri:
    raise ValueError("player_id and callback_uri must be non-empty strings")
```
Copy this pattern for `player_name`, `callback_uri`, `room_code` validation in new methods.

**`register_callback` as the internal broadcast registration pattern** (lines 36–56):
```python
def register_callback(self, player_id: str, callback_uri: str) -> bool:
    # ...validation...
    self.broadcaster.register_callback(player_id, callback_uri)
    return True
```
`create_game` and `join_game` call `self.broadcaster.register_callback(player_id, callback_uri)` directly (same call, no separate RPC round-trip — D-03).

**`@oneway` broadcast method pattern** (lines 58–69):
```python
@Pyro5.api.oneway
def broadcast_test(self, message: str) -> None:
    self.broadcaster.broadcast("test_event", {"message": message, "source": "broadcast_test"})
```
`start_game` triggers `self.broadcaster.broadcast("game_started", {...})` and `leave_game` triggers `self.broadcaster.broadcast("host_changed", {...})` after releasing `self.lock`. These calls happen OUTSIDE the `with self.lock:` block to avoid deadlock (RESEARCH Pitfall 4).

**Lock pattern** — every new method that mutates `self.sessions` must use:
```python
with self.lock:
    # read / mutate session state here
    # snapshot any data needed for broadcast
    broadcast_data = {...}
# broadcaster.broadcast() OUTSIDE the lock
self.broadcaster.broadcast("event_name", broadcast_data)
```

**`__main__` entry point pattern** (lines 72–86) — unchanged, no modifications needed.

---

### `bridge/bridge.py` — New: Socket.IO handlers for `create_game`, `join_game`, `start_game`, `disconnect`; `_sid_to_player` dict; `on_player_joined`/`on_game_started` in `BridgeCallbackReceiver`; Flask catch-all

**Analog:** `bridge/bridge.py` (Phase 1 self)

**Imports pattern** (lines 1–26):
```python
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Pyro5.api
import Pyro5.errors
from flask import Flask
from flask_socketio import SocketIO

import config
```
Phase 2 adds: `from flask import request, send_from_directory` and `from flask_socketio import join_room`

**Flask + SocketIO init pattern** (lines 31–34):
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*",
                    logger=True, engineio_logger=False)
```
Do NOT change this block. Static files: `Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="/assets")` or use `send_from_directory` — prefer the catch-all route approach from RESEARCH Pattern 5.

**BridgeCallbackReceiver — existing callback method pattern** (lines 42–62):
```python
@Pyro5.api.expose
class BridgeCallbackReceiver:

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_test_event(self, data: dict):
        try:
            socketio.emit("game_event", data)
            print(f"[BRIDGE] game_event emitted: {data}", flush=True)
            sys.stdout.flush()
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_test_event: {exc}", flush=True)
            sys.stderr.write(f"[BRIDGE] ERROR: {exc}\n")
            sys.stderr.flush()
```
New methods `on_player_joined`, `on_game_started`, `on_host_changed` copy this exact decorator stack (`@Pyro5.api.oneway` then `@Pyro5.api.callback`) and try/except structure, but emit `to=data["room_code"]` instead of broadcast.

**Per-thread proxy pattern** (lines 88–101):
```python
_thread_local = threading.local()

def get_game_server_proxy() -> Pyro5.api.Proxy:
    if not hasattr(_thread_local, "proxy"):
        _thread_local.proxy = Pyro5.api.Proxy(
            f"PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}"
        )
    return _thread_local.proxy
```
All new Socket.IO handlers call `proxy = get_game_server_proxy()` at the top — never a module-level proxy.

**Existing Socket.IO handler pattern** (lines 146–152):
```python
@socketio.on("ping")
def handle_ping():
    proxy = get_game_server_proxy()
    result = proxy.ping()
    print(f"[BRIDGE] ping from client → {result}")
    return result
```
New handlers (`create_game`, `join_game`, `start_game`) follow this exact shape: `@socketio.on(event)`, call `get_game_server_proxy()`, call the RPC method, return the result as Socket.IO ack. Add `join_room()` call for session-scoped events and populate `_sid_to_player`.

**`connect_to_game_server` error handling pattern** (lines 108–139):
```python
for attempt in range(1, max_attempts + 1):
    try:
        # ... operations ...
    except Exception as exc:  # noqa: BLE001
        print(f"[BRIDGE] Attempt {attempt}/{max_attempts} failed: {exc}")
        time.sleep(sleep_interval)
```
Use `except Exception as exc` (broad catch) with `flush=True` print in all new handler error paths, consistent with the existing pattern.

**`__main__` entry point pattern** (lines 159–167):
```python
if __name__ == "__main__":
    cb_uri, _daemon = start_callback_daemon()
    print(f"[BRIDGE] Callback receiver URI: {cb_uri}")

    if not connect_to_game_server(cb_uri):
        sys.exit(1)

    socketio.run(app, host="127.0.0.1", port=config.BRIDGE_PORT,
                 allow_unsafe_werkzeug=True)
```
The Flask catch-all route must be registered before `socketio.run()` but after `socketio = SocketIO(...)` to avoid shadowing Socket.IO routes (RESEARCH Pitfall 3).

---

### `config.py` — Possible addition: `FRONTEND_DIST_PATH`

**Analog:** `config.py` (Phase 1 self)

**Pattern** (lines 1–14):
```python
import os

NS_HOST = os.environ.get("PYRO_NS_HOST", "127.0.0.1")
GAME_SERVER_PORT = 9091
BRIDGE_PORT = 5000
GAME_SERVER_NAME = "game.server"
```
If `FRONTEND_DIST_PATH` is added, follow the same pattern:
```python
FRONTEND_DIST_PATH = os.environ.get(
    "FRONTEND_DIST",
    os.path.join(os.path.dirname(__file__), "frontend", "dist")
)
```

---

### `tests/test_session.py` — New: 6 unit tests for SESSION-01 through SESSION-06

**Analog:** `tests/test_unit.py`

**Imports + helper pattern** (lines 1–37):
```python
import threading
import time

import pytest
import Pyro5.api
import Pyro5.errors

from server.game_server import GameServer


def _start_daemon(obj, object_id: str):
    """Register obj in a new daemon and start requestLoop in a daemon thread."""
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    uri = daemon.register(obj, objectId=object_id)
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return daemon, str(uri)
```
Copy this helper verbatim into `tests/test_session.py`. Each test must start its own daemon and shut it down in a `finally` block.

**Test structure pattern** (lines 44–53):
```python
def test_ping():
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.game.server.ping")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            result = proxy.ping()
        assert result == "pong", f"Expected 'pong', got {result!r}"
    finally:
        daemon.shutdown()
```
New session tests follow the same `server = GameServer()` → `_start_daemon()` → `with Pyro5.api.Proxy(uri) as proxy:` → assert → `finally: daemon.shutdown()` structure.

**Callback receiver inline pattern** (lines 89–100):
```python
@Pyro5.api.expose
class TestCallbackReceiver:
    def __init__(self):
        self.received = []
        self.event = threading.Event()

    def on_test_event(self, data):
        self.received.append(data)
        self.event.set()
```
For `test_player_joined_broadcast` (SESSION-05), define an inline `TestCallbackReceiver` class inside the test function, exposing `on_player_joined(self, data)` instead of `on_test_event`. Use `receiver.event.wait(timeout=5)` to assert delivery.

**Broadcast delivery wait pattern** (lines 109–121):
```python
server.broadcaster.register_callback("r1", cb_uri)
server.broadcaster.broadcast("test_event", {"msg": "hello"})
delivered = receiver.event.wait(timeout=5)
assert delivered, "Timed out waiting for broadcast delivery (>5 s)"
assert len(receiver.received) == 1
```
Copy this wait pattern for broadcast delivery assertions.

---

### `frontend/vite.config.ts` (new — no codebase analog)

No analog exists. Use RESEARCH Pattern 6 verbatim:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/socket.io': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
```

---

### `frontend/src/main.tsx` (new — no codebase analog)

No analog exists. Standard Vite React-TS entry point:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

---

### `frontend/src/App.tsx` (new — no codebase analog)

No analog exists. Use RESEARCH Pattern 7 verbatim:
```tsx
import { BrowserRouter, Routes, Route } from 'react-router'
import Landing from './pages/Landing'
import CreateGame from './pages/CreateGame'
import JoinGame from './pages/JoinGame'
import JoinByCode from './pages/JoinByCode'
import Lobby from './pages/Lobby'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/create" element={<CreateGame />} />
        <Route path="/join" element={<JoinGame />} />
        <Route path="/join/:code" element={<JoinByCode />} />
        <Route path="/lobby/:sessionId" element={<Lobby />} />
      </Routes>
    </BrowserRouter>
  )
}
```

---

### `frontend/src/socket.ts` (new — no codebase analog)

No analog exists. Use RESEARCH Pattern 8 verbatim:
```typescript
import { io } from 'socket.io-client'

const socket = io({ path: '/socket.io', autoConnect: false })

export default socket
```
`autoConnect: false` means pages must call `socket.connect()` when mounting. Pages call `socket.disconnect()` or `socket.off(event)` on unmount (D-06 localStorage pattern applies here).

---

### `frontend/src/pages/Landing.tsx`, `CreateGame.tsx`, `JoinGame.tsx`, `JoinByCode.tsx` (new — no codebase analog)

No analog exists. All page components follow the same base shape derived from RESEARCH Pattern 7 and Pattern 8:
```tsx
import { useNavigate } from 'react-router'
import socket from '../socket'

export default function PageName() {
  const navigate = useNavigate()

  const handleSubmit = () => {
    socket.connect()
    socket.emit('event_name', { ...payload }, (response: Record<string, unknown>) => {
      if (response.error) {
        // show error
        return
      }
      localStorage.setItem('player_id', response.player_id as string)
      localStorage.setItem('room_code', response.room_code as string)
      localStorage.setItem('is_host', String(response.is_host))
      navigate(`/lobby/${response.room_code}`)
    })
  }

  return ( /* JSX per UI.md screen spec */ )
}
```

---

### `frontend/src/pages/Lobby.tsx` (new — no codebase analog)

No analog exists. Use RESEARCH code example as the primary reference (RESEARCH §Code Examples "Frontend: Lobby Component Real-Time Update"):
```tsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import socket from '../socket'

interface Player { player_id: string; player_name: string; is_host: boolean }

export default function Lobby() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [players, setPlayers] = useState<Player[]>([])
  const isHost = localStorage.getItem('is_host') === 'true'

  useEffect(() => {
    socket.on('player_joined', (data: { players: Player[] }) => {
      setPlayers(data.players)
    })
    socket.on('game_started', () => {
      // navigate to game phase route (Phase 3+)
    })
    return () => {
      socket.off('player_joined')
      socket.off('game_started')
    }
  }, [sessionId])

  const handleStart = () => {
    const playerId = localStorage.getItem('player_id')
    const maxTurns = Number(localStorage.getItem('max_turns') ?? 5)
    socket.emit('start_game', { player_id: playerId, max_turns: maxTurns })
  }

  return ( /* JSX per UI.md WEB-005 spec */ )
}
```

---

## Shared Patterns

### Pyro5 `@expose` + `@oneway` + `@callback` decorator stack
**Source:** `bridge/bridge.py` lines 42–62 and `server/game_server.py` lines 24, 58–69
**Apply to:** All new `BridgeCallbackReceiver` methods (`on_player_joined`, `on_game_started`, `on_host_changed`)
```python
@Pyro5.api.expose           # on the class
# ...
@Pyro5.api.oneway           # on each callback method — MUST be first decorator
@Pyro5.api.callback         # MUST be second decorator
def on_player_joined(self, data: dict):
    try:
        socketio.emit("player_joined", data, to=data["room_code"])
        print(f"[BRIDGE] player_joined emitted to {data['room_code']}", flush=True)
    except Exception as exc:
        print(f"[BRIDGE] ERROR in on_player_joined: {exc}", flush=True)
```

### Per-thread Pyro5 proxy
**Source:** `bridge/bridge.py` lines 88–101
**Apply to:** All new Socket.IO event handlers in `bridge.py`
```python
proxy = get_game_server_proxy()
```
Never pass a proxy between handlers or store at module level.

### `threading.RLock` for session mutations
**Source:** `server/game_server.py` lines 28–29
**Apply to:** All new `GameServer` methods (`create_game`, `join_game`, `start_game`, `leave_game`)
```python
with self.lock:
    # mutate self.sessions
    broadcast_data = {...}   # snapshot before releasing
# broadcast OUTSIDE the lock
```

### Error return dict pattern
**Source:** RESEARCH §Code Examples `join_game`
**Apply to:** `create_game`, `join_game`, `start_game` when validation fails
```python
return {"error": "jogo em andamento"}   # bridge propagates to frontend as ack
return {"error": "sala nao encontrada"}
return {"error": "sala cheia"}
```
Return a dict with `"error"` key — do NOT raise inside session methods. Raising is acceptable for programmer errors (bad types) but not for game-logic rejections.

### `sys.path.insert` portability header
**Source:** `server/game_server.py` lines 15–16 and `bridge/bridge.py` lines 17–18
**Apply to:** Any new top-level Python scripts
```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### Test daemon lifecycle pattern
**Source:** `tests/test_unit.py` lines 28–37
**Apply to:** All tests in `tests/test_session.py`
```python
def _start_daemon(obj, object_id: str):
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    uri = daemon.register(obj, objectId=object_id)
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return daemon, str(uri)
```
Always use a unique `object_id` per test (e.g., `"test.game.server.create_game"`) to avoid port conflicts when tests run in the same process.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/vite.config.ts` | config | — | No frontend build tooling exists in project yet |
| `frontend/src/main.tsx` | entry | — | First React file; no prior frontend code |
| `frontend/src/App.tsx` | router | request-response | No React Router usage exists in project |
| `frontend/src/socket.ts` | utility | event-driven | No socket.io-client usage exists in project |
| `frontend/src/pages/*.tsx` (5 files) | component | request-response / event-driven | No React components exist in project |

For all frontend files without analogs, RESEARCH.md Patterns 6–9 and the code examples section are the authoritative references.

---

## Metadata

**Analog search scope:** `/home/spacko/projects/faculdade/sd-rpc-av-1/server/`, `/home/spacko/projects/faculdade/sd-rpc-av-1/bridge/`, `/home/spacko/projects/faculdade/sd-rpc-av-1/tests/`, `/home/spacko/projects/faculdade/sd-rpc-av-1/config.py`
**Files scanned:** `server/game_server.py`, `server/event_broadcaster.py`, `bridge/bridge.py`, `config.py`, `tests/test_unit.py`
**Pattern extraction date:** 2026-05-12
