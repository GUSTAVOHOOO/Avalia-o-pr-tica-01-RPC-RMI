"""Unit tests for Phase 5 exchange and spy mechanics."""

import pytest
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


def _server_with_exchange_state(phase="EXCHANGE_PHASE"):
    server = GameServer()
    host = server.create_game("Alice", "PYRO:fake.alice@127.0.0.1:9999", 3)
    room_code = host["room_code"]
    join = server.join_game("Bob", "PYRO:fake.bob@127.0.0.1:9999", room_code)
    charlie = server.join_game("Charlie", "PYRO:fake.charlie@127.0.0.1:9999", room_code)
    player_ids = [host["player_id"], join["player_id"], charlie["player_id"]]
    server.broadcaster = FakeBroadcaster()
    session = server.sessions[room_code]
    session.turn_machine = TurnMachine(
        room_code,
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
            charlie["player_id"]: "chair",
        },
    )
    return server, session, host["player_id"], join["player_id"], charlie["player_id"]


# --- EXCHANGE tests (plan 02) ---

def test_request_exchange():
    """EXCHANGE-01: request_exchange() returns {ok, exchange_id} and creates ExchangeRecord."""
    server, session, alice_id, bob_id, charlie_id = _server_with_exchange_state("EXCHANGE_PHASE")
    result = server.request_exchange(alice_id, bob_id)

    assert result.get("ok") is True, f"Expected ok=True, got {result}"
    exchange_id = result.get("exchange_id")
    assert isinstance(exchange_id, str) and len(exchange_id) == 8, (
        f"Expected 8-char exchange_id, got {exchange_id!r}"
    )

    turn_state = session.turn_machine.current_turn_state
    assert exchange_id in turn_state.exchanges, "exchange_id not found in turn_state.exchanges"
    record = turn_state.exchanges[exchange_id]
    assert record.requester_id == alice_id
    assert record.target_id == bob_id
    assert record.status == "pending"

    assert alice_id in turn_state.exchange_participants, "alice not in exchange_participants"
    assert bob_id in turn_state.exchange_participants, "bob not in exchange_participants"

    # Private notification sent to target
    events = [e for e in server.broadcaster.events if e["type"] == "exchange_requested"]
    assert len(events) == 1, f"Expected 1 exchange_requested event, got {len(events)}"
    assert events[0].get("player_id") == bob_id


def test_request_exchange_wrong_phase():
    """EXCHANGE-01: request_exchange() in wrong phase returns invalid_phase."""
    server, session, alice_id, bob_id, charlie_id = _server_with_exchange_state("HINT_PHASE")
    result = server.request_exchange(alice_id, bob_id)
    assert result == {"error": "invalid_phase"}, f"Expected invalid_phase error, got {result}"


def test_respond_exchange_accept():
    """EXCHANGE-02: respond_exchange(accept=True) transitions ExchangeRecord status to accepted."""
    server, session, alice_id, bob_id, charlie_id = _server_with_exchange_state("EXCHANGE_PHASE")
    req_result = server.request_exchange(alice_id, bob_id)
    exchange_id = req_result["exchange_id"]

    result = server.respond_exchange(bob_id, exchange_id, True)
    assert result == {"ok": True}, f"Expected ok=True, got {result}"

    record = session.turn_machine.current_turn_state.exchanges[exchange_id]
    assert record.status == "accepted", f"Expected status=accepted, got {record.status}"


def test_respond_exchange_reject():
    """EXCHANGE-02: respond_exchange(accept=False) transitions ExchangeRecord status to rejected."""
    server, session, alice_id, bob_id, charlie_id = _server_with_exchange_state("EXCHANGE_PHASE")
    req_result = server.request_exchange(alice_id, bob_id)
    exchange_id = req_result["exchange_id"]

    result = server.respond_exchange(bob_id, exchange_id, False)
    assert result == {"ok": True}, f"Expected ok=True, got {result}"

    record = session.turn_machine.current_turn_state.exchanges[exchange_id]
    assert record.status == "rejected", f"Expected status=rejected, got {record.status}"


def _setup_accepted_exchange(phase="EXCHANGE_PHASE"):
    """Helper: creates a server with one accepted exchange ready for hint submission."""
    server, session, alice_id, bob_id, charlie_id = _server_with_exchange_state(phase)
    req = server.request_exchange(alice_id, bob_id)
    exchange_id = req["exchange_id"]
    server.respond_exchange(bob_id, exchange_id, True)
    # Clear broadcaster events accumulated during setup
    server.broadcaster.events.clear()
    return server, session, alice_id, bob_id, charlie_id, exchange_id


