"""Phase 2 unit tests — session management (SESSION-01 through SESSION-06).

Each test exercises Pyro5 RPC in-process using a real daemon in a background thread.
No mocks, no Name Server required.

Test coverage:
  test_create_game              — SESSION-01: create_game() returns {player_id, room_code, is_host=True} and stores session
  test_room_code_format         — SESSION-02: room_code is 6 uppercase alphanumeric; two calls return different codes
  test_join_game                — SESSION-03: join_game() returns {player_id, room_code, is_host=False} for valid WAITING room
  test_join_rejected_if_started — SESSION-04: join_game() returns {"error": "jogo em andamento"} when status != WAITING
  test_player_joined_broadcast  — SESSION-05: join_game() triggers PLAYER_JOINED broadcast delivered to registered callback
  test_start_game_validation    — SESSION-06: start_game() returns True only for host with ≥2 players; False otherwise
  test_host_transfer_on_leave   — SESSION-07: leave_game() transfers host to next player and broadcasts HOST_CHANGED
"""

import re
import threading

import pytest
import Pyro5.api
import Pyro5.errors

from server.game_server import GameServer


# ---------------------------------------------------------------------------
# Helper: start an in-process Pyro5 daemon for a single object
# ---------------------------------------------------------------------------

def _start_daemon(obj, object_id: str):
    """Register obj in a new daemon and start requestLoop in a daemon thread.

    Returns (daemon, uri_str).
    """
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    uri = daemon.register(obj, objectId=object_id)
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return daemon, str(uri)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_game():
    """SESSION-01: create_game() returns {player_id, room_code, is_host: True} and stores session."""
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.gs.create")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            result = proxy.create_game("Alice", "PYRO:fake.cb@127.0.0.1:9999", 5)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "player_id" in result, "Missing player_id in result"
        assert "room_code" in result, "Missing room_code in result"
        assert "is_host" in result, "Missing is_host in result"

        assert result["player_id"], "player_id must be a non-empty string"
        assert isinstance(result["player_id"], str), "player_id must be str"
        assert len(result["room_code"]) == 6, f"room_code must be 6 chars, got {len(result['room_code'])}"
        assert result["is_host"] is True, f"is_host must be True, got {result['is_host']}"

        room_code = result["room_code"]
        assert room_code in server.sessions, "Session not stored in server.sessions"
        session = server.sessions[room_code]
        assert session.status == "WAITING", f"Expected status WAITING, got {session.status}"
        assert session.player_count == 1, f"Expected 1 player, got {session.player_count}"
    finally:
        daemon.shutdown()


def test_room_code_format():
    """SESSION-02: room_code is 6 uppercase alphanumeric chars; two calls produce different codes."""
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.gs.room_code")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            result1 = proxy.create_game("Alice", "PYRO:fake.cb@127.0.0.1:9999", 5)
            result2 = proxy.create_game("Bob", "PYRO:fake.cb@127.0.0.1:9999", 5)

        code1 = result1["room_code"]
        code2 = result2["room_code"]

        assert re.match(r"^[A-Z0-9]{6}$", code1), f"room_code '{code1}' does not match ^[A-Z0-9]{{6}}$"
        assert re.match(r"^[A-Z0-9]{6}$", code2), f"room_code '{code2}' does not match ^[A-Z0-9]{{6}}$"
        assert code1 != code2, f"Two create_game calls returned the same room_code: {code1}"
    finally:
        daemon.shutdown()


def test_join_game():
    """SESSION-03: join_game() returns {player_id, room_code, is_host=False} for valid WAITING session."""
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.gs.join")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            create_result = proxy.create_game("Alice", "PYRO:fake.cb@127.0.0.1:9999", 5)
            room_code = create_result["room_code"]

            join_result = proxy.join_game("Bob", "PYRO:fake.cb@127.0.0.1:9999", room_code)

        assert isinstance(join_result, dict), f"Expected dict, got {type(join_result)}"
        assert "error" not in join_result, f"Unexpected error: {join_result.get('error')}"
        assert "player_id" in join_result, "Missing player_id in join result"
        assert "room_code" in join_result, "Missing room_code in join result"
        assert "is_host" in join_result, "Missing is_host in join result"

        assert join_result["room_code"] == room_code, "room_code in join result must match original"
        assert join_result["is_host"] is False, f"is_host must be False for joining player, got {join_result['is_host']}"

        session = server.sessions[room_code]
        assert session.player_count == 2, f"Expected 2 players after join, got {session.player_count}"
    finally:
        daemon.shutdown()


