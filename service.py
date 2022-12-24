import sqlite3
import sys
from random import randint

import xbmc

from resources.lib.common import tools

if tools.is_stub():
    # noinspection PyUnresolvedReferences
    from mock_kodi import MOCK

from resources.lib.modules.globals import g

from resources.lib.modules.seren_version import do_version_change
from resources.lib.modules.serenMonitor import SerenMonitor
from resources.lib.modules.update_news import do_update_news
from resources.lib.modules.manual_timezone import validate_timezone_detected

g.init_globals(sys.argv)
do_version_change()

g.log("##################  STARTING SERVICE  ######################")
g.log(f"### {g.ADDON_ID} {g.VERSION}")
g.log(f"### Platform: {g.PLATFORM}")
g.log(f"### Python: {sys.version.split(' ', 1)[0]}")
g.log(f"### SQLite: {sqlite3.sqlite_version}")  # pylint: disable=no-member
g.log(f"### Detected Kodi Version: {g.KODI_VERSION}")
g.log(f"### Detected timezone: {repr(g.LOCAL_TIMEZONE.zone)}")
g.log("#############  SERVICE ENTERED KEEP ALIVE  #################")

monitor = SerenMonitor()
try:
    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=longLifeServiceManager")')

    do_update_news()
    validate_timezone_detected()
    try:
        g.clear_kodi_bookmarks()
    except TypeError:
        g.log(
            "Unable to clear bookmarks on service init. This is not a problem if it occurs immediately after install.",
            "warning",
        )

    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=torrentCacheCleanup")')

    g.wait_for_abort(30)  # Sleep for a half a minute to allow widget loads to complete.
    while not monitor.abortRequested():
        xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=runMaintenance")')
        if not g.wait_for_abort(15):  # Sleep to make sure tokens refreshed during maintenance
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncTraktActivities")')
        if not g.wait_for_abort(15):  # Sleep to make sure we don't possibly clobber settings
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=cleanOrphanedMetadata")')
        if not g.wait_for_abort(15):  # Sleep to make sure we don't possibly clobber settings
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=updateLocalTimezone")')
        if g.wait_for_abort(60 * randint(13, 17)):
            break
finally:
    del monitor
    g.deinit()
