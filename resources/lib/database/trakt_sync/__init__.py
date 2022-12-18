import collections
import datetime
import json
import time
from functools import cached_property
from urllib import parse

import xbmcgui

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database import Database
from resources.lib.modules.exceptions import InvalidMediaTypeException
from resources.lib.modules.exceptions import UnsupportedProviderType
from resources.lib.modules.globals import g
from resources.lib.modules.metadataHandler import MetadataHandler
from resources.lib.modules.sync_lock import SyncLock

schema = {
    "shows_meta": {
        "columns": collections.OrderedDict(
            [
                ("id", ["INTEGER", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
                ("value", ["PICKLE", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(id, type)"],
        "default_seed": [],
    },
    "seasons_meta": {
        "columns": collections.OrderedDict(
            [
                ("id", ["INTEGER", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
                ("value", ["PICKLE", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(id, type)"],
        "default_seed": [],
    },
    "episodes_meta": {
        "columns": collections.OrderedDict(
            [
                ("id", ["INTEGER", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
                ("value", ["PICKLE", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(id, type)"],
        "default_seed": [],
    },
    "movies_meta": {
        "columns": collections.OrderedDict(
            [
                ("id", ["INTEGER", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
                ("value", ["PICKLE", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(id, type)"],
        "default_seed": [],
    },
    "shows": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("tvdb_id", ["INTEGER", "NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("imdb_id", ["INTEGER", "NULL"]),
                ("info", ["PICKLE", "NULL"]),
                ("cast", ["PICKLE", "NULL"]),
                ("art", ["PICKLE", "NULL"]),
                ("meta_hash", ["TEXT", "NULL"]),
                ("season_count", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("episode_count", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("unwatched_episodes", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("watched_episodes", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("last_updated", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("args", ["TEXT", "NOT NULL"]),
                ("air_date", ["TEXT"]),
                ("is_airing", ["BOOLEAN"]),
                ("last_watched_at", ["TEXT"]),
                ("last_collected_at", ["TEXT"]),
                ("user_rating", ["INTEGER", "NULL"]),
                ("needs_update", ["BOOLEAN", "NOT NULL", "DEFAULT 1"]),
                ("needs_milling", ["BOOLEAN", "NOT NULL", "DEFAULT 1"]),
            ]
        ),
        "table_constraints": [],
        "default_seed": [],
    },
    "seasons": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "NOT NULL"]),
                ("trakt_show_id", ["INTEGER", "NOT NULL"]),
                ("tvdb_id", ["INTEGER", "NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("season", ["INTEGER", "NOT NULL"]),
                ("info", ["PICKLE", "NULL"]),
                ("cast", ["PICKLE", "NULL"]),
                ("art", ["PICKLE", "NULL"]),
                ("meta_hash", ["TEXT", "NULL"]),
                ("episode_count", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("unwatched_episodes", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("watched_episodes", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("last_updated", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("args", ["TEXT", "NOT NULL"]),
                ("air_date", ["TEXT"]),
                ("is_airing", ["BOOLEAN"]),
                ("last_watched_at", ["TEXT"]),
                ("last_collected_at", ["TEXT"]),
                ("user_rating", ["INTEGER", "NULL"]),
                ("needs_update", ["BOOLEAN", "NOT NULL", "DEFAULT 1"]),
            ]
        ),
        "table_constraints": [
            "PRIMARY KEY(trakt_show_id, season)",
            "UNIQUE(trakt_id)"
            "FOREIGN KEY(trakt_show_id) REFERENCES shows(trakt_id) ON UPDATE CASCADE ON DELETE CASCADE",
        ],
        "default_seed": [],
    },
    "episodes": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "NOT NULL"]),
                ("trakt_show_id", ["INTEGER", "NOT NULL"]),
                ("trakt_season_id", ["INTEGER", "NOT NULL"]),
                ("season", ["INTEGER", "NOT NULL"]),
                ("tvdb_id", ["INTEGER", "NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("imdb_id", ["INTEGER", "NULL"]),
                ("info", ["PICKLE", "NULL"]),
                ("cast", ["PICKLE", "NULL"]),
                ("art", ["PICKLE", "NULL"]),
                ("meta_hash", ["TEXT", "NULL"]),
                ("last_updated", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("collected", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("watched", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("number", ["INTEGER", "NOT NULL"]),
                ("args", ["TEXT", "NOT NULL"]),
                ("air_date", ["TEXT"]),
                ("last_watched_at", ["TEXT"]),
                ("collected_at", ["TEXT"]),
                ("user_rating", ["INTEGER", "NULL"]),
                ("needs_update", ["BOOLEAN", "NOT NULL", "DEFAULT 1"]),
            ]
        ),
        "table_constraints": [
            "PRIMARY KEY(trakt_show_id, season, number)",
            "UNIQUE(trakt_id)"
            "FOREIGN KEY(trakt_season_id) REFERENCES seasons(trakt_id) ON UPDATE CASCADE ON DELETE CASCADE",
            "FOREIGN KEY(trakt_show_id) REFERENCES shows(trakt_id) ON UPDATE CASCADE ON DELETE CASCADE",
        ],
        "indices": [
            ("idx_episodes_showid", ["trakt_show_id"]),
            ("idx_episodes_seasonid", ["trakt_season_id"]),
            ("idx_episodes_showid_season_number_lastwatched", ["trakt_show_id", "season", "number", "last_watched_at"]),
            ("idx_episodes_season_number", ["season", "number"]),
            ("idx_episodes_collected", ["collected"]),
        ],
        "default_seed": [],
    },
    "movies": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("imdb_id", ["INTEGER", "NULL"]),
                ("info", ["PICKLE", "NULL"]),
                ("cast", ["PICKLE", "NULL"]),
                ("art", ["PICKLE", "NULL"]),
                ("meta_hash", ["TEXT", "NULL"]),
                ("last_updated", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("collected", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("watched", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("args", ["TEXT", "NOT NULL"]),
                ("air_date", ["TEXT"]),
                ("last_watched_at", ["TEXT"]),
                ("collected_at", ["TEXT"]),
                ("user_rating", ["INTEGER", "NULL"]),
                ("needs_update", ["BOOLEAN", "NOT NULL", "DEFAULT 1"]),
            ]
        ),
        "table_constraints": [],
        "indices": [
            ("idx_movies_collected", ["collected"]),
            ("idx_movies_watched_lastwatched", ["watched", "last_watched_at"]),
        ],
        "default_seed": [],
    },
    "hidden": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "NOT NULL"]),
                ("mediatype", ["TEXT", "NOT NULL"]),
                ("section", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY(trakt_id, trakt_id, mediatype, section)"],
        "indices": [("idx_hidden_section_mediatype", ["section", "mediatype"])],
        "default_seed": [],
    },
    "activities": {
        "columns": collections.OrderedDict(
            [
                ("sync_id", ["INTEGER", "PRIMARY KEY"]),
                (
                    "all_activities",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "shows_watched",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "movies_watched",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "shows_rated",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "movies_rated",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "shows_collected",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "movies_collected",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                ("hidden_sync", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                (
                    "shows_meta_update",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "movies_meta_update",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "movies_bookmarked",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                (
                    "episodes_bookmarked",
                    ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"],
                ),
                ("lists_sync", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("trakt_username", ["TEXT", "NULL"]),
                ("last_activities_call", ["INTEGER", "NOT NULL", "DEFAULT 1"]),
            ]
        ),
        "table_constraints": ["UNIQUE(sync_id)"],
        "default_seed": [],
    },
    "bookmarks": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("resume_time", ["TEXT", "NOT NULL"]),
                ("percent_played", ["TEXT", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("paused_at", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": [],
        "indices": [("idx_bookmarks_paused", ["paused_at"])],
        "default_seed": [],
    },
    "lists": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("name", ["TEXT", "NOT NULL"]),
                ("username", ["TEXT", "NOT NULL"]),
                ("last_updated", ["TEXT", "NOT NULL"]),
                ("movie", ["BOOLEAN", "NOT NULL"]),
                ("show", ["BOOLEAN", "NOT NULL"]),
                ("sort_by", ["TEXT", "NOT NULL"]),
                ("sort_how", ["TEXT", "NOT NULL"]),
                ("slug", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": [],
        "default_seed": [],
    },
}


class TraktSyncDatabase(Database):
    def __init__(
        self,
    ):
        super().__init__(g.TRAKT_SYNC_DB_PATH, schema)

        self.activities = {}
        self.item_list = []
        self.base_date = "1970-01-01T00:00:00"
        self.task_queue = ThreadPool()
        self.mill_task_queue = ThreadPool()
        self.refresh_activities()

        if self.activities is None:
            self.clear_all_meta(False)
            self.set_base_activities()

        self.notification_prefix = f"{g.ADDON_NAME}: Trakt"
        self.hide_unaired = g.get_bool_setting("general.hideUnAired")
        self.hide_specials = g.get_bool_setting("general.hideSpecials")
        self.hide_watched = g.get_bool_setting("general.hideWatched")
        self.date_delay = g.get_bool_setting("general.datedelay")
        self.page_limit = g.get_int_setting("item.limit")

    @cached_property
    def metadataHandler(self):
        from resources.lib.modules.metadataHandler import MetadataHandler

        return MetadataHandler()

    @cached_property
    def trakt_api(self):
        from resources.lib.indexers.trakt import TraktAPI

        return TraktAPI()

    def clear_specific_item_meta(self, trakt_id, media_type):
        if media_type in ["tvshow", "show"]:
            media_type = "shows"
        elif media_type == "movie":
            media_type = "movies"
        elif media_type == "episode":
            media_type = "episodes"
        elif media_type == "season":
            media_type = "seasons"

        if media_type not in ["shows", "movies", "seasons", "episodes"]:
            raise InvalidMediaTypeException(media_type)

        self.execute_sql(f"DELETE from {media_type}_meta where id=?", (trakt_id,))
        self.execute_sql(
            f"UPDATE {media_type} SET info=null, art=null, cast=null, meta_hash=null where trakt_id=?",
            (trakt_id,),
        )

    def _update_last_activities_call(self):
        self.execute_sql("UPDATE activities SET last_activities_call=? WHERE sync_id=1", (int(time.time()),))
        self.refresh_activities()

    def _insert_last_activities_column(self):
        self.execute_sql("ALTER TABLE activities ADD last_activities_call INTEGER NOT NULL DEFAULT 1")

    @staticmethod
    def _get_datetime_now():
        return g.datetime_to_string(datetime.datetime.utcnow())

    def refresh_activities(self):
        self.activities = self.fetchone("SELECT * FROM activities WHERE sync_id=1")

    def set_base_activities(self):
        self.execute_sql(
            "REPLACE INTO activities(sync_id, trakt_username) VALUES(1, ?)",
            (g.get_setting("trakt.username"),),
        )
        self.activities = self.fetchone("SELECT * FROM activities WHERE sync_id=1")

    def flush_activities(self, clear_meta=False):
        if clear_meta:
            self.clear_all_meta()
        self.execute_sql("DELETE FROM activities")
        self.set_base_activities()

    def clear_user_information(self, notify=True):
        username = self.activities["trakt_username"]
        self.execute_sql(
            [
                "UPDATE episodes SET watched=?",
                "UPDATE episodes SET collected=?",
                "UPDATE movies SET watched=?",
                "UPDATE movies SET collected=?",
                "UPDATE shows SET unwatched_episodes=?",
                "UPDATE shows SET watched_episodes=?",
                "UPDATE seasons SET unwatched_episodes=?",
                "UPDATE seasons SET watched_episodes=?",
            ],
            (0,),
        )
        self.execute_sql(
            [
                "UPDATE episodes SET last_watched_at=?",
                "UPDATE shows SET last_watched_at=?",
                "UPDATE seasons SET last_watched_at=?",
                "UPDATE movies SET last_watched_at=?",
            ],
            (None,),
        )
        self.execute_sql(
            [
                "UPDATE episodes SET collected_at=?",
                "UPDATE shows SET last_collected_at=?",
                "UPDATE seasons SET last_collected_at=?",
                "UPDATE movies SET collected_at=?",
            ],
            (None,),
        )
        self.execute_sql(
            [
                "DELETE from bookmarks WHERE TRUE",
                "DELETE from hidden WHERE TRUE",
            ]
        )
        self.execute_sql(
            [
                "UPDATE episodes SET user_rating=?",
                "UPDATE shows SET user_rating=?",
                "UPDATE seasons SET user_rating=?",
                "UPDATE movies SET user_rating=?",
            ],
            (None,),
        )
        self.execute_sql("DELETE from lists WHERE username=?", (username,))
        self.set_trakt_user("")
        self.set_base_activities()
        if notify:
            g.notification(self.notification_prefix, g.get_language_string(30270), time=5000)

    def set_trakt_user(self, trakt_username):
        g.log(f"Setting Trakt Username: {trakt_username}")
        self.execute_sql("UPDATE activities SET trakt_username=?", (trakt_username,))

    def clear_all_meta(self, notify=True):
        if notify:
            confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30179))
            if confirm == 0:
                return

        self.execute_sql(
            [
                "UPDATE shows SET info=?, cast=?, art=?, meta_hash=?",
                "UPDATE seasons SET info=?, cast=?, art=?, meta_hash=?",
                "UPDATE episodes SET info=?, cast=?, art=?, meta_hash=?",
                "UPDATE movies SET info=?, cast=?, art=?, meta_hash=?",
            ],
            (None, None, None, None),
        )

        self.execute_sql(
            [
                "DELETE FROM movies_meta",
                "DELETE FROM shows_meta",
                "DELETE FROM seasons_meta",
                "DELETE FROM episodes_meta",
            ]
        )
        if notify:
            g.notification(self.notification_prefix, g.get_language_string(30271), time=5000)

    def re_build_database(self, silent=False):
        if not silent:
            confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30179))
            if confirm == 0:
                return

        self.rebuild_database()
        self.set_base_activities()
        self.refresh_activities()

        from resources.lib.database.trakt_sync import activities

        if sync_errors := activities.TraktSyncDatabase().sync_activities(silent):
            g.notification(self.notification_prefix, g.get_language_string(30332), time=5000)
        elif sync_errors is None:
            self.refresh_activities()
        else:
            g.notification(self.notification_prefix, g.get_language_string(30272), time=5000)

    def save_to_meta_table(self, items, meta_type, provider_type, id_column):
        if items is None:
            return
        sql_statement = f"""
            INSERT INTO {meta_type}_meta (id, type, meta_hash, value) VALUES (?, ?, ?, ?)
            ON CONFLICT(id, type) DO UPDATE
                SET (meta_hash, value) = (excluded.meta_hash, excluded.value)
            """
        obj = None
        meta_hash = None
        if provider_type == "trakt":
            obj = MetadataHandler.trakt_object
            meta_hash = self.trakt_api.meta_hash
        elif provider_type == "tmdb":
            obj = MetadataHandler.tmdb_object
            meta_hash = self.metadataHandler.tmdb_api.meta_hash
        elif provider_type == "tvdb":
            obj = MetadataHandler.tvdb_object
            meta_hash = self.metadataHandler.tvdb_api.meta_hash
        elif provider_type == "fanart":
            obj = MetadataHandler.fanart_object
            meta_hash = self.metadataHandler.fanarttv_api.meta_hash
        elif provider_type == "omdb":
            obj = MetadataHandler.omdb_object
            meta_hash = self.metadataHandler.omdb_api.meta_hash

        if obj is None or meta_hash is None:
            raise UnsupportedProviderType(provider_type)

        self.execute_sql(
            sql_statement,
            (
                (i.get(id_column), provider_type, meta_hash, self.clean_meta(obj(i)))
                for i in items
                if (i and obj(i) and i.get(id_column) and MetadataHandler.full_meta_up_to_par(meta_type, obj(i)))
            ),
        )

        for i in items:
            if i and obj(i):
                if obj(i).get("seasons"):
                    self.save_to_meta_table(i.get("seasons"), "season", provider_type, id_column)
                if obj(i).get("episodes"):
                    self.save_to_meta_table(i.get("episodes"), "episode", provider_type, id_column)

    @staticmethod
    def clean_meta(item):
        if not item:
            return None

        result = {
            "info": {key: value for key, value in item.get("info", {}).items() if key not in ["seasons", "episodes"]},
            "art": item.get("art"),
            "cast": item.get("cast"),
        }

        if result.get("info") or result.get("art") or result.get("cast"):
            return result
        g.log(
            f"Bad Item meta discovered when cleaning - item: {item}",
            "error",
        )
        return None

    def _set_needs_update(self, items, media_type):
        update_list = self.fetchall(f"SELECT trakt_id from {media_type} WHERE needs_update")
        if not update_list:
            return
        update_set = {tid.get('trakt_id') for tid in update_list}
        for i in items:
            i["needs_update"] = i.get("trakt_id") in update_set

    def insert_trakt_movies(self, movies):
        if not movies:
            return

        to_insert = self._filter_trakt_items_that_needs_updating(movies, "movies")

        if not to_insert:
            return

        g.log(f"Inserting Movies into sync database: {len(to_insert)}")
        get = MetadataHandler.get_trakt_info
        self.execute_sql(
            self.upsert_movie_query,
            (
                (
                    i.get("trakt_id"),
                    None,
                    None,
                    None,
                    get(i, "collected"),
                    get(i, "watched"),
                    g.validate_date(get(i, "aired")),
                    g.validate_date(get(i, "dateadded")),
                    get(i, "tmdb_id"),
                    get(i, "imdb_id"),
                    None,
                    self._create_args(i),
                    g.validate_date(get(i, "collected_at")),
                    g.validate_date(get(i, "last_watched_at")),
                    get(i, "user_rating"),
                )
                for i in to_insert
            ),
        )
        self.save_to_meta_table(to_insert, "movies", "trakt", "trakt_id")
        self._set_needs_update(movies, "movies")

    def insert_trakt_shows(self, shows):
        if not shows:
            return

        to_insert = self._filter_trakt_items_that_needs_updating(shows, "shows")

        if not to_insert:
            return

        g.log(f"Inserting Shows into sync database: {len(to_insert)}")
        get = MetadataHandler.get_trakt_info
        self.execute_sql(
            self.upsert_show_query,
            (
                (
                    i.get("trakt_id"),
                    None,
                    None,
                    None,
                    g.validate_date(get(i, "aired")),
                    g.validate_date(get(i, "dateadded")),
                    get(i, "tmdb_id"),
                    get(i, "tvdb_id"),
                    get(i, "imdb_id"),
                    self.trakt_api.meta_hash,
                    get(i, "season_count"),
                    get(i, "episode_count"),
                    self._create_args(i),
                    get(i, "is_airing"),
                    g.validate_date(get(i, "last_watched_at")),
                    g.validate_date(get(i, "last_collected_at")),
                    get(i, "user_rating"),
                )
                for i in to_insert
            ),
        )
        self.save_to_meta_table(to_insert, "shows", "trakt", "trakt_id")
        self._set_needs_update(shows, "shows")

    def insert_trakt_episodes(self, episodes):
        if not episodes:
            return

        to_insert = self._filter_trakt_items_that_needs_updating(episodes, "episodes")

        if not to_insert:
            return
        g.log(f"Inserting episodes into sync database: {len(to_insert)}")
        get = MetadataHandler.get_trakt_info

        if missing_season_ids := [i for i in to_insert if not i.get("trakt_season_id")]:
            predicate = " OR ".join(
                [f"(trakt_show_id={get(i, 'trakt_show_id')} AND season={get(i, 'season')})" for i in missing_season_ids]
            )
            season_ids = self.fetchall(f"SELECT trakt_show_id, trakt_id, season FROM seasons WHERE {predicate}")
            season_ids = {f"{i['trakt_show_id']}-{i['season']}": i["trakt_id"] for i in season_ids}
            for i in to_insert:
                i["trakt_season_id"] = season_ids.get(f"{get(i, 'trakt_show_id')}-{get(i, 'season')}")

        self.execute_sql(
            self.upsert_episode_query,
            (
                (
                    i.get("trakt_id"),
                    i.get("trakt_show_id"),
                    i.get("trakt_season_id"),
                    get(i, "playcount"),
                    get(i, "collected"),
                    g.validate_date(get(i, "aired")),
                    g.validate_date(get(i, "dateadded")),
                    get(i, "season"),
                    get(i, "episode"),
                    get(i, "tmdb_id"),
                    get(i, "tvdb_id"),
                    get(i, "imdb_id"),
                    None,
                    None,
                    None,
                    self._create_args(i),
                    g.validate_date(get(i, "last_watched_at")),
                    g.validate_date(get(i, "collected_at")),
                    get(i, "user_rating"),
                    self.trakt_api.meta_hash,
                )
                for i in to_insert
            ),
        )
        self.save_to_meta_table(to_insert, "episodes", "trakt", "trakt_id")
        self._set_needs_update(episodes, "episodes")

    def insert_trakt_seasons(self, seasons):
        if not seasons:
            return

        to_insert = self._filter_trakt_items_that_needs_updating(seasons, "seasons")

        if not to_insert:
            return

        g.log(f"Inserting seasons into sync database: {len(to_insert)}")
        get = MetadataHandler.get_trakt_info
        self.execute_sql(
            self.upsert_season_query,
            (
                (
                    i.get("trakt_show_id"),
                    i.get("trakt_id"),
                    None,
                    None,
                    None,
                    g.validate_date(get(i, "aired")),
                    g.validate_date(get(i, "dateadded")),
                    get(i, "tmdb_id"),
                    get(i, "tvdb_id"),
                    self.trakt_api.meta_hash,
                    None,
                    get(i, "season"),
                    self._create_args(i),
                    g.validate_date(get(i, "last_watched_at")),
                    g.validate_date(get(i, "last_collected_at")),
                    get(i, "user_rating"),
                )
                for i in to_insert
            ),
        )
        self.save_to_meta_table(to_insert, "seasons", "trakt", "trakt_id")
        self._set_needs_update(seasons, "seasons")

    def _mill_if_needed(self, list_to_update, queue_wrapper=None, mill_episodes=True):
        if queue_wrapper is None:
            queue_wrapper = self._queue_mill_tasks

        ids_to_mill_check = ",".join(str(i.get("trakt_show_id", i.get("trakt_id"))) for i in list_to_update)
        now = self._get_datetime_now()

        query = f"""
            SELECT s.trakt_id, s.needs_milling, s.season_count, agg.meta_count, agg.tot_season_count, agg.tot_meta_count
            FROM shows AS s
                     LEFT JOIN(SELECT s.trakt_id,
                                      sum(CASE
                                              WHEN se.trakt_id IS NOT NULL
                                                  AND se.season != 0 AND Datetime(se.air_date) < Datetime('{now}')
                                                  THEN 1
                                              ELSE 0
                                          END)           AS season_count,
                                      sum(CASE
                                              WHEN sm.id IS NOT NULL
                                                  AND se.season != 0
                                                  AND Datetime(se.air_date) < Datetime('{now}')
                                                  THEN 1
                                              ELSE 0
                                          END)           AS meta_count,
                                      count(se.trakt_id) AS tot_season_count,
                                      count(sm.id)       AS tot_meta_count
                               FROM shows AS s
                                        INNER JOIN seasons AS se
                                                   ON s.trakt_id = se.trakt_show_id
                                        LEFT JOIN seasons_meta AS sm
                                                  ON sm.id = se.trakt_id
                                                      AND sm.type = 'trakt'
                                                      AND sm.meta_hash = '{self.trakt_api.meta_hash}'
                               WHERE s.trakt_id IN ({ids_to_mill_check})
                               GROUP BY s.trakt_id) AS agg
                              ON s.trakt_id = agg.trakt_id
            WHERE s.trakt_id IN ({ids_to_mill_check})
              AND (s.needs_milling
                OR (agg.season_count IS NULL OR agg.season_count != s.season_count)
                OR (agg.meta_count = 0 OR agg.meta_count != s.season_count)
                OR agg.tot_season_count != agg.tot_meta_count)
            """
        needs_milling = self.fetchall(query)
        if needs_milling is not None:
            needs_milling = {x.get('trakt_id') for x in needs_milling}
        else:
            needs_milling = set()

        if mill_episodes:
            query = f"""
                SELECT s.trakt_id,
                       s.episode_count,
                       agg.episode_count,
                       agg.meta_count,
                       agg.tot_episode_count,
                       agg.tot_meta_count
                FROM shows AS s
                         LEFT JOIN(SELECT s.trakt_id,
                                          sum(CASE
                                                  WHEN e.trakt_id IS NOT NULL
                                                      AND e.season != 0
                                                      AND Datetime(e.air_date) < Datetime('{now}')
                                                      THEN 1
                                              END)          AS episode_count,
                                          sum(CASE
                                                  WHEN em.id IS NOT NULL
                                                      AND e.season != 0
                                                      AND Datetime(e.air_date) < Datetime('{now}')
                                                      THEN 1
                                              END)          AS meta_count,
                                          count(e.trakt_id) AS tot_episode_count,
                                          count(em.id)      AS tot_meta_count
                                   FROM shows
                                            AS s
                                            INNER JOIn episodes AS e
                                                       ON s.trakt_id = e.trakt_show_id
                                            LEFT JOIN episodes_meta AS em
                                                      ON em.id = e.trakt_id
                                                          AND em.type = 'trakt'
                                                          AND em.meta_hash = '{self.trakt_api.meta_hash}'
                                   WHERE s.trakt_id IN ({ids_to_mill_check})
                                   GROUP BY s.trakt_id) AS agg ON s.trakt_id = agg.trakt_id
                WHERE s.trakt_id IN ({ids_to_mill_check})
                  AND ((agg.episode_count IS NULL OR agg.episode_count != s.episode_count)
                    OR (agg.meta_count = 0 OR agg.meta_count != s.episode_count)
                    OR agg.tot_episode_count != agg.tot_meta_count)
                """
            episodes_needs_milling = self.fetchall(query)
            if episodes_needs_milling is not None:
                needs_milling.update({x.get('trakt_id') for x in episodes_needs_milling})

        show_milling_count = len(needs_milling)
        if show_milling_count > 0:
            g.log(f"{show_milling_count} items require season milling", "debug")
        else:
            return

        self.mill_seasons(
            [i for i in list_to_update if i.get("trakt_show_id", i.get("trakt_id")) in needs_milling],
            queue_wrapper,
            mill_episodes,
        )

    def mill_seasons(self, trakt_collection, queue_wrapper, mill_episodes=False):
        with SyncLock(
            f"mill_seasons_episodes_{mill_episodes}",
            {show.get("trakt_show_id", show.get("trakt_id")) for show in trakt_collection},
        ) as sync_lock:
            # Everything we are milling may already be being milled in another process/thread
            # we need to check if there are any running IDs first.  The sync_lock wont exit until
            # the other process/thread is done with its milling giving good results.
            if len(sync_lock.running_ids) > 0:
                get = MetadataHandler.get_trakt_info
                trakt_info = MetadataHandler.trakt_info

                queue_wrapper(self._pull_show_seasons, [(i, mill_episodes) for i in sync_lock.running_ids])
                results = self.mill_task_queue.wait_completion()

                seasons = []
                episodes = []

                season_ids = {}
                episode_ids = {}

                for show in trakt_collection:
                    extended_seasons = {get(x, "season"): x for x in get(show, "seasons", [])}
                    # We make a dict here to ensure that the season numbers are unique due to a few bad trakt records.
                    for s_num, season in {get(x, "season"): x for x in results.get(show.get("trakt_id"), [])}.items():
                        trakt_info(season).update({"trakt_show_id": get(show, "trakt_id")})
                        trakt_info(season).update({"tmdb_show_id": get(show, "tmdb_id")})
                        trakt_info(season).update({"tvdb_show_id": get(show, "tvdb_id")})

                        season.update({"trakt_show_id": show.get("trakt_id")})
                        season.update({"tmdb_show_id": show.get("tmdb_id")})
                        season.update({"tvdb_show_id": show.get("tvdb_id")})

                        trakt_info(season).update({"dateadded": get(show, "dateadded")})
                        trakt_info(season).update({"tvshowtitle": get(show, "title")})

                        if s_num > 0:
                            show.update(
                                {
                                    "season_count": show.get("season_count", 0)
                                    + (1 if get(season, "aired_episodes", 0) > 0 else 0)
                                }
                            )
                            show.update(
                                {'episode_count': show.get("episode_count", 0) + get(season, "aired_episodes", 0)}
                            )

                        extended_season = extended_seasons.get(s_num)
                        if extended_season:
                            tools.smart_merge_dictionary(season, extended_season, keep_original=True)

                        seasons.append(season)
                        if get(show, "trakt_id") not in season_ids:
                            season_ids[get(show, "trakt_id")] = []

                        season_ids[get(show, "trakt_id")].append(get(season, "trakt_id"))

                        extended_episodes = {get(x, "episode"): x for x in get(extended_season, "episodes", [])}
                        for e_num, episode in {get(x, "episode"): x for x in get(season, "episodes", [])}.items():
                            trakt_info(episode).update({"trakt_show_id": get(show, "trakt_id")})
                            trakt_info(episode).update({"tmdb_show_id": get(show, "tmdb_id")})
                            trakt_info(episode).update({"tvdb_show_id": get(show, "tvdb_id")})
                            trakt_info(episode).update({"trakt_season_id": get(season, "trakt_id")})

                            episode.update({"trakt_show_id": show.get("trakt_id")})
                            episode.update({"tmdb_show_id": show.get("tmdb_id")})
                            episode.update({"tvdb_show_id": show.get("tvdb_id")})
                            episode.update({"trakt_season_id": season.get("trakt_id")})

                            trakt_info(episode).update({"tvshowtitle": get(show, "title")})

                            if extended_episode := extended_episodes.get(e_num):
                                tools.smart_merge_dictionary(episode, extended_episode, keep_original=True)

                            episodes.append(episode)
                            if get(show, "trakt_id") not in episode_ids:
                                episode_ids[get(show, "trakt_id")] = []

                            episode_ids[get(show, "trakt_id")].append(get(episode, "trakt_id"))

                self.insert_trakt_seasons(seasons)
                self.insert_trakt_episodes(episodes)

                if mill_episodes:
                    self.execute_sql(
                        [
                            f"""
                            DELETE FROM episodes
                            WHERE trakt_show_id = {trakt_id} AND trakt_id NOT IN ({','.join(map(str, episode))})
                            """
                            for trakt_id, episode in episode_ids.items()
                        ]
                    )

                self.execute_sql(
                    [
                        f"""
                        DELETE FROM seasons
                        WHERE trakt_show_id = {trakt_id} AND trakt_id NOT IN ({','.join(map(str, season))})
                        """
                        for trakt_id, season in season_ids.items()
                    ]
                )

                self.execute_sql(
                    "UPDATE shows SET episode_count=?, season_count=? WHERE trakt_id=? ",
                    (
                        (i.get("episode_count", 0), i.get("season_count", 0), i["trakt_id"])
                        for i in trakt_collection
                        if i["trakt_id"] in sync_lock.running_ids
                    ),
                )

                self.update_shows_statistics({"trakt_id": i} for i in sync_lock.running_ids)

                if mill_episodes:
                    self.update_season_statistics({"trakt_id": i['trakt_id']} for i in seasons)

                self.execute_sql(
                    f"UPDATE shows SET needs_milling=0 WHERE trakt_id IN ({','.join(map(str, sync_lock.running_ids))})"
                )

    def _filter_trakt_items_that_needs_updating(self, requested, media_type):
        if not requested:
            return requested

        get = MetadataHandler.get_trakt_info

        query_predicate = [
            f"({i.get('trakt_id')}, '{self.trakt_api.meta_hash}', '{get(i, 'dateadded')}')" for i in requested
        ]

        if not query_predicate:
            return []

        query = f"""
            WITH requested(trakt_id, meta_hash, updated_at) AS (VALUES {','.join(query_predicate)})
            SELECT r.trakt_id AS trakt_id
            FROM requested AS r
            LEFT JOIN {media_type} AS db
                      ON r.trakt_id == db.trakt_id
            LEFT JOIN {media_type}_meta AS m
                      ON db.trakt_id == id AND type = 'trakt'
            WHERE db.trakt_id IS NULL
                  OR m.value IS NULL
                  OR m.meta_hash != r.meta_hash
                  OR Datetime(db.last_updated) < Datetime(r.updated_at)
            """

        result = {r["trakt_id"] for r in self.fetchall(query)}

        media_record_type = media_type.rstrip('s')
        return [r.get(media_record_type, r) for r in requested if r.get("trakt_id") in result]

    def _pull_show_seasons(self, show_id, mill_episodes):
        return {
            show_id: self.trakt_api.get_json(
                f"/shows/{show_id}/seasons",
                extended="full,episodes" if mill_episodes else "full",
                translations=g.get_language_code() if g.get_language_code() != 'en' else None,
                timeout=(5, 30),
            )
        }

    @staticmethod
    def _create_args(item):
        get = MetadataHandler.get_trakt_info
        info = MetadataHandler.info
        args = {
            "trakt_id": get(item, "trakt_id", info(item).get("trakt_id")),
            "mediatype": get(item, "mediatype", info(item).get("mediatype")),
        }
        if args["trakt_id"] is None:
            import inspect

            g.log("Trakt ID not found in item!", "error")
            g.log(inspect.stack(), "error")
            g.log(item, "error")
        if args["mediatype"] == "season":
            args["trakt_show_id"] = get(item, "trakt_show_id", info(item).get("trakt_show_id"))
        if args["mediatype"] == "episode":
            args["trakt_show_id"] = get(item, "trakt_show_id", info(item).get("trakt_show_id"))
            args["trakt_season_id"] = get(item, "trakt_season_id", info(item).get("trakt_season_id"))
        return parse.quote(json.dumps(args, sort_keys=True))

    def _queue_mill_tasks(self, func, args):
        for arg in args:
            self.mill_task_queue.put(func, *arg)

    @staticmethod
    def requires_update(new_date, old_date):
        return tools.parse_datetime(new_date, False) > tools.parse_datetime(old_date, False)

    @staticmethod
    def wrap_in_trakt_object(items):
        for item in items:
            if item.get("show") is not None:
                info = item["show"].pop("info")
                item["show"].update({"trakt_id": info.get("trakt_id")})
                item["show"].update({"trakt_object": {"info": info}})
            if item.get("episode") is not None:
                info = item["episode"].pop("info")
                item["episode"].update({"trakt_id": info.get("trakt_id")})
                item["episode"].update({"tvdb_id": info.get("tvdb_id")})
                item["episode"].update({"tmdb_id": info.get("tmdb_id")})
                item["episode"].update({"trakt_object": {"info": info}})
        return items

    def _get_single_meta(self, trakt_url, trakt_id, media_type):
        return self._update_single_meta(
            trakt_url,
            self.fetchone(
                f"""
                SELECT id AS trakt_id, value AS trakt_object
                FROM {media_type}_meta
                WHERE id = ? AND type = 'trakt'
                """,
                (int(trakt_id),),
            ),
            media_type,
        )

    def _update_single_meta(self, trakt_url, item, media_type):
        trakt_object = MetadataHandler.trakt_object
        if item is None:
            item = {}
        if trakt_object(item) is None or trakt_object(item) == {}:
            new_object = self.trakt_api.get_json(trakt_url, extended="full")
            if media_type == "movies":
                self.insert_trakt_movies([new_object])
            elif media_type == "shows":
                self.insert_trakt_shows([new_object])
            elif media_type == "seasons":
                self.insert_trakt_seasons([new_object])
            elif media_type == "episodes":
                self.insert_trakt_episodes([new_object])
            item.update(new_object)
        return item

    def _extract_trakt_page(self, url, media_type, **params):
        result = []

        hide_watched = params.get("hide_watched", self.hide_watched)
        hide_unaired = params.get("hide_unaired", self.hide_unaired)
        get = MetadataHandler.get_trakt_info

        def _handle_page(current_page):
            if not current_page:
                return []
            if media_type == "movies":
                self.insert_trakt_movies(current_page)
            elif media_type == "shows":
                current_page = [i.get("show", i) for i in current_page]
                self.insert_trakt_shows(current_page)
            query = f"""
                WITH requested(trakt_id) AS (VALUES
                    {','.join('({})'.format(i.get('trakt_id', get(i, 'trakt_id'))) for i in current_page)})
                SELECT r.trakt_id AS trakt_id FROM requested AS r
                INNER JOIN {media_type} AS db
                    ON r.trakt_id == db.trakt_id
                LEFT JOIN {media_type}_meta AS m
                    ON db.trakt_id == id AND type = 'trakt'
                WHERE TRUE
                """
            if hide_unaired:
                query += f" AND Datetime(air_date) < Datetime('{self._get_datetime_now()}')"
            if hide_watched:
                if media_type == "movies":
                    query += " AND watched = 0"
                if media_type == "shows":
                    query += " AND watched_episodes < episode_count"
            result_ids = self.fetchall(query)
            result.extend(
                [
                    p
                    for p in current_page
                    if any(r for r in result_ids if p.get("trakt_id", get(p, "trakt_id")) == r.get("trakt_id"))
                ]
            )

        no_paging = params.get("no_paging", False)
        pull_all = params.pop("pull_all", False)
        ignore_cache = params.pop("ignore_cache", False)
        page_number = params.pop("page", 1)

        if pull_all:
            get_method = self.trakt_api.get_json if ignore_cache and no_paging else self.trakt_api.get_json_cached
            if ignore_cache and not no_paging and page_number == 1:
                params['overwrite_cache'] = True
            _handle_page(get_method(url, **params))
            if len(result) >= (self.page_limit * page_number) and not no_paging:
                return result[self.page_limit * (page_number - 1) : self.page_limit * page_number]
        else:
            params["limit"] = params.pop("page", self.page_limit)
            for page in self.trakt_api.get_all_pages_json(url, ignore_cache=ignore_cache, **params):
                _handle_page(page)
                if len(result) >= (self.page_limit * page_number) and not no_paging:
                    return result[self.page_limit * (page_number - 1) : self.page_limit * page_number]

        return result if no_paging else result[self.page_limit * (page_number - 1) :]

    def update_shows_statistics(self, trakt_list):
        self.__update_shows_statisics(trakt_list)

    def _update_all_shows_statisics(self):
        self.__update_shows_statisics()

    def __update_shows_statisics(self, trakt_list=None):
        now = self._get_datetime_now()
        if trakt_list:
            where_restriction_clause = f"WHERE trakt_id in ({','.join(str(i.get('trakt_id')) for i in trakt_list)})"
        else:
            where_restriction_clause = ""
        self.execute_sql(
            f"""
            UPDATE shows
            SET (
                    air_date, is_airing,
                    season_count, episode_count, watched_episodes, unwatched_episodes,
                    last_watched_at, last_collected_at
                    ) = (SELECT coalesce(CASE
                                             WHEN min(coalesce(e.air_date, datetime('9999-12-31T00:00:00'))
                                                      ) <> datetime('9999-12-31T00:00:00')
                                                 THEN min(e.air_date)
                                             END,
                                         s.air_date)               AS air_date,
                                coalesce(CASE
                                             WHEN max(e.trakt_id) IS NOT NULL
                                                 THEN CASE
                                                          WHEN e.season > 0 AND max(e.air_date) > datetime('{now}')
                                                              THEN 1
                                                          ELSE 0
                                                 END
                                             END, s.is_airing)     AS is_airing,
                                coalesce(CASE
                                             WHEN count(DISTINCT CASE
                                                                     WHEN e.season > 0
                                                                         AND Datetime(e.air_date) < Datetime('{now}')
                                                                         THEN season END) > 0
                                                 THEN count(DISTINCT CASE
                                                                         WHEN e.season > 0
                                                                             AND Datetime(e.air_date) < Datetime('{now}')
                                                                             THEN season END)
                                             END, s.season_count)  AS season_count,
                                coalesce(CASE
                                             WHEN max(e.trakt_id) IS NOT NULL
                                                 THEN sum(
                                                     CASE
                                                         WHEN e.season > 0
                                                             AND datetime(e.air_date) < datetime('{now}')
                                                             THEN 1
                                                         ELSE 0
                                                         END
                                                 )
                                             END, s.episode_count) AS episode_count,
                                coalesce(CASE
                                             WHEN max(e.trakt_id) IS NOT NULL
                                                 THEN sum(
                                                     CASE
                                                         WHEN e.season > 0 AND e.watched > 0
                                                             AND datetime(e.air_date) < datetime('{now}')
                                                             THEN 1
                                                         ELSE 0
                                                         END
                                                 )
                                             END,
                                         s.watched_episodes)       AS watched_episodes,
                                coalesce(CASE
                                             WHEN sum(CASE
                                                          WHEN e.season > 0
                                                              AND Datetime(e.air_date) < Datetime('{now}')
                                                              THEN 1 END) > s.episode_count
                                                 THEN sum(CASE
                                                              WHEN e.season > 0
                                                                  AND Datetime(e.air_date) < Datetime('{now}')
                                                                  THEN 1 END)
                                             ELSE s.episode_count
                                             END - sum(CASE
                                                           WHEN e.season > 0 AND e.watched > 0
                                                               AND Datetime(e.air_date) < Datetime('{now}')
                                                               THEN 1
                                                           ELSE 0
                                    END), s.unwatched_episodes)    AS unwatched_episodes,
                                CASE
                                    WHEN max(e.trakt_id) IS NOT NULL
                                        THEN max(e.last_watched_at)
                                    ELSE s.last_watched_at
                                    END                            AS last_watched_at,
                                CASE
                                    WHEN max(e.trakt_id) IS NOT NULL
                                        THEN max(e.collected_at)
                                    ELSE s.last_collected_at
                                    END                            AS last_collected_at
                         FROM shows AS s
                                  LEFT JOIN episodes AS e
                                            ON e.trakt_show_id = s.trakt_id
                         WHERE s.trakt_id = shows.trakt_id
                         GROUP BY e.trakt_show_id)
            {where_restriction_clause}
            """
        )

    def update_season_statistics(self, trakt_list):
        self.__update_season_statistics(trakt_list)

    def _update_all_season_statistics(self):
        self.__update_season_statistics()

    def __update_season_statistics(self, trakt_list=None):
        now = self._get_datetime_now()
        if trakt_list:
            where_restriction_clause = f"AND trakt_id in ({','.join(str(i.get('trakt_id')) for i in trakt_list)})"
        else:
            where_restriction_clause = ""
        self.execute_sql(
            f"""
            UPDATE seasons
            SET (
                    air_date, is_airing,
                    episode_count, watched_episodes, unwatched_episodes,
                    last_watched_at, last_collected_at
                    ) = (SELECT coalesce(
                                        CASE
                                            WHEN min(coalesce(e.air_date, datetime('9999-12-31T00:00:00'))
                                                     ) <> datetime('9999-12-31T00:00:00')
                                                THEN min(e.air_date)
                                            END,
                                        seasons.air_date
                                    )   as air_date,
                                CASE
                                    WHEN coalesce(
                                            CASE
                                                WHEN max(e.trakt_id) IS NOT NULL
                                                    THEN CASE
                                                             WHEN max(e.air_date) > datetime('{now}')
                                                                 THEN 1
                                                             ELSE 0
                                                    END
                                                END,
                                            seasons.is_airing
                                        )
                                        THEN coalesce(
                                            CASE
                                                WHEN max(e.trakt_id) IS NOT NULL
                                                    THEN CASE
                                                             WHEN max(e.air_date) > datetime('{now}')
                                                                 THEN 1
                                                             ELSE 0
                                                    END
                                                END,
                                            seasons.is_airing
                                        )
                                    ELSE 0
                                    END as is_airing,
                                CASE
                                    WHEN coalesce(
                                            CASE
                                                WHEN max(e.trakt_id) is not null
                                                    THEN sum(
                                                        CASE
                                                            WHEN datetime(e.air_date) < datetime('{now}')
                                                                THEN 1
                                                            ELSE 0
                                                            END
                                                    )
                                                END,
                                            seasons.episode_count
                                        ) IS NOT NULL
                                        THEN coalesce(
                                            CASE
                                                WHEN max(e.trakt_id) is not null
                                                    THEN sum(
                                                        CASE
                                                            WHEN datetime(e.air_date) < datetime('{now}')
                                                                THEN 1
                                                            ELSE 0
                                                            END
                                                    )
                                                END,
                                            seasons.episode_count
                                        )
                                    ELSE 0
                                    END AS episode_count,
                                CASE
                                    WHEN coalesce(
                                            CASE
                                                WHEN max(e.trakt_id) IS NOT NULL
                                                    THEN sum(
                                                        CASE
                                                            WHEN e.watched > 0
                                                                    AND datetime(e.air_date) < datetime('{now}')
                                                                THEN 1
                                                            ELSE 0
                                                            END
                                                    )
                                                END,
                                            seasons.watched_episodes
                                        ) IS NOT NULL
                                        THEN coalesce(
                                            CASE
                                                WHEN max(e.trakt_id) IS NOT NULL
                                                    THEN sum(
                                                        CASE
                                                            WHEN e.watched > 0
                                                                    AND datetime(e.air_date) < datetime('{now}')
                                                                THEN 1
                                                            ELSE 0
                                                            END
                                                    )
                                                END,
                                            seasons.watched_episodes
                                        )
                                    ELSE 0
                                    END AS watched_episodes,
                                CASE
                                    WHEN coalesce(
                                            CASE
                                                WHEN max(e.trakt_id) IS NOT NULL
                                                    THEN sum(
                                                        CASE
                                                            WHEN e.watched == 0
                                                                    AND datetime(e.air_date) < datetime('{now}')
                                                                THEN 1
                                                            ELSE 0
                                                            END
                                                    )
                                                END,
                                            seasons.unwatched_episodes
                                        ) IS NOT NULL
                                        THEN coalesce(
                                            CASE
                                                WHEN max(e.trakt_id) IS NOT NULL
                                                    THEN sum(
                                                        CASE
                                                            WHEN e.watched == 0
                                                                    AND datetime(e.air_date) < datetime('{now}')
                                                                THEN 1
                                                            ELSE 0
                                                            END
                                                    )
                                                END,
                                            seasons.unwatched_episodes
                                        )
                                    ELSE 0
                                    END AS unwatched_episodes,
                                CASE
                                    WHEN max(e.trakt_id) IS NOT NULL
                                        THEN max(e.last_watched_at)
                                    ELSE seasons.last_watched_at
                                    END AS last_watched_at,
                                CASE
                                    WHEN max(e.trakt_id) IS NOT NULL
                                        THEN max(e.collected_at)
                                    ELSE seasons.last_collected_at
                                    END AS last_collected_at
                         FROM episodes AS e
                         WHERE e.trakt_season_id = seasons.trakt_id
                         GROUP BY e.trakt_season_id)
            WHERE EXISTS(SELECT trakt_season_id FROM episodes AS ep WHERE ep.trakt_season_id = seasons.trakt_id)
            {where_restriction_clause}
            """
        )

    def clean_orphaned_metadata(self):
        media_meta_types = {
            "movies": ["trakt", "tmdb", "imdb", "fanart"],
            "episodes": ["trakt", "tmdb", "tvdb", "imdb", "fanart"],
            "seasons": ["trakt", "tmdb", "tvdb", "fanart"],
            "shows": ["trakt", "tmdb", "tvdb", "imdb", "fanart"],
        }
        for media_type in media_meta_types:
            for meta_type in media_meta_types[media_type]:
                if meta_type == "fanart":
                    self.execute_sql(self._clean_orphaned_fanart_metadata_query(media_type))
                else:
                    self.execute_sql(self._clean_orphaned_metadata_query(media_type, meta_type))

    def _clean_orphaned_metadata_query(self, media_type, meta_type):
        return f'''
            DELETE
            FROM {media_type}_meta
            WHERE type = '{meta_type}'
              AND id IN (SELECT id
                         FROM {media_type}_meta AS meta
                LEFT JOIN {media_type} AS media
                         ON media.{meta_type}_id = meta.id
                         WHERE meta.type = '{meta_type}'
                           AND media.{meta_type}_id IS NULL)
        '''

    def _clean_orphaned_fanart_metadata_query(self, media_type):
        if media_type == "movies":
            return f'''
                DELETE
                FROM {media_type}_meta
                WHERE type = 'fanart'
                  AND id IN (SELECT id
                             FROM {media_type}_meta AS meta
                                      LEFT JOIN {media_type} AS media ON media.imdb_id = meta.id OR media.tmdb_id = meta.id
                             WHERE meta.type = 'fanart'
                               AND media.imdb_id IS NULL
                               AND media.tmdb_id IS NULL)
            '''

        return f'''
            DELETE
            FROM {media_type}_meta
            WHERE type = 'fanart'
              AND id IN (SELECT id
                         FROM {media_type}_meta AS meta
                                  LEFT JOIN {media_type} AS media ON media.tvdb_id = meta.id
                         WHERE meta.type = 'fanart'
                           AND media.tvdb_id IS NULL)
        '''

    @property
    def upsert_movie_query(self):
        return """
                WITH new(trakt_id, info, art, cast, collected, watched, air_date,
                         last_updated, tmdb_id, imdb_id, meta_hash, args,
                         collected_at, last_watched_at, user_rating,
                         needs_update
                    ) AS (values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE))
                INSERT
                INTO movies(trakt_id, info, art, cast, collected, watched, air_date,
                            last_updated, tmdb_id, imdb_id, meta_hash, args,
                            collected_at, last_watched_at, user_rating,
                            needs_update)
                SELECT trakt_id,
                       info,
                       art,
                       [cast],
                       coalesce(collected, 0),
                       coalesce(watched, 0),
                       air_date,
                       coalesce(last_updated, '1970-01-01T00:00:00'),
                       tmdb_id,
                       imdb_id,
                       meta_hash,
                       coalesce(args, FALSE),
                       collected_at,
                       last_watched_at,
                       user_rating,
                       needs_update
                FROM new
                WHERE TRUE
                ON CONFLICT(trakt_id) DO UPDATE
                    SET (info, art, cast, collected, watched, air_date,
                            last_updated, tmdb_id, imdb_id, meta_hash,
                            args, collected_at, last_watched_at, user_rating,
                            needs_update) = (SELECT coalesce(new.info, old.info),
                                                    coalesce(new.art, old.art),
                                                    coalesce(new.cast, old.cast),
                                                    coalesce(new.collected, old.collected),
                                                    coalesce(new.watched, old.watched),
                                                    coalesce(new.air_date, old.air_date),
                                                    coalesce(new.last_updated, old.last_updated),
                                                    coalesce(new.tmdb_id, old.tmdb_id),
                                                    coalesce(new.imdb_id, old.imdb_id),
                                                    coalesce(new.meta_hash, old.meta_hash),
                                                    coalesce(new.args, old.args),
                                                    coalesce(new.collected_at, old.collected_at),
                                                    coalesce(new.last_watched_at, old.last_watched_at),
                                                    coalesce(new.user_rating, old.user_rating),
                                                    CASE
                                                        WHEN old.needs_update
                                                            THEN CASE
                                                                     WHEN new.info <> old.info
                                                                         OR new.art <> old.art
                                                                         OR new.cast <> old.cast
                                                                         THEN TRUE
                                                                     ELSE old.needs_update END
                                                        ELSE CASE
                                                                 WHEN Datetime(coalesce(old.last_updated, 0))
                                                                     < Datetime(new.last_updated)
                                                                     THEN TRUE
                                                                 ELSE FALSE END
                                                        END AS needs_update
                                             FROM new
                                                      LEFT JOIN movies AS old
                                                                ON old.trakt_id = new.trakt_id)
                """

    @property
    def upsert_show_query(self):
        return """
            WITH new(trakt_id, info, art, cast, air_date, last_updated,
                     tmdb_id, tvdb_id, imdb_id, meta_hash,
                     season_count, episode_count,
                     args, is_airing,
                     last_watched_at, last_collected_at, user_rating,
                     needs_update, needs_milling)
                     AS (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, TRUE))
            INSERT
            INTO shows(trakt_id, info, art, cast, air_date, last_updated,
                       tmdb_id, tvdb_id, imdb_id, meta_hash,
                       season_count, episode_count,
                       args, is_airing,
                       last_watched_at, last_collected_at, user_rating,
                       needs_update, needs_milling)
            SELECT trakt_id,
                   info,
                   art,
                   [cast],
                   air_date,
                   coalesce(last_updated, '1970-01-01T00:00:00'),
                   tmdb_id,
                   tvdb_id,
                   imdb_id,
                   meta_hash,
                   coalesce(season_count, 0),
                   coalesce(episode_count, 0),
                   coalesce(args, FALSE),
                   is_airing,
                   last_watched_at,
                   last_collected_at,
                   user_rating,
                   needs_update,
                   needs_milling
            FROM new
            WHERE TRUE
            ON CONFLICT(trakt_id) DO UPDATE
                SET (info, art, cast, air_date, last_updated,
                        tmdb_id, tvdb_id, imdb_id, meta_hash,
                        season_count, episode_count, watched_episodes, unwatched_episodes,
                        args, is_airing,
                        last_watched_at, last_collected_at, user_rating,
                        needs_update,
                        needs_milling) = (SELECT coalesce(new.info, old.info),
                                                 coalesce(new.art, old.art),
                                                 coalesce(new.cast, old.cast),
                                                 coalesce(new.air_date, old.air_date),
                                                 coalesce(new.last_updated, old.last_updated),
                                                 coalesce(new.tmdb_id, old.tmdb_id),
                                                 coalesce(new.tvdb_id, old.tvdb_id),
                                                 coalesce(new.imdb_id, old.imdb_id),
                                                 coalesce(new.meta_hash, old.meta_hash),
                                                 coalesce(new.season_count, old.season_count),
                                                 coalesce(new.episode_count, old.episode_count),
                                                 coalesce(old.watched_episodes, 0),
                                                 coalesce(old.unwatched_episodes, 0),
                                                 coalesce(new.args, old.args),
                                                 coalesce(new.is_airing, old.is_airing),
                                                 coalesce(new.last_watched_at, old.last_watched_at),
                                                 coalesce(new.last_collected_at, old.last_collected_at),
                                                 coalesce(new.user_rating, old.user_rating),
                                                 CASE
                                                     WHEN old.needs_update
                                                         THEN CASE
                                                                  WHEN new.info <> old.info
                                                                      OR new.art <> old.art
                                                                      OR new.cast <> old.cast
                                                                      THEN FALSE
                                                                  ELSE old.needs_update END
                                                     ELSE CASE
                                                              WHEN Datetime(coalesce(old.last_updated, 0))
                                                                  < Datetime(new.last_updated)
                                                                  THEN TRUE
                                                              ELSE FALSE END
                                                     END AS needs_update,
                                                 CASE
                                                     WHEN old.needs_milling THEN old.needs_milling
                                                     ELSE CASE
                                                              WHEN Datetime(coalesce(old.last_updated, 0))
                                                                  < Datetime(new.last_updated)
                                                                  THEN TRUE
                                                              ELSE FALSE END
                                                     END AS needs_milling
                                          FROM new
                                                   LEFT JOIN shows AS old
                                                             on old.trakt_id = new.trakt_id)
            """

    @property
    def upsert_season_query(self):
        return """
            WITH new(trakt_show_id, trakt_id, info, art, cast,
                     air_date, last_updated,
                     tmdb_id, tvdb_id, meta_hash, episode_count,
                     season, args,
                     last_watched_at, last_collected_at, user_rating,
                     needs_update) AS (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE))
            INSERT
            INTO seasons(trakt_show_id, trakt_id, info, art, cast,
                         air_date, last_updated,
                         tmdb_id, tvdb_id, meta_hash, episode_count,
                         season, args,
                         last_watched_at, last_collected_at, user_rating,
                         needs_update)
            SELECT trakt_show_id,
                   trakt_id,
                   info,
                   art,
                   [cast],
                   air_date,
                   coalesce(last_updated, '1970-01-01T00:00:00'),
                   tmdb_id,
                   tvdb_id,
                   meta_hash,
                   coalesce(episode_count, 0),
                   season,
                   coalesce(args, FALSE),
                   last_watched_at,
                   last_collected_at,
                   user_rating,
                   needs_update
            FROM new
            WHERE TRUE
            ON CONFLICT(trakt_show_id, season) DO UPDATE
                SET (trakt_id, info, art, cast,
                        air_date, last_updated,
                        tmdb_id, tvdb_id, meta_hash, episode_count,
                        args,
                        last_watched_at, last_collected_at, user_rating,
                        needs_update) = (SELECT new.trakt_id,
                                                coalesce(new.info, old.info),
                                                coalesce(new.art, old.art),
                                                coalesce(new.cast, old.cast),
                                                coalesce(new.air_date, old.air_date),
                                                coalesce(new.last_updated, old.last_updated),
                                                coalesce(new.tmdb_id, old.tmdb_id),
                                                coalesce(new.tvdb_id, old.tvdb_id),
                                                coalesce(new.meta_hash, old.meta_hash),
                                                coalesce(new.episode_count, old.episode_count),
                                                coalesce(new.args, old.args),
                                                coalesce(new.last_watched_at, old.last_watched_at),
                                                coalesce(new.last_collected_at, old.last_collected_at),
                                                coalesce(new.user_rating, old.user_rating),
                                                CASE
                                                    WHEN old.needs_update
                                                        THEN CASE
                                                                 WHEN new.info != old.info
                                                                     OR new.art != old.art
                                                                     OR new.cast != old.cast
                                                                     THEN FALSE
                                                                 ELSE old.needs_update END
                                                    ELSE CASE
                                                             WHEN Datetime(coalesce(old.last_updated, 0))
                                                                 < Datetime(new.last_updated)
                                                                 THEN TRUE
                                                             ELSE FALSE END
                                                    END AS needs_update
                                         FROM new
                                                  LEFT JOIN seasons AS old
                                                            ON old.trakt_show_id = new.trakt_show_id
                                                                AND old.season = new.season)
            """

    @property
    def upsert_episode_query(self):
        return """
            WITH new(trakt_id, trakt_show_id, trakt_season_id,
                     watched, collected,
                     air_date, last_updated,
                     season, number,
                     tmdb_id, tvdb_id, imdb_id,
                     info, art, cast,
                     args, last_watched_at, collected_at,
                     user_rating, meta_hash,
                     needs_update) AS (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE))
            INSERT
            INTO episodes(trakt_id, trakt_show_id, trakt_season_id,
                          watched, collected,
                          air_date, last_updated,
                          season, number,
                          tmdb_id, tvdb_id, imdb_id,
                          info, art, cast,
                          args, last_watched_at, collected_at,
                          user_rating, meta_hash, needs_update)
            SELECT trakt_id,
                   trakt_show_id,
                   trakt_season_id,
                   coalesce(watched, 0),
                   coalesce(collected, 0),
                   air_date,
                   coalesce(last_updated, '1970-01-01T00:00:00'),
                   season,
                   number,
                   tmdb_id,
                   tvdb_id,
                   imdb_id,
                   info,
                   art,
                   [cast],
                   coalesce(args, FALSE),
                   last_watched_at,
                   collected_at,
                   user_rating,
                   meta_hash,
                   needs_update
            FROM new
            WHERE TRUE
            ON CONFLICT(trakt_show_id, season, number) DO UPDATE
                SET (trakt_id, trakt_season_id,
                        watched, collected,
                        air_date, last_updated,
                        tmdb_id, tvdb_id, imdb_id,
                        info, art, cast,
                        args, last_watched_at, collected_at,
                        user_rating, meta_hash,
                        needs_update) = (SELECT new.trakt_id,
                                                coalesce(new.trakt_season_id, old.trakt_season_id),
                                                coalesce(new.watched, old.watched),
                                                coalesce(new.collected, old.collected),
                                                coalesce(new.air_date, old.air_date),
                                                coalesce(new.last_updated, old.last_updated),
                                                coalesce(new.tmdb_id, old.tmdb_id),
                                                coalesce(new.tvdb_id, old.tvdb_id),
                                                coalesce(new.imdb_id, old.imdb_id),
                                                coalesce(new.info, old.info),
                                                coalesce(new.art, old.art),
                                                coalesce(new.cast, old.cast),
                                                coalesce(new.args, old.args),
                                                coalesce(new.last_watched_at, old.last_watched_at),
                                                coalesce(new.collected_at, old.collected_at),
                                                coalesce(new.user_rating, old.user_rating),
                                                coalesce(new.meta_hash, old.meta_hash),
                                                CASE
                                                    WHEN old.needs_update
                                                        THEN CASE
                                                                 WHEN new.info <> old.info
                                                                     OR new.art <> old.art
                                                                     OR new.cast <> old.cast
                                                                     THEN FALSE
                                                                 ELSE old.needs_update END
                                                    ELSE CASE
                                                             WHEN
                                                                     Datetime(coalesce(old.last_updated, 0))
                                                                     < Datetime(new.last_updated)
                                                                 THEN TRUE
                                                             ELSE FALSE END
                                                    END AS needs_update
                                         FROM new
                                                  LEFT JOIN episodes AS old
                                                            ON old.trakt_show_id = new.trakt_show_id
                                                                AND old.season = new.season
                                                                AND old.number = new.number)
            """
