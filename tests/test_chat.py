"""Phase 7 tests — in-game chat (CHAT-01, CHAT-02).

Test coverage:
  test_send_chat_returns_ok           — CHAT-01: send_chat() returns {"ok": True} for valid player
  test_send_chat_broadcasts_payload   — CHAT-02: broadcast called with "chat_message" event and full payload
  test_send_chat_message_length_cap   — CHAT-01: message truncated to 200 chars in broadcast payload
  test_send_chat_unknown_player       — CHAT-01: unknown player_id returns {"error": ...}
"""

import pytest

from server.game_server import GameServer, GameSession, PlayerInfo


def _make_server_with_player(player_id="player-abc", player_name="Alice", room_code="CHAT01"):
    """Create a GameServer with a minimal 1-player session for chat tests."""
    server = GameServer()
    session = GameSession(
        room_code=room_code,
        host_id=player_id,
        max_turns=3,
        status="IN_PROGRESS",
        players=[
            PlayerInfo(
                player_id=player_id,
                player_name=player_name,
                callback_uri="PYRO:fake@127.0.0.1:9999",
                is_host=True,
            )
        ],
    )
    server.sessions[room_code] = session
    server._player_to_room[player_id] = room_code
    server.broadcaster.register_callback(player_id, "PYRO:fake@127.0.0.1:9999")
    return server


def test_send_chat_returns_ok():
    """CHAT-01: send_chat(player_id, "hello") for a player in a valid session
    returns {"ok": True}.

    Validates the happy path: a known player in an active session can send
    a chat message and receives a success acknowledgment.
    """
    server = _make_server_with_player()

    # Patch broadcast to avoid real network I/O
    captured = []
    original_broadcast = server.broadcaster.broadcast

    def mock_broadcast(event_type, data, exclude=None):
        captured.append((event_type, data))
        return []  # no failures

    server.broadcaster.broadcast = mock_broadcast

    result = server.send_chat("player-abc", "hello")
    assert result == {"ok": True}, f"Expected {{'ok': True}}, got {result}"


def test_send_chat_broadcasts_payload():
    """CHAT-02: broadcast() is called once with event_type "chat_message" and
    data containing keys {"player_id", "player_name", "message", "timestamp", "room_code"}.

    Validates that the chat fan-out delivers the full required payload to all
    players in the room (CHAT-02 broadcast spec).
    """
    server = _make_server_with_player(player_id="player-abc", player_name="Alice", room_code="CHAT01")

    captured = []

    def mock_broadcast(event_type, data, exclude=None):
        captured.append((event_type, data))
        return []

    server.broadcaster.broadcast = mock_broadcast

    server.send_chat("player-abc", "hello world")

    chat_events = [(et, d) for et, d in captured if et == "chat_message"]
    assert len(chat_events) == 1, f"Expected 1 chat_message broadcast, got {len(chat_events)}"

    payload = chat_events[0][1]
    required_keys = {"player_id", "player_name", "message", "timestamp", "room_code"}
    missing = required_keys - set(payload.keys())
    assert not missing, f"chat_message payload missing keys: {missing}"

    assert payload["player_id"] == "player-abc", "player_id mismatch"
    assert payload["player_name"] == "Alice", "player_name mismatch"
    assert payload["message"] == "hello world", "message mismatch"
    assert payload["room_code"] == "CHAT01", "room_code mismatch"
    assert isinstance(payload["timestamp"], float), "timestamp should be a float"


def test_send_chat_message_length_cap():
    """CHAT-01: A message of 300 characters is truncated to 200 in the broadcast payload.

    Validates the length cap specified in CHAT-01: messages exceeding 200 characters
    are silently truncated before broadcast to prevent chat spam.
    """
    server = _make_server_with_player()

    captured = []

    def mock_broadcast(event_type, data, exclude=None):
        captured.append((event_type, data))
        return []

    server.broadcaster.broadcast = mock_broadcast

    long_message = "A" * 300
    server.send_chat("player-abc", long_message)

    chat_events = [(et, d) for et, d in captured if et == "chat_message"]
    assert len(chat_events) == 1, "Expected exactly 1 chat_message broadcast"

    payload = chat_events[0][1]
    assert len(payload["message"]) == 200, (
        f"Expected message length 200, got {len(payload['message'])}"
    )
    assert payload["message"] == "A" * 200, "Truncated message content mismatch"


def test_send_chat_unknown_player():
    """CHAT-01: send_chat("unknown-id", "msg") returns {"error": ...}.

    Validates player validation: a player_id not present in any active session
    cannot send a chat message, preventing unauthorized message injection.
    """
    server = _make_server_with_player()

    result = server.send_chat("unknown-player-id", "hello")

    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "error" in result, "Expected 'error' key for unknown player, got none"
