from functools import cached_property

import xbmcgui

from resources.lib.modules.globals import g


class TraktContextMenu:
    """
    Handles manual user interactions to the Trakt API
    """

    def __init__(self, item_information):
        super().__init__()
        trakt_id = item_information["trakt_id"]
        item_type = item_information["action_args"]["mediatype"].lower()
        display_type = self._get_display_name(item_type)

        self._confirm_item_information(item_information)

        self.dialog_list = []

        self._handle_watched_options(item_information, item_type)
        self._handle_collected_options(item_information, trakt_id, display_type)
        self._handle_watchlist_options(item_type)

        standard_list = [
            g.get_language_string(30280),
            g.get_language_string(30281),
            g.get_language_string(30282).format(display_type),
            g.get_language_string(30283),
        ]

        self.dialog_list.extend(iter(standard_list))
        self._handle_progress_option(item_type, trakt_id)

        selection = xbmcgui.Dialog().select(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            self.dialog_list,
        )

        if selection == -1:
            return

        options = {
            g.get_language_string(30274).format(display_type): {
                "method": self._add_to_collection,
                "info_key": "info",
            },
            g.get_language_string(30275).format(display_type): {
                "method": self._remove_from_collection,
                "info_key": "info",
            },
            g.get_language_string(30276): {
                "method": self._add_to_watchlist,
                "info_key": "info",
            },
            g.get_language_string(30277): {
                "method": self._remove_from_watchlist,
                "info_key": "info",
            },
            g.get_language_string(30278): {
                "method": self._mark_watched,
                "info_key": "info",
            },
            g.get_language_string(30279): {
                "method": self._mark_unwatched,
                "info_key": "info",
            },
            g.get_language_string(30280): {
                "method": self._add_to_list,
                "info_key": "info",
            },
            g.get_language_string(30281): {
                "method": self._remove_from_list,
                "info_key": "info",
            },
            g.get_language_string(30282).format(display_type): {
                "method": self._hide_item,
                "info_key": "action_args",
            },
            g.get_language_string(30283): {
                "method": self._refresh_meta_information,
                "info_key": "info",
            },
            g.get_language_string(30284): {
                "method": self._remove_playback_history,
                "info_key": "info",
            },
        }

        selected_option = self.dialog_list[selection]
        if selected_option not in options:
            return
        else:
            selected_option = options[selected_option]

        selected_option["method"](item_information[selected_option["info_key"]])

    @cached_property
    def trakt_api(self):
        from resources.lib.indexers.trakt import TraktAPI

        return TraktAPI()

    @staticmethod
    def _get_display_name(content_type):
        if content_type == "movie":
            return g.get_language_string(30264)
        else:
            return g.get_language_string(30285)

    def _handle_watchlist_options(self, item_type):
        if item_type not in ["season", "episode"]:
            self.dialog_list += [
                g.get_language_string(30276),
                g.get_language_string(30277),
            ]

    def _handle_progress_option(self, item_type, trakt_id):
        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase

        if item_type not in ["show", "season"] and TraktSyncDatabase().get_bookmark(trakt_id):
            self.dialog_list.append(g.get_language_string(30284))

    def _handle_collected_options(self, item_information, trakt_id, display_type):
        if item_information["info"]["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            collection = [i["trakt_id"] for i in TraktSyncDatabase().get_all_collected_movies()]
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            collection = TraktSyncDatabase().get_collected_shows(force_all=True)
            collection = {i["trakt_id"] for i in collection if i is not None}
            trakt_id = self._get_show_id(item_information["info"])
        if trakt_id in collection:
            self.dialog_list.append(g.get_language_string(30275).format(display_type))
        else:
            self.dialog_list.append(g.get_language_string(30274).format(display_type))

    def _handle_watched_options(self, item_information, item_type):
        if item_type in ["movie", "episode"]:
            if item_information["play_count"] > 0:
                self.dialog_list.append(g.get_language_string(30279))
            else:
                self.dialog_list.append(g.get_language_string(30278))
        elif item_information.get("unwatched_episodes", 0) > 0:
            self.dialog_list.append(g.get_language_string(30278))
        else:
            self.dialog_list.append(g.get_language_string(30279))

    @staticmethod
    def _confirm_item_information(item_information):
        if item_information is None:
            raise TypeError("Invalid item information passed to Trakt Manager")

    @staticmethod
    def _refresh_meta_information(trakt_object):
        from resources.lib.database import trakt_sync

        trakt_sync.TraktSyncDatabase().clear_specific_item_meta(trakt_object["trakt_id"], trakt_object["mediatype"])
        g.container_refresh()
        g.trigger_widget_refresh()

    @staticmethod
    def _confirm_marked_watched(response, type):
        if response["added"][type] > 0:
            return True
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30287),
        )
        g.log(f"Failed to mark item as watched\nTrakt Response: {response}")

        return False

    @staticmethod
    def _confirm_marked_unwatched(response, type):
        if response["deleted"][type] > 0:
            return True
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30287),
        )
        g.log(f"Failed to mark item as unwatched\nTrakt Response: {response}")
        return False

    @staticmethod
    def _info_to_trakt_object(item_information, force_show=False):
        if force_show and item_information["mediatype"] in ("season", "episode"):
            ids = [{"ids": {"trakt": item_information["trakt_show_id"]}}]
            return {"shows": ids}
        ids = [{"ids": {"trakt": item_information["trakt_id"]}}]
        if item_information["mediatype"] == "movie":
            return {"movies": ids}
        elif item_information["mediatype"] == "season":
            return {"seasons": ids}
        elif item_information["mediatype"] == "tvshow":
            return {"shows": ids}
        elif item_information["mediatype"] == "episode":
            return {"episodes": ids}

    @staticmethod
    def _get_show_id(item_information):
        return (
            item_information["trakt_show_id"]
            if item_information["mediatype"] != "tvshow"
            else item_information["trakt_id"]
        )

    def _mark_watched(self, item_information, silent=False):
        response = self.trakt_api.post_json("sync/history", self._info_to_trakt_object(item_information))

        if item_information["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            if not self._confirm_marked_watched(response, "movies"):
                return
            TraktSyncDatabase().mark_movie_watched(item_information["trakt_id"])
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            if not self._confirm_marked_watched(response, "episodes"):
                return
            if item_information["mediatype"] == "episode":
                TraktSyncDatabase().mark_episode_watched(
                    item_information["trakt_show_id"],
                    item_information["season"],
                    item_information["episode"],
                )
            elif item_information["mediatype"] == "season":
                show_id = item_information["trakt_show_id"]
                season_no = item_information["season"]
                TraktSyncDatabase().mark_season_watched(show_id, season_no, 1)
            elif item_information["mediatype"] == "tvshow":
                TraktSyncDatabase().mark_show_watched(item_information["trakt_id"], 1)

        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30288),
        )
        if not silent:
            g.container_refresh()
            g.trigger_widget_refresh()

    def _mark_unwatched(self, item_information):
        response = self.trakt_api.post_json("sync/history/remove", self._info_to_trakt_object(item_information))

        if item_information["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            if not self._confirm_marked_unwatched(response, "movies"):
                return
            TraktSyncDatabase().mark_movie_unwatched(item_information["trakt_id"])

        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            if not self._confirm_marked_unwatched(response, "episodes"):
                return
            if item_information["mediatype"] == "episode":
                TraktSyncDatabase().mark_episode_unwatched(
                    item_information["trakt_show_id"],
                    item_information["season"],
                    item_information["episode"],
                )
            elif item_information["mediatype"] == "season":
                show_id = item_information["trakt_show_id"]
                season_no = item_information["season"]
                TraktSyncDatabase().mark_season_watched(show_id, season_no, 0)
            elif item_information["mediatype"] == "tvshow":
                TraktSyncDatabase().mark_show_watched(item_information["trakt_id"], 0)

        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase

        TraktSyncDatabase().remove_bookmark(item_information["trakt_id"])

        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30289),
        )
        g.container_refresh()
        g.trigger_widget_refresh()

    def _add_to_collection(self, item_information):
        self.trakt_api.post("sync/collection", self._info_to_trakt_object(item_information, True))

        if item_information["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            TraktSyncDatabase().mark_movie_collected(item_information["trakt_id"])
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            trakt_id = self._get_show_id(item_information)
            TraktSyncDatabase().mark_show_collected(trakt_id, 1)

        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30290),
        )
        g.trigger_widget_refresh()

    def _remove_from_collection(self, item_information):
        self.trakt_api.post("sync/collection/remove", self._info_to_trakt_object(item_information, True))

        if item_information["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            TraktSyncDatabase().mark_movie_uncollected(item_information["trakt_id"])
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            trakt_id = self._get_show_id(item_information)
            TraktSyncDatabase().mark_show_collected(trakt_id, 0)

        g.container_refresh()
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30291),
        )
        g.trigger_widget_refresh()

    def _add_to_watchlist(self, item_information):
        self.trakt_api.post("sync/watchlist", self._info_to_trakt_object(item_information, True))
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30292),
        )
        g.trigger_widget_refresh()

    def _remove_from_watchlist(self, item_information):
        self.trakt_api.post("sync/watchlist/remove", self._info_to_trakt_object(item_information, True))
        g.container_refresh()
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30293),
        )
        g.trigger_widget_refresh()

    def _add_to_list(self, item_information):
        from resources.lib.modules.metadataHandler import MetadataHandler

        get = MetadataHandler.get_trakt_info
        lists = self.trakt_api.get_json("users/me/lists")
        selection = xbmcgui.Dialog().select(
            f"{g.ADDON_NAME}: {g.get_language_string(30296)}",
            [get(i, "name") for i in lists],
        )
        if selection == -1:
            return
        selection = lists[selection]
        self.trakt_api.post_json(
            f"users/me/lists/{selection['trakt_id']}/items",
            self._info_to_trakt_object(item_information, True),
        )
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30294).format(get(selection, "name")),
        )
        g.trigger_widget_refresh()

    def _remove_from_list(self, item_information):
        from resources.lib.modules.metadataHandler import MetadataHandler

        get = MetadataHandler.get_trakt_info
        lists = self.trakt_api.get_json("users/me/lists")
        selection = xbmcgui.Dialog().select(
            f"{g.ADDON_NAME}: {g.get_language_string(30296)}",
            [get(i, "name") for i in lists],
        )
        if selection == -1:
            return
        selection = lists[selection]
        self.trakt_api.post_json(
            f'users/me/lists/{selection["trakt_id"]}/items/remove', self._info_to_trakt_object(item_information, True)
        )

        g.container_refresh()
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30286)}",
            g.get_language_string(30295).format(get(selection, "name")),
        )
        g.trigger_widget_refresh()

    def _hide_item(self, item_information):
        from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase

        if item_information['mediatype'] == "movie":
            section = "calendar"
            sections_display = [g.get_language_string(30298)]
            selection = 0
        else:
            sections_display = [g.get_language_string(30297), g.get_language_string(30298)]
            selection = xbmcgui.Dialog().select(
                f"{g.ADDON_NAME}: {g.get_language_string(30299)}",
                sections_display,
            )
            if selection == -1:
                return
            sections = ["progress_watched", "calendar"]
            section = sections[selection]

        self.trakt_api.post_json(
            f"users/hidden/{section}",
            self._info_to_trakt_object(item_information, True),
        )

        if item_information['mediatype'] == "movie":
            TraktSyncDatabase().add_hidden_item(item_information['trakt_id'], "movie", section)
        else:
            TraktSyncDatabase().add_hidden_item(
                item_information.get("trakt_show_id", item_information['trakt_id']), "tvshow", section
            )

        g.container_refresh()
        g.notification(
            g.ADDON_NAME,
            g.get_language_string(30300).format(sections_display[selection]),
        )
        g.trigger_widget_refresh()

    def _remove_playback_history(self, item_information):
        media_type = "episode" if item_information["mediatype"] != "movie" else "movie"
        progress = self.trakt_api.get_json(f"sync/playback/{media_type}s")
        if len(progress) == 0:
            return
        if media_type == "movie":
            progress_ids = [i["playback_id"] for i in progress if i["trakt_id"] == item_information["trakt_id"]]
        else:
            progress_ids = [
                i["playback_id"] for i in progress if i["episode"]["trakt_id"] == item_information["trakt_id"]
            ]

        for i in progress_ids:
            self.trakt_api.delete_request(f"sync/playback/{i}")

        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase

        TraktSyncDatabase().remove_bookmark(item_information["trakt_id"])

        g.container_refresh()
        g.notification(g.ADDON_NAME, g.get_language_string(30301))
        g.trigger_widget_refresh()
