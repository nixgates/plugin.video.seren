from resources.lib.database import trakt_sync
from resources.lib.modules.globals import g
from resources.lib.modules.guard_decorators import guard_against_none
from resources.lib.modules.guard_decorators import guard_against_none_or_empty
from resources.lib.modules.metadataHandler import MetadataHandler


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    def extract_trakt_page(self, url, **params):
        return super()._extract_trakt_page(url, "movies", **params)

    @guard_against_none(list)
    def get_movie_list(self, trakt_list, **params):
        self._update_movies(trakt_list)
        query = f"""
            SELECT m.trakt_id,
                   m.info,
                   m.art,
                   m.cast,
                   m.args,
                   b.resume_time,
                   b.percent_played,
                   m.watched AS play_count,
                   m.user_rating
            FROM movies AS m
                     LEFT JOIN bookmarks AS b
                               ON m.trakt_id = b.trakt_id
            WHERE m.trakt_id IN ({','.join(str(i.get('trakt_id')) for i in trakt_list)})
            """

        if params.get("hide_unaired", self.hide_unaired):
            query += f" AND Datetime(air_date) < Datetime('{self._get_datetime_now()}')"
        if params.get("hide_watched", self.hide_watched):
            query += " AND watched = 0"

        return MetadataHandler.sort_list_items(self.fetchall(query), trakt_list)

    @guard_against_none(list)
    def get_collected_movies(self, page):
        paginate = g.get_bool_setting("general.paginatecollection")

        query = """
            SELECT m.trakt_id, meta.value AS trakt_object
            FROM movies AS m
                     LEFT JOIN movies_meta AS meta
                               ON m.trakt_id = meta.id
            WHERE collected = TRUE
            """

        if paginate:
            query += f"ORDER BY collected_at desc LIMIT {self.page_limit} OFFSET {self.page_limit * (page - 1)}"

        return self.fetchall(query)

    @guard_against_none(list)
    def get_watched_movies(self, page):
        return self.fetchall(
            f"""
            SELECT m.trakt_id, meta.value AS trakt_object
            FROM movies AS m
                     LEFT JOIN movies_meta AS meta
                               ON m.trakt_id = meta.id
            WHERE watched = 1
            ORDER BY last_watched_at DESC
            LIMIT {self.page_limit} OFFSET {self.page_limit * (page - 1)}
            """
        )

    def get_all_collected_movies(self):
        return self.fetchall(
            """
            SELECT m.trakt_id, meta.value AS trakt_object
            FROM movies AS m
                     LEFT JOIN movies_meta AS meta
                         ON m.trakt_id = meta.id
            WHERE collected = TRUE
            """
        )

    @guard_against_none()
    def mark_movie_watched(self, trakt_id):
        play_count = self.fetchone("SELECT watched FROM movies WHERE trakt_id=?", (trakt_id,))["watched"]
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
            f"UPDATE movies SET {column}=?, {datetime_column}=? WHERE trakt_id=?",
            (value, self._get_datetime_now() if value > 0 else None, trakt_id),
        )

    def _fetch_movie_summary(self, trakt_id):
        return self.trakt_api.get_json_cached(f"movies/{trakt_id}", extended=True)

    @guard_against_none(list)
    def get_movie(self, trakt_id):
        return self.get_movie_list([self._get_single_movie_meta(trakt_id)], hide_unaired=False, hide_watched=False)[0]

    @guard_against_none()
    def _get_single_movie_meta(self, trakt_id):
        return self._get_single_meta(f"/movies/{trakt_id}", trakt_id, "movies")

    @guard_against_none_or_empty()
    def _update_movies(self, list_to_update):
        get = MetadataHandler.get_trakt_info

        sql_statement = f"""
            WITH requested(trakt_id, last_updated) AS (VALUES
                    {','.join(f"({i.get('trakt_id')},'{get(i, 'dateadded')}')" for i in list_to_update)})
            SELECT r.trakt_id,
                   trakt.value      AS trakt_object,
                   trakt.meta_hash  AS trakt_meta_hash,
                   tmdb_id,
                   tmdb.value       AS tmdb_object,
                   tmdb.meta_hash   AS tmdb_meta_hash,
                   fanart.value     AS fanart_object,
                   fanart.meta_hash AS fanart_meta_hash,
                   m.imdb_id,
                   omdb.value       AS omdb_object,
                   omdb.meta_hash   AS omdb_meta_hash,
                   m.needs_update
            FROM requested as r
                     LEFT JOIN movies AS m
                               ON r.trakt_id = m.trakt_id
                     LEFT JOIN movies_meta AS trakt
                               ON trakt.id = m.trakt_id AND trakt.type = 'trakt'
                     LEFT JOIN movies_meta AS tmdb
                               ON tmdb.id = m.tmdb_id AND tmdb.type = 'tmdb'
                     LEFT JOIN movies_meta AS omdb
                               ON omdb.id = m.imdb_id AND omdb.type = 'omdb'
                     LEFT JOIN movies_meta AS fanart
                               ON fanart.id = m.tmdb_id AND fanart.type = 'fanart'
            """

        db_list_to_update = self.fetchall(sql_statement)

        for movie in db_list_to_update:
            self.task_queue.put(self.metadataHandler.update, movie)
        updated_items = self.task_queue.wait_completion()

        if not updated_items:
            return

        self.task_queue.put(
            self.save_to_meta_table,
            (i for i in updated_items if "tmdb_object" in i),
            "movies",
            "tmdb",
            "tmdb_id",
        )
        self.task_queue.put(
            self.save_to_meta_table,
            (i for i in updated_items if "fanart_object" in i),
            "movies",
            "fanart",
            "tmdb_id",
        )
        self.task_queue.put(
            self.save_to_meta_table,
            (i for i in updated_items if "omdb_object" in i),
            "movies",
            "omdb",
            "imdb_id",
        )
        self.task_queue.wait_completion()

        formatted_items = self.metadataHandler.format_db_object(updated_items)

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
                    None,
                )
                for i in formatted_items
            ],
        )
