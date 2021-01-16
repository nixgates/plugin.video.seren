# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.database import trakt_sync
from resources.lib.modules.globals import g
from resources.lib.modules.guard_decorators import (
    guard_against_none,
    guard_against_none_or_empty,
)
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
        return super(TraktSyncDatabase, self)._extract_trakt_page(
            url, "shows", **params
        )

    @guard_against_none()
    def _update_shows_statistics_from_show_id(self, trakt_show_id):
        self.update_shows_statistics([{"trakt_id": trakt_show_id}])
        self.update_season_statistics(
            self.execute_sql(
                "select trakt_id from seasons where trakt_show_id=?", (trakt_show_id,)
            )
        )

    @guard_against_none()
    def mark_show_watched(self, show_id, watched):
        """
        Mark watched status for all items of a show
        :param show_id: Trakt ID of the show to update
        :type show_id: int
        :param watched: 1 for watched 0 for unwatched
        :type watched: int
        :return: None
        :rtype: None
        """
        g.log("Marking show {} as watched in sync database".format(show_id), "debug")
        self._mill_if_needed([{"trakt_id": show_id}])
        self.execute_sql(
            "UPDATE episodes SET watched=?, last_watched_at=? WHERE trakt_show_id=?",
            (watched, self._get_datetime_now(), show_id),
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
        g.log("Marking season {} as watched in sync database".format(season), "debug")
        self.execute_sql(
            "UPDATE episodes SET watched=?, last_watched_at=?"
            " WHERE trakt_show_id=? AND season=?",
            (watched, self._get_datetime_now(), show_id, season),
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
        g.log("Marking show {} as collected in sync database".format(show_id), "debug")
        self._mill_if_needed([{"trakt_id": show_id}])
        self.execute_sql(
            "UPDATE episodes SET collected=?, collected_at=? WHERE trakt_show_id=?",
            (collected, self._get_datetime_now(), show_id),
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
        g.log("Marking episode {} S{}E{} as watched in sync database".format(show_id, season, number), "debug")
        play_count = self.execute_sql(
            "SELECT watched from episodes "
            "where trakt_show_id=? and season=? and number=?",
            (show_id, season, number),
        ).fetchone()["watched"]
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
        g.log("Marking episode {} S{}E{} as unwatched in sync database".format(show_id, season, number), "debug")
        self.execute_sql(
            "UPDATE episodes SET watched=0 WHERE trakt_show_id=? and season=? and number=?",
            (show_id, season, number),
        )
        self._update_shows_statistics_from_show_id(show_id)

    @guard_against_none()
    def _mark_show_record(self, column, value, show_id):
        self.execute_sql(
            "UPDATE shows SET {}=? WHERE trakt_id=?".format(column), (value, show_id)
        )

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
            "UPDATE episodes SET {}=?, {}=? WHERE trakt_show_id=? AND season=? AND "
            "number=?".format(column, datetime_column),
            (value, self._get_datetime_now(), show_id, season, number),
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
        paginate = g.get_bool_setting("general.paginatecollection")

        query = """select sm.id as trakt_id, sm.value as trakt_object, MAX(ep.last_watched_at) as lw from shows_meta as
        sm left join episodes as ep on ep.trakt_show_id = sm.id and sm.type = 'trakt' where last_watched_at not NULL
        GROUP BY trakt_show_id ORDER BY last_watched_at DESC"""

        if paginate and not force_all:
            query += " LIMIT {} OFFSET {}".format(
                self.page_limit, self.page_limit * (page - 1)
            )

        return self.execute_sql(query).fetchall()

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

        query = """select e.trakt_show_id as trakt_id, m.value as trakt_object from episodes as e left 
        join shows as sh on sh.trakt_id = e.trakt_show_id left join shows_meta as m on m.id = e.trakt_show_id and 
        m.type='trakt' where e.collected = 1 group by e.trakt_show_id
        """

        if paginate and not force_all:
            query += "ORDER BY max(e.collected_at) desc LIMIT {} OFFSET {}".format(
                self.page_limit, self.page_limit * (page - 1)
            )

        return self.execute_sql(query).fetchall()

    def get_collected_episodes(self):
        """
        Returns a list of all episode objects marked as collected
        :return: List of episode objects
        :rtype: list
        """
        return self.execute_sql(
            """SELECT trakt_id as trakt_id FROM episodes WHERE collected=1"""
        ).fetchall()

    @guard_against_none(list)
    def get_show_list(self, trakt_list, **params):
        """
        Takes in a list of shows from a Trakt endpoint, updates meta where required and returns the formatted list
        :param trakt_list: List of shows to retrieve
        :type trakt_list: list
        :return: List of updated shows with full meta
        :rtype: list
        """
        g.log("Fetching show list from sync database", "debug")
        trakt_list = [i for i in trakt_list if i.get("trakt_id")]
        self.insert_trakt_shows(
            self.filter_trakt_items_that_needs_updating(trakt_list, "shows")
        )
        self._update_mill_format_shows(trakt_list, False)
        g.log("Show list update and milling compelete", "debug")
        statement = """SELECT s.trakt_id, s.info, s.cast, s.art, s.args, s.watched_episodes, s.unwatched_episodes, 
        s.episode_count, s.season_count FROM shows as s WHERE s.trakt_id in ({}) """.format(
            ",".join((str(i.get("trakt_id")) for i in trakt_list))
        )
        if params.pop("hide_unaired", self.hide_unaired):
            statement += " AND Datetime(s.air_date) < Datetime('now')"
        if params.pop("hide_watched", self.hide_watched):
            statement += " AND s.watched_episodes < s.episode_count"

        return MetadataHandler.sort_list_items(
            self.execute_sql(statement).fetchall(), trakt_list
        )

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
        g.log("Fetching season list from sync database", "debug")
        self._try_update_seasons(trakt_show_id)
        g.log("Updated requested seasons", "debug")
        statement = """SELECT s.trakt_id, s.info, s.cast, s.art, s.args, s.watched_episodes, s.unwatched_episodes, 
        s.episode_count FROM seasons AS s WHERE """
        if trakt_id is not None:
            statement += "s.trakt_id == {}".format(trakt_id)
        else:
            statement += "s.trakt_show_id = {}".format(trakt_show_id)
        if params.pop("hide_unaired", self.hide_unaired):
            statement += " AND Datetime(s.air_date) < Datetime('now')"
        if params.pop("self.hide_specials", self.hide_specials):
            statement += " AND s.season != 0"
        if params.pop("hide_watched", self.hide_watched):
            statement += " AND s.watched_episodes < s.episode_count"
        statement += " order by s.Season"
        return self.execute_sql(statement).fetchall()

    @guard_against_none(list, 1, 2, 4)
    def get_episode_list(
        self,
        trakt_show_id,
        trakt_season_id=None,
        trakt_id=None,
        minimum_episode=None,
        **params
    ):
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
        g.log("Fetching Episode list from sync database", "debug")
        self._try_update_episodes(trakt_show_id, trakt_season_id, trakt_id)
        g.log("Updated required episodes", "debug")
        statement = """SELECT e.trakt_id, e.info, e.cast, e.art, e.args, e.watched as play_count,
         b.resume_time as resume_time, b.percent_played as percent_played FROM episodes as e 
         LEFT JOIN bookmarks as b on e.trakt_id = b.trakt_id WHERE """

        if trakt_season_id is not None:
            statement += "e.trakt_season_id = {} ".format(trakt_season_id)
        elif trakt_id is not None:
            statement += "e.trakt_id = {} ".format(trakt_id)
        else:
            statement += "e.trakt_show_id = {} ".format(trakt_show_id)
        if params.pop("hide_unaired", self.hide_unaired):
            statement += " AND Datetime(e.air_date) < Datetime('now') "
        if params.pop("self.hide_specials", self.hide_specials):
            statement += " AND e.season != 0"
        if params.pop("hide_watched", self.hide_watched):
            statement += " AND e.watched = 0"
        if minimum_episode:
            statement += " AND e.number >= {}".format(int(minimum_episode))
        statement += " order by e.season, e.number "
        return self.execute_sql(statement).fetchall()

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
        in_predicate = ",".join(
            [str(i["trakt_id"]) for i in trakt_items if i["trakt_id"] is not None]
        )
        if g.get_bool_setting("general.showRemainingUnwatched"):
            query = """SELECT e.trakt_id, e.info, e.cast, e.art, e.args, e.watched as play_count, b.resume_time as 
            resume_time, b.percent_played as percent_played, se.watched_episodes, se.unwatched_episodes, 
            se.episode_count FROM episodes as e INNER JOIN seasons se on e.trakt_season_id = se.trakt_id
            LEFT JOIN bookmarks as b on e.Trakt_id = b.Trakt_id WHERE e.trakt_id in ({})""".format(
                in_predicate
            )
        else:
            query = """SELECT e.trakt_id, e.info, e.cast, e.art, e.args, e.watched as play_count, b.resume_time as 
            resume_time, b.percent_played as percent_played FROM episodes as e LEFT JOIN bookmarks as b on e.Trakt_id = 
            b.Trakt_id WHERE e.trakt_id in ({})""".format(
                in_predicate
            )

        if params.pop("hide_unaired", self.hide_unaired):
            query += " AND Datetime(e.air_date) < Datetime('now') "
        if params.pop("hide_specials", self.hide_specials):
            query += " AND e.season != 0"
        if params.pop("hide_watched", self.hide_watched):
            query += " AND e.watched = 0"

        return MetadataHandler.sort_list_items(
            self.execute_sql(query).fetchall(), trakt_items
        )

    @guard_against_none()
    def _get_single_show_meta(self, trakt_id):
        return self._get_single_meta("/shows/{}".format(trakt_id), trakt_id, "shows")

    @guard_against_none(list)
    def get_show(self, trakt_id):
        """
        Returns a single show record from the database with full meta
        :param trakt_id: Shows Trakt ID
        :type trakt_id: int
        :return: Show item with full meta
        :rtype: dict
        """
        return self.get_show_list([self._get_single_show_meta(trakt_id)])[0]

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
        return self.get_season_list(trakt_show_id, trakt_id)[0]

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
        result = self.get_episode_list(trakt_show_id, trakt_id=trakt_id)
        result = result[0]
        result.update(
            self.execute_sql(
                """select s.season_count, s.episode_count as show_episode_count, 
        se.episode_count, se.is_airing, a.absoluteNumber from episodes as e INNER JOIN seasons as se on se.trakt_id = 
        e.trakt_season_id INNER JOIN shows as s on s.trakt_id = e.trakt_show_id INNER JOIN 
        (select e.trakt_show_id, count(distinct e.trakt_id) as absoluteNumber from episodes as e inner join 
        (select e.trakt_show_id, (e.season*10 + e.number) as identifier from episodes as e where e.trakt_id = ?) as 
        agg on agg.trakt_show_id = e.trakt_show_id and agg.identifier >= (e.season*10 + number) group by 
        e.trakt_show_id) as a on a.trakt_show_id = e.trakt_show_id WHERE e.trakt_id = ?""",
                (trakt_id, trakt_id),
            ).fetchone()
        )
        return result

    def _repair_missing_trakt_items(self, list_to_update, media_type):
        trakt_object = MetadataHandler.trakt_object

        missing_trakt = [item for item in list_to_update if trakt_object(item) is None]
        if len(missing_trakt) > 0:
            [
                self.task_queue.put(
                    self._update_single_meta,
                    "{}/{}".format(media_type, show.get("trakt_id")),
                    show,
                    media_type,
                )
                for show in missing_trakt
            ]
            self.task_queue.wait_completion()
            self.update_missing_trakt_objects(list_to_update, missing_trakt)

        return list_to_update

    @guard_against_none(list)
    def _update_objects(self, list_to_update, db_list_to_update, media_type):

        self.update_missing_trakt_objects(db_list_to_update, list_to_update)
        db_list_to_update = self._repair_missing_trakt_items(
            db_list_to_update, media_type
        )

        [self.task_queue.put(self.metadataHandler.update, i) for i in db_list_to_update]
        updated_items = self.task_queue.wait_completion()

        if updated_items is None:
            return

        updated_items = [i for i in updated_items if i is not None]

        self.save_to_meta_table(
            (i for i in updated_items if "trakt_object" in i),
            media_type,
            "trakt",
            "trakt_id",
        )
        self.save_to_meta_table(
            (i for i in updated_items if "tmdb_object" in i),
            media_type,
            "tmdb",
            "tmdb_id",
        )
        self.save_to_meta_table(
            (i for i in updated_items if "tvdb_object" in i),
            media_type,
            "tvdb",
            "tvdb_id",
        )
        self.save_to_meta_table(
            (i for i in updated_items if "fanart_object" in i),
            media_type,
            "fanart",
            "tvdb_id",
        )
        self.save_to_meta_table(
            (i for i in updated_items if "omdb_object" in i),
            media_type,
            "omdb",
            "imdb_id",
        )

        return updated_items

    def _format_objects(self, updated_items):
        return self.metadataHandler.format_db_object(updated_items)

    @guard_against_none_or_empty()
    def _update_shows(self, list_to_update):
        get = MetadataHandler.get_trakt_info
        sql_statement = """WITH requested(trakt_id, last_updated) AS (VALUES {}) select r.trakt_id, trakt.value as 
        trakt_object, trakt.meta_hash as trakt_meta_hash, tmdb_id, tmdb.value as tmdb_object, tmdb.meta_hash as 
        tmdb_meta_hash, tvdb_id, tvdb.value as tvdb_object, tvdb.meta_hash as tvdb_meta_hash, fanart.value as 
        fanart_object, fanart.meta_hash as fanart_meta_hash, s.imdb_id, omdb.value as omdb_object, omdb.meta_hash as 
        omdb_meta_hash, CASE WHEN s.last_updated is null or (Datetime(s.last_updated) < Datetime(r.last_updated)) 
        THEN 'true' else 'false' END as NeedsUpdate FROM requested as r LEFT JOIN shows as s on r.trakt_id = 
        s.trakt_id LEFT JOIN shows_meta as trakt on trakt.id = s.trakt_id and trakt.type = 'trakt' LEFT JOIN 
        shows_meta as tmdb on tmdb.id = s.tmdb_id and tmdb.type = 'tmdb' LEFT JOIN shows_meta as tvdb on tvdb.id = 
        s.tvdb_id and tvdb.type = 'tvdb' LEFT JOIN shows_meta as fanart on fanart.id = s.tvdb_id and fanart.type = 
        'fanart' LEFT JOIN shows_meta as omdb on omdb.id = s.imdb_id and omdb.type = 'omdb' """.format(
            ",".join(
                "({},'{}')".format(
                    i.get("trakt_show_id", i.get("trakt_id")), get(i, "dateadded")
                )
                for i in list_to_update
            )
        )

        db_list_to_update = self.execute_sql(sql_statement).fetchall()
        updated_items = self._update_objects(
            list_to_update, db_list_to_update, "shows"
        )

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
                    i["info"]["trakt_id"],
                )
                for i in formatted_items
            ),
        )

    def _update_mill_format_shows(self, trakt_list, mill_episodes=False):
        if not trakt_list or len(trakt_list) == 0:
            return
        trakt_list = trakt_list if isinstance(trakt_list, list) else [trakt_list]
        self.parent_task_queue.put(self._update_shows, self.filter_items_that_needs_updating(trakt_list, 'shows'))
        self.parent_task_queue.put(self._mill_if_needed, trakt_list, None, mill_episodes)

        self.parent_task_queue.wait_completion()

    @guard_against_none_or_empty()
    def _identify_seasons_to_update(self, list_to_update):
        get = MetadataHandler.get_trakt_info
        sql_statement = """WITH requested(trakt_id, last_updated) AS (VALUES {}) SELECT r.trakt_id as trakt_id, 
        trakt.value as trakt_object, trakt.meta_hash as trakt_meta_hash, sh.tmdb_id as tmdb_show_id, se.tmdb_id as 
        tmdb_id, tmdb.value as tmdb_object, tmdb.meta_hash as tmdb_meta_hash, sh.tvdb_id as tvdb_show_id, se.tvdb_id 
        as tvdb_id, tvdb.value as tvdb_object, tvdb.meta_hash as tvdb_meta_hash, fanart.value as fanart_object, 
        fanart.meta_hash as fanart_meta_hash, sh.imdb_id, omdb.value as omdb_object, omdb.meta_hash as omdb_meta_hash, 
        sh.info as show_info, sh.art as show_art, sh.cast as show_cast, CASE WHEN se.last_updated is null or (
        Datetime(se.last_updated) < Datetime(r.last_updated)) THEN 'true' else 'false' END as NeedsUpdate FROM 
        requested as r LEFT JOIN seasons as se on r.trakt_id = se.trakt_id LEFT JOIN shows as sh on sh.trakt_id = 
        se.trakt_show_id LEFT JOIN seasons_meta as trakt on trakt.id = se.trakt_id and trakt.type = 'trakt' LEFT JOIN 
        seasons_meta as tmdb on tmdb.id = se.tmdb_id and tmdb.type = 'tmdb' LEFT JOIN seasons_meta as tvdb on tvdb.id 
        = se.tvdb_id and tvdb.type = 'tvdb' LEFT JOIN seasons_meta as fanart on fanart.id = se.tvdb_id and 
        fanart.type = 'fanart' LEFT JOIN seasons_meta as omdb on omdb.id = sh.imdb_id and omdb.type = 'omdb' 
        """.format(
            ",".join(
                "({},'{}')".format(i.get("trakt_id"), get(i, "dateadded"))
                for i in list_to_update
            )
        )

        return self.execute_sql(sql_statement).fetchall()

    @guard_against_none_or_empty()
    def _update_seasons(self, list_to_update):
        db_list_to_update = self._identify_seasons_to_update(list_to_update)
        if db_list_to_update is None:
            db_list_to_update = []

        return self._update_objects(list_to_update, db_list_to_update, "seasons")

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
                    i["info"]["trakt_id"],
                )
                for i in formatted_items
            ),
        )

    @guard_against_none_or_empty()
    def _identify_episodes_to_update(self, list_to_update):
        get = MetadataHandler.get_trakt_info
        query = """WITH requested(trakt_id, last_updated) AS (VALUES {}) SELECT r.trakt_id as trakt_id, 
        ep.trakt_season_id, ep.trakt_show_id, trakt.value as trakt_object, trakt.meta_hash as trakt_meta_hash, 
        ep.tmdb_id as tmdb_id, tmdb.value as tmdb_object, tmdb.meta_hash as tmdb_meta_hash, ep.tvdb_id as tvdb_id, 
        tvdb.value as tvdb_object, tvdb.meta_hash as tvdb_meta_hash, fanart.value as fanart_object, fanart.meta_hash 
        as fanart_meta_hash, ep.imdb_id, omdb.value as omdb_object, omdb.meta_hash as omdb_meta_hash, sh.tmdb_id as 
        tmdb_show_id, sh.tvdb_id as tvdb_show_id, sh.info as show_info, sh.art as show_art, sh.cast as show_cast, 
        ep.trakt_season_id, se.tmdb_id as tmdb_season_id, sh.tvdb_id as tvdb_season_id, se.info as season_info, 
        se.art as season_art, se.cast as season_cast, CASE WHEN ep.last_updated is null or (Datetime(ep.last_updated) 
        < Datetime(r.last_updated)) THEN 'true' else 'false' END as NeedsUpdate FROM requested as r LEFT JOIN 
        episodes as ep on r.trakt_id = ep.trakt_id LEFT JOIN shows as sh on sh.trakt_id = ep.trakt_show_id LEFT JOIN 
        seasons as se on se.trakt_id = ep.trakt_season_id LEFT JOIN episodes_meta as trakt on trakt.id = ep.trakt_id 
        and trakt.type = 'trakt' LEFT JOIN episodes_meta as tmdb on tmdb.id = ep.tmdb_id and tmdb.type = 'tmdb' LEFT 
        JOIN episodes_meta as tvdb on tvdb.id = ep.tvdb_id and tvdb.type = 'tvdb' LEFT JOIN episodes_meta as fanart 
        on fanart.id = ep.tvdb_id and fanart.type = 'fanart' LEFT JOIN episodes_meta as omdb on omdb.id = ep.imdb_id 
        and omdb.type = 'omdb' """.format(
            ",".join(
                "({},'{}')".format(i.get("trakt_id"), get(i, "dateadded"))
                for i in list_to_update
            )
        )

        return self.execute_sql(query).fetchall()

    @guard_against_none_or_empty()
    def _update_episodes(self, list_to_update):
        db_list_to_update = self._identify_episodes_to_update(list_to_update)

        if db_list_to_update is None:
            db_list_to_update = []

        return self._update_objects(list_to_update, db_list_to_update, "episodes")

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
                    self.metadataHandler.meta_hash,
                    i["info"]["trakt_id"],
                )
                for i in formatted_items
            ),
        )

    @guard_against_none(None, 1)
    def _try_update_seasons(self, trakt_show_id, trakt_season_id=None):
        show_meta = self._get_single_show_meta(trakt_show_id)
        self._update_mill_format_shows(show_meta, True)
        query = """SELECT s.trakt_id, value as trakt_object, s.trakt_show_id, sh.tmdb_id as tmdb_show_id, sh.tvdb_id 
        as tvdb_show_id FROM seasons as s INNER JOIN shows as sh on s.trakt_show_id = sh.trakt_id LEFT JOIN 
        seasons_meta as m on m.id = s.trakt_id and m.type = \'trakt\' where """

        if trakt_season_id is not None:
            query += "s.trakt_id = {}".format(trakt_season_id)
        else:
            query += "sh.trakt_id = {}".format(trakt_show_id)

        seasons_to_update = self.filter_items_that_needs_updating(
            self.execute_sql(query).fetchall(), "seasons"
            )

        self._update_seasons(seasons_to_update)
        self._format_seasons(seasons_to_update)

    @guard_against_none(None, 1, 2)
    def _try_update_episodes(self, trakt_show_id, trakt_season_id=None, trakt_id=None):
        show_meta = self._get_single_show_meta(trakt_show_id)
        self._update_mill_format_shows(show_meta, True)
        query = """SELECT value as trakt_object, e.trakt_id, e.trakt_show_id, sh.tmdb_id as tmdb_show_id, sh.tvdb_id 
        as tvdb_show_id FROM episodes as e INNER JOIN shows as sh on e.trakt_show_id = sh.trakt_id INNER JOIN 
        episodes_meta as m on m.id = e.trakt_id and m.type='trakt' where """

        if trakt_id is not None:
            query += "e.trakt_id = {}".format(trakt_id)
        elif trakt_season_id is not None:
            query += "e.trakt_season_id = {}".format(trakt_season_id)
        else:
            query += "sh.trakt_id = {}".format(trakt_show_id)

        episodes_to_update = self.filter_items_that_needs_updating(
            self.execute_sql(query).fetchall(), "episodes"
            )

        self._update_episodes(episodes_to_update)
        self._format_episodes(episodes_to_update)

    @guard_against_none()
    def _try_update_mixed_episodes(self, trakt_items):
        self.insert_trakt_shows(
            self.filter_trakt_items_that_needs_updating(
                [i.get("show") for i in trakt_items if i.get("show")], "shows",
            )
        )

        if [i for i in trakt_items if not i.get("show")]:
            [
                self.task_queue.put(self._get_single_show_meta, i["trakt_show_id"])
                for i in trakt_items
                if not i.get("show")
            ]
            self.task_queue.wait_completion()

        shows = self.execute_sql(
            """SELECT value as trakt_object, s.trakt_id, s.tvdb_id, s.tmdb_id FROM shows as s 
        INNER JOIN shows_meta as m on m.id = s.trakt_id and  m.type='trakt' where s.trakt_id in ({})""".format(
                ",".join(str(i.get("trakt_show_id")) for i in trakt_items)
            )
        ).fetchall()

        self._update_mill_format_shows(shows, True)

        seasons_to_update = self.filter_items_that_needs_updating(
                self.execute_sql(
                    """SELECT value as trakt_object, se.trakt_id, se.trakt_show_id, sh.tmdb_id as tmdb_show_id, 
                    sh.tvdb_id as tvdb_show_id FROM seasons as se INNER JOIN shows as sh on se.trakt_show_id = 
                    sh.trakt_id INNER JOIN seasons_meta as sm on sm.id = se.trakt_id and sm.type='trakt' where 
                    se.trakt_id in (select e.trakt_season_id FROM episodes e where e.trakt_id in ({}))""".format(
                        ",".join(str(i.get("trakt_id")) for i in trakt_items)
                    )
                ).fetchall(),
                "seasons",
            )

        episodes_to_update = self.filter_items_that_needs_updating(
            self.execute_sql(
                """SELECT value as trakt_object, 
        e.trakt_id, e.trakt_show_id, sh.tmdb_id as tmdb_show_id, sh.tvdb_id as tvdb_show_id FROM episodes as e INNER 
        JOIN shows as sh on e.trakt_show_id = sh.trakt_id INNER JOIN episodes_meta as em on em.id = e.trakt_id and 
        em.type='trakt' where e.trakt_id in ({})""".format(
                        ",".join(str(i.get("trakt_id")) for i in trakt_items)
                    )
                ).fetchall(),
                "episodes",
            )

        self.parent_task_queue.put(self._update_seasons, seasons_to_update)
        self.parent_task_queue.put(self._update_episodes, episodes_to_update)

        self.parent_task_queue.wait_completion()

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
        query = """SELECT e.trakt_id, e.number AS episode_x, e.season AS season_x, e.trakt_show_id, em.value AS 
        episode, sm.value AS show, s.tmdb_id AS tmdb_show_id, s.tvdb_id AS tvdb_show_id, inner.last_watched_at, 
        e.air_date FROM episodes AS e INNER JOIN shows AS s ON s.trakt_id = e.trakt_show_id INNER JOIN (SELECT 
        e.trakt_show_id, Min(e.season) AS season, Min(e.number) AS number, nw.last_watched_at AS last_watched_at FROM 
        episodes AS e INNER JOIN (SELECT e.trakt_show_id, CASE WHEN Max(e.season) == max_watched_season AND Max(
        e.number) == max_watched_episode_number THEN 1 ELSE Min(e.season) END AS season, CASE WHEN Max(e.season) == 
        max_watched_season AND Max(e.number) == max_watched_episode_number THEN 1 ELSE Max(e.number) END AS number, 
        mw.last_watched_at AS last_watched_at FROM episodes e LEFT JOIN (SELECT mw_se.trakt_show_id, 
        Max(mw_se.season) AS max_watched_season, mw_ep.number AS max_watched_episode_number, mw_ep.last_watched_at AS 
        last_watched_at FROM episodes AS mw_se INNER JOIN (SELECT trakt_show_id, season, Max(number) AS number, 
        Max(last_watched_at) AS last_watched_at FROM episodes WHERE watched = 1 AND season > 0 GROUP BY 
        trakt_show_id, season) AS mw_ep ON mw_se.trakt_show_id = mw_ep.trakt_show_id AND mw_se.season = mw_ep.season 
        GROUP BY mw_se.trakt_show_id) AS mw ON e.trakt_show_id = mw.trakt_show_id WHERE (e.season = 
        mw.max_watched_season AND e.number = mw.max_watched_episode_number + 1 AND watched = 0) OR (e.season = 
        mw.max_watched_season + 1 AND e.number = 1) GROUP BY e.trakt_show_id) AS nw ON (e.trakt_show_id == 
        nw.trakt_show_id AND e.season == nw.season AND e.number >= nw.number) WHERE e.season > 0 AND watched = 0 AND 
        e.trakt_show_id NOT IN (SELECT trakt_id AS trakt_show_id FROM hidden WHERE SECTION IN ('progress_watched')) 
        AND Datetime(air_date) < Datetime('now') GROUP BY e.trakt_show_id) AS INNER ON e.trakt_show_id == 
        inner.trakt_show_id AND e.season == inner.season AND e.number == inner.number LEFT JOIN episodes_meta AS em 
        ON e.trakt_id = em.id AND em.TYPE = 'trakt' LEFT JOIN shows_meta AS sm ON e.trakt_show_id = sm.id AND sm.TYPE 
        = 'trakt' """
        if sort_by_last_watched:
            query += " ORDER BY inner.last_watched_at DESC"
        else:
            query += " ORDER BY e.air_date DESC"
        results = self.execute_sql(query).fetchall()
        return self.wrap_in_trakt_object(results)

    def get_watched_episodes(self, page=1):
        """
        Get watched episodes from database
        :param page: Page to request
        :type page: int
        :return: List of episode objects
        :rtype: list
        """
        return self.wrap_in_trakt_object(
            self.execute_sql(
                """SELECT e.trakt_id, e.number as episode_x, e.season as 
        season_x, e.trakt_show_id, em.value AS episode, sm.value AS show, s.tmdb_id AS tmdb_show_id, s.tvdb_id AS 
        tvdb_show_id, e.last_watched_at FROM episodes AS e inner join shows AS s ON s.trakt_id = e.trakt_show_id left 
        join episodes_meta AS em ON e.trakt_id = em.id AND em.TYPE = 'trakt' left join shows_meta AS sm ON 
        e.trakt_show_id = sm.id AND sm.TYPE = 'trakt' order by e.last_watched_at desc LIMIT {} OFFSET {} """.format(
                    self.page_limit, self.page_limit * (page - 1)
                )
            ).fetchall()
        )

    def get_unfinished_collected_shows(self, page=1):
        """
        Returns a list of shows the user has collected but not completed watching
        :param page: Page to request
        :type page: int
        :return: List of show objects
        :rtype: list
        """
        return self.execute_sql(
            """select m.id as trakt_id, value as trakt_object from shows_meta as m inner join(
        select ep.trakt_show_id, max(ep.collected_at) as collected_at from episodes as ep where ep.season != 0 and 
        ep.watched = 0 and ep.collected = 1 GROUP BY ep.trakt_show_id HAVING count(*) > 0) as u on u.trakt_show_id = 
        m.id and m.type='trakt' ORDER BY u.collected_at LIMIT {} OFFSET {} """.format(
                self.page_limit, self.page_limit * (page - 1)
            )
        ).fetchall()

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
        self.insert_trakt_shows(
            self.filter_trakt_items_that_needs_updating(show, "shows")
        )
        self._mill_if_needed(show)
        return self.execute_sql(
            """select trakt_id, trakt_show_id from seasons where trakt_show_id=? and season =? """,
            (trakt_show_id, season),
        ).fetchone()

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
        self.insert_trakt_shows(
            self.filter_trakt_items_that_needs_updating(show, "shows")
        )
        self._mill_if_needed(show)
        return self.execute_sql(
            """select trakt_id, trakt_show_id from episodes where trakt_show_id=? and season =? 
        and number=?""",
            (trakt_show_id, season, episode),
        ).fetchone()

