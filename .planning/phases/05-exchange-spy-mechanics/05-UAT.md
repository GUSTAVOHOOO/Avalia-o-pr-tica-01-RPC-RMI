---
status: partial
phase: 05-exchange-spy-mechanics
source:
  - .planning/phases/05-exchange-spy-mechanics/05-01-SUMMARY.md
  - .planning/phases/05-exchange-spy-mechanics/05-02-SUMMARY.md
  - .planning/phases/05-exchange-spy-mechanics/05-03-SUMMARY.md
  - .planning/phases/05-exchange-spy-mechanics/05-04-SUMMARY.md
started: "2026-05-16T00:00:00Z"
updated: "2026-05-16T00:00:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. Request Exchange — target receives private notification
expected: |
  During EXCHANGE_PHASE, Player A emits `request_exchange` with another player's ID.
  The target player (Player B) receives a private `exchange_requested` SocketIO event
  containing the exchange_id and the requester's player_id. Player A gets a success
  response `{ok: true, exchange_id: "..."}`. No hint words are visible to anyone yet.
result: skipped
reason: "Frontend action panels for exchange/spy are Phase 8 scope (D-07 in 05-CONTEXT.md). Phase 5 is backend+bridge only."

### 2. Reject Exchange — exchange is cancelled
expected: |
  Player B receives an `exchange_requested` notification and emits `respond_exchange`
  with `accept: false`. The exchange is cancelled. No further events are sent.
  Both players can observe the rejection feedback in the UI.
result: skipped
reason: "Frontend action panels for exchange/spy are Phase 8 scope (D-07 in 05-CONTEXT.md). Phase 5 is backend+bridge only."

### 3. Accept + Submit Hints — private delivery to both participants
expected: |
  Player B accepts the exchange request. Both players submit a hint word via
  `submit_exchange_hint`. When the second hint is submitted, all players receive an
  `exchange_completed` broadcast (no hint words in the payload). The two exchange
  participants each receive a private `exchange_hints` event containing both hints.
  Players outside the exchange do NOT see the hint words.
result: skipped
reason: "Frontend action panels for exchange/spy are Phase 8 scope (D-07 in 05-CONTEXT.md). Phase 5 is backend+bridge only."

### 4. One Exchange Per Turn — second request blocked
expected: |
  A player who has already been in an exchange (either as requester or target) attempts
  to request another exchange in the same turn. The server returns an error response
  (not `ok: true`). No second exchange is created.
result: skipped
reason: "Frontend action panels for exchange/spy are Phase 8 scope (D-07 in 05-CONTEXT.md). Phase 5 is backend+bridge only."

### 5. SPY_PHASE Skipped When No Exchanges
expected: |
  A turn where no exchanges were completed (nobody requested, or all requests were
  rejected). After EXCHANGE_PHASE, the game advances directly to SCORING_PHASE,
  skipping SPY_PHASE entirely. Players receive a `phase_changed` event going straight
  to SCORING_PHASE with no SPY_PHASE in between.
result: skipped
reason: "Cannot observe phase transitions without exchange UI. Phase 8 work."

### 6. SPY_PHASE Entered When Exchanges Exist
expected: |
  A turn where at least one exchange was completed. After EXCHANGE_PHASE ends, the game
  enters SPY_PHASE. Players receive a `phase_changed` event with `phase: SPY_PHASE`
  and a `spy_targets` list containing the IDs of completed exchanges.
result: skipped
reason: "Cannot trigger completed exchanges without exchange UI. Phase 8 work."

### 7. Spy Attempt — success path (private hints delivered)
expected: |
  During SPY_PHASE, a player who did NOT participate in an exchange emits `attempt_spy`
  targeting a completed exchange_id. On success (70% probability), the spy privately
  receives a `spy_success` event with both hint words. No public broadcast occurs; other
  players see nothing.
result: skipped
reason: "Frontend spy panel is Phase 8 scope (D-07 in 05-CONTEXT.md). Phase 5 is backend+bridge only."

### 8. Spy Attempt — discovery path (penalty broadcast)
expected: |
  During SPY_PHASE, a spy attempt triggers the 30% discovery outcome. The spy loses 10
  points (visible after scoring). All players receive a public `spy_discovered` broadcast
  naming the spy. The spy does NOT receive the hint words.
result: skipped
reason: "Frontend spy panel is Phase 8 scope (D-07 in 05-CONTEXT.md). Phase 5 is backend+bridge only."

### 9. Spy Own Exchange Blocked
expected: |
  A player who participated in a completed exchange attempts to spy on that same exchange.
  The server returns an error (not `ok: true`). No spy event is sent.
result: skipped
reason: "Frontend spy panel is Phase 8 scope (D-07 in 05-CONTEXT.md). Phase 5 is backend+bridge only."

### 10. One Spy Attempt Per Turn
expected: |
  A player who already used their spy slot attempts a second `attempt_spy` in the same
  SPY_PHASE. The server returns an error. No second spy event is fired.
result: skipped
reason: "Frontend spy panel is Phase 8 scope (D-07 in 05-CONTEXT.md). Phase 5 is backend+bridge only."

## Summary

total: 10
passed: 0
issues: 0
pending: 0
skipped: 10

## Gaps

[none — all tests skipped due to intentional Phase 8 frontend scope boundary (D-07)]
