import time

import xbmc

from resources.lib.modules.globals import g

ONWAKE_NETWORK_UP_DELAY = 5


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
            g.log("System.OnWake notification received", "info")
            if not g.wait_for_abort(ONWAKE_NETWORK_UP_DELAY):  # Sleep for 5 seconds to make sure network is up
                if g.PLATFORM == "android":
                    g.clear_runtime_setting("system.sleeping")
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=runMaintenance")')
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=torrentCacheCleanup")')
            if not g.wait_for_abort(15):  # Sleep to make sure tokens refreshed during maintenance
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncTraktActivities")')

        if method == "System.OnSleep":
            g.log("System.OnSleep notification received", "info")
            if g.PLATFORM == "android":
                g.set_runtime_setting("system.sleeping", True)
