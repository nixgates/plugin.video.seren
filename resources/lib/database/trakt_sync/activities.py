import itertools
import time

import xbmc
import xbmcgui

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
        super().__init__()
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
                "Shows ratings",
                ("shows", "rated_at"),
                "shows_rated",
                self._sync_rated_shows,
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
            (
                "Movie ratings",
                ("movies", "rated_at"),
                "movies_rated",
                self._sync_rated_movies,
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
            g.log("Activities endpoint called too frequently, skipping sync", 'info')
            return None
        else:
            remote_activities = self.trakt_api.get_json("sync/last_activities")
            self._update_last_activities_call()
            return remote_activities

    @stopwatch
    def sync_activities(self, silent=False):
        with GlobalLock("trakt.sync"):

            trakt_auth = g.get_setting("trakt.auth")
            update_time = str(self._get_datetime_now())

            if not trakt_auth:
                g.log("TraktSync: No Trakt auth present, no sync will occur", "warning")
                return

            self.refresh_activities()
            remote_activities = self.fetch_remote_activities(silent)

            if remote_activities is None:
                g.log("Activities Sync Failure: Unable to connect to Trakt or activities called too often", "error")
                return True

            if self.requires_update(remote_activities["all"], self.activities["all_activities"]):
                try:
                    self._check_for_first_run(silent, trakt_auth)
                    self._do_sync_acitivites(remote_activities)
                finally:
                    self._finalize_process(update_time)

            self._update_all_shows_statisics()
            self._update_all_season_statistics()

        return self.sync_errors

    def _finalize_process(self, update_time):
        if self.progress_dialog is not None:
            self.progress_dialog.close()
            del self.progress_dialog
            self.progress_dialog = None

        if not self.sync_errors:
            self._update_activity_record("all_activities", update_time)
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=widgetRefresh&playing=False")')

    def _do_sync_acitivites(self, remote_activities):
        total_activities = len(self._sync_activities_list)
        for idx, activity in enumerate(self._sync_activities_list):

            try:
                update_time = str(self._get_datetime_now())

                if g.abort_requested():
                    return
                self.current_dialog_text = f"Syncing {activity[0]}"
                self._update_progress(int(float(idx + 1) / total_activities * 100))

                last_activity_update = remote_activities

                if activity[1] is not None:
                    for key in activity[1]:
                        last_activity_update = last_activity_update[key]
                    if not self.requires_update(last_activity_update, self.activities[activity[2]]):
                        g.log(f"Skipping {activity[0]}, does not require update")
                        continue

                g.log(f"Running Activity: {activity[0]}")
                activity[3]()
                self._update_activity_record(activity[2], update_time)
            except ActivitySyncFailure as e:
                g.log(f"Failed to sync activity: {activity[0]} - {e}")
                self.sync_errors = True
                continue

    def _check_for_first_run(self, silent, trakt_auth):
        if not silent and str(self.activities["all_activities"]) == self.base_date and trakt_auth is not None:
            g.notification(g.ADDON_NAME, g.get_language_string(30177))
            # Give the people time to read the damn notification
            xbmc.sleep(500)
            self.silent = False
            self.progress_dialog = xbmcgui.DialogProgressBG()
            self.progress_dialog.create(f"{g.ADDON_NAME}Sync", "Seren: Trakt Sync")

    def _sync_movie_bookmarks(self):
        try:
            self._sync_bookmarks("movies")
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _sync_show_bookmarks(self):
        try:
            self._sync_bookmarks("episodes")
        except Exception as e:
            raise ActivitySyncFailure(e) from e

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
            self.execute_sql("DELETE FROM hidden")
            self.execute_sql(
                db.insert_query,
                (
                    (i.get("trakt_id"), get(i.get("season", i), "mediatype"), key)
                    for key, value in items.items()
                    for i in value
                ),
            )
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _fetch_hidden_section(self, section):
        items = []
        for paged_items in self.trakt_api.get_all_pages_json(f"users/hidden/{section}", ignore_cache=True):
            items.extend(paged_items)
        return {section: items}

    def _sync_watched_movies(self):
        try:
            trakt_watched = self.trakt_api.get_json("/sync/watched/movies", extended="full")
            if len(trakt_watched) == 0:
                return
            self.insert_trakt_movies(trakt_watched)
            self.execute_sql(
                [
                    "UPDATE movies SET watched = 0",
                    f"""
                    UPDATE movies SET watched=1
                    WHERE trakt_id IN ({','.join(str(i.get('trakt_id')) for i in trakt_watched)})
                    """,
                ]
            )
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _sync_collection_movies(self):
        try:
            trakt_collection = self.trakt_api.get_json("sync/collection/movies", extended="full")
            if len(trakt_collection) == 0:
                return
            self.insert_trakt_movies(trakt_collection)
            self.execute_sql(
                [
                    "UPDATE movies SET collected=0",
                    f"""
                    UPDATE movies SET collected=1
                    WHERE trakt_id IN ({','.join(str(i.get('trakt_id')) for i in trakt_collection)})
                    """,
                ]
            )
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _sync_rated_movies(self):
        try:
            trakt_rated = self.trakt_api.get_all_pages_json(
                "/sync/ratings/movies", extended="full", limit=50, ignore_cache=True
            )
            trakt_rated = list(itertools.chain.from_iterable(trakt_rated))

            self.insert_trakt_movies(trakt_rated)

            get = MetadataHandler.get_trakt_info
            with self.create_temp_table(
                "_movies_rated", ["trakt_id", "user_rating"], primary_key="trakt_id"
            ) as temp_table:
                temp_table.insert_data(
                    [
                        {"trakt_id": get(movie, "trakt_id"), "user_rating": get(movie, "user_rating")}
                        for movie in trakt_rated
                    ]
                )
                self.execute_sql(
                    [
                        "UPDATE movies SET user_rating=NULL",
                        """
                        UPDATE movies
                        SET user_rating = (
                            SELECT user_rating
                            FROM _movies_rated
                            WHERE _movies_rated.trakt_id = movies.trakt_id
                        )
                        WHERE EXISTS (
                            SELECT user_rating
                            FROM _movies_rated
                            WHERE _movies_rated.trakt_id = movies.trakt_id
                        )
                        """,
                    ]
                )
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def sync_watched_episodes(self):
        try:
            get = MetadataHandler.get_trakt_info
            trakt_watched = self.trakt_api.get_json("sync/watched/shows", extended="full")
            if not trakt_watched:
                return
            self.insert_trakt_shows(trakt_watched)
            self._mill_if_needed(trakt_watched, self._queue_with_progress)

            with self.create_temp_table(
                "_episodes_watched",
                ["trakt_show_id", "season", "episode", "last_watched_at", "watched"],
                primary_key="trakt_show_id, season, episode",
            ) as temp_table:
                temp_table.insert_data(
                    [
                        {
                            "trakt_show_id": show.get("trakt_id"),
                            "season": get(season, "season"),
                            "episode": get(episode, "episode"),
                            "last_watched_at": get(episode, "last_watched_at"),
                            "watched": get(episode, "playcount"),
                        }
                        for show in trakt_watched
                        for season in get(show, "seasons", [])
                        for episode in get(season, "episodes", [])
                    ]
                )

                self.execute_sql(
                    [
                        "UPDATE episodes SET watched=0",
                        """
                        UPDATE episodes
                        SET (watched, last_watched_at) = (
                            SELECT watched, last_watched_at
                            FROM _episodes_watched
                            WHERE _episodes_watched.trakt_show_id = episodes.trakt_show_id
                                AND _episodes_watched.season = episodes.season
                                AND _episodes_watched.episode = episodes.number
                        )
                        WHERE EXISTS(
                            SELECT watched, last_watched_at
                            FROM _episodes_watched
                            WHERE _episodes_watched.trakt_show_id = episodes.trakt_show_id
                                AND _episodes_watched.season = episodes.season
                                AND _episodes_watched.episode = episodes.number
                        )
                        """,
                    ]
                )

            self.update_shows_statistics(trakt_watched)
            self.update_season_statistics(
                self.fetchall(
                    f"""
                    SELECT trakt_id FROM seasons
                    WHERE trakt_show_id IN ({','.join({str(i.get('trakt_id')) for i in trakt_watched})})
                    """
                )
            )
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def sync_collection_episodes(self):
        try:
            get = MetadataHandler.get_trakt_info
            trakt_collection = self.trakt_api.get_json("sync/collection/shows", extended="full")
            if not trakt_collection:
                return

            self.insert_trakt_shows(trakt_collection)
            self._mill_if_needed(trakt_collection, self._queue_with_progress)

            with self.create_temp_table(
                "_episodes_collected",
                ["trakt_show_id", "season", "episode", "collected_at", "collected"],
                primary_key="trakt_show_id, season, episode",
            ) as temp_table:
                temp_table.insert_data(
                    [
                        {
                            "trakt_show_id": show.get("trakt_id"),
                            "season": get(season, "season"),
                            "episode": get(episode, "episode"),
                            "collected_at": get(episode, "collected_at"),
                            "collected": get(episode, "collected"),
                        }
                        for show in trakt_collection
                        for season in get(show, "seasons", [])
                        for episode in get(season, "episodes", [])
                    ]
                )

                self.execute_sql(
                    [
                        "UPDATE episodes SET collected=0",
                        """
                        UPDATE episodes
                        SET (collected, collected_at) = (
                            SELECT collected, collected_at
                            FROM _episodes_collected
                            WHERE _episodes_collected.trakt_show_id = episodes.trakt_show_id
                                AND _episodes_collected.season = episodes.season
                                AND _episodes_collected.episode = episodes.number
                        )
                        WHERE EXISTS(
                            SELECT collected, collected_at
                            FROM _episodes_collected
                            WHERE _episodes_collected.trakt_show_id = episodes.trakt_show_id
                                AND _episodes_collected.season = episodes.season
                                AND _episodes_collected.episode = episodes.number
                        )
                        """,
                    ]
                )

            self.update_shows_statistics(trakt_collection)
            self.update_season_statistics(
                self.fetchall(
                    f"""
                    SELECT trakt_id FROM seasons
                    WHERE trakt_show_id IN ({','.join({str(i.get('trakt_id')) for i in trakt_collection})})
                    """
                )
            )

        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _sync_rated_shows(self):
        try:
            trakt_rated_shows = self.trakt_api.get_all_pages_json(
                "sync/ratings/shows", extended="full", limit=50, ignore_cache=True
            )
            trakt_rated_shows = list(itertools.chain.from_iterable(trakt_rated_shows))
            self.insert_trakt_shows(trakt_rated_shows)

            trakt_rated_seasons = self.trakt_api.get_all_pages_json(
                "sync/ratings/seasons", extended="full", limit=50, ignore_cache=True
            )
            trakt_rated_seasons = list(itertools.chain.from_iterable(trakt_rated_seasons))
            self.insert_trakt_shows(i.get("show") for i in trakt_rated_seasons)

            def fetch_rated_episodes(rating):
                return self.trakt_api.get_json(
                    f"sync/ratings/episodes/{rating}", extended="full", no_paging=True, timeout=90
                )

            self._queue_with_progress(fetch_rated_episodes, [(i,) for i in range(1, 11)])
            trakt_rated_episodes = self.mill_task_queue.wait_completion()
            self.insert_trakt_shows(i.get("show") for i in trakt_rated_episodes)

            self._mill_if_needed(
                trakt_rated_shows + trakt_rated_seasons + trakt_rated_episodes, self._queue_with_progress
            )

            get = MetadataHandler.get_trakt_info

            with self.create_temp_table(
                "_shows_rated", ["trakt_id", "user_rating"], primary_key="trakt_id"
            ) as temp_table:
                temp_table.insert_data(
                    [
                        {"trakt_id": get(show, "trakt_id"), "user_rating": get(show, "user_rating")}
                        for show in trakt_rated_shows
                    ]
                )
                self.execute_sql(
                    [
                        "UPDATE shows SET user_rating=NULL",
                        """
                        UPDATE shows
                        SET user_rating = (
                            SELECT user_rating
                            FROM _shows_rated
                            WHERE _shows_rated.trakt_id = shows.trakt_id
                        )
                        WHERE EXISTS (
                            SELECT user_rating
                            FROM _shows_rated
                            WHERE _shows_rated.trakt_id = shows.trakt_id
                        )
                        """,
                    ]
                )

            with self.create_temp_table(
                "_seasons_rated", ["trakt_id", "user_rating"], primary_key="trakt_id"
            ) as temp_table:
                temp_table.insert_data(
                    [
                        {"trakt_id": season.get("trakt_id"), "user_rating": get(season.get("season"), "user_rating")}
                        for season in trakt_rated_seasons
                    ]
                )
                self.execute_sql(
                    [
                        "UPDATE seasons SET user_rating=NULL",
                        """
                        UPDATE seasons
                        SET user_rating = (
                            SELECT user_rating
                            FROM _seasons_rated
                            WHERE _seasons_rated.trakt_id = seasons.trakt_id
                        )
                        WHERE EXISTS (
                            SELECT user_rating
                            FROM _seasons_rated
                            WHERE _seasons_rated.trakt_id = seasons.trakt_id
                        )
                        """,
                    ]
                )

            with self.create_temp_table(
                "_episodes_rated", ["trakt_id", "user_rating"], primary_key="trakt_id"
            ) as temp_table:
                temp_table.insert_data(
                    [
                        {"trakt_id": episode.get("trakt_id"), "user_rating": get(episode.get("episode"), "user_rating")}
                        for episode in trakt_rated_episodes
                    ]
                )
                self.execute_sql(
                    [
                        "UPDATE episodes SET user_rating=NULL",
                        """
                        UPDATE episodes
                        SET user_rating = (
                            SELECT user_rating
                            FROM _episodes_rated
                            WHERE _episodes_rated.trakt_id = episodes.trakt_id
                        )
                        WHERE EXISTS (
                            SELECT user_rating
                            FROM _episodes_rated
                            WHERE _episodes_rated.trakt_id = episodes.trakt_id
                        )
                        """,
                    ]
                )

        except Exception as e:
            raise ActivitySyncFailure(e)

    def _filter_lists_items_that_needs_updating(self, requested):
        # TODO: This is never called, the query is also broken and we don't seem to sync lists
        if len(requested) == 0:
            return requested

        get = MetadataHandler.get_trakt_info
        query = """WITH requested(trakt_id, meta_hash, updated_at) AS (VALUES {}) select r.trakt_id as trakt_id from
        requested as r left join lists as db on r.trakt_id == db.trakt_id  where db.trakt_id IS NULL or (Datetime(
        db.last_updated) < Datetime(r.updated_at)) or db.list_type == 'Unknown' """.format(
            ",".join(
                f"""({i.get("trakt_id")}, '{self.trakt_api.meta_hash}', '{i.get("dateadded", get(i, "dateadded"))}')"""
                for i in requested
                if i.get("trakt_id")
            )
        )

        result = {r["trakt_id"] for r in self.fetchall(query)}
        return [r for r in requested if r.get("trakt_id") and r.get("trakt_id") in result]

    def _update_progress(self, progress, text=None):
        if not self.silent:
            if text:
                self.progress_dialog.update(progress, text)
            else:
                self.progress_dialog.update(progress, self.current_dialog_text)

    def _update_activity_record(self, record, time):
        self.execute_sql(f"UPDATE activities SET {record}=? WHERE sync_id=1", (time,))

    def _sync_bookmarks(self, bookmark_type):
        get = MetadataHandler.get_trakt_info
        self.execute_sql("DELETE FROM bookmarks WHERE type=?", (bookmark_type[:-1],))
        base_sql_statement = "INSERT INTO bookmarks VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING"
        for progress in self.trakt_api.get_all_pages_json(
            f"sync/playback/{bookmark_type}", extended="full", timeout=60, limit=50, ignore_cache=True
        ):
            if bookmark_type == "movies":
                self.execute_sql(
                    base_sql_statement,
                    (
                        (
                            i.get("trakt_id"),
                            int(float(get(i, "percentplayed") / 100) * get(i, "duration")),
                            get(i, "percentplayed"),
                            bookmark_type[:-1],
                            get(i, "paused_at"),
                        )
                        for i in progress
                        if get(i, "percentplayed") and 0 < get(i, "percentplayed") < 100 and get(i, "duration")
                    ),
                )
                self.insert_trakt_movies(progress)
            else:
                self.execute_sql(
                    base_sql_statement,
                    (
                        (
                            i.get("trakt_id"),
                            int(float(i.get("percentplayed") / 100) * get(i['episode'], "duration")),
                            i.get("percentplayed"),
                            bookmark_type[:-1],
                            i.get("paused_at"),
                        )
                        for i in progress
                        if i.get("percentplayed") and 0 < i.get("percentplayed") < 100 and get(i['episode'], "duration")
                    ),
                )
                self.insert_trakt_shows([i['show'] for i in progress if i.get("show")])
                self._mill_if_needed([i['show'] for i in progress if i.get("show")], mill_episodes=True)

    def _queue_with_progress(self, func, args):
        for idx, arg in enumerate(args):
            self.mill_task_queue.put(func, *arg)
            progress = int(float(idx + 1) / len(args) * 100)
            self._update_progress(progress)
