# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import random
import sys

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.database.skinManager import SkinManager
from resources.lib.database.trakt_sync.shows import TraktSyncDatabase
from resources.lib.gui.windows.persistent_background import PersistentBackground
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.modules.globals import g
from resources.lib.modules.list_builder import ListBuilder
from resources.lib.modules.metadataHandler import MetadataHandler


class SmartPlay:
    """
    Provides smart operations for playback
    """
    def __init__(self, item_information):
        self.list_builder = ListBuilder()
        if "info" not in item_information:
            item_information = tools.get_item_information(item_information)
        self.item_information = item_information

        if not isinstance(self.item_information, dict):
            raise TypeError("Item Information is not a dictionary")

        self.show_trakt_id = self.item_information.get("trakt_show_id")
        if not self.show_trakt_id and "action_args" in self.item_information:
            self.show_trakt_id = self._extract_show_id_from_args(
                self.item_information["action_args"]
            )

        self.display_style = g.get_int_setting("smartplay.displaystyle")
        self.trakt_api = TraktAPI()

    @staticmethod
    def _extract_show_id_from_args(action_args):
        if action_args["mediatype"] in ["tvshow", "movie"]:
            return action_args["trakt_id"]
        elif action_args["mediatype"] in ["episode", "season"]:
            return action_args["trakt_show_id"]

    def get_season_info(self):
        """
        Fetches all season information for current show from database
        :return:
        :rtype:
        """
        return TraktSyncDatabase().get_season_list(self.show_trakt_id)

    def resume_show(self):
        """
        Identifies resumse point for a show and plays from there
        :return:
        :rtype:
        """
        g.cancel_playback()
        g.close_all_dialogs()
        g.PLAYLIST.clear()

        window = self._get_window()

        window.set_text(g.get_language_string(30063))
        window.show()

        window.set_text(g.get_language_string(30064))

        season_id, episode = self.get_resume_episode()

        window.set_text(g.get_language_string(30065))

        window.set_text(g.get_language_string(30066))

        self.build_playlist(season_id, episode)

        window.set_text(g.get_language_string(30338))

        g.log(
            "Begining play from Season ID {} Episode {}".format(season_id, episode),
            "info",
        )

        window.close()
        del window

        xbmc.Player().play(g.PLAYLIST)

    def build_playlist(self, season_id=None, minimum_episode=None):
        """
        Uses available information to add relevant episodes to the current playlist
        :param season_id: Trakt ID of season to build
        :type season_id: int
        :param minimum_episode: Minimum episodes to add from
        :type minimum_episode: int
        :return:
        :rtype:
        """
        if season_id is None:
            season_id = self.item_information["info"]["trakt_season_id"]

        if minimum_episode is None:
            minimum_episode = int(self.item_information["info"]["episode"]) + 1

        try:
            [
                g.PLAYLIST.add(url=i[0], listitem=i[1])
                for i in self.list_builder.episode_list_builder(
                    self.show_trakt_id,
                    season_id,
                    minimum_episode=minimum_episode,
                    smart_play=True,
                    hide_unaired=True,
                )
            ]
        except TypeError:
            g.log_stacktrace()
            g.log(
                "Unable to add more episodes to the playlist, they may not be available for the requested season",
                "error",
            )
            return

    def get_resume_episode(self):
        """
        Fetches playback information for current show and identifies the next episode to be resumed/watched
        :return: (Season, Episode) tuple
        :rtype: tuple
        """
        get = MetadataHandler().get_trakt_info
        info = MetadataHandler().info
        try:
            playback_history = self.trakt_api.get_json(
                "sync/history/shows/{}".format(self.show_trakt_id), limit=1
            )[0]
            action = playback_history["action"]
            episode_info = playback_history["episode"]
            season = get(episode_info, "season")
            episode = get(episode_info, "episode")
        except IndexError:
            # Capture failure to get old playback and resume from first episode
            action = "watch"
            season = 1
            episode = 1

        if action != "watch":
            episode += 1

        all_seasons = self.get_season_info()
        season_info = [i for i in all_seasons if info(i).get("season") == season][0]

        if episode >= info(season_info).get("episode_count"):
            season += 1
            episode = 1

        if self.final_episode_check(season, episode):
            season = 1
            episode = 1

        season_id = info(
            [i for i in all_seasons if info(i).get("season") == season][0]).get("trakt_id")

        return season_id, episode

    def final_episode_check(self, season, episode):
        """
        Checks to see if the current item is the last episode aired for the show
        :param season: Season number of item to check
        :type season: int
        :param episode: Episode number of item to check
        :type episode: int
        :return: True if item is last aired episode else false
        :rtype: bool
        """
        get = MetadataHandler().get_trakt_info
        season = int(season)
        episode = int(episode)

        last_aired = self.trakt_api.get_json(
            "shows/{}/last_episode".format(self.show_trakt_id)
        )

        if season > get(last_aired, "season"):
            return True

        if season == get(last_aired, "season") and episode == get(last_aired, "number"):
            return True

        return False

    def append_next_season(self):
        """
        Checks if current episode is the last episode for the season, if true adds next seasons episodes to playlist
        :return:
        :rtype:
        """
        episode = self.item_information["info"]["episode"]
        season = self.item_information["info"]["season"]
        season_info = self.get_season_info()
        current_season_info = [i for i in season_info if season == i["info"]["season"]][0]
        if episode != current_season_info["episode_count"]:
            return

        next_season = [i for i in season_info if i["info"]["season"] == season + 1]
        if len(next_season) == 0:
            return

        season_id = next_season[0]["trakt_id"]
        self.build_playlist(season_id, 1)

    @staticmethod
    def pre_scrape():
        """
        Checks whether a item exists in the current playlist after current item and then pre-fetches results
        :return:
        :rtype:
        """
        next_position = g.PLAYLIST.getposition() + 1
        if next_position >= g.PLAYLIST.size():
            return

        url = g.PLAYLIST[  # pylint: disable=unsubscriptable-object
            next_position
        ].getPath()

        if not url:
            return

        url = url.replace("getSources", "preScrape")
        g.set_setting("general.tempSilent", "true")
        g.log("Running Pre-Scrape: {}".format(url))
        xbmc.executebuiltin('RunPlugin("{}")'.format(url))

    def shuffle_play(self):
        """
        Creates a playlist of shuffled episodes for selected show and plays it
        :return:
        :rtype:
        """

        g.PLAYLIST.clear()
        window = self._get_window()
        window.show()
        window.set_text(g.get_language_string(30065))

        season_list = self.trakt_api.get_json(
            "shows/{}/seasons".format(self.show_trakt_id), extended="episodes"
        )
        if season_list[0]["trakt_object"]["info"]["season"] == 0:
            season_list.pop(0)

        window.set_text(g.get_language_string(30066))

        episode_list = [
            episode
            for season in season_list
            for episode in season["trakt_object"]["info"]["episodes"]
        ]
        random.shuffle(episode_list)
        episode_list = episode_list[:40]
        [
            episode.update({"trakt_show_id": self.show_trakt_id})
            for episode in episode_list
        ]

        playlist = self.list_builder.mixed_episode_builder(
            episode_list, smart_play=True
        )

        window.set_text(g.get_language_string(30067))

        for episode in playlist:
            if episode is not None:
                g.PLAYLIST.add(url=episode[0], listitem=episode[1])

        window.close()
        del window

        g.PLAYLIST.shuffle()
        xbmc.Player().play(g.PLAYLIST)

    def play_from_random_point(self):
        """
        Select a random episode for show and plays from that point onwards
        :return:
        :rtype:
        """

        import random

        g.PLAYLIST.clear()

        season_id = random.choice(self.get_season_info())["trakt_id"]
        playlist = self.list_builder.episode_list_builder(
            self.show_trakt_id, trakt_season=season_id, smart_play=True
        )
        random_episode = random.randint(0, len(playlist) - 1)
        playlist = playlist[random_episode]
        g.PLAYLIST.add(url=playlist[0], listitem=playlist[1])
        xbmc.Player().play(g.PLAYLIST)

    def create_single_item_playlist_from_info(self):
        g.cancel_playback()
        name = self.item_information["info"]["title"]
        item = g.add_directory_item(
            name,
            action="getSources",
            menu_item=self.item_information,
            action_args=tools.construct_action_args(self.item_information),
            bulk_add=True,
            is_playable=True,
            )
        g.PLAYLIST.add(url=sys.argv[0] + sys.argv[2], listitem=item[1])
        return g.PLAYLIST

    def playlist_present_check(self, ignore_setting=False):
        """
        Confirms if a playlist is currently present. If not or playlist is for a different item, clear current list
        and build a new one
        :param ignore_setting: Force playlist building if setting is disabled
        :type ignore_setting: bool
        :return: Playlist if playlist is present else False
        :rtype: any
        """
        if g.get_bool_setting("smartplay.playlistcreate") or ignore_setting:

            if not self.item_information["info"]["mediatype"] == "episode":
                g.log("Movie playback requested, clearing playlist")
                g.PLAYLIST.clear()
                return False

            playlist_uris = [
                g.PLAYLIST[i].getPath()  # pylint: disable=unsubscriptable-object
                for i in range(g.PLAYLIST.size())
            ]

            # Check to see if we are just starting playback and kodi has created a playlist
            if len(playlist_uris) == 1 and playlist_uris[0].split('/')[-1] == sys.argv[2]:
                return False

            if g.PLAYLIST.getposition() == -1:
                return self.create_single_item_playlist_from_info()

            if [i for i in playlist_uris if g.ADDON_NAME.lower() not in i]:
                g.log("Cleaning up other addon items from playlsit", "debug")
                playlist_uris = []
                
            action_args = [
                g.legacy_action_args_converter(
                    g.legacy_params_converter(
                        dict(tools.parse_qsl(i.split("?")[-1]))
                        )
                    )["action_args"]
                for i in playlist_uris]
  
            show_ids = set(tools.deconstruct_action_args(i).get('trakt_show_id') for i in action_args)

            if len(show_ids) > 1 and self.show_trakt_id not in show_ids:
                g.log("Cleaning up items from other shows", "debug")
                playlist_uris = []

            if (len(playlist_uris) == 0 or
                (len(playlist_uris) > 1 and not any(sys.argv[2] in i for i in playlist_uris))) or \
                    g.PLAYLIST.getposition() == -1:
                return self.create_single_item_playlist_from_info()

        return False

    def is_season_final(self):
        """
        Checks if episode in question is the final for the season
        :return: bool
        :rtype: True if last episode of season, else False
        """
        season = [i for i in self.get_season_info()
                  if int(self.item_information["info"]["season"]) == int(i["info"]["season"])][0]

        if self.item_information["info"]["episode"] == season["episode_count"]:
            return True
        else:
            return False

    @staticmethod
    def handle_resume_prompt(resume_switch, force_resume_off=False, force_resume_on=False, force_resume_check=False):
        """
        Handles displaying of resume prompt for item if required
        :param resume_switch: Resume param from arg string
        :type resume_switch: any
        :param force_resume_off: Disable resuming of item
        :type force_resume_off: bool
        :param force_resume_on: Force try resuming item
        :type force_resume_on: bool
        :param force_resume_check: Force a database check for item resume point
        :type force_resume_check: bool
        :return: Resume time in seconds for item
        :rtype: int
        """
        bookmark_style = g.get_int_setting("general.bookmarkstyle")

        if force_resume_check and not resume_switch:
            from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase

            trakt_id = g.REQUEST_PARAMS.get("action_args").get("trakt_id")

            bookmark = TraktSyncDatabase().get_bookmark(trakt_id)
            if bookmark:
                g.log("bookmark: {}".format(bookmark))
                resume_switch = bookmark["resume_time"]

        if (
            g.PLAYLIST.size() <= 1
            and resume_switch is not None
            and bookmark_style != 2
            and not force_resume_off
        ):

            if bookmark_style == 0 and not force_resume_on:
                import datetime

                selection = xbmcgui.Dialog().contextmenu(
                    [
                        "{} {}".format(
                            g.get_language_string(30062),
                            datetime.timedelta(seconds=int(resume_switch)),
                        ),
                        g.get_language_string(30362),
                    ]
                )
                if selection == -1:
                    g.cancel_playback()
                    sys.exit()
                elif selection != 0:
                    resume_switch = None
        else:
            resume_switch = None

        return resume_switch

    def _get_window(self):
        if self.display_style == 0:
            return PersistentBackground(
                *SkinManager().confirm_skin_path("persistent_background.xml"),
                item_information=self.item_information
            )
        else:
            return BackgroundWindowAdapter()


class BackgroundWindowAdapter(xbmcgui.DialogProgressBG):
    """
    Ease of use adapter for handling smart play dialogs
    """
    def __init__(self):
        super(BackgroundWindowAdapter, self).__init__()
        self.text = ""
        self.created = False

    def show(self):
        """
        Show the dialog to the user
        :return:
        :rtype:
        """
        self.create(g.ADDON_NAME, self.text)

    def set_text(self, text):
        """
        Sets the dialog text
        :param text: Text to display to user
        :type text: str
        :return:
        :rtype:
        """
        self.text = text
        if self.created:
            self.update()

    def update(self, percent=None, heading=None, message=None):
        """
        Update dialog progress
        :param percent: Percent of progress
        :type percent: int
        :param heading: Text to set as dialog heading
        :type heading: str
        :param message: Text to set as dialog message
        :type message: str
        :return:
        :rtype:
        """
        super(BackgroundWindowAdapter, self).update(percent, heading, message)
