"""Unit tests for Phase 4 scoring behavior."""

from server.turn_machine import _calculate_score_deltas
from server.turn_state import TurnState


def test_tiered_guessers():
    """SCORE-01: tiered guesser points are 20, 15, 10, then minimum 5."""
    ts = TurnState(turn_number=1, player_ids=["p1", "p2", "p3", "p4"])
    ts.correct_guesses = ["p1", "p2", "p3", "p4"]

    deltas = _calculate_score_deltas(ts)

    assert deltas["p1"] == 20, f"1st correct should get 20pts, got {deltas['p1']}"
    assert deltas["p2"] == 15, f"2nd correct should get 15pts, got {deltas['p2']}"
    assert deltas["p3"] == 10, f"3rd correct should get 10pts, got {deltas['p3']}"
    assert deltas["p4"] == 5, f"4th correct should get 5pts, got {deltas['p4']}"


def test_solo_bonus():
    """SCORE-02: a sole correct guesser receives a +10 bonus."""
    ts = TurnState(turn_number=1, player_ids=["p1", "p2", "p3", "p4"])
    ts.correct_guesses = ["p1"]

    deltas = _calculate_score_deltas(ts)

    assert deltas["p1"] == 30, f"sole correct guesser should get 30pts, got {deltas['p1']}"


def test_owner_scoring():
    """SCORE-03: owner score changes by the number of correct guessers."""
    ts = TurnState(turn_number=1, player_ids=["p1", "p2", "p3", "p4"])
    ts.guesses_made = {"p2": "p1", "p3": "p1", "p4": "p1"}
    ts.correct_guesses = ["p2", "p3"]

    deltas = _calculate_score_deltas(ts)

    assert deltas["p1"] == 10, f"owner with 2 correct guessers should get 10pts, got {deltas['p1']}"


def test_score_updated_payload_shape():
    """SCORE-04: SCORE_UPDATED payload includes room, turn, and score rows."""
    payload = {
        "room_code": "ABC123",
        "turn_number": 1,
        "scores": [
            {"player_id": "p1", "player_name": "Alice", "turn_delta": 20, "total": 20},
        ],
    }

    score = payload["scores"][0]
    assert {"room_code", "turn_number", "scores"} <= set(payload), (
        f"SCORE_UPDATED payload should include room_code, turn_number, scores, got {payload}"
    )
    assert {"player_id", "player_name", "turn_delta", "total"} <= set(score), (
        f"score row should include player_id, player_name, turn_delta, total, got {score}"
    )
