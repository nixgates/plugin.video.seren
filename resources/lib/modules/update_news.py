import xbmcgui

from resources.lib.modules.globals import g

update_news_versions = {
    "2.1.4": 30530,
    "2.2.0": 30566,
}


def do_update_news():
    last_update_news_version = g.get_setting("update.news.version")
    max_update_news_version = max(update_news_versions)

    if not last_update_news_version:
        g.set_setting("update.news.version", max_update_news_version)
        return

    if max_update_news_version == last_update_news_version:
        return

    for msg in [
        g.get_language_string(update_news_versions[v])
        for v in sorted(update_news_versions)
        if v > last_update_news_version
    ]:
        xbmcgui.Dialog().ok(f"{g.ADDON_NAME} - {g.get_language_string(30567)}", msg)

    g.set_setting("update.news.version", max_update_news_version)
