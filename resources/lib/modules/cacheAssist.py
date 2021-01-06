# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import re
import time

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database.torrentAssist import TorrentAssist
from resources.lib.debrid import all_debrid
from resources.lib.debrid import premiumize
from resources.lib.debrid import real_debrid
from resources.lib.modules.exceptions import (
    GeneralCachingFailure,
    DebridNotEnabled,
    FailureAtRemoteParty,
    )
from resources.lib.modules.exceptions import KodiShutdownException
from resources.lib.modules.globals import g


class _BaseCacheAssist(TorrentAssist):
    def __init__(self, uncached_source, silent=False):
        super(_BaseCacheAssist, self).__init__()
        self.debrid_slug = None
        self.debrid_readable = None
        self.transfer_id = None
        self.transfer_info = None
        self.uncached_source = uncached_source
        self.current_percent = -1
        self.previous_percent = -1
        self.status = "starting"
        self.last_progression_timestamp = time.time()
        self.download_speed = 0
        self.seeds = 0
        self.silent = silent
        self.cancelled = False
        self.thread_pool = ThreadPool()
        self.progress_message = "Status: {} | Progress: {} | Speed: {} | Peers: {}"

    def _update_database(self):
        self.add_assist_torrent(
            self.debrid_slug,
            self.debrid_readable,
            self.status,
            self.uncached_source["release_title"],
            str(self.current_percent),
            )

    def run_single_status_cycle(self):
        self._update_status()
        self._update_database()

    def _update_status(self):
        """
        Polls debrid and updates class variables
        :return: None
        """

    def _delete_transfer(self):
        """
        Clears transfer from debrid provider
        :return: None
        """

    def _is_expired(self):
        """
        Confirms that progression hasn't stalled for over 3 hours

        :return: BOOL
        """
        if (
                self.current_percent == self.previous_percent
                and (self.last_progression_timestamp + 10800) < time.time()
        ):
            return True
        else:
            return False

    def cancel_process(self):
        self._handle_failure("User has cancelled process")
        self.cancelled = True

    @staticmethod
    def prompt_download_style():
        return xbmcgui.Dialog().yesno(
            g.ADDON_NAME,
            g.get_language_string(30492),
            yeslabel=g.get_language_string(30493),
            nolabel=g.get_language_string(30491),
            )

    def _get_progress_string(self):
        return self.progress_message.format(
            g.color_string(self.status.title()),
            g.color_string(self.current_percent),
            g.color_string(self.get_display_speed()),
            g.color_string(self.seeds),
            )

    def do_cache(self):

        yesno = self.prompt_download_style()

        if yesno:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30504))
            self.thread_pool.put(self.status_update_loop)
            return {"result": "background", "source": None}
        else:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(
                g.get_language_string(30335),
                tools.create_multiline_message(
                    line1="Title: {}".format(
                        g.color_string(self.uncached_source["release_title"].upper())
                        ),
                    line2=self._get_progress_string(),
                    ),
                )

            monitor = xbmc.Monitor()
            while not progress_dialog.iscanceled() and not monitor.abortRequested():
                xbmc.sleep(5000)
                self.run_single_status_cycle()
                progress_dialog.update(
                    int(self.current_percent), self._get_progress_string()
                    )
                if self.current_percent == 100:
                    progress_dialog.close()
                    break

            if progress_dialog.iscanceled() and self.current_percent != 100:

                self._handle_cancellation()
                self.cancel_process()
                return {"result": "error", "source": None}
            else:
                self.uncached_source["debrid_provider"] = self.debrid_slug
                return {"result": "success", "source": self.uncached_source}

    @staticmethod
    def _handle_cancellation():
        return xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30504))

    def status_update_loop(self):
        monitor = xbmc.Monitor()
        while not monitor.abortRequested() and not self.cancelled:
            if monitor.waitForAbort(10):
                raise KodiShutdownException(
                    "Kodi Shutdown requested, cancelling download"
                    )
            try:
                self._update_status()
                g.log(
                    self.progress_message.format(
                        self.status,
                        self.current_percent,
                        self.get_display_speed(),
                        self.seeds,
                        )
                    )
                if self.status == "finished":
                    self._notify_user_of_completion()
                    self._update_database()
                    break

                if self.status == "downloading":
                    self._do_download_frame()
                else:
                    self._handle_failure("Unkonown Failure at Debrid Provider")

            except KodiShutdownException:
                self._delete_transfer()
                break

            except Exception as e:
                self._delete_transfer()
                raise e

    def _notify_user_of_completion(self):
        if not self.silent:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME + ": %s" % self.uncached_source["release_title"],
                g.get_language_string(30484)
                + " %s" % self.uncached_source["release_title"],
                time=5000,
                )

    def _do_download_frame(self):
        if self._is_expired():
            self._handle_failure("Lack of progress")
        else:
            self._update_database()

    def _handle_failure(self, reason):
        if not self.silent:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME,
                g.get_language_string(30485) % self.uncached_source["release_title"],
                time=5000,
                )
        self.status = "failed"
        self._update_database()
        self._delete_transfer()
        raise GeneralCachingFailure(
            "Could not create cache for magnet - {} \n Reason: {}"
            "".format(self.uncached_source["release_title"], reason)
            )

    def get_display_speed(self):

        """
        Returns a display friendly version of the current speed
        :return: String eg: (125.54 KB/s)
        """

        speed = self.download_speed
        speed_categories = ["B/s", "KB/s", "MB/s"]
        for i in speed_categories:
            if speed / 1024 < 1:
                return "{} {}".format(tools.safe_round(speed, 2), i)
            else:
                speed = speed / 1024


