# Phase 4: Core Turn Loop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 4-core-turn-loop
**Areas discussed:** Turn state location, Guess attempt policy, Hint progress visibility, Frontend scope

---

## Turn State Location

| Option | Description | Selected |
|--------|-------------|----------|
| TurnState dataclass | New TurnState dataclass held by TurnMachine. Clean separation: TurnMachine owns timing/phases, TurnState owns game data. Aligns with existing GameSession/PlayerInfo dataclass pattern. | ✓ |
| Extend TurnMachine directly | Add hints_submitted, guesses_made, correct_guesses as attributes on TurnMachine. Simpler but mixes concerns. Harder to reset cleanly between turns. | |
| GameSession holds it | GameSession.current_turn_state set by GameServer. TurnMachine only does timing. Spreads state across two classes. | |

**User's choice:** TurnState dataclass (recommended option)
**Notes:** TurnMachine creates a fresh TurnState at each HINT_PHASE entry. Fields chosen: hints_submitted, guesses_made, correct_guesses, image_assignments.

---

## Guess Attempt Policy

**Q1: One target, multiple attempts vs one attempt total?**

| Option | Description | Selected |
|--------|-------------|----------|
| One target, unlimited attempts | Pick a target, keep guessing words until correct or phase ends. GUESS-05 restricts the target, not the tries. | |
| One attempt total | One word against one target. If wrong, can't retry this turn. | ✓ |

**User's choice:** One attempt total
**Notes:** Stricter interpretation. guesses_made dict enforces it; further calls return `{"error": "already_guessed"}`.

**Q2: Reject duplicate submit_guess calls?**

| Option | Description | Selected |
|--------|-------------|----------|
| Reject with error message | Returns `{"error": "already_guessed"}`. UI disables input after first submission. | ✓ |
| Silent no-op | Server ignores; UI gets no signal. | |

**Q3: Self-targeting?**

| Option | Description | Selected |
|--------|-------------|----------|
| Server rejects self-targeting | Returns error if player_id == target_player. Frontend hides own entry from dropdown. | ✓ |
| You decide | Leave to planner. | |

---

## Hint Progress Visibility

**Q1: What do players see when a hint is submitted?**

| Option | Description | Selected |
|--------|-------------|----------|
| Hint word revealed immediately | HINT_RECEIVED includes the word. Players see chips appearing. | |
| Only 'hint submitted' status (blind) | HINT_RECEIVED tells everyone a hint was submitted but not what it says — revealed only at GUESS_PHASE start. | ✓ |

**User's choice:** Blind hints — sealed envelope pattern.

**Q2: How are hints revealed at GUESS_PHASE?**

| Option | Description | Selected |
|--------|-------------|----------|
| PHASE_CHANGED payload includes all hints | hints_submitted dict included in GUESS_PHASE transition payload. One event, no extra RPC. | ✓ |
| New HINTS_REVEALED broadcast event | Separate on_hints_revealed() on BridgeCallbackReceiver. More explicit but adds an event type. | |
| Clients call get_game_state() on phase change | Pull on transition — polling-ish, against push-event architecture. | |

**Q3: Progress counter during HINT_PHASE?**

| Option | Description | Selected |
|--------|-------------|----------|
| Count without names/words | HINT_RECEIVED includes hints_count and total_players. UI shows '2/4 hints received'. | ✓ |
| Checkmarks per player name | Shows WHO submitted, not just how many. | |
| No counter | Only countdown timer. | |

---

## Frontend Scope

**Q1: Action inputs layout?**

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in GameScreen, visible by phase | Action zone shows right input for current phase. No modals. Conditional rendering. | ✓ |
| Modal overlays per phase (UI-06 spec) | Each phase triggers a modal. Closer to final spec but adds complexity Phase 8 will restyle anyway. | |

**Q2: Score display?**

| Option | Description | Selected |
|--------|-------------|----------|
| Inline score panel in GameScreen | SCORE_UPDATED triggers a panel section. No separate route. Phase 8 adds animation. | ✓ |
| Separate /score route between turns | Navigate to /score/:roomCode, then back. Clean but adds routing complexity. | |

**Q3: Image bank mapping format?**

| Option | Description | Selected |
|--------|-------------|----------|
| JSON file: images/manifest.json | {filename: object_name}. Server reads at startup. Simple to extend. | ✓ |
| Filename IS the object name | No mapping file, convention over config. Breaks with spaces or display names. | |
| You decide | Leave to planner. | |

---

## Claude's Discretion

- Image assignment timing: whether OBJECT_ASSIGNED fires at ROUND_START or HINT_PHASE start — left to planner.
- Exact-match case normalization: case-insensitive strip+lowercase — left to planner.
- Number of starter images in bank: minimum 8 — left to planner.

## Deferred Ideas

- Modal overlays per phase (HINT modal, GUESS modal) — deferred to Phase 8 per UI-06.
- Synonym arbitration (GUESS-03) — deferred to Phase 6.
- "Who submitted" vs "how many submitted" visibility — Phase 4 shows count only; could revisit in Phase 8.
