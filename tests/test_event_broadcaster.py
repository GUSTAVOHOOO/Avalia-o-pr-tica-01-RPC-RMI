"""Phase 7 tests — EventBroadcaster failure counter + PLAYER_LEFT broadcast (INFRA-07).

Test coverage:
  test_consecutive_failure_counter    — INFRA-07 / D-08: 3 consecutive failures adds player to failed list
  test_failure_resets_on_success      — INFRA-07 / D-08: successful delivery resets failure counter
  test_player_left_broadcast_on_failure — INFRA-07: PLAYER_LEFT event broadcast with {player_id, player_name, room_code}
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from server.event_broadcaster import EventBroadcaster
from server.game_server import GameServer, GameSession, PlayerInfo


def test_consecutive_failure_counter():
    """INFRA-07 / D-08: After 3 consecutive transient exceptions on broadcast(), the
    player_id appears in the returned failed list.

    Validates D-08 threshold logic: failure_counts[player_id] >= 3 triggers removal.
    """
    broadcaster = EventBroadcaster()
    broadcaster.register_callback("player1", "PYRO:fake@127.0.0.1:9999")

    # Patch Pyro5.api.Proxy to raise a transient exception (not ConnectionRefusedError)
    with patch("server.event_broadcaster.Pyro5.api.Proxy") as mock_proxy_cls:
        mock_proxy_cls.return_value.__enter__ = MagicMock(side_effect=Exception("transient"))
        mock_proxy_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First call: count = 1, player not yet failed
        failed1 = broadcaster.broadcast("test_event", {"x": 1})
        assert "player1" not in failed1, "Should not be failed after 1st transient error"

        # Second call: count = 2, still not failed
        failed2 = broadcaster.broadcast("test_event", {"x": 2})
        assert "player1" not in failed2, "Should not be failed after 2nd transient error"

        # Third call: count = 3 → triggers removal
        # Re-register because the broadcaster may have removed the callback earlier
        # (it has not, only at count=3)
        broadcaster.register_callback("player1", "PYRO:fake@127.0.0.1:9999")
        failed3 = broadcaster.broadcast("test_event", {"x": 3})
        assert "player1" in failed3, "Should be in failed list after 3rd consecutive transient error"


def test_failure_resets_on_success():
    """INFRA-07 / D-08: After a failure followed by a successful delivery,
    failure_counts[player_id] is not present (reset on success).

    Validates D-08 counter reset behavior: a single successful broadcast
    clears the consecutive-failure counter for that player_id.
    """
    broadcaster = EventBroadcaster()
    broadcaster.register_callback("player1", "PYRO:fake@127.0.0.1:9999")

    # Induce 2 transient failures
    with patch("server.event_broadcaster.Pyro5.api.Proxy") as mock_proxy_cls:
        mock_proxy_cls.return_value.__enter__ = MagicMock(side_effect=Exception("transient"))
        mock_proxy_cls.return_value.__exit__ = MagicMock(return_value=False)
        broadcaster.broadcast("test_event", {"x": 1})
        broadcaster.broadcast("test_event", {"x": 2})

    assert broadcaster.failure_counts.get("player1", 0) == 2, "Counter should be 2 after 2 failures"

    # Now simulate a successful delivery
    mock_method = MagicMock()
    mock_proxy_instance = MagicMock()
    mock_proxy_instance.__enter__ = MagicMock(return_value=mock_proxy_instance)
    mock_proxy_instance.__exit__ = MagicMock(return_value=False)
    mock_proxy_instance.on_test_event = mock_method

    with patch("server.event_broadcaster.Pyro5.api.Proxy", return_value=mock_proxy_instance):
        failed = broadcaster.broadcast("test_event", {"x": 3})

    assert "player1" not in failed, "Player should not be failed after successful delivery"
    assert "player1" not in broadcaster.failure_counts, (
        "failure_counts should not contain player1 after successful reset"
    )


def test_player_left_broadcast_on_failure():
    """INFRA-07: GameServer._remove_failed_players() is called with the failed list;
    a PLAYER_LEFT event is broadcast with payload {player_id, player_name, room_code}.

    Validates that the PLAYER_LEFT broadcast is triggered when a player exceeds
    the consecutive callback failure threshold (D-08).
    """
    server = GameServer()
    room_code = "ROOM01"
    player_id = "player-abc"
    player_name = "Alice"

    # Manually seed session state (avoid start_game overhead)
    session = GameSession(
        room_code=room_code,
        host_id="host-id",
        max_turns=3,
        status="IN_PROGRESS",
        players=[
            PlayerInfo(player_id="host-id", player_name="Host", callback_uri="PYRO:x@127.0.0.1:1", is_host=True),
            PlayerInfo(player_id=player_id, player_name=player_name, callback_uri="PYRO:x@127.0.0.1:2", is_host=False),
        ],
    )
    server.sessions[room_code] = session
    server._player_to_room[player_id] = room_code

    # Collect "player_left" broadcasts
    player_left_payloads = []
    original_broadcast = server.broadcaster.broadcast

    def capture_broadcast(event_type, data, exclude=None):
        if event_type == "player_left":
            player_left_payloads.append(data)
        return original_broadcast(event_type, data, exclude=exclude)

    server.broadcaster.broadcast = capture_broadcast

    # Call _remove_failed_players directly with our player_id
    server._remove_failed_players([player_id])

    assert len(player_left_payloads) == 1, (
        f"Expected 1 player_left broadcast, got {len(player_left_payloads)}"
    )
    payload = player_left_payloads[0]
    assert payload.get("player_id") == player_id, "player_id mismatch in player_left payload"
    assert payload.get("player_name") == player_name, "player_name mismatch in player_left payload"
    assert payload.get("room_code") == room_code, "room_code mismatch in player_left payload"

    # Player should be removed from session
    remaining_ids = [p.player_id for p in session.players]
    assert player_id not in remaining_ids, "Player should be removed from session.players"
