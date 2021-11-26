# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import datetime

import xbmcgui

from resources.lib.common import tools
from resources.lib.database.searchHistory import SearchHistory
from resources.lib.database.trakt_sync import movies
from resources.lib.database.trakt_sync.bookmark import (
    TraktSyncDatabase as BookmarkDatabase,
)
from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase as HiddenDatabase
from resources.lib.indexers.trakt import TraktAPI, trakt_auth_guard
from resources.lib.modules.globals import g
from resources.lib.modules.list_builder import ListBuilder


class Menus:
    def __init__(self):
        self.trakt = TraktAPI()
        self.movies_database = movies.TraktSyncDatabase()
        self.list_builder = ListBuilder()
        self.page_limit = g.get_int_setting("item.limit")
        self.page_start = (g.PAGE - 1) * self.page_limit
        self.page_end = g.PAGE * self.page_limit

    ######################################################
    # MENUS
    ######################################################

    @trakt_auth_guard
    def on_deck_movies(self):
        hidden_movies = HiddenDatabase().get_hidden_items("progress_watched", "movies")
        bookmark_sync = BookmarkDatabase()
        bookmarked_items = [
                               i
                               for i in bookmark_sync.get_all_bookmark_items("movie")
                               if i["trakt_id"] not in hidden_movies
                           ][self.page_start:self.page_end]
        self.list_builder.movie_menu_builder(bookmarked_items)

    @staticmethod
    def discover_movies():
        g.add_directory_item(
            g.get_language_string(30004),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="popular",
            description=g.get_language_string(30417),
        )
        g.add_directory_item(
            g.get_language_string(30369),
            action="moviePopularRecent",
            description=g.get_language_string(30418),
        )
        if g.get_setting("trakt.auth"):
            g.add_directory_item(
                g.get_language_string(30005),
                action="moviesRecommended",
                description=g.get_language_string(30419),
            )
        g.add_directory_item(
            g.get_language_string(30006),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="trending",
            description=g.get_language_string(30420),
        )
        g.add_directory_item(
            g.get_language_string(30370),
            action="movieTrendingRecent",
            description=g.get_language_string(30421),
        )
        g.add_directory_item(
            g.get_language_string(30007),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="played",
            description=g.get_language_string(30422),
        )
        g.add_directory_item(
            g.get_language_string(30008),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="watched",
            description=g.get_language_string(30423),
        )
        g.add_directory_item(
            g.get_language_string(30009),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="collected",
            description=g.get_language_string(30424),
        )
        g.add_directory_item(
            g.get_language_string(30375),
            action="TrendingLists",
            mediatype="movies",
            description=g.get_language_string(30425),
        )
        g.add_directory_item(
            g.get_language_string(30377),
            action="PopularLists",
            mediatype="movies",
            description=g.get_language_string(30426),
        )
        if not g.get_bool_setting("general.hideUnAired"):
            g.add_directory_item(
                g.get_language_string(30010),
                action="genericEndpoint",
                mediatype="movies",
                endpoint="anticipated",
                description=g.get_language_string(30427),
            )
        g.add_directory_item(
            g.get_language_string(30012),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="boxoffice",
            description=g.get_language_string(30428),
        )
        g.add_directory_item(
            g.get_language_string(30011),
            action="moviesUpdated",
            description=g.get_language_string(30429),
        )
        g.add_directory_item(
            g.get_language_string(30042),
            action="movieGenres",
            description=g.get_language_string(30430),
        )
        g.add_directory_item(
            g.get_language_string(30184),
            action="movieYears",
            description=g.get_language_string(30431),
        )
        g.add_directory_item(
            g.get_language_string(30203),
            action="movieByActor",
            description=g.get_language_string(30397),
        )
        if not g.get_bool_setting("searchHistory"):
            g.add_directory_item(
                g.get_language_string(30013),
                action="moviesSearch",
                description=g.get_language_string(30393),
            )
        else:
            g.add_directory_item(
                g.get_language_string(30013),
                action="moviesSearchHistory",
                description=g.get_language_string(30395),
            )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    @trakt_auth_guard
    def my_movies():
        g.add_directory_item(
            g.get_language_string(30043),
            action="onDeckMovies",
            description=g.get_language_string(30432),
        )
        g.add_directory_item(
            g.get_language_string(30014),
            action="moviesMyCollection",
            description=g.get_language_string(30433),
        )
        g.add_directory_item(
            g.get_language_string(30015),
            action="moviesMyWatchlist",
            description=g.get_language_string(30434),
        )
        g.add_directory_item(
            g.get_language_string(30044),
            action="myTraktLists",
            mediatype="movies",
            description=g.get_language_string(30435),
        )
        g.add_directory_item(
            g.get_language_string(30373),
            action="myLikedLists",
            mediatype="movies",
            description=g.get_language_string(30436),
        )
        g.add_directory_item(
            g.get_language_string(30347),
            action="myWatchedMovies",
            description=g.get_language_string(30437),
        )
        g.close_directory(g.CONTENT_MENU)

    def generic_endpoint(self, endpoint):
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/{}".format(endpoint), extended="full", page=g.PAGE
        )
        self.list_builder.movie_menu_builder(trakt_list)

    def movie_popular_recent(self):
        year_range = "{}-{}".format(
            datetime.datetime.now().year - 1, datetime.datetime.now().year
        )
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/popular", years=year_range, page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    def movie_trending_recent(self):
        year_range = "{}-{}".format(
            datetime.datetime.now().year - 1, datetime.datetime.now().year
        )
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/trending", years=year_range, page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    @trakt_auth_guard
    def my_movie_collection(self):
        paginate = not g.get_bool_setting("general.paginatecollection")
        sort = "title" if paginate else False
        self.list_builder.movie_menu_builder(
            movies.TraktSyncDatabase().get_collected_movies(g.PAGE),
            no_paging=paginate,
            sort=sort,
        )

    @trakt_auth_guard
    def my_movie_watchlist(self):
        paginate = not g.get_bool_setting("general.paginatetraktlists")
        trakt_list = self.movies_database.extract_trakt_page(
            "users/me/watchlist/movies",
            extended="full",
            page=g.PAGE,
            ignore_cache=True,
            no_paging=paginate,
            pull_all=True,
        )
        self.list_builder.movie_menu_builder(trakt_list, no_paging=paginate)

    @trakt_auth_guard
    def movies_recommended(self):
        trakt_list = self.movies_database.extract_trakt_page(
            "recommendations/movies",
            ignore_collected=True,
            extended="full",
            page=g.PAGE,
        )
        self.list_builder.movie_menu_builder(trakt_list)

    def movies_updated(self):
        import datetime

        date = datetime.date.today() - datetime.timedelta(days=29)
        date = date.strftime(g.DATE_FORMAT)
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/updates/{}".format(date), page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    @staticmethod
    def movies_search_history():
        history = SearchHistory().get_search_history("movie")
        g.add_directory_item(
            g.get_language_string(30194),
            action="moviesSearch",
            description=g.get_language_string(30393),
        )
        g.add_directory_item(
            g.get_language_string(30193),
            action="clearSearchHistory",
            mediatype="movie",
            is_folder=False,
            description=g.get_language_string(30403),
        )

        for i in history:
            g.add_directory_item(i, action="moviesSearchResults", action_args=i)
        g.close_directory(g.CONTENT_MENU)

    def movies_search(self, query=None):
        if query is None:
            query = g.get_keyboard_input(heading=g.get_language_string(30013))
            if not query:
                g.cancel_directory()
                return

        if g.get_bool_setting("searchHistory"):
            SearchHistory().add_search_history("movie", query)

        self.movies_search_results(query)

    def movies_search_results(self, query):
        trakt_list = self.movies_database.extract_trakt_page(
            "search/movie",
            query=query,
            extended="full",
            page=g.PAGE,
            hide_watched=False,
            hide_unaired=False,
        )

        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(
            [
                movie
                for movie in trakt_list
                if float(movie["trakt_object"]["info"]["score"]) > 0
            ],
            hide_watched=False,
            hide_unaired=False,
        )

    def movies_related(self, args):
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/{}/related".format(args), page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    @staticmethod
    def movies_years():
        from datetime import datetime

        year = int(datetime.today().year)
        years = []
        for i in range(year - 100, year + 1):
            years.append(i)
        years = sorted(years, reverse=True)
        [
            g.add_directory_item(str(i), action="movieYearsMovies", action_args=i)
            for i in years
        ]
        g.close_directory(g.CONTENT_MENU)

    def movie_years_results(self, year):
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/popular", years=year, page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    def movies_by_actor(self, query):
        if query is None:
            query = g.get_keyboard_input(g.get_language_string(30013))
            if not query:
                g.cancel_directory()
                return

        if g.get_bool_setting("searchHistory"):
            SearchHistory().add_search_history("movieActor", query)

        query = g.transliterate_string(query)
        # Try to deal with transliterated chinese actor names as some character -> word transliterations can be joined
        # I have no idea of the rules and it could well be arbitrary
        # This approach will only work if only one pair of adjoining transliterated chars are joined
        name_parts = query.split()
        for i in range(len(name_parts), 0, -1):
            query = "-".join(name_parts[:i]) + "-".join(name_parts[i:i + 1])
            query = tools.quote_plus(query)

            trakt_list = self.movies_database.extract_trakt_page(
                "people/{}/movies".format(query),
                extended="full",
                page=g.PAGE,
                hide_watched=False,
                hide_unaired=False
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
        self.list_builder.movie_menu_builder(trakt_list,
                                             hide_watched=False,
                                             hide_unaired=False)

    def movies_genres(self):
        g.add_directory_item(
            g.get_language_string(30045), action="movieGenresGet",
            menu_item={
                    "art": dict.fromkeys(
                        ['icon', 'poster', 'thumb', 'fanart'], g.GENRES_PATH + "list.png"
                    )
                }
        )
        genres = self.trakt.get_json_cached("genres/movies")
        if genres is None:
            g.cancel_directory()
            return
        for i in genres:
            g.add_directory_item(
                i["name"], action="movieGenresGet", action_args=i["slug"],
                menu_item={
                    "art": dict.fromkeys(
                        ['icon', 'poster', 'thumb', 'fanart'], "{}{}.png".format(g.GENRES_PATH, i["slug"])
                    )
                }
            )
        g.close_directory(g.CONTENT_GENRES)

    def movies_genre_list(self, args):
        trakt_endpoint = (
            "trending"
            if g.get_int_setting("general.genres.endpoint") == 0
            else "popular"
        )
        if args is None:
            genre_display_list = []
            genres = self.trakt.get_json_cached("genres/movies")
            for genre in genres:
                gi = xbmcgui.ListItem(genre["name"])
                gi.setArt({"thumb": "{}{}.png".format(g.GENRES_PATH, genre["slug"])})
                genre_display_list.append(gi)
            genre_multiselect = xbmcgui.Dialog().multiselect(
                "{}: {}".format(g.ADDON_NAME, g.get_language_string(30320)),
                genre_display_list, useDetails=True
            )
            if genre_multiselect is None:
                return
            genre_string = ",".join([genres[i]["slug"] for i in genre_multiselect])
        else:
            genre_string = tools.unquote(args)

        trakt_list = self.movies_database.extract_trakt_page(
            "movies/{}".format(trakt_endpoint),
            genres=genre_string,
            page=g.PAGE,
            extended="full"
        )

        if trakt_list is None:
            g.cancel_directory()
            return

        self.list_builder.movie_menu_builder(trakt_list, next_args=genre_string)

    @trakt_auth_guard
    def my_watched_movies(self):
        watched_movies = movies.TraktSyncDatabase().get_watched_movies(g.PAGE)
        self.list_builder.movie_menu_builder(watched_movies)
