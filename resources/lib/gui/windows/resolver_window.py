import threading

from resources.lib.common import tools
from resources.lib.gui.windows.single_item_window import SingleItemWindow
from resources.lib.modules.resolver import Resolver
from . import set_info_properties


class ResolverWindow(SingleItemWindow):
    """
    Window for Resolver
    """

    def __init__(self, xml_file, location=None, item_information=None):
        super(ResolverWindow, self).__init__(
            xml_file, location, item_information=item_information
        )
        self.return_data = None
        self.progress = 1
        self.resolver = None
        self.sources = None
        self.pack_select = False
        self.item_information = item_information

    def onInit(self, test=False):
        """
        Callback method from Kodi to trigger background threads to process resolving
        :param test: Used for Unit testing purposes only
        :type test: bool
        :return: None
        :rtype: None
        """
        super(ResolverWindow, self).onInit()
        threading.Thread(target=self._background_thread, args=(test,)).start()

    def _background_thread(self, test):
        if not test:
            stream_link = None
            release_title = None

            for source in self.sources:
                if self.canceled:
                    return
                self._update_window_properties(source)
                stream_link, release_title = self.resolver.resolve_single_source(
                    source, self.item_information, self.pack_select
                )
                if stream_link:
                    break
            self.return_data = stream_link, release_title
            self.close()

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

    def doModal(
        self,
        sources=None,
        pack_select=False,
        from_source_select=False,
    ):
        """
        Opens window in an intractable mode and runs background scripts
        :param sources: List of sources to attempt to resolve
        :type sources: list
        :param item_information: Metadata dict of item attempting to resolve for
        :type item_information: dict
        :param pack_select: Set to True to enable manual file selection
        :type pack_select: bool
        :param from_source_select: Set to True to set a window property with same name for skinning purposes
        :type pack_select: bool
        :return: Stream link
        :rtype: str
        """
        self.sources = sources if sources else []
        self.pack_select = pack_select

        if not self.sources:
            return None, None

        self.resolver = Resolver()
        self._update_window_properties(self.sources[0])
        self.setProperty(
            "from_source_select", "true" if from_source_select else "false"
        )

        super(ResolverWindow, self).doModal()

        if not self.canceled:
            return self.return_data
        else:
            return None, None
