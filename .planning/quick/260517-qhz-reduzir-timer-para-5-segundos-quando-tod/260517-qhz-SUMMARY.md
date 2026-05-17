---
quick_id: 260517-qhz
status: complete
completed: 2026-05-17
---

# Summary

Implemented a five-second completion grace timer for phases where every required player action is done before the normal phase duration ends.

## Changed

- Added `PHASE_COMPLETION_GRACE_SECONDS = 5` in `config.py`.
- Added `TurnMachine.shorten_current_phase()` to cancel the old timer, schedule a short replacement timer, and broadcast `phase_timer_shortened`.
- Replaced immediate completion advances in hint, guess, exchange, and spy flows with timer shortening.
- Forwarded `phase_timer_shortened` from the bridge to the browser.
- Updated `GameScreen` to refresh only the visible countdown for the shortened timer.
- Updated focused tests to validate the short grace period before advancing.

## Verified

- Python compile check passed.
- Focused backend phase-completion tests passed.
- Frontend production build passed.
