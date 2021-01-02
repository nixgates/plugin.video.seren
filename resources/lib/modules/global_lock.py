# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import threading

import xbmc

from resources.lib.modules.globals import g


class GlobalLock(object):
    def __init__(self, lock_name, threading_lock=threading.Lock(), run_once=False, check_sum=None):
        self._win = g.HOME_WINDOW
        self._lock_name = lock_name
        self._run_once = run_once
        self._lock_format = "{}.GlobalLock.{}.{}"
        self._threading_lock = threading_lock
        self._check_sum = check_sum or 'global'

    def _create_key(self, value):
        return self._lock_format.format(g.ADDON_NAME, self._lock_name, value)

    def _run(self):
        if self.runned_once():
            return
        monitor = xbmc.Monitor()
        while not monitor.abortRequested() and self.running():
            if monitor.waitForAbort(.100):
                break
        self._win.setProperty(self._create_key("Running"), 'true')

    def running(self):
        return self._win.getProperty(self._create_key("Running")) == 'true'

    def runned_once(self):
        return self._win.getProperty(self._create_key("RunOnce")) == 'true' and \
               self._win.getProperty(self._create_key("CheckSum")) == self._check_sum

    def __enter__(self):
        self._threading_lock.acquire()
        self._run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._run_once:
                self._win.setProperty(self._create_key("RunOnce"), 'true')
                self._win.setProperty(self._create_key("CheckSum"), self._check_sum)
            self._win.clearProperty(self._create_key("Running"))
        finally:
            self._threading_lock.release()
