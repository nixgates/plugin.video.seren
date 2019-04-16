# -*- coding: utf-8 -*-

import os
import xbmc

from resources.lib.common import maintenance
from resources.lib.common import tools
from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase

tools.log('##################  STARTING SERVICE  ######################')

tools.setSetting('general.tempSilent', 'false')
tools.log('Checking Common API Tokens for refresh')
if tools.getSetting('general.checkAddonUpdates') == 'true':
    maintenance.check_for_addon_update()
maintenance.run_maintenance()
tools.log('Initial API Checks have completed succesfully')
monitor = xbmc.Monitor()
tools.log('#############  SERVICE ENTERED KEEP ALIVE  #################')
TraktSyncDatabase().sync_activities()

while not monitor.abortRequested():
    try:
        if monitor.waitForAbort(60 * 15):
            break
        tools.execute('RunPlugin("plugin://plugin.video.%s/?action=runMaintenance")' % tools.addonName.lower())
        TraktSyncDatabase().sync_activities()
    except:
        continue


