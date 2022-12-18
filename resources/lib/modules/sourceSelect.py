from resources.lib.database.skinManager import SkinManager
from resources.lib.modules.exceptions import NoPlayableSourcesException
from resources.lib.modules.globals import g


def source_select(uncached_sources, source_list, item_information):
    selection = None

    try:
        if len(source_list) == 0 and len(uncached_sources) == 0:
            return None

        from resources.lib.gui.windows.source_select import SourceSelect

        selection = None
        try:
            window = SourceSelect(
                *SkinManager().confirm_skin_path("source_select.xml"),
                item_information=item_information,
                sources=source_list,
                uncached=uncached_sources
            )
            selection = window.doModal()
        finally:
            del window

        if selection is None:
            g.notification(g.ADDON_NAME, g.get_language_string(30032), time=5000)
            raise NoPlayableSourcesException
        if not selection:
            g.cancel_playback()

    finally:
        return selection
