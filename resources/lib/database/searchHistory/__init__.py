# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import collections
import threading

import xbmcgui

from resources.lib.database import Database
from resources.lib.modules.globals import g

migrate_db_lock = threading.Lock()

schema = {
    'search_history': {
        'columns': collections.OrderedDict([
            ("type", ["TEXT", "NOT NULL"]),
            ("value", ["TEXT", "NOT NULL"])
        ]),
        "table_constraints": ["UNIQUE(value, type) ON CONFLICT REPLACE"],
        "default_seed": []
    }
}


class SearchHistory(Database):
    def __init__(self):
        super(SearchHistory, self).__init__(g.SEARCH_HISTORY_DB_PATH, schema, migrate_db_lock)
        self.table_name = next(iter(schema))

    def get_search_history(self, media_type):
        """
        Get all records for the given media type
        :param media_type: Media type to search for
        :type media_type: str
        :return: List of all search terms
        :rtype: list
        """
        return [i['value'] for i in self.execute_sql(
            "SELECT * FROM search_history where type = ? order by RowID desc LIMIT 50",
            (media_type,)).fetchall()]

    def add_search_history(self, media_type, search_string):
        """
        Add a new search history record
        :param media_type: Media type of search
        :type media_type: str
        :param search_string: String uesd in search
        :type search_string: str
        :return: None
        :rtype: None
        """
        self.execute_sql("REPLACE INTO search_history Values (?,?)", (media_type, search_string))

    def clear_search_history(self, media_type=None):
        """
        Clears optionall all records for a specific media type or all if not supplied
        :param media_type: Type of media to restrict clear for
        :type media_type: str
        :return: None
        :rtype: None
        """
        if xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30229)):
            if media_type is not None:
                self.execute_sql("DELETE FROM {} where type = ?".format(self.table_name), (media_type,))
                g.container_refresh()
            else:
                self.execute_sql("DELETE FROM {}".format(self.table_name))
