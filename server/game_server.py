"""GameServer — Pyro5 RPC daemon exposing the core game API.

Registers itself with the Pyro5 Name Server under config.GAME_SERVER_NAME
so bridge and clients can discover it without hardcoded URIs (INFRA-06).

Bind address is always 127.0.0.1 (T-01-04 — never 0.0.0.0).
Name Server lookup always passes host=config.NS_HOST to avoid UDP broadcast
(D-01/D-02).
"""

import sys
import threading

import Pyro5.api

import config
from server.event_broadcaster import EventBroadcaster


@Pyro5.api.expose
class GameServer:
    """Exposed Pyro5 server object.  All public methods are callable via RPC."""

    def __init__(self):
        self.lock = threading.RLock()
        self.broadcaster = EventBroadcaster()

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


if __name__ == "__main__":
    server = GameServer()
    daemon = Pyro5.api.Daemon(host="127.0.0.1", port=config.GAME_SERVER_PORT)
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
