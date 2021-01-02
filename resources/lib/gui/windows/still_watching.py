# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g


class StillWatching(BaseWindow):
    """
    Dialog to confirm user is stil watching the player
    """
    def __init__(self, xml_file, xml_location, item_information=None):
        try:
            self.player = xbmc.Player()
            self.playing_file = self.player.getPlayingFile()
            self.closed = False
            self.duration = self.player.getTotalTime() - self.player.getTime()
            super(StillWatching, self).__init__(
                xml_file, xml_location, item_information=item_information
            )
        except:
            g.log_stacktrace()

    def onInit(self):
        """
        Runs when window is displayed
        :return: None
        :rtype: none
        """
        self.background_tasks()

    def calculate_percent(self):
        """
        Calculates percent of playing item is watched
        :return: Percentage played
        :rtype: int
        """
        return (
            (int(self.player.getTotalTime()) - int(self.player.getTime()))
            / float(self.duration)
        ) * 100

    def background_tasks(self):
        """
        Runs background watcher tasks
        :return: None
        :rtype: none
        """
        try:
            try:
                progress_bar = self.getControlProgress(3014)
            except:
                progress_bar = None

            while (
                (int(self.player.getTotalTime()) - int(self.player.getTime())) > 1
                and not self.closed
                and self.playing_file == self.player.getPlayingFile()
                and not g.abort_requested()
            ):
                xbmc.sleep(500)
                if progress_bar is not None:
                    progress_bar.setPercent(self.calculate_percent())

            if not self.closed:
                self.player.pause()
        except:
            g.log_stacktrace()

        self.close()

    def doModal(self):
        """
        Call to display window in an interactive fashion
        :return: None
        :rtype: none
        """
        try:
            super(StillWatching, self).doModal()
        except:
            g.log_stacktrace()

    def close(self):
        """
         Call to close window
         :return: None
         :rtype: none
         """
        self.closed = True
        super(StillWatching, self).close()

    def onClick(self, control_id):
        """
        Callback from kodi when a click event occurs in dialog
        :param control_id: control the click was perfomed on
        :type control_id: int
        :return: None
        :rtype: none
        """
        self.handle_action(7, control_id)

    def handle_action(self, action, control_id=None):
        """
        Handles click or keyboard actions
        :param action: Action Id of event
        :type action: int
        :param control_id: Control event processed on if available
        :type control_id: int
        :return: None
        :rtype: none
        """
        if control_id is None:
            control_id = self.getFocusId()

        if action != 7:
            return

        if control_id == 3001:
            self.player.playnext()
            self.close()
        if control_id == 3002:
            self.close()
        if control_id == 3003:
            self.player.stop()
            self.close()
