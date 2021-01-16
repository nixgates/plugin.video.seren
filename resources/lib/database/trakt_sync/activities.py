# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime

import xbmc
import xbmcgui
import time

from resources.lib.database import trakt_sync
from resources.lib.database.trakt_sync import hidden
from resources.lib.modules.exceptions import ActivitySyncFailure
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g
from resources.lib.modules.metadataHandler import MetadataHandler
from resources.lib.modules.timeLogger import stopwatch


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    sync_errors = False

    def __init__(self):
        super(TraktSyncDatabase, self).__init__()
        self.progress_dialog = None
        self.silent = True
        self.current_dialog_text = None
        self._sync_activities_list = [
            # (title, (remote, keys), local_activities_key, func)
            ("Hidden Shows", ("shows", "hidden_at"), "hidden_sync", self._sync_hidden),
            (
                "Watched Shows",
                ("episodes", "watched_at"),
                "shows_watched",
                self.sync_watched_episodes,
            ),
            (
                "Collected Shows",
                ("episodes", "collected_at"),
                "shows_collected",
                self.sync_collection_episodes,
            ),
            (
                "Show bookmarks",
                ("episodes", "paused_at"),
                "episodes_bookmarked",
                self._sync_show_bookmarks,
            ),
            (
                "Hidden Movies",
                ("movies", "hidden_at"),
                "hidden_sync",
                self._sync_hidden,
            ),
            (
                "Watched Movies",
                ("movies", "watched_at"),
                "movies_watched",
                self._sync_watched_movies,
            ),
            (
                "Collected Movies",
                ("movies", "collected_at"),
                "movies_collected",
                self._sync_collection_movies,
            ),
            (
                "Movie bookmarks",
                ("movies", "paused_at"),
                "movies_bookmarked",
                self._sync_movie_bookmarks,
            ),
        ]

    def fetch_remote_activities(self, silent=False):
        """
        Enforces a timeout for the activities call to Trakt based on database timestamp of last pull.
        :return: If last call occurred less than 10 minutes ago, return None, else return latest activities
        :rtype: Any
        """
        self.refresh_activities()
        if "last_activities_call" not in self.activities:
            g.log("Last activities call timestamp not present in database, migrating database change")
            self._insert_last_activities_column()
            self.refresh_activities()
            last_activities_call = 0
        else:
            last_activities_call = self.activities["last_activities_call"]

        if time.time() < (last_activities_call + (5 * 60)):
            g.log("Activities endpoint call to frequently! An issue is occuring!", 'error')
            return None
        else:
            remote_activities = self.trakt_api.get_json("sync/last_activities")
            self._update_last_activities_call()
            return remote_activities

    @stopwatch
    def sync_activities(self, silent=False):
        with GlobalLock("trakt.sync"):

            trakt_auth = g.get_setting("trakt.auth")
            update_time = str(datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))

            if trakt_auth is None:
                g.log("TraktSync: No Trakt auth present, no sync will occur", "warning")
                return
            self.refresh_activities()
            remote_activities = self.fetch_remote_activities(silent)

            if remote_activities is None:
                g.log("Activities Sync Failure: Unable to connect to Trakt or activities called to often", "error")
                return True

            if not self.requires_update(remote_activities["all"],
                                        self.activities["all_activities"]):
                self._update_all_shows_statisics()
                self._update_all_season_statistics()
                return

            self._check_for_first_run(silent, trakt_auth)

            self._do_sync_acitivites(remote_activities)

            # Begin iterating sync items

            self._finalize_process(update_time)

            self._update_all_shows_statisics()
            self._update_all_season_statistics()

        return self.sync_errors

    def _finalize_process(self, update_time):
        if self.progress_dialog is not None:
            self.progress_dialog.close()
            self.progress_dialog = None

        if not self.sync_errors:
            self._update_activity_record("all_activities", update_time)
            g.trigger_widget_refresh()

    def _do_sync_acitivites(self, remote_activities):
        total_activities = len(self._sync_activities_list)
        for idx, activity in enumerate(self._sync_activities_list):

            try:
                update_time = str(datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))

                monitor = xbmc.Monitor()
                if monitor.abortRequested():
                    return
                del monitor
                self.current_dialog_text = "Syncing {}".format(activity[0])
                self._update_progress(int(float(idx + 1) / total_activities * 100))

                last_activity_update = remote_activities

                if activity[1] is not None:
                    for key in activity[1]:
                        last_activity_update = last_activity_update[key]
                    if not self.requires_update(
                            last_activity_update, self.activities[activity[2]]
                    ):
                        g.log(
                            "Skipping {}, does not require update".format(activity[0])
                        )
                        continue

                g.log("Running Activity: {}".format(activity[0]))
                activity[3]()
                self._update_activity_record(activity[2], update_time)
            except ActivitySyncFailure as e:
                g.log("Falied to sync activity: {} - {}".format(activity[0], e))
                self.sync_errors = True
                continue

    def _check_for_first_run(self, silent, trakt_auth):
        if (
                not silent
                and str(self.activities["all_activities"]) == self.base_date
                and trakt_auth is not None
        ):
            g.notification(g.ADDON_NAME, g.get_language_string(30197))
            # Give the people time to read the damn notification
            xbmc.sleep(500)
            self.silent = False
            self.progress_dialog = xbmcgui.DialogProgressBG()
            self.progress_dialog.create(g.ADDON_NAME + "Sync", "Seren: Trakt Sync")

    def _sync_movie_bookmarks(self):
        try:
            self._sync_bookmarks("movies")
        except Exception as e:
            raise ActivitySyncFailure(e)

    def _sync_show_bookmarks(self):
        try:
            self._sync_bookmarks("episodes")
        except Exception as e:
            raise ActivitySyncFailure(e)

    def _sync_hidden(self):
        try:
            db = hidden.TraktSyncDatabase()
            get = MetadataHandler.get_trakt_info
            sections = [
                ("calendar",),
                ("progress_watched",),
                ("progress_watched_reset",),
                ("progress_collected",),
                ("recommendations",),
            ]

            self._queue_with_progress(self._fetch_hidden_section, sections)
            items = self.mill_task_queue.wait_completion()
            self.execute_sql("delete from hidden")
            self.execute_sql(
                db.insert_query,
                (
                    (i.get("trakt_id"), get(i, "mediatype"), key)
                    for key, value in items.items()
                    for i in value
                ),
            )
        except Exception as e:
            raise ActivitySyncFailure(e)

    def _fetch_hidden_section(self, section):
        items = []
        [
            items.extend(paged_items)
            for paged_items in self.trakt_api.get_all_pages_json(
            "users/hidden/{}".format(section)
        )
        ]
        return {section: items}

    def _sync_watched_movies(self):
        try:
            trakt_watched = self.trakt_api.get_json(
                "/sync/watched/movies", extended="full"
            )
            if len(trakt_watched) == 0:
                return
            self.execute_sql("UPDATE movies SET watched=0")
            self.insert_trakt_movies(
                self.filter_trakt_items_that_needs_updating(trakt_watched, "movies")
            )
            self.execute_sql(
                "UPDATE movies SET watched=1 where trakt_id in ({})".format(
                    ",".join(str(i.get("trakt_id")) for i in trakt_watched)
                )
            )
        except Exception as e:
            raise ActivitySyncFailure(e)

    def _sync_collection_movies(self):
        try:
            trakt_collection = self.trakt_api.get_json(
                "sync/collection/movies", extended="full"
            )
            if len(trakt_collection) == 0:
                return
            self.execute_sql("UPDATE movies SET collected=0")
            self.insert_trakt_movies(
                self.filter_trakt_items_that_needs_updating(trakt_collection, "movies")
            )
            self.execute_sql(
                "UPDATE movies SET collected=1 where trakt_id in ({})".format(
                    ",".join(str(i.get("trakt_id")) for i in trakt_collection)
                )
            )
        except Exception as e:
            raise ActivitySyncFailure(e)

    def sync_watched_episodes(self):
        try:
            get = MetadataHandler.get_trakt_info
            trakt_watched = self.trakt_api.get_json(
                "sync/watched/shows", extended="full"
            )
            if len(trakt_watched) == 0:
                return
            self.insert_trakt_shows(
                self.filter_trakt_items_that_needs_updating(trakt_watched, "shows")
            )
            self._mill_if_needed(trakt_watched, self._queue_with_progress)
            self.execute_sql("UPDATE episodes SET watched=0")
            with self.create_temp_table("_episodes_watched",
                                        ["trakt_show_id", "season", "episode", "last_watched_at",
                                         "watched"]) as temp_table:
                temp_table.insert_data([{
                    "trakt_show_id": show.get("trakt_id"),
                    "season": get(season, "season"),
                    "episode": get(episode, "episode"),
                    "last_watched_at": get(episode, "last_watched_at"),
                    "watched": get(episode, "playcount")}
                    for show in trakt_watched
                    for season in get(show, "seasons", [])
                    for episode in get(season, "episodes", [])
                ])
                self.execute_sql('INSERT OR REPLACE INTO episodes (trakt_id, trakt_show_id, trakt_season_id, season, '
                                 'tvdb_id, tmdb_id, imdb_id, info, "cast", art, meta_hash, last_updated, collected, '
                                 'watched, "number", args, air_date, last_watched_at, collected_at) SELECT trakt_id, '
                                 'e.trakt_show_id, trakt_season_id, e.season, tvdb_id, tmdb_id, imdb_id, info, '
                                 '"cast", art, meta_hash, last_updated, collected, ew.watched, ew.episode as '
                                 '"number", args, air_date, ew.last_watched_at, collected_at FROM episodes as e INNER '
                                 'JOIN _episodes_watched as ew on e.trakt_show_id = ew.trakt_show_id AND e.season = '
                                 'ew.season and e.number = ew.episode')

            self.update_shows_statistics(trakt_watched)
            self.update_season_statistics(self.execute_sql(
                "select trakt_id from seasons where trakt_show_id in ({})"
                    .format(",".join({str(i.get("trakt_id")) for i in trakt_watched}))).fetchall())
        except Exception as e:
            raise ActivitySyncFailure(e)

    def sync_collection_episodes(self):
        try:
            get = MetadataHandler.get_trakt_info
            trakt_collection = self.trakt_api.get_json(
                "sync/collection/shows", extended="full"
            )
            if len(trakt_collection) == 0:
                return

            self.insert_trakt_shows(
                self.filter_trakt_items_that_needs_updating(trakt_collection, "shows")
            )
            self._mill_if_needed(trakt_collection, self._queue_with_progress)

            self.execute_sql("UPDATE episodes SET collected=0")

            with self.create_temp_table("_episodes_collected",
                                        ["trakt_show_id", "season", "episode", "collected_at",
                                         "collected"]) as temp_table:
                temp_table.insert_data([{
                    "trakt_show_id": show.get("trakt_id"),
                    "season": get(season, "season"),
                    "episode": get(episode, "episode"),
                    "collected_at": get(episode, "collected_at"),
                    "collected": get(episode, "collected")}
                    for show in trakt_collection
                    for season in get(show, "seasons", [])
                    for episode in get(season, "episodes", [])
                ])
                self.execute_sql('INSERT OR REPLACE INTO episodes (trakt_id, trakt_show_id, trakt_season_id, '
                                 'season, tvdb_id, tmdb_id, imdb_id, info, "cast", art, meta_hash, last_updated, '
                                 'collected, watched, "number", args, air_date, last_watched_at, collected_at) '
                                 'SELECT trakt_id, e.trakt_show_id, trakt_season_id, e.season, tvdb_id, tmdb_id, '
                                 'imdb_id, info, "cast", art, meta_hash, last_updated, ec.collected, watched, '
                                 'ec.episode as "number", args, air_date, last_watched_at, ec.collected_at FROM '
                                 'episodes as e INNER JOIN _episodes_collected as ec on e.trakt_show_id = '
                                 'ec.trakt_show_id AND e.season = ec.season and e.number = ec.episode').fetchall()

            self.update_shows_statistics(trakt_collection)
            self.update_season_statistics(self.execute_sql(
                "select trakt_id from seasons where trakt_show_id in ({})"
                    .format(",".join({str(i.get("trakt_id")) for i in trakt_collection}))).fetchall())

        except Exception as e:
            raise ActivitySyncFailure(e)

    def _filter_lists_items_that_needs_updating(self, requested):
        if len(requested) == 0:
            return requested

        get = MetadataHandler.get_trakt_info
        query = """WITH requested(trakt_id, meta_hash, updated_at) AS (VALUES {}) select r.trakt_id as trakt_id from 
        requested as r left join lists as db on r.trakt_id == db.trakt_id  where db.trakt_id IS NULL or (Datetime(
        db.last_updated) < Datetime(r.updated_at)) or db.list_type == 'Unknown' """.format(
            ",".join(
                "({}, '{}', '{}')".format(
                    i.get("trakt_id"),
                    self.trakt_api.meta_hash,
                    i.get("dateadded", get(i, "dateadded")),
                )
                for i in requested
                if i.get("trakt_id")
            )
        )

        result = set(r["trakt_id"] for r in self.execute_sql(query).fetchall())
        return [
            r for r in requested if r.get("trakt_id") and r.get("trakt_id") in result
        ]

    def _update_progress(self, progress, text=None):
        if not self.silent:
            if text:
                self.progress_dialog.update(progress, text)
            else:
                self.progress_dialog.update(progress, self.current_dialog_text)

    def _update_activity_record(self, record, time):
        self.execute_sql(
            "UPDATE activities SET {}=? WHERE sync_id=1".format(record), (time,)
        )

    def _sync_bookmarks(self, bookmark_type):
        get = MetadataHandler.get_trakt_info
        self.execute_sql("DELETE FROM bookmarks WHERE type=?", (bookmark_type[:-1],))
        base_sql_statement = "REPLACE INTO bookmarks VALUES (?, ?, ?, ?, ?)"
        for progress in self.trakt_api.get_all_pages_json(
                "sync/playback/{}".format(bookmark_type), extended="full", timeout=60
        ):
            if bookmark_type == "movies":
                self.execute_sql(
                    base_sql_statement,
                    (
                        (
                            i.get("trakt_id"),
                            get(i, "resumetime"),
                            get(i, "percentplayed"),
                            bookmark_type[:-1],
                            get(i, "paused_at"),
                        )
                        for i in progress
                        if get(i, "percentplayed") is not None
                           and 0 < get(i, "percentplayed") < 100
                    ),
                )
            else:
                self.execute_sql(
                    base_sql_statement,
                    (
                        (
                            i.get("trakt_id"),
                            int(
                                float(i.get("progress") / 100)
                                * get(i["episode"], "duration")
                            ),
                            i.get("progress"),
                            bookmark_type[:-1],
                            i.get("paused_at"),
                        )
                        for i in progress
                        if i.get("progress") is not None and 0 < i.get("progress") < 100
                    ),
                )

    def _queue_with_progress(self, func, args):
        for idx, arg in enumerate(args):
            self.mill_task_queue.put(func, *arg)
            progress = int(float(idx + 1) / len(args) * 100)
            self._update_progress(progress)
