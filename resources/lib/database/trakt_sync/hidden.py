# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.database import trakt_sync


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    @property
    def insert_query(self):
        return "REPLACE INTO hidden (trakt_id, mediatype, section) VALUES (?, ?, ?)"

    def add_hidden_item(self, trakt_id, media_type, section):
        self.execute_sql(self.insert_query, (trakt_id, media_type, section))

    def get_hidden_items(self, section, media_type=None):

        if media_type is None:
            return self.execute_sql(
                "SELECT trakt_id FROM hidden WHERE section=?", (section,)
            ).fetchall()
        else:
            return self.execute_sql(
                "SELECT trakt_id FROM hidden WHERE section=? and mediatype=?",
                (section, media_type),
            ).fetchall()

    def remove_item(self, section, trakt_id):
        self.execute_sql(
            "DELETE FROM hidden WHERE section=? AND trakt_id=?",
            (str(section), int(trakt_id)),
        )
