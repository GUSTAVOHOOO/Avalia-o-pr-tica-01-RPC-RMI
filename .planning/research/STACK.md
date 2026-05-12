# Technology Stack

**Project:** Jogo de Adivinhação Multijogador — RPC/Pyro5
**Researched:** 2026-05-12
**Overall confidence:** HIGH (all major choices verified via Context7 and official sources)

---

## Recommended Stack

### Core RPC Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pyro5 | 5.16 | Python RPC backbone, game server, callbacks | Required by course. Latest stable (Dec 21, 2025). Python 3.10+ required in 5.16. |
| serpent | >=1.27 (auto-installed) | Default serializer for Pyro5 | Installed automatically as Pyro5 dependency. Safe, handles most Python types, no config needed. |

**Pyro5 version note:** v5.16 (latest stable) dropped Python 3.8 and 3.9. Use Python 3.10, 3.11, or 3.12. The project maintainer has declared "super low maintenance mode" — the library is stable and feature-complete, not dying, but expect no new features.

### Bridge Layer (WebSocket to Pyro5)

**Recommendation: Flask-SocketIO 5.x with threading async_mode**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Flask-SocketIO | 5.6.1 | WebSocket/SocketIO server, bridge to Pyro5 | See rationale below |
| Flask | 3.x | Web framework underlying Flask-SocketIO | Required by Flask-SocketIO |
| simple-websocket | latest | WebSocket transport for threading mode | Required when using async_mode='threading' without gevent/eventlet |

**Bridge choice rationale:**

Flask-SocketIO wins over FastAPI WebSockets and aiohttp for this specific use case for three reasons:

1. **Thread-safe cross-context emit.** The bridge must receive Pyro5 callbacks (which arrive in a dedicated callback daemon thread) and forward them to browser clients. Flask-SocketIO's `socketio.emit()` is explicitly designed to be called from any thread outside a request context — it broadcasts with `broadcast=True` assumed. FastAPI's native WebSockets require async/await throughout; calling them from a synchronous Pyro5 callback thread requires thread-to-asyncio bridging (`asyncio.run_coroutine_threadsafe`), which is non-trivial and a common source of deadlocks.

2. **No async mismatch.** Pyro5 is synchronous, blocking, and thread-based. Flask-SocketIO in threading mode is also synchronous and thread-based. They share the same concurrency model. FastAPI is ASGI/asyncio; mixing sync Pyro5 callbacks into an async event loop is the biggest integration risk in this stack.

3. **Socket.IO client in the browser is mature and handles reconnection.** The browser Socket.IO client (socket.io@4.x CDN) handles reconnection logic, event namespacing, and fallback transports automatically. You get `socket.on('game_event', handler)` for free. Raw WebSockets with FastAPI require you to build reconnection and message routing yourself.

**Async mode choice within Flask-SocketIO:** Use `async_mode='threading'` (Python standard library threads). Eventlet is not actively maintained (confirmed in Flask-SocketIO docs). Gevent works but adds a C-extension dependency. Threading mode with `simple-websocket` covers WebSocket transport, supports Gunicorn multi-threaded, and has no monkey-patching gotchas.

**Why NOT FastAPI + native WebSockets:**
- Requires async/await throughout; Pyro5 callbacks are sync
- No built-in Socket.IO protocol; must implement room management, reconnect, event routing manually
- Thread-to-asyncio bridging for callback forwarding is error-prone
- Higher complexity for a 2-person academic project with a 1-semester timeline

**Why NOT aiohttp:**
- Also async-native; same thread/async mismatch as FastAPI
- Smaller ecosystem, fewer examples of Pyro5 bridge patterns
- Less documentation for this exact use case

### Frontend

**Recommendation: Vanilla JS + Socket.IO client CDN**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| socket.io-client | 4.x (CDN) | WebSocket/SocketIO browser client | Matches Flask-SocketIO server protocol version |
| Vanilla HTML/CSS/JS | — | UI rendering and state | No build step, no npm, minimal setup |
| Tailwind CSS | 3.x (CDN play) | Styling | CDN play build, zero configuration, fast prototyping |

