# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.gui.windows.single_item_window import SingleItemWindow


class PersistentBackground(SingleItemWindow):
    def __init__(self, xml_file, location, item_information=None):
        super(PersistentBackground, self).__init__(
            xml_file, location, item_information=item_information
        )

    def set_text(self, text):
        self.setProperty("notification_text", text)

    def set_process_started(self):
        self.setProperty("process_started", "true")

    def show(self):
        self.setProperty('process_started', 'false')
        super(PersistentBackground, self).show()
