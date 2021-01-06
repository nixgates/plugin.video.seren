import xbmcgui

from resources.lib.modules.globals import g

last_update_required = "2.0"

update_messages = [
        g.get_language_string(30571)
    ]

def do_update_news():
    if last_update_required == g.get_setting("update.news.version"):
        return

    for msg in update_messages:
        xbmcgui.Dialog().ok(g.ADDON_NAME, msg)

    g.set_setting("update.news.version", last_update_required)
