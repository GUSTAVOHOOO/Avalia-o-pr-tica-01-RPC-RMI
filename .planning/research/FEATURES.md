# Feature Landscape

**Domain:** Turn-based multiplayer word/image guessing game (party game, 2–6 players, browser-based)
**Researched:** 2026-05-12
**Context:** Academic MVP demonstrating Pyro5 RPC + distributed systems; 2-person team, one semester

---

## Table Stakes

Features players treat as baseline expectations. Their absence causes abandonment before the game even starts or immediately after.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Shareable room code / invite link | Every web party game uses this (skribbl.io, Codenames, netgames.io). Players won't manually find each other. | Low | UUID room code displayed in lobby; copy button. |
| Player list visible in lobby | Players need to know who joined before starting. "Ready" state per player optional but expected. | Low | Broadcast `player_joined` event via Pyro5 callback. |
| Host-controlled game start | One player (creator) controls when game begins. Prevents premature start. | Low | Host flag stored server-side; non-hosts see "Waiting for host". |
| Per-phase countdown timer with visual feedback | Without a visible timer, players don't know when to act. Color change (green → yellow → red) is standard. | Medium | Timer ticks on server; client receives `timer_tick` events. The PRD already specifies this. |
| Automatic phase transitions | If timer expires without all players acting, game must advance anyway. Manual transitions cause stalled games. | Medium | Server timer thread triggers phase change, broadcasts `phase_changed` event. |
| Real-time scoreboard visible during game | Players need persistent context of who's winning. Hidden scoreboard kills engagement. | Low | Sidebar updated after each SCORING phase event. |
| End-of-round score delta | Showing "+15 pts" per player per round is standard; flat scoreboard alone isn't enough. | Low | Include `round_delta` in SCORING event payload. |
| Clear "whose turn / what phase" indicator | Party games with unclear turn state break down immediately. Every player must know what to do right now. | Low | Persistent header or badge: "HINT phase — 28s remaining — waiting for: Alice, Bob". |
| Reconnection / state restoration | A disconnected player rejoining must receive current game state. Loss-of-progress on refresh is a known UX failure mode. | Medium-High | Server stores full game state in memory; `get_game_state()` RPC called on reconnect. Ghost-player bug (new socket ID) must be handled via persistent player token (UUID in localStorage). |
| Chat separated from game actions | Confirmed as highest UX risk in PROJECT.md. Players accidentally submitting guesses via chat is a game-breaker. | Medium | Two distinct UI panels. Chat uses a `chat_message` RPC; game actions use typed RPCs. Visual and label separation is mandatory. |
| Post-game results screen | Players expect a summary/podium after the game ends. Dropping them to a blank screen is jarring. | Low | Final scoreboard + winner highlight + "Play again" vote. |

---

## Differentiators

