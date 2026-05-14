# Phase 5: Exchange + Spy Mechanics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 5-exchange-spy-mechanics
**Areas discussed:** EXCHANGE/SPY concurrency, Exchange state & lifecycle, Frontend scope, SPY_PHASE with no active exchanges

---

## EXCHANGE/SPY Concurrency

| Option | Description | Selected |
|--------|-------------|----------|
| Keep sequential | EXCHANGE_PHASE → SPY_PHASE as separate phases with separate timers. Spy targets only completed exchanges. | ✓ |
| Collapse into one combined phase | Single EXCHANGE_SPY_PHASE where both happen simultaneously. Matches SPY-01 "simultaneous" wording. | |

**User's choice:** Keep sequential

**Notes:** SPY-01's "simultaneous ao EXCHANGE" wording in REQUIREMENTS.md is overridden by this decision. Spy targets completed exchanges only — rejected, pending, or partially-submitted exchanges are not spy targets.

---

## Spy Target Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Completed exchanges only | SPY_PHASE shows only exchanges where accept + both hints submitted. | ✓ |
| Any accepted exchange | Spy can target accepted exchanges even before hints submitted. | |

**User's choice:** Completed exchanges only

---

## Exchange State & Lifecycle — Storage

| Option | Description | Selected |
|--------|-------------|----------|
| New fields on TurnState | `exchanges` dict + `completed_exchanges` list + participant/spy sets added to TurnState. Pure data, no Pyro5, testable. | ✓ |
| On GameSession | Attach exchange state to GameSession alongside accumulated_scores. | |

**User's choice:** New fields on TurnState

---

## Exchange State & Lifecycle — exchange_id Generation

| Option | Description | Selected |
|--------|-------------|----------|
| uuid4 short prefix | `str(uuid.uuid4())[:8]` — short, unique within a turn. | ✓ |
| Sequential counter | `exchange_1`, `exchange_2`, etc. | |

**User's choice:** uuid4 short prefix

---

## Exchange State & Lifecycle — Phase End Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Drop silently | Incomplete exchanges discarded at EXCHANGE_PHASE end, no cancellation broadcast. | ✓ |
| Broadcast cancellation | Server sends EXCHANGE_CANCELLED for each incomplete exchange. | |

**User's choice:** Drop silently

---

## Frontend Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Backend + bridge only | No new frontend panels. GameScreen shows phase name + countdown only. Exchange/spy UI is Phase 8. | ✓ |
| Inline panels in GameScreen | Add simple exchange/spy panels following Phase 4's inline pattern. | |

**User's choice:** Backend + bridge only

---

## SPY_PHASE with No Active Exchanges

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-skip SPY_PHASE | If `completed_exchanges` is empty, TurnMachine jumps to SCORING_PHASE. Conditional in `_compute_next()`. | ✓ |
| Run the timer anyway | SPY_PHASE always runs. `attempt_spy()` returns error if no exchanges exist. | |

**User's choice:** Auto-skip SPY_PHASE

---

## Claude's Discretion

- ExchangeRecord as nested dataclass in `turn_state.py` vs separate `exchange_record.py`
- `random.random() < 0.3` vs `random.choices()` for spy probability
- SPY_PHASE PHASE_CHANGED payload: `spy_targets: [id, ...]` list vs `spy_target_count: N`

## Deferred Ideas

- Spy success bonus (+5pts) — deferred to v2 per REQUIREMENTS.md v2 list
- Exchange/spy inline action panels in GameScreen — deferred to Phase 8 (UI-06)
- Configurable spy probability by host — deferred to v2
