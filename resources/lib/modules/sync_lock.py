# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from resources.lib.modules.globals import g


class SyncLock(object):
    def __init__(self, lock_name, trakt_ids=()):
        self._win = g.HOME_WINDOW
        self._lock_name = lock_name
        self._lock_format = "{}.SyncLock.{}.{}"
        self._trakt_ids = trakt_ids
        self._running_ids = []
        self._handle = str(g.PLUGIN_HANDLE)

    def _create_key(self, value):
        return self._lock_format.format(g.ADDON_NAME, self._lock_name, value)

    def _run_id(self, i):
        self._win.setProperty(self._create_key(i), self._handle)
        return i

    def _run(self):
        self._running_ids = [self._run_id(i) for i in self._trakt_ids
                             if self._win.getProperty(self._create_key(i)) != self._handle]

    def _still_processing(self):
        return all(self._win.getProperty(self._create_key(i)) is None for i in self._trakt_ids)

    @property
    def running_ids(self):
        return self._running_ids

    def __enter__(self):
        self._run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        [self._win.clearProperty(self._create_key(i)) for i in self._trakt_ids
         if self._win.getProperty(self._create_key(i)) == self._handle]
        monitor = xbmc.Monitor()
        while not monitor.abortRequested() and self._still_processing():
            if monitor.waitForAbort(.100):
                break

