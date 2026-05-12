"""test_client.py — CLI smoke test for the Pyro5 callback pipeline.

Manual 3-terminal demo artifact (D-04):
  Terminal 1: python -m Pyro5.nameserver --host 127.0.0.1
  Terminal 2: python server/game_server.py
  Terminal 3: python client/test_client.py

On success, prints "[PUSH RECEIVED]" within 10 seconds.

Callback daemon binds to 127.0.0.1 only (T-01-07 — loopback).
Game server is discovered via PYRONAME lookup — no hardcoded IP:port (INFRA-06).
"""

import os
import sys
import threading
import time

# Allow `import config` when running as `python client/test_client.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Pyro5.api

import config


@Pyro5.api.expose
class TestCallback:
    """Callback receiver registered with the GameServer to accept push events."""

    def __init__(self):
        self.received = []

    @Pyro5.api.oneway
    @Pyro5.api.callback
    def on_test_event(self, data: dict) -> None:
        """Called by the GameServer when broadcast_test() fires.

        Decorated @oneway so the server call returns immediately.
        Decorated @callback so Pyro5 allows the reverse call direction.
        """
        print(f"[PUSH RECEIVED] {data}")
        self.received.append(data)


def main() -> None:
    # Start callback daemon bound to loopback (T-01-07)
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    cb = TestCallback()
    cb_uri = daemon.register(cb)

    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()

    with Pyro5.api.Proxy(f"PYRONAME:{config.GAME_SERVER_NAME}@{config.NS_HOST}") as server:
        server.register_callback("test-cli", str(cb_uri))
        print("Registered callback. Waiting 10 seconds for push events...")
        time.sleep(10)

    daemon.shutdown()

    if not cb.received:
        print("WARNING: No push events received in 10 seconds.")
        sys.exit(1)

    print(f"Done. Received {len(cb.received)} push event(s).")


if __name__ == "__main__":
    main()
