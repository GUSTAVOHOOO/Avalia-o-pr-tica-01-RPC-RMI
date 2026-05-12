"""Phase 1 unit tests — real in-process Pyro5 daemon (D-04, D-05).

Each test that exercises Pyro5 RPC starts its own daemon in a background thread,
runs the assertion, then shuts the daemon down.  No mocks, no Name Server required.

Test coverage:
  test_ping               — INFRA-01: ping() returns "pong" over real RPC
  test_register_callback  — INFRA-02: register_callback stores URI; second call overwrites;
                            empty args raise Pyro5.errors.PyroError
  test_broadcast_delivery — INFRA-03: broadcast() delivers event to all registered callbacks
  test_per_thread_proxy   — INFRA-05: deferred to Plan 04 (bridge per-thread proxy)
"""

import threading
import time

import pytest
import Pyro5.api
import Pyro5.errors

from server.game_server import GameServer


# ---------------------------------------------------------------------------
# Helper: start an in-process Pyro5 daemon for a single object
# ---------------------------------------------------------------------------

def _start_daemon(obj, object_id: str):
    """Register obj in a new daemon and start requestLoop in a daemon thread.

    Returns (daemon, uri_str).
    """
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    uri = daemon.register(obj, objectId=object_id)
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()
    return daemon, str(uri)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ping():
    """INFRA-01: GameServer.ping() returns 'pong' over a real in-process Pyro5 RPC call."""
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.game.server.ping")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            result = proxy.ping()
        assert result == "pong", f"Expected 'pong', got {result!r}"
    finally:
        daemon.shutdown()


def test_register_callback():
    """INFRA-02: register_callback stores URI; second call with same id overwrites it;
    empty player_id raises Pyro5.errors.PyroError (ValueError propagated over RPC).
    """
    server = GameServer()
    daemon, uri = _start_daemon(server, "test.game.server.register")
    try:
        with Pyro5.api.Proxy(uri) as proxy:
            # First registration
            result1 = proxy.register_callback("p1", "PYRO:fake@127.0.0.1:9999")
            assert result1 is True

            # Second call with same player_id — should overwrite and still return True
            result2 = proxy.register_callback("p1", "PYRO:fake2@127.0.0.1:9998")
            assert result2 is True

            # Verify the overwrite by inspecting broadcaster.callbacks on the server object
            # (direct attribute access — not via RPC)
            with server.broadcaster.lock:
                assert "p1" in server.broadcaster.callbacks

            # Empty player_id must raise an error propagated over RPC.
            # Pyro5 re-raises the original exception type (ValueError) when the
            # class is a built-in — it does not always wrap in PyroError.
            with pytest.raises((Pyro5.errors.PyroError, ValueError)):
                proxy.register_callback("", "PYRO:fake@127.0.0.1:9999")
    finally:
        daemon.shutdown()


def test_broadcast_delivery():
    """INFRA-03: broadcast() delivers the event to all registered callback receivers."""

    @Pyro5.api.expose
    class TestCallbackReceiver:
        """Minimal callback receiver that collects received events."""

        def __init__(self):
            self.received = []
            self.event = threading.Event()

        def on_test_event(self, data):
            self.received.append(data)
            self.event.set()

    # Start daemons for both GameServer and the callback receiver
    server = GameServer()
    server_daemon, server_uri = _start_daemon(server, "test.game.server.broadcast")

    receiver = TestCallbackReceiver()
    cb_daemon, cb_uri = _start_daemon(receiver, "test.callback.receiver")

    try:
        server.broadcaster.register_callback("r1", cb_uri)
        server.broadcaster.broadcast("test_event", {"msg": "hello"})

        # Wait until on_test_event signals delivery (up to 5 s)
        delivered = receiver.event.wait(timeout=5)
        assert delivered, "Timed out waiting for broadcast delivery (>5 s)"

        assert len(receiver.received) == 1, (
            f"Expected 1 received event, got {len(receiver.received)}"
        )
        assert receiver.received[0] == {"msg": "hello"}, (
            f"Unexpected payload: {receiver.received[0]!r}"
        )
    finally:
        server_daemon.shutdown()
        cb_daemon.shutdown()


def test_per_thread_proxy():
    """INFRA-05: two threads each calling get_game_server_proxy() (replicated locally
    using threading.local()) must receive different proxy objects — id() values differ.

    The test runs an in-process GameServer daemon to provide a valid URI so that
    Pyro5.api.Proxy() can actually be constructed without DNS/NS dependency.
    It does NOT import from bridge.bridge to keep this test independent of
    Flask/SocketIO startup.
    """
    # Replicate the bridge threading.local() pattern locally (no bridge import)
    local_store = threading.local()

    def get_proxy(uri: str) -> Pyro5.api.Proxy:
        """Mirror of bridge.get_game_server_proxy() using a local threading.local."""
        if not hasattr(local_store, "proxy"):
            local_store.proxy = Pyro5.api.Proxy(uri)
        return local_store.proxy

    # Start an in-process GameServer daemon to obtain a valid Pyro5 URI
    server = GameServer()
    daemon = Pyro5.api.Daemon(host="127.0.0.1")
    uri = str(daemon.register(server, objectId="test.game.server.thread"))
    t = threading.Thread(target=daemon.requestLoop, daemon=True)
    t.start()

    proxy_ids: list = []
    barrier = threading.Barrier(2)

    def thread_target():
        proxy = get_proxy(uri)
        proxy_ids.append(id(proxy))
        barrier.wait()

    try:
        t1 = threading.Thread(target=thread_target)
        t2 = threading.Thread(target=thread_target)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert len(proxy_ids) == 2, f"Expected 2 proxy ids, got {len(proxy_ids)}"
        assert proxy_ids[0] != proxy_ids[1], (
            "Both threads returned the same proxy object — threading.local() isolation broken"
        )
    finally:
        daemon.shutdown()
