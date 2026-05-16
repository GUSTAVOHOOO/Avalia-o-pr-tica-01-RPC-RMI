"""Phase 7 test stubs — reconnect_player RPC (INFRA-08).

Wave 0: all stubs skip; Wave 1 plan 07-02 replaces pytest.skip with real assertions.

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
    pytest.skip("stub — implemented by plan 07-02")


def test_reconnect_player_unknown_uuid():
    """INFRA-08: reconnect_player("invalid-uuid", "ROOM01", "PYRO:x@127.0.0.1:0")
    returns {"error": ...}.

    Validates server-side UUID validation: unknown player_id must not be
    re-registered or granted a reconnect state response.
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_reconnect_player_updates_callback_uri():
    """INFRA-08 / D-02: After reconnect_player(), broadcaster.callbacks[player_id]
    equals the new callback_uri.

    Validates that the callback URI is re-registered for the reconnecting player
    so future broadcasts reach their new bridge session.
    """
    pytest.skip("stub — implemented by plan 07-02")
