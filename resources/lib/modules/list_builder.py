# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import datetime

import xbmcplugin

from resources.lib.common import tools
from resources.lib.database.trakt_sync import movies, shows
from resources.lib.modules.globals import g


class ListBuilder(object):
    """
    Ease of use class to handle building menus of lists or list items
    """

    def __init__(self):
        self.date_delay = g.get_bool_setting("general.datedelay")
        self.title_appends_mixed = g.get_setting("general.appendtitles")
        self.title_appends_general = g.get_setting("general.appendepisodegeneral")
        self.flatten_episodes = g.get_bool_setting("general.flatten.episodes")
        self.page_limit = g.get_int_setting("item.limit")
        self.hide_unaired = g.get_bool_setting("general.hideUnAired")
        self.list_title_appends = g.get_setting("general.appendListTitles")

    def season_list_builder(self, show_id, **params):
        """
        Builds a menu list of a shows seasons
        :param show_id: Trakt ID of show
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        return self._common_menu_builder(
            shows.TraktSyncDatabase().get_season_list(show_id, **params),
            g.CONTENT_SEASON,
            "seasonEpisodes",
            **params
        )

    def episode_list_builder(self, trakt_show_id, trakt_season=None, **params):
        """
        Builds a menu list of a episodes for specified show's season
        :param trakt_show_id: Trakt ID of show
        :param trakt_season: season number
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        params["is_folder"] = False
        params["is_playable"] = True
        action = "getSources"

        return self._common_menu_builder(
            shows.TraktSyncDatabase().get_episode_list(
                trakt_show_id,
                trakt_season,
                minimum_episode=params.pop("minimum_episode", None),
                **params
            ),
            g.CONTENT_EPISODE,
            action,
            **params
        )

    def mixed_episode_builder(self, trakt_list, **params):
        """
        Builds a menu list of episodes of mixed shows/seasons
        :param trakt_list: List of episode objects
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        params["is_folder"] = False
        params["is_playable"] = True
        params["mixed_list"] = True
        action = "getSources"

        return self._common_menu_builder(
            shows.TraktSyncDatabase().get_mixed_episode_list(trakt_list, **params),
            g.CONTENT_EPISODE,
            action,
            **params
        )

    def show_list_builder(self, trakt_list, **params):
        """
        Builds a mneu list of shows
        :param trakt_list: List of show objects
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        action = "flatEpisodes" if self.flatten_episodes else "showSeasons"
        if g.get_bool_setting("smartplay.clickresume"):
            params["is_folder"] = False
            params["is_playable"] = True
            action = "forceResumeShow"

        self._common_menu_builder(
            shows.TraktSyncDatabase().get_show_list(trakt_list, **params),
            g.CONTENT_SHOW,
            action,
            **params
        )

    def movie_menu_builder(self, trakt_list, **params):
        """
        Builds a mneu list of movies
        :param trakt_list: List of movie objects
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        params["is_folder"] = False
        params["is_playable"] = True
        action = "getSources"

        self._common_menu_builder(
            movies.TraktSyncDatabase().get_movie_list(trakt_list, **params),
            g.CONTENT_MOVIE,
            action,
            **params
        )

    def lists_menu_builder(self, trakt_list, **params):
        """
        Builds a menu list of lists
        :param trakt_list: List of list objects
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        self._common_menu_builder(trakt_list, g.CONTENT_FOLDER, "traktList", **params)

    def _common_menu_builder(
        self, trakt_list, content_type, action="getSources", **params
    ):
        if len(trakt_list) == 0:
            g.log("We received no titles to build a list", "warning")
            g.cancel_directory()
            return

        smart_play = params.pop("smart_play", False)
        no_paging = params.pop("no_paging", False)
        sort = params.pop("sort", False)
        list_items = []
        prepend_date = params.pop("prepend_date", False)
        mixed_list = params.pop("mixed_list", False)
        params.pop("hide_unaired", None)
        params.pop("hide_watched", None)
        try:
            params["bulk_add"] = True
            list_items = [
                g.add_directory_item(
                    item.get("name"),
                    action=action,
                    menu_item=item,
                    action_args=item.get("args"),
                    **params
                )
                for item in self._post_process_list(
                    trakt_list, prepend_date, mixed_list
                )
                if item is not None
            ]

            if smart_play:
                return list_items
            else:
                xbmcplugin.addDirectoryItems(
                    g.PLUGIN_HANDLE, list_items, len(list_items)
                )
        except Exception as e:
            g.log_stacktrace()
            if not smart_play:
                g.cancel_directory()
            raise e

        finally:
            if not smart_play:
                if (
                    not (
                        g.FROM_WIDGET and g.get_bool_setting("general.widget.hide_next")
                    )
                    and not no_paging
                    and len(list_items) >= self.page_limit
                ):
                    g.REQUEST_PARAMS["page"] = g.PAGE + 1
                    params = g.REQUEST_PARAMS
                    params.update({"special_sort": "bottom"})
                    g.add_directory_item(g.get_language_string(30016), **params)
                g.close_directory(content_type, sort=sort)

    def is_aired(self, info):
        """
        Confirms supplied item has aired based on meta
        :param info: Meta of item
        :return: Bool, True if object has aired else False
        """
        air_date = info.get("aired", info.get("premiered"))

        if not air_date:
            return False

        if int(air_date[:4]) < 1970:
            return True

        time_format = tools.DATE_FORMAT

        if len(air_date) == 10:
            time_format = "%Y-%m-%d"

        if self.date_delay:
            air_date = tools.parse_datetime(air_date, time_format, False)
            air_date += datetime.timedelta(days=1)
        else:
            air_date = tools.parse_datetime(air_date, time_format, False)

        if air_date >= datetime.datetime.now():
            return False
        else:
            return True

    def _post_process_list(self, item_list, prepend_date=False, mixed_list=False):
        return [
            self._post_process(item, prepend_date, mixed_list) for item in item_list
        ]

    def _post_process(self, item, prepend_date=False, mixed_list=False):
        if not item:
            return

        name = g.decode_py2(item.get("info", {}).get("title"))

        if not name:
            g.log("Item has no title: {}".format(item), "error")

        if (
            not item["info"]["mediatype"] == "list"
            and not self.hide_unaired
            and not self.is_aired(item["info"])
        ):
            name = g.color_string(tools.italic_string(name), "red")

        if item["info"]["mediatype"] == "episode":
            if self.title_appends_mixed and mixed_list:
                name = self._handle_episode_title_appending(
                    name, item, self.title_appends_mixed
                )
            elif self.title_appends_general and not mixed_list:
                name = self._handle_episode_title_appending(
                    name, item, self.title_appends_general
                )

        if item["info"]["mediatype"] == "list" and self.list_title_appends == "1":
            name += " - {}".format(
                g.color_string(g.encode_py2(item["info"]["username"]))
            )

        if not item["info"]["mediatype"] == "list" and prepend_date:
            release_day = tools.parse_datetime(item["info"]["aired"][:10])
            if release_day:
                release_day = release_day.strftime("%d %b")
                name = "[{}] {}".format(release_day, g.encode_py2(name))
        item.update({"name": name})
        item["info"]["title"] = name

        return item

    @staticmethod
    def _handle_episode_title_appending(name, item, title_append_style):
        if title_append_style == "1":
            name = "{}x{} {}".format(
                g.display_string(item["info"]["season"]).zfill(2),
                g.display_string(item["info"]["episode"]).zfill(2),
                g.display_string(name),
            )

        elif title_append_style == "2":
            name = "{}: {}".format(
                g.color_string(item["info"]["tvshowtitle"]), g.display_string(name)
            )

        elif title_append_style == "3":
            name = "{}: {}x{} {}".format(
                g.color_string(item["info"]["tvshowtitle"]),
                g.display_string(item["info"]["season"]).zfill(2),
                g.display_string(item["info"]["episode"]).zfill(2),
                g.display_string(name),
            )

        return name
