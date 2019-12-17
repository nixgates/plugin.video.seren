# -*- coding: utf-8 -*-

import xbmc

from resources.lib.common import maintenance
from resources.lib.common import tools
from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase

tools.log('##################  STARTING SERVICE  ######################')
monitor = xbmc.Monitor()

tools.setSetting('general.tempSilent', 'false')

tools.log('Performing initial background maintenance...')

if tools.getSetting('general.checkAddonUpdates') == 'true':
    maintenance.check_for_addon_update()

TraktSyncDatabase().sync_activities()

maintenance.run_maintenance()

tools.log('Initial maintenance cycle completed')

tools.log('#############  SERVICE ENTERED KEEP ALIVE  #################')

while not monitor.abortRequested():
    try:
        if monitor.waitForAbort(60 * 15):
            break
        tools.execute('RunPlugin("plugin://plugin.video.%s/?action=runMaintenance")' % tools.addonName.lower())
        TraktSyncDatabase().sync_activities()
    except:
        continue


