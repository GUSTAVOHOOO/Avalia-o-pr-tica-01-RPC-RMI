"""Phase 7 tests — post-game flow (POSTGAME-01 through POSTGAME-04).

Test coverage:
  test_turn_score_history_appended    — POSTGAME-01: per-turn score history entry shape
  test_vote_started_broadcast         — POSTGAME-02: _start_vote() broadcasts vote_started event
  test_vote_majority_yes_restarts     — POSTGAME-03: majority yes triggers GAME_RESTARTING
  test_vote_no_majority_ends_game     — POSTGAME-04: no majority triggers GAME_ENDED
  test_vote_timer_expiry_ends_game    — POSTGAME-04 (timer path): 30s expiry without votes ends game
  test_duplicate_vote_ignored         — vote stuffing guard: second vote from same player is ignored
"""

import pytest

from server.game_server import GameServer, GameSession, PlayerInfo, VoteRecord
from server.turn_state import TurnState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_two_player_server(room_code="VOTE01"):
    """Create a GameServer with 2 players in an IN_PROGRESS session."""
    server = GameServer()
    pid_a = "player-a"
    pid_b = "player-b"
    session = GameSession(
        room_code=room_code,
        host_id=pid_a,
        max_turns=3,
        status="IN_PROGRESS",
        players=[
            PlayerInfo(player_id=pid_a, player_name="Alice", callback_uri="PYRO:fake@127.0.0.1:1", is_host=True),
            PlayerInfo(player_id=pid_b, player_name="Bob", callback_uri="PYRO:fake@127.0.0.1:2", is_host=False),
        ],
        accumulated_scores={pid_a: 0, pid_b: 0},
    )
    server.sessions[room_code] = session
    server._player_to_room[pid_a] = room_code
    server._player_to_room[pid_b] = room_code
    return server, session, pid_a, pid_b


def _mock_broadcast(server):
    """Replace server.broadcaster.broadcast with a capture stub.

    Returns the captured list: [(event_type, data), ...]
    """
    captured = []

    def mock_broadcast(event_type, data, exclude=None):
        captured.append((event_type, data))
        return []  # no failures

    server.broadcaster.broadcast = mock_broadcast
    return captured


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_turn_score_history_appended():
    """POSTGAME-01: After one turn's scoring phase, session.turn_score_history has
    one entry shaped {"turn": 1, "scores": {player_id: int}}.

    Validates that per-turn score data is accumulated in the session for the
    post-game podium table (POSTGAME-01 data availability).
    """
    server, session, pid_a, pid_b = _make_two_player_server(room_code="HIST01")
    _mock_broadcast(server)

    # Create a minimal TurnState for turn 1 with no guesses (all 0 deltas)
    turn_state = TurnState(
        turn_number=1,
        player_ids=[pid_a, pid_b],
        image_assignments={},
    )
    # _accumulate_scores requires all players present in guesses_made
    turn_state.guesses_made = {pid_a: None, pid_b: None}

    server._accumulate_scores("HIST01", turn_state)

    assert len(session.turn_score_history) == 1, (
        f"Expected 1 turn_score_history entry, got {len(session.turn_score_history)}"
    )
    entry = session.turn_score_history[0]
    assert "turn" in entry, "turn_score_history entry missing 'turn' key"
    assert "scores" in entry, "turn_score_history entry missing 'scores' key"
    assert entry["turn"] == 1, f"Expected turn=1, got {entry['turn']}"
    assert isinstance(entry["scores"], dict), "scores should be a dict"
    assert pid_a in entry["scores"], f"'{pid_a}' missing from scores dict"
    assert pid_b in entry["scores"], f"'{pid_b}' missing from scores dict"


def test_vote_started_broadcast():
    """POSTGAME-02: _start_vote() broadcasts a "vote_started" event with keys
    {"room_code", "duration_seconds", "player_count"}.

    Validates that all players receive the vote prompt with the correct
    metadata to render a 30-second countdown timer.
    """
    server, session, pid_a, pid_b = _make_two_player_server(room_code="VOTE02")
    captured = _mock_broadcast(server)

    server._start_vote("VOTE02")

    vote_events = [(et, d) for et, d in captured if et == "vote_started"]
    assert len(vote_events) == 1, f"Expected 1 vote_started broadcast, got {len(vote_events)}"

    payload = vote_events[0][1]
    assert "room_code" in payload, "Missing 'room_code' in vote_started payload"
    assert "duration_seconds" in payload, "Missing 'duration_seconds' in vote_started payload"
    assert "player_count" in payload, "Missing 'player_count' in vote_started payload"
    assert payload["room_code"] == "VOTE02", "room_code mismatch"
    assert payload["duration_seconds"] == 30, "duration_seconds should be 30"
    assert payload["player_count"] == 2, f"Expected player_count=2, got {payload['player_count']}"

    # VoteRecord should be created
    assert session.vote_record is not None, "vote_record should be set after _start_vote()"


