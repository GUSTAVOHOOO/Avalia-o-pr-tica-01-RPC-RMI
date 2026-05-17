"""Unit tests for Phase 4 turn-state behavior (+ Phase 5 ExchangeRecord additions)."""

import time

import config
from server.game_server import GameServer
from server.turn_machine import TurnMachine
from server.turn_state import TurnState, ExchangeRecord


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
    session.turn_machine._phase_start_time = time.monotonic()
    session.turn_machine.current_turn_state = TurnState(
        turn_number=1,
        player_ids=player_ids,
        image_assignments={
            host["player_id"]: "maçã",
            join["player_id"]: "bicicleta",
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


def test_all_hints_shortens_timer_then_advances():
    """HINT-04: all submitted hints shorten the timer before GUESS_PHASE."""
    original_grace = config.PHASE_COMPLETION_GRACE_SECONDS
    config.PHASE_COMPLETION_GRACE_SECONDS = 0.05
    server, session, player_id, other_id = _server_with_turn_state()

    try:
        server.submit_hint(player_id, "red")
        server.submit_hint(other_id, "round")

        assert session.turn_machine.current_phase == "HINT_PHASE"
        assert server.broadcaster.events[-1]["type"] == "phase_timer_shortened"
        time.sleep(0.12)
        assert session.turn_machine.current_phase == "GUESS_PHASE", (
            f"all hints should advance to GUESS_PHASE after grace timer, got {session.turn_machine.current_phase}"
        )
    finally:
        config.PHASE_COMPLETION_GRACE_SECONDS = original_grace


def test_submit_guess_correct():
    """GUESS-01: correct case-insensitive guess records the guesser."""
    server, session, player_id, other_id = _server_with_turn_state("GUESS_PHASE")

    result = server.submit_guess(player_id, other_id, "Bicicleta")

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


def test_all_guesses_shortens_timer_then_advances():
    """GUESS-03: all guessed/skipped players shorten the timer before EXCHANGE_PHASE."""
    original_grace = config.PHASE_COMPLETION_GRACE_SECONDS
    config.PHASE_COMPLETION_GRACE_SECONDS = 0.05
    server, session, player_id, other_id = _server_with_turn_state("GUESS_PHASE")

    try:
        server.submit_guess(player_id, other_id, "bicicleta")
        server.skip_guess(other_id)

        assert session.turn_machine.current_phase == "GUESS_PHASE"
        assert server.broadcaster.events[-1]["type"] == "phase_timer_shortened"
        time.sleep(0.12)
        assert session.turn_machine.current_phase == "EXCHANGE_PHASE", (
            f"all guesses should advance to EXCHANGE_PHASE after grace timer, got {session.turn_machine.current_phase}"
        )
    finally:
        config.PHASE_COMPLETION_GRACE_SECONDS = original_grace


def test_guess_result_broadcast():
    """GUESS-04: GUESS_RESULT includes is_correct and guesser_id."""
    server, _session, player_id, other_id = _server_with_turn_state("GUESS_PHASE")

    server.submit_guess(player_id, other_id, "bicicleta")
    event = server.broadcaster.events[-1]["data"]

    assert event["guesser_id"] == player_id and isinstance(event["is_correct"], bool), (
        f"GUESS_RESULT payload should include guesser_id and is_correct, got {event}"
    )


def test_guess_one_per_turn():
    """GUESS-05: a second submit_guess() call returns already_guessed."""
    server, _session, player_id, other_id = _server_with_turn_state("GUESS_PHASE")

    server.submit_guess(player_id, other_id, "bicicleta")
    result = server.submit_guess(player_id, other_id, "cadeira")

    assert result == {"error": "already_guessed"}, (
        f"second guess should be rejected, got {result}"
    )


def test_guess_no_self_target():
    """GUESS-05: self-target guesses return cannot_guess_own_object."""
    server, _session, player_id, _other_id = _server_with_turn_state("GUESS_PHASE")

    result = server.submit_guess(player_id, player_id, "maçã")

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


def test_object_assignment_reused_across_turns():
    """IMAGE-03: the same object assignment is reused until the game restarts."""
    server = GameServer()
    host = server.create_game("Alice", "PYRO:fake.alice@127.0.0.1:9999", 3)
    server.join_game("Bob", "PYRO:fake.bob@127.0.0.1:9999", host["room_code"])
    server.broadcaster = FakeBroadcaster()

    server._assign_images_for_turn(host["room_code"])
    first_turn = server._consume_image_assignments(host["room_code"])
    second_turn = server._consume_image_assignments(host["room_code"])

    assert second_turn == first_turn, (
        f"object assignments should persist across turns, got {first_turn} then {second_turn}"
    )


def test_get_player_view_returns_current_object_assignment():
    """IMAGE-02: reconnecting GameScreen can recover its private object assignment."""
    server, session, player_id, _other_id = _server_with_turn_state("HINT_PHASE")

    result = server.get_player_view(session.room_code, player_id)

    assert result["object_assignment"] == {
        "image_url": "/static/images/apple.jpg",
        "object_name": "maçã",
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


# --- Phase 5: ExchangeRecord dataclass tests ---

def test_exchange_record_defaults():
    """ExchangeRecord defaults: status='pending', requester_hint=None, target_hint=None."""
    er = ExchangeRecord("p1", "p2")
    assert er.status == "pending", f"default status should be 'pending', got {er.status}"
    assert er.requester_hint is None, f"requester_hint should default to None, got {er.requester_hint}"
    assert er.target_hint is None, f"target_hint should default to None, got {er.target_hint}"


def test_exchange_record_fields():
    """ExchangeRecord stores requester_id and target_id correctly."""
    er = ExchangeRecord("alice", "bob")
    assert er.requester_id == "alice"
    assert er.target_id == "bob"


def test_turn_state_new_fields_defaults():
    """TurnState has 4 new Phase 5 fields with correct default values."""
    ts = TurnState(1, ["p1"])
    assert ts.exchanges == {}, f"exchanges should default to {{}}, got {ts.exchanges}"
    assert ts.completed_exchanges == [], f"completed_exchanges should default to [], got {ts.completed_exchanges}"
    assert ts.exchange_participants == set(), (
        f"exchange_participants should default to set(), got {ts.exchange_participants}"
    )
    assert ts.exchange_skips == set(), f"exchange_skips should default to set(), got {ts.exchange_skips}"
    assert ts.spy_attempts == set(), f"spy_attempts should default to set(), got {ts.spy_attempts}"


def test_turn_state_all_hints_still_works():
    """all_hints_submitted() still functions correctly after Phase 5 additions."""
    ts = TurnState(1, ["p1", "p2"])
    assert ts.all_hints_submitted() is False, "no hints yet — should be False"
    ts.hints_submitted["p1"] = "red"
    ts.hints_submitted["p2"] = "round"
    assert ts.all_hints_submitted() is True, "all hints submitted — should be True"
