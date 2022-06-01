# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.gui.windows.smartplay_window import SmartPlayWindow


class StillWatching(SmartPlayWindow):
    """
    Dialog to confirm user is stil watching the player
    """

    def __init__(self, xml_file, xml_location, item_information=None):
        super(StillWatching, self).__init__(
            xml_file, xml_location, item_information=item_information
        )

    def smart_play_action(self):
        if not self.closed:
            self.player.pause()
