---
quick_id: 260514-iib
status: complete
date: 2026-05-14
branch: docker-demo-infra
---

# Summary: Docker Demo Infrastructure

## What was done

Created full Docker Compose infrastructure for demo day on branch `docker-demo-infra`.

### config.py
Added two env-var-backed config values (both default to `127.0.0.1` — no local behaviour change):
- `PYRO_BIND_HOST` — controls Pyro5 daemon bind/advertise host (set to container service name in Docker)
- `FLASK_BIND_HOST` — controls Flask/SocketIO bind host (set to `0.0.0.0` for bridge in Docker)

### bridge/bridge.py + server/game_server.py
Replaced the two hardcoded `"127.0.0.1"` daemon bind strings with `config.PYRO_BIND_HOST` and the Flask `host=` arg with `config.FLASK_BIND_HOST`.

### Dockerfile
Single `python:3.11-slim` image shared by all three services. Installs `requirements.txt`, copies source. No CMD — overridden per service in docker-compose.

### docker-compose.yml
Three services on `game-net` bridge network:
- `nameserver` — `python -m Pyro5.utils.nameserver --host 0.0.0.0`, healthcheck via `locate_ns(host='localhost')`
- `gameserver` — `python server/game_server.py`, env: `PYRO_NS_HOST=nameserver`, `PYRO_BIND_HOST=gameserver`, healthcheck via NS lookup + ping()
- `bridge` — `python bridge/bridge.py`, env: `PYRO_NS_HOST=nameserver`, `PYRO_BIND_HOST=bridge`, `FLASK_BIND_HOST=0.0.0.0`, port 5000:5000, healthcheck via TCP socket connect

Startup order: `nameserver` → `gameserver` → `bridge` enforced via `depends_on: condition: service_healthy`.

### .dockerignore
Excludes: `venv/`, `__pycache__/`, `*.pyc`, `.git/`, `.planning/`, `.claude/`, `frontend/node_modules/`, frontend build sources (keeps `frontend/dist/`).

### start-demo.sh
One-command demo launcher:
1. `docker compose up -d --build`
2. Polls until bridge is `(healthy)` (120s timeout, prints logs on failure)
3. Starts `ngrok http 5000` in background
4. Queries `localhost:4040/api/tunnels` and prints the HTTPS public URL
