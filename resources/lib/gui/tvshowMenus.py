# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import datetime

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.common import tools
from resources.lib.database.searchHistory import SearchHistory
from resources.lib.database.trakt_sync import bookmark, hidden, shows
from resources.lib.database.trakt_sync.shows import TraktSyncDatabase
from resources.lib.indexers.trakt import TraktAPI, trakt_auth_guard
from resources.lib.modules.globals import g
from resources.lib.modules.list_builder import ListBuilder


class Menus:
    def __init__(self):
        self.trakt = TraktAPI()
        self.language_code = g.get_language_code()
        self.trakt_database = TraktSyncDatabase()
        self.hidden_database = hidden.TraktSyncDatabase()
        self.bookmark_database = bookmark.TraktSyncDatabase()
        self.shows_database = shows.TraktSyncDatabase()
        self.list_builder = ListBuilder()
        self.page_limit = g.get_int_setting("item.limit")

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
        ][: self.page_limit]
        self.list_builder.mixed_episode_builder(bookmarked_items)

    @staticmethod
    def discover_shows():

        g.add_directory_item(
            g.get_language_string(30004),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="popular",
            description=g.get_language_string(30450),
        )
        g.add_directory_item(
            g.get_language_string(30378),
            action="showsPopularRecent",
            description=g.get_language_string(30451),
        )
        if g.get_setting("trakt.auth"):
            g.add_directory_item(
                g.get_language_string(30005),
                action="showsRecommended",
                description=g.get_language_string(30452),
            )
        g.add_directory_item(
            g.get_language_string(30006),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="trending",
            description=g.get_language_string(30453),
        )
        g.add_directory_item(
            g.get_language_string(30379),
            action="showsTrendingRecent",
            description=g.get_language_string(30454),
        )
        g.add_directory_item(
            g.get_language_string(30047),
            action="showsNew",
            description=g.get_language_string(30455),
        )
        g.add_directory_item(
            g.get_language_string(30007),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="played",
            description=g.get_language_string(30456),
        )
        g.add_directory_item(
            g.get_language_string(30008),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="watched",
            description=g.get_language_string(30457),
        )
        g.add_directory_item(
            g.get_language_string(30009),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="collected",
            description=g.get_language_string(30458),
        )
        g.add_directory_item(
            g.get_language_string(30385),
            action="TrendingLists",
            mediatype="shows",
            description=g.get_language_string(30459),
        )
        g.add_directory_item(
            g.get_language_string(30387),
            action="PopularLists",
            mediatype="shows",
            description=g.get_language_string(30460),
        )
        if not g.get_bool_setting("general.hideUnAired"):
            g.add_directory_item(
                g.get_language_string(30010),
                action="genericEndpoint",
                mediatype="shows",
                endpoint="anticipated",
                description=g.get_language_string(30461),
            )

        g.add_directory_item(
            g.get_language_string(30011),
            action="showsUpdated",
            description=g.get_language_string(30462),
        )
        g.add_directory_item(
            g.get_language_string(30186),
            action="showsNetworks",
            description=g.get_language_string(30463),
        )
        g.add_directory_item(
            g.get_language_string(30188),
            action="showYears",
            description=g.get_language_string(30464),
        )
        g.add_directory_item(
            g.get_language_string(30043),
            action="tvGenres",
            description=g.get_language_string(30465),
        )
        g.add_directory_item(
            g.get_language_string(30212),
            action="showsByActor",
            description=g.get_language_string(30466),
        )
        if not g.get_bool_setting("searchHistory"):
            g.add_directory_item(
                g.get_language_string(30013),
                action="showsSearch",
                description=g.get_language_string(30405),
            )
        else:
            g.add_directory_item(
                g.get_language_string(30013),
                action="showsSearchHistory",
                description=g.get_language_string(30407),
            )
        g.close_directory(g.CONTENT_FOLDER)

    @staticmethod
    @trakt_auth_guard
    def my_shows():
        g.add_directory_item(
            g.get_language_string(30044),
            action="onDeckShows",
            description=g.get_language_string(30467),
        )
        g.add_directory_item(
            g.get_language_string(30014),
            action="showsMyCollection",
            description=g.get_language_string(30468),
        )
        g.add_directory_item(
            g.get_language_string(30015),
            action="showsMyWatchlist",
            description=g.get_language_string(30469),
        )
        g.add_directory_item(
            g.get_language_string(30096),
            action="showsRecentlyWatched",
            description=g.get_language_string(30519),
        )
        g.add_directory_item(
            g.get_language_string(30232),
            action="showsNextUp",
            description=g.get_language_string(30470),
        )
        g.add_directory_item(
            g.get_language_string(30233),
            action="myUpcomingEpisodes",
            description=g.get_language_string(30471),
        )
        g.add_directory_item(
            g.get_language_string(30234),
            action="showsMyProgress",
            description=g.get_language_string(30472),
        )
        g.add_directory_item(
            g.get_language_string(30235),
            action="showsMyRecentEpisodes",
            description=g.get_language_string(30473),
        )
        g.add_directory_item(
            g.get_language_string(30236),
            action="myTraktLists",
            mediatype="shows",
            description=g.get_language_string(30474),
        )
        g.add_directory_item(
            g.get_language_string(30383),
            action="myLikedLists",
            mediatype="shows",
            description=g.get_language_string(30475),
        )
        g.add_directory_item(
            g.get_language_string(30356),
            action="myWatchedEpisodes",
            description=g.get_language_string(30476),
        )
        g.close_directory(g.CONTENT_FOLDER)

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
        paginate = not g.get_bool_setting("general.paginatecollection")
        sort = "title" if paginate else False
        trakt_list = self.trakt_database.get_collected_shows(g.PAGE)
        self.list_builder.show_list_builder(trakt_list, no_paging=paginate, sort=sort)

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
        trakt_list = self.trakt_database.get_unfinished_collected_shows(g.PAGE)
        self.list_builder.show_list_builder(trakt_list)

    @trakt_auth_guard
    def shows_recommended(self):
        trakt_list = self.shows_database.extract_trakt_page(
            "recommendations/shows", ignore_collected=True, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    def shows_new(self):
        hidden_items = self.hidden_database.get_hidden_items("recommendations", "shows")
        date_string = datetime.datetime.today() - datetime.timedelta(days=29)
        trakt_list = self.trakt.get_json(
            "calendars/all/shows/new/{}/30".format(date_string.strftime("%d-%m-%Y")),
            languages=','.join({'en', self.language_code}),
            extended="full",
        )
        trakt_list = [i.get("show") for i in trakt_list if i["trakt_show_id"] not in hidden_items]
        self.list_builder.show_list_builder(trakt_list, no_paging=True)

    def shows_recently_watched(self):
        self.list_builder.show_list_builder(
            self.trakt_database.get_recently_watched_shows()
        )

    def my_next_up(self):
        episodes = self.trakt_database.get_nextup_episodes(
            g.get_int_setting("nextup.sort") == 1
        )
        self.list_builder.mixed_episode_builder(episodes, no_paging=True)

    @trakt_auth_guard
    def my_recent_episodes(self):
        hidden_shows = self.hidden_database.get_hidden_items("calendar", "shows")
        date_string = datetime.datetime.today() - datetime.timedelta(days=13)
        trakt_list = self.trakt.get_json(
            "calendars/my/shows/{}/14".format(
                date_string.strftime("%d-%m-%Y"), extended="full"
            )
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
            "%Y-%m-%d"
        )
        upcoming_episodes = self.trakt.get_json(
            "calendars/my/shows/{}/30".format(tomorrow), extended="full"
        )[: self.page_limit]
        self.list_builder.mixed_episode_builder(
            upcoming_episodes,
            prepend_date=True,
            no_paging=True,
            hide_unaired=False
        )

    def shows_networks(self):
        trakt_list = self.trakt.get_json_cached("networks")
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
        g.close_directory(g.CONTENT_FOLDER)

    def shows_networks_results(self, network):
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/popular", networks=network, page=g.PAGE, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)
        g.close_directory(g.CONTENT_SHOW)

    def shows_updated(self):
        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime("%Y-%m-%d")
        trakt_list = self.trakt.get_json(
            "shows/updates/{}".format(date), extended="full"
        )
        self.list_builder.show_list_builder(trakt_list, no_paging=True)

    @staticmethod
    def shows_search_history():
        history = SearchHistory().get_search_history("tvshow")
        g.add_directory_item(
            g.get_language_string(30204),
            action="showsSearch",
            description=g.get_language_string(30405),
        )
        g.add_directory_item(
            g.get_language_string(30202),
            action="clearSearchHistory",
            mediatype="tvshow",
            is_folder=False,
            description=g.get_language_string(30202),
        )
        for i in history:
            g.add_directory_item(
                i,
                action="showsSearchResults",
                action_args=tools.construct_action_args(i),
            )
        g.close_directory(g.CONTENT_FOLDER)

    def shows_search(self, query=None):
        if not query:
            k = xbmc.Keyboard("", g.get_language_string(30013))
            k.doModal()
            query = k.getText() if k.isConfirmed() else None
            del k
            if not query:
                g.cancel_directory()
                return

        query = g.decode_py2(query)
        if g.get_bool_setting("searchHistory"):
            SearchHistory().add_search_history("tvshow", query)
        query = g.deaccent_string(g.display_string(query))
        self.shows_search_results(query)

    def shows_search_results(self, query):
        trakt_list = self.trakt.get_json_paged(
            "search/show",
            query=tools.unquote(query),
            page=g.PAGE,
            extended="full",
            field="title",
        )
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(
            [
                show
                for show in trakt_list
                if float(show["trakt_object"]["info"]["score"]) > 0
            ]
        )

    def shows_by_actor(self, actor):
        if not actor:
            k = xbmc.Keyboard("", g.get_language_string(30013))
            k.doModal()
            query = k.getText() if k.isConfirmed() else None
            del k
            if not query:
                g.cancel_directory()
                return
        else:
            query = tools.unquote(actor)

        if g.get_bool_setting("searchHistory"):
            SearchHistory().add_search_history("showActor", query)
        query = g.deaccent_string(query)
        query = query.replace(" ", "-")
        query = tools.quote_plus(query)

        self.list_builder.show_list_builder(
            self.trakt.get_json_paged(
                "people/{}/shows".format(query), extended="full", page=g.PAGE
            ),
            hide_watched=False,
            hide_unaired=False,
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
        g.add_directory_item(g.get_language_string(30046), action="showGenresGet")
        genres = self.trakt.get_json_cached("genres/shows", extended="full")

        if genres is None:
            g.cancel_directory()
            return

        for i in genres:
            g.add_directory_item(
                i["name"], action="showGenresGet", action_args=i["slug"]
            )
        g.close_directory(g.CONTENT_GENRES)

    def shows_genre_list(self, args):
        trakt_endpoint = (
            "trending"
            if g.get_int_setting("general.genres.endpoint") == 0
            else "popular"
        )
        if args is None:
            genre_display_list = []
            genre_string = ""
            genres = self.trakt.get_json_cached("genres/shows")

            for genre in genres:
                genre_display_list.append(genre["name"])
            genre_multiselect = xbmcgui.Dialog().multiselect(
                "{}: {}".format(g.ADDON_NAME, g.get_language_string(30330)),
                genre_display_list,
            )

            if genre_multiselect is None:
                return
            for selection in genre_multiselect:
                genre_string += ", {}".format(genres[selection]["slug"])
            genre_string = genre_string[2:]

        else:
            genre_string = args

        trakt_list = self.shows_database.extract_trakt_page(
            "shows/{}".format(trakt_endpoint),
            genres=genre_string,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return

        self.list_builder.show_list_builder(trakt_list)

    def shows_related(self, args):
        trakt_list = self.trakt.get_json(
            "shows/{}/related".format(args), extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    def shows_years(self, year=None):
        if year is None:
            current_year = int(
                tools.parse_datetime(
                    datetime.datetime.today().strftime("%Y-%m-%d")
                ).year
            )
            all_years = reversed([year for year in range(1900, current_year + 1)])
            menu_items = []
            for year in all_years:
                menu_items.append(
                    g.add_directory_item(
                        str(year), action="showYears", action_args=year, bulk_add=True
                    )
                )
            xbmcplugin.addDirectoryItems(g.PLUGIN_HANDLE, menu_items, len(menu_items))
            g.close_directory(g.CONTENT_SHOW)
        else:
            trakt_list = self.trakt.get_json(
                "shows/popular", years=year, page=g.PAGE, extended="full"
            )
            self.list_builder.show_list_builder(trakt_list)

    @trakt_auth_guard
    def my_watched_episode(self):
        watched_episodes = self.trakt_database.get_watched_episodes(g.PAGE)
        self.list_builder.mixed_episode_builder(watched_episodes)
