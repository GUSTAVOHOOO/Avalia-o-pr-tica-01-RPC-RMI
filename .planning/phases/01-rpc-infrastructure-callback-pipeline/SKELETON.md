---
phase: 01-rpc-infrastructure-callback-pipeline
type: walking-skeleton
created: 2026-05-12
---

# Walking Skeleton — Phase 1

## Capability Proven

Three OS processes (pyro5 Name Server, GameServer daemon, Flask-SocketIO Bridge) run and communicate. A server-pushed Pyro5 callback arrives at `client/test_client.py` without the client having polled or requested it.

**The demo sequence:**
1. `venv/bin/pyro5-ns --host 127.0.0.1` — Name Server starts; listens on 9090
2. `venv/bin/python server/game_server.py` — GameServer daemon starts on 9091; registers under "game.server" in NS
3. `venv/bin/python bridge/bridge.py` — Bridge starts on 5000; discovers GameServer via NS; registers BridgeCallbackReceiver as a Pyro5 callback
4. Operator calls `GameServer.broadcast_test("hello")` — fires @oneway, returns immediately
5. EventBroadcaster calls `proxy.on_test_event({"message": "hello"})` on all registered callbacks
6. BridgeCallbackReceiver.on_test_event() fires in the bridge process; calls `socketio.emit("game_event", data)` — visible in bridge log
7. `venv/bin/python client/test_client.py` (with NS + GameServer running): prints `[PUSH RECEIVED] {...}` and exits

**Phase 1 is complete when all 4 pytest tests pass AND the 3-terminal smoke test is manually approved.**

---

## Architectural Decisions

These decisions are locked for the entire project. Subsequent phases build on them without renegotiating.

| Decision | Value | Rationale | Locked By |
|----------|-------|-----------|-----------|
| RPC backbone | Pyro5 5.16 | Required by course; native callbacks; Name Server included | Course requirement + CLAUDE.md |
| Python version | 3.11.2 (`/usr/bin/python3.11`) | Pyro5 docs "supported on 3.9+"; 3.8 (mise default) is unsupported; venv from 3.11 | RESEARCH.md Pitfall 5 |
| WebSocket bridge | Flask-SocketIO 5.6.1, `async_mode='threading'` | Browsers cannot call Pyro5 directly; threading mode is compatible with Pyro5 sync callbacks; eventlet deprecated | D-08, CLAUDE.md |
| Callback pattern | EventBroadcaster — `{player_id: Proxy(callback_uri)}` dict with Lock | Server-side fan-out to all registered receivers via @oneway | PRD §8.1, D-09 |
| @oneway on broadcasts | All GameServer methods calling broadcaster must be @oneway | Prevents callback deadlock in Pyro5's thread-per-connection model | D-09, RESEARCH.md Pitfall 1 |
| Per-thread proxy in bridge | `threading.local()` for Pyro5 proxies in Flask-SocketIO handlers | Pyro5 proxies are not thread-safe; shared proxy under concurrent requests corrupts socket stream | D-10, RESEARCH.md Pitfall 2 |
| NS discovery | `locate_ns(host=config.NS_HOST)` — never bare `locate_ns()` | UDP broadcast may be blocked by firewall/VPN on demo day | D-01, D-02 |
| Config source of truth | `config.py` at project root — `NS_HOST`, `GAME_SERVER_PORT=9091`, `BRIDGE_PORT=5000` | Single import point for all processes; env var override via `PYRO_NS_HOST` | D-07 |
| Image serving | Flask static URLs — never raw bytes through Pyro5 | serpent is inefficient for binary; no base64 overhead | CLAUDE.md, C4 pitfall |

---

## Stack Touched in Phase 1

| Layer | Technology | Version | File(s) |
|-------|-----------|---------|---------|
| RPC daemon | Pyro5 | 5.16 | server/game_server.py |
| RPC serializer | serpent | 1.42 (auto) | (no config needed) |
| Event fan-out | Python threading + Pyro5 proxies | — | server/event_broadcaster.py |
| WebSocket bridge | Flask-SocketIO | 5.6.1 | bridge/bridge.py |
| WebSocket transport | Flask + simple-websocket | 3.1.x + latest | bridge/bridge.py |
| Shared config | Python stdlib (os.environ) | — | config.py |
| Test runner | pytest | 7.2.1 | tests/test_unit.py, pytest.ini |
| CLI smoke test | Python stdlib (threading, time) + Pyro5 | — | client/test_client.py |

---

## Directory Layout

This layout is fixed. Subsequent phases add files within it.

```
(project root)/
├── config.py                  # NS_HOST, GAME_SERVER_PORT, BRIDGE_PORT, GAME_SERVER_NAME
├── requirements.txt           # Pyro5==5.16, Flask, flask-socketio==5.6.1, simple-websocket, pytest
├── pytest.ini                 # testpaths = tests
├── .gitignore                 # venv/
├── venv/                      # python3.11 venv (gitignored)
├── server/
│   ├── __init__.py
│   ├── game_server.py         # GameServer(@expose): ping, register_callback, broadcast_test(@oneway)
│   └── event_broadcaster.py   # EventBroadcaster: callbacks dict, broadcast(), send_to_player()
├── bridge/
│   ├── __init__.py
│   └── bridge.py              # Flask-SocketIO app, BridgeCallbackReceiver, threading.local proxy
├── client/
│   ├── __init__.py
│   └── test_client.py         # CLI: NS discovery → register callback → wait for push → print → exit
└── tests/
    ├── __init__.py
    └── test_unit.py           # Real in-process daemon tests: test_ping, test_register_callback,
                               #   test_broadcast_delivery, test_per_thread_proxy
```

---

## What Is Out of Scope for Phase 1

| Category | Example | First Phase |
|----------|---------|-------------|
| Game mechanics | hints, guesses, scoring | Phase 4 |
| Player sessions | join_game, room codes, lobby | Phase 2 |
| Phase machine / timers | HINT_PHASE → GUESS_PHASE | Phase 3 |
| HTML/CSS frontend | browser UI, Tailwind, Socket.IO JS client | Phase 2+ |
| Image serving | Flask static route, Pillow | Phase 4 |
| Synonym arbitration | NLTK, WordNet, Wu-Palmer | Phase 6 |
| Reconnection / state restore | localStorage UUID, get_game_state() | Phase 7 |
| Authentication | any form of login | Out of scope entirely (v2) |
| Database / persistence | any storage beyond in-memory dicts | Out of scope entirely |

---

## Startup Reference (for all phases)

```bash
# Terminal 1
source venv/bin/activate
pyro5-ns --host 127.0.0.1

# Terminal 2
source venv/bin/activate
python server/game_server.py

# Terminal 3 (bridge — Phase 1+)
source venv/bin/activate
python bridge/bridge.py

# Test (separate terminal, Phase 1 smoke test)
source venv/bin/activate
python client/test_client.py

# Unit tests (any terminal)
venv/bin/pytest tests/ -v
```

Environment variable override (for non-localhost deployment in later phases):
```bash
export PYRO_NS_HOST=192.168.x.x
```
