---
plan: 06-04
status: complete
---

# Summary — 06-04: Fix synonym arbitration on turns 2+

## What was done

Replaced the two separate lambdas (`on_round_start` + `on_hint_phase_start`) in the TurnMachine construction inside `start_game()` with a single local function `_hint_phase_cb` that calls `_assign_images_for_turn` first and explicitly returns the result of `_consume_image_assignments`.

**Root cause:** `_assign_images_for_turn` was only called via `on_round_start`. From turn 2 onward, TurnMachine goes TURN_END → HINT_PHASE directly, skipping ROUND_START. So `image_assignments` was empty on turns 2+, causing `expected = ""` for every player and `is_correct = False` for every guess.

**Fix (server/game_server.py ~line 484):**

```python
def _hint_phase_cb():
    self._assign_images_for_turn(room_code_for_cb)
    return self._consume_image_assignments(room_code_for_cb)

target_session.turn_machine = TurnMachine(
    ...
    on_hint_phase_start=_hint_phase_cb,
    ...
)
```

`on_round_start` removed — no longer needed.

## Verification

- `python -m pytest tests/ -x -q` → 61 passed, 0 failures
- Forbidden forms avoided: no lambda tuple, no function without explicit return
