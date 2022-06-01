# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.gui.windows.smartplay_window import SmartPlayWindow
from resources.lib.modules.globals import g


class PlayingNext(SmartPlayWindow):
    """
    Dialog to provide quick skipping to next playlist item if available.
    """

    def __init__(self, xml_file, xml_location, item_information=None):
        super(PlayingNext, self).__init__(
            xml_file, xml_location, item_information=item_information
        )
        self.default_action = g.get_int_setting("playingnext.defaultaction")

    def smart_play_action(self):
        if (
            self.default_action == 1
            and self.playing_file == self.getPlayingFile()
            and not self.closed
        ):
            self.pause()
