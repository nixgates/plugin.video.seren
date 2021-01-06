# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import abc
import os
import time

import requests
import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.debrid.all_debrid import AllDebrid
from resources.lib.debrid.premiumize import Premiumize
from resources.lib.debrid.real_debrid import RealDebrid
from resources.lib.modules.exceptions import (
    TaskDoesNotExist,
    InvalidWebPath,
    GeneralIOError,
    SourceNotAvailable,
    FileAlreadyExists,
    InvalidSourceType,
    UnexpectedResponse
)
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g

CLOCK = time.time

STORAGE_LOCATION = g.DOWNLOAD_PATH
VALID_SOURCE_TYPES = ["torrent", "hoster", "cloud"]


class Manager:
    download_init_status = {
        "speed": "0 B/s",
        "progress": "0",
        "filename": "",
        "eta": "99h",
        "filesize": "0",
        "downloaded": "0",
    }

    def __init__(self):
        self.index = "SerenDownloadManagerIndex"
        self._win = g.HOME_WINDOW
        self.download_ids = []
        self.downloads = {}

    def remove_from_index(self, url_hash):
        """
        Removes requested task id from the global index
        :param url_hash:
        :return:
        """
        self.download_ids.remove(url_hash)
        self._win.setProperty("SDMIndex", ",".join(self.download_ids))

    def get_all_tasks_info(self):
        """
        Returns all currently active download task information
        :return: list
        """
        self._get_download_index()
        downloads = {}

        for url_hash in self.download_ids:
            downloads[url_hash] = self.get_task_info(url_hash)
        return downloads.values()

    def _get_download_index(self):
        """
        Refreshes download IDS from window index
        :return:
        """
        self.download_ids = [
            i for i in self._win.getProperty("SDMIndex").split(",") if i
        ]

    def _insert_into_index(self):
        """
        Inserts new ID into window index
        :return:
        """
        self._win.setProperty("SDMIndex", ",".join(self.download_ids))

    def update_task_info(self, url_hash, download_dict):
        """
        Updates download information stored in window property for download task
        :param url_hash: String
        :param download_dict: dict
        :return:
        """
        self._win.setProperty(
            "sdm.{}".format(url_hash), tools.construct_action_args(download_dict)
        )

    def get_task_info(self, url_hash):
        """
        Takes a task hash and returns the information stored in the Window property
        :param url_hash: Sting
        :return: dict
        """
        try:
            return tools.deconstruct_action_args(
                self._win.getProperty("sdm.{}".format(url_hash))
            )
        except Exception:
            raise TaskDoesNotExist(url_hash)

    def cancel_task(self, url_hash):
        """
        Sets status of download to canceled
        :param url_hash: string
        :return: None
        """
        g.log("Sending cancellation for task: {}".format(url_hash), "debug")
        self._get_download_index()
        info = self.get_task_info(url_hash)
        info["canceled"] = True
        self.update_task_info(url_hash, info)

    def create_download_task(self, url_hash):
        """
        Takes a download id and handles window property population
        :param url_hash: string
        :return: bool
        """
        with GlobalLock("SerenDownloaderUpdate"):
            self._get_download_index()
            if url_hash in self.download_ids:
                xbmcgui.Dialog().ok(
                    g.ADDON_NAME, "Can not create download task as it already exists!"
                )
                return False
            self.download_ids.append(url_hash)
            self._insert_into_index()
            self.download_init_status["hash"] = url_hash
            self.downloads[url_hash] = self.download_init_status
            self.update_task_info(url_hash, self.downloads[url_hash])
            return True

    def remove_download_task(self, url_hash):
        """
        Takes a download id a handles the clearing of download task from the window
        :param url_hash:
        :return: None
        """
        self._get_download_index()
        with GlobalLock("SerenDownloaderUpdate"):
            self._get_download_index()
            self._win.clearProperty("sdm.{}".format(url_hash))
            if url_hash in self.download_ids:
                self.remove_from_index(url_hash)

    def clear_complete(self):
        for download in self.get_all_tasks_info():
            if download["progress"] >= 100:
                self.remove_download_task(download["hash"])