class _PremiumizeCacheAssist(_BaseCacheAssist):
    def __init__(self, uncached_source, silent=False):
        if not g.premiumize_enabled():
            raise DebridNotEnabled

        super(_PremiumizeCacheAssist, self).__init__(uncached_source, silent)
        self.debrid_slug = "premiumize"
        self.debrid_readable = "Premiumize"
        self.debrid = premiumize.Premiumize()

        self.transfer_info = self.debrid.create_transfer(uncached_source["magnet"])
        self.transfer_id = self.transfer_info["id"]
        self._update_status()

        self.transfer_id = self.transfer_info["id"]

    def _update_status(self):
        transfer_status = [
            i
            for i in self.debrid.list_transfers()["transfers"]
            if i["id"] == self.transfer_id
            ][0]
        if transfer_status["status"] == "running":
            transfer_status["status"] = "downloading"

        self.previous_percent = self.current_percent
        self.current_percent = tools.safe_round(transfer_status["progress"] * 100, 2)
        message = re.findall(
            r"(\d*.\d* .{1,2}\/s) from (\d*)", transfer_status["message"]
            )

        try:
            self.download_speed = message[0][0]
            self.seeds = message[0][1]
        except IndexError:
            self.download_speed = "0.00 B/s"
            self.seeds = "0"

        self.status = transfer_status["status"]

    def _delete_transfer(self):
        self.debrid.delete_transfer(self.transfer_id)

    def get_display_speed(self):
        return self.download_speed


class _RealDebridCacheAssist(_BaseCacheAssist):
    def __init__(self, uncached_source, silent=False):
        if not g.real_debrid_enabled():
            raise DebridNotEnabled

        super(_RealDebridCacheAssist, self).__init__(uncached_source, silent)
        self.debrid_slug = "real_debrid"
        self.debrid_readable = "Real Debrid"
        self.debrid = real_debrid.RealDebrid()
        self.transfer_info = self.debrid.add_magnet(uncached_source["magnet"])
        self.transfer_id = self.transfer_info["id"]
        self.transfer_info = self.debrid.torrent_info(self.transfer_id)
        g.log("Starting transfer {}".format(self.transfer_id))
        self.file_keys = []

        for file in self.transfer_info["files"]:
            filename = file["path"]
            key = file["id"]
            if any(
                    filename.lower().endswith(extension)
                    for extension in g.common_video_extensions
                    ):
                self.file_keys.append(str(key))
        if len(self.file_keys) == 1:
            self.file_keys = str(self.file_keys[0])
        self._select_files()
        self._update_status()

    def _select_files(self):
        if not self.file_keys:
            raise GeneralCachingFailure(
                "Unable to select any relevent files for torrent"
                )
        g.log(
            "Selecting files: {} - Transfer ID: {}".format(
                self.file_keys, self.transfer_id
                )
            )
        response = self.debrid.torrent_select(
            self.transfer_id, ",".join(self.file_keys)
            )
        if "error" in response:
            raise FailureAtRemoteParty(
                "Unable to select torrent files - {}".format(response)
                )

    def _update_status(self):

        status = self.debrid.torrent_info(self.transfer_info["id"])
        downloading_status = [
            "queued",
            "downloading",
            "compressing",
            "magnet_conversion",
            "waiting_files_selection",
            ]
        if "error" in status or status.get("status", "") in ["", "magnet_error"]:
            g.log(
                "Failure to create cache: {} - {}".format(self.debrid_readable, status)
                )
            raise FailureAtRemoteParty(status["error"])
        if status["status"] == "waiting_files_selection":
            self._select_files()
        if status["status"] in downloading_status:
            self.status = "downloading"
        elif status["status"] == "downloaded":
            self.status = "finished"
        else:
            g.log("invalid status: {}".format(status["status"]))
            self.status = "failed"

        self.seeds = status.get("seeders", 0)
        self.download_speed = status.get("speed", 0)

        self.previous_percent = self.current_percent
        self.current_percent = tools.safe_round(status["progress"], 2)

    def delete_transfer(self):
        self.debrid.delete_torrent(self.transfer_id)


