# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import copy
import json
import sys
import time
from sqlite3 import OperationalError

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.common import tools
from resources.lib.database.trakt_sync import bookmark
from resources.lib.indexers import trakt
from resources.lib.modules import smartPlay, database, subtitles
from resources.lib.modules.globals import g


class SerenPlayer(xbmc.Player):
    """
    Class to handle playback methods and accept callbacks from Kodi player
    """

    def __init__(self):
        super(SerenPlayer, self).__init__()

        self._trakt_api = trakt.TraktAPI()
        self.trakt_id = None
        self.mediatype = None
        self.offset = None
        self.playing_file = None
        self.scrobbling_enabled = g.get_bool_setting("trakt.scrobbling")
        self.item_information = None
        self.smart_playlists = g.get_bool_setting("smartplay.playlistcreate")
        self.smart_module = None
        self.current_time = 0
        self.total_time = 0
        self.watched_percentage = 0
        self.ignoreSecondsAtStart = g.get_int_setting("trakt.ignoreSecondsAtStart")
        self.min_time_before_scrape = max(self.total_time * 0.2, 600)
        self.playCountMinimumPercent = g.get_int_setting(
            "trakt.playCountMinimumPercent"
            )
        self.dialogs_enabled = g.get_bool_setting(
            "smartplay.playingnextdialog"
            ) or g.get_bool_setting("smartplay.stillwatching")
        self.pre_scrape_enabled = g.get_bool_setting("smartPlay.preScrape")
        self.playing_next_time = g.get_int_setting("playingnext.time")
        self.bookmark_sync = bookmark.TraktSyncDatabase()
        self.trakt_enabled = True if g.get_setting("trakt.auth", "") else False
        self._running_path = None

        # Flags
        self.resumed = False
        self.playback_started = False
        self.playback_error = False
        self.playback_ended = False
        self.playback_stopped = False
        self.scrobbled = False
        self.scrobble_started = False
        self._force_marked_watched = False
        self.dialogs_triggered = False
        self.pre_scrape_initiated = False
        self.playback_timestamp = 0

    def play_source(self, stream_link, item_information, resume_time=None):
        """Method for handling playing of sources.

        :param stream_link: Direct link of source to be played or dict containing more information about the stream
        to play
        :type stream_link: str|dict
        :param item_information: Information about the item to be played
        :type item_information:dict
        :param resume_time:Time to resume the source at
        :type resume_time:int
        :rtype:None
        """
        self.pre_scrape_initiated = False
        if resume_time:
            self.offset = float(resume_time)

        if not stream_link:
            g.cancel_playback()
            return

        self.playing_file = stream_link
        self.item_information = item_information
        self.smart_module = smartPlay.SmartPlay(item_information)
        self.mediatype = self.item_information["info"]["mediatype"]
        self.trakt_id = self.item_information["info"]["trakt_id"]

        if self.item_information.get("resume", "false") == "true":
            self._try_get_bookmark()

        self._handle_bookmark()
        self._add_support_for_external_trakt_scrobbling()

        g.close_busy_dialog()
        g.close_all_dialogs()

        xbmcplugin.setResolvedUrl(g.PLUGIN_HANDLE, True, self._create_list_item(stream_link))

        self._keep_alive()

    # region Kodi player overrides
    def getTotalTime(self):
        """
        Returns total time for playing file if user is playing a file
        :return: Total length of file else 0 if not playing an item
        :rtype: int
        """
        if self.isPlaying():
            return xbmc.Player().getTotalTime()
        else:
            return 0

    def getTime(self):
        """
        Gets current position in seconds from start of item
        :return: Current position or 0 if not playing a file
        :rtype: int
        """
        if self.isPlaying():
            return xbmc.Player().getTime()
        else:
            return 0

    def isPlaying(self):
        """
        Retuns True if currently playing an item else False
        :return: True if playing an item else False
        :rtype: bool
        """
        return xbmc.Player().isPlaying()

    def isPlayingVideo(self):
        """
        Returns true if currently playing item is a video file
        :return: True if playing a file and it is video else False
        :rtype: bool
        """
        return xbmc.Player().isPlayingVideo()

    def seekTime(self, time):
        """
        Seeks the specified amount of time as fractional seconds if playing a file. The time specified is relative to
        the beginning of the currently. playing media file.
        :param time: Time to seek as fractional seconds
        :type time: float
        :return: None
        :rtype: None
        """
        if self.isPlaying():
            return xbmc.Player().seekTime(time)
        else:
            return None

    def getSubtitles(self):
        """
        Get subtitle stream name if playing a file
        :return: Stream Name if playing a file else None
        :rtype: str, None
        """
        if self.isPlaying():
            return xbmc.Player().getSubtitles()
        else:
            return None

    def getAvailableSubtitleStreams(self):
        """
        Get Subtitle stream names.
        :return: List of available subtitle streams
        :rtype: list, None
        """
        if self.isPlaying():
            return xbmc.Player().getAvailableSubtitleStreams()
        else:
            return None

    def setSubtitles(self, subtitle):
        """
        Set subtitle file and enable subtitles if currently playing an item.
        :param subtitle:  Path to file to use as source of subtitles
        :type subtitle: str
        :return: None
        :rtype: None
        """
        if self.isPlaying():
            xbmc.Player().setSubtitles(subtitle)
        else:
            return None

    def getPlayingFile(self):
        """
        Fetches the path to the playing file else returns None
        :return: Path to file
        :rtype: str/None
        """
        if self.isPlaying():
            try:
                return xbmc.Player().getPlayingFile()
            except RuntimeError:
                # seems that we have a racing condition between isPlaying() and getPlayingFile()
                return None
        else:
            return None

    def pause(self):
        """
        Pauses playing item if item is playing
        :return: None
        :rtype: None
        """
        if self.isPlaying():
            return xbmc.Player().pause()
        else:
            return None

    # endregion

    # region Kodi player callbacks
    def onAVStarted(self):
        """
        Callback method from Kodi to advise that AV stream has started
        :return: None
        :rtype: None
        """
        self._start_playback()

    def onAVChange(self):
        """
        Callback method from Kodi to advise that AV stream has started
        This is being used as a fallback for instances where AVStarted fails
        :return: None
        :rtype: None
        """
        self._start_playback()

    def onPlayBackSeek(self, time, seekOffset):
        """
        Callback method from Kodi when a seek event has occured
        :param time: Time to seek to
        :type time: int
        :param seekOffset: Offset from previous position
        :type seekOffset: int
        :return: None
        :rtype: None
        """
        seekOffset /= 1000
        self._trakt_start_watching(offset=seekOffset, re_scrobble=True)

    def onPlayBackSeekChapter(self, chapter):
        """
        Callback method from Kodi when user performs a chapter seek.
        :param chapter: Chapter seeked to
        :type chapter: int
        :return: None
        :rtype: None
        """
        self._trakt_start_watching(re_scrobble=True)

    def onPlayBackResumed(self):
        """
        Callback method from Kodi when user resumes a paused file.
        :return: None
        :rtype: None
        """
        self._trakt_start_watching(re_scrobble=True)

    def onPlayBackEnded(self):
        """
        Callback method from Kodi when playback has finished
        :return: None
        :rtype: None
        """
        self.playback_ended = True if self.playback_started else False
        self._end_playback()
        if g.PLAYLIST.getposition() == g.PLAYLIST.size() or g.PLAYLIST.size() == 1:
            g.PLAYLIST.clear()

    def onPlayBackStopped(self):
        """
        Callback method from Kodi when user stops a file.
        :return: None
        :rtype: None
        """
        self.playback_stopped = True if self.playback_started else False
        g.PLAYLIST.clear()
        self._end_playback()

    def onPlayBackPaused(self):
        """
        Callback method from Kodi when user pauses a file.
        :return: None
        :rtype: None
        """
        self._handle_bookmark()
        self._trakt_stop_watching()

    def onPlayBackError(self):
        """
        Callback method from Kodi when playback stops due to an error
        :return: None
        :rtype: None
        """
        g.log("Kodi has reported an error and has stopped playback!", "warning")
        self.playback_error = True
        g.PLAYLIST.clear()
        self._end_playback()
        sys.exit(1)

    # endregion

    def _start_playback(self):
        if self.playback_started:
            return

        self.playback_started = True
        self.plaback_stopped = False
        self.scrobbled = False
        self.playback_timestamp = time.time()

        g.close_all_dialogs()

        if self.smart_playlists and self.mediatype == "episode":
            if g.PLAYLIST.size() == 1 and not self.smart_module.is_season_final():
                self.smart_module.build_playlist()
            elif g.PLAYLIST.size() == g.PLAYLIST.getposition() + 1:
                self.smart_module.append_next_season()

    def _end_playback(self):
        self._mark_watched_dialog()
        self._handle_bookmark()
        self._trakt_stop_watching()
        if g.get_bool_setting("general.force.widget.refresh.playback"):
            g.trigger_widget_refresh()

    def _add_subtitle_if_needed(self):
        if not g.get_bool_setting("general.subtitle.enable"):
            return

        preferred_lang = self._get_kodi_preferred_subtitle_language()

        if preferred_lang == self.getSubtitles():
            return

        subtitle = subtitles.SubtitleService().get_subtitle()
        if subtitle is not None:
            self.setSubtitles(subtitle)

    @staticmethod
    def _get_kodi_preferred_subtitle_language():
        language = g.get_kodi_preferred_subtitle_language(True)
        if language == "original":
            audio_streams = xbmc.Player().getAvailableAudioStreams()
            if not audio_streams or len(audio_streams) == 0:
                return None
            return audio_streams[0]
        elif language == "default":
            return xbmc.getLanguage(xbmc.ISO_639_2)
        elif language == "none":
            return None
        elif language == "forced_only":
            return None
        else:
            return language

    def _create_list_item(self, stream_link):
        info = copy.deepcopy(self.item_information["info"])
        g.clean_info_keys(info)

        if isinstance(stream_link, dict) and stream_link["type"] == "Adaptive":
            provider = stream_link["provider_imports"]
            provider_module = __import__(
                "{}.{}".format(provider[0], provider[1]), fromlist=[""]
                )
            if not hasattr(provider_module, "get_listitem") and hasattr(
                    provider_module, "sources"
                    ):
                provider_module = provider_module.sources()
            item = provider_module.get_listitem(stream_link)
        else:
            item = xbmcgui.ListItem(path=stream_link)
            info["FileNameAndPath"] = tools.unquote(self.playing_file)
            item.setInfo("video", info)
            item.setProperty("IsPlayable", "true")

        art = self.item_information.get("art", {})
        item.setArt(art if isinstance(art, dict) else {})
        cast = self.item_information.get("cast", [])
        item.setCast(cast if isinstance(cast, list) else [])
        item.setUniqueIDs(
            {i.split("_")[0]: info[i] for i in info.keys() if i.endswith("id")},
            )
        return item

    def _add_support_for_external_trakt_scrobbling(self):
        if self.trakt_enabled and self.scrobbling_enabled:
            return
        trakt_meta = {}
        info = self.item_information.get("info")
        if info:
            if info.get("tmdb_id"):
                trakt_meta.update({"tmdb": info.get("tmdb_id")})
            if info.get("imdb_id"):
                trakt_meta.update({"imdb": info.get("imdb_id")})
            if info.get("trakt_slug"):
                trakt_meta.update({"slug": info.get("trakt_slug")})
            if info.get("tvdb_id"):
                trakt_meta.update({"tvdb": info.get("tvdb_id")})
        g.HOME_WINDOW.setProperty(
            "script.trakt.ids", json.dumps(trakt_meta, sort_keys=True)
        )

    def _update_progress(self, offset=None):
        self.current_time = self.getTime()

        if not self.total_time:
            return 0

        self.watched_percentage = 0

        if offset is not None:
            self.current_time += offset

        if self.total_time > 0:
            try:
                self.watched_percentage = tools.safe_round(
                    float(self.current_time) / float(self.total_time) * 100, 2
                    )
                if self.watched_percentage > 100:
                    self.watched_percentage = 100
            except TypeError:
                pass

    def _log_debug_information(self):
        g.log("PlaybackIdentifedAt: {}".format(self.getTime()), "debug")
        g.log("IgnoringSecondsAtStart: {}".format(self.ignoreSecondsAtStart), "debug")
        g.log("PreScrapeSeconds: {}".format(self.min_time_before_scrape), "debug")
        g.log("PlayCountMin: {}".format(self.playCountMinimumPercent), "debug")
        g.log("DialogsEnabled: {}".format(self.dialogs_enabled), "debug")
        g.log("TraktEnabled: {}".format(self.trakt_enabled), "debug")
        g.log("DialogSeconds: {}".format(self.playing_next_time), "debug")
        g.log("TotalMediaLength: {}".format(self.getTotalTime()), "debug")

    # region Trakt
    def _trakt_start_watching(self, offset=None, re_scrobble=False):
        if (
                not self.trakt_enabled
                or not self.scrobbling_enabled
                or (self.scrobbled and not re_scrobble)
                or (self.scrobble_started and not re_scrobble)
         ):
            return

        if (
                self.watched_percentage >= self.playCountMinimumPercent
                or self.current_time < self.ignoreSecondsAtStart
         ):
            return

        try:
            post_data = self._build_trakt_object(offset=offset)

            self._trakt_api.post("scrobble/start", post_data)
        except:
            g.log_stacktrace()
        self.scrobble_started = True

    def _trakt_stop_watching(self):
        if (
                not self.trakt_enabled
                or not self.scrobbling_enabled
                or self.scrobbled
                or g.get_global_setting("marked_watched_dialog_open")
                or self.current_time < self.ignoreSecondsAtStart
         ):
            return

        post_data = self._build_trakt_object()

        if (
                post_data["progress"] >= self.playCountMinimumPercent
                or self._force_marked_watched
         ):
            post_data["progress"] = (
                80 if post_data["progress"] < 80 else post_data["progress"]
             )
            try:
                scrobble_response = self._trakt_api.post("scrobble/stop", post_data)
            except:
                g.log_stacktrace()
                return
            if scrobble_response.status_code in (201, 409):
                self._trakt_mark_playing_item_watched()
                self.scrobbled = True
        elif self.current_time > self.ignoreSecondsAtStart:
            try:
                scrobble_response = self._trakt_api.post("scrobble/pause", post_data)
            except:
                g.log_stacktrace()
                return
        else:
            return

        if not scrobble_response.status_code == 201:
            g.log("Error scrobbling item to Trakt")

    def _trakt_mark_playing_item_watched(self):
        if self.mediatype == "episode":
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            TraktSyncDatabase().mark_episode_watched(
                self.item_information["info"]["trakt_show_id"],
                self.item_information["info"]["season"],
                self.item_information["info"]["episode"],
                )
        if self.mediatype == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            TraktSyncDatabase().mark_movie_watched(self.trakt_id)

    def _build_trakt_object(self, offset=None):
        post_data = {self.mediatype: {"ids": {"trakt": self.trakt_id}}}
        if offset:
            self._update_progress(offset)

        post_data["progress"] = self.watched_percentage
        return post_data

    def _mark_watched_dialog(self):
        if g.get_global_setting("marked_watched_dialog_open"):
            return

        if (
                self.getPlayingFile()
                and self._running_path
                and self._running_path != self.getPlayingFile()
                and self.watched_percentage < self.playCountMinimumPercent
                and (time.time() - self.playback_timestamp) > 600
         ):
            xbmc.sleep(10000)
            g.set_global_setting("marked_watched_dialog_open", True)
            if xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30526)):
                self._force_marked_watched = True
            g.set_global_setting("marked_watched_dialog_open", False)

    # endregion

    def _keep_alive(self):
        for i in range(0, 480):
            self._running_path = self.getPlayingFile()
            if self._is_file_playing() or self._playback_has_stopped():
                break
            xbmc.sleep(250)

        self.total_time = self.getTotalTime()

        if self.offset and not self.resumed:
            self.seekTime(self.offset)
            self.resumed = True

        self._log_debug_information()
        self._add_subtitle_if_needed()
        xbmc.sleep(5000)

        while self._is_file_playing() and not g.abort_requested():

            self._update_progress()

            if not self.scrobble_started:
                self._trakt_start_watching()

            time_left = int(self.total_time) - int(self.current_time)

            if self.min_time_before_scrape > time_left and not self.pre_scrape_initiated:
                self._handle_pre_scrape()

            if (self.watched_percentage >= self.playCountMinimumPercent) and not self.scrobbled:
                self._trakt_stop_watching()
                self._handle_bookmark()

            if self.dialogs_enabled and not self.dialogs_triggered:
                if time_left <= self.playing_next_time:
                    xbmc.executebuiltin(
                        'RunPlugin("plugin://plugin.video.seren/?action=runPlayerDialogs")'
                        )
                    self.dialogs_triggered = True

            xbmc.sleep(100)

        self._end_playback()

    def _playback_has_stopped(self):
        return self.playback_stopped or self.playback_error or self.playback_ended

    def _handle_pre_scrape(self):
        if self.pre_scrape_enabled and not self.pre_scrape_initiated:
            self.smart_module.pre_scrape()
            self.pre_scrape_initiated = True

    def _try_get_bookmark(self):
        bm = self.bookmark_sync.get_bookmark(self.trakt_id)
        self.offset = bm["resumeTime"] if bm is not None else None

    def _handle_bookmark(self):
        if g.get_global_setting("marked_watched_dialog_open"):
            return

        try:
            database.clear_local_bookmarks()
        except OperationalError:
            pass

        if self.current_time == 0 or self.total_time == 0:
            self.bookmark_sync.remove_bookmark(self.trakt_id)
            return

        if (
                self.watched_percentage < self.playCountMinimumPercent
                and self.current_time >= self.ignoreSecondsAtStart
                and not self._force_marked_watched
         ):
            self.bookmark_sync.set_bookmark(
                self.trakt_id,
                int(self.current_time),
                self.mediatype,
                self.watched_percentage,
                )
        else:
            self.bookmark_sync.remove_bookmark(self.trakt_id)

    def _is_file_playing(self):
        if self._playback_has_stopped():
            return False

        if not self.playback_started:
            return False

        if self._running_path is None or self._running_path.startswith("plugin://"):
            return False

        playing_file = self.getPlayingFile()
        return self._running_path == playing_file


