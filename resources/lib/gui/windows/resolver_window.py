from . import set_info_properties
from resources.lib.common import tools
from resources.lib.gui.windows.single_item_window import SingleItemWindow
from resources.lib.modules.globals import g
from resources.lib.modules.resolver import Resolver


class ResolverWindow(SingleItemWindow):
    """
    Window for Resolver
    """

    def __init__(self, xml_file, location=None, item_information=None, close_callback=None):
        super().__init__(xml_file, location, item_information=item_information)
        self.return_data = None, None
        self.progress = 1
        self.resolver = None
        self.sources = None
        self.pack_select = False
        self.item_information = item_information
        self.close_callback = close_callback

    def onInit(self):
        """
        Callback method from Kodi to trigger background threads to process resolving
        :param test: Used for Unit testing purposes only
        :type test: bool
        :return: None
        :rtype: None
        """
        super().onInit()

    def _resolve_source(self):
        stream_link = None
        release_title = None

        for source in self.sources:
            if self.canceled:
                return None, None
            self._update_window_properties(source)
            try:
                stream_link, release_title = self.resolver.resolve_single_source(
                    source, self.item_information, self.pack_select
                )
                if stream_link:
                    break
            except Exception:
                g.log_stacktrace()
                continue
        if stream_link is None:
            self.return_data = "none", "none"
        else:
            self.return_data = stream_link, release_title

    def get_return_data(self):
        return (None, None) if self.canceled else self.return_data

    def _update_window_properties(self, source):
        debrid_provider = source.get("debrid_provider", "None").replace("_", " ")
        if "size" in source and source["size"] != "Variable":
            self.setProperty("source_size", tools.source_size_display(source["size"]))

        self.setProperty("release_title", source["release_title"])
        self.setProperty("debrid_provider", debrid_provider)
        self.setProperty("source_provider", source["provider"])
        self.setProperty("source_resolution", source["quality"])
        set_info_properties(source.get("info", {}), self)
        self.setProperty("source_type", source["type"])

        provider_imports = source.get("provider_imports", [])
        source_icon = self.provider_class.get_icon(provider_imports)
        if source_icon is not None:
            self.setProperty("source.icon", source_icon)

    def doModal(
        self,
        sources=None,
        pack_select=False,
    ):
        """
        Opens window in an intractable mode and runs background scripts
        :param sources: List of sources to attempt to resolve
        :type sources: list
        :param pack_select: Set to True to enable manual file selection
        :type pack_select: bool
        :return: Stream link
        :rtype: str
        """
        self.sources = sources or []
        self.pack_select = pack_select

        if not self.sources:
            return None, None

        self.resolver = Resolver()

        self._update_window_properties(self.sources[0])
        self._resolve_source()

        super().doModal()

    def close(self):
        super().close()
        if self.close_callback:
            self.close_callback
