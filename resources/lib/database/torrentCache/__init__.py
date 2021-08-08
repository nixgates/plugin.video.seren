# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import collections
import threading

import xbmcgui

from resources.lib.database import Database
from resources.lib.modules.globals import g

schema = {
    "cache": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["TEXT", "NOT NULL"]),
                ("meta", ["PICKLE", "NOT NULL"]),
                ("hash", ["TEXT", "NOT NULL", "PRIMARY KEY"]),
                ("season", ["TEXT", "NOT NULL"]),
                ("episode", ["TEXT", "NOT NULL"]),
                ("package", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(hash)"],
        "default_seed": [],
    }
}


class TorrentCache(Database):
    def __init__(self):
        super(TorrentCache, self).__init__(g.TORRENT_CACHE, schema)
        self.table_name = next(iter(schema))
        self.enabled = g.get_bool_setting("general.torrentCache")

    def get_torrents(self, item_meta):
        if not self.enabled:
            return []
        if item_meta["info"]["mediatype"] == "episode":
            season = item_meta["info"]["season"]
            episode = item_meta["info"]["episode"]
            trakt_id = item_meta["info"]["trakt_show_id"]

            torrent_list = self.fetchall(
                "SELECT * FROM cache WHERE trakt_id=? AND package=?",
                (trakt_id, "tvshow"),
            )
            torrent_list += self.fetchall(
                "SELECT * FROM cache WHERE trakt_id=? AND package=? AND season=?",
                (trakt_id, "season", season),
            )
            torrent_list += self.fetchall(
                "SELECT * FROM cache WHERE trakt_id=? AND package=? AND season=? "
                "AND episode=?",
                (trakt_id, "single", season, episode),
            )

        else:
            trakt_id = item_meta["trakt_id"]
            torrent_list = self.fetchall(
                "SELECT * FROM cache WHERE trakt_id=?", (trakt_id,)
            )

        return [i["meta"] for i in torrent_list]

    def add_torrent(self, item_meta, torrent_objects):
        if not self.enabled:
            return []
        if item_meta["info"]["mediatype"] == "episode":
            season = item_meta["info"]["season"]
            episode = item_meta["info"]["episode"]
            trakt_id = item_meta["info"]["trakt_show_id"]
        else:
            season = 0
            episode = 0
            trakt_id = item_meta["trakt_id"]

        self.execute_sql(
            "REPLACE INTO {} (trakt_id, meta, hash, season, episode, package) "
            "VALUES (?, ?, ?, ?, ?, ?)".format(self.table_name),
            (
                (
                    trakt_id,
                    torrent_object,
                    torrent_object["hash"],
                    season,
                    episode,
                    torrent_object["package"],
                )
                for torrent_object in torrent_objects
            ),
        )

    def clear_all(self):
        g.show_busy_dialog()
        self.rebuild_database()
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30514))
        g.close_busy_dialog()
