import xbmc
from resources.lib.common import maintenance
from resources.lib.common import tools

tools.log('##################  STARTING SERVICE  ######################')
tools.log('Checking for incorrect addon ID')
import os, xbmc


if tools.kodiVersion == 17:
    if tools.condVisibility('System.HasAddon(plugin.video.Seren)'):
        tools.log('Incorrect Addon ID Identified')
        tools.log('Performing Migration')
        data_path = os.path.join(xbmc.translatePath('special://home'), 'userdata', 'addon_data')
        dir_listing = os.listdir(data_path)
        if 'plugin.video.Seren' in dir_listing:
            os.rename(os.path.join(data_path, 'plugin.video.Seren'), os.path.join(data_path, 'plugin.video.seren'))

        platform = sys.platform

        tools.showDialog.yesno('Seren',
                               'Because of an issue with original addon ID on release,'
                               ' Seren requires a restart of Kodi after this update.\n'
                               'Please restart Kodi now.')
    else:
        tools.log('No old release version found on device')

if tools.kodiVersion == 18:
    tools.log("VERSION 18")
if tools.kodiVersion == '18':
    tools.log("TEXT VERSION 18")

if tools.kodiVersion == 18:
    tools.log('VERSION 18 FOUND')
    data_path = os.path.join(xbmc.translatePath('special://home'), 'userdata', 'addon_data')
    dir_listing = os.listdir(data_path)
    if 'plugin.video.Seren' in dir_listing:
        os.rename(os.path.join(data_path, 'plugin.video.Seren'), os.path.join(data_path, 'plugin.video.seren'))
        tools.showDialog.yesno('Seren',
                               'Because of an issue with original addon ID on release,'
                               ' Seren requires a restart of Kodi after this update.\n'
                               'Please restart Kodi now.')

tools.log('Checking Common API Tokens for refresh')
maintenance.run_maintenance()
tools.log('Initial API Checks have completed succesfully')
monitor = xbmc.Monitor()
tools.log('#############  SERVICE ENTERED KEEP ALIVE  #################')

while not monitor.abortRequested():
    try:
        if monitor.waitForAbort(60*30):
            break
        tools.execute('RunPlugin("plugin://plugin.video.%s/?action=runMaintenance")' % tools.addonName.lower())
    except:
        continue