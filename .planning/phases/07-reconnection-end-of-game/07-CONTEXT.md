# Phase 7: Reconnection + End-of-Game - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver session reconnection (UUID from localStorage → `get_game_state()` → restore client state without treating the player as new), graceful player removal when callbacks repeatedly fail (with PLAYER_LEFT broadcast), host transfer on lobby disconnect (already wired), in-game chat (send_chat RPC + on_chat_message callback, visually separated from game actions), and post-game flow (podium + per-turn scores + play-again vote with 30s timer → restart with new images or redirect to landing).

Requirements in scope: INFRA-07, INFRA-08, SESSION-07, POSTGAME-01, POSTGAME-02, POSTGAME-03, POSTGAME-04, CHAT-01, CHAT-02, CHAT-03, CHAT-04

</domain>

<decisions>
## Implementation Decisions

### Reconnection Architecture

- **D-01:** Bridge uses a **grace period (~5s)** before calling `leave_game()` on Socket.IO disconnect. If the player reconnects within the window (providing their UUID from localStorage), the pending leave is cancelled and their callback re-registered. Minimal server-side changes needed.
- **D-02:** Client emits a **new `reconnect_game` Socket.IO event** with `{player_id, room_code}` on reconnect. Bridge checks if the UUID is still active (player did not time out), re-registers their callback URI, and returns the current game state.
- **D-03:** Reconnect state delivery reuses the existing **`get_player_view(room_code, player_id)`** — no new data structure. This returns everything needed to restore the client: current phase, scores, image assignment, hints received so far.

### Chat

- **D-04:** Chat input uses **different colors + explicit labels** to achieve "radical visual separation" (CHAT-03/04): chat input labeled "Mensagem de chat" in a secondary color (gray/blue); game action inputs (hint, guess) labeled explicitly and styled in primary color. No ambiguity about which field does what.
- **D-05:** Chat placement within the main game screen (tab vs. fixed panel) — **Claude's discretion**; must satisfy UI-04 "placar/eventos/chat em tabs" and CHAT-03/04 separation requirements.

### Play-Again Vote

- **D-06:** Vote counting semantics — **Claude's discretion**. Planner should define the exact majority rule (strict >50% of connected players, or any-yes-over-no excluding abstentions). The POSTGAME requirements say "maioria vota continuar" → restart; anything else → end.
- **D-07:** When the game truly ends (vote closes with no majority to continue, or majority votes stop): post-game screen stays visible briefly, then **all players are redirected to the landing page**. Session is deleted on the server.

### Player Disconnect Feedback (INFRA-07)

- **D-08:** When callbacks fail **3 consecutive times** for a player, they are removed from the active callback list. Server broadcasts a **PLAYER_LEFT event** with the player's name so remaining players see a notification (e.g., toast "Jogador X saiu da partida"). Game continues uninterrupted with remaining players.

### Already-Decided (Carried Forward)

- SESSION-07 (host transfer on lobby disconnect) is **already fully implemented** in `leave_game()` — it promotes the next player and broadcasts HOST_CHANGED. The bridge already routes HOST_CHANGED. No new work needed.

### Claude's Discretion

- Chat placement within the game screen (tab vs. fixed panel) — must satisfy UI-04 and CHAT-03/04; specific layout is planner's call.
- Exact vote counting semantics (strict majority vs. active-voter majority) — planner's call as long as abstentions don't accidentally enable continuation with very few votes.
- Whether the grace-period timer in the bridge uses `threading.Timer` or a per-SID dict with timestamp checks — planner's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §INFRA-07, INFRA-08 — Callback failure removal + UUID reconnect spec
- `.planning/REQUIREMENTS.md` §SESSION-07 — Host transfer on lobby disconnect (already implemented — verify before adding duplicate code)
- `.planning/REQUIREMENTS.md` §POSTGAME-01 to 04 — Full post-game flow: podium, vote timer, restart vs. end
- `.planning/REQUIREMENTS.md` §CHAT-01 to 04 — Chat RPC + callback + visual separation requirements
- `.planning/ROADMAP.md` §Phase 7 — 5 success criteria that must all be TRUE for phase completion

