"""Phase 7 test stubs — EventBroadcaster failure counter + PLAYER_LEFT broadcast (INFRA-07).

Wave 0: all stubs skip; Wave 1 plan 07-02 replaces pytest.skip with real assertions.

Test coverage:
  test_consecutive_failure_counter    — INFRA-07 / D-08: 3 consecutive failures adds player to failed list
  test_failure_resets_on_success      — INFRA-07 / D-08: successful delivery resets failure counter
  test_player_left_broadcast_on_failure — INFRA-07: PLAYER_LEFT event broadcast with {player_id, player_name, room_code}
"""

import pytest


def test_consecutive_failure_counter():
    """INFRA-07 / D-08: After 3 consecutive transient exceptions on broadcast(), the
    player_id appears in the returned failed list.

    Validates D-08 threshold logic: failure_counts[player_id] >= 3 triggers removal.
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_failure_resets_on_success():
    """INFRA-07 / D-08: After a failure followed by a successful delivery,
    failure_counts[player_id] is not present (reset on success).

    Validates D-08 counter reset behavior: a single successful broadcast
    clears the consecutive-failure counter for that player_id.
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_player_left_broadcast_on_failure():
    """INFRA-07: GameServer._remove_failed_players() is called with the failed list;
    a PLAYER_LEFT event is broadcast with payload {player_id, player_name, room_code}.

    Validates that the PLAYER_LEFT broadcast is triggered when a player exceeds
    the consecutive callback failure threshold (D-08).
    """
    pytest.skip("stub — implemented by plan 07-02")
