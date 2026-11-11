import threading
import time

from resources.lib.modules.globals import g

_wait_state = threading.local()

# Longest an interactive play waits for a background sync that is milling the same show.
SYNC_WAIT_CAP_SECONDS = 4.0


class BoundedSyncWait:
    """Cap how long SyncLock exits on this thread may wait for another sync to finish milling.

    One absolute deadline covers every wait made inside the block, so several waits share the budget.
    A play resolves its episode in more than one place and Kodi re-invokes the plugin once for the playlist, each in
    its own process, so the deadline is kept in a runtime setting: blocks entered within a minute of the first
    share its deadline instead of each getting a fresh budget.
    Meant for interactive playback, which would otherwise sit silently behind a background Trakt/MDBList sync.
    """

    _SHARED_KEY = "sync_wait_cap"

    def __init__(self, max_seconds):
        self._max_seconds = max_seconds
        self._previous = None

    def __enter__(self):
        now = time.time()
        deadline = now + self._max_seconds
        try:
            shared = str(g.get_runtime_setting(self._SHARED_KEY) or "").split("|")
            if len(shared) == 2 and now - float(shared[1]) < 60:
                deadline = float(shared[0])
            else:
                g.set_runtime_setting(self._SHARED_KEY, f"{deadline}|{now}")
        except (ValueError, TypeError):
            g.set_runtime_setting(self._SHARED_KEY, f"{deadline}|{now}")
        self._previous = getattr(_wait_state, "deadline", None)
        _wait_state.deadline = deadline
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _wait_state.deadline = self._previous


class SyncLock:
    def __init__(self, lock_name, trakt_ids=None):
        self._lock_name = lock_name
        self._lock_format = "{}.SyncLock.{}.{}"
        self._trakt_ids = trakt_ids or []
        self._running_ids = set()

    def _create_key(self, value):
        return self._lock_format.format(g.ADDON_NAME, self._lock_name, value)

    def _run_id(self, i):
        g.set_runtime_setting(self._create_key(i), True)
        return i

    def _run(self):
        self._running_ids = {
            self._run_id(i) for i in self._trakt_ids if not g.get_bool_runtime_setting(self._create_key(i))
        }

    def _still_processing(self):
        return any(g.get_bool_runtime_setting(self._create_key(i)) for i in self._trakt_ids)

    @property
    def running_ids(self):
        return self._running_ids

    def __enter__(self):
        self._run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for i in self._running_ids:
            g.clear_runtime_setting(self._create_key(i))
        deadline = getattr(_wait_state, "deadline", None)
        started = time.time()
        while not g.abort_requested() and self._still_processing() and not g.wait_for_abort(0.100):
            if deadline is not None and time.time() >= deadline:
                busy = [i for i in self._trakt_ids if g.get_bool_runtime_setting(self._create_key(i))]
                g.log(
                    f"SyncLock {self._lock_name}: another sync is still milling show id(s) {busy}; "
                    f"continuing after {time.time() - started:.1f}s with the data already stored",
                    "warning",
                )
                break
