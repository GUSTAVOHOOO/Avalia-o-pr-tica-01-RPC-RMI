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
from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, join_room

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

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_player_joined(self, data: dict):
        """Receives PLAYER_JOINED push from GameServer; routes to correct Socket.IO room."""
        try:
            socketio.emit("player_joined", data, to=data["room_code"])
            print(f"[BRIDGE] player_joined emitted to room {data['room_code']}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_player_joined: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_game_started(self, data: dict):
        """Receives GAME_STARTED push from GameServer; routes to correct Socket.IO room."""
        try:
            socketio.emit("game_started", data, to=data["room_code"])
            print(f"[BRIDGE] game_started emitted to room {data['room_code']}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_game_started: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_host_changed(self, data: dict):
        """Receives HOST_CHANGED push from GameServer when host leaves; routes to room."""
        try:
            socketio.emit("host_changed", data, to=data["room_code"])
            print(f"[BRIDGE] host_changed emitted to room {data['room_code']}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_host_changed: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_phase_changed(self, data: dict):
        """Receives PHASE_CHANGED push from TurnMachine (via GameServer broadcaster); routes to room."""
        try:
            socketio.emit("phase_changed", data, to=data["room_code"])
            print(f"[BRIDGE] phase_changed emitted to room {data['room_code']} phase={data.get('phase')}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_phase_changed: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_game_ended(self, data: dict):
        """Receives GAME_ENDED push from TurnMachine (via GameServer broadcaster); routes to room."""
        try:
            socketio.emit("game_ended", data, to=data["room_code"])
            print(f"[BRIDGE] game_ended emitted to room {data['room_code']}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_game_ended: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_hint_received(self, data: dict):
        """Receives HINT_RECEIVED push from GameServer; routes to room."""
        try:
            socketio.emit("hint_received", data, to=data["room_code"])
            print(
                "[BRIDGE] hint_received emitted to room "
                f"{data['room_code']} count={data.get('hints_count')}/{data.get('total_players')}",
                flush=True,
            )
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_hint_received: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_guess_result(self, data: dict):
        """Receives GUESS_RESULT push from GameServer; routes to room."""
        try:
            socketio.emit("guess_result", data, to=data["room_code"])
            print(
                f"[BRIDGE] guess_result emitted is_correct={data.get('is_correct')}",
                flush=True,
            )
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_guess_result: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_score_updated(self, data: dict):
        """Receives SCORE_UPDATED push from GameServer; routes to room."""
        try:
            socketio.emit("score_updated", data, to=data["room_code"])
            print(f"[BRIDGE] score_updated emitted to room {data['room_code']}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_score_updated: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_object_assigned(self, data: dict):
        """Receives OBJECT_ASSIGNED push from GameServer; routes privately to target player SID."""
        target_player_id = data.get("target_player_id")
        with _sid_lock:
            sid = _player_to_sid.get(target_player_id)
        if not sid:
            print(f"[BRIDGE] player SID not found for {target_player_id}", flush=True)
            return
        try:
            socketio.emit("object_assigned", data, to=sid)
            print(
                f"[BRIDGE] object_assigned -> sid={sid} player={target_player_id}",
                flush=True,
            )
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_object_assigned: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_exchange_requested(self, data: dict):
        """Private notification to exchange target player."""
        target_player_id = data.get("target_player_id")
        with _sid_lock:
            sid = _player_to_sid.get(target_player_id)
        if not sid:
            print(f"[BRIDGE] player SID not found for {target_player_id}", flush=True)
            return
        try:
            socketio.emit("exchange_requested", data, to=sid)
            print(f"[BRIDGE] exchange_requested -> sid={sid} player={target_player_id}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_exchange_requested: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_exchange_completed(self, data: dict):
        """Public broadcast when both players complete a private hint exchange."""
        try:
            socketio.emit("exchange_completed", data, to=data["room_code"])
            print(f"[BRIDGE] exchange_completed emitted to room {data['room_code']}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_exchange_completed: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_exchange_hints(self, data: dict):
        """Private hint delivery to one exchange participant."""
        target_player_id = data.get("target_player_id")
        with _sid_lock:
            sid = _player_to_sid.get(target_player_id)
        if not sid:
            print(f"[BRIDGE] player SID not found for {target_player_id}", flush=True)
            return
        try:
            socketio.emit("exchange_hints", data, to=sid)
            print(f"[BRIDGE] exchange_hints -> sid={sid} player={target_player_id}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_exchange_hints: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_spy_discovered(self, data: dict):
        """Public broadcast when a spy is discovered during SPY_PHASE."""
        try:
            socketio.emit("spy_discovered", data, to=data["room_code"])
            print(f"[BRIDGE] spy_discovered emitted spy={data.get('spy_name')} to room {data['room_code']}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_spy_discovered: {exc}", flush=True)

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_spy_success(self, data: dict):
        """Private spy success delivery — hints sent only to spy, no public event."""
        target_player_id = data.get("target_player_id")
        with _sid_lock:
            sid = _player_to_sid.get(target_player_id)
        if not sid:
            print(f"[BRIDGE] player SID not found for {target_player_id}", flush=True)
            return
        try:
            socketio.emit("spy_success", data, to=sid)
            print(f"[BRIDGE] spy_success -> sid={sid} spy={target_player_id}", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] ERROR in on_spy_success: {exc}", flush=True)


# ---------------------------------------------------------------------------
# Callback daemon startup — binds receiver to a loopback Pyro5 daemon
# ---------------------------------------------------------------------------

def start_callback_daemon() -> tuple:
    """Start a background Pyro5 daemon hosting BridgeCallbackReceiver.

    Returns (uri_str, daemon) so the caller can pass the URI to GameServer
    and hold a reference to prevent GC of the daemon.
    """
    daemon = Pyro5.api.Daemon(host=config.DAEMON_BIND_HOST)
    receiver = BridgeCallbackReceiver()
    uri = daemon.register(receiver)
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return str(uri), daemon


# ---------------------------------------------------------------------------
# Module-level state (D-07)
# ---------------------------------------------------------------------------

# Maps request.sid → player_id; populated on create_game / join_game (D-07)
_sid_to_player: dict = {}
_player_to_sid: dict = {}
# Lock protecting _sid_to_player from concurrent mutations across handler threads (CR-03)
_sid_lock = threading.Lock()

# Bridge callback URI set in __main__ after start_callback_daemon(); handlers
# read this to pass the bridge's receiver URI to GameServer methods (Pitfall 2)
_cb_uri = ""

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


@socketio.on("create_game")
def handle_create_game(data):
    """Create a new game session and join the Socket.IO room for that session.

    Payload: {player_name: str, max_turns: int}
    Returns (as ack): {player_id, room_code, is_host} or {error: str}
    """
    proxy = get_game_server_proxy()
    result = proxy.create_game(
        data["player_name"], _cb_uri, int(data["max_turns"])
    )
    if "error" not in result:
        with _sid_lock:
            _sid_to_player[request.sid] = result["player_id"]
            _player_to_sid[result["player_id"]] = request.sid
        join_room(result["room_code"])
        print(
            f"[BRIDGE] create_game: player {result['player_id']} "
            f"joined room {result['room_code']}", flush=True
        )
    return result


@socketio.on("join_game")
def handle_join_game(data):
    """Join an existing game session's Socket.IO room.

    Payload: {player_name: str, room_code: str}
    Returns (as ack): {player_id, room_code, is_host} or {error: str}
    """
    proxy = get_game_server_proxy()
    result = proxy.join_game(
        data["player_name"], _cb_uri, data["room_code"]
    )
    if "error" not in result:
        with _sid_lock:
            _sid_to_player[request.sid] = result["player_id"]
            _player_to_sid[result["player_id"]] = request.sid
        join_room(result["room_code"])
        print(
            f"[BRIDGE] join_game: player {result['player_id']} "
            f"joined room {result['room_code']}", flush=True
        )
    return result


@socketio.on("get_players")
def handle_get_players(data):
    """Return the current player list for a room — called by Lobby on mount (CR-01).

    Payload: {room_code: str}
    Returns (as ack): {players: list} or {error: str}
    """
    room_code = (data or {}).get("room_code", "")
    if not room_code:
        return {"error": "room_code required"}
    proxy = get_game_server_proxy()
    result = proxy.get_session(room_code)
    return result


@socketio.on("start_game")
def handle_start_game(data):
    """Request game start — only valid for host with ≥2 players in the session.

    Payload: {} (player_id resolved server-side via _sid_to_player; max_turns
    comes from the session created at create_game time — not from client payload,
    CR-04)
    Returns (as ack): {success: bool} or {error: str}
    """
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "sessao nao encontrada"}
    proxy = get_game_server_proxy()
    success = proxy.start_game(player_id)
    if not success:
        socketio.emit(
            "start_game_error",
            {"error": "Nao autorizado ou jogadores insuficientes"},
            to=request.sid,
        )
    return {"success": success}


@socketio.on("submit_hint")
def handle_submit_hint(data):
    """Submit this player's one-word hint for the active turn."""
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "sessao nao encontrada"}
    proxy = get_game_server_proxy()
    result = proxy.submit_hint(player_id, (data or {}).get("hint_word", ""))
    print(f"[BRIDGE] submit_hint from player {player_id} -> {result}", flush=True)
    return result


@socketio.on("submit_guess")
def handle_submit_guess(data):
    """Submit this player's guess; identity is resolved from SID, never client payload."""
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "sessao nao encontrada"}
    proxy = get_game_server_proxy()
    result = proxy.submit_guess(
        player_id,
        (data or {}).get("target_player_id", ""),
        (data or {}).get("guess_word", ""),
    )
    print(f"[BRIDGE] submit_guess from player {player_id} -> {result}", flush=True)
    return result


@socketio.on("skip_guess")
def handle_skip_guess(data):
    """Skip this player's guess for the active turn."""
    with _sid_lock:
        player_id = _sid_to_player.get(request.sid)
    if not player_id:
        return {"error": "sessao nao encontrada"}
    proxy = get_game_server_proxy()
    result = proxy.skip_guess(player_id)
    print(f"[BRIDGE] skip_guess from player {player_id} -> {result}", flush=True)
    return result


@socketio.on("join_room")
def handle_join_room(data):
    """Join (or rejoin) the Socket.IO room for a given room_code.

    Called by GameScreen on mount so the client starts receiving
    room-scoped phase_changed / game_ended events (D-09).

    Payload: {room_code: str}
    """
    room_code = (data or {}).get("room_code", "")
    player_id = (data or {}).get("player_id", "")
    if not room_code:
        return {"error": "room_code required"}
    join_room(room_code)
    print(f"[BRIDGE] join_room: sid={request.sid} joined room {room_code}", flush=True)
    proxy = get_game_server_proxy()
    if player_id:
        result = proxy.get_player_view(room_code, player_id)
        if "error" not in result:
            with _sid_lock:
                _sid_to_player[request.sid] = player_id
                _player_to_sid[player_id] = request.sid
        return result
    return proxy.get_session(room_code)


@socketio.on("disconnect")
def handle_disconnect(reason):
    """On disconnect, remove player from session via leave_game RPC."""
    with _sid_lock:
        player_id = _sid_to_player.pop(request.sid, None)
        if player_id:
            _player_to_sid.pop(player_id, None)
    if player_id:
        try:
            proxy = get_game_server_proxy()
            proxy.leave_game(player_id)
            print(f"[BRIDGE] disconnect: player {player_id} left (reason: {reason})", flush=True)
        except Exception as exc:
            print(f"[BRIDGE] leave_game failed for {player_id}: {exc}", flush=True)


# ---------------------------------------------------------------------------
# Flask catch-all — serves React SPA for all non-Socket.IO routes (D-10, D-11)
# Registered AFTER socketio init to avoid shadowing Socket.IO routes (Pitfall 3)
# ---------------------------------------------------------------------------

@app.route("/static/images/<path:filename>")
def serve_image(filename):
    """Serve server-controlled object images from the image bank."""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "..", "server", "images"),
        filename,
    )


@app.route("/favicon.ico")
def favicon():
    """Avoid noisy 404s from browsers requesting a favicon during demos."""
    return "", 204


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    """Serve frontend dist assets or fall back to index.html for React Router.

    Uses send_from_directory's built-in path-traversal guard (CR-05).
    The manual os.path.exists check was removed to avoid probing the filesystem
    with unsanitised user-controlled paths.
    """
    if path:
        try:
            return send_from_directory(config.FRONTEND_DIST_PATH, path)
        except Exception:
            pass
    return send_from_directory(config.FRONTEND_DIST_PATH, "index.html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _cb_uri, _daemon = start_callback_daemon()
    print(f"[BRIDGE] Callback receiver URI: {_cb_uri}")

    if not connect_to_game_server(_cb_uri):
        sys.exit(1)

    socketio.run(app, host=config.FLASK_BIND_HOST, port=config.BRIDGE_PORT,
                 allow_unsafe_werkzeug=True)