**Frontend choice rationale:**

The game UI has significant per-phase modal logic (HINT, GUESS, EXCHANGE, SPY, SCORING), a live scoreboard, phase timer, and chat panel. This is interactive enough that HTMX alone is the wrong fit — HTMX excels at server-rendered hypermedia updates, not client-side state machines for game phases.

Alpine.js is genuinely attractive for this project (15KB, no build step, reactive `x-data` bindings). It handles the client-side game state (current phase, timer countdown, modal visibility) cleanly. However, for an academic project where demonstrating distributed systems is the evaluation goal — not frontend sophistication — vanilla JS reduces cognitive overhead and has zero dependency risk. The Socket.IO event handlers map directly to game state changes without a framework layer.

If the team wants lightweight reactivity without a build tool: Alpine.js 3.x via CDN is the upgrade. Add `<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>` and the frontend immediately gains reactive state. This is an additive option, not a requirement.

**Do NOT use React.** The PROJECT.md mentions "React/HTML" as a possibility, but React requires a build pipeline (Vite/Create React App), npm, and component thinking that adds weeks of unrelated complexity for an already constrained academic project. The course is evaluating Pyro5 RPC, not React. Keep the frontend thin.

### Synonym Arbitration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| NLTK | 3.9.x | NLP toolkit, WordNet interface | Standard Python NLP library, Open Multilingual Wordnet support |
| wordnet corpus | (via nltk.download) | English synsets | Downloaded once with `nltk.download('wordnet')` |
| omw-1.4 corpus | (via nltk.download) | Open Multilingual Wordnet including Portuguese | `nltk.download('omw-1.4')` enables `lang='por'` lookup |

**NLTK WordNet for Portuguese:**

NLTK accesses the Open Multilingual Wordnet (OMW) via the `omw-1.4` corpus download. Portuguese is supported with language code `'por'`. The pattern:

```python
from nltk.corpus import wordnet as wn

def is_synonym_or_match(guess: str, target: str) -> bool:
    # Get synsets for target word in Portuguese
    target_synsets = wn.synsets(target, lang='por')
    guess_synsets = wn.synsets(guess, lang='por')
    
    # Check if synsets overlap (same concept)
    if set(target_synsets) & set(guess_synsets):
        return True
    
    # Check WUP similarity (Wu-Palmer) as fuzzy threshold
    for ts in target_synsets:
        for gs in guess_synsets:
            if ts.wup_similarity(gs) is not None and ts.wup_similarity(gs) > 0.9:
                return True
    return False
```

**Confidence caveat (MEDIUM):** The OMW Portuguese data varies in completeness by domain. Common nouns (objects, animals, household items) are well-covered. Verify `nltk.download('omw-1.4')` installs without issue on the deployment machine. As a fallback, the `wn` library (PyPI package `wn`) offers more explicit control over which wordnet to load, but NLTK is simpler for this scope.

**Alternative considered — `wn` package (goodmami/wn):** More modern API, explicit Portuguese wordnet loading (`wn.download('omw-por:1.4')`). Recommended if NLTK OMW Portuguese coverage proves insufficient during testing. LOW priority to switch unless NLTK fails.

### Image Serving

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pillow | 12.1.0 | Image loading, resizing, format conversion | Standard Python image library, zero config, serves from disk |

**Pattern:** Images live as files on the server. Flask-SocketIO (being Flask underneath) serves them as static files via `send_from_directory` or as base64-encoded strings in Socket.IO events. The simplest correct approach is to serve images as static assets over HTTP (Flask route `/images/<filename>`) and only pass the filename/URL through Pyro5 events.

**Do NOT pass raw image bytes through Pyro5 RPC.** Pyro5's serpent serializer can handle binary data but it's inefficient for images. Pass a URL or filename; let the browser fetch the image directly from Flask's static handler.

```python
# Server sends event with image reference, not raw bytes
socketio.emit('round_started', {
    'player_id': pid,
    'image_url': f'/images/{filename}',
    'round': round_num
})
```

---

## Version Summary

