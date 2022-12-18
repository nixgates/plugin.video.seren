from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database import trakt_sync
from resources.lib.modules.globals import g
from resources.lib.modules.guard_decorators import guard_against_none
from resources.lib.modules.guard_decorators import guard_against_none_or_empty
from resources.lib.modules.metadataHandler import MetadataHandler


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    """
    Handles database records for show/season/episode items

    """

    def extract_trakt_page(self, url, **params):
        """
        Extracts items from page
        :param url: URL endpoint to extract
        :type url: string
        :param params: Kwargs to pass to super call
        :type params: any
        :return: List of items from page
        :rtype: list
        """
        return super()._extract_trakt_page(url, "shows", **params)

    @guard_against_none()
    def _update_shows_statistics_from_show_id(self, trakt_show_id):
        self.update_shows_statistics([{"trakt_id": trakt_show_id}])
        self.update_season_statistics(
            self.fetchall("select trakt_id from seasons where trakt_show_id=?", (trakt_show_id,))
        )

    @guard_against_none()
    def mark_show_watched(self, show_id, watched):
        """
        Mark watched status for all items of a show except specials
        :param show_id: Trakt ID of the show to update
        :type show_id: int
        :param watched: 1 for watched 0 for unwatched
        :type watched: int
        :return: None
        :rtype: None
        """
        g.log(f"Marking show {show_id} as watched in sync database", "debug")
        self._mill_if_needed([{"trakt_id": show_id}])
        self.execute_sql(
            "UPDATE episodes SET watched=?, last_watched_at=? WHERE trakt_show_id = ? AND season != 0",
            (watched, self._get_datetime_now() if watched > 0 else None, show_id),
        )
        self._update_shows_statistics_from_show_id(show_id)

    @guard_against_none()
    def mark_season_watched(self, show_id, season, watched):
        """
         Mark watched status for all items of a season
        :param show_id: Trakt ID of the show to update
        :type show_id: int
        :param season: Season number to mark
        :type season: int
        :param watched: 1 for watched 0 for unwatched
        :type watched: int
        :return: None
        :rtype: None
        """
        g.log(f"Marking season {season} as watched in sync database", "debug")
        self.execute_sql(
            "UPDATE episodes SET watched=?, last_watched_at=?" " WHERE trakt_show_id=? AND season=?",
            (
                watched,
                self._get_datetime_now() if watched > 0 else None,
                show_id,
                season,
            ),
        )
        self._update_shows_statistics_from_show_id(show_id)

    @guard_against_none()
    def mark_show_collected(self, show_id, collected):
        """
        Sets collected status for all items of a given show
        :param show_id: ID of show to update
        :type show_id: int
        :param collected: Status of collection (1=True, 0=False)
        :type collected: int
        :return: None
        :rtype: None
        """
        g.log(f"Marking show {show_id} as collected in sync database", "debug")
        self._mill_if_needed([{"trakt_id": show_id}])
        self.execute_sql(
            "UPDATE episodes SET collected=?, collected_at=? WHERE trakt_show_id=?",
            (collected, self._get_datetime_now() if collected > 0 else None, show_id),
        )

    @guard_against_none()
    def mark_episode_watched(self, show_id, season, number):
        """
        Mark an individual episode item as watched
        :param show_id: ID of show to update
        :type show_id: int
        :param season: Season number of episode
        :type season: int
        :param number: Episode number to update
        :type number: int
        :return: None
        :rtype: None
        """
        g.log(
            f"Marking episode {show_id} S{season}E{number} as watched in sync database",
            "debug",
        )
        play_count = self.fetchone(
            "SELECT watched from episodes " "where trakt_show_id=? and season=? and number=?",
            (show_id, season, number),
        ).get("watched")
        if play_count is None:
            return
        self._mark_episode_record("watched", play_count + 1, show_id, season, number)
        self._update_shows_statistics_from_show_id(show_id)

    @guard_against_none()
    def mark_episode_unwatched(self, show_id, season, number):
        """
        Mark an individual episode item as unwatched
        :param show_id: ID of show to update
        :type show_id: int
        :param season: Season number of episode
        :type season: int
        :param number: Episode number to update
        :type number: int
        :return: None
        :rtype: None
        """
        g.log(
            f"Marking episode {show_id} S{season}E{number} as unwatched in sync database",
            "debug",
        )

        self._mark_episode_record("watched", 0, show_id, season, number)
        self._update_shows_statistics_from_show_id(show_id)

    @guard_against_none()
    def _mark_show_record(self, column, value, show_id):
        self.execute_sql(f"UPDATE shows SET {column}=? WHERE trakt_id=?", (value, show_id))

    @guard_against_none()
    def _mark_episode_record(self, column, value, show_id, season, number):
        if column == "watched":
            datetime_column = "last_watched_at"
        elif column == "collected":
            datetime_column = "collected_at"
        else:
            datetime_column = None

        if datetime_column is None:
            # Just in case we forgot any methods that call this
            raise ValueError
        self.execute_sql(
            f"UPDATE episodes SET {column}=?, {datetime_column}=? WHERE trakt_show_id=? AND season=? AND number=?",
            (
                value,
                self._get_datetime_now() if value > 0 else None,
                show_id,
                season,
                number,
            ),
        )
        self._update_shows_statistics_from_show_id(show_id)

    @guard_against_none(list)
    def get_recently_watched_shows(self, page=1, force_all=False):
        """
        Returns a list of recently watched shows
        :param page: Page to pull
        :type page: int
        :param force_all: Enforce pulling of all items
        :type force_all: bool
        :return: List of show records
        :rtype: list
        """

        query = """
            SELECT sm.id                   AS trakt_id,
                   sm.value                AS trakt_object,
                   MAX(ep.last_watched_at) AS lw
            FROM shows_meta AS sm
                     LEFT JOIN episodes AS ep
                               ON ep.trakt_show_id = sm.id AND sm.type = 'trakt'
            WHERE watched > 0
            GROUP BY trakt_show_id
            ORDER BY last_watched_at DESC
            """

        if not force_all:
            query += f" LIMIT {self.page_limit} OFFSET {self.page_limit * (page - 1)}"

        return self.fetchall(query)

    @guard_against_none(list)
    def get_collected_shows(self, page=1, force_all=False):
        """
        Returns all shows marked as collected from the database
        :param page: Page to pull
        :type page: int
        :param force_all: Enforce pulling of all items
        :type force_all: bool
        :return: List of show records
        :rtype: list
        """
        paginate = g.get_bool_setting("general.paginatecollection")
        sort = g.get_int_setting("general.sortcollection")

        order_by = "ORDER BY max(e.collected_at) DESC" if sort == 0 else ""
        limit = (
            f"LIMIT {self.page_limit} OFFSET {self.page_limit * (page - 1)}"
            if paginate and not force_all and sort != 1
            else ""
        )

        query = f"""
            SELECT e.trakt_show_id AS trakt_id, m.value AS trakt_object
            FROM episodes AS e
                     LEFT JOIN shows AS sh
                               ON sh.trakt_id = e.trakt_show_id
                     LEFT JOIN shows_meta AS m
                               ON m.id = e.trakt_show_id AND m.type = 'trakt'
            WHERE e.collected = TRUE
            GROUP BY e.trakt_show_id
            {order_by}
            {limit}
            """

        return self.fetchall(query)

    def get_collected_episodes(self):
        """
        Returns a list of all episode objects marked as collected
        :return: List of episode objects
        :rtype: list
        """
        return self.fetchall("""SELECT trakt_id as trakt_id FROM episodes WHERE collected=1""")

    @guard_against_none(list)
    def get_show_list(self, trakt_list, **params):
        """
        Takes in a list of shows from a Trakt endpoint, updates meta where required and returns the formatted list
        :param trakt_list: List of shows to retrieve
        :type trakt_list: list
        :return: List of updated shows with full meta
        :rtype: list
        """
        g.log("Fetching show list from sync database and updating", "debug")
        trakt_list = [i for i in trakt_list if i.get("trakt_id")]
        self._update_mill_format_shows(trakt_list, False)
        g.log("Show list update and milling complete", "debug")
        statement = f"""
            SELECT s.trakt_id, s.info, s.cast, s.art, s.args, s.watched_episodes, s.unwatched_episodes, s.episode_count,
                s.season_count, s.air_date, s.user_rating
            FROM shows AS s
            WHERE s.trakt_id IN ({','.join(str(i.get('trakt_id')) for i in trakt_list)})
            """
        if params.pop("hide_unaired", self.hide_unaired):
            statement += f" AND Datetime(s.air_date) < Datetime('{self._get_datetime_now()}')"
        if params.pop("hide_watched", self.hide_watched):
            statement += " AND s.watched_episodes < s.episode_count"

        return MetadataHandler.sort_list_items(self.fetchall(statement), trakt_list)

    @guard_against_none(list, 1)
    def get_season_list(self, trakt_show_id, trakt_id=None, **params):
        """
        Fetches a list of seasons from database for a given show with full meta
        :param trakt_show_id: Trakt ID of show
        :type trakt_show_id: int
        :param trakt_id: Trakt ID of season
        :type trakt_id: int
        :return: List of seasons with full meta
        :rtype: list
        """
        g.log("Fetching season list from sync database and updating", "debug")
        self._try_update_seasons(trakt_show_id, trakt_id)
        g.log("Updated requested seasons", "debug")
        statement = """SELECT s.trakt_id, s.info, s.cast, s.art, s.args, s.watched_episodes, s.unwatched_episodes,
        s.episode_count, s.air_date, s.user_rating FROM seasons AS s WHERE """
        if trakt_id is not None:
            statement += f"s.trakt_id == {trakt_id}"
        else:
            statement += f"s.trakt_show_id = {trakt_show_id}"
        if params.pop("hide_unaired", self.hide_unaired):
            statement += f" AND Datetime(s.air_date) < Datetime('{self._get_datetime_now()}')"
        if params.pop("self.hide_specials", self.hide_specials):
            statement += " AND s.season != 0"
        if params.pop("hide_watched", self.hide_watched):
            statement += " AND s.watched_episodes < s.episode_count"
        statement += " order by s.Season"
        return self.fetchall(statement)

    @guard_against_none(list, 1, 2, 4)
    def get_episode_list(self, trakt_show_id, trakt_season_id=None, trakt_id=None, minimum_episode=None, **params):
        """
        Retrieves a list of episodes or a given season with full meta
        :param trakt_show_id: Trakt ID of show
        :type trakt_show_id: int
        :param trakt_season_id:  Trakt ID of season
        :type trakt_season_id: int
        :param trakt_id: Optional Trakt ID of single episode to pull
        :type trakt_id: int
        :param hide_unaired: Optional hiding of un-aired items
        :type hide_unaired: bool
        :param minimum_episode: Optional minimum episode to set as a floor
        :type minimum_episode: int
        :return: List of episode objects with full meta
        :rtype: list
        """
        g.log("Fetching Episode list from sync database and updating", "debug")
        self._try_update_episodes(trakt_show_id, trakt_season_id, trakt_id)
        g.log("Updated required episodes", "debug")
        statement = """SELECT e.trakt_id, e.trakt_show_id, e.trakt_season_id, e.info, e.cast, e.art, e.args, e.watched as play_count,
         b.resume_time as resume_time, b.percent_played as percent_played, e.user_rating FROM episodes as e
         LEFT JOIN bookmarks as b on e.trakt_id = b.trakt_id WHERE """

        if trakt_season_id is not None:
            statement += f"e.trakt_season_id = {trakt_season_id} "
        elif trakt_id is not None:
            statement += f"e.trakt_id = {trakt_id} "
        else:
            statement += f"e.trakt_show_id = {trakt_show_id} "
        if params.pop("hide_unaired", self.hide_unaired):
            statement += f" AND Datetime(e.air_date) < Datetime('{self._get_datetime_now()}') "
        if params.pop("self.hide_specials", self.hide_specials):
            statement += " AND e.season != 0"
        if params.pop("hide_watched", self.hide_watched):
            statement += " AND e.watched = 0"
        if minimum_episode:
            statement += f" AND e.number >= {int(minimum_episode)}"
        statement += " order by e.season, e.number "
        return self.fetchall(statement)

    @guard_against_none(list)
    def get_mixed_episode_list(self, trakt_items, **params):
        """
        Returns a list of mixed episodes from different or same show
        :param trakt_items: List of show & episodes object pairs
        :type trakt_items: list
        :return: List of episode objects with full meta
        :rtype: list
        """
        g.log("Fetching mixed episode list from sync database", "debug")
        self._try_update_mixed_episodes(trakt_items)
        in_predicate = ",".join([str(i["trakt_id"]) for i in trakt_items if i["trakt_id"] is not None])
        if g.get_bool_setting("general.showRemainingUnwatched"):
            query = f"""
                SELECT e.trakt_id,
                       e.info,
                       e.cast,
                       e.art,
                       e.args,
                       e.watched        AS play_count,
                       b.resume_time    AS resume_time,
                       b.percent_played AS percent_played,
                       se.watched_episodes,
                       se.unwatched_episodes,
                       se.episode_count,
                       e.user_rating
                FROM episodes AS e
                         INNER JOIN seasons se
                                    ON e.trakt_season_id = se.trakt_id
                         LEFT JOIN bookmarks AS b
                                   ON e.trakt_id = b.trakt_id
                WHERE e.trakt_id IN ({in_predicate})
                """
        else:
            query = f"""
                SELECT e.trakt_id, e.info, e.cast, e.art, e.args, e.watched AS play_count, b.resume_time AS resume_time,
                    b.percent_played AS percent_played, e.user_rating
                FROM episodes AS e LEFT JOIN bookmarks AS b ON e.Trakt_id = b.Trakt_id
                WHERE e.trakt_id IN ({in_predicate})
                """
        if params.pop("hide_unaired", self.hide_unaired):
            query += f" AND Datetime(e.air_date) < Datetime('{self._get_datetime_now()}') "
        if params.pop("hide_specials", self.hide_specials):
            query += " AND e.season != 0"
        if params.pop("hide_watched", self.hide_watched):
            query += " AND e.watched = 0"

        return MetadataHandler.sort_list_items(self.fetchall(query), trakt_items)

    @guard_against_none()
    def _get_single_show_meta(self, trakt_id):
        return self._get_single_meta(f"/shows/{trakt_id}", trakt_id, "shows")

    @guard_against_none(list)
    def get_show(self, trakt_id):
        """
        Returns a single show record from the database with full meta
        :param trakt_id: Shows Trakt ID
        :type trakt_id: int
        :return: Show item with full meta
        :rtype: dict
        """
        result = self.get_show_list([self._get_single_show_meta(trakt_id)], hide_unaired=False, hide_watched=False)
        return result[0] if len(result) > 0 else []

    @guard_against_none(list)
    def get_season(self, trakt_id, trakt_show_id):
        """
        Returns a single season record from the database with full meta
        :param trakt_id: Trakt ID of season
        :type trakt_id: int
        :param trakt_show_id: Trakt ID of show
        :type trakt_show_id: int
        :return: Season item with full meta
        :rtype: dict
        """
        result = self.get_season_list(trakt_show_id, trakt_id, hide_unaired=False, hide_watched=False)
        return result[0] if len(result) > 0 else []

    @guard_against_none(list)
    def get_episode(self, trakt_id, trakt_show_id):
        """
        Returns a single episode record from the database with full meta
        :param trakt_id: Trakt ID of episode
        :type trakt_id: int
        :param trakt_show_id: Trakt ID of show
        :type trakt_show_id: int
        :return: Episode object with full meta
        :rtype: dict
        """
        result = self.get_episode_list(trakt_show_id, trakt_id=trakt_id, hide_unaired=False, hide_watched=False)
        if len(result) > 0:
            result = result[0]
            result.update(
                self.fetchone(
                    f"""
                    SELECT s.season_count,
                           s.episode_count AS show_episode_count,
                           se.episode_count,
                           se.is_airing,
                           a.absoluteNumber,
                           e.user_rating
                    FROM episodes AS e
                             INNER JOIN seasons AS se
                                        ON se.trakt_id = e.trakt_season_id
                             INNER JOIN shows AS s ON s.trakt_id = e.trakt_show_id
                             INNER JOIN (SELECT e.trakt_show_id, count(DISTINCT e.trakt_id) AS absoluteNumber
                                         FROM episodes AS e
                                                  INNER JOIN (SELECT e.trakt_show_id,
                                                                     (e.season * 10 + e.number) AS identifier
                                                              FROM episodes AS e
                                                              WHERE e.trakt_id = {trakt_id}) AS agg
                                                             ON agg.trakt_show_id = e.trakt_show_id
                                                                 AND agg.identifier >= (e.season * 10 + number)
                                         GROUP BY e.trakt_show_id) AS a
                                        ON a.trakt_show_id = e.trakt_show_id
                    WHERE e.trakt_id = {trakt_id}
                    """
                )
            )
        return result

    @guard_against_none(list)
    def _update_objects(self, db_list_to_update, media_type):

        threadpool = ThreadPool()
        for i in db_list_to_update:
            threadpool.put(self.metadataHandler.update, i)
        updated_items = threadpool.wait_completion()

        if updated_items is None:
            return

        threadpool.put(
            self.save_to_meta_table,
            (i for i in updated_items if i and "trakt_object" in i),
            media_type,
            "trakt",
            "trakt_id",
        )
        threadpool.put(
            self.save_to_meta_table,
            (i for i in updated_items if i and "tmdb_object" in i),
            media_type,
            "tmdb",
            "tmdb_id",
        )
        threadpool.put(
            self.save_to_meta_table,
            (i for i in updated_items if i and "tvdb_object" in i),
            media_type,
            "tvdb",
            "tvdb_id",
        )
        threadpool.put(
            self.save_to_meta_table,
            (i for i in updated_items if i and "fanart_object" in i),
            media_type,
            "fanart",
            "tvdb_id",
        )
        threadpool.put(
            self.save_to_meta_table,
            (i for i in updated_items if i and "omdb_object" in i),
            media_type,
            "omdb",
            "imdb_id",
        )
        threadpool.wait_completion()

        return updated_items

    def _format_objects(self, updated_items):
        return self.metadataHandler.format_db_object(updated_items)

    @guard_against_none_or_empty()
    def _update_shows(self, list_to_update):
        get = MetadataHandler.get_trakt_info
        sql_statement = f"""
            WITH requested(trakt_id, last_updated) AS (VALUES
                {','.join("({},'{}')".format(i.get('trakt_show_id', i.get('trakt_id')), get(i, 'dateadded'))
                          for i in list_to_update)})
            SELECT r.trakt_id,
                   trakt.value      AS trakt_object,
                   trakt.meta_hash  AS trakt_meta_hash,
                   tmdb_id,
                   tmdb.value       AS tmdb_object,
                   tmdb.meta_hash   AS tmdb_meta_hash,
                   tvdb_id,
                   tvdb.value       AS tvdb_object,
                   tvdb.meta_hash   AS tvdb_meta_hash,
                   fanart.value     AS fanart_object,
                   fanart.meta_hash AS fanart_meta_hash,
                   s.imdb_id,
                   omdb.value       AS omdb_object,
                   omdb.meta_hash   AS omdb_meta_hash,
                   s.needs_update
            FROM requested AS r
                     LEFT JOIN shows AS s ON r.trakt_id = s.trakt_id
                     LEFT JOIN shows_meta AS trakt ON trakt.id = s.trakt_id AND trakt.type = 'trakt'
                     LEFT JOIN shows_meta AS tmdb ON tmdb.id = s.tmdb_id AND tmdb.type = 'tmdb'
                     LEFT JOIN shows_meta AS tvdb ON tvdb.id = s.tvdb_id AND tvdb.type = 'tvdb'
                     LEFT JOIN shows_meta AS omdb ON omdb.id = s.imdb_id AND omdb.type = 'omdb'
                     LEFT JOIN shows_meta AS fanart ON fanart.id = s.tvdb_id AND fanart.type = 'fanart'
            """

        db_list_to_update = self.fetchall(sql_statement)
        updated_items = self._update_objects(db_list_to_update, "shows")

        formatted_items = self._format_objects(updated_items)

        if formatted_items is None:
            return

        self.execute_sql(
            self.upsert_show_query,
            (
                (
                    i["info"]["trakt_id"],
                    i["info"],
                    i.get("art"),
                    i.get("cast"),
                    i["info"].get("aired"),
                    i["info"].get("dateadded"),
                    i["info"].get("tmdb_id"),
                    i["info"].get("tvdb_id"),
                    i["info"].get("imdb_id"),
                    self.metadataHandler.meta_hash,
                    i["info"].get("season_count"),
                    i["info"].get("episode_count"),
                    self._create_args(i),
                    i["info"].get("is_airing"),
                    i["info"].get("last_watched_at"),
                    i["info"].get("last_collected_at"),
                    i["info"].get("user_rating"),
                )
                for i in formatted_items
            ),
        )
        self.update_shows_statistics({"trakt_id": i["info"]["trakt_id"]} for i in formatted_items)

    def _update_mill_format_shows(self, trakt_list, mill_episodes=False):
        if not trakt_list:
            return
        trakt_list = trakt_list if isinstance(trakt_list, list) else [trakt_list]
        self.insert_trakt_shows(trakt_list)
        self._update_shows(trakt_list)
        self._mill_if_needed(trakt_list, None, mill_episodes)

    @guard_against_none_or_empty()
    def _identify_seasons_to_update(self, list_to_update):
        get = MetadataHandler.get_trakt_info
        sql_statement = f"""
            WITH requested(trakt_id, last_updated) AS (VALUES
                    {','.join(f"({i.get('trakt_id')},'{get(i, 'dateadded')}')" for i in list_to_update)})
            SELECT r.trakt_id       AS trakt_id,
                   trakt.value      AS trakt_object,
                   trakt.meta_hash  AS trakt_meta_hash,
                   sh.tmdb_id       AS tmdb_show_id,
                   se.tmdb_id       AS tmdb_id,
                   tmdb.value       AS tmdb_object,
                   tmdb.meta_hash   AS tmdb_meta_hash,
                   sh.tvdb_id       AS tvdb_show_id,
                   se.tvdb_id       AS tvdb_id,
                   tvdb.value       AS tvdb_object,
                   tvdb.meta_hash   AS tvdb_meta_hash,
                   fanart.value     AS fanart_object,
                   fanart.meta_hash AS fanart_meta_hash,
                   sh.info          AS show_info,
                   sh.art           AS show_art,
                   sh.cast          AS show_cast,
                   se.needs_update
            FROM requested AS r
                     LEFT JOIN seasons AS se ON r.trakt_id = se.trakt_id
                     LEFT JOIN shows AS sh ON sh.trakt_id = se.trakt_show_id
                     LEFT JOIN seasons_meta AS trakt ON trakt.id = se.trakt_id AND trakt.type = 'trakt'
                     LEFT JOIN seasons_meta AS tmdb ON tmdb.id = se.tmdb_id AND tmdb.type = 'tmdb'
                     LEFT JOIN seasons_meta AS tvdb ON tvdb.id = se.tvdb_id AND tvdb.type = 'tvdb'
                     LEFT JOIN seasons_meta AS fanart ON fanart.id = se.tvdb_id AND fanart.type = 'fanart'
            """

        return self.fetchall(sql_statement)

    @guard_against_none_or_empty()
    def _update_seasons(self, list_to_update):
        db_list_to_update = self._identify_seasons_to_update(list_to_update)
        if db_list_to_update is None:
            db_list_to_update = []

        return self._update_objects(db_list_to_update, "seasons")

    @guard_against_none_or_empty()
    def _format_seasons(self, list_to_update):
        formatted_items = self._format_objects(self._identify_seasons_to_update(list_to_update))

        if formatted_items is None:
            return

        self.execute_sql(
            self.upsert_season_query,
            (
                (
                    i["info"]["trakt_show_id"],
                    i["info"]["trakt_id"],
                    i["info"],
                    i.get("art"),
                    i.get("cast"),
                    i["info"].get("aired"),
                    i["info"].get("dateadded"),
                    i["info"].get("tmdb_id"),
                    i["info"].get("tvdb_id"),
                    self.metadataHandler.meta_hash,
                    i["info"].get("episode_count"),
                    i["info"].get("season"),
                    self._create_args(i),
                    i["info"].get("last_watched_at"),
                    i["info"].get("last_collected_at"),
                    i["info"].get("user_rating"),
                )
                for i in formatted_items
            ),
        )
        self.update_season_statistics({"trakt_id": i["info"]["trakt_id"]} for i in formatted_items)

    @guard_against_none_or_empty()
    def _identify_episodes_to_update(self, list_to_update):
        get = MetadataHandler.get_trakt_info
        query = f"""
            WITH requested(trakt_id, last_updated) AS (VALUES
                    {','.join(f"({i.get('trakt_id')},'{get(i, 'dateadded')}')" for i in list_to_update)})
            SELECT r.trakt_id       AS trakt_id,
                   ep.trakt_season_id,
                   ep.trakt_show_id,
                   trakt.value      AS trakt_object,
                   trakt.meta_hash  AS trakt_meta_hash,
                   ep.tmdb_id       AS tmdb_id,
                   tmdb.value       AS tmdb_object,
                   tmdb.meta_hash   AS tmdb_meta_hash,
                   ep.tvdb_id       AS tvdb_id,
                   tvdb.value       AS tvdb_object,
                   tvdb.meta_hash   AS tvdb_meta_hash,
                   fanart.value     AS fanart_object,
                   fanart.meta_hash AS fanart_meta_hash,
                   ep.imdb_id,
                   omdb.value       AS omdb_object,
                   omdb.meta_hash   AS omdb_meta_hash,
                   sh.tmdb_id       AS tmdb_show_id,
                   sh.tvdb_id       AS tvdb_show_id,
                   sh.info          AS show_info,
                   sh.art           AS show_art,
                   sh.cast          AS show_cast,
                   ep.trakt_season_id,
                   se.tmdb_id       AS tmdb_season_id,
                   sh.tvdb_id       AS tvdb_season_id,
                   se.info          AS season_info,
                   se.art           AS season_art,
                   se.cast          AS season_cast,
                   ep.needs_update
            FROM requested AS r
                     LEFT JOIN episodes AS ep ON r.trakt_id = ep.trakt_id
                     LEFT JOIN shows AS sh ON sh.trakt_id = ep.trakt_show_id
                     LEFT JOIN seasons AS se ON se.trakt_id = ep.trakt_season_id
                     LEFT JOIN episodes_meta AS trakt ON trakt.id = ep.trakt_id AND trakt.type = 'trakt'
                     LEFT JOIN episodes_meta AS tmdb ON tmdb.id = ep.tmdb_id AND tmdb.type = 'tmdb'
                     LEFT JOIN episodes_meta AS tvdb ON tvdb.id = ep.tvdb_id AND tvdb.type = 'tvdb'
                     LEFT JOIN episodes_meta AS omdb ON omdb.id = ep.imdb_id AND omdb.type = 'omdb'
                     LEFT JOIN episodes_meta AS fanart ON fanart.id = ep.tvdb_id AND fanart.type = 'fanart'
            """

        return self.fetchall(query)

    @guard_against_none_or_empty()
    def _update_episodes(self, list_to_update):
        db_list_to_update = self._identify_episodes_to_update(list_to_update)

        if db_list_to_update is None:
            db_list_to_update = []

        return self._update_objects(db_list_to_update, "episodes")

    @guard_against_none_or_empty()
    def _format_episodes(self, list_to_update):
        formatted_items = self._format_objects(self._identify_episodes_to_update(list_to_update))

        if formatted_items is None:
            return
        self.execute_sql(
            self.upsert_episode_query,
            (
                (
                    i["info"]["trakt_id"],
                    i["info"]["trakt_show_id"],
                    i["info"]["trakt_season_id"],
                    None,
                    None,
                    i["info"].get("aired"),
                    i["info"].get("dateadded"),
                    i["info"].get("season"),
                    i["info"].get("episode"),
                    i["info"].get("tmdb_id"),
                    i["info"].get("tvdb_id"),
                    i["info"].get("imdb_id"),
                    i["info"],
                    i.get("art"),
                    i.get("cast"),
                    self._create_args(i),
                    None,
                    None,
                    None,
                    self.metadataHandler.meta_hash,
                )
                for i in formatted_items
            ),
        )

    @guard_against_none(None, 1)
    def _try_update_seasons(self, trakt_show_id, trakt_season_id=None):
        show_meta = self._get_single_show_meta(trakt_show_id)
        self._update_mill_format_shows(show_meta, True)

        if trakt_season_id is not None:
            where_clause = f"WHERE s.trakt_id = {trakt_season_id}"
        else:
            where_clause = f"WHERE sh.trakt_id = {trakt_show_id}"
        query = f"""
            SELECT s.trakt_id,
                   value      AS trakt_object,
                   s.trakt_show_id,
                   sh.tmdb_id AS tmdb_show_id,
                   sh.tvdb_id AS tvdb_show_id
            FROM seasons AS s
                     INNER JOIN shows AS sh ON s.trakt_show_id = sh.trakt_id
                     LEFT JOIN seasons_meta AS m ON m.id = s.trakt_id AND m.type = 'trakt'
            {where_clause}
            """

        seasons_to_update = self.fetchall(query)

        self._update_seasons(seasons_to_update)
        self._format_seasons(seasons_to_update)

    @guard_against_none(None, 1, 2)
    def _try_update_episodes(self, trakt_show_id, trakt_season_id=None, trakt_id=None):
        show_meta = self._get_single_show_meta(trakt_show_id)
        self._update_mill_format_shows(show_meta, True)
        if trakt_id is not None:
            where_clause = f"WHERE e.trakt_id = {trakt_id}"
        elif trakt_season_id is not None:
            where_clause = f"WHERE e.trakt_season_id = {trakt_season_id}"
        else:
            where_clause = f"WHERE sh.trakt_id = {trakt_show_id}"
        query = f"""
            SELECT value      AS trakt_object,
                   e.trakt_id,
                   e.trakt_show_id,
                   sh.tmdb_id AS tmdb_show_id,
                   sh.tvdb_id
                              AS tvdb_show_id
            FROM episodes AS e
                     INNER JOIN shows AS sh ON e.trakt_show_id = sh.trakt_id
                     INNER JOIN episodes_meta AS m ON m.id = e.trakt_id AND m.type = 'trakt'
            {where_clause}
            """

        episodes_to_update = self.fetchall(query)

        self._update_episodes(episodes_to_update)
        self._format_episodes(episodes_to_update)

    @guard_against_none()
    def _try_update_mixed_episodes(self, trakt_items):
        self.insert_trakt_shows([i["show"] for i in trakt_items if i.get("show")])

        for i in trakt_items:
            if not i.get("show"):
                self.task_queue.put(self._get_single_show_meta, i["trakt_show_id"])
        self.task_queue.wait_completion()

        shows = self.fetchall(
            f"""
            SELECT value AS trakt_object,
                   s.trakt_id,
                   s.tvdb_id,
                   s.tmdb_id
            FROM shows AS s
                     INNER JOIN shows_meta AS m ON m.id = s.trakt_id and m.type = 'trakt'
            WHERE s.trakt_id IN ({','.join(str(i.get('trakt_show_id')) for i in trakt_items)})
            """
        )

        self._update_mill_format_shows(shows, True)

        seasons_to_update = self.fetchall(
            f"""
                SELECT value      AS trakt_object,
                       se.trakt_id,
                       se.trakt_show_id,
                       sh.tmdb_id AS tmdb_show_id,
                       sh.tvdb_id AS tvdb_show_id
                FROM seasons AS se
                         INNER JOIN shows AS sh ON se.trakt_show_id = sh.trakt_id
                         INNER JOIN seasons_meta AS sm ON sm.id = se.trakt_id AND sm.type = 'trakt'
                WHERE se.trakt_id IN (SELECT e.trakt_season_id
                                      FROM episodes e
                                      WHERE e.trakt_id IN ({','.join(str(i.get('trakt_id')) for i in trakt_items)})
            )
            """
        )

        episodes_to_update = self.fetchall(
            f"""
            SELECT value      AS trakt_object,
                   e.trakt_id,
                   e.trakt_show_id,
                   sh.tmdb_id AS tmdb_show_id,
                   sh.tvdb_id AS tvdb_show_id
            FROM episodes AS e
                     INNER JOIN shows AS sh
                                ON e.trakt_show_id = sh.trakt_id
                     INNER JOIN episodes_meta AS em
                                ON em.id = e.trakt_id
            WHERE e.trakt_id IN ({','.join(str(i.get('trakt_id')) for i in trakt_items)})
            """
        )

        self._update_seasons(seasons_to_update)
        self._update_episodes(episodes_to_update)

        self._format_seasons(seasons_to_update)
        self._format_episodes(episodes_to_update)

    def get_nextup_episodes(self, sort_by_last_watched=False):
        """
        Fetches a mock trakt response of items that a user should watch next for each show
        :param sort_by_last_watched: Optional sorting by last_watched_at column
        :type sort_by_last_watched: bool
        :return: List of mixed episode/show pairs
        :rtype: list
        """
        if sort_by_last_watched:
            order_by = "ORDER BY inner_episodes.last_watched_at DESC"
        else:
            order_by = "ORDER BY e.air_date DESC"
        query = f"""
            SELECT e.trakt_id,
                   e.number  AS episode_x,
                   e.season  AS season_x,
                   e.trakt_show_id,
                   em.value  AS episode,
                   sm.value  AS show,
                   s.tmdb_id AS tmdb_show_id,
                   s.tvdb_id AS tvdb_show_id,
                   inner_episodes.last_watched_at,
                   e.air_date
            FROM episodes AS e
                     INNER JOIN shows AS s
                                ON s.trakt_id = e.trakt_show_id
                     INNER JOIN (SELECT e.trakt_show_id,
                                        Min(e.season)      AS season,
                                        Min(e.number)      AS number,
                                        nw.last_watched_at AS last_watched_at
                                 FROM episodes AS e
                                      INNER JOIN (SELECT e.trakt_show_id,
                                                         CASE
                                                             WHEN Max(e.season) == max_watched_season AND
                                                                  Max(e.number) == max_watched_episode_number
                                                                 THEN 1
                                                             ELSE Min(e.season)
                                                             END            AS season,
                                                         CASE
                                                             WHEN Max(e.season) == max_watched_season AND
                                                                  Max(e.number) == max_watched_episode_number
                                                                 THEN 1
                                                             ELSE Max(e.number)
                                                             END            AS number,
                                                         mw.last_watched_at AS last_watched_at
                                                  FROM episodes e
                                                       LEFT JOIN (SELECT mw_se.trakt_show_id,
                                                                         Max(mw_se.season) AS max_watched_season,
                                                                         mw_ep.number     AS max_watched_episode_number,
                                                                         mw_ep.last_watched_at AS last_watched_at
                                                                  FROM episodes AS mw_se
                                                                       INNER JOIN (SELECT trakt_show_id,
                                                                                          season,
                                                                                          Max(number)         AS number,
                                                                                          Max(last_watched_at)
                                                                                                AS last_watched_at
                                                                                   FROM episodes
                                                                                   WHERE watched >= 1 AND season > 0
                                                                                   GROUP BY trakt_show_id, season
                                                                       ) AS mw_ep
                                                                          ON mw_se.trakt_show_id = mw_ep.trakt_show_id
                                                                              AND mw_se.season = mw_ep.season
                                                                  GROUP BY mw_se.trakt_show_id) AS mw
                                                            ON e.trakt_show_id = mw.trakt_show_id
                                                  WHERE (e.season = mw.max_watched_season AND
                                                         e.number = mw.max_watched_episode_number + 1
                                                      AND watched = 0)
                                                     OR (e.season = mw.max_watched_season + 1 AND e.number = 1)
                                                  GROUP BY e.trakt_show_id) AS nw
                                                 ON (e.trakt_show_id == nw.trakt_show_id
                                                     AND e.season == nw.season
                                                     AND e.number >= nw.number)
                                 WHERE e.season > 0
                                   AND watched = 0
                                   AND e.trakt_show_id NOT IN (SELECT trakt_id AS trakt_show_id
                                                               FROM hidden
                                                               WHERE SECTION IN ('progress_watched'))
                                   AND Datetime(air_date) < Datetime('{self._get_datetime_now()}')
                                 GROUP BY e.trakt_show_id) AS inner_episodes
                            ON e.trakt_show_id == inner_episodes.trakt_show_id
                                AND e.season == inner_episodes.season
                                AND e.number == inner_episodes.number
                     LEFT JOIN episodes_meta AS em ON e.trakt_id = em.id AND em.type = 'trakt'
                     LEFT JOIN shows_meta AS sm ON e.trakt_show_id = sm.id AND sm.type = 'trakt'
            {order_by}
            """

        return self.wrap_in_trakt_object(self.fetchall(query))

    def get_watched_episodes(self, page=1):
        """
        Get watched episodes from database
        :param page: Page to request
        :type page: int
        :return: List of episode objects
        :rtype: list
        """
        return self.wrap_in_trakt_object(
            self.fetchall(
                f"""
                SELECT e.trakt_id,
                       e.number  AS episode_x,
                       e.season  AS season_x,
                       e.trakt_show_id,
                       em.value  AS episode,
                       sm.value  AS show,
                       s.tmdb_id AS tmdb_show_id,
                       s.tvdb_id AS tvdb_show_id,
                       e.last_watched_at
                FROM episodes AS e
                         INNER JOIN shows AS s
                             ON s.trakt_id = e.trakt_show_id
                         LEFT JOIN episodes_meta AS em
                             ON e.trakt_id = em.id
                         LEFT JOIN shows_meta AS sm
                             ON e.trakt_show_id = sm.id
                ORDER BY e.last_watched_at DESC
                LIMIT {self.page_limit} OFFSET {self.page_limit * (page - 1)}
                """
            )
        )

    def get_unfinished_collected_shows(self, page=1):
        """
        Returns a list of shows the user has collected but not completed watching
        :param page: Page to request
        :type page: int
        :return: List of show objects
        :rtype: list
        """
        paginate = g.get_bool_setting("general.paginatecollection")
        sort = g.get_int_setting("general.sortcollection")

        order_by = "ORDER BY collected_at DESC" if sort == 0 else ""
        limit = f" LIMIT {self.page_limit} OFFSET {self.page_limit * (page - 1)}" if paginate and sort != 1 else ""

        query = f"""
            SELECT m.id AS trakt_id, value AS trakt_object
            FROM shows_meta AS m
                     INNER JOIN(SELECT ep.trakt_show_id, max(ep.collected_at) AS collected_at
                                FROM episodes AS ep
                                WHERE ep.season != 0
                                  AND ep.watched = 0
                                  AND ep.collected = 1
                                GROUP BY ep.trakt_show_id
                                HAVING count(*) > 0) AS u
                         ON u.trakt_show_id = m.id AND m.type = 'trakt'
            {order_by}
            {limit}
            """

        return self.fetchall(query)

    @guard_against_none()
    def get_season_action_args(self, trakt_show_id, season):
        """
        Returns action_args for a given season
        :param trakt_show_id: Trakt ID of show
        :type trakt_show_id: int
        :param season: Season number
        :type season: int
        :return: Action Args in a dictionary format
        :rtype: dict
        """
        show = [self._get_single_show_meta(trakt_show_id)]
        self.insert_trakt_shows(show)
        self._mill_if_needed(show)
        return self.fetchone(
            "SELECT trakt_id, trakt_show_id FROM seasons WHERE trakt_show_id=? AND season =?",
            (trakt_show_id, season),
        )

    @guard_against_none()
    def get_episode_action_args(self, trakt_show_id, season, episode):
        """
        Fetches action args for a given episode
        :param trakt_show_id: Trakt ID of show
        :type trakt_show_id: int
        :param season: Season number of episode
        :type season: int
        :param episode: Number of requested episode
        :type episode: int
        :return: Action Args in a dictionary format
        :rtype: dict
        """
        show = [self._get_single_show_meta(trakt_show_id)]
        self.insert_trakt_shows(show)
        self._mill_if_needed(show)
        return self.fetchone(
            """SELECT trakt_id, trakt_show_id FROM episodes WHERE trakt_show_id=? AND season=? AND number=?""",
            (trakt_show_id, season, episode),
        )
