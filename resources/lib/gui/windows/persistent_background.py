# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.gui.windows.base_window import BaseWindow


class PersistentBackground(BaseWindow):

    def __init__(self, xml_file, location, item_information=None):
        super(PersistentBackground, self).__init__(xml_file, location, item_information=item_information)

    def onInit(self):
        super(PersistentBackground, self).onInit()

    def set_text(self, text):
        self.setProperty('notification_text', text)

    def onAction(self, action):
        super(PersistentBackground, self).onAction(action)
