"""TurnState - per-turn mutable game state.

Pure Python data object used by TurnMachine and GameServer. It intentionally
has no Pyro5, config, or server imports so it stays easy to unit test.
"""

import dataclasses
from typing import Optional


@dataclasses.dataclass
class ExchangeRecord:
    """Tracks one 1-on-1 private hint exchange within a turn."""

    requester_id: str
    target_id: str
    status: str = "pending"           # "pending" | "accepted" | "rejected" | "completed"
    requester_hint: Optional[str] = None
    target_hint: Optional[str] = None


@dataclasses.dataclass
class TurnState:
    """State collected during a single turn."""

    turn_number: int
    player_ids: list
    hints_submitted: dict = dataclasses.field(default_factory=dict)
    guesses_made: dict = dataclasses.field(default_factory=dict)
    correct_guesses: list = dataclasses.field(default_factory=list)
    image_assignments: dict = dataclasses.field(default_factory=dict)
    exchanges: dict = dataclasses.field(default_factory=dict)              # exchange_id -> ExchangeRecord (D-03)
    completed_exchanges: list = dataclasses.field(default_factory=list)    # ordered list of completed exchange_ids, spy target list (D-03)
    exchange_participants: set = dataclasses.field(default_factory=set)    # player_ids that used their exchange slot (D-03, EXCHANGE-06)
    exchange_skips: set = dataclasses.field(default_factory=set)            # player_ids that chose not to exchange this turn
    spy_attempts: set = dataclasses.field(default_factory=set)             # player_ids that used their spy slot (D-03, SPY-05)

    def all_hints_submitted(self) -> bool:
        """Return True when every player has submitted or been backfilled."""
        return len(self.hints_submitted) >= len(self.player_ids)

    def all_guesses_submitted(self) -> bool:
        """Return True when every player guessed or skipped."""
        return len(self.guesses_made) >= len(self.player_ids)

    def exchange_phase_complete(self) -> bool:
        """Return True when no active exchange remains and fewer than 2 players can still exchange."""
        active_statuses = {"pending", "accepted"}
        if any(record.status in active_statuses for record in self.exchanges.values()):
            return False
        unavailable = self.exchange_participants | self.exchange_skips
        available_count = len([player_id for player_id in self.player_ids if player_id not in unavailable])
        return available_count < 2

    def spy_eligible_players(self) -> set:
        """Players that still have at least one completed exchange they can spy on."""
        eligible = set()
        for player_id in self.player_ids:
            for exchange_id in self.completed_exchanges:
                record = self.exchanges.get(exchange_id)
                if record is not None and player_id not in (record.requester_id, record.target_id):
                    eligible.add(player_id)
                    break
        return eligible

    def all_spy_attempts_submitted(self) -> bool:
        """Return True when every eligible player used their spy attempt."""
        return self.spy_eligible_players() <= self.spy_attempts