| Package | Pinned Version | Install |
|---------|---------------|---------|
| Pyro5 | 5.16 | `pip install Pyro5==5.16` |
| serpent | auto via Pyro5 | (installed as dependency) |
| Flask | 3.1.x | `pip install Flask` |
| Flask-SocketIO | 5.6.1 | `pip install flask-socketio==5.6.1` |
| simple-websocket | latest | `pip install simple-websocket` |
| NLTK | 3.9.x | `pip install nltk` |
| Pillow | 12.1.0 | `pip install Pillow==12.1.0` |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Bridge | Flask-SocketIO (threading) | FastAPI + native WS | Async/sync mismatch with Pyro5 callbacks; no Socket.IO protocol layer |
| Bridge | Flask-SocketIO (threading) | aiohttp | Same async mismatch; lower ecosystem for this use case |
| Bridge async_mode | threading | eventlet | eventlet is no longer actively maintained (confirmed by Flask-SocketIO docs) |
| Bridge async_mode | threading | gevent | Works, but adds C extension; threading is simpler for 2-person team |
| Frontend | Vanilla JS + Socket.IO | React | Build pipeline overhead; course evaluates RPC not frontend framework |
| Frontend | Vanilla JS + Socket.IO | HTMX | HTMX is hypermedia/server-rendered; game phase state machine is client-side |
| Frontend | Vanilla JS + Socket.IO | Alpine.js | Valid upgrade if reactive binding needed; additive option, not blocking |
| NLP | NLTK + omw-1.4 | `wn` package | NLTK is simpler for scope; `wn` is fallback if OMW Portuguese coverage fails |
| Serializer | serpent (default) | msgpack | Requires explicit config in Pyro5; no benefit for this scale (2-4 players) |

---

## Installation

```bash
# Python 3.10+ required (Pyro5 5.16 dropped 3.8/3.9)

# Core RPC
pip install Pyro5==5.16

# Bridge layer
pip install flask-socketio==5.6.1 simple-websocket

# NLP for synonym arbitration
pip install nltk
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# Image serving
pip install Pillow==12.1.0
```

Or as `requirements.txt`:
```
Pyro5==5.16
flask-socketio==5.6.1
simple-websocket
nltk
Pillow==12.1.0
```

---

## Key Pyro5 Patterns for This Project

### 1. Server object with single instance and thread-safety

```python
import Pyro5.api
import threading

@Pyro5.api.expose
@Pyro5.api.behavior(instance_mode="single")
class GameServer:
    def __init__(self):
        self._lock = threading.RLock()
        self._callbacks = {}  # player_id -> callback proxy

    def register_callback(self, player_id, callback_uri):
        with self._lock:
            self._callbacks[player_id] = Pyro5.api.Proxy(callback_uri)

    @Pyro5.api.oneway
    def broadcast_event(self, event_type, data):
        # oneway: returns immediately, doesn't block callers
        with self._lock:
            dead = []
            for pid, cb in self._callbacks.items():
                try:
                    cb.on_game_event(event_type, data)
                except Exception:
                    dead.append(pid)
            for pid in dead:
                del self._callbacks[pid]
```

### 2. Bridge callback object (runs inside Flask-SocketIO process)

```python
import Pyro5.api
import threading

@Pyro5.api.expose
class BridgeCallback:
    """Registered with Pyro5 daemon inside the bridge process.
    When the game server calls on_game_event(), we forward to Socket.IO."""

    def __init__(self, socketio):
        self._socketio = socketio

    @Pyro5.api.expose
    @Pyro5.api.callback
    def on_game_event(self, event_type, data):
        # Called by Pyro5 server in the callback daemon thread
        # socketio.emit() is thread-safe and works outside request context
        self._socketio.emit(event_type, data)

# In bridge startup:
def start_callback_daemon(socketio):
    daemon = Pyro5.api.Daemon()
    cb = BridgeCallback(socketio)
    uri = daemon.register(cb)
    # Run requestLoop in background thread so bridge process can also serve HTTP
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return str(uri)
```

### 3. Name Server usage

