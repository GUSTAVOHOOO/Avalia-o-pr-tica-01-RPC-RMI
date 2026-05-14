"""TurnMachine — server-side finite state machine for game phase progression.

Drives the game through a fixed phase sequence using threading.Timer with a
generation counter to prevent double-advances (TURN-04). All broadcaster.broadcast()
calls happen OUTSIDE the RLock to avoid deadlock during network I/O (anti-pattern
documented in RESEARCH.md Pitfall 1).

No Pyro5 dependency — TurnMachine is a pure Python class, enabling in-process unit
testing without starting any daemons.
"""

import logging
import threading
import time
from typing import Optional

import config
from server.turn_state import TurnState

logger = logging.getLogger(__name__)

# Phase sequence — ROUND_START happens once at game start; subsequent turns begin at
# HINT_PHASE (D-06: skip ROUND_START on turns 2+).
PHASE_SEQUENCE = [
    "ROUND_START",
    "HINT_PHASE",
    "GUESS_PHASE",
    "EXCHANGE_PHASE",
    "SPY_PHASE",
    "SCORING_PHASE",
    "TURN_END",
]


def _calculate_score_deltas(turn_state) -> dict:
    """Calculate per-player score deltas for the current turn."""
    deltas = {player_id: 0 for player_id in turn_state.player_ids}

    for index, guesser_id in enumerate(turn_state.correct_guesses):
        points = max(20 - index * 5, 5)
        deltas[guesser_id] = deltas.get(guesser_id, 0) + points

    if len(turn_state.correct_guesses) == 1:
        guesser_id = turn_state.correct_guesses[0]
        deltas[guesser_id] = deltas.get(guesser_id, 0) + 10

    targets = {
        target_player_id
        for target_player_id in turn_state.guesses_made.values()
        if target_player_id is not None
    }
    for owner_id in targets:
        all_targeters = [
            guesser_id
            for guesser_id, target_id in turn_state.guesses_made.items()
            if target_id == owner_id
        ]
        correct_targeters = [
            guesser_id
            for guesser_id in turn_state.correct_guesses
            if turn_state.guesses_made.get(guesser_id) == owner_id
        ]
        if not all_targeters or not correct_targeters:
            owner_points = 0
        elif len(correct_targeters) == len(all_targeters):
            owner_points = -10
        else:
            owner_points = max(15 - (len(correct_targeters) - 1) * 5, 0)
        deltas[owner_id] = deltas.get(owner_id, 0) + owner_points

    return deltas


