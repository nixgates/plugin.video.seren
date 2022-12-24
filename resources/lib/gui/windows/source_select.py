import xbmcgui

from resources.lib.database.skinManager import SkinManager
from resources.lib.gui.windows.manual_caching import ManualCacheWindow
from resources.lib.gui.windows.source_window import SourceWindow
from resources.lib.modules.download_manager import create_task as download_file
from resources.lib.modules.exceptions import InvalidSourceType
from resources.lib.modules.globals import g
from resources.lib.modules.helpers import Resolverhelper


class SourceSelect(SourceWindow):
    """
    Window for source select
    """

    def __init__(self, xml_file, location, item_information=None, sources=None, uncached=None):
        super().__init__(xml_file, location, item_information=item_information, sources=sources)
        self.uncached_sources = uncached or []
        self.position = -1
        self.stream_link = False
        self.setProperty("instant_close", "false")
        self.setProperty("resolving", "false")

    def doModal(self):
        """
        Opens window in an interactive mode and runs background scripts
        :return:
        """
        super().doModal()
        return self.stream_link

    def handle_action(self, action_id, control_id=None):
        self.position = self.display_list.getSelectedPosition()

        if action_id == 117:
            response = xbmcgui.Dialog().contextmenu(
                [
                    g.get_language_string(30320),
                    g.get_language_string(30473),
                    g.get_language_string(30483),
                ]
            )
            if response == 0:
                self._resolve_item(False)
            elif response == 1:
                if not (download_location := g.get_setting("download.location")) or download_location == "userdata":
                    g.open_addon_settings(0, 26)
                    g.notification(g.ADDON_NAME, g.get_language_string(30446))
                else:
                    try:
                        download_file(self.sources[self.display_list.getSelectedPosition()])
                        g.notification(g.ADDON_NAME, g.get_language_string(30634), sound=False)
                    except InvalidSourceType as ist:
                        xbmcgui.Dialog().ok(
                            g.ADDON_NAME,
                            g.get_language_string(30641).format(ist.source_type),
                        )

            elif response == 2:
                self._resolve_item(True)

        if action_id == 7:
            if control_id == 1000:
                self._resolve_item(False)
            elif control_id == 2001:
                self._open_manual_cache_assist()
            elif control_id == 2999:
                self.close()

    def _resolve_item(self, pack_select):
        if g.get_bool_setting('general.autotrynext') and not pack_select:
            sources = self.sources[self.position :]
        else:
            sources = [self.sources[self.position]]

        resolver_helper = Resolverhelper()
        self.setProperty("resolving", "true")
        self.stream_link = resolver_helper.resolve_silent_or_visible(
            sources,
            self.item_information,
            pack_select,
            overwrite_cache=pack_select,
        )

        if self.stream_link is None:
            self.setProperty("resolving", "false")
            resolver_helper.close_window()
            g.notification(g.ADDON_NAME, g.get_language_string(30032), time=2000)
        else:
            self.setProperty("instant_close", "true")
            self.close()

    def _open_manual_cache_assist(self):
        newly_cached_source = None
        try:
            window = ManualCacheWindow(
                *SkinManager().confirm_skin_path('manual_caching.xml'),
                item_information=self.item_information,
                sources=self.uncached_sources,
                close_text=g.get_language_string(30624),
            )
            newly_cached_source = window.doModal()
        finally:
            del window

        if newly_cached_source is None:
            return

        self.sources = [newly_cached_source] + self.sources
        self.onInit()
