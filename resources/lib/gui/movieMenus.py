# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import datetime

import xbmc
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
        ][: self.page_limit]
        self.list_builder.movie_menu_builder(bookmarked_items)

    @staticmethod
    def discover_movies():
        g.add_directory_item(
            g.get_language_string(30004),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="popular",
            description=g.get_language_string(30429),
        )
        g.add_directory_item(
            g.get_language_string(30380),
            action="moviePopularRecent",
            description=g.get_language_string(30430),
        )
        if g.get_setting("trakt.auth"):
            g.add_directory_item(
                g.get_language_string(30005),
                action="moviesRecommended",
                description=g.get_language_string(30431),
            )
        g.add_directory_item(
            g.get_language_string(30006),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="trending",
            description=g.get_language_string(30432),
        )
        g.add_directory_item(
            g.get_language_string(30381),
            action="movieTrendingRecent",
            description=g.get_language_string(30433),
        )
        g.add_directory_item(
            g.get_language_string(30007),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="played",
            description=g.get_language_string(30434),
        )
        g.add_directory_item(
            g.get_language_string(30008),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="watched",
            description=g.get_language_string(30435),
        )
        g.add_directory_item(
            g.get_language_string(30009),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="collected",
            description=g.get_language_string(30436),
        )
        g.add_directory_item(
            g.get_language_string(30386),
            action="TrendingLists",
            mediatype="movies",
            description=g.get_language_string(30437),
        )
        g.add_directory_item(
            g.get_language_string(30388),
            action="PopularLists",
            mediatype="movies",
            description=g.get_language_string(30438),
        )
        if not g.get_bool_setting("general.hideUnAired"):
            g.add_directory_item(
                g.get_language_string(30010),
                action="genericEndpoint",
                mediatype="movies",
                endpoint="anticipated",
                description=g.get_language_string(30439),
            )
        g.add_directory_item(
            g.get_language_string(30012),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="boxoffice",
            description=g.get_language_string(30440),
        )
        g.add_directory_item(
            g.get_language_string(30011),
            action="moviesUpdated",
            description=g.get_language_string(30441),
        )
        g.add_directory_item(
            g.get_language_string(30043),
            action="movieGenres",
            description=g.get_language_string(30442),
        )
        g.add_directory_item(
            g.get_language_string(30188),
            action="movieYears",
            description=g.get_language_string(30443),
        )
        g.add_directory_item(
            g.get_language_string(30212),
            action="movieByActor",
            description=g.get_language_string(30408),
        )
        if not g.get_bool_setting("searchHistory"):
            g.add_directory_item(
                g.get_language_string(30013),
                action="moviesSearch",
                description=g.get_language_string(30404),
            )
        else:
            g.add_directory_item(
                g.get_language_string(30013),
                action="moviesSearchHistory",
                description=g.get_language_string(30406),
            )
        g.close_directory(g.CONTENT_FOLDER)

    @staticmethod
    @trakt_auth_guard
    def my_movies():
        g.add_directory_item(
            g.get_language_string(30044),
            action="onDeckMovies",
            description=g.get_language_string(30444),
        )
        g.add_directory_item(
            g.get_language_string(30014),
            action="moviesMyCollection",
            description=g.get_language_string(30445),
        )
        g.add_directory_item(
            g.get_language_string(30015),
            action="moviesMyWatchlist",
            description=g.get_language_string(30446),
        )
        g.add_directory_item(
            g.get_language_string(30045),
            action="myTraktLists",
            mediatype="movies",
            description=g.get_language_string(30447),
        )
        g.add_directory_item(
            g.get_language_string(30384),
            action="myLikedLists",
            mediatype="movies",
            description=g.get_language_string(30448),
        )
        g.add_directory_item(
            g.get_language_string(30357),
            action="myWatchedMovies",
            description=g.get_language_string(30449),
        )
        g.close_directory(g.CONTENT_FOLDER)

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

        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime("%Y-%m-%d")
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/updates/{}".format(date), page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    @staticmethod
    def movies_search_history():
        history = SearchHistory().get_search_history("movie")
        g.add_directory_item(
            g.get_language_string(30203),
            action="moviesSearch",
            description=g.get_language_string(30404),
        )
        g.add_directory_item(
            g.get_language_string(30202),
            action="clearSearchHistory",
            mediatype="movie",
            is_folder=False,
            description=g.get_language_string(30414),
        )

        for i in history:
            g.add_directory_item(i, action="moviesSearchResults", action_args=i)
        g.close_directory(g.CONTENT_FOLDER)

    def movies_search(self, query=None):
        if query is None:
            k = xbmc.Keyboard("", g.get_language_string(30013))
            k.doModal()
            query = k.getText() if k.isConfirmed() else None
            del k
            if not query:
                g.cancel_directory()
                return

        query = g.decode_py2(query)
        if g.get_bool_setting("searchHistory"):
            SearchHistory().add_search_history("movie", query)
        query = g.deaccent_string(g.display_string(query))
        query = tools.quote(query)

        self.movies_search_results(query)

    def movies_search_results(self, query):
        trakt_list = self.trakt.get_json_paged(
            "search/movie", query=tools.unquote(query), extended="full", page=g.PAGE
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
        g.close_directory(g.CONTENT_FOLDER)

    def movie_years_results(self, year):
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/popular", years=year, page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    def movies_by_actor(self, actor):
        if actor is None:
            k = xbmc.Keyboard("", g.get_language_string(30013))
            k.doModal()
            query = k.getText() if k.isConfirmed() else None
            if not query:
                g.cancel_directory()
                return
        else:
            query = tools.unquote(actor)

        if g.get_bool_setting("searchHistory"):
            SearchHistory().add_search_history("movieActor", query)
        query = g.deaccent_string(query)
        query = query.replace(" ", "-")
        query = tools.quote_plus(query)

        self.list_builder.movie_menu_builder(
            self.trakt.get_json_paged(
                "people/{}/movies".format(query), extended="full", page=g.PAGE
            ),
            hide_watched=False,
            hide_unaired=False,
        )

    def movies_genres(self):
        g.add_directory_item(g.get_language_string(30046), action="movieGenresGet")
        genres = self.trakt.get_json("genres/movies")
        if genres is None:
            g.cancel_directory()
            return
        for i in genres:
            g.add_directory_item(
                i["name"], action="movieGenresGet", action_args=i["slug"]
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
            genres = self.trakt.get_json("genres/movies")
            for genre in genres:
                genre_display_list.append(genre["name"])
            genre_multiselect = xbmcgui.Dialog().multiselect(
                "{}: {}".format(g.ADDON_NAME, g.get_language_string(30330)),
                genre_display_list,
            )
            if genre_multiselect is None:
                return
            genre_string = ",".join([genres[i]["slug"] for i in genre_multiselect])
        else:
            genre_string = tools.unquote(args)

        trakt_list = self.trakt.get_json_cached(
            "movies/{}".format(trakt_endpoint),
            genres=genre_string,
            page=g.PAGE,
            extended="full",
        )
        self.list_builder.movie_menu_builder(trakt_list)

    @trakt_auth_guard
    def my_watched_movies(self):
        watched_movies = movies.TraktSyncDatabase().get_watched_movies(g.PAGE)
        self.list_builder.movie_menu_builder(watched_movies)
