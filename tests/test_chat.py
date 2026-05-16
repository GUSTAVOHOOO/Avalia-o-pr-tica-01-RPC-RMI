"""Phase 7 test stubs — in-game chat (CHAT-01, CHAT-02).

Wave 0: all stubs skip; Wave 1 plan 07-02 replaces pytest.skip with real assertions.

Test coverage:
  test_send_chat_returns_ok           — CHAT-01: send_chat() returns {"ok": True} for valid player
  test_send_chat_broadcasts_payload   — CHAT-02: broadcast called with "chat_message" event and full payload
  test_send_chat_message_length_cap   — CHAT-01: message truncated to 200 chars in broadcast payload
  test_send_chat_unknown_player       — CHAT-01: unknown player_id returns {"error": ...}
"""

import pytest


def test_send_chat_returns_ok():
    """CHAT-01: send_chat(player_id, "hello") for a player in a valid session
    returns {"ok": True}.

    Validates the happy path: a known player in an active session can send
    a chat message and receives a success acknowledgment.
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_send_chat_broadcasts_payload():
    """CHAT-02: broadcast() is called once with event_type "chat_message" and
    data containing keys {"player_id", "player_name", "message", "timestamp", "room_code"}.

    Validates that the chat fan-out delivers the full required payload to all
    players in the room (CHAT-02 broadcast spec).
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_send_chat_message_length_cap():
    """CHAT-01: A message of 300 characters is truncated to 200 in the broadcast payload.

    Validates the length cap specified in CHAT-01: messages exceeding 200 characters
    are silently truncated before broadcast to prevent chat spam.
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_send_chat_unknown_player():
    """CHAT-01: send_chat("unknown-id", "msg") returns {"error": ...}.

    Validates player validation: a player_id not present in any active session
    cannot send a chat message, preventing unauthorized message injection.
    """
    pytest.skip("stub — implemented by plan 07-02")