class PlayerDialogs(xbmc.Player):
    """
    Handles dialogs that appear over playing items
    """

    def __init__(self):
        super(PlayerDialogs, self).__init__()
        self._min_time = g.get_int_setting("playingnext.time")
        self.playing_file = None

    def display_dialog(self):
        """
        Handles the initiating of dialogs and deciding which dialog to display if required
        :return: None
        :rtype: None
        """
        try:
            self.playing_file = self.getPlayingFile()
        except RuntimeError:
            g.log("Kodi did not return a playing file, killing playback dialogs", "error")
            return
        if g.PLAYLIST.size() > 0 and g.PLAYLIST.getposition() != (
                g.PLAYLIST.size() - 1
         ):
            if g.get_bool_setting("smartplay.stillwatching") and self._still_watching_calc():
                target = self._show_still_watching
            elif g.get_bool_setting("smartplay.playingnextdialog"):
                target = self._show_playing_next
            else:
                return

            if self.playing_file != self.getPlayingFile():
                return

            if not self.isPlayingVideo():
                return

            if not self._is_video_window_open():
                return

            target()

    @staticmethod
    def _still_watching_calc():
        calculation = float(g.PLAYLIST.getposition() + 1) / g.get_float_setting(
            "stillwatching.numepisodes"
            )

        if calculation == 0:
            return False

        return calculation.is_integer()

    def _show_playing_next(self):
        from resources.lib.gui.windows.playing_next import PlayingNext
        from resources.lib.database.skinManager import SkinManager

        window = PlayingNext(
            *SkinManager().confirm_skin_path("playing_next.xml"),
            item_information=self._get_next_item_item_information()
            )
        window.doModal()
        del window

    def _show_still_watching(self):
        from resources.lib.gui.windows.still_watching import StillWatching
        from resources.lib.database.skinManager import SkinManager

        window = StillWatching(
            *SkinManager().confirm_skin_path("still_watching.xml"),
            item_information=self._get_next_item_item_information()
            )
        window.doModal()
        del window

    @staticmethod
    def _get_next_item_item_information():
        current_position = g.PLAYLIST.getposition()
        url = g.PLAYLIST[  # pylint: disable=unsubscriptable-object
            current_position + 1
            ].getPath()
        params = dict(tools.parse_qsl(tools.unquote(url.split("?")[1])))
        return tools.get_item_information(
            tools.deconstruct_action_args(params.get("action_args"))
            )

    @staticmethod
    def _is_video_window_open():
        if xbmcgui.getCurrentWindowId() != 12005:
            return False
        return True
