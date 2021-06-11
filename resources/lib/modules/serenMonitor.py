# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.modules.globals import g

try:
    import xbmc
except ImportError:
    from mock_kodi import xbmc


class SerenMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        super(SerenMonitor, self).onSettingsChanged()
        g.log("SETTINGS UPDATED", "info")
        if g.SETTINGS_CACHE.get_settings_persisted_flag():
            return
        g.log("FLUSHING SETTINGS CACHE", "info")
        g.SETTINGS_CACHE.clear_cache()
        g.trigger_widget_refresh()
