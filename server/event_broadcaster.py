"""EventBroadcaster — manages Pyro5 callback proxies and fan-out delivery.

Stores a {player_id: Proxy(callback_uri)} dict protected by a threading.Lock.
broadcast() snapshots the dict under lock, iterates outside the lock (avoids
holding the lock during network I/O), and removes failed entries.
"""

import threading

import Pyro5.api


class EventBroadcaster:
    """Manages registered callback URIs and delivers events to them.

    Stores URI strings (not Proxy objects) — Pyro5 proxies are not thread-safe
    and must be created in the thread that uses them (C2 pitfall).
    """

    def __init__(self):
        self.callbacks = {}          # player_id -> uri str
        self.lock = threading.Lock()

    def register_callback(self, player_id: str, callback_uri: str):
        """Store (or overwrite) the callback URI for player_id.

        A second call with the same player_id replaces the existing entry.
        """
        with self.lock:
            self.callbacks[player_id] = callback_uri

    def unregister_callback(self, player_id: str):
        """Remove the callback URI for player_id if present (WR-05).

        Safe to call even if player_id was never registered (no-op).
        """
        with self.lock:
            self.callbacks.pop(player_id, None)

    def broadcast(self, event_type: str, data: dict, exclude=None):
        """Fan-out event_type to all registered callbacks.

        Snapshots the URI dict under lock, creates a fresh proxy per call in
        the calling thread (Pyro5 proxies are not thread-safe — C2 pitfall),
        iterates outside the lock so network I/O doesn't block registration.
        Failed entries are removed from self.callbacks after the iteration.

        Args:
            event_type: Name appended to "on_" to form the method name called on
                        each callback receiver (e.g. "test_event" -> on_test_event).
            data: Payload dict passed to each callback method.
            exclude: Optional list of player_ids to skip.
        """
        exclude = exclude or []
        failed = []

        with self.lock:
            snapshot = dict(self.callbacks)   # copy URIs under lock; iterate outside

        delivered_uris = set()
        for player_id, uri in snapshot.items():
            if player_id in exclude:
                continue
            if uri in delivered_uris:
                continue
            delivered_uris.add(uri)
            try:
                with Pyro5.api.Proxy(uri) as proxy:
                    method = getattr(proxy, "on_" + event_type.lower())
                    method(data)
            except (ConnectionRefusedError, OSError) as e:
                # Permanent failure — remote end is gone; remove entry (WR-03)
                print(f"[EventBroadcaster] Permanent callback failure for {player_id}: {e}",
                      flush=True)
                failed.append(player_id)
            except Exception as e:
                # Transient failure (timeout, etc.) — log but keep registration
                print(f"[EventBroadcaster] Transient callback error for {player_id}: {e}",
                      flush=True)

        if failed:
            with self.lock:
                for pid in failed:
                    self.callbacks.pop(pid, None)

    def send_to_player(self, player_id: str, event_type: str, data: dict):
        """Deliver event_type to a single registered player."""
        with self.lock:
            uri = self.callbacks.get(player_id)

        if uri is None:
            return

        try:
            with Pyro5.api.Proxy(uri) as proxy:
                method = getattr(proxy, "on_" + event_type.lower())
                method(data)
        except Exception as e:
            print(f"[EventBroadcaster] send_to_player failed for {player_id}: {e}",
                  flush=True)
            with self.lock:
                self.callbacks.pop(player_id, None)
