"""Flask-SocketIO bridge — translates WebSocket events to Pyro5 RPC calls and
routes server-initiated Pyro5 callbacks back to connected browsers.

Key design decisions:
  - async_mode='threading' hardcoded (D-08, Pitfall 6)
  - BridgeCallbackReceiver runs in a background Pyro5 daemon thread (Pitfall 3)
  - Per-thread Pyro5 proxy via threading.local() (D-10, Pitfall 2)
  - Bridge startup retries locate_ns() for up to 10s (D-03, Pitfall 3)
  - All daemons and Flask bind to 127.0.0.1 only (T-01-09)
"""

import os
import sys
import threading
import time

# Allow `import config` when running as `python bridge/bridge.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Pyro5.api
import Pyro5.errors
from flask import Flask
from flask_socketio import SocketIO

import config

# ---------------------------------------------------------------------------
# Flask app + SocketIO — async_mode MUST be 'threading', never rely on default
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*",
                    logger=True, engineio_logger=False)


# ---------------------------------------------------------------------------
# BridgeCallbackReceiver — receives @oneway Pyro5 callbacks from GameServer
#                          and emits them as Socket.IO events to browsers
# ---------------------------------------------------------------------------

@Pyro5.api.expose
class BridgeCallbackReceiver:
    """Pyro5 callback receiver that lives inside the bridge process.

    Its on_* methods fire in the bridge's Pyro5 daemon background thread.
    Calling socketio.emit() from a non-request thread is safe in threading mode
    (Flask-SocketIO docs confirmed, D-08, Pitfall 6).
    """

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_test_event(self, data: dict):
        """Receives a broadcast_test() push from GameServer and emits to browsers."""
        try:
            socketio.emit("game_event", data)
            print(f"[BRIDGE] game_event emitted: {data}", flush=True)
            sys.stdout.flush()
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_test_event: {exc}", flush=True)
            sys.stderr.write(f"[BRIDGE] ERROR: {exc}\n")
            sys.stderr.flush()


# ---------------------------------------------------------------------------
# Callback daemon startup — binds receiver to a loopback Pyro5 daemon
# ---------------------------------------------------------------------------

def start_callback_daemon() -> tuple:
    """Start a background Pyro5 daemon hosting BridgeCallbackReceiver.

    Returns (uri_str, daemon) so the caller can pass the URI to GameServer
    and hold a reference to prevent GC of the daemon.
    """
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    receiver = BridgeCallbackReceiver()
    uri = daemon.register(receiver)
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return str(uri), daemon


# ---------------------------------------------------------------------------
# Per-thread Pyro5 proxy (D-10) — each Flask-SocketIO handler thread gets its
# own proxy; sharing a proxy across threads corrupts the data stream (Pitfall 2)
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def get_game_server_proxy() -> Pyro5.api.Proxy:
    """Return the per-thread Proxy for the GameServer.

    Creates a new Proxy on first call per thread, then reuses it on subsequent
    calls from the same thread.  Threads never share a proxy.
    """
    if not hasattr(_thread_local, "proxy"):
        _thread_local.proxy = Pyro5.api.Proxy(
            f"PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}"
        )
    return _thread_local.proxy


# ---------------------------------------------------------------------------
# Startup retry — poll NS + GameServer for up to 10 seconds (D-03, Pitfall 3)
# ---------------------------------------------------------------------------

def connect_to_game_server(cb_uri: str) -> bool:
    """Register the callback URI with GameServer, retrying for up to 10 seconds.

    Returns True on success, False if the deadline is exceeded.

    Strategy:
      - max_attempts=20 × sleep_interval=0.5s ≈ 10 second window
      - Each attempt: locate NS, create a fresh proxy, call ping(), register
    """
    max_attempts = 20
    sleep_interval = 0.5

    for attempt in range(1, max_attempts + 1):
        try:
            Pyro5.api.locate_ns(host=config.NS_HOST)          # raises if NS not up
            proxy = Pyro5.api.Proxy(
                f"PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}"
            )
            proxy.ping()                                       # raises if server not up
            proxy.register_callback("bridge", cb_uri)
            proxy._pyroRelease()
            print("[BRIDGE] Connected to GameServer and registered callback.")
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[BRIDGE] Attempt {attempt}/{max_attempts} failed: {exc}")
            time.sleep(sleep_interval)

    print(
        "[BRIDGE] ERROR: Could not connect to GameServer after 10s. "
        "Is NS + GameServer running?"
    )
    return False


# ---------------------------------------------------------------------------
# Socket.IO event handlers
# ---------------------------------------------------------------------------

@socketio.on("ping")
def handle_ping():
    """Forward a browser 'ping' event to GameServer via per-thread proxy."""
    proxy = get_game_server_proxy()
    result = proxy.ping()
    print(f"[BRIDGE] ping from client → {result}")
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cb_uri, _daemon = start_callback_daemon()
    print(f"[BRIDGE] Callback receiver URI: {cb_uri}")

    if not connect_to_game_server(cb_uri):
        sys.exit(1)

    socketio.run(app, host="127.0.0.1", port=config.BRIDGE_PORT,
                 allow_unsafe_werkzeug=True)
