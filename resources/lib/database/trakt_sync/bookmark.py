from resources.lib.database import trakt_sync


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    def get_bookmark(self, trakt_id):
        return self.fetchone("SELECT * FROM bookmarks WHERE trakt_id=?", (trakt_id,))

    def set_bookmark(self, trakt_id, time_in_seconds, media_type, percent_played):
        paused_at = self._get_datetime_now()
        self.execute_sql(
            "REPLACE INTO bookmarks Values (?, ?, ?, ?, ?)",
            (trakt_id, time_in_seconds, percent_played, media_type, paused_at),
        )

    def remove_bookmark(self, trakt_id):
        self.execute_sql("DELETE FROM bookmarks WHERE trakt_id=?", (trakt_id,))

    def get_all_bookmark_items(self, mediatype):
        if mediatype == "episode":
            query = """
                SELECT ep.trakt_show_id   AS trakt_show_id,
                       bm.trakt_id        AS trakt_id,
                       ep.trakt_season_id AS trakt_season_id,
                       bm.resume_time     AS progress,
                       em.value           AS episode,
                       sm.value           AS show
                FROM bookmarks AS bm
                         INNER JOIN episodes AS ep
                                    ON bm.trakt_id = ep.trakt_id
                         INNER JOIN episodes_meta AS em
                                    ON ep.trakt_id = em.id AND em.type = 'trakt'
                         LEFT JOIN shows_meta AS sm
                                   ON ep.trakt_show_id = sm.id AND sm.type = 'trakt'
                WHERE bm.type = 'episode'
                GROUP BY ep.trakt_show_id
                ORDER BY Datetime(bm.paused_at) DESC
                """
        else:
            query = """
                SELECT bm.trakt_id,
                       bm.resume_time AS progress,
                       mm.value       AS trakt_object
                FROM bookmarks AS bm
                         LEFT JOIN movies_meta AS mm
                                   ON bm.trakt_id = mm.id
                WHERE bm.type = 'movie'
                ORDER BY bm.paused_at DESC
                """

        return self.wrap_in_trakt_object(self.fetchall(query))
