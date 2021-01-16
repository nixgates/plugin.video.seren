# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import collections
import datetime
import json
import threading
import time

import xbmcgui

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database import Database
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.modules.exceptions import (
    UnsupportedProviderType,
    InvalidMediaTypeException,
)
from resources.lib.modules.globals import g
from resources.lib.modules.metadataHandler import MetadataHandler
from resources.lib.modules.sync_lock import SyncLock

migrate_db_lock = threading.Lock()

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
            ]
        ),
        "table_constraints": [],
        "default_seed": [],
    },
    "seasons": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
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
            ]
        ),
        "table_constraints": [
            "UNIQUE(trakt_show_id, season)",
            # "FOREIGN KEY(trakt_show_id) REFERENCES shows(trakt_id) ON DELETE CASCADE"
        ],
        "default_seed": [],
    },
    "episodes": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
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
            ]
        ),
        "table_constraints": [
            "UNIQUE(trakt_id, season, number)",
            # "FOREIGN KEY(trakt_season_id) REFERENCES seasons(trakt_id) ON DELETE CASCADE",
            # "FOREIGN KEY(trakt_show_id) REFERENCES shows(trakt_id) ON DELETE CASCADE"
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
            ]
        ),
        "table_constraints": [],
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
                ("seren_version", ["TEXT", "NOT NULL"]),
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
        "default_seed": [],
    },
    "lists": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "NOT NULL"]),
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
        "table_constraints": ["PRIMARY KEY(trakt_id)"],
        "default_seed": [],
    },
}


