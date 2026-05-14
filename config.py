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

# Path to the compiled React frontend dist directory (D-09)
# Override via FRONTEND_DIST env var; default to frontend/dist next to this file
FRONTEND_DIST_PATH = os.environ.get(
    "FRONTEND_DIST",
    os.path.join(os.path.dirname(__file__), "frontend", "dist"),
)

# Per-phase timer durations in seconds (D-04). Tune here; never in game logic.
PHASE_DURATIONS = {
    "ROUND_START":    5,
    "HINT_PHASE":    60,
    "GUESS_PHASE":   60,
    "EXCHANGE_PHASE": 45,
    "SPY_PHASE":     30,
    "SCORING_PHASE": 15,
    "TURN_END":       5,
}
