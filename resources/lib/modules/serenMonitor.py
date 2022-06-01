# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import time

import xbmc

from resources.lib.modules.globals import g


class SerenMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        callback_time = int(time.time())
        if g.get_int_runtime_setting("onSettingsChangedLastCalled") == callback_time:
            g.log("Debouncing onSettingsChange call", "debug")
            # This check is to debounce multiple onSettingsChange calls to the nearest second as the callbacks
            # can come a bit late after setting multiple settings programmatically and cause
            # the settings persisted flag to be cleared
            return
        g.set_runtime_setting("onSettingsChangedLastCalled", callback_time)
        g.log("SETTINGS UPDATED", "info")
        if g.SETTINGS_CACHE.get_settings_persisted_flag():
            return
        g.log("FLUSHING SETTINGS CACHE", "info")
        g.SETTINGS_CACHE.clear_cache()
        g.trigger_widget_refresh(if_playing=False)

    def onNotification(self, sender, method, data):
        if method == "System.OnWake":
            g.log("System.OnWake notification received" "info")
            xbmc.executebuiltin(
                'RunPlugin("plugin://plugin.video.seren/?action=runMaintenance")'
            )
            xbmc.executebuiltin(
                'RunPlugin("plugin://plugin.video.seren/?action=torrentCacheCleanup")'
            )
            if not g.wait_for_abort(15):  # Sleep to make sure tokens refreshed during maintenance
                xbmc.executebuiltin(
                    'RunPlugin("plugin://plugin.video.seren/?action=syncTraktActivities")'
                )
        return
