"""EventBroadcaster — manages Pyro5 callback proxies and fan-out delivery.

Stores a {player_id: Proxy(callback_uri)} dict protected by a threading.Lock.
broadcast() snapshots the dict under lock, iterates outside the lock (avoids
holding the lock during network I/O), and removes failed entries.
"""

import threading

import Pyro5.api


class EventBroadcaster:
    """Manages registered callback proxies and delivers events to them."""

    def __init__(self):
        self.callbacks = {}          # player_id -> Pyro5.api.Proxy
        self.lock = threading.Lock()

    def register_callback(self, player_id: str, callback_uri: str):
        """Store (or overwrite) the callback proxy for player_id.

        A second call with the same player_id replaces the existing proxy.
        """
        with self.lock:
            self.callbacks[player_id] = Pyro5.api.Proxy(callback_uri)

    def broadcast(self, event_type: str, data: dict, exclude=None):
        """Fan-out event_type to all registered callbacks.

        Snapshots the callbacks dict under lock, then iterates outside the lock
        so network I/O does not block other threads from registering callbacks.
        Failed proxies are removed from self.callbacks after the iteration.

        Args:
            event_type: Name appended to "on_" to form the method name called on
                        each callback receiver (e.g. "test_event" -> on_test_event).
            data: Payload dict passed to each callback method.
            exclude: Optional list of player_ids to skip.
        """
        exclude = exclude or []
        failed = []

        with self.lock:
            snapshot = dict(self.callbacks)   # copy under lock; iterate outside

        for player_id, proxy in snapshot.items():
            if player_id in exclude:
                continue
            try:
                method = getattr(proxy, "on_" + event_type.lower())
                method(data)
            except Exception as e:
                print(f"[EventBroadcaster] Callback failed for {player_id}: {e}")
                failed.append(player_id)

        if failed:
            with self.lock:
                for pid in failed:
                    self.callbacks.pop(pid, None)

    def send_to_player(self, player_id: str, event_type: str, data: dict):
        """Deliver event_type to a single registered player.

        Raises KeyError silently (caught internally) if player_id is not
        registered — the caller does not need to handle missing players.
        """
        with self.lock:
            proxy = self.callbacks.get(player_id)

        if proxy is None:
            return

        try:
            method = getattr(proxy, "on_" + event_type.lower())
            method(data)
        except Exception as e:
            print(f"[EventBroadcaster] send_to_player failed for {player_id}: {e}")
            with self.lock:
                self.callbacks.pop(player_id, None)
