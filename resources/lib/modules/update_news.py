import xbmcgui

from resources.lib.modules.globals import g

last_update_required = "2.1.4"


def do_update_news():
    if last_update_required == g.get_setting("update.news.version"):
        return

    for msg in [g.get_language_string(30559)]:
        xbmcgui.Dialog().ok(g.ADDON_NAME, msg)

    g.set_setting("update.news.version", last_update_required)
