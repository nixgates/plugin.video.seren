# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmcgui

from resources.lib.gui.windows.base_window import BaseWindow

ACTION_PREVIOUS_MENU = 10
ACTION_PLAYER_STOP = 13
ACTION_NAV_BACK = 92


class SingleItemWindow(BaseWindow):
    def __init__(self, xml_file, location, item_information=None):
        super(SingleItemWindow, self).__init__(xml_file, location, item_information)

    def onInit(self):
        if self.item_information:
            persistent_list = xbmcgui.ControlList(-100, -100, 0, 0)
            self.addControl(persistent_list)
            persistent_list.addItem(
                self.get_list_item_with_properties(self.item_information)
            )
            self.setFocusId(persistent_list.getId())

        super(SingleItemWindow, self).onInit()