class _DownloadTask:
    def __init__(self, filename=None):
        self.storage_location = g.DOWNLOAD_PATH

        if not xbmcvfs.exists(self.storage_location):
            xbmcvfs.mkdir(self.storage_location)

        self.manager = Manager()
        self.file_size = -1
        self.progress = -1
        self.speed = -1
        self.remaining_seconds = -1
        self._output_path = None
        self._canceled = False
        self._elapsed_time = 0
        self.bytes_consumed = 0
        self._output_file = None
        self.output_filename = filename
        self._start_time = CLOCK()
        self.status = "Starting"
        self.url_hash = ""

    def download(self, url, overwrite=False):
        """

        :param url: Web Path to file eg:(http://google.com/images/randomimage.jpeg)
        :param overwrite: opt. This will trigger a removal any conflicting files prior to download
        :return: Bool - True = Completed successfully / False = Cancelled
        """
        g.log("Downloading file: {}".format(url))
        if not url or not url.startswith("http"):
            raise InvalidWebPath(url)

        if self.output_filename is None:
            self.output_filename = url.split("/")[-1]
        g.log(
            "Filename: {} - Location: {}".format(
                self.output_filename, self.storage_location
            )
        )
        output_file = self._create_file(url, overwrite)
        self._output_file = output_file
        g.log("Created file - {}".format(self._output_path))
        head = requests.head(url)

        if head.status_code != 200:
            g.log("Server did not respond correctly to the head request")
            self._handle_failure()
            raise requests.exceptions.ConnectionError(head.status_code)

        self.url_hash = tools.md5_hash(url)
        if not self._add_download_to_dm():
            g.log("Failed to create download manager task", "error")
            self._handle_failure()
            return

        self.file_size = int(head.headers.get("content-length", None))
        self.progress = 0
        self.speed = 0
        self.status = "downloading"

        monitor = xbmc.Monitor()
        for chunk in requests.get(url, stream=True).iter_content(1024 * 1024):
            if monitor.abortRequested():
                self._handle_failure()
                g.log(
                    "Shutdown requested - Cancelling download: {}".format(
                        self.output_filename
                    ),
                    "warning",
                )
                self.cancel_download()
            if self._is_canceled():
                g.log(
                    "User cancellation - Cancelling download: {}".format(
                        self.output_filename
                    ),
                    "warning",
                )
                self.cancel_download()
                self.status = "canceled"
                return False
            result = output_file.write(chunk)
            if not result:
                self._handle_failure()
                self.status = "failed"
                g.log(
                    "Failed to fetch chunk from remote server -"
                    " Cancelling download: {}".format(self.output_filename),
                    "error",
                )
                raise GeneralIOError(self.output_filename)
            else:
                self._update_status(len(chunk))

        g.log(
            "Download has completed successfully - Filename: {}".format(
                self.output_filename
            )
        )
        return True

    def _add_download_to_dm(self):
        """
        :return: bool
        """
        return self.manager.create_download_task(self.url_hash)

    def _is_canceled(self):
        """
        :return: bool
        """
        return self.manager.get_task_info(self.url_hash).get("canceled", False)

    def _create_file(self, url, overwrite):

        """
        Confirms the paths and returns a file object
        :param url:
        :return: xbmcvfs.File Object
        """
        if not self.output_filename:
            self.output_filename = url.split("/")[-1]
            self.output_filename = tools.unquote(self.output_filename)
        self._output_path = os.path.join(self.storage_location, self.output_filename)
        output_path = os.path.join(self._output_path)
        output_path = tools.validate_path(output_path)

        if xbmcvfs.exists(output_path):
            if not overwrite:
                raise FileAlreadyExists(output_path)
            else:
                result = xbmcvfs.delete(output_path)
                if not result:
                    raise GeneralIOError(output_path)

        return xbmcvfs.File(output_path, "w")

    def _update_status(self, chunk_size):

        """
        :param chunk_size: int
        :return: None
        """

        self.bytes_consumed += chunk_size
        self.progress = int((float(self.bytes_consumed) / self.file_size) * 100)
        self.speed = self.bytes_consumed / (CLOCK() - self._start_time)
        self.remaining_seconds = (
            float(self.file_size - self.bytes_consumed) / self.speed
        )
        self.manager.update_task_info(
            self.url_hash,
            {
                "speed": self.get_display_speed(),
                "progress": self.progress,
                "filename": self.output_filename,
                "eta": self.get_remaining_time_display(),
                "filesize": self.file_size,
                "downloaded": self.bytes_consumed,
                "hash": self.url_hash,
            },
        )

    def get_display_speed(self):

        """
        Returns a display friendly version of the current speed
        :return: String
        """

        speed = self.speed
        speed_categories = ["B/s", "KB/s", "MB/s"]
        if self.progress >= 100:
            return "-"
        for i in speed_categories:
            if speed / 1024 < 1:
                return "{} {}".format(tools.safe_round(speed, 2), i)
            else:
                speed = speed / 1024

    def get_remaining_time_display(self):
        """
        Returns a display friendly version of the remaining time
        :return: String
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
        :return: None
        """

        self._canceled = True
        self._handle_failure()

    def _handle_failure(self):

        """
        Handle removal of any files in the event of a cancellation or error
        :return: None
        """
        self.manager.remove_download_task(self.url_hash)
        self._output_file.close()

        if xbmcvfs.exists(self._output_path):
            result = xbmcvfs.delete(self._output_path)
            if not result:
                raise GeneralIOError(
                    "Failed to delete file: {}".format(self._output_path)
                )


