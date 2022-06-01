# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import datetime

import xbmcgui
import xbmcplugin

from resources.lib.common import tools
from resources.lib.common.tools import cached_property
from resources.lib.indexers import trakt_auth_guard
from resources.lib.modules.globals import g


class Menus(object):
    def __init__(self):
        self.page_limit = g.get_int_setting("item.limit")
        self.page_start = (g.PAGE - 1) * self.page_limit
        self.page_end = g.PAGE * self.page_limit

    # Cached properties to lazy load imports

    @cached_property
    def shows_database(self):
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase
        return TraktSyncDatabase()

    @cached_property
    def search_history(self):
        from resources.lib.database.searchHistory import SearchHistory
        return SearchHistory()

    @cached_property
    def hidden_database(self):
        from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase as HiddenDatabase
        return HiddenDatabase()

    @cached_property
    def bookmark_database(self):
        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase as BookmarkDatabase
        return BookmarkDatabase()

    @cached_property
    def trakt_api(self):
        from resources.lib.indexers.trakt import TraktAPI
        return TraktAPI()

    @cached_property
    def list_builder(self):
        from resources.lib.modules.list_builder import ListBuilder
        return ListBuilder()

    ######################################################
    # MENUS
    ######################################################

    @trakt_auth_guard
    def on_deck_shows(self):
        hidden_shows = self.hidden_database.get_hidden_items(
            "progress_watched", "tvshow"
        )
        bookmarked_items = [
                               i
                               for i in self.bookmark_database.get_all_bookmark_items("episode")
                               if i["trakt_show_id"] not in hidden_shows
                           ][self.page_start:self.page_end]
        self.list_builder.mixed_episode_builder(bookmarked_items)

    @staticmethod
    def discover_shows():

        g.add_directory_item(
            g.get_language_string(30004),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="popular",
            description=g.get_language_string(30416),
        )
        g.add_directory_item(
            g.get_language_string(30345),
            action="showsPopularRecent",
            description=g.get_language_string(30417),
        )
        if g.get_setting("trakt.auth"):
            g.add_directory_item(
                g.get_language_string(30005),
                action="showsRecommended",
                description=g.get_language_string(30418),
            )
        g.add_directory_item(
            g.get_language_string(30006),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="trending",
            description=g.get_language_string(30419),
        )
        g.add_directory_item(
            g.get_language_string(30346),
            action="showsTrendingRecent",
            description=g.get_language_string(30420),
        )
        g.add_directory_item(
            g.get_language_string(30046),
            action="showsNew",
            description=g.get_language_string(30421),
        )
        g.add_directory_item(
            g.get_language_string(30007),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="played",
            description=g.get_language_string(30422),
        )
        g.add_directory_item(
            g.get_language_string(30008),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="watched",
            description=g.get_language_string(30423),
        )
        g.add_directory_item(
            g.get_language_string(30009),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="collected",
            description=g.get_language_string(30424),
        )
        g.add_directory_item(
            g.get_language_string(30352),
            action="TrendingLists",
            mediatype="shows",
            description=g.get_language_string(30425),
        )
        g.add_directory_item(
            g.get_language_string(30354),
            action="PopularLists",
            mediatype="shows",
            description=g.get_language_string(30426),
        )
        if not g.get_bool_setting("general.hideUnAired"):
            g.add_directory_item(
                g.get_language_string(30010),
                action="genericEndpoint",
                mediatype="shows",
                endpoint="anticipated",
                description=g.get_language_string(30427),
            )

        g.add_directory_item(
            g.get_language_string(30011),
            action="showsUpdated",
            description=g.get_language_string(30428),
        )
        g.add_directory_item(
            g.get_language_string(30169),
            action="showsNetworks",
            description=g.get_language_string(30429),
        )
        g.add_directory_item(
            g.get_language_string(30171),
            action="showYears",
            description=g.get_language_string(30430),
        )
        g.add_directory_item(
            g.get_language_string(30042),
            action="tvGenres",
            description=g.get_language_string(30431),
        )
        g.add_directory_item(
            g.get_language_string(30190),
            action="showsByActor",
            description=g.get_language_string(30432),
        )
        if not g.get_bool_setting("searchHistory"):
            g.add_directory_item(
                g.get_language_string(30013),
                action="showsSearch",
                description=g.get_language_string(30372),
            )
        else:
            g.add_directory_item(
                g.get_language_string(30013),
                action="showsSearchHistory",
                description=g.get_language_string(30374),
            )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    @trakt_auth_guard
    def my_shows():
        g.add_directory_item(
            g.get_language_string(30043),
            action="onDeckShows",
            description=g.get_language_string(30433),
        )
        g.add_directory_item(
            g.get_language_string(30014),
            action="showsMyCollection",
            description=g.get_language_string(30434),
        )
        g.add_directory_item(
            g.get_language_string(30015),
            action="showsMyWatchlist",
            description=g.get_language_string(30435),
        )
        g.add_directory_item(
            g.get_language_string(30090),
            action="showsRecentlyWatched",
            description=g.get_language_string(30479),
        )
        g.add_directory_item(
            g.get_language_string(30210),
            action="showsNextUp",
            description=g.get_language_string(30436),
        )
        g.add_directory_item(
            g.get_language_string(30211),
            action="myUpcomingEpisodes",
            description=g.get_language_string(30437),
        )
        g.add_directory_item(
            g.get_language_string(30212),
            action="showsMyProgress",
            description=g.get_language_string(30438),
        )
        g.add_directory_item(
            g.get_language_string(30213),
            action="showsMyRecentEpisodes",
            description=g.get_language_string(30439),
        )
        g.add_directory_item(
            g.get_language_string(30214),
            action="myTraktLists",
            mediatype="shows",
            description=g.get_language_string(30440),
        )
        g.add_directory_item(
            g.get_language_string(30350),
            action="myLikedLists",
            mediatype="shows",
            description=g.get_language_string(30441),
        )
        g.add_directory_item(
            g.get_language_string(30325),
            action="myWatchedEpisodes",
            description=g.get_language_string(30442),
        )
        g.close_directory(g.CONTENT_MENU)

    def generic_endpoint(self, endpoint):
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/{}".format(endpoint), page=g.PAGE, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    def shows_popular_recent(self):
        year_range = "{}-{}".format(
            datetime.datetime.now().year - 1, datetime.datetime.now().year
        )
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/popular", years=year_range, page=g.PAGE, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    def shows_trending_recent(self):
        year_range = "{}-{}".format(
            datetime.datetime.now().year - 1, datetime.datetime.now().year
        )
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/trending", years=year_range, page=g.PAGE, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    @trakt_auth_guard
    def my_shows_collection(self):
        no_paging = not g.get_bool_setting("general.paginatecollection")
        sort = "title" if g.get_int_setting("general.sortcollection") == 1 else False
        trakt_list = self.shows_database.get_collected_shows(g.PAGE)
        if sort == "title" and not no_paging:
            trakt_list = sorted(trakt_list, key=lambda k: tools.SORT_TOKEN_REGEX
                                .sub("", k["trakt_object"]["info"].get('title').lower()))
            offset = (g.PAGE - 1) * self.page_limit
            trakt_list = trakt_list[offset:offset + self.page_limit]
        self.list_builder.show_list_builder(trakt_list, no_paging=no_paging, sort=sort)

    @trakt_auth_guard
    def my_shows_watchlist(self):
        paginate = not g.get_bool_setting("general.paginatetraktlists")
        trakt_list = self.shows_database.extract_trakt_page(
            "users/me/watchlist/shows",
            extended="full",
            page=g.PAGE,
            ignore_cache=True,
            no_paging=paginate,
            pull_all=True,
        )
        self.list_builder.show_list_builder(trakt_list, no_paging=paginate)

    @trakt_auth_guard
    def my_show_progress(self):
        no_paging = not g.get_bool_setting("general.paginatecollection")
        sort = "title" if g.get_int_setting("general.sortcollection") == 1 else False
        trakt_list = self.shows_database.get_unfinished_collected_shows(g.PAGE)
        if sort == "title" and not no_paging:
            trakt_list = sorted(trakt_list, key=lambda k: tools.SORT_TOKEN_REGEX
                                .sub("", k["trakt_object"]["info"].get('title').lower()))
            offset = (g.PAGE - 1) * self.page_limit
            trakt_list = trakt_list[offset:offset + self.page_limit]
        self.list_builder.show_list_builder(trakt_list, no_paging=no_paging, sort=sort)

    @trakt_auth_guard
    def shows_recommended(self):
        trakt_list = self.shows_database.extract_trakt_page(
            "recommendations/shows", ignore_collected=True, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    def shows_new(self):
        hidden_items = self.hidden_database.get_hidden_items("recommendations", "shows")
        date_string = datetime.datetime.today() - datetime.timedelta(days=29)
        trakt_list = self.shows_database.extract_trakt_page(
            "calendars/all/shows/new/{}/30".format(date_string.strftime("%d-%m-%Y")),
            languages=','.join({'en', g.get_language_code()}),
            extended="full",
            pull_all=True,
            no_paging=True,
            ignore_cache=True,
            hide_watched=False,
            hide_unaired=False
        )
        trakt_list = [i for i in trakt_list if i["trakt_id"] not in hidden_items][:self.page_limit]
        self.list_builder.show_list_builder(trakt_list, no_paging=True)

    def shows_recently_watched(self):
        self.list_builder.show_list_builder(
            self.shows_database.get_recently_watched_shows(),
            no_paging=True
        )

    def my_next_up(self):
        episodes = self.shows_database.get_nextup_episodes(
            g.get_int_setting("nextup.sort") == 1
        )
        self.list_builder.mixed_episode_builder(episodes, no_paging=True)

    @trakt_auth_guard
    def my_recent_episodes(self):
        hidden_shows = self.hidden_database.get_hidden_items("calendar", "shows")
        date_string = datetime.datetime.today() - datetime.timedelta(days=13)
        trakt_list = self.trakt_api.get_json(
            "calendars/my/shows/{}/14".format(
                date_string.strftime("%d-%m-%Y")
            ),
            extended="full",
            pull_all=True
        )
        trakt_list = sorted(
            [i for i in trakt_list if i["trakt_show_id"] not in hidden_shows],
            key=lambda t: t["first_aired"],
            reverse=True,
        )

        self.list_builder.mixed_episode_builder(trakt_list)

    @trakt_auth_guard
    def my_upcoming_episodes(self):
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime(
            g.DATE_FORMAT
        )
        upcoming_episodes = self.trakt_api.get_json(
            "calendars/my/shows/{}/30".format(tomorrow),
            extended="full",
            pull_all=True
        )[: self.page_limit]
        self.list_builder.mixed_episode_builder(
            upcoming_episodes,
            prepend_date=True,
            no_paging=True,
            hide_unaired=False
        )

    def shows_networks(self):
        trakt_list = self.trakt_api.get_json_cached("networks")
        list_items = []
        for i in trakt_list:
            list_items.append(
                g.add_directory_item(
                    i["name"],
                    action="showsNetworkShows",
                    action_args=i["name"],
                    bulk_add=True,
                )
            )
        xbmcplugin.addDirectoryItems(g.PLUGIN_HANDLE, list_items, len(list_items))
        g.close_directory(g.CONTENT_MENU)

    def shows_networks_results(self, network):
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/popular", networks=network, page=g.PAGE, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)
        g.close_directory(g.CONTENT_SHOW)

    def shows_updated(self):
        date = datetime.date.today() - datetime.timedelta(days=29)
        date = date.strftime(g.DATE_FORMAT)
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/updates/{}".format(date),
            extended="full",
            ignore_cache=True,
            hide_watched=False,
            hide_unaired=False
        )
        self.list_builder.show_list_builder(trakt_list, no_paging=True)

    def shows_search_history(self):
        history = self.search_history.get_search_history("tvshow")
        g.add_directory_item(
            g.get_language_string(30182),
            action="showsSearch",
            description=g.get_language_string(30372),
        )
        g.add_directory_item(
            g.get_language_string(30180),
            action="clearSearchHistory",
            mediatype="tvshow",
            is_folder=False,
            description=g.get_language_string(30180),
        )
        for i in history:
            remove_path = g.create_url(
                g.BASE_URL,
                {"action": "removeSearchHistory", "mediatype": "tvshow", "endpoint": i},
            )
            g.add_directory_item(
                i,
                action="showsSearchResults",
                action_args=tools.construct_action_args(i),
                cm=[
                    (g.get_language_string(30565), "RunPlugin({})".format(remove_path))
                ],
            )
        g.close_directory(g.CONTENT_MENU)

    def shows_search(self, query=None):
        if not query:
            query = g.get_keyboard_input(g.get_language_string(30013))
            if not query:
                g.cancel_directory()
                return

        if g.get_bool_setting("searchHistory"):
            self.search_history.add_search_history("tvshow", query)
        self.shows_search_results(query)

    def shows_search_results(self, query):
        trakt_list = self.shows_database.extract_trakt_page(
            "search/show",
            query=query,
            page=g.PAGE,
            extended="full",
            field="title",
            hide_unaired=False,
            hide_watched=False
        )

        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(
            [
                show
                for show in trakt_list
                if float(show["trakt_object"]["info"]["score"]) > 0
            ],
            hide_unaired=False,
            hide_watched=False
        )

    def shows_by_actor(self, query):
        if not query:
            query = g.get_keyboard_input(g.get_language_string(30013))
            if not query:
                g.cancel_directory()
                return

        if g.get_bool_setting("searchHistory"):
            self.search_history.add_search_history("showActor", query)

        query = g.transliterate_string(query)
        # Try to deal with transliterated chinese actor names as some character -> word transliterations can be joined
        # I have no idea of the rules and it could well be arbitrary
        # This approach will only work if only one pair of adjoining transliterated chars are joined
        name_parts = query.split()
        for i in range(len(name_parts), 0, -1):
            query = "-".join(name_parts[:i]) + "-".join(name_parts[i:i + 1])
            query = tools.quote_plus(query)

            trakt_list = self.shows_database.extract_trakt_page(
                    "people/{}/shows".format(query),
                    extended="full",
                    page=g.PAGE,
                    hide_watched=False,
                    hide_unaired=False,
            )
            if not trakt_list:
                continue
            else:
                break

        try:
            if not trakt_list or 'trakt_id' not in trakt_list[0]:
                raise KeyError
        except KeyError:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list,
                                            hide_watched=False,
                                            hide_unaired=False
                                            )

    def show_seasons(self, args):
        self.list_builder.season_list_builder(args["trakt_id"], no_paging=True)

    def season_episodes(self, args):
        self.list_builder.episode_list_builder(
            args["trakt_show_id"], args["trakt_id"], no_paging=True
        )

    def flat_episode_list(self, args):
        self.list_builder.episode_list_builder(args["trakt_id"], no_paging=True)

    def shows_genres(self):
        g.add_directory_item(
            g.get_language_string(30045), action="showsGenresGet",
            menu_item={
                "art": dict.fromkeys(
                    ['icon', 'poster', 'thumb', 'fanart'], g.GENRES_PATH + "list.png"
                )
            }
        )
        genres = self.trakt_api.get_json_cached("genres/shows", extended="full")

        if genres is None:
            g.cancel_directory()
            return

        for i in genres:
            g.add_directory_item(
                i["name"], action="showGenresGet", action_args=i["slug"],
                menu_item={
                    "art": dict.fromkeys(
                        ['icon', 'poster', 'thumb', 'fanart'], "{}{}.png".format(g.GENRES_PATH, i["slug"])
                    )
                }
            )
        g.close_directory(g.CONTENT_GENRES)

    def shows_genre_list(self, args):
        if args is None:
            genre_display_list = []
            genre_string = ""
            genres = self.trakt_api.get_json_cached("genres/shows")

            for genre in genres:
                gi = xbmcgui.ListItem(genre["name"])
                gi.setArt({"thumb": "{}{}.png".format(g.GENRES_PATH, genre["slug"])})
                genre_display_list.append(gi)
            genre_multiselect = xbmcgui.Dialog().multiselect(
                "{}: {}".format(g.ADDON_NAME, g.get_language_string(30303)),
                genre_display_list, useDetails=True
            )

            if genre_multiselect is None:
                return
            for selection in genre_multiselect:
                genre_string += ", {}".format(genres[selection]["slug"])
            genre_string = genre_string[2:]
        else:
            genre_string = tools.unquote(args)

        trakt_list = self.shows_database.extract_trakt_page(
            "shows/{}".format(
                "trending" if g.get_int_setting("general.genres.endpoint.tv") == 0 else "popular"
            ),
            genres=genre_string,
            page=g.PAGE,
            extended="full"
        )

        if trakt_list is None:
            g.cancel_directory()
            return

        self.list_builder.show_list_builder(trakt_list, next_args=genre_string)

    def shows_related(self, args):
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/{}/related".format(args), extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    def shows_years(self, year=None):
        if year is None:
            current_year = datetime.datetime.today().year
            for year in range(current_year, 1899, -1):
                g.add_directory_item(
                    g.UNICODE(year), action="showYears", action_args=year
                )
            g.close_directory(g.CONTENT_MENU)
        else:
            trakt_list = self.shows_database.extract_trakt_page(
                "shows/popular", years=year, page=g.PAGE, extended="full", hide_watched=False
            )
            self.list_builder.show_list_builder(trakt_list)

    @trakt_auth_guard
    def my_watched_episode(self):
        watched_episodes = self.shows_database.get_watched_episodes(g.PAGE)
        self.list_builder.mixed_episode_builder(watched_episodes)
