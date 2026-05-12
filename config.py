import os

# Name Server host — read from env var PYRO_NS_HOST with default 127.0.0.1 (D-02)
# All locate_ns() calls must pass host=NS_HOST to avoid UDP broadcast (D-01)
NS_HOST = os.environ.get("PYRO_NS_HOST", "127.0.0.1")

# Game server listens on this port (D-07)
GAME_SERVER_PORT = 9091

# Flask-SocketIO bridge listens on this port (D-07)
BRIDGE_PORT = 5000

# Pyro5 registration name for the game server — used in both server and clients
GAME_SERVER_NAME = "game.server"