class _DebridDownloadBase(object):
    def __init__(self, source):
        self.thread_pool = ThreadPool()
        self.source = source
        self.average_speed = "0 B/s"
        self.progress = 0
        self.downloaders = []
        self.debrid_module = None
        self._confirm_source_downloadable()

    def _confirm_source_downloadable(self):
        if not self.source.get("type") in VALID_SOURCE_TYPES:
            raise InvalidSourceType(self.source.get("type"))

    @abc.abstractmethod
    def _fetch_available_files(self):
        """
        Fetches available files in source and returns a list of (path, filename) tuples
        :return: List
        """

    @abc.abstractmethod
    def _resolve_file_url(self, file):
        """
        :param file: Dict
        :return: String
        """

    def _get_selected_files(self):
        """
        :return:
        """
        if self.source.get("type") in ["hoster", "cloud"]:
            return self.source
        available_files = self._fetch_available_files()
        available_files = [
            (i, i["path"].split("/")[-1])
            for i in available_files
            if source_utils.is_file_ext_valid(i["path"])
        ]
        available_files = sorted(available_files, key=lambda k: k[1])
        file_titles = [i[1] for i in available_files]

        selection = xbmcgui.Dialog().multiselect(
            g.get_language_string(30509), file_titles
        )
        selection = [available_files[i] for i in selection]
        return selection

    def _initiate_download(self, url, output_filename=None):
        """
        Creates Downloader Class and adds it to current download thread pool
        :param url: String
        :param output_filename: String
        :return: None
        """
        downloader = _DownloadTask(output_filename)
        self.downloaders.append(downloader)
        self.thread_pool.put(downloader.download, url, True)

    def _resolver_setup(self, selected_files):
        """

        :param selected_files:
        :return:
        """
        return selected_files

    @abc.abstractmethod
    def _get_single_item_info(self, source):
        """

        :param source:
        :return:
        """

    def _handle_potential_multi(self):
        """
        Requests selection of files from user and begins download tasks
        :return:  None
        """
        selected_files = self._get_selected_files()
        selected_files = self._resolver_setup(selected_files)
        for i in selected_files:
            self._initiate_download(self._resolve_file_url(i), i[1])

    def download(self):
        """
        Begins required download type for provided source
        :return:
        """
        if self.source["type"] not in ["hoster", "cloud"]:
            self._handle_potential_multi()
        else:
            source_info = self._get_single_item_info(self.source)
            self._initiate_download(
                self._resolve_file_url([source_info]), self.source["release_title"]
            )