class _AllDebridCacheAssist(_BaseCacheAssist):
    def __init__(self, uncached_source, silent=False):
        if not g.all_debrid_enabled():
            raise DebridNotEnabled
        super(_AllDebridCacheAssist, self).__init__(uncached_source, silent)
        self.debrid_slug = "all_debrid"
        self.debrid_readable = "All Debrid"
        self.debrid = all_debrid.AllDebrid()

        self.uncached_source = uncached_source
        self.transfer_info = self.debrid.upload_magnet(uncached_source["magnet"])[
            "magnets"
        ][0]
        self.transfer_id = self.transfer_info["id"]
        self.transfer_info = self.debrid.magnet_status(self.transfer_id)["magnets"]
        self._update_status()

    def _update_status(self):

        status = self.debrid.magnet_status(self.transfer_id)["magnets"]

        if status["status"] == "Downloading":
            self.status = "downloading"
        elif status["status"] == "Ready":
            self.status = "finished"
        else:
            self.status = "failed"

        self.previous_percent = self.current_percent
        self.seeds = status["seeders"]
        self.download_speed = status["downloadSpeed"]

        total_size = status["size"]
        downloaded = status["downloaded"]

        if downloaded > 0:
            self.current_percent = tools.safe_round(
                (float(downloaded) / total_size) * 100, 2
                )

    def delete_transfer(self):
        self.debrid.delete_magnet(self.transfer_id)


class CacheAssistHelper:
    def __init__(self):
        self.locations = [
            ("Premiumize", _PremiumizeCacheAssist, "premiumize", g.premiumize_enabled()),
            ("Real Debrid", _RealDebridCacheAssist, "real_debrid", g.real_debrid_enabled()),
            ("AllDebrid", _AllDebridCacheAssist, "all_debrid", g.all_debrid_enabled()),
            ]

    def _get_cache_location(self):
        debrid_class = self.locations[g.get_int_setting("general.cachelocation")]
        if not debrid_class[3]:
            enabled_locations = [i for i in self.locations if i[3]]
            if enabled_locations:
                return enabled_locations[0]
            else:
                return None
        else:
            return debrid_class

    def manual_cache(self, uncached_source, preferred_debrid_slug=None, silent=True):
        """
            This is a ease of use method that will return the initialised debrid class with a transfer started
            This method will not start the status loop, you must start and monitor the class separately

        :param uncached_source: DICTIONARY
        :param preferred_debrid_slug: STRING
        :param silent: BOOL
        :return: Debrid Provider Cache Class
        """

        debrid_class = None

        if preferred_debrid_slug is not None:
            debrid_class = [i for i in self.locations if i[2] == preferred_debrid_slug and i[3]][0]

        if not debrid_class:
            debrid_class = self._get_cache_location()

        if not debrid_class:
            xbmcgui.Dialog().ok("Seren", g.get_language_string(30208))
            return

        return debrid_class[1](uncached_source, silent)

    def auto_cache(self, torrent_list):
        """
        NOTE: This entry is locking
        :param torrent_list: LIST
        :return: None
        """
        if not torrent_list:
            return
        debrid_class = self.locations[g.get_int_setting("general.cachelocation")][1]

        if len(torrent_list) == 0:
            selected_source = torrent_list[0]
        else:
            selected_source = _approx_best_source(torrent_list)

        try:
            debrid_class = debrid_class(selected_source)
            debrid_class.status_update_loop()
        except DebridNotEnabled:
            tools.log(
                "Failed to start cache assist as selected debrid provider is not enabled or setup correctly",
                "error",
                )
            return

        xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30483))


def _approx_best_source(source_list):
    quality_list = ["1080p", "720p", "SD"]
    source_list = [i for i in source_list if i]

    for quality in quality_list:
        quality_filter = [i for i in source_list if i["quality"] == quality]
        if len(quality_filter) > 0:
            packtype_filter = [
                i
                for i in quality_filter
                if i["package"] == "show" or i["package"] == "season"
                ]
            sorted_list = sorted(
                packtype_filter, key=lambda k: k["seeds"], reverse=True
                )
            if len(sorted_list) > 0:
                return sorted_list[0]
            else:
                package_type_list = [
                    i for i in quality_filter if i["package"] == "single"
                    ]
                sorted_list = sorted(
                    package_type_list, key=lambda k: k["seeds"], reverse=True
                    )
                if len(sorted_list) > 0:
                    return sorted_list[0]

    return None