def test_submit_exchange_hint_completes():
    """EXCHANGE-03: submit_exchange_hint() by both parties sets status to completed."""
    server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_accepted_exchange()

    server.submit_exchange_hint(alice_id, exchange_id, "round")
    result = server.submit_exchange_hint(bob_id, exchange_id, "wheels")
    assert result == {"ok": True}, f"Expected ok=True, got {result}"

    turn_state = session.turn_machine.current_turn_state
    record = turn_state.exchanges[exchange_id]
    assert record.status == "completed", f"Expected status=completed, got {record.status}"
    assert exchange_id in turn_state.completed_exchanges, (
        f"exchange_id not in completed_exchanges: {turn_state.completed_exchanges}"
    )


def test_exchange_completed_payload():
    """EXCHANGE-04: EXCHANGE_COMPLETED broadcast contains no hint content."""
    server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_accepted_exchange()

    server.submit_exchange_hint(alice_id, exchange_id, "round")
    server.submit_exchange_hint(bob_id, exchange_id, "wheels")

    broadcast_events = [
        e for e in server.broadcaster.events
        if e["type"] == "exchange_completed"
    ]
    assert len(broadcast_events) == 1, (
        f"Expected 1 exchange_completed broadcast, got {len(broadcast_events)}"
    )
    payload = broadcast_events[0]["data"]
    assert "requester_hint" not in payload, "requester_hint must not appear in broadcast payload"
    assert "target_hint" not in payload, "target_hint must not appear in broadcast payload"
    assert "room_code" in payload
    assert "exchange_id" in payload
    assert "requester_id" in payload
    assert "target_id" in payload


def test_private_hints_delivered():
    """EXCHANGE-05: Private hints delivered to both participants after completion."""
    server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_accepted_exchange()

    server.submit_exchange_hint(alice_id, exchange_id, "round")
    server.submit_exchange_hint(bob_id, exchange_id, "wheels")

    private_events = [
        e for e in server.broadcaster.events
        if e["type"] == "exchange_hints"
    ]
    assert len(private_events) == 2, (
        f"Expected 2 exchange_hints events, got {len(private_events)}"
    )
    target_ids = {e["player_id"] for e in private_events}
    assert alice_id in target_ids, "No exchange_hints event for alice"
    assert bob_id in target_ids, "No exchange_hints event for bob"


def test_exchange_one_per_turn():
    """EXCHANGE-06: Second request_exchange() from same player returns already_used_exchange."""
    server, session, alice_id, bob_id, charlie_id = _server_with_exchange_state("EXCHANGE_PHASE")
    server.request_exchange(alice_id, bob_id)

    result = server.request_exchange(alice_id, charlie_id)
    assert result == {"error": "already_used_exchange"}, (
        f"Expected already_used_exchange error, got {result}"
    )


def test_skip_exchange_records_choice():
    """EXCHANGE-07: skip_exchange() marks a player as unavailable for private exchanges."""
    server, session, alice_id, bob_id, charlie_id = _server_with_exchange_state("EXCHANGE_PHASE")

    result = server.skip_exchange(alice_id)

    assert result == {"ok": True}, f"Expected ok=True, got {result}"
    assert alice_id in session.turn_machine.current_turn_state.exchange_skips


def test_exchange_phase_auto_advances_when_no_pair_available():
    """EXCHANGE-08: phase advances when everyone has exchanged or skipped."""
    server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_accepted_exchange()

    # Complete the accepted Alice/Bob exchange. Charlie is the only player left, so no new pair remains.
    server.submit_exchange_hint(alice_id, exchange_id, "round")
    server.submit_exchange_hint(bob_id, exchange_id, "wheels")

    assert session.turn_machine.current_phase == "SPY_PHASE", (
        f"completed exchange with an eligible spy should advance to SPY_PHASE, got {session.turn_machine.current_phase}"
    )


def test_spy_phase_skipped_when_no_exchanges():
    """D-06: _compute_next('EXCHANGE_PHASE') with empty completed_exchanges returns SCORING_PHASE."""
    _server, session, _alice, _bob, _charlie = _server_with_exchange_state("EXCHANGE_PHASE")
    tm = session.turn_machine
    # completed_exchanges is empty (default)
    assert tm.current_turn_state.completed_exchanges == []
    result = tm._compute_next("EXCHANGE_PHASE")
    assert result == "SCORING_PHASE", (
        f"With no completed exchanges, _compute_next should skip SPY_PHASE and return SCORING_PHASE, got {result}"
    )


def test_spy_phase_entered_when_exchange_exists():
    """D-06: _compute_next('EXCHANGE_PHASE') with one completed exchange returns SPY_PHASE."""
    _server, session, _alice, _bob, _charlie = _server_with_exchange_state("EXCHANGE_PHASE")
    tm = session.turn_machine
    # Simulate a completed exchange
    tm.current_turn_state.completed_exchanges.append("abc12345")
    result = tm._compute_next("EXCHANGE_PHASE")
    assert result == "SPY_PHASE", (
        f"With at least one completed exchange, _compute_next should return SPY_PHASE, got {result}"
    )