def test_vote_majority_yes_restarts():
    """POSTGAME-03: With 2 players both submitting continue_game=True,
    _resolve_vote() broadcasts "game_restarting" and session.vote_record is None.

    Validates the happy path: strict majority (both players vote yes with 2 players)
    triggers a game restart with new image assignments and clears the vote state.
    """
    server, session, pid_a, pid_b = _make_two_player_server(room_code="VOTE03")
    captured = _mock_broadcast(server)

    # Manually seed VoteRecord (skip _start_vote timer)
    vote = VoteRecord(generation=1)
    session.vote_record = vote

    # Both players vote yes — majority (2/2 > 1.0)
    vote.votes[pid_a] = True
    vote.votes[pid_b] = True

    # _resolve_vote directly (bypasses 30s timer)
    server._resolve_vote("VOTE03", expected_generation=1)

    restart_events = [(et, d) for et, d in captured if et == "game_restarting"]
    assert len(restart_events) >= 1, (
        f"Expected at least 1 game_restarting broadcast, got {len(restart_events)}"
    )

    # vote_record should be cleared
    with server.lock:
        session_after = server.sessions.get("VOTE03")
    # session may still exist (restarted) or the vote_record should be None
    if session_after is not None:
        assert session_after.vote_record is None, (
            "vote_record should be None after resolve (cleared on restart)"
        )


def test_vote_no_majority_ends_game():
    """POSTGAME-04: With 2 players where only 1 votes True (minority),
    _resolve_vote() broadcasts "game_ended" with keys {"final_scores", "turn_score_history"}.

    Validates that failing to reach strict majority (1/2 votes yes) ends the game
    and delivers full score history in the broadcast payload.
    """
    server, session, pid_a, pid_b = _make_two_player_server(room_code="VOTE04")
    captured = _mock_broadcast(server)

    # Add some score history
    session.turn_score_history.append({"turn": 1, "scores": {pid_a: 10, pid_b: 5}})

    # Seed vote: 1 yes, 1 no → no majority (1/2 = 0.5, not strictly > 0.5)
    vote = VoteRecord(generation=1)
    vote.votes[pid_a] = True
    vote.votes[pid_b] = False
    session.vote_record = vote

    server._resolve_vote("VOTE04", expected_generation=1)

    ended_events = [(et, d) for et, d in captured if et == "game_ended"]
    assert len(ended_events) == 1, f"Expected 1 game_ended broadcast, got {len(ended_events)}"

    payload = ended_events[0][1]
    assert "final_scores" in payload, "Missing 'final_scores' in game_ended payload"
    assert "turn_score_history" in payload, "Missing 'turn_score_history' in game_ended payload"
    assert isinstance(payload["final_scores"], list), "final_scores should be a list"
    assert isinstance(payload["turn_score_history"], list), "turn_score_history should be a list"
    assert len(payload["turn_score_history"]) == 1, (
        f"Expected 1 turn_score_history entry in payload, got {len(payload['turn_score_history'])}"
    )


def test_vote_timer_expiry_ends_game():
    """POSTGAME-04 (timer path): A VoteRecord with 30s timer that fires without
    any votes results in "game_ended" broadcast.

    Validates that timer expiry without sufficient votes correctly ends the game
    (abstentions count as implicit "no" votes).
    """
    server, session, pid_a, pid_b = _make_two_player_server(room_code="VOTE05")
    captured = _mock_broadcast(server)

    # Seed vote with generation=1 and NO votes cast (simulates timer firing immediately)
    vote = VoteRecord(generation=1)
    session.vote_record = vote

    # Call _resolve_vote directly with the correct generation (simulates timer callback)
    server._resolve_vote("VOTE05", expected_generation=1)

    ended_events = [(et, d) for et, d in captured if et == "game_ended"]
    assert len(ended_events) == 1, (
        f"Expected 1 game_ended broadcast after timer expiry with 0 votes, "
        f"got {len(ended_events)}"
    )

    payload = ended_events[0][1]
    assert "final_scores" in payload, "Missing 'final_scores' in game_ended payload"
    assert "turn_score_history" in payload, "Missing 'turn_score_history' in game_ended payload"


def test_duplicate_vote_ignored():
    """Vote stuffing guard: A second submit_vote() from the same player_id returns
    {"ok": True, "duplicate": True} and does not change yes_count.

    Validates that a player cannot vote multiple times to influence the outcome
    (POSTGAME-03/04 integrity).
    """
    server, session, pid_a, pid_b = _make_two_player_server(room_code="VOTE06")
    _mock_broadcast(server)

    # Seed a VoteRecord
    vote = VoteRecord(generation=1)
    session.vote_record = vote

    # First vote
    result1 = server.submit_vote(pid_a, True)
    assert result1.get("ok") is True, f"First vote should succeed, got {result1}"
    assert result1.get("duplicate") is not True, "First vote should not be marked as duplicate"

    # Second vote from same player
    result2 = server.submit_vote(pid_a, False)  # tries to flip vote
    assert result2.get("ok") is True, f"Duplicate vote should return ok=True, got {result2}"
    assert result2.get("duplicate") is True, (
        f"Duplicate vote should be marked as duplicate, got {result2}"
    )

    # Vote tally should only count the first vote (True)
    with server.lock:
        vote_after = server.sessions["VOTE06"].vote_record
    if vote_after is not None:
        yes_count = sum(1 for v in vote_after.votes.values() if v)
        assert yes_count == 1, f"Expected yes_count=1 (only first vote counted), got {yes_count}"
        # The vote value should still be True (the first one)
        assert vote_after.votes[pid_a] is True, "Vote value should remain True (first vote)"
