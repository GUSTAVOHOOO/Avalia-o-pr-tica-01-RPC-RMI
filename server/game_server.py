"""GameServer — Pyro5 RPC daemon exposing the core game API.

Registers itself with the Pyro5 Name Server under config.GAME_SERVER_NAME
so bridge and clients can discover it without hardcoded URIs (INFRA-06).

Bind address is always 127.0.0.1 (T-01-04 — never 0.0.0.0).
Name Server lookup always passes host=config.NS_HOST to avoid UDP broadcast
(D-01/D-02).
"""

import dataclasses
import json
import os
import random
import string
import sys
import threading
import uuid
from typing import List, Optional

# Allow `import config` when running as `python server/game_server.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Pyro5.api

import config
from server.event_broadcaster import EventBroadcaster
from server.turn_machine import TurnMachine


# ---------------------------------------------------------------------------
# Session dataclasses
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class PlayerInfo:
    """Represents a player within a game session."""

    player_id: str
    player_name: str
    callback_uri: str
    is_host: bool


@dataclasses.dataclass
class GameSession:
    """Authoritative game session state stored on the server.

    All mutations must hold GameServer.lock (RLock).
    """

    room_code: str
    host_id: str
    max_turns: int
    status: str  # "WAITING" | "IN_PROGRESS" | "ENDED"
    players: List[PlayerInfo] = dataclasses.field(default_factory=list)
    turn_machine: object = dataclasses.field(default=None, repr=False)  # TurnMachine instance, set by start_game()
    accumulated_scores: dict = dataclasses.field(default_factory=dict)
    current_image_assignments: dict = dataclasses.field(default_factory=dict)

    @property
    def player_count(self) -> int:
        """Number of players currently in the session."""
        return len(self.players)

    def get_player_dicts(self) -> list:
        """Return a serializable list of player info dicts."""
        return [
            {
                "player_id": p.player_id,
                "player_name": p.player_name,
                "is_host": p.is_host,
            }
            for p in self.players
        ]


# ---------------------------------------------------------------------------
# GameServer
# ---------------------------------------------------------------------------

