import xbmcgui

from resources.lib.gui.windows.base_window import BaseWindow


class SingleItemWindow(BaseWindow):
    def __init__(self, xml_file, location, item_information=None):
        super().__init__(xml_file, location, item_information)

    def onInit(self):
        if self.item_information:
            persistent_list = xbmcgui.ControlList(-100, -100, 0, 0)
            self.addControl(persistent_list)
            persistent_list.addItem(self.get_list_item_with_properties(self.item_information))
            self.setFocusId(persistent_list.getId())

        super().onInit()

    def handle_action(self, action_id, control_id=None):
        pass
