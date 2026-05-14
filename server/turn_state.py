"""TurnState - per-turn mutable game state.

Pure Python data object used by TurnMachine and GameServer. It intentionally
has no Pyro5, config, or server imports so it stays easy to unit test.
"""

import dataclasses


@dataclasses.dataclass
class TurnState:
    """State collected during a single turn."""

    turn_number: int
    player_ids: list
    hints_submitted: dict = dataclasses.field(default_factory=dict)
    guesses_made: dict = dataclasses.field(default_factory=dict)
    correct_guesses: list = dataclasses.field(default_factory=list)
    image_assignments: dict = dataclasses.field(default_factory=dict)

    def all_hints_submitted(self) -> bool:
        """Return True when every player has submitted or been backfilled."""
        return len(self.hints_submitted) >= len(self.player_ids)
