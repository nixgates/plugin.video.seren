import datetime
from functools import cached_property
from urllib import parse

import xbmcgui

from resources.lib.common import tools
from resources.lib.indexers import trakt_auth_guard
from resources.lib.modules.globals import g


class Menus:
    def __init__(self):
        self.page_limit = g.get_int_setting("item.limit")
        self.page_start = (g.PAGE - 1) * self.page_limit
        self.page_end = g.PAGE * self.page_limit

    # Cached properties to lazy load imports

    @cached_property
    def movies_database(self):
        from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

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

    @staticmethod
    def discover_movies():
        g.add_directory_item(
            g.get_language_string(30004),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="popular",
            description=g.get_language_string(30395),
            menu_item=g.create_icon_dict("movies_popular", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30347),
            action="moviePopularRecent",
            description=g.get_language_string(30396),
            menu_item=g.create_icon_dict("movies_recent", g.ICONS_PATH),
        )
        if g.get_setting("trakt.auth"):
            g.add_directory_item(
                g.get_language_string(30005),
                action="moviesRecommended",
                description=g.get_language_string(30397),
                menu_item=g.create_icon_dict("movies_recommended", g.ICONS_PATH),
            )
        g.add_directory_item(
            g.get_language_string(30006),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="trending",
            description=g.get_language_string(30398),
            menu_item=g.create_icon_dict("movies_trending", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30348),
            action="movieTrendingRecent",
            description=g.get_language_string(30399),
            menu_item=g.create_icon_dict("movies_recent", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30007),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="played",
            description=g.get_language_string(30400),
            menu_item=g.create_icon_dict("movies_played", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30008),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="watched",
            description=g.get_language_string(30401),
            menu_item=g.create_icon_dict("movies_watched", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30009),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="collected",
            description=g.get_language_string(30402),
            menu_item=g.create_icon_dict("movies_collected", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30353),
            action="TrendingLists",
            mediatype="movies",
            description=g.get_language_string(30403),
            menu_item=g.create_icon_dict("list_trending", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30355),
            action="PopularLists",
            mediatype="movies",
            description=g.get_language_string(30404),
            menu_item=g.create_icon_dict("list_popular", g.ICONS_PATH),
        )
        if not g.get_bool_setting("general.hideUnAired"):
            g.add_directory_item(
                g.get_language_string(30010),
                action="genericEndpoint",
                mediatype="movies",
                endpoint="anticipated",
                description=g.get_language_string(30405),
                menu_item=g.create_icon_dict("movies_anticipated", g.ICONS_PATH),
            )
        g.add_directory_item(
            g.get_language_string(30012),
            action="genericEndpoint",
            mediatype="movies",
            endpoint="boxoffice",
            description=g.get_language_string(30406),
            menu_item=g.create_icon_dict("movies_topten", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30011),
            action="moviesUpdated",
            description=g.get_language_string(30407),
            menu_item=g.create_icon_dict("movies_recent", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30042),
            action="movieGenres",
            description=g.get_language_string(30408),
            menu_item=g.create_icon_dict("movies_genres", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30171),
            action="movieYears",
            description=g.get_language_string(30409),
            menu_item=g.create_icon_dict("movies_calendar", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30190),
            action="movieByActor",
            description=g.get_language_string(30375),
            menu_item=g.create_icon_dict("movies_actor", g.ICONS_PATH),
        )
        if not g.get_bool_setting("searchHistory"):
            g.add_directory_item(
                g.get_language_string(30013),
                action="moviesSearch",
                description=g.get_language_string(30371),
                menu_item=g.create_icon_dict("movies_search", g.ICONS_PATH),
            )
        else:
            g.add_directory_item(
                g.get_language_string(30013),
                action="moviesSearchHistory",
                description=g.get_language_string(30373),
                menu_item=g.create_icon_dict("movies_search", g.ICONS_PATH),
            )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    @trakt_auth_guard
    def my_movies():
        g.add_directory_item(
            g.get_language_string(30043),
            action="onDeckMovies",
            description=g.get_language_string(30410),
            menu_item=g.create_icon_dict("movies_progress", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30014),
            action="moviesMyCollection",
            description=g.get_language_string(30411),
            menu_item=g.create_icon_dict("movies_collected", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30015),
            action="moviesMyWatchlist",
            description=g.get_language_string(30412),
            menu_item=g.create_icon_dict("movies_watched", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30044),
            action="myTraktLists",
            mediatype="movies",
            description=g.get_language_string(30413),
            menu_item=g.create_icon_dict("list_trakt", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30351),
            action="myLikedLists",
            mediatype="movies",
            description=g.get_language_string(30414),
            menu_item=g.create_icon_dict("list_liked", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30326),
            action="myWatchedMovies",
            description=g.get_language_string(30415),
            menu_item=g.create_icon_dict("movies_watched", g.ICONS_PATH),
        )
        g.close_directory(g.CONTENT_MENU)

    def generic_endpoint(self, endpoint):
        trakt_list = self.movies_database.extract_trakt_page(f"movies/{endpoint}", extended="full", page=g.PAGE)
        self.list_builder.movie_menu_builder(trakt_list)

    def movie_popular_recent(self):
        year_range = f"{datetime.datetime.now().year - 1}-{datetime.datetime.now().year}"
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/popular", years=year_range, page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    def movie_trending_recent(self):
        year_range = f"{datetime.datetime.now().year - 1}-{datetime.datetime.now().year}"
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/trending", years=year_range, page=g.PAGE, extended="full"
        )
        self.list_builder.movie_menu_builder(trakt_list)

    @trakt_auth_guard
    def on_deck_movies(self):
        hidden_movies = self.hidden_database.get_hidden_items("progress_watched", "movies")
        bookmarked_items = [
            i for i in self.bookmark_database.get_all_bookmark_items("movie") if i["trakt_id"] not in hidden_movies
        ][self.page_start : self.page_end]
        self.list_builder.movie_menu_builder(bookmarked_items)

    @trakt_auth_guard
    def my_movie_collection(self):
        paginate = not g.get_bool_setting("general.paginatecollection")
        sort = "title" if paginate else False
        self.list_builder.movie_menu_builder(
            self.movies_database.get_collected_movies(g.PAGE),
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
        date = g.datetime_to_string(date)
        trakt_list = self.movies_database.extract_trakt_page(f"movies/updates/{date}", page=g.PAGE, extended="full")
        self.list_builder.movie_menu_builder(trakt_list)

    def movies_search_history(self):
        history = self.search_history.get_search_history("movie")
        g.add_directory_item(
            g.get_language_string(30181),
            action="moviesSearch",
            description=g.get_language_string(30371),
        )
        g.add_directory_item(
            g.get_language_string(30180),
            action="clearSearchHistory",
            mediatype="movie",
            is_folder=False,
            description=g.get_language_string(30381),
        )

        for i in history:
            remove_path = g.create_url(
                g.BASE_URL,
                {"action": "removeSearchHistory", "mediatype": "movie", "endpoint": i},
            )
            g.add_directory_item(
                i,
                action="moviesSearchResults",
                action_args=tools.construct_action_args(i),
                cm=[(g.get_language_string(30565), f"RunPlugin({remove_path})")],
            )
        g.close_directory(g.CONTENT_MENU)

    def movies_search(self, query=None):
        if query is None:
            query = g.get_keyboard_input(heading=g.get_language_string(30013))
            if not query:
                g.cancel_directory()
                return

        if g.get_bool_setting("searchHistory"):
            self.search_history.add_search_history("movie", query)

        self.movies_search_results(query)

    def movies_search_results(self, query):
        trakt_list = self.movies_database.extract_trakt_page(
            "search/movie",
            query=query,
            fields="title,aliases",
            extended="full",
            page=g.PAGE,
            hide_watched=False,
            hide_unaired=False,
        )

        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(
            [movie for movie in trakt_list if float(movie["trakt_object"]["info"]["score"]) > 0],
            hide_watched=False,
            hide_unaired=False,
        )

    def movies_related(self, args):
        trakt_list = self.movies_database.extract_trakt_page(f"movies/{args}/related", page=g.PAGE, extended="full")
        self.list_builder.movie_menu_builder(trakt_list)

    @staticmethod
    def movies_years():
        from datetime import datetime

        year = int(datetime.today().year)

        for year in range(year, 1899, -1):
            g.add_directory_item(str(year), action="movieYearsMovies", action_args=year)
        g.close_directory(g.CONTENT_MENU)

    def movie_years_results(self, year):
        trakt_list = self.movies_database.extract_trakt_page("movies/popular", years=year, page=g.PAGE, extended="full")
        self.list_builder.movie_menu_builder(trakt_list)

    def movies_by_actor(self, query):
        if query is None:
            query = g.get_keyboard_input(g.get_language_string(30013))
            if not query:
                g.cancel_directory()
                return

        if g.get_bool_setting("searchHistory"):
            self.search_history.add_search_history("movieActor", query)

        query = g.transliterate_string(query)
        # Try to deal with transliterated chinese actor names as some character -> word transliterations can be joined
        # I have no idea of the rules and it could well be arbitrary
        # This approach will only work if only one pair of adjoining transliterated chars are joined
        name_parts = query.split()
        for i in range(len(name_parts), 0, -1):
            query = "-".join(name_parts[:i]) + "-".join(name_parts[i : i + 1])
            query = parse.quote_plus(query)

            trakt_list = self.movies_database.extract_trakt_page(
                f"people/{query}/movies", extended="full", page=g.PAGE, hide_watched=False, hide_unaired=False
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
        self.list_builder.movie_menu_builder(trakt_list, hide_watched=False, hide_unaired=False)

    def movies_genres(self):
        g.add_directory_item(
            g.get_language_string(30045),
            action="movieGenresGet",
            menu_item=g.create_icon_dict("list", g.ICONS_PATH),
        )
        genres = self.trakt_api.get_json_cached("genres/movies")
        if genres is None:
            g.cancel_directory()
            return
        for i in genres:
            g.add_directory_item(
                i["name"],
                action="movieGenresGet",
                action_args=i["slug"],
                menu_item=g.create_icon_dict(i['slug'], g.GENRES_PATH),
            )
        g.close_directory(g.CONTENT_GENRES)

    def movies_genre_list(self, args):
        if args is None:
            genre_display_list = []
            genres = self.trakt_api.get_json_cached("genres/movies")
            for genre in genres:
                gi = xbmcgui.ListItem(genre["name"])
                gi.setArt({"thumb": f"{g.GENRES_PATH}{genre['slug']}.png"})
                genre_display_list.append(gi)
            genre_multiselect = xbmcgui.Dialog().multiselect(
                f"{g.ADDON_NAME}: {g.get_language_string(30303)}", genre_display_list, useDetails=True
            )
            if genre_multiselect is None:
                return
            genre_string = ",".join([genres[i]["slug"] for i in genre_multiselect])
        else:
            genre_string = parse.unquote(args)

        trakt_list = self.movies_database.extract_trakt_page(
            f"movies/{'trending' if g.get_int_setting('general.genres.endpoint.movies') == 0 else 'popular'}",
            genres=genre_string,
            page=g.PAGE,
            extended="full",
        )

        if trakt_list is None:
            g.cancel_directory()
            return

        self.list_builder.movie_menu_builder(trakt_list, next_args=genre_string)

    @trakt_auth_guard
    def my_watched_movies(self):
        watched_movies = self.movies_database.get_watched_movies(g.PAGE)
        self.list_builder.movie_menu_builder(watched_movies)
