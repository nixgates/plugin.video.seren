import xbmc
from resources.lib.common import maintenance
from resources.lib.common import tools

tools.log('##################  STARTING SERVICE  ######################')
tools.log('Checking Common API Tokens for refresh')
maintenance.run_maintenance()
tools.log('Initial API Checks have completed succesfully')
monitor = xbmc.Monitor()
tools.log('#############  SERVICE ENTERED KEEP ALIVE  #################')

while not monitor.abortRequested():
    try:
        if monitor.waitForAbort(60*30):
            break
        tools.execute('RunPlugin("plugin://plugin.video.%s/?action=runMaintenance")' % tools.addonName)
    except:
        continue