# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.database import trakt_sync


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    def get_bookmark(self, trakt_id):
        return self.execute_sql(
            "SELECT * FROM bookmarks WHERE trakt_id=?", (trakt_id,)
        ).fetchone()

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
            query = """select ep.trakt_show_id as trakt_show_id, bm.trakt_id as trakt_id, ep.trakt_season_id as 
            trakt_season_id, bm.resume_time as progress, em.value as episode, sm.value as show from bookmarks as bm 
            inner join episodes as ep on bm.trakt_id = ep.trakt_id inner join episodes_meta as em on ep.trakt_id = 
            em.id and em.type == 'trakt' left join shows_meta as sm on ep.trakt_show_id = sm.id and sm.type == 'trakt' 
            WHERE bm.type = 'episode' GROUP BY ep.trakt_show_id ORDER BY Datetime(bm.paused_at) DESC """
        else:
            query = """select bm.trakt_id, bm.resume_time as progress, mm.value as trakt_object from bookmarks as bm 
            left join movies_meta as mm on bm.trakt_id = mm.id and mm.type = 'trakt' WHERE bm.type = 'movie'
             ORDER BY bm.paused_at desc """

        return self.wrap_in_trakt_object(self.execute_sql(query).fetchall())
