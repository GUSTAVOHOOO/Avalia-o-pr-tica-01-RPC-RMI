"""Unit tests for Phase 4 turn-state behavior."""

from server.game_server import GameServer
from server.turn_machine import TurnMachine
from server.turn_state import TurnState


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


def _server_with_turn_state(phase="HINT_PHASE"):
    server = GameServer()
    host = server.create_game("Alice", "PYRO:fake.alice@127.0.0.1:9999", 3)
    join = server.join_game("Bob", "PYRO:fake.bob@127.0.0.1:9999", host["room_code"])
    player_ids = [host["player_id"], join["player_id"]]
    server.broadcaster = FakeBroadcaster()
    session = server.sessions[host["room_code"]]
    session.turn_machine = TurnMachine(
        host["room_code"],
        max_turns=3,
        broadcaster=server.broadcaster,
        player_ids=player_ids,
    )
    session.turn_machine.current_phase = phase
    session.turn_machine.current_turn_state = TurnState(
        turn_number=1,
        player_ids=player_ids,
        image_assignments={
            host["player_id"]: "apple",
            join["player_id"]: "bicycle",
        },
    )
    return server, session, host["player_id"], join["player_id"]


def test_submit_hint():
    """HINT-01: submit_hint() stores hint word in TurnState.hints_submitted."""
    server, session, player_id, _other_id = _server_with_turn_state()

    result = server.submit_hint(player_id, " red ")

    assert result == {"ok": True}, f"submit_hint should accept first hint, got {result}"
    assert session.turn_machine.current_turn_state.hints_submitted[player_id] == "red", (
        f"hint should be stripped and stored, got {session.turn_machine.current_turn_state.hints_submitted}"
    )


def test_submit_hint_duplicate():
    """HINT-01: second submit_hint() call returns already_submitted."""
    server, _session, player_id, _other_id = _server_with_turn_state()

    server.submit_hint(player_id, "red")
    result = server.submit_hint(player_id, "round")

    assert result == {"error": "already_submitted"}, (
        f"duplicate hint should be rejected, got {result}"
    )


def test_hint_received_payload():
    """HINT-02: HINT_RECEIVED includes counts but not the hint word."""
    server, _session, player_id, _other_id = _server_with_turn_state()

    server.submit_hint(player_id, "red")
    event = server.broadcaster.events[-1]["data"]

    assert "hint_word" not in event, f"HINT_RECEIVED must not reveal hint word, got {event}"
    assert event["hints_count"] == 1 and event["total_players"] == 2, (
        f"HINT_RECEIVED should include counts, got {event}"
    )


def test_hint_empty_on_timer():
    """HINT-03: timer expiry fills missing hints with empty strings."""
    broadcaster = FakeBroadcaster()
    tm = TurnMachine("ROOM1", max_turns=1, broadcaster=broadcaster, player_ids=["p1", "p2"])
    tm.start()
    tm.advance_phase_manual()
    tm.advance_phase_manual()

    assert tm.current_turn_state.hints_submitted["p2"] == "", (
        f"missing hint should be backfilled as empty string, got {tm.current_turn_state.hints_submitted}"
    )


def test_all_hints_auto_advance():
    """HINT-04: all submitted hints auto-advance to GUESS_PHASE."""
    server, session, player_id, other_id = _server_with_turn_state()

    server.submit_hint(player_id, "red")
    server.submit_hint(other_id, "round")

    assert session.turn_machine.current_phase == "GUESS_PHASE", (
        f"all hints should auto-advance to GUESS_PHASE, got {session.turn_machine.current_phase}"
    )


def test_submit_guess_correct():
    """GUESS-01: correct case-insensitive guess records the guesser."""
    server, session, player_id, other_id = _server_with_turn_state("GUESS_PHASE")

    result = server.submit_guess(player_id, other_id, "Bicycle")

    assert result == {"ok": True, "is_correct": True}, f"correct guess should be accepted, got {result}"
    assert player_id in session.turn_machine.current_turn_state.correct_guesses, (
        f"correct guesser should be recorded, got {session.turn_machine.current_turn_state.correct_guesses}"
    )


def test_skip_guess():
    """GUESS-02: skip_guess() records None for the player."""
    server, session, player_id, _other_id = _server_with_turn_state("GUESS_PHASE")

    result = server.skip_guess(player_id)

    assert result == {"ok": True}, f"skip_guess should return ok, got {result}"
    assert session.turn_machine.current_turn_state.guesses_made[player_id] is None, (
        f"skip should record None, got {session.turn_machine.current_turn_state.guesses_made}"
    )


