import abc

import xbmcgui

from . import set_info_properties
from resources.lib.common import tools
from resources.lib.gui.windows.base_window import BaseWindow


class SourceWindow(BaseWindow):
    """
    Common window class for source selection type windows.
    """

    def __init__(self, xml_file, location, item_information=None, sources=None):
        super().__init__(xml_file, location, item_information=item_information)
        self.sources = sources or []
        self.item_information = item_information
        self.display_list = None

    def onInit(self):
        self.display_list = self.getControlList(1000)
        self.populate_sources_list()

        self.set_default_focus(self.display_list, 2999, control_list_reset=True)
        super().onInit()

    def populate_sources_list(self):
        self.display_list.reset()

        for i in self.sources:
            menu_item = xbmcgui.ListItem(label=f"{i['release_title']}")
            provider_imports = i.get("provider_imports", [])
            source_icon = self.provider_class.get_icon(provider_imports)
            if source_icon is not None:
                menu_item.setProperty("source.icon", source_icon)

            for info in i:
                try:
                    if info == "info":
                        continue
                    value = i[info]
                    if info == "size":
                        value = tools.source_size_display(value)
                    menu_item.setProperty(info, str(value).replace("_", " "))
                except UnicodeEncodeError:
                    menu_item.setProperty(info, i[info])

            set_info_properties(i.get("info", {}), menu_item)
            self.display_list.addItem(menu_item)

    @abc.abstractmethod
    def handle_action(self, action_id, control_id=None):
        pass
