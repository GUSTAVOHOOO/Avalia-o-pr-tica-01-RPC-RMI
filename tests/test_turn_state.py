"""Wave 0 test stubs for Phase 4 turn-state behavior.

The production modules used by these tests are introduced in later Phase 4
plans. Each test skips before importing those modules so the suite can collect
cleanly while the implementation is still pending.
"""

import pytest


class FakeBroadcaster:
    def __init__(self):
        self.events = []

    def broadcast(self, event_type, data, exclude=None):
        self.events.append({
            "type": event_type,
            "data": data,
        })

    def send_to_player(self, player_id, event_type, data):
        self.events.append({
            "type": event_type,
            "player_id": player_id,
            "data": data,
        })


def test_submit_hint():
    """HINT-01: submit_hint() stores hint word in TurnState.hints_submitted."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    result = server.submit_hint("p1", "red")
    assert result == {"ok": True}, f"submit_hint should accept first hint, got {result}"


def test_submit_hint_duplicate():
    """HINT-01: second submit_hint() call returns already_submitted."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    server.submit_hint("p1", "red")
    result = server.submit_hint("p1", "round")
    assert result == {"error": "already_submitted"}, (
        f"duplicate hint should be rejected, got {result}"
    )


def test_hint_received_payload():
    """HINT-02: HINT_RECEIVED includes counts but not the hint word."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    server.submit_hint("p1", "red")
    event = server.broadcaster.events[-1]["data"]
    assert "hint_word" not in event and event["hints_count"] == 1, (
        f"HINT_RECEIVED should hide hint word and include counts, got {event}"
    )


def test_hint_empty_on_timer():
    """HINT-03: timer expiry fills missing hints with empty strings."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.turn_machine import TurnMachine

    broadcaster = FakeBroadcaster()
    tm = TurnMachine("ROOM1", max_turns=1, broadcaster=broadcaster, player_ids=["p1", "p2"])
    tm.advance_phase_manual()
    assert tm.current_turn_state.hints_submitted["p2"] == "", (
        f"missing hint should be backfilled as empty string, got {tm.current_turn_state.hints_submitted}"
    )


def test_all_hints_auto_advance():
    """HINT-04: all submitted hints auto-advance to GUESS_PHASE."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    server.submit_hint("p1", "red")
    server.submit_hint("p2", "round")
    phases = [e["data"].get("phase") for e in server.broadcaster.events]
    assert "GUESS_PHASE" in phases, f"all hints should auto-advance, got phases {phases}"


def test_submit_guess_correct():
    """GUESS-01: correct case-insensitive guess records the guesser."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    result = server.submit_guess("p1", "p2", "Apple")
    assert result == {"ok": True}, f"correct guess should be accepted, got {result}"


def test_skip_guess():
    """GUESS-02: skip_guess() records None for the player."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    result = server.skip_guess("p1")
    assert result == {"ok": True}, f"skip_guess should return ok, got {result}"


def test_guess_result_broadcast():
    """GUESS-04: GUESS_RESULT includes is_correct and guesser_id."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    server.submit_guess("p1", "p2", "apple")
    event = server.broadcaster.events[-1]["data"]
    assert event["guesser_id"] == "p1" and isinstance(event["is_correct"], bool), (
        f"GUESS_RESULT payload should include guesser_id and is_correct, got {event}"
    )


def test_guess_one_per_turn():
    """GUESS-05: a second submit_guess() call returns already_guessed."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    server.submit_guess("p1", "p2", "apple")
    result = server.submit_guess("p1", "p3", "chair")
    assert result == {"error": "already_guessed"}, (
        f"second guess should be rejected, got {result}"
    )


def test_guess_no_self_target():
    """GUESS-05: self-target guesses return cannot_guess_own_object."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    result = server.submit_guess("p1", "p1", "apple")
    assert result == {"error": "cannot_guess_own_object"}, (
        f"self-target guess should be rejected, got {result}"
    )


def test_image_manifest_load():
    """IMAGE-01: GameServer loads server/images/manifest.json at startup."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    assert server.image_manifest, "image_manifest should be loaded and non-empty"


def test_object_assigned_payload():
    """IMAGE-02: OBJECT_ASSIGNED includes image_url and object_name."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    event = server.broadcaster.events[-1]["data"]
    assert event["image_url"].startswith("/static/images/") and event["object_name"], (
        f"OBJECT_ASSIGNED payload should include static URL and object name, got {event}"
    )


def test_score_updated_payload():
    """SCORE-04: SCORE_UPDATED includes turn number and per-player score rows."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    event = server.broadcaster.events[-1]["data"]
    score = event["scores"][0]
    assert {"player_id", "player_name", "turn_delta", "total"} <= set(score), (
        f"score rows should include player_id, player_name, turn_delta, total, got {score}"
    )


def test_get_scores():
    """SCORE-05: get_scores() returns integer totals keyed by player_id."""
    pytest.skip("Wave 0 stub - implement in Plan 02/03")
    from server.game_server import GameServer

    server = GameServer()
    scores = server.get_scores("p1")
    assert all(isinstance(total, int) for total in scores.values()), (
        f"get_scores should return integer totals, got {scores}"
    )
