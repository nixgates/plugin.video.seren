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
    def extract_trakt_page(self, url, **params):
        return super(TraktSyncDatabase, self)._extract_trakt_page(
            url, "movies", **params
        )

    @guard_against_none(list)
    def get_movie_list(self, trakt_list, **params):
        self._update_movies(self.filter_items_that_needs_updating(trakt_list, "movies"))
        query = """SELECT m.trakt_id, m.info, m.art, m.cast, m.args, b.resume_time, b.percent_played, m.watched as 
        play_count FROM movies as m left join bookmarks as b on m.trakt_id = b.trakt_id WHERE m.trakt_id in ({})""".format(
            ",".join((str(i.get("trakt_id")) for i in trakt_list))
        )

        if params.get("hide_unaired", self.hide_unaired):
            query += " AND Datetime(air_date) < Datetime('now')"
        if params.get("hide_watched", self.hide_watched):
            query += " AND watched = 0"

        return MetadataHandler.sort_list_items(
            self.execute_sql(query).fetchall(), trakt_list
        )

    @guard_against_none(list)
    def get_collected_movies(self, page):
        paginate = g.get_bool_setting("general.paginatecollection")

        query = """SELECT m.trakt_id, meta.value as trakt_object FROM movies as m LEFT JOIN 
        movies_meta as meta on m.trakt_id = meta.id and meta.type = 'trakt' WHERE collected = 1 
        """

        if paginate:
            query += "ORDER BY collected_at desc LIMIT {} OFFSET {}".format(
                self.page_limit, self.page_limit * (page - 1)
            )

        return self.execute_sql(query).fetchall()

    @guard_against_none(list)
    def get_watched_movies(self, page):
        return self.execute_sql(
            """SELECT m.trakt_id, meta.value as trakt_object FROM movies as m LEFT JOIN 
        movies_meta as meta on m.trakt_id = meta.id and meta.type = 'trakt' WHERE watched = 1 
        ORDER BY last_watched_at desc LIMIT {} OFFSET {}""".format(
                self.page_limit, self.page_limit * (page - 1)
            )
        ).fetchall()

    def get_all_collected_movies(self):
        return self.execute_sql(
            """SELECT m.trakt_id, meta.value as trakt_object FROM movies as m LEFT JOIN 
        movies_meta as meta on m.trakt_id = meta.id and meta.type = 'trakt' WHERE collected = 1"""
        )

    @guard_against_none()
    def mark_movie_watched(self, trakt_id):
        play_count = self.execute_sql(
            "select watched from movies where trakt_id=?", (trakt_id,)
        ).fetchone()["watched"]
        self._mark_movie_record("watched", play_count + 1, trakt_id)

    @guard_against_none()
    def mark_movie_unwatched(self, trakt_id):
        self._mark_movie_record("watched", 0, trakt_id)

    @guard_against_none()
    def mark_movie_collected(self, trakt_id):
        self._mark_movie_record("collected", 1, trakt_id)

    @guard_against_none()
    def mark_movie_uncollected(self, trakt_id):
        self._mark_movie_record("collected", 0, trakt_id)

    @guard_against_none()
    def _mark_movie_record(self, column, value, trakt_id):
        if column == "watched":
            datetime_column = "last_watched_at"
        elif column == "collected":
            datetime_column = "collected_at"
        else:
            datetime_column = None
        if datetime_column is None:
            # Just in case we forgot any methods that call this
            raise TypeError("NoneType Error: Date Time Column")
        self.execute_sql(
            "UPDATE movies SET {}=?, {}='{}' WHERE trakt_id=?".format(
                column, datetime_column, self._get_datetime_now()
            ),
            (value, trakt_id),
        )

    def _fetch_movie_summary(self, trakt_id):
        return self.trakt_api.get_json_cached(
            "movies/{}".format(trakt_id), extended=True
        )

    @guard_against_none(list)
    def get_movie(self, trakt_id):
        return self.get_movie_list(
            [
                self.execute_sql(
                    """WITH requested(trakt_id) AS (VALUES ({})) select r.trakt_id as 
        trakt_id, db.value as trakt_object from requested as r left join movies_meta as db on r.trakt_id == db.id and 
        type = 'trakt' """.format(
                        trakt_id
                    )
                ).fetchone()
            ]
        )[0]

    @guard_against_none_or_empty()
    def _update_movies(self, list_to_update):
        trakt_object = MetadataHandler.trakt_object
        get = MetadataHandler.get_trakt_info

        missing_trakt = [
            movie
            for movie in list_to_update
            if trakt_object(movie) is None or trakt_object(movie) == {}
        ]
        if len(missing_trakt) > 0:
            [
                self.task_queue.put(
                    self._update_single_meta,
                    "movies/{}".format(movie.get("trakt_id")),
                    movie,
                    "movies",
                )
                for movie in missing_trakt
            ]
            self.task_queue.wait_completion()
            self.update_missing_trakt_objects(list_to_update, missing_trakt)

        sql_statement = """WITH requested(trakt_id, last_updated) AS (VALUES {}) SELECT r.trakt_id, trakt.value as  
        trakt_object, trakt.meta_hash as trakt_meta_hash, tmdb_id, tmdb.value as tmdb_object, tmdb.meta_hash as 
        tmdb_meta_hash, fanart.value as fanart_object, fanart.meta_hash as fanart_meta_hash, m.imdb_id, omdb.value as 
        omdb_object, omdb.meta_hash as omdb_meta_hash, CASE WHEN m.last_updated is null or (Datetime(m.last_updated) 
        < Datetime(r.last_updated)) THEN 'true' else 'false' END as NeedsUpdate FROM requested as r LEFT JOIN movies 
        as m on r.trakt_id = m.trakt_id LEFT JOIN movies_meta as trakt on trakt.id = m.trakt_id and trakt.type = 
        'trakt' LEFT JOIN movies_meta as tmdb on tmdb.id = m.tmdb_id and tmdb.type = 'tmdb' LEFT JOIN movies_meta as 
        fanart on fanart.id = m.tmdb_id and fanart.type = 'fanart' LEFT JOIN movies_meta as omdb on omdb.id = 
        m.imdb_id and omdb.type = 'omdb' """.format(
            ",".join(
                "({},'{}')".format(i.get("trakt_id"), get(i, "dateadded"))
                for i in list_to_update
            )
        )

        db_list_to_update = self.execute_sql(sql_statement).fetchall()

        self.update_missing_trakt_objects(db_list_to_update, list_to_update)

        [
            self.task_queue.put(self.metadataHandler.update, movie)
            for movie in db_list_to_update
        ]
        updated_items = self.task_queue.wait_completion()

        if not updated_items:
            return

        self.save_to_meta_table(
            (i for i in updated_items if "trakt_object" in i),
            "movies",
            "trakt",
            "trakt_id",
        )
        self.save_to_meta_table(
            (i for i in updated_items if "tmdb_object" in i),
            "movies",
            "tmdb",
            "tmdb_id",
        )
        self.save_to_meta_table(
            (i for i in updated_items if "fanart_object" in i),
            "movies",
            "fanart",
            "tmdb_id",
        )
        self.save_to_meta_table(
            (i for i in updated_items if "omdb_object" in i),
            "movies",
            "omdb",
            "imdb_id",
        )

        formatted_items = [
            i for i in self.metadataHandler.format_db_object(updated_items)
        ]

        self.execute_sql(
            self.upsert_movie_query,
            [
                (
                    i["info"]["trakt_id"],
                    i["info"],
                    i.get("art"),
                    i.get("cast"),
                    None,
                    None,
                    i["info"].get("aired"),
                    i["info"].get("dateadded"),
                    i["info"].get("tmdb_id"),
                    i["info"].get("imdb_id"),
                    self.metadataHandler.meta_hash,
                    self._create_args(i),
                    None,
                    None,
                    i["info"]["trakt_id"],
                )
                for i in formatted_items
            ],
        )