class TurnMachine:
    """Manages game phase state machine with auto-advancing timers.

    Args:
        room_code: Identifier for the game session (included in every broadcast).
        max_turns: Total number of turns before GAME_ENDED is broadcast.
        broadcaster: EventBroadcaster instance — receives broadcast() calls.

    Thread-safety: All mutable state is protected by self.lock (threading.RLock).
    broadcaster.broadcast() is always called AFTER releasing the lock.
    """

    def __init__(self, room_code: str, max_turns: int, broadcaster,
                 player_ids=None, on_game_ended=None, on_round_start=None,
                 on_hint_phase_start=None, on_scoring_phase=None):
        self.room_code = room_code
        self.max_turns = max_turns
        self.broadcaster = broadcaster
        self.player_ids = list(player_ids or [])
        self._on_game_ended = on_game_ended  # optional callable(); called with no args when game ends (D-07)
        self._on_round_start = on_round_start
        self._on_hint_phase_start = on_hint_phase_start
        self._on_scoring_phase = on_scoring_phase

        self.lock = threading.RLock()
        self.current_phase: str = "WAITING"
        self.current_turn: int = 1
        self._generation: int = 0
        self._timer_handle: Optional[threading.Timer] = None
        self._phase_start_time: float = 0.0
        self.current_turn_state: Optional[TurnState] = None

    def start(self):
        """Kick off the state machine at ROUND_START.

        Called by GameServer.start_game() AFTER broadcasting game_started, so that
        browsers have navigated to GameScreen before the first phase_changed fires.
        """
        self._advance_to("ROUND_START")

    def _advance_to(self, phase: str, from_timer: bool = False,
                    expected_generation: int = -1):
        """Core transition method — must always be called with no lock held by caller.

        Steps (CRITICAL ordering to avoid broadcast-inside-lock deadlock):
          1. Enter with self.lock block
          2. If from_timer: check generation — stale timer → log + return (TURN-04)
          3. Cancel existing timer handle; set to None
          4. Increment _generation; capture gen_snapshot for closure
          5. Update current_phase, _phase_start_time
          6. If phase == "GAME_ENDED": build game_ended broadcast_data (no timer)
          7. Else: build phase_changed broadcast_data + schedule new threading.Timer
          8. Exit with self.lock block
          9. AFTER lock exits: call broadcaster.broadcast()
        """
        broadcast_data: Optional[dict] = None
        game_ended = False
        scoring_turn_state = None

        with self.lock:
            if from_timer:
                # Generation check — stale timer guard (TURN-04)
                if self._generation != expected_generation:
                    logger.info(
                        "[TurnMachine] Stale timer suppressed "
                        "(room=%s gen_expected=%d gen_current=%d)",
                        self.room_code, expected_generation, self._generation,
                    )
                    return

            # Cancel any running timer before proceeding
            if self._timer_handle is not None:
                self._timer_handle.cancel()
                self._timer_handle = None

            self._generation += 1
            gen_snapshot = self._generation  # capture for closure — NEVER use self._generation in lambda

            self.current_phase = phase
            self._phase_start_time = time.monotonic()
            duration = config.PHASE_DURATIONS.get(phase, 30)

            if phase == "GAME_ENDED":
                game_ended = True
                broadcast_data = {
                    "room_code": self.room_code,
                    "current_turn": self.current_turn,
                    "max_turns": self.max_turns,
                }
            else:
                if phase == "HINT_PHASE":
                    image_assignments = (
                        self._on_hint_phase_start()
                        if self._on_hint_phase_start is not None
                        else {}
                    )
                    self.current_turn_state = TurnState(
                        turn_number=self.current_turn,
                        player_ids=list(self.player_ids),
                        image_assignments=dict(image_assignments or {}),
                    )
                elif phase == "GUESS_PHASE" and self.current_turn_state is not None:
                    for player_id in self.current_turn_state.player_ids:
                        if player_id not in self.current_turn_state.hints_submitted:
                            self.current_turn_state.hints_submitted[player_id] = ""
                elif phase == "SCORING_PHASE":
                    scoring_turn_state = self.current_turn_state

                # Capture phase in closure so callback uses the correct phase name
                _phase_snapshot = phase

                def _timer_callback():
                    next_phase = self._compute_next(_phase_snapshot)
                    self._advance_to(
                        next_phase,
                        from_timer=True,
                        expected_generation=gen_snapshot,
                    )

                self._timer_handle = threading.Timer(duration, _timer_callback)
                self._timer_handle.daemon = True
                self._timer_handle.start()

                broadcast_data = {
                    "room_code": self.room_code,
                    "phase": phase,
                    "remaining_seconds": duration,
                    "current_turn": self.current_turn,
                    "max_turns": self.max_turns,
                }
                if phase == "GUESS_PHASE" and self.current_turn_state is not None:
                    broadcast_data["hints"] = dict(self.current_turn_state.hints_submitted)

        # Broadcast OUTSIDE the lock — network I/O must never hold the state lock
        if game_ended:
            self.broadcaster.broadcast("game_ended", broadcast_data)
            # Notify GameServer to mark session ENDED — called with no lock held (T-03-10)
            if self._on_game_ended is not None:
                self._on_game_ended()
        else:
            self.broadcaster.broadcast("phase_changed", broadcast_data)
            if phase == "ROUND_START" and self._on_round_start is not None:
                self._on_round_start()
            if phase == "SCORING_PHASE" and self._on_scoring_phase is not None:
                self._on_scoring_phase(scoring_turn_state)

    def _compute_next(self, current_phase: str) -> str:
        """Determine the next phase given current_phase and current turn state.

        Acquires self.lock (RLock re-entry is safe — always called from _advance_to
        timer callback which does NOT hold the lock at call time).

        For TURN_END:
          - If current_turn >= max_turns → "GAME_ENDED" (last turn, D-07)
          - Otherwise → increment current_turn, return "HINT_PHASE" (D-06: skip ROUND_START)

        For all other phases: return the next item in PHASE_SEQUENCE.
        """
        with self.lock:
            if current_phase == "TURN_END":
                if self.current_turn >= self.max_turns:
                    return "GAME_ENDED"
                self.current_turn += 1
                return "HINT_PHASE"  # Skip ROUND_START on subsequent turns (D-06)
            idx = PHASE_SEQUENCE.index(current_phase)
            return PHASE_SEQUENCE[idx + 1]

    def advance_phase_manual(self):
        """Manually advance to the next phase immediately.

        Used by GameServer.advance_phase() RPC method (operator/test hook).
        Does NOT pass from_timer=True — this is a deliberate manual skip, so the
        generation counter increment cancels any pending stale timer callback.
        """
        with self.lock:
            next_phase = self._compute_next(self.current_phase)
        self._advance_to(next_phase)

    def advance_to_guess_phase(self):
        """Fast path from HINT_PHASE to GUESS_PHASE after all hints arrive."""
        with self.lock:
            if self.current_phase != "HINT_PHASE":
                return False
        self._advance_to("GUESS_PHASE")
        return True

    @property
    def remaining_seconds(self) -> int:
        """Approximate seconds remaining in the current phase.

        Computed from _phase_start_time + PHASE_DURATIONS[current_phase].
        Returns 0 if phase has no duration (e.g., WAITING, GAME_ENDED).
        """
        with self.lock:
            duration = config.PHASE_DURATIONS.get(self.current_phase, 0)
            elapsed = time.monotonic() - self._phase_start_time
            return max(0, int(duration - elapsed))
