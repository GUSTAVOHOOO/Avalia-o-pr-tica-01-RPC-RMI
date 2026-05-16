"""Phase 7 test stubs — post-game flow (POSTGAME-01 through POSTGAME-04).

Wave 0: all stubs skip; Wave 1 plan 07-02 replaces pytest.skip with real assertions.

Test coverage:
  test_turn_score_history_appended    — POSTGAME-01: per-turn score history entry shape
  test_vote_started_broadcast         — POSTGAME-02: _start_vote() broadcasts vote_started event
  test_vote_majority_yes_restarts     — POSTGAME-03: majority yes triggers GAME_RESTARTING
  test_vote_no_majority_ends_game     — POSTGAME-04: no majority triggers GAME_ENDED
  test_vote_timer_expiry_ends_game    — POSTGAME-04 (timer path): 30s expiry without votes ends game
  test_duplicate_vote_ignored         — vote stuffing guard: second vote from same player is ignored
"""

import pytest


def test_turn_score_history_appended():
    """POSTGAME-01: After one turn's scoring phase, session.turn_score_history has
    one entry shaped {"turn": 1, "scores": {player_id: int}}.

    Validates that per-turn score data is accumulated in the session for the
    post-game podium table (POSTGAME-01 data availability).
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_vote_started_broadcast():
    """POSTGAME-02: _start_vote() broadcasts a "vote_started" event with keys
    {"room_code", "duration_seconds", "player_count"}.

    Validates that all players receive the vote prompt with the correct
    metadata to render a 30-second countdown timer.
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_vote_majority_yes_restarts():
    """POSTGAME-03: With 2 players both submitting continue_game=True,
    _resolve_vote() broadcasts "game_restarting" and session.vote_record is None.

    Validates the happy path: strict majority (both players vote yes with 2 players)
    triggers a game restart with new image assignments and clears the vote state.
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_vote_no_majority_ends_game():
    """POSTGAME-04: With 2 players where only 1 votes True (minority),
    _resolve_vote() broadcasts "game_ended" with keys {"final_scores", "turn_score_history"}.

    Validates that failing to reach strict majority (1/2 votes yes) ends the game
    and delivers full score history in the broadcast payload.
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_vote_timer_expiry_ends_game():
    """POSTGAME-04 (timer path): A VoteRecord with 30s timer that fires without
    any votes results in "game_ended" broadcast.

    Validates that timer expiry without sufficient votes correctly ends the game
    (abstentions count as implicit "no" votes).
    """
    pytest.skip("stub — implemented by plan 07-02")


def test_duplicate_vote_ignored():
    """Vote stuffing guard: A second submit_vote() from the same player_id returns
    {"ok": True, "duplicate": True} and does not change yes_count.

    Validates that a player cannot vote multiple times to influence the outcome
    (POSTGAME-03/04 integrity).
    """
    pytest.skip("stub — implemented by plan 07-02")