def test_guess_result_broadcast():
    """GUESS-04: GUESS_RESULT includes is_correct and guesser_id."""
    server, _session, player_id, other_id = _server_with_turn_state("GUESS_PHASE")

    server.submit_guess(player_id, other_id, "bicycle")
    event = server.broadcaster.events[-1]["data"]

    assert event["guesser_id"] == player_id and isinstance(event["is_correct"], bool), (
        f"GUESS_RESULT payload should include guesser_id and is_correct, got {event}"
    )


def test_guess_one_per_turn():
    """GUESS-05: a second submit_guess() call returns already_guessed."""
    server, _session, player_id, other_id = _server_with_turn_state("GUESS_PHASE")

    server.submit_guess(player_id, other_id, "bicycle")
    result = server.submit_guess(player_id, other_id, "chair")

    assert result == {"error": "already_guessed"}, (
        f"second guess should be rejected, got {result}"
    )


def test_guess_no_self_target():
    """GUESS-05: self-target guesses return cannot_guess_own_object."""
    server, _session, player_id, _other_id = _server_with_turn_state("GUESS_PHASE")

    result = server.submit_guess(player_id, player_id, "apple")

    assert result == {"error": "cannot_guess_own_object"}, (
        f"self-target guess should be rejected, got {result}"
    )


def test_image_manifest_load():
    """IMAGE-01: GameServer loads server/images/manifest.json at startup."""
    server = GameServer()

    assert len(server._image_manifest) >= 8, (
        f"_image_manifest should have at least 8 entries, got {len(server._image_manifest)}"
    )
    assert all(isinstance(value, str) and value for value in server._image_manifest.values()), (
        f"manifest object names should be non-empty strings, got {server._image_manifest}"
    )


def test_object_assigned_payload():
    """IMAGE-02: OBJECT_ASSIGNED includes image_url and object_name."""
    server = GameServer()
    host = server.create_game("Alice", "PYRO:fake.alice@127.0.0.1:9999", 3)
    server.join_game("Bob", "PYRO:fake.bob@127.0.0.1:9999", host["room_code"])
    server.broadcaster = FakeBroadcaster()

    server._assign_images_for_turn(host["room_code"])
    object_events = [e for e in server.broadcaster.events if e["type"] == "object_assigned"]

    assert len(object_events) == 2, f"expected 2 object_assigned events, got {object_events}"
    event = object_events[0]["data"]
    assert event["image_url"].startswith("/static/images/") and event["object_name"], (
        f"OBJECT_ASSIGNED payload should include static URL and object name, got {event}"
    )


def test_get_player_view_returns_current_object_assignment():
    """IMAGE-02: reconnecting GameScreen can recover its private object assignment."""
    server, session, player_id, _other_id = _server_with_turn_state("HINT_PHASE")

    result = server.get_player_view(session.room_code, player_id)

    assert result["object_assignment"] == {
        "image_url": "/static/images/apple.jpg",
        "object_name": "apple",
    }, f"player view should include current private assignment, got {result}"


def test_score_updated_payload():
    """SCORE-04: SCORE_UPDATED includes turn number and per-player score rows."""
    server, session, player_id, other_id = _server_with_turn_state("SCORING_PHASE")
    turn_state = session.turn_machine.current_turn_state
    turn_state.guesses_made = {player_id: other_id}
    turn_state.correct_guesses = [player_id]

    server._accumulate_scores(session.room_code, turn_state)
    event = server.broadcaster.events[-1]["data"]
    score = event["scores"][0]

    assert event["turn_number"] == 1, f"score event should include turn_number, got {event}"
    assert {"player_id", "player_name", "turn_delta", "total"} <= set(score), (
        f"score rows should include player_id, player_name, turn_delta, total, got {score}"
    )


def test_get_scores():
    """SCORE-05: get_scores() returns integer totals keyed by player_id."""
    server, session, player_id, other_id = _server_with_turn_state("GUESS_PHASE")
    session.accumulated_scores[player_id] = 20
    session.accumulated_scores[other_id] = -10

    result = server.get_scores(player_id)

    assert result == {"scores": {player_id: 20, other_id: -10}}, (
        f"get_scores should return accumulated scores, got {result}"
    )
