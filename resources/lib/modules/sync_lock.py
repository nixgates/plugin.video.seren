from resources.lib.modules.globals import g


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
        while not g.abort_requested() and self._still_processing() and not g.wait_for_abort(0.100):
            pass
