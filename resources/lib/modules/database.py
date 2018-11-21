# -*- coding: utf-8 -*-
"""
    Covenant Add-on

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
import time
from resources.lib.common import tools

try:
    from sqlite3 import dbapi2 as db, OperationalError
except ImportError:
    from pysqlite2 import dbapi2 as db, OperationalError

"""
This module is used to get/set cache for every action done in the system
"""

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
        if 'set_key' in kwargs:
            key = _hash_function(kwargs['set_key'])
        else:
            key = _hash_function(function, args)
        cache_result = cache_get(key)
        if cache_result:
            if _is_cache_valid(cache_result['date'], duration):
                try:
                    return ast.literal_eval(cache_result['value'].encode('utf-8'))
                except:
                    return ast.literal_eval(cache_result['value'])

        fresh_result = repr(function(*args))
        if not fresh_result:
            # If the cache is old, but we didn't get fresh result, return the old cache
            if cache_result:
                return cache_result
            return None
        cache_insert(key, fresh_result)
        try:
            data = ast.literal_eval(fresh_result.encode('utf-8'))
            return data
        except:
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
    except:
        import traceback
        traceback.print_exc()


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
        tools.showDialog.notification(tools.addonName + ': Cache', 'All Cache Successfully Cleared', time=5000)
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
        import traceback
        traceback.print_exc()
        pass
    tools.showDialog.notification(tools.addonName + ': Cache', 'Torrent Cache Successfully Cleared', time=5000)

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
        import traceback
        traceback.print_exc()
        pass
    tools.showDialog.notification(tools.addonName + ': Cache', 'Active Torrent Database Successfully Cleared', time=5000)

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
        import traceback
        traceback.print_exc()
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

def uninstall_provider_package(package_name):
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute("DELETE FROM providers WHERE package=?", (package_name,))
        cursor.connection.commit()
    except:
        import traceback
        traceback.print_exc()

def clear_providers():
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute("DROP TABLE IF EXISTS providers")
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except:
                pass
    except:
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
        tools.log('ADDED TRANSFER')
        tools.log("CHECKING IF IT EXISTS")
        cursor.execute("SELECT * FROM transfers")
        transfers = cursor.fetchall()

    except:
        import traceback
        traceback.print_exc()
        pass

def remove_premiumize_transfer(transfer_id):
    try:
        cursor = _get_connection_cursor(tools.premiumizeDB)
        cursor.execute("DELETE FROM transfers WHERE transfer_id=?", (transfer_id,))
        cursor.connection.commit()
    except:
        import traceback
        traceback.print_exc()


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
