import threading

from resources.lib.common import tools
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g
from resources.lib.modules.resolver import Resolver


class ResolverWindow(BaseWindow):
    """
    Window for Resolver
    """

    def __init__(self, xml_file, location=None, item_information=None):
        super(ResolverWindow, self).__init__(xml_file, location, item_information=item_information)
        self.return_data = None
        self.canceled = False
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

            for source in self.sources:
                if self.canceled:
                    return
                self._update_window_properties(source)
                stream_link = self.resolver.resolve_single_source(source, self.item_information, self.pack_select)
                if stream_link:
                    break

            self.return_data = stream_link
            self.close()

    def _update_window_properties(self, source):
        debrid_provider = source.get("debrid_provider", "None").replace("_", " ")
        if "size" in source and source["size"] != "Variable":
            self.setProperty("source_size", tools.source_size_display(source["size"]))

        self.setProperty("release_title", g.display_string(source["release_title"]))
        self.setProperty("debrid_provider", debrid_provider)
        self.setProperty("source_provider", source["provider"])
        self.setProperty("source_resolution", source["quality"])
        self.setProperty("source_info", " ".join(source["info"]))
        self.setProperty("source_type", source["type"])

    def doModal(self, sources=None, item_information=None, pack_select=False):
        """
        Opens window in an intractable mode and runs background scripts
        :param sources: List of sources to attempt to resolve
        :type sources: list
        :param item_information: Metadata dict of item attempting to resolve for
        :type item_information: dict
        :param pack_select: Set to True to enable manual file selection
        :type pack_select: bool
        :return: Stream link
        :rtype: str
        """
        self.sources = sources if sources else []
        self.item_information = item_information if item_information else {}
        self.pack_select = pack_select
        self.resolver = Resolver()
        self._update_window_properties(sources[0])

        super(ResolverWindow, self).doModal()

        if not self.canceled:
            return self.return_data
        else:
            return None

    def onAction(self, action):
        """
        Callback method from Kodi when an action is performed within dialog
        :param action: Action Object
        :type action: action
        :return: None
        :rtype: None
        """
        action = action.getId()
        if action == 92 or action == 10:
            self.canceled = True
            self.close()

    def close(self):
        """
        Closes this window
        :return: None
        :rtype: None
        """
        super(ResolverWindow, self).close()
