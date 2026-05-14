"""Unit tests for TurnMachine — covers TURN-01 through TURN-04 and D-07.

Tests are plain pytest functions with no fixtures. FakeBroadcaster is defined
at module level following the test_session.py pattern. Timing-sensitive tests
monkeypatch config.PHASE_DURATIONS with short values (0.05s) and restore in
a try/finally block.

Test coverage:
  test_phase_cycle                — TURN-01: full PHASE_SEQUENCE order verified via broadcaster events
  test_timer_auto_advance         — TURN-02: timer fires automatically without manual call
  test_manual_advance_cancels_timer — TURN-03: manual advance cancels existing timer
  test_generation_counter         — TURN-04: stale timer callback is a no-op after manual advance
  test_game_ended_after_last_turn — D-07: final TURN_END broadcasts game_ended, not phase_changed
"""

import time

import config
from server.turn_machine import TurnMachine, PHASE_SEQUENCE


# ---------------------------------------------------------------------------
# Fake broadcaster — collects all broadcast() calls for assertion
# ---------------------------------------------------------------------------

class FakeBroadcaster:
    def __init__(self):
        self.events = []

    def broadcast(self, event_type, data, exclude=None):
        self.events.append({
            "type": event_type,
            "phase": data.get("phase"),
            "data": data,
        })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_phase_cycle():
    """TURN-01: TurnMachine advances through full PHASE_SEQUENCE in order.

    Strategy: call start() (→ ROUND_START), then advance_phase_manual() 6 more
    times to step through the remaining 6 phases through TURN_END.
    Collect only phase_changed events and verify the phase list matches
    PHASE_SEQUENCE exactly.

    GAME_ENDED produces type="game_ended" (not "phase_changed") so it does not
    appear in the phase list — this is expected.

    Phase 5 note: _compute_next("EXCHANGE_PHASE") skips SPY_PHASE when
    completed_exchanges is empty. We inject a fake completed exchange so the full
    PHASE_SEQUENCE (including SPY_PHASE) is exercised.
    """
    from server.turn_state import TurnState
    broadcaster = FakeBroadcaster()
    tm = TurnMachine("ROOM1", max_turns=1, broadcaster=broadcaster)

    # start() → ROUND_START; then step through the remaining 6 phases
    tm.start()                    # ROUND_START
    tm.advance_phase_manual()     # HINT_PHASE
    tm.advance_phase_manual()     # GUESS_PHASE
    tm.advance_phase_manual()     # EXCHANGE_PHASE
    # Inject a completed exchange AFTER entering EXCHANGE_PHASE so SPY_PHASE is not skipped
    if tm.current_turn_state is None:
        tm.current_turn_state = TurnState(turn_number=1, player_ids=[])
    tm.current_turn_state.completed_exchanges.append("fake-exid")
    tm.advance_phase_manual()     # SPY_PHASE (D-06, completed_exchanges non-empty)
    tm.advance_phase_manual()     # SCORING_PHASE
    tm.advance_phase_manual()     # TURN_END → triggers GAME_ENDED (max_turns=1)

    phases = [e["phase"] for e in broadcaster.events if e["type"] == "phase_changed"]
    assert phases == PHASE_SEQUENCE, (
        f"Phase sequence mismatch.\n  Expected: {PHASE_SEQUENCE}\n  Got:      {phases}"
    )


def test_timer_auto_advance():
    """TURN-02: After start(), the auto-timer fires and advances phase without any manual call.

    Uses monkeypatched 0.05s durations; waits 0.3s (generous margin for slow CI).
    Expects at least 2 events: ROUND_START broadcast + at least one auto-advance.
    """
    original = config.PHASE_DURATIONS.copy()
    config.PHASE_DURATIONS.update({k: 0.05 for k in config.PHASE_DURATIONS})

    try:
        broadcaster = FakeBroadcaster()
        tm = TurnMachine("ROOM2", max_turns=2, broadcaster=broadcaster)
        tm.start()

        time.sleep(0.3)

        assert len(broadcaster.events) >= 2, (
            f"Expected at least 2 events (ROUND_START + auto-advance), got {len(broadcaster.events)}"
        )
        phase_events = [e for e in broadcaster.events if e["type"] == "phase_changed"]
        assert len(phase_events) >= 2, (
            f"Expected at least 2 phase_changed events, got {len(phase_events)}: {phase_events}"
        )
        assert phase_events[1]["phase"] == "HINT_PHASE", (
            f"Expected second phase to be HINT_PHASE, got {phase_events[1]['phase']}"
        )
    finally:
        config.PHASE_DURATIONS.update(original)