These are not expected by default but make the experience meaningfully better than a bare-bones implementation. For an academic project, 1–2 of these go a long way toward a demo that feels like a real product.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Bluff mechanics in private exchange | The ability to send false hints in EXCHANGE adds a deception layer absent from similar games. Unique to this design. | Low (mechanic is free — it's just not validated) | The PRD defines this. UI should surface: "Hint sent privately — the other player cannot verify it." |
| Espionage risk/reward asymmetry | 30% discovery risk with −10pt penalty is an interesting risk-taking mechanic. Rare in casual word games. | Medium | PRD-defined. The uncertainty of outcome (server-side RNG) is itself the mechanic — no extra UI complexity needed beyond showing outcome. |
| Synonym-aware arbitration | Accepting "auto" when the answer is "car" is expected by players. Exact-match-only guessing feels broken. | Medium | Use NLTK WordNet Wu-Palmer similarity. Requires threshold calibration. See PITFALLS.md — Wu-Palmer has coverage gaps and can return None. |
| "Spy detected" public shaming notification | Broadcasting who got caught spying adds social drama and spectator value even for non-spies. | Low | Just a broadcast event on discovery. High social payoff for minimal implementation cost. |
| Turn summary popup | End-of-SCORING phase popup showing all guesses, who guessed correctly, and point changes gives closure to each round. | Low-Medium | Replaces having to mentally track the sidebar. High signal-to-noise for demo purposes. |
| Configurable number of turns at room creation | Allows short demo games (3 turns) vs longer sessions (10 turns). Almost zero implementation cost. | Low | Already in PROJECT.md requirements. |

---

## Anti-Features

Features to explicitly NOT build for this academic MVP. Each has a "why" and an alternative approach.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Spectator mode | Adds a distinct player role with different state visibility. Out of scope in PROJECT.md. Doubles state-management complexity. | Document as future work. |
| Persistent user accounts / authentication | PRD explicitly out of scope. Adds auth layer with no grade value. | Nickname-by-session only. Store player token (UUID) in browser localStorage for reconnection, not an account. |
| Game pause / timer hold | PRD: "timer não para". Pause logic requires server-side state negotiation across all clients. | Auto-empty-hint on timeout (already a KEY DECISION in PROJECT.md). |
| In-game friend lists or social graph | Zero relevance. Users share a room code instead. | Share link via clipboard copy button. |
| Custom image upload | Adds file serving and storage layer. PRD: "imagens fornecidas pelo servidor". | Static image set bundled with server. |
| Kick-vote or moderation tools | skribbl.io analysis confirms this is valuable for public lobbies. This is a private-invite academic game (2–6 known players). Adds complex consensus logic. | Host-only kick via single RPC `kick_player(player_id)`. |
| Undo / replay of actions | Turn-based games with bluffing and espionage cannot allow undo without breaking game integrity. | None — actions are final. Make this explicit in UI ("This action cannot be undone"). |
| Leaderboard across sessions | No persistence layer. Out of scope. | End-of-session podium only. |
| Mobile-optimized layout beyond basic responsiveness | Pyro5/RPC demo is evaluated on desktop. Mobile polish is scope creep for an academic deadline. | Basic responsive CSS so the game doesn't break on mobile, no further investment. |
| Sound effects / music | Nice-to-have with no grade impact. Takes disproportionate time. | Silence is fine. Timer color change conveys urgency without audio. |
| AI / bot players | Requires NLP or scripted logic. No grade value. | Minimum 2 human players required; document this. |

---

## Feature Dependencies

Dependencies describe what must exist before another feature can work correctly.

```
Room code + join_game RPC
    → Player list broadcast
        → Host-controlled start
            → Phase machine (HINT → GUESS → EXCHANGE → SPY → SCORING)
                → Server-side timer per phase
                    → Automatic phase transition on timeout
                        → Phase-specific action RPCs (submit_hint, submit_guess, request_exchange, attempt_spy)
                            → Scoring calculation
                                → SCORING broadcast event
                                    → Post-game results screen
                                        → Play-again vote

Player token (localStorage UUID)
    → Reconnection / get_game_state RPC
        → State restoration on rejoin

Chat channel (independent RPC path)
    [No dependency on game state — runs in parallel]

WordNet/NLTK setup
    → Synonym-based guess arbitration
        → Guess submission RPC
```

Key constraint: **the phase machine is the backbone**. No other game mechanic can be built until phase transitions and their timer are stable. This should be the first working vertical slice.

---

## Mechanics the PRD Covers Well (Confirmed by Research)

These are already in the PRD and align with what players expect from the genre:

- One-word hint per turn — identical to Codenames spymaster mechanic; well-understood by players
- Timer per phase — standard expectation; PRD specifies 30–60s
- Voting to continue after last turn — expected end-state for party games
- Public notification of private exchange (without content) — correct design; revealing content would eliminate bluff value
- Automated arbitration (no manual validation) — PRD Key Decision confirmed as correct; manual validation blocks UI flow

---

## Mechanics the PRD Did Not Explicitly Address (Gaps Found by Research)

These are player expectations that are implied but not spelled out in the PRD. The team should decide explicitly rather than discover them mid-implementation.

| Gap | Player Expectation | Recommended Decision |
|-----|-------------------|---------------------|
| What happens when a player disconnects mid-turn? | Game should not permanently stall. | Server detects WebSocket disconnect via bridge; marks player as `disconnected`; their timer slot auto-skips (same as empty-hint timeout rule). Document this behavior. |
| Can a disconnected player reconnect and resume? | Yes, this is expected. | Player UUID token in localStorage + `get_game_state()` RPC returning full current state (phase, hints, scores, timer remaining). |
| What happens if host disconnects? | Players are stranded. | Promote next player in join-order to host automatically. One RPC check on disconnect. |
| Is there a minimum player count to start? | Games should not start with 1 player. | Server enforces minimum 2 players before allowing host to start. |
| Can a player join mid-game? | Varies by game. For a guessing game with secret images, mid-game join is problematic (no image was assigned). | Reject mid-game joins. Lobby-only enrollment. Broadcast "game in progress" to late joiners. |
| What does the HINT phase look like when some players have already submitted? | Players who submitted early are in limbo. | Show a "waiting" indicator per player (submitted / pending) without revealing hint content. Identical pattern to Among Us task completion indicators. |
| Is there feedback when a guess is accepted (synonym match) vs. rejected? | Yes — players need to know whether their guess registered. | Immediate response RPC that returns `{accepted: true/false, matched_word: "car", similarity_score: 0.87}`. Show this inline. |

---

## Complexity Estimates Summary

| Feature | Effort | Risk |
|---------|--------|------|
| Room code + lobby + host start | Low | Low |
| Phase machine with timer | Medium | Medium — thread safety with RLock |
| Phase-specific action RPCs | Medium | Low per RPC, cumulative effort |
| Pyro5 callback broadcast | Medium | Medium — bridge plumbing |
| Reconnection + state restore | Medium-High | High — ghost player / token matching |
| Chat (separate channel) | Low | Low if isolated from game state |
| Synonym arbitration (NLTK) | Medium | Medium — Wu-Palmer None-returns, threshold tuning |
| Espionage RNG + discovery | Low | Low |
| Private exchange + bluff | Low | Low — no server validation needed |
| Scoring calculation | Medium | Low — math is defined in PRD |
| Post-game podium + play-again vote | Low | Low |

---

## MVP Recommendation

**Build in this order:**

1. Room creation, join, player list, host start — the lobby loop
2. Phase machine (HINT → SCORING) with server-side timer and automatic transitions — the backbone
3. One full working turn: submit_hint → submit_guess (exact match only first) → scoring broadcast
4. Pyro5 callback pipeline: confirm all clients receive events before adding more mechanics
5. Add synonym arbitration (NLTK) once basic guess flow works
6. Add EXCHANGE and SPY mechanics (lower risk, slot into existing phase machine)
7. Reconnection / state restore — highest-risk feature, tackle before final demo
8. Chat (last, it's independent and low risk)

**Defer if time-constrained:**
- Turn summary popup (nice but not critical for grade)
- Host auto-promotion on disconnect (document the limitation instead)
- Full mobile responsiveness beyond basic layout

---

## Sources

- skribbl.io design analysis: https://mechanicsofmagic.com/2024/04/23/critical-play-skribbl-io-22/
- Multiplayer reconnection best practices: https://www.getgud.io/blog/how-to-successfully-create-a-reconnect-ability-in-multiplayer-games/
- Lobby system best practices: https://forum.heroiclabs.com/t/best-practices-to-create-a-lobby-system/1735
- NLTK WordNet similarity (Wu-Palmer): https://www.geeksforgeeks.org/nlp/nlp-wupalmer-wordnet-similarity/
- Game scope management: https://www.codecks.io/blog/2025/how-to-avoid-scope-creep-in-game-development/
- Social deduction lobby patterns (One Night Werewolf): https://netgames.io/games/onu-werewolf/
- Codenames online: https://codenames.game/
- Ghost player / socket.io reconnection pattern: GitHub issue discussions, getgud.io reconnect guide
