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
    pytest.skip("stub — implement in plan 02")


def test_request_exchange_wrong_phase():
    """EXCHANGE-01: request_exchange() in wrong phase returns invalid_phase."""
    pytest.skip("stub — implement in plan 02")


def test_respond_exchange_accept():
    """EXCHANGE-02: respond_exchange(accept=True) transitions ExchangeRecord status to accepted."""
    pytest.skip("stub — implement in plan 02")


def test_respond_exchange_reject():
    """EXCHANGE-02: respond_exchange(accept=False) transitions ExchangeRecord status to rejected."""
    pytest.skip("stub — implement in plan 02")


def test_submit_exchange_hint_completes():
    """EXCHANGE-03: submit_exchange_hint() by both parties sets status to completed."""
    pytest.skip("stub — implement in plan 02")


def test_exchange_completed_payload():
    """EXCHANGE-04: EXCHANGE_COMPLETED broadcast contains no hint content."""
    pytest.skip("stub — implement in plan 02")


def test_private_hints_delivered():
    """EXCHANGE-05: Private hints delivered to both participants after completion."""
    pytest.skip("stub — implement in plan 02")


def test_exchange_one_per_turn():
    """EXCHANGE-06: Second request_exchange() from same player returns already_used_exchange."""
    pytest.skip("stub — implement in plan 02")


def test_spy_phase_skipped_when_no_exchanges():
    """D-06: _compute_next('EXCHANGE_PHASE') with empty completed_exchanges returns SCORING_PHASE."""
    pytest.skip("stub — implement in plan 02")


def test_spy_phase_entered_when_exchange_exists():
    """D-06: _compute_next('EXCHANGE_PHASE') with one completed exchange returns SPY_PHASE."""
    pytest.skip("stub — implement in plan 02")


# --- SPY tests (plan 03) ---

def test_spy_wrong_phase():
    """SPY-01: attempt_spy() in EXCHANGE_PHASE returns invalid_phase."""
    pytest.skip("stub — implement in plan 03")


def test_spy_discovery_probability():
    """SPY-02: Over 100 calls, approximately 30% result in discovered: True + score penalty."""
    pytest.skip("stub — implement in plan 03")


def test_spy_success_private():
    """SPY-03: Undetected spy receives both hints silently; no public broadcast."""
    pytest.skip("stub — implement in plan 03")


def test_spy_own_exchange_rejected():
    """SPY-04: Exchange participant attempting spy returns cannot_spy_own_exchange."""
    pytest.skip("stub — implement in plan 03")


def test_spy_one_per_turn():
    """SPY-05: Second attempt_spy() from same player returns already_used_spy."""
    pytest.skip("stub — implement in plan 03")