class TraktSyncDatabase(Database):
    def __init__(self,):
        super(TraktSyncDatabase, self).__init__(
            g.TRAKT_SYNC_DB_PATH, schema, migrate_db_lock
        )
        self.metadataHandler = MetadataHandler()
        self.trakt_api = TraktAPI()

        self.activities = {}
        self.item_list = []
        self.base_date = "1970-01-01T00:00:00"
        self.task_queue = ThreadPool()
        self.mill_task_queue = ThreadPool()
        self.parent_task_queue = ThreadPool()
        self.refresh_activities()

        # If you make changes to the required meta in any indexer that is cached in this database
        # You will need to update the below version number to match the new addon version
        # This will ensure that the metadata required for operations is available

        self.last_meta_update = "2.0.0"
        if self.activities is None:
            self.clear_all_meta(False)
            self.set_base_activities()

        if self.activities is not None:
            self._check_database_version()

        self.notification_prefix = "{}: Trakt".format(g.ADDON_NAME)
        self.hide_unaired = g.get_bool_setting("general.hideUnAired")
        self.hide_specials = g.get_bool_setting("general.hideSpecials")
        self.hide_watched = g.get_bool_setting("general.hideWatched")
        self.date_delay = g.get_bool_setting("general.datedelay")
        self.page_limit = g.get_int_setting("item.limit")

    def clear_specific_item_meta(self, trakt_id, media_type):
        if media_type == "tvshow":
            media_type = "shows"
        elif media_type == "show":
            media_type = "shows"
        elif media_type == "movie":
            media_type = "movies"
        elif media_type == "episode":
            media_type = "episodes"
        elif media_type == "season":
            media_type = "seasons"

        if media_type not in ["shows", "movies", "seasons", "episodes"]:
            raise InvalidMediaTypeException(media_type)

        self.execute_sql(
            "DELETE from {}_meta where id=?".format(media_type), (trakt_id,)
        )
        self.execute_sql(
            "UPDATE {} SET info=null, art=null, cast=null, meta_hash=null where trakt_id=?"
            "".format(media_type),
            (trakt_id,),
        )

    def _update_last_activities_call(self):
        self.execute_sql("UPDATE activities SET last_activities_call=? WHERE sync_id=1", (int(time.time()),))
        self.refresh_activities()

    def _insert_last_activities_column(self):
        self.execute_sql("ALTER TABLE activities ADD last_activities_call INTEGER NOT NULL DEFAULT 1")

    @staticmethod
    def _get_datetime_now():
        return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def refresh_activities(self):
        self.activities = self.execute_sql(
            "SELECT * FROM activities WHERE sync_id=1"
        ).fetchone()

    def set_base_activities(self):
        self.execute_sql(
            "INSERT OR REPLACE INTO activities(sync_id, seren_version, trakt_username) VALUES(1, ?, ?)",
            (self.last_meta_update, g.get_setting("trakt.username")),
        )
        self.activities = self.execute_sql(
            "SELECT * FROM activities WHERE sync_id=1"
        ).fetchone()

    def _check_database_version(self):
        # If we are updating from a database prior to database versioning, we must clear the meta data
        # Migrate from older versions before trakt username tracking
        if tools.compare_version_numbers(
            self.activities["seren_version"], self.last_meta_update
        ):
            g.log("Rebuilding Trakt Sync Database Version")
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30363))
            try:
                self.re_build_database(True)
            except:
                self.rebuild_database()

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
                "UPDATE movies SET last_watched_at=?",
            ],
            (None,),
        )
        self.execute_sql(
            ["DELETE from bookmarks WHERE 1=1", "DELETE from hidden WHERE 1=1",]
        )
        self.execute_sql("DELETE from lists WHERE username=?", (username,))
        self.set_trakt_user("")
        self.set_base_activities()
        if notify:
            g.notification(
                self.notification_prefix, g.get_language_string(30297), time=5000
            )

    def set_trakt_user(self, trakt_username):
        g.log("Setting Trakt Username: {}".format(trakt_username))
        self.execute_sql("UPDATE activities SET trakt_username=?", (trakt_username,))

    def clear_all_meta(self, notify=True):
        if notify:
            confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30201))
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
            g.notification(
                self.notification_prefix, g.get_language_string(30298), time=5000
            )

    def re_build_database(self, silent=False):
        if not silent:
            confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30201))
            if confirm == 0:
                return

        self.clear_all_meta(False)
        self.clear_user_information(False)
        self.rebuild_database()
        self.set_base_activities()
        self.refresh_activities()

        from resources.lib.database.trakt_sync import activities

        sync_errors = activities.TraktSyncDatabase().sync_activities(silent)

        if sync_errors:
            g.notification(
                self.notification_prefix, g.get_language_string(30364), time=5000
            )
        elif sync_errors is None:
            self.refresh_activities()
        else:
            g.notification(
                self.notification_prefix, g.get_language_string(30299), time=5000
            )

    def filter_items_that_needs_updating(self, requested, media_type):
        if requested is None or len(requested) == 0:
            return []
        query = """WITH requested(trakt_id, meta_hash) AS (VALUES {}) select r.trakt_id as trakt_id from requested as 
        r left join {} as db on r.trakt_id == db.trakt_id where db.trakt_id IS NULL or (db.info is null or db.art is 
        null or db.cast is null or r.meta_hash != db.meta_hash)""".format(
            ",".join(
                [
                    "({}, '{}')".format(
                        i.get("trakt_id"), self.metadataHandler.meta_hash
                    )
                    for i in requested
                ]
            ),
            media_type,
        )
        result = set(r["trakt_id"] for r in self.execute_sql(query).fetchall())
        return [r for r in requested if r.get("trakt_id") in result]

    def save_to_meta_table(self, items, meta_type, provider_type, id_column):
        if items is None:
            return
        sql_statement = "replace into {}_meta (id ,type, meta_hash, value) VALUES (?, ?, ?, ?)".format(
            meta_type
        )
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
                if i
                and obj(i)
                and i.get(id_column)
                and MetadataHandler.full_meta_up_to_par(meta_type, obj(i))
            ),
        )

        for i in items:
            if i and obj(i):
                if obj(i).get("seasons"):
                    self.save_to_meta_table(
                        i.get("seasons"), "season", provider_type, id_column
                    )
                if obj(i).get("episodes"):
                    self.save_to_meta_table(
                        i.get("episodes"), "episode", provider_type, id_column
                    )

    @staticmethod
    def clean_meta(item):
        if not item:
            return None

        result = {
            "info": {
                key: value
                for key, value in item.get("info", {}).items()
                if key != "seasons" and key != "episodes"
            },
            "art": item.get("art"),
            "cast": item.get("cast"),
        }
        if not result.get("info") and not result.get("art") and not result.get("cast"):
            g.log(
                "Bad Item meta discovered when cleaning - item: {}".format(item),
                "error",
            )
            return None
        else:
            return result

    def insert_trakt_movies(self, movies):
        g.log("Inserting Movies into sync database: {}".format(len(movies)))
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
                    tools.validate_date(get(i, "aired")),
                    tools.validate_date(get(i, "dateadded")),
                    get(i, "tmdb_id"),
                    get(i, "imdb_id"),
                    None,
                    self._create_args(i),
                    tools.validate_date(get(i, "collected_at")),
                    tools.validate_date(get(i, "last_watched_at")),
                    i.get("trakt_id"),
                )
                for i in movies
            ),
        )
        self.save_to_meta_table(movies, "movies", "trakt", "trakt_id")

    def insert_trakt_shows(self, shows):
        g.log("Inserting Shows into sync database: {}".format(len(shows)))
        get = MetadataHandler.get_trakt_info
        self.execute_sql(
            self.upsert_show_query,
            (
                (
                    i.get("trakt_id"),
                    None,
                    None,
                    None,
                    tools.validate_date(get(i, "aired")),
                    tools.validate_date(get(i, "dateadded")),
                    get(i, "tmdb_id"),
                    get(i, "tvdb_id"),
                    get(i, "imdb_id"),
                    self.trakt_api.meta_hash,
                    get(i, "season_count"),
                    get(i, "episode_count"),
                    self._create_args(i),
                    get(i, "is_airing"),
                    i.get("trakt_id"),
                )
                for i in shows
            ),
        )
        self.save_to_meta_table(shows, "shows", "trakt", "trakt_id")

    def insert_trakt_episodes(self, episodes):
        g.log("Inserting episodes into sync database: {}".format(len(episodes)))
        get = MetadataHandler.get_trakt_info
        self.execute_sql(
            self.upsert_episode_query,
            (
                (
                    i.get("trakt_id"),
                    i.get("trakt_show_id"),
                    i.get("trakt_season_id"),
                    get(i, "playcount"),
                    get(i, "collected"),
                    tools.validate_date(get(i, "aired")),
                    tools.validate_date(get(i, "dateadded")),
                    get(i, "season"),
                    get(i, "episode"),
                    get(i, "tmdb_id"),
                    get(i, "tvdb_id"),
                    get(i, "imdb_id"),
                    None,
                    None,
                    None,
                    self._create_args(i),
                    tools.validate_date(get(i, "last_watched_at")),
                    tools.validate_date(get(i, "collected_at")),
                    self.trakt_api.meta_hash,
                    i.get("trakt_id"),
                )
                for i in episodes
            ),
        )
        self.save_to_meta_table(episodes, "episodes", "trakt", "trakt_id")

    def insert_trakt_seasons(self, seasons):
        g.log("Inserting seasons into sync database: {}".format(len(seasons)))
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
                    tools.validate_date(get(i, "aired")),
                    tools.validate_date(get(i, "dateadded")),
                    get(i, "tmdb_id"),
                    get(i, "tvdb_id"),
                    self.trakt_api.meta_hash,
                    None,
                    get(i, "season"),
                    self._create_args(i),
                    i.get("trakt_id"),
                )
                for i in seasons
            ),
        )
        self.save_to_meta_table(seasons, "seasons", "trakt", "trakt_id")

    def _mill_if_needed(self, list_to_update, queue_wrapper=None, mill_episodes=True):
        if queue_wrapper is None:
            queue_wrapper = self._queue_mill_tasks

        if mill_episodes:
            query = """select s.trakt_id, CASE WHEN (agg.episode_count is NULL or 
            agg.episode_count != s.episode_count) or (agg.meta_count=0 or agg.meta_count!=s.episode_count) THEN 'True' 
            ELSE 'False' END as needs_update from shows as s left join(select s.trakt_id, count(e.trakt_id) as 
            episode_count, count(em.id) as meta_count from shows as s inner join episodes as e on s.trakt_id = 
            e.trakt_show_id left join episodes_meta as em on em.id = e.trakt_id and em.type = 'trakt' and em.meta_hash = 
            '{}' where e.season != 0 and Datetime(e.air_date) < Datetime('now') GROUP BY s.trakt_id) as agg on s.trakt_id == 
            agg.trakt_id WHERE s.trakt_id in ({})""".format(
                self.trakt_api.meta_hash,
                ",".join(
                    str(i.get("trakt_show_id", i.get("trakt_id"))) for i in list_to_update
                ),
            )
        else:
            query = """select s.trakt_id, agg.meta_count, s.season_count, CASE WHEN (agg.season_count is NULL or 
                agg.season_count != s.season_count) or (agg.meta_count=0 or agg.meta_count!=s.season_count) THEN 'True' 
                ELSE 'False' END as needs_update from shows as s left join(select s.trakt_id, count(se.trakt_id) as 
                season_count, count(sm.id) as meta_count from shows as s inner join seasons as se on s.trakt_id = 
                se.trakt_show_id left join seasons_meta as sm on sm.id = se.trakt_id and sm.type = 'trakt' and sm.meta_hash = 
                '{}' where se.season != 0 and Datetime(se.air_date) < Datetime('now') 
                GROUP BY s.trakt_id) as agg on s.trakt_id == agg.trakt_id WHERE s.trakt_id in ({})""".format(
                self.trakt_api.meta_hash,
                ",".join(
                    str(i.get("trakt_show_id", i.get("trakt_id"))) for i in list_to_update
                ),
            )
        needs_update = self.execute_sql(query).fetchall()
        if needs_update is None or all(
            x["needs_update"] == "False" for x in needs_update
        ):
            return

        g.log("{} items require season milling".format(len([i for i in needs_update if i["needs_update"] ==
                                                            "True"])), "debug")
        self.mill_seasons(
            [
                i
                for i in list_to_update
                if any(
                    x["needs_update"] == "True"
                    and x.get("trakt_id") == i.get("trakt_show_id", i.get("trakt_id"))
                    for x in needs_update
                )
            ],
            queue_wrapper,
            mill_episodes
        )

    def mill_seasons(self, trakt_collection, queue_wrapper, mill_episodes=False):
        with SyncLock(
            "mill_seasons_episodes_{}".format(mill_episodes),
            {
                show.get("trakt_show_id", show.get("trakt_id"))
                for show in trakt_collection
            },
        ) as sync_lock:
            get = MetadataHandler.get_trakt_info
            queue_wrapper(
                self._pull_show_seasons, [(i, mill_episodes) for i in sync_lock.running_ids]
            )
            results = self.mill_task_queue.wait_completion()

            seasons = []
            episodes = []
            trakt_info = MetadataHandler.trakt_info

            for show in trakt_collection:
                extended_seasons = get(show, "seasons", [])
                for season in results.get(show.get("trakt_id"), []):
                    if self.hide_specials and get(season, "season") == 0:
                        continue

                    trakt_info(season).update({"trakt_show_id": get(show, "trakt_id")})
                    trakt_info(season).update({"tmdb_show_id": get(show, "tmdb_id")})
                    trakt_info(season).update({"tvdb_show_id": get(show, "tvdb_id")})

                    season.update({"trakt_show_id": show.get("trakt_id")})
                    season.update({"tmdb_show_id": show.get("tmdb_id")})
                    season.update({"tvdb_show_id": show.get("tvdb_id")})

                    trakt_info(season).update({"dateadded": get(show, "dateadded")})
                    trakt_info(season).update({"tvshowtitle": get(show, "title")})

                    if not get(season, "season") == 0:
                        show.update({"season_count": show.get("season_count", 0) + (1 if get(season, "aired_episodes", 0) > 0 else 0)})
                        show.update(
                            {
                                'episode_count': show.get("episode_count", 0) + get(season, "aired_episodes", 0)
                                }
                            )
                    for episode in get(season, "episodes", []):
                        trakt_info(episode).update({"trakt_show_id": get(show, "trakt_id")})
                        trakt_info(episode).update({"tmdb_show_id": get(show, "tmdb_id")})
                        trakt_info(episode).update({"tvdb_show_id": get(show, "tvdb_id")})
                        trakt_info(episode).update({"trakt_season_id": get(season, "trakt_id")})

                        episode.update({"trakt_show_id": show.get("trakt_id")})
                        episode.update({"tmdb_show_id": show.get("tmdb_id")})
                        episode.update({"tvdb_show_id": show.get("tvdb_id")})
                        episode.update({"trakt_season_id": season.get("trakt_id")})

                        trakt_info(episode).update({"tvshowtitle": get(show, "title")})
                        for extended_season in (x for x in extended_seasons
                                                if get(x, "season") == get(season, "season")):
                            [
                                tools.smart_merge_dictionary(episode, extended_episode)
                                for extended_episode in
                                (x for x in get(extended_season, "episodes", [])
                                    if get(x, "episode") == get(episode, "episode"))
                             ]
                            tools.smart_merge_dictionary(season, extended_season)
                        episodes.append(episode)
                    seasons.append(season)

            self.insert_trakt_seasons(
                self.filter_trakt_items_that_needs_updating(seasons, "seasons")
            )
            self.insert_trakt_episodes(
                self.filter_trakt_items_that_needs_updating(episodes, "episodes")
            )

            self.execute_sql("UPDATE shows SET episode_count=?, season_count=? WHERE trakt_id=? ",
                             [(i.get("episode_count", 0), i.get("season_count", 0), i["trakt_id"])
                              for i in trakt_collection])

            self.update_shows_statistics({"trakt_id": i} for i in sync_lock.running_ids)

            if mill_episodes:
                self.update_season_statistics(
                    {"trakt_id": i} for i in sync_lock.running_ids
                    )

    def filter_trakt_items_that_needs_updating(self, requested, media_type):
        if len(requested) == 0:
            return requested

        get = MetadataHandler.get_trakt_info
        query = """WITH requested(trakt_id, meta_hash, updated_at) AS (VALUES {}) 
        select r.trakt_id as trakt_id from requested as r left join {} as db on r.trakt_id == db.trakt_id 
        left join {}_meta as m on db.trakt_id == id and type=\"trakt\" where db.trakt_id IS NULL or m.value IS NULL or 
        m.meta_hash != r.meta_hash or (Datetime(db.last_updated) < Datetime(r.updated_at))""".format(
            ",".join(
                "({}, '{}', '{}')".format(
                    i.get("trakt_id"), self.trakt_api.meta_hash, get(i, "dateadded")
                )
                for i in requested
                if i.get("trakt_id")
            ),
            media_type,
            media_type,
        )

        result = set(r["trakt_id"] for r in self.execute_sql(query).fetchall())
        return [
            r for r in requested if r.get("trakt_id") and r.get("trakt_id") in result
        ]

    def _pull_show_seasons(self, show_id, mill_episodes=False):
        return {
            show_id: self.trakt_api.get_json(
                "/shows/{}/seasons".format(show_id),
                extended="full,episodes" if mill_episodes else "full",
                translations=g.get_language_code(),
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
            g.log(inspect.stack())
            g.log(item)
        if args["mediatype"] == "season":
            args["trakt_show_id"] = get(
                item, "trakt_show_id", info(item).get("trakt_show_id")
            )
        if args["mediatype"] == "episode":
            args["trakt_show_id"] = get(
                item, "trakt_show_id", info(item).get("trakt_show_id")
            )
            args["trakt_season_id"] = get(
                item, "trakt_season_id", info(item).get("trakt_season_id")
            )
        return tools.quote(json.dumps(args, sort_keys=True))

    def _queue_mill_tasks(self, func, args):
        for arg in args:
            self.mill_task_queue.put(func, *arg)

    @staticmethod
    def requires_update(new_date, old_date):
        if tools.parse_datetime(
            new_date, tools.DATE_FORMAT, False
        ) > tools.parse_datetime(old_date, "%Y-%m-%dT%H:%M:%S", False):
            return True
        else:
            return False

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
            self.execute_sql(
                """select id as trakt_id, value as trakt_object from 
        {}_meta where id = ? and type = 'trakt' """.format(
                    media_type
                ),
                (int(trakt_id),),
            ).fetchone(),
            media_type,
        )

    def _update_single_meta(self, trakt_url, item, media_type):
        trakt_object = MetadataHandler.trakt_object
        if item is None:
            item = {}
        if trakt_object(item) is None or trakt_object(item) == {}:
            new_object = self.trakt_api.get_json(trakt_url, extended="full")
            self.save_to_meta_table([new_object], media_type, "trakt", "trakt_id")
            item.update(new_object)
        return item

    @staticmethod
    def update_missing_trakt_objects(db_list_to_update, list_to_update):
        for item in db_list_to_update:
            if item.get("trakt_object") is None:
                try:
                    item.update(
                        next(
                            i
                            for i in list_to_update
                            if int(i.get("trakt_id") or 0)
                            == int(item.get("trakt_id") or 0)
                        )
                    )
                except StopIteration:
                    g.log(
                        "Failed to find item in list to update, original item: \n {}".format(
                            item
                        )
                    )

    def _extract_trakt_page(self, url, media_type, **params):
        result = []

        def _handle_page(page):
            if not page or len(page) == 0:
                return []
            to_insert = self.filter_trakt_items_that_needs_updating(page, media_type)
            if media_type == "movies":
                self.insert_trakt_movies(to_insert)
            elif media_type == "shows":
                self.insert_trakt_shows(to_insert)
            query = (
                "WITH requested(trakt_id) AS (VALUES {}) select r.trakt_id as trakt_id from requested as r inner "
                "join {} as db on r.trakt_id == db.trakt_id left join {}_meta as m on db.trakt_id == "
                "id and type = 'trakt' where 1=1".format(
                    ",".join("({})".format(i.get("trakt_id")) for i in page),
                    media_type,
                    media_type,
                )
            )
            if self.hide_unaired:
                query += " AND Datetime(air_date) < Datetime('now')"
            if self.hide_watched:
                if media_type == "movies":
                    query += " AND watched = 0"
                if media_type == "shows":
                    query += " AND watched_episodes < episode_count"
            result.extend(self.execute_sql(query).fetchall())

        no_paging = params.get("no_paging", False)
        pull_all = params.pop("pull_all", False)
        page_number = params.pop("page", 1)

        if pull_all:
            _handle_page(self.trakt_api.get_json_cached(url, **params))
            if len(result) >= (self.page_limit * page_number) and not no_paging:
                return result[
                    self.page_limit * (page_number - 1) : self.page_limit * page_number
                ]
        else:
            params["limit"] = params.pop("page", self.page_limit)
            for page in self.trakt_api.get_all_pages_json(url, **params):
                _handle_page(page)
                if len(result) >= (self.page_limit * page_number) and not no_paging:
                    return result[
                        self.page_limit
                        * (page_number - 1) : self.page_limit
                        * page_number
                    ]

        if no_paging:
            return result
        return result[self.page_limit * (page_number - 1) :]

    def update_shows_statistics(self, trakt_list):
        to_update = ",".join({str(i.get("trakt_id")) for i in trakt_list})
        self.execute_sql(
            """INSERT or REPLACE into shows (trakt_id, info, art, cast, air_date, last_updated, tmdb_id, tvdb_id,             
            imdb_id, meta_hash, season_count, episode_count, watched_episodes, unwatched_episodes, args, is_airing) 
            SELECT old.trakt_id, old.info, old.art, old.cast, old.air_date, old.last_updated, old.tmdb_id, 
            old.tvdb_id, old.imdb_id, old.meta_hash, old.season_count, old.episode_count, COALESCE( 
            new.watched_episodes, old.watched_episodes), COALESCE(new.unwatched_episodes, old.unwatched_episodes), 
            old.args, old.is_airing FROM (select sh.trakt_id, sh.episode_count - sum(CASE WHEN e.watched > 0 AND 
            e.season != 0 AND Datetime(e.air_date) < Datetime('now') THEN 1 ELSE 0 END) as unwatched_episodes, 
            sum(CASE WHEN e.watched > 0 AND e.season != 0 AND Datetime(e.air_date) < Datetime('now') THEN 1 ELSE 0 
            END) as watched_episodes from shows as sh left join episodes as e on e.trakt_show_id = sh.trakt_id group 
            by sh.trakt_id) AS new LEFT JOIN (SELECT * FROM shows) AS old on old.trakt_id = new.trakt_id where 
            old.trakt_id in ({})""".format(
                to_update
            )
        )

    def _update_all_shows_statisics(self):
        self.execute_sql(
            """INSERT or REPLACE into shows (trakt_id, info, art, cast, air_date, last_updated, tmdb_id, tvdb_id,             
            imdb_id, meta_hash, season_count, episode_count, watched_episodes, unwatched_episodes, args, is_airing) 
            SELECT old.trakt_id, old.info, old.art, old.cast, old.air_date, old.last_updated, old.tmdb_id, 
            old.tvdb_id, old.imdb_id, old.meta_hash, old.season_count, old.episode_count, COALESCE( 
            new.watched_episodes, old.watched_episodes), COALESCE(new.unwatched_episodes, old.unwatched_episodes), 
            old.args, old.is_airing FROM (select sh.trakt_id, sh.episode_count - sum(CASE WHEN e.watched > 0 AND 
            e.season != 0 AND Datetime(e.air_date) < Datetime('now') THEN 1 ELSE 0 END) as unwatched_episodes, 
            sum(CASE WHEN e.watched > 0 AND e.season != 0 AND Datetime(e.air_date) < Datetime('now') THEN 1 ELSE 0 
            END) as watched_episodes from shows as sh left join episodes as e on e.trakt_show_id = sh.trakt_id group 
            by sh.trakt_id) AS new LEFT JOIN (SELECT * FROM shows) AS old on old.trakt_id = new.trakt_id where 
            old.trakt_id in (SELECT trakt_id from shows where 1=1)"""
        )

    def update_season_statistics(self, trakt_list):
        to_update = ",".join({str(i.get("trakt_id")) for i in trakt_list})

        self.execute_sql(
            """INSERT or REPLACE into seasons ( trakt_show_id, trakt_id, info, art, cast, air_date, last_updated,
             tmdb_id, tvdb_id, meta_hash, episode_count, watched_episodes, unwatched_episodes, is_airing, season, args 
             ) SELECT old.trakt_show_id, old.trakt_id, old.info, old.art, old.cast, old.air_date, old.last_updated, 
             old.tmdb_id, old.tvdb_id, old.meta_hash, COALESCE(new.episode_count, old.episode_count), 
             COALESCE(new.watched_episodes, old.watched_episodes), COALESCE(new.unwatched_episodes, 
             old.unwatched_episodes), COALESCE(new.is_airing, old.is_airing), old.season, old.args FROM ( SELECT 
             se.trakt_id,  sum( CASE WHEN datetime(e.air_date) < datetime('now') THEN 1 ELSE 0 END) AS episode_count, 
             sum( CASE WHEN e.watched == 0 AND datetime(e.air_date) < datetime('now') THEN 1 ELSE 0 END) AS 
             unwatched_episodes, sum( CASE WHEN e.watched > 0 AND datetime(e.air_date) < datetime('now') THEN 1 ELSE 0 
             END) AS watched_episodes, CASE WHEN max(e.air_date) > datetime('now') THEN 1 ELSE 0 END AS is_airing FROM 
             seasons AS se INNER JOIN episodes AS e ON e.trakt_season_id = se.trakt_id WHERE se.season != 0 GROUP BY 
             se.trakt_id) AS new LEFT JOIN ( SELECT * FROM seasons) AS old ON new.trakt_id = old.trakt_id where 
             old.trakt_id in ({})""".format(
                to_update
            )
        )

    def _update_all_season_statistics(self):
        self.execute_sql(
            """INSERT or REPLACE into seasons ( trakt_show_id, trakt_id, info, art, cast, air_date, last_updated,
             tmdb_id, tvdb_id, meta_hash, episode_count, watched_episodes, unwatched_episodes, is_airing, season, args
             ) SELECT old.trakt_show_id, old.trakt_id, old.info, old.art, old.cast, old.air_date, old.last_updated,
             old.tmdb_id, old.tvdb_id, old.meta_hash, COALESCE(new.episode_count, old.episode_count),
             COALESCE(new.watched_episodes, old.watched_episodes), COALESCE(new.unwatched_episodes,
             old.unwatched_episodes), COALESCE(new.is_airing, old.is_airing), old.season, old.args FROM ( SELECT
             se.trakt_id,  sum( CASE WHEN datetime(e.air_date) < datetime('now') THEN 1 ELSE 0 END) AS episode_count,
             sum( CASE WHEN e.watched == 0 AND datetime(e.air_date) < datetime('now') THEN 1 ELSE 0 END) AS
             unwatched_episodes, sum( CASE WHEN e.watched > 0 AND datetime(e.air_date) < datetime('now') THEN 1 ELSE 0
             END) AS watched_episodes, CASE WHEN max(e.air_date) > datetime('now') THEN 1 ELSE 0 END AS is_airing FROM
             seasons AS se INNER JOIN episodes AS e ON e.trakt_season_id = se.trakt_id WHERE se.season != 0 GROUP BY
             se.trakt_id) AS new LEFT JOIN ( SELECT * FROM seasons) AS old ON new.trakt_id = old.trakt_id where
             old.trakt_id in (SELECT trakt_id from seasons where 1==1)"""
        )

    @property
    def upsert_movie_query(self):
        return """INSERT or REPLACE into movies ( trakt_id, info, art, cast, collected, watched, air_date, 
        last_updated, tmdb_id, imdb_id, meta_hash, args, collected_at, last_watched_at ) SELECT COALESCE(
        new.trakt_id, old.trakt_id), COALESCE(new.info, old.info), COALESCE(new.art, old.art), COALESCE(new.cast, 
        old.cast), COALESCE(new.collected, old.collected), COALESCE(new.watched, old.watched), COALESCE(new.air_date, 
        old.air_date), COALESCE(new.last_updated, old.last_updated), COALESCE(new.tmdb_id, old.tmdb_id), 
        COALESCE(new.imdb_id, old.imdb_id), COALESCE(new.meta_hash, old.meta_hash), COALESCE(new.args, old.args), 
        COALESCE(new.collected_at, old.collected_at), COALESCE(new.last_watched_at, old.last_watched_at) FROM ( 
        SELECT ? AS trakt_id, ? AS info, ? AS art, ? AS cast, ? AS collected, ? as watched, ? AS air_date, 
        ? AS last_updated, ? AS tmdb_id, ? AS imdb_id, ? AS meta_hash, ? AS args, ? AS collected_at, 
        ? AS last_watched_at) AS new LEFT JOIN (SELECT * FROM movies WHERE trakt_id = ? limit 1) AS old """

    @property
    def upsert_show_query(self):
        return """INSERT or REPLACE into shows (trakt_id, info, art, cast, air_date, last_updated, tmdb_id, tvdb_id, 
        imdb_id, meta_hash, season_count, episode_count, watched_episodes, unwatched_episodes, args, is_airing) SELECT 
        COALESCE(new.trakt_id, old.trakt_id), COALESCE(new.info, old.info), COALESCE(new.art, old.art), COALESCE(
        new.cast, old.cast), COALESCE(new.air_date, old.air_date), COALESCE(new.last_updated, old.last_updated), 
        COALESCE(new.tmdb_id, old.tmdb_id), COALESCE(new.tvdb_id, old.tvdb_id), COALESCE(new.imdb_id, old.imdb_id), 
        COALESCE(new.meta_hash, old.meta_hash), COALESCE(new.season_count, old.season_count), 
        COALESCE(new.episode_count, old.episode_count), COALESCE(old.watched_episodes, 0), 
        COALESCE(old.unwatched_episodes, 0), COALESCE(new.args, old.args), COALESCE(new.is_airing, old.is_airing) FROM 
        (SELECT ? AS trakt_id, ? AS info, ? AS art, ? AS cast, ? AS air_date, ? AS last_updated, ? AS tmdb_id, ? AS 
        tvdb_id, ? AS imdb_id, ? AS meta_hash, ? AS season_count,? AS episode_count, ? AS args, ? as is_airing) AS 
        new LEFT JOIN (SELECT * FROM shows WHERE trakt_id = ? limit 1) AS old """

    @property
    def upsert_season_query(self):
        return """INSERT or REPLACE into seasons ( trakt_show_id, trakt_id, info, art, cast, air_date, last_updated, 
        tmdb_id, tvdb_id, meta_hash, episode_count, watched_episodes, unwatched_episodes, season, args, is_airing ) 
        SELECT COALESCE(new.trakt_show_id, old.trakt_show_id), COALESCE(new.trakt_id, old.trakt_id), COALESCE(new.info, 
        old.info), COALESCE(new.art, old.art), COALESCE(new.cast, old.cast), COALESCE(new.air_date, old.air_date), 
        COALESCE(new.last_updated, old.last_updated), COALESCE(new.tmdb_id, old.tmdb_id), COALESCE(new.tvdb_id, 
        old.tvdb_id), COALESCE(new.meta_hash, old.meta_hash), COALESCE(new.episode_count, old.episode_count), 
        old.watched_episodes, old.unwatched_episodes, COALESCE(new.season, old.season), COALESCE(new.args, 
        old.args), old.is_airing FROM ( SELECT ? AS trakt_show_id, ? AS trakt_id, ? AS info, ? AS art, ? AS cast, ? 
        AS air_date, ? AS last_updated, ? AS tmdb_id, ? AS tvdb_id, ? AS meta_hash, ? AS episode_count, ? AS season, ? 
        AS args) AS new LEFT JOIN ( SELECT * FROM seasons WHERE trakt_id = ? limit 1) AS old """

    @property
    def upsert_episode_query(self):
        return """INSERT or REPLACE into episodes (trakt_id, trakt_show_id, trakt_season_id, watched, collected, 
        air_date, last_updated, season, number, tmdb_id, tvdb_id, imdb_id, info, art, cast, args, last_watched_at, 
        collected_at, meta_hash ) SELECT COALESCE (new.trakt_id , old.trakt_id), COALESCE (new.trakt_show_id , 
        old.trakt_show_id), COALESCE (new.trakt_season_id , old.trakt_season_id), COALESCE (new.watched , 
        old.watched), COALESCE (new.collected , old.collected), COALESCE (new.air_date , old.air_date), 
        COALESCE (new.last_updated , old.last_updated), COALESCE (new.season , old.season), COALESCE (new.number , 
        old.number), COALESCE (new.tmdb_id , old.tmdb_id), COALESCE (new.tvdb_id , old.tvdb_id), COALESCE (
        new.imdb_id , old.imdb_id), COALESCE (new.info , old.info), COALESCE (new.art , old.art), COALESCE (new.cast 
        , old.cast), COALESCE (new.args , old.args), COALESCE (new.last_watched_at , old.last_watched_at), 
        COALESCE (new.collected_at , old.collected_at), COALESCE (new.meta_hash , old.meta_hash) FROM (SELECT ? AS 
        trakt_id, ? AS trakt_show_id, ? AS trakt_season_id, ? AS watched, ? AS collected, ? AS air_date, 
        ? AS last_updated, ? AS season, ? AS number, ? AS tmdb_id, ? AS tvdb_id, ? AS imdb_id, ? AS info, ? AS art, 
        ? AS cast, ? AS args, ? AS last_watched_at, ? AS collected_at, ? AS meta_hash) AS new LEFT JOIN ( SELECT * 
        FROM episodes WHERE trakt_id = ? limit 1) AS old """