def test_spy_phase_skipped_when_no_eligible_spy():
    """D-06: two-player completed exchange has no eligible spy and skips SPY_PHASE."""
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
    session.turn_machine.current_phase = "EXCHANGE_PHASE"
    session.turn_machine.current_turn_state = TurnState(turn_number=1, player_ids=player_ids)
    req = server.request_exchange(host["player_id"], join["player_id"])
    server.respond_exchange(join["player_id"], req["exchange_id"], True)
    server.submit_exchange_hint(host["player_id"], req["exchange_id"], "round")
    server.submit_exchange_hint(join["player_id"], req["exchange_id"], "wheels")

    assert session.turn_machine.current_phase == "SCORING_PHASE", (
        f"two-player exchange should skip SPY_PHASE, got {session.turn_machine.current_phase}"
    )


def _setup_spy_state():
    """Helper: creates server with SPY_PHASE active and one completed exchange ready for spying."""
    server, session, alice_id, bob_id, charlie_id = _server_with_exchange_state("EXCHANGE_PHASE")
    req = server.request_exchange(alice_id, bob_id)
    exchange_id = req["exchange_id"]
    server.respond_exchange(bob_id, exchange_id, True)
    server.submit_exchange_hint(alice_id, exchange_id, "round")
    server.submit_exchange_hint(bob_id, exchange_id, "wheels")
    # Move to SPY_PHASE
    session.turn_machine.current_phase = "SPY_PHASE"
    server.broadcaster.events.clear()
    return server, session, alice_id, bob_id, charlie_id, exchange_id


# --- SPY tests (plan 03) ---

def test_spy_wrong_phase():
    """SPY-01: attempt_spy() in EXCHANGE_PHASE returns invalid_phase."""
    server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_spy_state()
    # Override phase back to EXCHANGE_PHASE for this test
    session.turn_machine.current_phase = "EXCHANGE_PHASE"
    result = server.attempt_spy(charlie_id, exchange_id)
    assert result == {"error": "invalid_phase"}, f"Expected invalid_phase, got {result}"


def test_spy_discovery_probability():
    """SPY-02: Over 100 calls, approximately 30% result in discovered: True + score penalty."""
    discovered_count = 0
    for _ in range(100):
        server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_spy_state()
        result = server.attempt_spy(charlie_id, exchange_id)
        assert result.get("ok") is True, f"Unexpected result: {result}"
        if result.get("discovered") is True:
            discovered_count += 1

    fraction = discovered_count / 100
    assert 0.15 <= fraction <= 0.50, (
        f"Discovery fraction {fraction:.2f} outside expected range [0.15, 0.50]"
    )


def test_spy_success_private():
    """SPY-03: Undetected spy receives both hints silently; no public broadcast."""
    import random as _random
    # Force success by patching random.random to return 0.99 (above 0.3 threshold)
    original_random = _random.random
    _random.random = lambda: 0.99
    try:
        server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_spy_state()
        result = server.attempt_spy(charlie_id, exchange_id)
    finally:
        _random.random = original_random

    assert result == {"ok": True, "discovered": False}, f"Expected not-discovered, got {result}"

    private_events = [
        e for e in server.broadcaster.events
        if e["type"] == "spy_success"
    ]
    assert len(private_events) == 1, f"Expected 1 spy_success event, got {len(private_events)}"
    assert private_events[0].get("player_id") == charlie_id

    public_events = [
        e for e in server.broadcaster.events
        if e["type"] == "spy_discovered"
    ]
    assert len(public_events) == 0, f"Expected no spy_discovered broadcast, got {len(public_events)}"


def test_spy_own_exchange_rejected():
    """SPY-04: Exchange participant attempting spy returns cannot_spy_own_exchange."""
    server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_spy_state()
    # alice is the requester — she cannot spy on her own exchange
    result = server.attempt_spy(alice_id, exchange_id)
    assert result == {"error": "cannot_spy_own_exchange"}, (
        f"Expected cannot_spy_own_exchange, got {result}"
    )


def test_spy_one_per_turn():
    """SPY-05: Second attempt_spy() from same player returns already_used_spy."""
    server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_spy_state()
    server.attempt_spy(charlie_id, exchange_id)

    result = server.attempt_spy(charlie_id, exchange_id)
    assert result == {"error": "already_used_spy"}, (
        f"Expected already_used_spy on second attempt, got {result}"
    )


def test_spy_phase_auto_advances_after_all_eligible_attempt():
    """SPY-06: when the only eligible spy attempts, phase advances to SCORING_PHASE."""
    server, session, alice_id, bob_id, charlie_id, exchange_id = _setup_spy_state()

    server.attempt_spy(charlie_id, exchange_id)

    assert session.turn_machine.current_phase == "SCORING_PHASE", (
        f"all eligible spy attempts should auto-advance to SCORING_PHASE, got {session.turn_machine.current_phase}"
    )
