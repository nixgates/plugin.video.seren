# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g


class PlayingNext(BaseWindow):
    """
    Dialog to provide quick skipping to next playlist item if available.
    """
    def __init__(self, xml_file, xml_location, item_information=None):

        try:
            super(PlayingNext, self).__init__(
                xml_file, xml_location, item_information=item_information
            )
            self.playing_file = self.getPlayingFile()
            self.duration = self.getTotalTime() - self.getTime()
            self.closed = False
            self.default_action = g.get_int_setting("playingnext.defaultaction")
        except:
            g.log_stacktrace()

    # region player methods
    def getTotalTime(self):
        """
        Fetches total time of current playing item
        :return: Total time in seconds
        :rtype: float
        """
        if self.isPlaying():
            return xbmc.Player().getTotalTime()
        else:
            return 0

    def getTime(self):
        """
        Get curent position of playing item
        :return: Current position in seconds
        :rtype: float
        """
        if self.isPlaying():
            return xbmc.Player().getTime()
        else:
            return 0

    def isPlaying(self):
        """
        Checks if an item is currently playing
        :return: True if player is currently playing something
        :rtype: bool
        """
        return xbmc.Player().isPlaying()

    def getPlayingFile(self):
        """
        Returns path to playing item
        :return: path to playing item
        :rtype: str
        """
        return xbmc.Player().getPlayingFile()

    def seekTime(self, seekTime):
        """
        Seeks player to provided point in time
        :param seekTime: Time to seek to in fractional seconds
        :type seekTime: float
        :return: none
        :rtype: none
        """
        xbmc.Player().seekTime(seekTime)

    def pause(self):
        """
        Pauses currently playing item
        :return: None
        :rtype: none
        """
        xbmc.Player().pause()

    # endregion

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
            (int(self.getTotalTime()) - int(self.getTime())) / float(self.duration)
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
                int(self.getTotalTime()) - int(self.getTime()) > 2
                and not self.closed
                and self.playing_file == self.getPlayingFile()
                and not g.abort_requested()
            ):
                xbmc.sleep(500)
                if progress_bar is not None:
                    progress_bar.setPercent(self.calculate_percent())

            if (
                self.default_action == 1
                and self.playing_file == self.getPlayingFile()
                and not self.closed
            ):
                self.pause()
        except:
            import traceback

            g.log_stacktrace()

        self.close()

    def doModal(self):
        """
        Call to display window in an interactive fashion
        :return: None
        :rtype: none
        """
        try:
            super(PlayingNext, self).doModal()
        except:
            g.log_stacktrace()

    def close(self):
        """
        Call to close window
        :return: None
        :rtype: none
        """
        self.closed = True
        super(PlayingNext, self).close()

    def onClick(self, control_id):
        """
        Callback from kodi when a click event occurs in dialog
        :param control_id: control the click was perfomed on
        :type control_id: int
        :return: None
        :rtype: none
        """
        g.log("Click - {}".format(control_id))
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
        g.log("Action Handle - {}".format(action))
        if action != 7:
            return
        if control_id is None:
            control_id = self.getFocusId()
        if control_id == 3001:
            self.seekTime(self.getTotalTime())
            self.close()
        if control_id == 3002:
            self.close()
