# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from resources.lib.modules.globals import g


class SyncLock(object):
    def __init__(self, lock_name, trakt_ids=()):
        self._lock_name = lock_name
        self._lock_format = "{}.SyncLock.{}.{}"
        self._trakt_ids = trakt_ids
        self._running_ids = []
        self._handle = str(g.PLUGIN_HANDLE)

    def _create_key(self, value):
        return self._lock_format.format(g.ADDON_NAME, self._lock_name, value)

    def _run_id(self, i):
        g.HOME_WINDOW.setProperty(self._create_key(i), self._handle)
        return i

    def _run(self):
        self._running_ids = [self._run_id(i) for i in self._trakt_ids
                             if g.HOME_WINDOW.getProperty(self._create_key(i)) != self._handle]

    def _still_processing(self):
        return all(g.HOME_WINDOW.getProperty(self._create_key(i)) is None for i in self._trakt_ids)

    @property
    def running_ids(self):
        return self._running_ids

    def __enter__(self):
        self._run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        [g.HOME_WINDOW.clearProperty(self._create_key(i)) for i in self._trakt_ids
         if g.HOME_WINDOW.getProperty(self._create_key(i)) == self._handle]
        while not g.abort_requested() and self._still_processing():
            if g.wait_for_abort(.100):
                break

