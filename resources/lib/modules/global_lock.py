from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.globals import g


class GlobalLock:
    def __init__(self, lock_name, run_once=False, check_sum=None):
        self._lock_name = lock_name
        self._run_once = run_once
        self._lock_format = "{}.GlobalLock.{}.{}"
        self._check_sum = check_sum or 'global'

    def _create_key(self, value):
        return self._lock_format.format(g.ADDON_NAME, self._lock_name, value)

    def _run(self):
        while not g.abort_requested() and self._running() and not g.wait_for_abort(0.100):
            pass
        g.set_runtime_setting(self._create_key("Running"), True)
        self._check_ran_once_already()

    def _running(self):
        return g.get_bool_runtime_setting(self._create_key("Running"))

    def _check_ran_once_already(self):
        if (
            g.get_bool_runtime_setting(self._create_key("RunOnce"))
            and g.get_runtime_setting(self._create_key("CheckSum")) == self._check_sum
        ):
            g.clear_runtime_setting(self._create_key("Running"))
            raise RanOnceAlready(f"Lock name: {self._lock_name}, Checksum: {self._check_sum}")

    def __enter__(self):
        self._run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._run_once:
            g.set_runtime_setting(self._create_key("RunOnce"), True)
            g.set_runtime_setting(self._create_key("CheckSum"), self._check_sum)
        g.clear_runtime_setting(self._create_key("Running"))
