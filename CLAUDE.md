<!-- GSD:project-start source:PROJECT.md -->
## Project

**Jogo de Adivinhação Multijogador — RPC/Pyro5**

Jogo multijogador de adivinhação em tempo real construído como trabalho acadêmico para a disciplina CC5SDT (Sistemas Distribuídos e Tecnologias) na UTFPR — Campus Santa Helena, semestre 2026-1. Cada jogador recebe uma imagem secreta de um objeto e, a cada turno, envia uma dica de uma palavra para todos. Os outros jogadores tentam adivinhar os objetos, com mecânicas de troca privada de dicas, espionagem com risco de penalidade e sistema de pontuação automático. Interface web (React/HTML) no front-end e comunicação exclusivamente via Pyro5 RPC no back-end.

**Core Value:** Demonstrar arquitetura distribuída event-driven funcional: servidor Pyro5 com callbacks push para todos os clientes, mecânicas de jogo completas (dicas, palpites, trocas privadas, espionagem) e interface web reagindo em tempo real — tudo funcionando com 2–4 jogadores simultâneos.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core RPC Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pyro5 | 5.16 | Python RPC backbone, game server, callbacks | Required by course. Latest stable (Dec 21, 2025). Python 3.10+ required in 5.16. |
| serpent | >=1.27 (auto-installed) | Default serializer for Pyro5 | Installed automatically as Pyro5 dependency. Safe, handles most Python types, no config needed. |
### Bridge Layer (WebSocket to Pyro5)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Flask-SocketIO | 5.6.1 | WebSocket/SocketIO server, bridge to Pyro5 | See rationale below |
| Flask | 3.x | Web framework underlying Flask-SocketIO | Required by Flask-SocketIO |
| simple-websocket | latest | WebSocket transport for threading mode | Required when using async_mode='threading' without gevent/eventlet |
- Requires async/await throughout; Pyro5 callbacks are sync
- No built-in Socket.IO protocol; must implement room management, reconnect, event routing manually
- Thread-to-asyncio bridging for callback forwarding is error-prone
- Higher complexity for a 2-person academic project with a 1-semester timeline
- Also async-native; same thread/async mismatch as FastAPI
- Smaller ecosystem, fewer examples of Pyro5 bridge patterns
- Less documentation for this exact use case
### Frontend
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| socket.io-client | 4.x (CDN) | WebSocket/SocketIO browser client | Matches Flask-SocketIO server protocol version |
| Vanilla HTML/CSS/JS | — | UI rendering and state | No build step, no npm, minimal setup |
| Tailwind CSS | 3.x (CDN play) | Styling | CDN play build, zero configuration, fast prototyping |
### Synonym Arbitration
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| NLTK | 3.9.x | NLP toolkit, WordNet interface | Standard Python NLP library, Open Multilingual Wordnet support |
| wordnet corpus | (via nltk.download) | English synsets | Downloaded once with `nltk.download('wordnet')` |
| omw-1.4 corpus | (via nltk.download) | Open Multilingual Wordnet including Portuguese | `nltk.download('omw-1.4')` enables `lang='por'` lookup |
### Image Serving
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pillow | 12.1.0 | Image loading, resizing, format conversion | Standard Python image library, zero config, serves from disk |
# Server sends event with image reference, not raw bytes
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
## Installation
# Python 3.10+ required (Pyro5 5.16 dropped 3.8/3.9)
# Core RPC
# Bridge layer
# NLP for synonym arbitration
# Image serving
## Key Pyro5 Patterns for This Project
### 1. Server object with single instance and thread-safety
### 2. Bridge callback object (runs inside Flask-SocketIO process)
# In bridge startup:
### 3. Name Server usage
# Terminal 1: start nameserver
# Terminal 2: game server registers itself
# Bridge process looks up game server
### 4. @oneway for fire-and-forget pushes
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

## Subagent Parallelism (Claude Code)

Unlike Codex/OpenCode, Claude Code supports native parallelism.
When there are multiple independent subagents to spawn simultaneously,
fire ALL of them in parallel before waiting for any result.

The "ORCHESTRATOR RULE — CODEX RUNTIME" instructions found in GSD workflows
do NOT apply here. In Claude Code, independent subagents must be dispatched
concurrently, not sequentially.