```bash
# Terminal 1: start nameserver
python -m Pyro5.nameserver

# Terminal 2: game server registers itself
ns = Pyro5.core.locate_ns()
ns.register("game.server", uri)

# Bridge process looks up game server
proxy = Pyro5.api.Proxy("PYRONAME:game.server")
```

### 4. @oneway for fire-and-forget pushes

Use `@Pyro5.api.oneway` on the client-side callback's `on_game_event` method. This makes the game server's broadcast call return immediately without waiting for all clients to acknowledge. Critical for timers and broadcast events where you don't want one slow client to block all others.

---

## Confidence Assessment

| Area | Confidence | Source |
|------|------------|--------|
| Pyro5 version (5.16) | HIGH | GitHub releases page, readthedocs PDF dated Dec 21, 2025 |
| Pyro5 callback pattern | HIGH | Context7 official docs + chatbox example verified |
| @oneway and @expose decorators | HIGH | Context7 official docs, multiple code examples |
| Flask-SocketIO version (5.6.1) | HIGH | PyPI page verified Feb 21, 2026 |
| Flask-SocketIO threading mode recommendation | HIGH | Context7 official docs explicitly state eventlet deprecated |
| Flask-SocketIO cross-thread emit | HIGH | Official docs + multiple GitHub issues confirming pattern |
| NLTK + omw-1.4 Portuguese support | MEDIUM | Search results confirm 'por' lang code works; coverage quality of OMW for PT nouns not benchmarked |
| Pillow 12.1.0 | HIGH | Context7 version field |
| FastAPI unsuitability for this bridge | HIGH | Async/sync mismatch confirmed by multiple sources + FastAPI WebSocket docs |
| Alpine.js as optional frontend upgrade | MEDIUM | Community sources, not specifically validated for Socket.IO integration at this scope |

---

## What NOT to Use

| Technology | Reason to Avoid |
|------------|----------------|
| React / Vue / Angular | Build pipeline overhead; course evaluates RPC not frontend; adds 2+ weeks unrelated complexity |
| FastAPI WebSockets | ASGI async model conflicts with Pyro5 sync callbacks; thread-to-asyncio bridging is a known deadlock risk |
| aiohttp | Same async conflict as FastAPI; no Socket.IO protocol layer |
| eventlet (async_mode) | Officially deprecated in Flask-SocketIO docs as of 2025; preference given to gevent then threading |
| Pyro4 | Predecessor to Pyro5; different import paths, not the course requirement |
| RPyC / gRPC / Java RMI | Explicitly out of scope per PROJECT.md |
| Raw TCP sockets | Prohibited by course constraint ("comunicação exclusivamente via RPC/Pyro5") |
| msgpack serializer for Pyro5 | Requires explicit configuration; no throughput benefit at 2-4 player scale |
| Binary image data over Pyro5 | Serpent is inefficient for binary; serve images via Flask static routes instead |
| SQLite / any database | Out of scope; no persistence between sessions required |
| Redis / message broker | Overkill for 2-4 players; Pyro5 callbacks handle push directly |

---

## Sources

- Pyro5 GitHub releases: https://github.com/irmen/Pyro5/releases
- Pyro5 documentation (5.16): https://pyro5.readthedocs.io/en/latest/
- Pyro5 chatbox example (callback pattern): https://github.com/irmen/Pyro5/tree/master/examples/chatbox
- Pyro5 callback client docs: https://pyro5.readthedocs.io/en/latest/clientcode.html
- Flask-SocketIO PyPI (version 5.6.1, Feb 2026): https://pypi.org/project/Flask-SocketIO/
- Flask-SocketIO getting started: https://flask-socketio.readthedocs.io/en/latest/getting_started.html
- Flask-SocketIO deployment (async modes): https://flask-socketio.readthedocs.io/en/latest/deployment.html
- NLTK WordNet howto: https://www.nltk.org/howto/wordnet.html
- Open Multilingual Wordnet: https://www.openwordnet-pt.org/
- Pillow (12.1.0) Context7: https://context7.com/python-pillow/pillow/llms.txt
- FastAPI WebSockets comparison: https://dev.to/deepak_mishra_35863517037/modern-alternatives-flask-socketio-vs-fastapi-and-quart-5gh6