@Pyro5.api.expose
class GameServer:
    """Exposed Pyro5 server object.  All public methods are callable via RPC."""

    def __init__(self):
        self.lock = threading.RLock()
        self.broadcaster = EventBroadcaster()
        self.sessions: dict = {}  # room_code -> GameSession
        self._player_to_room: dict = {}  # player_id -> room_code (WR-06)
        manifest_path = os.path.join(os.path.dirname(__file__), "images", "manifest.json")
        with open(manifest_path, encoding="utf-8") as manifest_file:
            self._image_manifest: dict = json.load(manifest_file)
        self._used_images_this_game: dict = {}

    def ping(self) -> str:
        """Health-check endpoint — returns 'pong'."""
        return "pong"

    def register_callback(self, player_id: str, callback_uri: str) -> bool:
        """Register (or overwrite) a callback URI for a player.

        Both arguments must be non-empty strings (T-01-03 input validation).
        Raises ValueError if either is empty or not a str.

        Args:
            player_id: Unique identifier for the player.
            callback_uri: Pyro5 URI of the player's callback daemon
                          (e.g. "PYRO:player.cb@127.0.0.1:PORT").

        Returns:
            True on success.
        """
        if not isinstance(player_id, str) or not player_id:
            raise ValueError("player_id and callback_uri must be non-empty strings")
        if not isinstance(callback_uri, str) or not callback_uri:
            raise ValueError("player_id and callback_uri must be non-empty strings")

        self.broadcaster.register_callback(player_id, callback_uri)
        return True

    @Pyro5.api.oneway
    def broadcast_test(self, message: str) -> None:
        """Fire-and-forget broadcast to all registered callbacks.

        Decorated with @oneway so the caller returns immediately without
        waiting for callbacks to complete — prevents deadlock when a
        callback receiver proxy is registered (D-09).

        Args:
            message: Arbitrary string payload included in the test event data.
        """
        self.broadcaster.broadcast("test_event", {"message": message, "source": "broadcast_test"})

    # -----------------------------------------------------------------------
    # Session management methods (Phase 2)
    # -----------------------------------------------------------------------

    def _generate_room_code(self) -> str:
        """Generate a unique 6-character uppercase alphanumeric room code.

        Must be called while self.lock is held.  Retries until a code not
        already in self.sessions is found (collision avoidance).
        """
        chars = string.ascii_uppercase + string.digits
        while True:
            code = "".join(random.choices(chars, k=6))
            if code not in self.sessions:
                return code

    def create_game(self, player_name: str, callback_uri: str, max_turns: int) -> dict:
        """Create a new game session and register the host's callback.

        Validates inputs server-side (T-02-02, T-02-03).  Absorbs callback
        registration so the bridge does NOT need to call register_callback
        separately (D-03).

        Args:
            player_name: Host's display name (non-empty, max 20 chars).
            callback_uri: Pyro5 URI of the player's callback daemon.
            max_turns: Number of game turns; must be in {3, 5, 7, 10}.

        Returns:
            {"player_id": str, "room_code": str, "is_host": True}

        Raises:
            ValueError: On invalid arguments.
        """
        if not isinstance(player_name, str) or not player_name:
            raise ValueError("player_name must be a non-empty string")
        if len(player_name) > 20:
            raise ValueError("player_name must be at most 20 characters")
        if not isinstance(callback_uri, str) or not callback_uri:
            raise ValueError("callback_uri must be a non-empty string")
        if max_turns not in {3, 5, 7, 10}:
            raise ValueError("max_turns must be one of {3, 5, 7, 10}")

        with self.lock:
            room_code = self._generate_room_code()
            player_id = str(uuid.uuid4())
            player = PlayerInfo(
                player_id=player_id,
                player_name=player_name,
                callback_uri=callback_uri,
                is_host=True,
            )
            session = GameSession(
                room_code=room_code,
                host_id=player_id,
                max_turns=max_turns,
                status="WAITING",
                players=[player],
            )
            self.sessions[room_code] = session
            self.broadcaster.register_callback(player_id, callback_uri)
            self._player_to_room[player_id] = room_code  # WR-06

        # No broadcast on create — first player has no one to notify (D-03)
        return {"player_id": player_id, "room_code": room_code, "is_host": True}

    def join_game(self, player_name: str, callback_uri: str, room_code: str) -> dict:
        """Join an existing WAITING game session and register the player's callback.

        Validates session state before allowing join (T-02-06, SESSION-04).
        Broadcasts PLAYER_JOINED OUTSIDE the lock to avoid deadlock (Pitfall 4).

        Args:
            player_name: Joining player's display name (non-empty, max 20 chars).
            callback_uri: Pyro5 URI of the player's callback daemon.
            room_code: 6-character code identifying the target session.

        Returns:
            {"player_id": str, "room_code": str, "is_host": False}  on success
            {"error": str}  when join is rejected.
        """
        if not isinstance(player_name, str) or not player_name:
            raise ValueError("player_name must be a non-empty string")
        if len(player_name) > 20:
            raise ValueError("player_name must be at most 20 characters")
        if not isinstance(callback_uri, str) or not callback_uri:
            raise ValueError("callback_uri must be a non-empty string")
        if not isinstance(room_code, str) or not room_code:
            raise ValueError("room_code must be a non-empty string")

        broadcast_data = None

        with self.lock:
            session = self.sessions.get(room_code)
            if session is None:
                return {"error": "sala nao encontrada"}
            if session.status != "WAITING":
                return {"error": "jogo em andamento"}
            if session.player_count >= 6:
                return {"error": "sala cheia"}

            player_id = str(uuid.uuid4())
            player = PlayerInfo(
                player_id=player_id,
                player_name=player_name,
                callback_uri=callback_uri,
                is_host=False,
            )
            session.players.append(player)
            self.broadcaster.register_callback(player_id, callback_uri)
            self._player_to_room[player_id] = room_code  # WR-06

            # Snapshot broadcast data before releasing lock (Pitfall 4)
            broadcast_data = {
                "room_code": room_code,
                "player": {
                    "player_id": player_id,
                    "player_name": player_name,
                    "is_host": False,
                },
                "players": session.get_player_dicts(),
            }

        # Broadcast OUTSIDE the lock — EventBroadcaster.broadcast() does network I/O
        self.broadcaster.broadcast("player_joined", broadcast_data)
        return {"player_id": player_id, "room_code": room_code, "is_host": False}

    def get_session(self, room_code: str) -> dict:
        """Return the current player list for a session (CR-01 — Lobby mount query).

        Args:
            room_code: The 6-character room identifier.

        Returns:
            {"players": list}  with serializable player dicts on success.
            {"error": str}  if room_code is not found.
        """
        with self.lock:
            session = self.sessions.get(room_code)
            if session is None:
                return {"error": "sala nao encontrada"}

            result = {
                "room_code": session.room_code,
                "status": session.status,
                "players": session.get_player_dicts(),
                "max_turns": session.max_turns,
            }
            if session.turn_machine is not None:
                result.update({
                    "phase": session.turn_machine.current_phase,
                    "remaining_seconds": session.turn_machine.remaining_seconds,
                    "current_turn": session.turn_machine.current_turn,
                })
            return result

    def _set_session_ended(self, room_code: str) -> None:
        """Mark session as ENDED. Called from TurnMachine on_game_ended callback (D-07).

        Acquires self.lock independently — called from TurnMachine's timer thread
        which never holds GameServer.lock, so no re-entrancy risk (T-03-10).
        """
        with self.lock:
            session = self.sessions.get(room_code)
            if session is not None:
                session.status = "ENDED"

    def _assign_images_for_turn(self, room_code: str) -> None:
        """Assign one unique image to each player and privately notify them."""
        assignments = []

        with self.lock:
            session = self.sessions.get(room_code)
            if session is None:
                return

            players = list(session.players)
            used = self._used_images_this_game.setdefault(room_code, set())
            available = [filename for filename in self._image_manifest if filename not in used]
            if len(available) < len(players):
                used.clear()
                available = list(self._image_manifest)

            selected = random.sample(available, len(players))
            session.current_image_assignments.clear()
            for player, filename in zip(players, selected):
                object_name = self._image_manifest[filename]
                session.current_image_assignments[player.player_id] = object_name
                used.add(filename)
                assignments.append((player.player_id, filename, object_name))

        for player_id, filename, object_name in assignments:
            self.broadcaster.send_to_player(
                player_id,
                "object_assigned",
                {
                    "target_player_id": player_id,
                    "image_url": f"/static/images/{filename}",
                    "object_name": object_name,
                },
            )

    def _consume_image_assignments(self, room_code: str) -> dict:
        """Snapshot and clear staged image assignments for TurnState creation."""
        with self.lock:
            session = self.sessions.get(room_code)
            if session is None:
                return {}
            snapshot = dict(session.current_image_assignments)
            session.current_image_assignments.clear()
            return snapshot

    def _accumulate_scores(self, room_code: str, turn_state) -> None:
        """Plan 03 replaces this no-op with real score accumulation."""
        print(f"[GameServer] scoring callback fired for room {room_code}", flush=True)

    def start_game(self, player_id: str) -> bool:
        """Start the game session if caller is host and ≥2 players are present.

        Validates host authorization (T-02-01, SESSION-06).  Broadcasts
        GAME_STARTED outside the lock.  max_turns is taken from the session
        (set at create_game time) — not accepted from the caller (CR-04).

        Creates a TurnMachine with on_game_ended callback and calls
        turn_machine.start() AFTER broadcasting game_started, so browsers
        navigate to GameScreen before the first phase_changed fires (T-03-07).

        Args:
            player_id: The player attempting to start the game (must be host).

        Returns:
            True if game was started; False if validation fails.
        """
        broadcast_data = None
        target_session = None

        with self.lock:
            # O(1) lookup via _player_to_room index (WR-06)
            room_code = self._player_to_room.get(player_id)
            target_session = self.sessions.get(room_code) if room_code else None

            if target_session is None:
                return False
            if target_session.host_id != player_id:
                return False
            if target_session.player_count < 2:
                return False

            target_session.status = "IN_PROGRESS"

            room_code_for_cb = target_session.room_code  # capture for closure
            target_session.turn_machine = TurnMachine(
                room_code=target_session.room_code,
                max_turns=target_session.max_turns,
                broadcaster=self.broadcaster,
                player_ids=[p.player_id for p in target_session.players],
                on_game_ended=lambda: self._set_session_ended(room_code_for_cb),
                on_round_start=lambda: self._assign_images_for_turn(room_code_for_cb),
                on_hint_phase_start=lambda: self._consume_image_assignments(room_code_for_cb),
                on_scoring_phase=lambda ts: self._accumulate_scores(room_code_for_cb, ts),
            )

            broadcast_data = {
                "room_code": target_session.room_code,
                "players": target_session.get_player_dicts(),
            }

        # Broadcast OUTSIDE the lock — then start TurnMachine AFTER game_started (T-03-07)
        self.broadcaster.broadcast("game_started", broadcast_data)
        target_session.turn_machine.start()  # fires ROUND_START AFTER game_started broadcast
        return True

    def advance_phase(self, player_id: str = None) -> bool:
        """Operator/test RPC: skip current phase immediately.

        Not decorated with @oneway — caller needs confirmation before asserting state
        (RESEARCH.md Pitfall 5).
        player_id accepted but not validated in Phase 3 (authorization deferred per CONTEXT.md).

        Returns True if advance succeeded; False if no active turn machine for this player's session.
        """
        with self.lock:
            room_code = self._player_to_room.get(player_id) if player_id else None
            # If no player_id, try first IN_PROGRESS session (for test convenience)
            if room_code is None:
                room_code = next(
                    (rc for rc, s in self.sessions.items() if s.status == "IN_PROGRESS"),
                    None
                )
            if room_code is None:
                return False
            session = self.sessions.get(room_code)
            if session is None or session.turn_machine is None:
                return False
            tm = session.turn_machine

        tm.advance_phase_manual()
        return True

    def leave_game(self, player_id: str) -> bool:
        """Remove a player from their session.

        If the leaving player was host and the session is WAITING, the next
        player in join order is promoted to host.  If the session becomes
        empty, it is deleted.  Broadcasts HOST_CHANGED outside the lock if
        host changed (D-05).

        Args:
            player_id: The player leaving the game.

        Returns:
            True if player was found and removed; False otherwise.
        """
        broadcast_data = None
        host_changed = False

        with self.lock:
            # O(1) lookup via _player_to_room index (WR-06)
            room_code = self._player_to_room.pop(player_id, None)
            if room_code is None:
                return False
            target_session = self.sessions.get(room_code)
            if target_session is None:
                return False

            # Remove the player and unregister their callback (WR-05)
            target_session.players = [
                p for p in target_session.players if p.player_id != player_id
            ]
            self.broadcaster.unregister_callback(player_id)

            # If session is now empty, delete it
            if not target_session.players:
                del self.sessions[target_session.room_code]
                return True

            # If the leaving player was the host and session is still WAITING,
            # promote the first remaining player as the new host
            was_host = (target_session.host_id == player_id)
            if was_host and target_session.status == "WAITING":
                new_host = target_session.players[0]
                new_host.is_host = True
                target_session.host_id = new_host.player_id
                host_changed = True
                broadcast_data = {
                    "room_code": target_session.room_code,
                    "new_host_id": new_host.player_id,
                    "players": target_session.get_player_dicts(),
                }

        # Broadcast HOST_CHANGED OUTSIDE the lock
        if host_changed and broadcast_data:
            self.broadcaster.broadcast("host_changed", broadcast_data)

        return True


if __name__ == "__main__":
    server = GameServer()
    daemon = Pyro5.api.Daemon(host=config.DAEMON_BIND_HOST, port=config.GAME_SERVER_PORT)
    uri = daemon.register(server, objectId=config.GAME_SERVER_NAME)

    try:
        ns = Pyro5.api.locate_ns(host=config.NS_HOST)
        ns.register(config.GAME_SERVER_NAME, uri)
        print(f"GameServer ready at {uri}")
        print(f"Registered in NS as '{config.GAME_SERVER_NAME}'")
    except Exception as e:
        print(f"Warning: could not register with Name Server: {e}", file=sys.stderr)
        print(f"GameServer ready at {uri} (direct URI — NS not available)")

    daemon.requestLoop()