### Architecture
- `.planning/PROJECT.md` §Key Decisions — locked decisions (RLock, per-thread proxies, broadcast outside lock)
- `CLAUDE.md` §Key Pyro5 Patterns — patterns 1–4

### Prior Phase Context
- `.planning/phases/06-synonym-arbitration/06-CONTEXT.md` — broadcast pattern reference
- `.planning/phases/04-core-turn-loop/04-CONTEXT.md` — image_assignments, get_player_view shape, score structure

### Existing Implementation (read before writing new code)
- `bridge/bridge.py:557–570` — current `handle_disconnect()` that immediately calls `leave_game()`; D-01 requires changing this to add grace period
- `bridge/bridge.py:80–90` — existing HOST_CHANGED routing (SESSION-07 already wired here)
- `server/game_server.py:897–952` — `leave_game()` implementation; already handles host transfer and HOST_CHANGED broadcast
- `server/game_server.py:321–357` — `get_player_view()` — canonical reconnect state payload (D-03)
- `server/event_broadcaster.py` — broadcast mechanism; D-08 requires adding failure counter per player_id

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/game_server.py:321` — `get_player_view(room_code, player_id)` already returns full client state: phase, scores, hints, image assignment. Use as `get_game_state()` response (D-03).
- `server/game_server.py:897` — `leave_game()` already handles host transfer + HOST_CHANGED broadcast — SESSION-07 is already done.
- `bridge/bridge.py:557` — `handle_disconnect()` is the single change point for D-01 (add grace period before `leave_game()` call).
- `server/event_broadcaster.py` — add per-player failure counter for INFRA-07/D-08.

### Established Patterns
- Broadcast outside lock — all `broadcaster.broadcast()` calls after `with self.lock:` exits. PLAYER_LEFT broadcast (D-08) must follow this pattern.
- Return dicts from `@Pyro5.api.expose` methods: `{"ok": True, ...}` or `{"error": "reason"}`.
- Threading.Timer used in `start_game()` for phase transitions — same pattern for vote 30s timer.
- `_sid_to_player` / `_player_to_sid` dicts in bridge (with `_sid_lock`) — the reconnect flow needs to update these mappings when the new Socket.IO session is established.

### Integration Points
- `bridge/bridge.py` — add `@socketio.on('reconnect_game')` handler (D-02); modify `handle_disconnect()` for grace period (D-01).
- `server/game_server.py` — add `reconnect_player(player_id, room_code, callback_uri)` RPC that re-registers callback without creating a new player (D-02); add `send_chat()` (CHAT-01); add `start_vote()` / `submit_vote()` (POSTGAME-02/03/04).
- `server/event_broadcaster.py` — add failure counter per player_id; after 3 consecutive failures, call back into GameServer to remove player (INFRA-07/D-08).
- Frontend `socket.ts` — on connect, check localStorage for `{player_id, room_code}`; if found, emit `reconnect_game` event instead of new join flow.

</code_context>

<specifics>
## Specific Ideas

- Reconnect event name: `reconnect_game` (Socket.IO event from client); server-side RPC: `reconnect_player(player_id, room_code, callback_uri)`.
- Grace period duration: ~5 seconds before bridge calls `leave_game()`. Use `threading.Timer(5, leave_fn)` per SID; cancel on reconnect.
- PLAYER_LEFT event payload: `{player_id, player_name, room_code}` — mirrors PLAYER_JOINED structure.
- Vote end events: `GAME_RESTARTING` (new images assigned, ROUND_START incoming) vs. `GAME_ENDED` (redirect trigger for client).
- Chat event: `on_chat_message` callback with `{player_id, player_name, message, timestamp}`.
- Post-game screen: shows top-3 podium + per-turn breakdown table; then a vote section with timer bar (same timer component pattern as game phases).

</specifics>

<deferred>
## Deferred Ideas

- Reconnection notification banner (UI-09 "amber: reconnecting, red: offline") — the banner behavior is specified in REQUIREMENTS.md UI-09 but detailed visual treatment deferred to Phase 8 UI Polish.
- Spectator mode — v2, deferred at project init.
- Persistent game history — v2, deferred at project init.

</deferred>

---

*Phase: 7-reconnection-end-of-game*
*Context gathered: 2026-05-15*