def test_join_rejected_if_started():
    """SESSION-04: join_game() returns {"error": "jogo em andamento"} when status != WAITING."""
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.gs.join_reject")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            create_result = proxy.create_game("Alice", "PYRO:fake.cb@127.0.0.1:9999", 5)
            room_code = create_result["room_code"]

        # Manually set session status to IN_PROGRESS on the server object directly
        server.sessions[room_code].status = "IN_PROGRESS"

        with Pyro5.api.Proxy(uri) as proxy:
            join_result = proxy.join_game("Bob", "PYRO:fake.cb@127.0.0.1:9999", room_code)

        assert isinstance(join_result, dict), f"Expected dict, got {type(join_result)}"
        assert "error" in join_result, "Expected 'error' key in result when game is in progress"
        assert join_result["error"] == "jogo em andamento", (
            f"Expected error 'jogo em andamento', got '{join_result['error']}'"
        )
    finally:
        daemon.shutdown()


def test_player_joined_broadcast():
    """SESSION-05: join_game() triggers PLAYER_JOINED broadcast delivered to registered callback."""

    @Pyro5.api.expose
    class TestCallbackReceiver:
        """Minimal callback receiver that collects player_joined events."""

        def __init__(self):
            self.received = []
            self.event = threading.Event()

        def on_player_joined(self, data):
            self.received.append(data)
            self.event.set()

    server = GameServer()
    server_daemon, server_uri = _start_daemon(server, "test.gs.broadcast")

    receiver = TestCallbackReceiver()
    cb_daemon, cb_uri = _start_daemon(receiver, "test.gs.cb.receiver")

    try:
        with Pyro5.api.Proxy(server_uri) as proxy:
            create_result = proxy.create_game("Alice", cb_uri, 5)
            room_code = create_result["room_code"]

            proxy.join_game("Bob", cb_uri, room_code)

        # Wait until on_player_joined signals delivery (up to 5 s)
        delivered = receiver.event.wait(timeout=5)
        assert delivered, "Timed out waiting for PLAYER_JOINED broadcast delivery (>5 s)"

        assert len(receiver.received) >= 1, (
            f"Expected at least 1 received event, got {len(receiver.received)}"
        )
        # The broadcast payload must contain room_code
        assert "room_code" in receiver.received[0], (
            f"Expected 'room_code' in broadcast payload, got {receiver.received[0]!r}"
        )
    finally:
        server_daemon.shutdown()
        cb_daemon.shutdown()


def test_start_game_validation():
    """SESSION-06: start_game() returns True only for host with ≥2 players; False otherwise."""
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.gs.start_game")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            create_result = proxy.create_game("Alice", "PYRO:fake.cb@127.0.0.1:9999", 5)
            host_player_id = create_result["player_id"]
            room_code = create_result["room_code"]

            # Only 1 player — start_game must return False even for host
            result_one_player = proxy.start_game(host_player_id)
            assert result_one_player is False, (
                f"start_game must return False with only 1 player, got {result_one_player}"
            )

            # Add second player
            join_result = proxy.join_game("Bob", "PYRO:fake.cb@127.0.0.1:9999", room_code)
            non_host_player_id = join_result["player_id"]

            # Non-host tries to start — must return False
            result_non_host = proxy.start_game(non_host_player_id)
            assert result_non_host is False, (
                f"start_game must return False for non-host player, got {result_non_host}"
            )

            # Host with 2 players — must return True
            result_host = proxy.start_game(host_player_id)
            assert result_host is True, (
                f"start_game must return True for host with ≥2 players, got {result_host}"
            )
    finally:
        daemon.shutdown()


def test_host_transfer_on_leave():
    """SESSION-07: leave_game() transfers host to next player and broadcasts HOST_CHANGED.

    Setup: 2-player session (Player A as host, Player B as non-host).
    Action: Player A calls leave_game().
    Assertions:
      - session.host_id == player_B_id (host transferred to remaining player)
      - A HOST_CHANGED broadcast was received by a registered callback with
        keys {new_host_id, room_code}

    Validates SESSION-07 host-transfer-on-leave behavior.
    """
    pytest.skip("stub — implemented by plan 07-02")
