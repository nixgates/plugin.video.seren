# -*- coding: utf-8 -*-

import threading
from datetime import datetime

from resources.lib.common import tools
from resources.lib.common.worker import ThreadPool
from resources.lib.gui import seren_dialog

try:
    from Queue import Queue
except:
    from queue import Queue

try:
    from sqlite3 import dbapi2 as db, OperationalError
except ImportError:
    from pysqlite2 import dbapi2 as db, OperationalError

database_path = tools.traktSyncDB


class TraktSyncDatabase:
    def __init__(self):

        self.activites = {}

        self._build_show_table()
        self._build_episode_table()
        self._build_movies_table()
        self._build_hidden_items()
        self._build_sync_activities()
        self._build_season_table()

        self.item_list = []
        self.threads = []
        self.task_queue = ThreadPool(workers=4)
        self.queue_finished = False
        self.task_len = 0
        self.base_date = '1970-01-01T00:00:00'
        self.number_of_threads = 20

        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM activities WHERE sync_id=1')
        self.activites = cursor.fetchone()

        # If you make changes to the required meta in any indexer that is cached in this database
        # You will need to update the below version number to match the new addon version
        # This will ensure that the metadata required for operations is available

        self.last_meta_update = '1.4.0'

        if self.activites is None:
            meta = '{}'
            cursor.execute("UPDATE shows SET kodi_meta=?", (meta,))
            cursor.execute("UPDATE seasons SET kodi_meta=?", (meta,))
            cursor.execute("UPDATE episodes SET kodi_meta=?", (meta,))
            cursor.execute("UPDATE movies SET kodi_meta=?", (meta,))

            cursor.execute('INSERT INTO activities(sync_id, all_activities, shows_watched, movies_watched,'
                           ' movies_collected, shows_collected, hidden_sync, shows_meta_update, movies_meta_update,'
                           'seren_version, trakt_username) '
                           'VALUES(1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           (self.base_date, self.base_date, self.base_date, self.base_date, self.base_date,
                            self.base_date, self.base_date, self.base_date, self.last_meta_update,
                            tools.getSetting('trakt.username')))
            cursor.connection.commit()
            cursor.execute('SELECT * FROM activities WHERE sync_id=1')
            self.activites = cursor.fetchone()
        cursor.close()

        if self.activites is not None:
            self._check_database_version()


    def _check_database_version(self):

        # If we are updating from a database prior to database versioning, we must clear the meta data

        # Migrate from older versions before trakt username tracking
        if 'trakt_username' not in self.activites and tools.getSetting('trakt.auth') != '':
            tools.log('Upgrading Trakt Sync Database Version to support Trakt username identification')
            cursor = self._get_cursor()
            cursor.execute('ALTER TABLE activities ADD COLUMN trakt_username TEXT')
            cursor.execute('UPDATE activities SET trakt_username = ?', (tools.getSetting('trakt.username'),))
            cursor.connection.commit()
            cursor.close()

        # Migrate from an old version before database migrations
        if 'seren_version' not in self.activites:
            tools.log('Upgrading Trakt Sync Database Version')
            self.clear_all_meta(False)
            cursor = self._get_cursor()
            cursor.execute('ALTER TABLE activities ADD COLUMN seren_version TEXT')
            cursor.execute('UPDATE activities SET seren_version = ?', (self.last_meta_update,))
            cursor.connection.commit()
            cursor.close()

        if tools.check_version_numbers(self.activites['seren_version'], self.last_meta_update):
            tools.log('Upgrading Trakt Sync Database Version')
            self.clear_all_meta(False)
            cursor = self._get_cursor()
            cursor.execute('UPDATE activities SET seren_version=?', (self.last_meta_update,))
            cursor.connection.commit()
            cursor.close()
            return

        if tools.check_version_numbers(tools.addonVersion, self.activites['seren_version']) and \
                        self.activites['seren_version'] != self.last_meta_update:
            tools.log('Downgrading Trakt Sync Database Version')
            self.clear_all_meta(False)
            cursor = self._get_cursor()
            cursor.execute('UPDATE activities SET seren_version=?', (self.last_meta_update,))
            cursor.connection.commit()
            cursor.close()
            return

    def _build_show_table(self):
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS shows '
                       '(trakt_id INTEGER PRIMARY KEY, '
                       'kodi_meta TEXT NOT NULL, '
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
                       'kodi_meta TEXT NOT NULL, '
                       'last_updated TEXT NOT NULL, '
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
                       'movies_meta_update TEXT NOT NULL,'
                       'seren_version TEXT NOT NULL,'
                       'trakt_username TEXT) '
                       )
        cursor.connection.commit()
        cursor.close()

    def _get_cursor(self):
        conn = _get_connection()
        conn.execute("PRAGMA FOREIGN_KEYS = 1")
        cursor = conn.cursor()
        return cursor

    def flush_activities(self, clear_meta=True):
        if clear_meta:
            self.clear_all_meta()
        cursor = self._get_cursor()
        cursor.execute('DROP TABLE activities')
        cursor.connection.commit()
        cursor.close()

    def clear_user_information(self):
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=0')
        cursor.execute('UPDATE episodes SET collected=0')
        cursor.execute('UPDATE movies SET watched=0')
        cursor.execute('UPDATE movies SET collected=0')
        cursor.connection.commit()
        cursor.close()
        self.set_trakt_user('')
        tools.showDialog.notification(tools.addonName + ': Trakt', tools.lang(40260), time=5000)

    def set_trakt_user(self, trakt_username):
        cursor = self._get_cursor()
        tools.log('Setting Trakt Username: %s' % trakt_username)
        cursor.execute('UPDATE activities SET trakt_username=?', (trakt_username,))
        cursor.connection.commit()
        cursor.close()

    def clear_all_meta(self, notify=True):
        if notify:
            confirm = tools.showDialog.yesno(tools.addonName, tools.lang(40139))
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
        tools.showDialog.notification(tools.addonName + ': Trakt', tools.lang(40261), time=5000)

    def clear_specific_meta(self, trakt_object):

        if 'seasons' in trakt_object:
            show_id = trakt_object['show_id']
            season_no = trakt_object['seasons'][0]['number']
            cursor = self._get_cursor()
            cursor.execute('UPDATE episodes SET kodi_meta=? WHERE show_id=? AND season=?', ('{}', show_id, season_no))
            cursor.execute('UPDATE seasons SET kodi_meta=? WHERE show_id=? AND season=?', ('{}', show_id, season_no))
            cursor.connection.commit()
            cursor.close()

        elif 'shows' in trakt_object:
            show_id = trakt_object['shows'][0]['ids']['trakt']
            cursor = self._get_cursor()
            cursor.execute('UPDATE shows SET kodi_meta=? WHERE trakt_id=?', ('{}', show_id))
            cursor.execute('UPDATE episodes SET kodi_meta=? WHERE show_id=? ', ('{}', show_id))
            cursor.execute('UPDATE seasons SET kodi_meta=? WHERE show_id=? ', ('{}', show_id))
            cursor.connection.commit()
            cursor.close()

        elif 'episodes' in trakt_object:
            trakt_id = trakt_object['episodes'][0]['ids']['trakt']
            cursor = self._get_cursor()
            cursor.execute('UPDATE episodes SET kodi_meta=? WHERE trakt_id=? ', ('{}', trakt_id))
            cursor.connection.commit()
            cursor.close()

        elif 'movies' in trakt_object:
            trakt_id = trakt_object['movies'][0]['ids']['trakt']
            cursor = self._get_cursor()
            cursor.execute('UPDATE movies SET kodi_meta=? WHERE trakt_id=? ', ('{}', trakt_id))
            cursor.connection.commit()
            cursor.close()


    def re_build_database(self):
        confirm = tools.showDialog.yesno(tools.addonName, tools.lang(40139))
        if confirm == 0:
            return

        cursor = self._get_cursor()
        cursor.execute('DROP TABLE shows')
        cursor.execute('DROP TABLE seasons')
        cursor.execute('DROP TABLE episodes')
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
        tools.showDialog.notification(tools.addonName + ': Trakt', tools.lang(40262), time=5000)


def _bring_out_your_dead(population):
    dead = None
    remaining_population = [i for i in population if i is not dead]
    return remaining_population


def _utc_now_as_trakt_string():
    date = datetime.utcnow()
    return date.strftime(tools.trakt_gmt_format)


def _strf_local_date(datetime_object):
    return datetime_object.strftime('%Y-%m-%dT%H:%M:%S')


def _parse_local_date_format(datestring):
    return tools.datetime_workaround(datestring, tools.trakt_gmt_format.strip('.000Z'), date_only=False)


def _requires_update(new_date, old_date):
    if tools.datetime_workaround(new_date, tools.trakt_gmt_format, False) > \
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
