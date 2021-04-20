# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import sqlite3
import sys
from random import randint

import xbmc

from resources.lib.common import tools

if tools.is_stub():
    # noinspection PyUnresolvedReferences
    from mock_kodi import MOCK

from resources.lib.modules.globals import g

from resources.lib.common import maintenance
from resources.lib.database.trakt_sync.activities import TraktSyncDatabase
from resources.lib.modules.serenMonitor import SerenMonitor
from resources.lib.modules.update_news import do_update_news

g.init_globals(sys.argv)
g.set_setting("general.tempSilent", "false")
g.HOME_WINDOW.setProperty("SerenDownloadManagerIndex", "{}")

g.log("##################  STARTING SERVICE  ######################")
g.log("### {} {}".format(g.ADDON_ID, g.VERSION))
g.log("### PLATFORM: {}".format(g.PLATFORM))
g.log("### SQLite: {}".format(sqlite3.sqlite_version))  # pylint: disable=no-member
g.log("#############  SERVICE ENTERED KEEP ALIVE  #################")

monitor = SerenMonitor()
try:
    xbmc.executebuiltin(
        'RunPlugin("plugin://plugin.video.seren/?action=longLifeServiceManager")'
    )

    do_update_news()
    g.clear_kodi_bookmarks()

    # Disable the restoration of reuselanguageinvoker addon.xml based on settings value on upgrade.
    # It can still be toggled in settings although initially it will show user's last setting value
    # This is in preparation for removal of user setting/toggle.
    # maintenance.toggle_reuselanguageinvoker(
    #     True if g.get_setting("reuselanguageinvoker.status") == "Enabled" else False)

    while not monitor.abortRequested():
        try:
            if g.get_bool_setting("general.checkAddonUpdates"):
                maintenance.check_for_addon_update()
            try:
                maintenance.run_maintenance()
                TraktSyncDatabase().sync_activities()
            except Exception as e:
                g.log("Background Service Failure", "error")
                g.log_stacktrace()
            if g.wait_for_abort(60 * randint(13, 17)):
                break
        except:  # pylint: disable=bare-except
            g.log("Background service failure", "error")
            g.log_stacktrace()
            if g.wait_for_abort(60 * randint(13, 17)):
                break
            continue
finally:
    del monitor
    g.deinit()
