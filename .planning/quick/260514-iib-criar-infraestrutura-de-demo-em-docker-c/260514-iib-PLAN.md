---
quick_id: 260514-iib
slug: criar-infraestrutura-de-demo-em-docker-c
description: criar infraestrutura de demo em docker compose para o projeto Pyro5/Flask-SocketIO
date: 2026-05-14
branch: docker-demo-infra
---

# Quick Task 260514-iib: Docker Demo Infrastructure

## Goal

Stand up the Pyro5/Flask-SocketIO project in Docker Compose for demo day, with ngrok integration and a one-command start script.

## Tasks

### Task 1 — Bind host env vars in config.py and code

**Files:** `config.py`, `bridge/bridge.py`, `server/game_server.py`

Add `PYRO_BIND_HOST` (Pyro5 daemon bind host, default `127.0.0.1`) and `FLASK_BIND_HOST` (Flask bind host, default `127.0.0.1`) to config.py. Update bridge and game_server to use these instead of the hardcoded `"127.0.0.1"` strings so Docker containers can advertise their service name in Pyro5 URIs and Flask can accept external connections.

**Verify:** `grep -n "PYRO_BIND_HOST\|FLASK_BIND_HOST" config.py` shows both vars. Local smoke test (no Docker) still binds to 127.0.0.1 by default.

### Task 2 — Docker files

**Files:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`

Single `Dockerfile` using `python:3.11-slim`, installs `requirements.txt`, copies source. `docker-compose.yml` defines three services (`nameserver`, `gameserver`, `bridge`) on a shared `game-net` bridge network with real healthchecks and `depends_on: condition: service_healthy` ordering. Bridge exposes port 5000. `.dockerignore` excludes `venv/`, `node_modules/`, `.planning/`, `.claude/`, `__pycache__/`, etc.

**Verify:** `docker compose config` parses without errors.

### Task 3 — start-demo.sh

**Files:** `start-demo.sh`

Shell script that: (1) runs `docker compose up -d --build`, (2) polls `docker compose ps` until bridge is `(healthy)` or times out with logs, (3) starts `ngrok http 5000` in background, (4) queries `localhost:4040/api/tunnels` and prints the HTTPS public URL.

**Verify:** Script is executable, `bash -n start-demo.sh` passes syntax check.
