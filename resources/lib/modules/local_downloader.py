# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import time

import requests
import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.exceptions import (
    FileAlreadyExists,
    InvalidWebPath,
    GeneralIOError,
)
from resources.lib.modules.globals import g


class Downloader:
    def __init__(self, filename=None):
        self.storage_location = g.DOWNLOAD_PATH

        self._confirm_default_download_folder_exists()

        self.file_size = -1
        self.progress = -1
        self.speed = -1
        self.remaining_seconds = -1

        self._output_path = None
        self._canceled = False
        self._elapsed_time = 0
        self._bytes_consumed = 0
        self._output_file = None
        self._output_filename = filename
        self._start_time = time.time()

    def _confirm_default_download_folder_exists(self):
        if not xbmcvfs.exists(self.storage_location):
            xbmcvfs.mkdir(self.storage_location)

    def download(self, url, overwrite=False):

        """

        :param url: Web Path to file eg:(http://google.com/images/randomimage.jpeg)
        :param overwrite: opt. This will trigger a removal any conflicting files prior to download
        :return: Bool - True = Completed successfully / False = Cancelled
        """

        if not url or not url.startswith("http"):
            raise InvalidWebPath(url)

        output_file = self._create_file(url, overwrite)
        head = requests.head(url)

        if head.status_code != 200:
            raise requests.exceptions.ConnectionError

        self.file_size = int(head.headers.get("content-length", None))
        self.progress = 0
        self.speed = 0

        monitor = xbmc.Monitor()
        for chunk in requests.get(url, stream=True).iter_content(1024 * 1024):
            if monitor.abortRequested():
                self.cancel_download()
            if self._canceled:
                return False
            result = output_file.write(chunk)
            if not result:
                self._handle_failure()
                raise GeneralIOError(self._output_filename)
            else:
                self._update_status(len(chunk))

        return True

    def _create_file(self, url, overwrite):

        """
        Confirms the paths and returns a file object
        :param url:
        :return: xbmcvfs.File Object
        """
        if not self._output_filename:
            self._output_filename = url.split("/")[-1]
            self._output_filename = tools.unquote(self._output_filename)

        output_path = os.path.join(self.storage_location, self._output_filename)
        output_path = tools.validate_path(output_path)

        if xbmcvfs.exists(output_path):
            if not overwrite:
                raise FileAlreadyExists
            else:
                result = xbmcvfs.delete(output_path)
                if not result:
                    raise GeneralIOError(self._output_filename)

        return xbmcvfs.File(output_path, "w")

    def _update_status(self, chunk_size):

        """
        Updates feedback information
        :return:
        """

        self._bytes_consumed += chunk_size
        self.progress = int((float(self._bytes_consumed) / self.file_size) * 100)
        self.speed = self._bytes_consumed / (time.time() - self._start_time)
        self.remaining_seconds = (
            float(self.file_size - self._bytes_consumed) / self.speed
        )
        g.log(
            "Speed: {} | Remaining Time: {} | Progress: {}".format(
                self.get_display_speed(),
                self.get_remainging_time_display(),
                self.progress,
            )
        )

    def get_display_speed(self):

        """
        Returns a display friendly version of the current speed
        :return: String eg: (125.54 KB/s)
        """

        speed = self.speed
        speed_categories = ["B/s", "KB/s", "MB/s"]
        for i in speed_categories:
            if speed / 1024 < 1:
                return "{} {}".format(tools.safe_round(speed, 2), i)
            else:
                speed = speed / 1024

    def get_remainging_time_display(self):
        """
        Returns a display friendly version of the remaining time
        :return: String eg: (45.5s)
        """

        seconds = self.remaining_seconds
        categories = ["s", "m", "h"]
        for i in categories:
            if seconds / 60 < 1:
                return "{}{}".format(tools.safe_round(seconds, 1), i)
            else:
                seconds = seconds / 60

    def cancel_download(self):
        """
        Stops download stream and runs cleanup
        :return:
        """

        self._canceled = True
        self._handle_failure()

    def _handle_failure(self):

        """
        Handle removal of any files in the event of a cancellation or error
        :return:
        """

        if not self._output_file:
            return
        else:
            if not self._output_path:
                return
            else:
                if xbmcvfs.exists(self._output_path):
                    result = xbmcvfs.delete(self._output_path)
                    if not result:
                        raise GeneralIOError(self._output_path)
            self._output_file.close()


def set_download_location():
    """
    Sets the relevant download location to settings
    :return:
    """

    storage_location = g.DOWNLOAD_PATH
    new_location = xbmcgui.Dialog().browse(
        0, g.get_language_string(30480), "video", defaultt=storage_location
    )
    g.set_setting("download.location", new_location)
