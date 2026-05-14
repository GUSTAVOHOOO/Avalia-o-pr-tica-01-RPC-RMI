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
    spy_attempts: set = dataclasses.field(default_factory=set)             # player_ids that used their spy slot (D-03, SPY-05)

    def all_hints_submitted(self) -> bool:
        """Return True when every player has submitted or been backfilled."""
        return len(self.hints_submitted) >= len(self.player_ids)
