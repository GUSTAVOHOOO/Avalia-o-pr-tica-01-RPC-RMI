"""Phase 7 tests — reconnect_player RPC (INFRA-08).

Uses the same _start_daemon helper pattern as test_session.py:
  - Real in-process Pyro5 daemon started in a background thread
  - No mocks, no Name Server required

Test coverage:
  test_reconnect_player_returns_player_view   — INFRA-08 / D-03: reconnect returns get_player_view() shape
  test_reconnect_player_unknown_uuid          — INFRA-08: unknown player_id returns {"error": ...}
  test_reconnect_player_updates_callback_uri  — INFRA-08 / D-02: callback re-registered with new URI
"""

import threading

import pytest
import Pyro5.api

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

def test_reconnect_player_returns_player_view():
    """INFRA-08 / D-03: reconnect_player(player_id, room_code, cb_uri) on a server
    with an active session returns a dict containing keys "phase", "players",
    "room_code" (same shape as get_player_view).

    Validates that reconnect state delivery reuses get_player_view() without
    introducing a new data structure.
    """
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.gs.reconnect.view")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            # Create a 2-player session and start the game so get_player_view returns phase info
            result_a = proxy.create_game("Alice", "PYRO:fake@127.0.0.1:9999", 3)
            player_a_id = result_a["player_id"]
            room_code = result_a["room_code"]

            proxy.join_game("Bob", "PYRO:fake@127.0.0.1:9999", room_code)

            # Call reconnect_player with the existing player's id
            reconnect_result = proxy.reconnect_player(
                player_a_id, room_code, "PYRO:new_cb@127.0.0.1:9998"
            )

        assert isinstance(reconnect_result, dict), (
            f"Expected dict, got {type(reconnect_result)}"
        )
        assert "error" not in reconnect_result, (
            f"Unexpected error: {reconnect_result.get('error')}"
        )
        assert "players" in reconnect_result, "Missing 'players' key in reconnect result"
        assert "room_code" in reconnect_result, "Missing 'room_code' key in reconnect result"
        assert reconnect_result["room_code"] == room_code, "room_code mismatch"
    finally:
        daemon.shutdown()


def test_reconnect_player_unknown_uuid():
    """INFRA-08: reconnect_player("invalid-uuid", "ROOM01", "PYRO:x@127.0.0.1:0")
    returns {"error": ...}.

    Validates server-side UUID validation: unknown player_id must not be
    re-registered or granted a reconnect state response.
    """
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.gs.reconnect.unknown")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            # Create a session to have at least one room
            result = proxy.create_game("Alice", "PYRO:fake@127.0.0.1:9999", 3)
            room_code = result["room_code"]

            # Unknown player_id
            reconnect_result = proxy.reconnect_player(
                "unknown-player-id", room_code, "PYRO:fake@127.0.0.1:9999"
            )

        assert isinstance(reconnect_result, dict), (
            f"Expected dict, got {type(reconnect_result)}"
        )
        assert "error" in reconnect_result, (
            "Expected 'error' key for unknown player_id, got none"
        )
    finally:
        daemon.shutdown()


def test_reconnect_player_updates_callback_uri():
    """INFRA-08 / D-02: After reconnect_player(), broadcaster.callbacks[player_id]
    equals the new callback_uri.

    Validates that the callback URI is re-registered for the reconnecting player
    so future broadcasts reach their new bridge session.
    """
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.gs.reconnect.uri")
    new_callback_uri = "PYRO:new_callback@127.0.0.1:12345"
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            result = proxy.create_game("Alice", "PYRO:old_cb@127.0.0.1:9999", 3)
            player_id = result["player_id"]
            room_code = result["room_code"]

            proxy.join_game("Bob", "PYRO:fake@127.0.0.1:9999", room_code)

            proxy.reconnect_player(player_id, room_code, new_callback_uri)

        # Check the broadcaster's callback dict directly on the server object
        assert server.broadcaster.callbacks.get(player_id) == new_callback_uri, (
            f"Expected callback URI to be '{new_callback_uri}', "
            f"got '{server.broadcaster.callbacks.get(player_id)}'"
        )
    finally:
        daemon.shutdown()