class _PremiumizeDownloader(_DebridDownloadBase):
    def __init__(self, source):
        super(_PremiumizeDownloader, self).__init__(source)
        self.debrid_module = Premiumize()
        self.available_files = []

    def _fetch_available_files(self):
        if self.source["type"] in ["hoster", "cloud"]:
            return self.source
        self.available_files = self.debrid_module.direct_download(
            self.source["magnet"]
        )["content"]
        return self.available_files

    def _get_single_item_info(self, source):
        return self.debrid_module.item_details(source["url"])

    def _resolve_file_url(self, file):
        return file[0]["link"]


class _RealDebridDownloader(_DebridDownloadBase):
    def __init__(self, source):
        super(_RealDebridDownloader, self).__init__(source)
        self.debrid_module = RealDebrid()
        self.available_files = []

    def _fetch_available_files(self):
        availability = self.debrid_module.check_hash(self.source["hash"])
        availability = [
            i
            for i in availability[self.source["hash"]]["rd"]
            if self.debrid_module.is_streamable_storage_type(i)
        ]
        try:
            availability = sorted(availability, key=lambda k: len(k.values()))[0]
        except IndexError:
            raise SourceNotAvailable

        self.available_files = [
            {"path": value["filename"], "index": key}
            for key, value in availability.items()
        ]
        return self.available_files

    def _resolve_file_url(self, file):
        return self.debrid_module.resolve_hoster(file[0]["url"])

    def _resolver_setup(self, selected_files):
        if self.source.get("type") in ["hoster", "cloud"]:
            return [(self.source.get("url", ""), self.source.get("release_tile"))]

        torrent_id = self.debrid_module.add_magnet(self.source["magnet"])["id"]
        self.debrid_module.torrent_select(
            torrent_id, ",".join([i["index"] for i in self.available_files])
        )
        info = self.debrid_module.torrent_info(torrent_id)
        remote_files = {str(i["id"]): idx for idx, i in enumerate(info["files"])}
        selected_files = [(remote_files[i[0]["index"]], i[1]) for i in selected_files]
        selected_files = [(info["links"][i[0]], i[1]) for i in selected_files]
        return selected_files

    def _get_single_item_info(self, source):
        return source


class _AllDebridDownloader(_DebridDownloadBase):
    def __init__(self, source):
        super(_AllDebridDownloader, self).__init__(source)
        self.debrid_module = AllDebrid()
        self.available_files = []

    def _fetch_available_files(self):
        self.magnet_id = self.debrid_module.upload_magnet(self.source['hash'])["magnets"][0]["id"]
        status = self.debrid_module.magnet_status(self.magnet_id)['magnets']
        if status["status"] != "Ready":
            raise UnexpectedResponse(status)
        return [{'path': i['filename'], 'url': i['link']} for i in status['links']]

    def _get_single_item_info(self, source):
        return source

    def _resolve_file_url(self, file):
        return self.debrid_module.resolve_hoster(file[0]["url"])


def _get_debrid_downloader_class(source):
    """
    Takes source and returns the relevant debrid class for source
    :param source: dict
    :return: object
    """
    debrid_providers = {
        "premiumize": _PremiumizeDownloader,
        "real_debrid": _RealDebridDownloader,
        "all_debrid": _AllDebridDownloader,
    }
    return debrid_providers[source["debrid_provider"]](source)


def create_task(source):
    """
    Takes source and auto fires of download process
    :param source: dict
    :return: None
    """
    if not source.get("type") in VALID_SOURCE_TYPES:
        raise InvalidSourceType(source.get("type"))
    debrid_class = _get_debrid_downloader_class(source)
    debrid_class.download()


def set_download_location():
    """
    Requests new file location from user and stores in settings
    :return: None
    """

    new_location = xbmcgui.Dialog().browse(
        0, g.get_language_string(30480), "video", defaultt=STORAGE_LOCATION
    )
    g.set_setting("download.location", new_location)
