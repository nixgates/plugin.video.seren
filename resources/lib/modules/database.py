# -*- coding: utf-8 -*-
"""
    Seren Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import ast
import hashlib
import re
import threading
import time

from resources.lib.common import tools

try:
    from sqlite3 import dbapi2 as db, OperationalError
except ImportError:
    from pysqlite2 import dbapi2 as db, OperationalError

cache_table = 'cache'

def get(function, duration, *args, **kwargs):
    # type: (function, int, object) -> object or None
    """
    Gets cached value for provided function with optional arguments, or executes and stores the result
    :param function: Function to be executed
    :param duration: Duration of validity of cache in hours
    :param args: Optional arguments for the provided function
    """
    try:

        reload = False
        if 'seren_reload' in kwargs:
            reload = kwargs['seren_reload']
            kwargs.pop('seren_reload')

        key = _hash_function(function, args)
        cache_result = cache_get(key)
        if not reload:
            if cache_result:
                if _is_cache_valid(cache_result['date'], duration):
                    try:
                        return_data = ast.literal_eval(cache_result['value'])
                        return return_data
                    except:
                        return ast.literal_eval(cache_result['value'])

        fresh_result = repr(function(*args))
        if not fresh_result or fresh_result is None:
            # If the cache is old, but we didn't get fresh result, return the old cache
            if cache_result:
                return cache_result
            return None
        insert_thread = threading.Thread(target=cache_insert, args=(key, fresh_result))
        insert_thread.start()

        data = ast.literal_eval(fresh_result)
        return data

    except Exception:
        import traceback
        traceback.print_exc()
        return None

def timeout(function, *args):
    try:
        key = _hash_function(function, args)
        result = cache_get(key)
        return int(result['date'])
    except Exception:
        return None

def cache_get(key):
    # type: (str, str) -> dict or None
    try:
        cursor = _get_connection_cursor(tools.cacheFile)
        cursor.execute("SELECT * FROM %s WHERE key = ?" % cache_table, [key])
        return cursor.fetchone()
    except OperationalError:
        return None

def cache_insert(key, value):
    tools.database_sema.acquire()
    try:
        # type: (str, str) -> None
        cursor = _get_connection_cursor(tools.cacheFile)
        now = int(time.time())
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS %s (key TEXT, value TEXT, date INTEGER, UNIQUE(key))"
            % cache_table
        )
        update_result = cursor.execute(
            "UPDATE %s SET value=?,date=? WHERE key=?"
            % cache_table, (value, now, key))

        if update_result.rowcount is 0:
            cursor.execute(
                "INSERT INTO %s Values (?, ?, ?)"
                % cache_table, (key, value, now)
            )

        cursor.connection.commit()
        tools.database_sema.release()
    except:
        import traceback
        traceback.print_exc()
        tools.database_sema.release()
        pass


def cache_clear():
    try:
        cursor = _get_connection_cursor(tools.cacheFile)

        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except:
                pass
        tools.showDialog.notification(tools.addonName + ': Cache', tools.lang(32078), time=5000)
    except:
        pass

def cache_clear_all():
    cache_clear()
        
def _get_connection_cursor(filepath):
    conn = _get_connection(filepath)
    return conn.cursor()

def _get_connection(filepath):
    tools.makeFile(tools.dataPath)
    conn = db.connect(filepath)
    conn.row_factory = _dict_factory
    return conn

def getSearchHistory(media_type):
    try:
        cursor = _get_connection_cursor(tools.searchHistoryDB)
        cursor.execute("CREATE TABLE IF NOT EXISTS %s (value TEXT, media_type TEXT)" % "history")
        cursor.execute("SELECT * FROM history WHERE media_type = ?", [media_type])
        history = cursor.fetchall()
        history.reverse()
        history = history[:50]
        filter = []
        for i in history:
            if i['value'] not in filter:
                filter.append(i['value'])

        return filter
    except:
        import traceback
        traceback.print_exc()
        return []

def addSearchHistory(search_string, media_type):
    cursor = _get_connection_cursor(tools.searchHistoryDB)
    cursor.execute('CREATE TABLE IF NOT EXISTS %s (value TEXT, media_type TEXT)' % "history")

    cursor.execute(
        "INSERT INTO %s Values (?, ?)"
        % "history", (search_string, str(media_type))
    )

    cursor.connection.commit()

def clearSearchHistory():

    cursor = _get_connection_cursor(tools.searchHistoryDB)
    cursor.execute("DROP TABLE IF EXISTS history")
    try:
        cursor.execute("VACCUM")
    except:
        pass
    cursor.connection.commit()


def getTorrents(trakt_id):
    if tools.getSetting('general.torrentCache') == 'false':
        return []
    try:
        torrent_list = []
        results = []

        cursor = _get_connection_cursor(tools.torrentScrapeCacheFile)
        cursor.execute("SELECT * FROM %s WHERE key = ?" % cache_table, [trakt_id])
        results = cursor.fetchall()
        for torrent in results:
            torrent_list.append(ast.literal_eval(torrent['value']))

        return torrent_list

    except:
        return []

def addTorrent(trakt_id, torrent_object):
    if tools.getSetting('general.torrentCache') == 'false':
        return
    cursor = _get_connection_cursor(tools.torrentScrapeCacheFile)
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS %s (key TEXT, value TEXT, UNIQUE(value))"
        % cache_table
    )
    update_result = cursor.execute(
        "UPDATE %s SET key=? WHERE value=?"
        % cache_table, (trakt_id, str(torrent_object)))

    if update_result.rowcount is 0:
        cursor.execute(
            "INSERT INTO %s Values (?, ?)"
            % cache_table, (trakt_id, str(torrent_object))
        )

    cursor.connection.commit()

def torrent_cache_clear():
    try:

        cursor = _get_connection_cursor(tools.torrentScrapeCacheFile)
        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except:
                pass
    except:
        pass
    tools.showDialog.notification(tools.addonName + ': Cache', tools.lang(32079), time=5000)

def get_assist_torrents():
    try:
        cursor = _get_connection_cursor(tools.activeTorrentsDBFile)
        cursor.execute("SELECT * FROM torrents")
        results = cursor.fetchall()
        return results
    except:
        return None

def clear_non_active_assist():
    cursor = _get_connection_cursor(tools.activeTorrentsDBFile)
    cursor.execute(
        "DELETE FROM torrents WHERE status = 'failed'"
    )
    cursor.execute(
        "DELETE FROM torrents WHERE status = 'finished'"
    )
    cursor.connection.commit()

def add_assist_torrent(debrid_id, provider, status, release_title, progress):
    cursor = _get_connection_cursor(tools.activeTorrentsDBFile)
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS torrents "
        "(debrid_id TEXT PRIMARY KEY, provider TEXT, status TEXT, release_title TEXT, progress TEXT)"
    )
    update_result = cursor.execute(
        "UPDATE torrents SET status=?, progress=? WHERE debrid_id=?", (status, progress, debrid_id))

    if update_result.rowcount is 0:
        cursor.execute(
            "INSERT INTO torrents Values (?, ?, ?, ?, ?)",
            (debrid_id, provider, status, release_title, progress))

    cursor.connection.commit()

def clear_assist_torrents():
    try:
        cursor = _get_connection_cursor(tools.activeTorrentsDBFile)

        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute("DROP TABLE IF EXISTS torrents")
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except:
                pass
    except:
        pass
    tools.showDialog.notification(tools.addonName + ': Cache', tools.lang(32080), time=5000)

def get_providers():
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS providers (hash TEXT,"
            " provider_name TEXT, status TEXT, package TEXT, country TEXT, provider_type TEXT, UNIQUE(hash))"
        )
        cursor.execute("SELECT * FROM providers")
        sources = cursor.fetchall()
        return sources
    except:
        pass

def get_provider_packages():
    tools.log('Getting provider packages')
    cursor = _get_connection_cursor(tools.providersDB)

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS packages (hash TEXT,"
        " pack_name TEXT, author TEXT, remote_meta TEXT, version TEXT, UNIQUE(hash))"
    )
    cursor.execute("SELECT * FROM packages")
    packages = cursor.fetchall()
    return packages

def add_provider_package(pack_name, author, remote_meta, version):
    try:

        hash = _hash_function('%s%s' % (pack_name, author))
        cursor = _get_connection_cursor(tools.providersDB)

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS packages (hash TEXT,"
            " pack_name TEXT, author TEXT, remote_meta TEXT, version TEXT, UNIQUE(hash))"
        )

        update_result = cursor.execute(
            "UPDATE packages SET pack_name=?, author=?, remote_meta=?, version=? WHERE hash=?",
            (pack_name, author, remote_meta, version, hash)
        )

        if update_result.rowcount is 0:
            cursor.execute(
                "INSERT INTO packages Values (?, ?, ?, ?, ?)",
                (hash, pack_name, author, remote_meta, version)
            )
        cursor.connection.commit()
    except:
        import traceback
        traceback.print_exc()
        pass

def remove_provider_package(pack_name):
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute("DELETE FROM packages WHERE pack_name=?", (pack_name,))
        cursor.execute("DELETE FROM providers WHERE package=?", (pack_name,))
        cursor.connection.commit()
    except:
        pass

def add_provider(provider_name, package, status, language, provider_type):
    try:

        hash = _hash_function('%s%s' % (provider_name, package))
        cursor = _get_connection_cursor(tools.providersDB)

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS providers (hash TEXT,"
            " provider_name TEXT, status TEXT, package TEXT, country TEXT, provider_type TEXT, UNIQUE(hash))"
        )

        update_result = cursor.execute(
            "UPDATE providers SET provider_name=?, status=?, package=?, country=?, provider_type=? WHERE hash=?",
            (provider_name, status, package, language, provider_type, hash)
        )

        if update_result.rowcount is 0:
            cursor.execute(
                "INSERT INTO providers Values (?, ?, ?, ?, ?, ?)",
                (hash, provider_name, status, package, language, provider_type)
            )
        cursor.connection.commit()
    except:
        import traceback
        traceback.print_exc()
        pass

def remove_individual_provider(provider_name, package_name):
    try:
        hash = _hash_function('%s%s' % (provider_name, package_name))
        cursor = _get_connection(tools.providersDB)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS providers (hash TEXT,"
            " provider_name TEXT, status TEXT, package TEXT, country TEXT, provider_type TEXT, UNIQUE(hash))"
        )
        cursor.execute("DELETE FROM providers WHERE hash=?", hash
                       )

        cursor.connection.commit()
    except:
        pass


def remove_package_providers(package_name):
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute("DELETE FROM providers WHERE package=?", (package_name,))
        cursor.connection.commit()
    except:
        pass

def clear_providers():
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute("DROP TABLE IF EXISTS providers")
                cursor.execute("VACCUM")
            except:
                pass

            try:
                cursor.execute("DROP TABLE IF EXISTS packages")
                cursor.execute("VACUUM")
            except:
                pass

        cursor.connection.commit()
    except:
        pass

def get_premiumize_transfers():
    try:
        cursor = _get_connection_cursor(tools.premiumizeDB)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS transfers (transfer_id TEXT)"
        )
        cursor.execute("SELECT * FROM transfers")
        transfers = cursor.fetchall()
        return transfers
    except:
        pass

def add_premiumize_transfer(transfer_id):
    try:

        cursor = _get_connection_cursor(tools.premiumizeDB)
        cursor.execute("CREATE TABLE IF NOT EXISTS transfers (transfer_id TEXT)")

        update_result = cursor.execute("UPDATE transfers SET transfer_id=? WHERE transfer_id=?",
                                       (transfer_id, transfer_id))

        if update_result.rowcount is 0:
            cursor.execute("INSERT INTO transfers Values (?)", (transfer_id,))
        cursor.connection.commit()
        cursor.execute("SELECT * FROM transfers")
        transfers = cursor.fetchall()

    except:
        pass

def remove_premiumize_transfer(transfer_id):
    try:
        cursor = _get_connection_cursor(tools.premiumizeDB)
        cursor.execute("DELETE FROM transfers WHERE transfer_id=?", (transfer_id,))
        cursor.connection.commit()
    except:
        pass

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _hash_function(function_instance, *args):
    return _get_function_name(function_instance) + _generate_md5(args)


def _get_function_name(function_instance):
    return re.sub('.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))


def _generate_md5(*args):
    md5_hash = hashlib.md5()
    try:
        [md5_hash.update(str(arg)) for arg in args]
    except:
        [md5_hash.update(str(arg).encode('utf-8')) for arg in args]
    return str(md5_hash.hexdigest())


def _is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff

def cache_version_check():

    if _find_cache_version():
        cache_clear()

        # cache_clear_meta(); cache_clear_providers()
        # tools.infoDialog(tools.lang(32057).encode('utf-8'), sound=True, icon='INFO')
        
def _find_cache_version():

    import os
    versionFile = os.path.join(tools.dataPath, 'cache.v')
    try: 
        with open(versionFile, 'rb') as fh: oldVersion = fh.read()
    except: oldVersion = '0'
    try:
        curVersion = tools.addon('script.module.incursion').getAddonInfo('version')
        if oldVersion != curVersion: 
            with open(versionFile, 'wb') as fh: fh.write(curVersion)
            return True
        else: return False
    except: return False