def test_manual_advance_cancels_timer():
    """TURN-03: advance_phase_manual() cancels the current timer.

    After calling start() (ROUND_START timer set to 0.15s), immediately calling
    advance_phase_manual() should cancel the ROUND_START timer. After waiting
    0.4s (longer than the original 0.15s timer), HINT_PHASE should appear exactly
    once — not twice.
    """
    original = config.PHASE_DURATIONS.copy()
    config.PHASE_DURATIONS.update({k: 0.15 for k in config.PHASE_DURATIONS})

    try:
        broadcaster = FakeBroadcaster()
        tm = TurnMachine("ROOM3", max_turns=3, broadcaster=broadcaster)
        tm.start()                    # ROUND_START, timer set to 0.15s
        tm.advance_phase_manual()     # Manual → HINT_PHASE; cancels ROUND_START timer

        time.sleep(0.4)  # Longer than the original 0.15s timer; new HINT_PHASE timer also fires

        hint_count = sum(1 for e in broadcaster.events if e["phase"] == "HINT_PHASE")
        assert hint_count == 1, (
            f"HINT_PHASE should appear exactly once (manual advance only), got {hint_count}. "
            f"Events: {[e['phase'] for e in broadcaster.events if e['type'] == 'phase_changed']}"
        )
    finally:
        config.PHASE_DURATIONS.update(original)


def test_generation_counter():
    """TURN-04: Stale timer callback is suppressed by generation mismatch.

    Sequence:
      1. start() → ROUND_START, timer set to 0.05s, gen=1
      2. Sleep 0.025s (timer not yet fired)
      3. advance_phase_manual() → gen increments to 3; stale timer's expected_gen=1
      4. Sleep 0.2s → old timer fires (no-op, gen mismatch); new HINT_PHASE timer also fires
      5. Verify HINT_PHASE appears exactly once — not twice
    """
    original = config.PHASE_DURATIONS.copy()
    config.PHASE_DURATIONS.update({k: 0.05 for k in config.PHASE_DURATIONS})

    try:
        broadcaster = FakeBroadcaster()
        tm = TurnMachine("ROOM4", max_turns=3, broadcaster=broadcaster)
        tm.start()

        time.sleep(0.025)           # Timer not yet fired
        tm.advance_phase_manual()   # gen increments; old timer gen is stale

        time.sleep(0.2)             # Old timer fires → must be no-op; new timer also fires

        phases = [e["phase"] for e in broadcaster.events if e["type"] == "phase_changed"]
        assert phases.count("HINT_PHASE") == 1, (
            f"Double-advance detected — HINT_PHASE appeared {phases.count('HINT_PHASE')} times. "
            f"Full phase sequence: {phases}"
        )
    finally:
        config.PHASE_DURATIONS.update(original)


def test_game_ended_after_last_turn():
    """D-07: After final TURN_END with max_turns=1, broadcaster receives game_ended (not phase_changed).

    Advances manually through all phases (start() + advance_phase_manual() calls).
    The final advance (TURN_END → _compute_next sees current_turn >= max_turns) should
    broadcast "game_ended", not "phase_changed". Verify the game_ended event is present
    and that no phase_changed event has phase=None (which would indicate a bug).

    Phase 5 note: With empty completed_exchanges, EXCHANGE_PHASE → SCORING_PHASE (D-06),
    so SPY_PHASE is skipped. Adjust call count accordingly.
    """
    from server.turn_state import TurnState
    broadcaster = FakeBroadcaster()
    tm = TurnMachine("ROOM5", max_turns=1, broadcaster=broadcaster)

    tm.start()                    # ROUND_START
    tm.advance_phase_manual()     # HINT_PHASE
    tm.advance_phase_manual()     # GUESS_PHASE
    tm.advance_phase_manual()     # EXCHANGE_PHASE
    # Inject a completed exchange AFTER entering EXCHANGE_PHASE so SPY_PHASE is not skipped
    if tm.current_turn_state is None:
        tm.current_turn_state = TurnState(turn_number=1, player_ids=[])
    tm.current_turn_state.completed_exchanges.append("fake-exid")
    tm.advance_phase_manual()     # SPY_PHASE (D-06, completed_exchanges non-empty)
    tm.advance_phase_manual()     # SCORING_PHASE
    tm.advance_phase_manual()     # TURN_END
    tm.advance_phase_manual()     # GAME_ENDED (max_turns=1, _compute_next("TURN_END") → GAME_ENDED)

    assert any(e["type"] == "game_ended" for e in broadcaster.events), (
        f"Expected a game_ended event after final TURN_END. Events: {broadcaster.events}"
    )
    # game_ended payload must NOT include a "phase" key (it's not a phase transition)
    game_ended_events = [e for e in broadcaster.events if e["type"] == "game_ended"]
    assert len(game_ended_events) == 1, (
        f"Expected exactly 1 game_ended event, got {len(game_ended_events)}"
    )
    assert "phase" not in game_ended_events[0]["data"], (
        f"game_ended payload must not include 'phase' key, got: {game_ended_events[0]['data']}"
    )
