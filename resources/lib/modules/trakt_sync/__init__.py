# -*- coding: utf-8 -*-

import threading
from datetime import datetime
import json

from resources.lib.common import tools
try:
    from Queue import Queue
except:
    from queue import Queue

try:
    from sqlite3 import dbapi2 as db, OperationalError
except ImportError:
    from pysqlite2 import dbapi2 as db, OperationalError

database_path = tools.traktSyncDB

# threading.stack_size(64 * 1024)


class TraktSyncDatabase:
    def __init__(self):

        self._build_show_table()
        self._build_episode_table()
        self._build_movies_table()
        self._build_hidden_items()
        self._build_sync_activities()
        self._build_season_table()

        self.item_list = []
        self.threads = []
        self.task_queue = Queue(40)
        self.queue_finished = False
        self.task_len = 0
        self.base_date = '1970-01-01T00:00:00'

        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM activities WHERE sync_id=1')
        self.activites = cursor.fetchone()
        if self.activites is None:
            cursor.execute('INSERT INTO activities(sync_id, all_activities, shows_watched, movies_watched,'
                           ' movies_collected, shows_collected, hidden_sync, shows_meta_update, movies_meta_update) '
                           'VALUES(1, ?, ?, ?, ?, ?, ?, ?, ?)',
                           (self.base_date, self.base_date, self.base_date, self.base_date, self.base_date,
                            self.base_date, self.base_date, self.base_date))
            cursor.connection.commit()
            cursor.execute('SELECT * FROM activities WHERE sync_id=1')
            self.activites = cursor.fetchone()
        cursor.close()

    def _build_show_table(self):
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS shows '
                       '(trakt_id INTEGER PRIMARY KEY, '
                       'kodi_meta INTEGER NOT NULL, '
                       'last_updated TEXT NOT NULL, '
                       'UNIQUE(trakt_id))')
        cursor.connection.commit()
        cursor.close()

    def _build_episode_table(self):
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS episodes ('
                       'show_id INTEGER NOT NULL, '
                       'trakt_id INTEGER NOT NULL PRIMARY KEY, '
                       'season INTEGER NOT NULL, '
                       'kodi_meta TEXT, '
                       'last_updated STRING NOT NULL, '
                       'watched INTEGER NOT NULL, '
                       'collected INTEGER NOT NULL, '
                       'number INTEGER NOT NULL, '
                       'UNIQUE (trakt_id),'
                       'FOREIGN KEY(show_id) REFERENCES shows(trakt_id) ON DELETE CASCADE)')
        cursor.connection.commit()
        cursor.close()

    def _build_season_table(self):
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS seasons ('
                       'show_id INTEGER NOT NULL, '
                       'season INTEGER NOT NULL, '
                       'kodi_meta TEXT NOT NULL, '
                       'FOREIGN KEY(show_id) REFERENCES shows(trakt_id) ON DELETE CASCADE)')
        cursor.connection.commit()
        cursor.close()

    def _build_movies_table(self):
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS movies ('
                       'trakt_id INTEGER NOT NULL PRIMARY KEY, '
                       'kodi_meta TEXT NOT NULL, '
                       'collected INTEGER NOT NULL, '
                       'watched INTEGER NOT NULL, '
                       'last_updated INTEGER NOT NULL, '
                       'UNIQUE (trakt_id))')
        cursor.connection.commit()
        cursor.close()

    def _build_hidden_items(self):
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS hidden ('
                       'id_section TEXT NOT NULL, '
                       'trakt_id INTEGER NOT NULL, '
                       'item_type TEXT NOT NULL, '
                       'section TEXT NOT NULL, '
                       'UNIQUE (id_section))')

        cursor.connection.commit()
        cursor.close()

    def _build_sync_activities(self):
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS activities ('
                       'sync_id INTEGER PRIMARY KEY, '
                       'all_activities TEXT NOT NULL, '
                       'shows_watched TEXT NOT NULL, '
                       'movies_watched TEXT NOT NULL, '
                       'shows_collected TEXT NOT NULL, '
                       'movies_collected TEXT NOT NULL, '
                       'hidden_sync TEXT NOT NULL,'
                       'shows_meta_update TEXT NOT NULL,'
                       'movies_meta_update TEXT NOT NULL) '
                       )
        cursor.connection.commit()
        cursor.close()

    def _get_cursor(self):
        conn = _get_connection()
        conn.execute("PRAGMA FOREIGN_KEYS = 1")
        cursor = conn.cursor()
        return cursor

    def _run_threads(self):
        for i in self.threads:
            i.start()

        for i in self.threads:
            i.join()

    def _start_queue_workers(self):

        self.queue_finished = False

        for i in range(40):
            self.threads.append(threading.Thread(target=self._queue_worker))

        for i in self.threads:
            i.start()

    def _finish_queue_workers(self):

        self.queue_finished = True

        for i in self.threads:
            i.join()

        self.threads = []

    def _queue_worker(self):
        while not self.task_queue.empty() or not self.queue_finished:
            try:
                target = self.task_queue.get(timeout=3)
            except:
                continue
            try:
                target[0](*target[1])
            except:
                pass
            self.task_len -= 1

    def flush_activities(self):
        cursor = self._get_cursor()
        cursor.execute('DROP TABLE activities')
        cursor.connection.commit()
        cursor.close()

    def clear_all_meta(self):
        confirm = tools.showDialog.yesno(tools.addonName, '[COLOR red]WARNING[/COLOR]'
                                                          '/nThis will reset all meta, are you sure?')
        if confirm == 0:
            return

        meta = '{}'
        cursor = self._get_cursor()
        cursor.execute("UPDATE shows SET kodi_meta=?", (meta,))
        cursor.execute("UPDATE seasons SET kodi_meta=?", (meta,))
        cursor.execute("UPDATE episodes SET kodi_meta=?", (meta,))
        cursor.execute("UPDATE movies SET kodi_meta=?", (meta,))
        cursor.connection.commit()
        cursor.close()

    def re_build_database(self):
        confirm = tools.showDialog.yesno(tools.addonName, '[COLOR red]WARNING[/COLOR]'
                                                          '/nThis will reset all meta, are you sure?')
        if confirm == 0:
            return

        cursor = self._get_cursor()
        cursor.execute('DROP TABLE shows')
        cursor.execute('DROP TABLE seasons')
        cursor.execute('DROP TABLE sepisodes')
        cursor.execute('DROP TABLE movies')
        cursor.execute('DROP TABLE activities')
        cursor.execute('DROP TABLE hidden')
        cursor.connection.commit()
        cursor.close()

        self._build_show_table()
        self._build_episode_table()
        self._build_movies_table()
        self._build_hidden_items()
        self._build_sync_activities()
        self._build_season_table()

        from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase as activities
        activities().sync_activities()


def _bring_out_your_dead(population):
    dead = None
    remaining_population = [i for i in population if i is not dead]
    return remaining_population


def _utc_now_as_trakt_string():
    date = datetime.utcnow()
    return date.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def _strf_local_date(datetime_object):
    return datetime_object.strftime('%Y-%m-%dT%H:%M:%S')


def _parse_local_date_format(datestring):
    return tools.datetime_workaround(datestring, '%Y-%m-%dT%H:%M:%S', date_only=False)


def _requires_update(new_date, old_date):
    if tools.datetime_workaround(new_date, '%Y-%m-%dT%H:%M:%S.000Z', False) > \
            tools.datetime_workaround(old_date, '%Y-%m-%dT%H:%M:%S', False):
        return True
    else:
        return False


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _get_connection():
    tools.makeFile(tools.dataPath)
    conn = db.connect(database_path, timeout=60.0)
    conn.row_factory = _dict_factory
    return conn
