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
        sources = False
        reload = False
        if 'seren_reload' in kwargs:
            reload = kwargs['seren_reload']
            kwargs.pop('seren_reload')

        if 'seren_sources' in kwargs:
            sources = True
            kwargs.pop('seren_sources')

        key = _hash_function(function, args, kwargs)
        cache_result = cache_get(key)
        if not reload:
            if cache_result:
                if _is_cache_valid(cache_result['date'], duration):
                    try:
                        return_data = ast.literal_eval(cache_result['value'])
                        return return_data
                    except:
                        return ast.literal_eval(cache_result['value'])
        fresh_result = repr(function(*args, **kwargs))
        if not fresh_result or fresh_result is None:
            # If the cache is old, but we didn't get fresh result, return the old cache
            if cache_result:
                return cache_result
            return None

        data = ast.literal_eval(fresh_result)

        # Because I'm lazy, I've added this crap code so sources won't cache if there are no results
        if not sources or len(data[1]) > 0:
            cache_insert(key, fresh_result)

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
        results = cursor.fetchone()
        cursor.close()
        return results
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
        cursor.close()
    except:
        try:cursor.close()
        except: pass
        import traceback
        traceback.print_exc()
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
        cursor.close()
        history.reverse()
        history = history[:50]
        filter = []
        for i in history:
            if i['value'] not in filter:
                filter.append(i['value'])

        return filter
    except:
        try:cursor.close()
        except: pass
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
    cursor.close()

def clearSearchHistory():

    cursor = _get_connection_cursor(tools.searchHistoryDB)
    cursor.execute("DROP TABLE IF EXISTS history")
    try:
        cursor.execute("VACCUM")
    except:
        pass
    cursor.connection.commit()
    cursor.close()


def getTorrents(item_meta):
    if tools.getSetting('general.torrentCache') == 'false':
        return []
    try:
        cursor = _get_connection_cursor(tools.torrentScrapeCacheFile)

        if 'showInfo' in item_meta:
            season = item_meta['info']['season']
            episode = item_meta['info']['episode']
            trakt_id = item_meta['showInfo']['ids']['trakt']

            cursor.execute("SELECT * FROM %s WHERE trakt_id=? AND package=?" % cache_table, (trakt_id, 'show'))
            torrent_list = cursor.fetchall()
            cursor.execute("SELECT * FROM %s WHERE trakt_id=? AND package=? AND season=?" % cache_table,
                           (trakt_id, 'season', season))
            torrent_list += cursor.fetchall()
            cursor.execute("SELECT * FROM %s WHERE trakt_id=? AND package=? AND season=? AND episode=?" % cache_table,
                           (trakt_id, 'single', season, episode))
            torrent_list += cursor.fetchall()
        else:
            trakt_id = item_meta['ids']['trakt']

            cursor.execute("SELECT * FROM %s WHERE trakt_id=?" % cache_table, (trakt_id,))
            torrent_list = cursor.fetchall()

        cursor.close()

        torrent_list = [ast.literal_eval(torrent['meta']) for torrent in torrent_list]

        return torrent_list

    except:
        try:
            cursor.close()
        except:
            pass
        import traceback
        traceback.print_exc()
        return []

def addTorrent(item_meta, torrent_objects):
    if tools.getSetting('general.torrentCache') == 'false':
        return

    if 'showInfo' in item_meta:
        season = item_meta['info']['season']
        episode = item_meta['info']['episode']
        trakt_id = item_meta['showInfo']['ids']['trakt']
    else:
        season = 0
        episode = 0
        trakt_id = item_meta['ids']['trakt']

    cursor = _get_connection_cursor(tools.torrentScrapeCacheFile)

    try:
        # Confirm we are on the newer version of the torrent cache database
        columns = [i['name'] for i in cursor.execute("PRAGMA table_info(cache);").fetchall()]
        if 'trakt_id' not in columns:
            raise Exception
    except:
        tools.log("WE ARE UPGRADING")
        cursor.execute("DROP TABLE IF EXISTS cache")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS %s ("
            "trakt_id TEXT, "
            "meta TEXT, "
            "hash TEXT, "
            "season TEXT, "
            "episode TEXT, "
            "package, "
            "UNIQUE(hash))"
            % cache_table
        )

    for torrent_object in torrent_objects:
        try:
            hash = torrent_object['hash']
            pack = torrent_object['package']
            update_result = cursor.execute(
                "UPDATE %s SET trakt_id=?, meta=?, season=?, episode=?, package=? WHERE hash=?"
                % cache_table, (trakt_id, str(torrent_object), season, episode, pack,
                                hash))

            if update_result.rowcount is 0:
                cursor.execute(
                    "INSERT INTO %s Values (?, ?, ?, ?, ?, ?)"
                    % cache_table, (trakt_id, str(torrent_object), hash, season, episode, pack)
                )
        except:
            import traceback
            traceback.print_exc()

    cursor.connection.commit()
    cursor.close()

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
    cursor.close()
    tools.showDialog.notification(tools.addonName + ': Cache', tools.lang(32079), time=5000)

def get_assist_torrents():
    try:
        cursor = _get_connection_cursor(tools.activeTorrentsDBFile)
        cursor.execute("SELECT * FROM torrents")
        results = cursor.fetchall()
        cursor.close()
        return results
    except:
        try:cursor.close()
        except: pass
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
    cursor.close()

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
    cursor.close()

def clear_assist_torrents():
    try:
        cursor = _get_connection_cursor(tools.activeTorrentsDBFile)

        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute("DROP TABLE IF EXISTS torrents")
                cursor.execute("VACUUM")
                cursor.connection.commit()
                cursor.close()
            except:
                pass
    except:
        pass
    try:
        cursor.close()
    except:
        pass
    tools.showDialog.notification(tools.addonName + ': Cache', tools.lang(32080), time=5000)

def get_single_provider(provider_name, package, country):
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS providers (hash TEXT,"
            " provider_name TEXT, status TEXT, package TEXT, country TEXT, provider_type TEXT, UNIQUE(hash))"
        )
        cursor.execute("SELECT * FROM providers WHERE provider_name=? AND package=? AND country=?",
                       (provider_name, package, country))
        sources = cursor.fetchone()
        cursor.close()
        return sources
    except:
        try:cursor.close()
        except: pass
        pass

def get_providers():
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS providers (hash TEXT,"
            " provider_name TEXT, status TEXT, package TEXT, country TEXT, provider_type TEXT, UNIQUE(hash))"
        )
        cursor.execute("SELECT * FROM providers")
        sources = cursor.fetchall()
        cursor.close()
        return sources
    except:
        try:cursor.close()
        except: pass
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
    cursor.close()
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
        cursor.close()
    except:
        try:cursor.close()
        except: pass
        import traceback
        traceback.print_exc()
        pass

def remove_provider_package(pack_name):
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute("DELETE FROM packages WHERE pack_name=?", (pack_name,))
        cursor.execute("DELETE FROM providers WHERE package=?", (pack_name,))
        cursor.connection.commit()
        cursor.close()
    except:
        try:cursor.close()
        except: pass
        pass

def add_provider(provider_name, package, status, language, provider_type):
    try:

        hash = _hash_function('%s%s' % (provider_name, package))
        cursor = _get_connection_cursor(tools.providersDB)

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS providers (hash TEXT,"
            " provider_name TEXT, status TEXT, package TEXT, country TEXT, provider_type TEXT, UNIQUE(hash))"
        )

        cursor.execute('SELECT * FROM providers WHERE hash=?', (hash,))
        current_settings = cursor.fetchall()
        if len(current_settings) == 0:
            tools.log('Inserting %s' % hash)
            cursor.execute(
                "INSERT INTO providers Values (?, ?, ?, ?, ?, ?)",
                (hash, provider_name, status, package, language, provider_type)
            )
        else:
            tools.log('skipping provider')

        cursor.connection.commit()
        cursor.close()
    except:
        try:cursor.close()
        except: pass
        import traceback
        traceback.print_exc()
        pass

def remove_individual_provider(provider_name, package_name):
    try:
        hash = _hash_function('%s%s' % (provider_name, package_name))
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS providers (hash TEXT,"
            " provider_name TEXT, status TEXT, package TEXT, country TEXT, provider_type TEXT, UNIQUE(hash))"
        )
        cursor.execute("DELETE FROM providers WHERE hash=?", (hash,)
                       )
        cursor.connection.commit()
        cursor.close()
    except:
        import traceback
        traceback.print_exc()
        try:cursor.close()
        except: pass
        pass


def remove_package_providers(package_name):
    try:
        cursor = _get_connection_cursor(tools.providersDB)
        cursor.execute("DELETE FROM providers WHERE package=?", (package_name,))
        cursor.connection.commit()
        cursor.close()
    except:
        try:cursor.close()
        except: pass
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
        cursor.close()
    except:
        try:cursor.close()
        except: pass
        pass

def get_premiumize_transfers():
    try:
        cursor = _get_connection_cursor(tools.premiumizeDB)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS transfers (transfer_id TEXT)"
        )
        cursor.execute("SELECT * FROM transfers")
        transfers = cursor.fetchall()
        cursor.close()
        return transfers
    except:
        try:cursor.close()
        except: pass
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
        cursor.close()
    except:
        try:cursor.close()
        except: pass
        pass

def remove_premiumize_transfer(transfer_id):
    try:
        cursor = _get_connection_cursor(tools.premiumizeDB)
        cursor.execute("DELETE FROM transfers WHERE transfer_id=?", (transfer_id,))
        cursor.connection.commit()
        cursor.close()
    except:
        try:cursor.close()
        except: pass
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
        curVersion = tools.addon('script.module.seren').getAddonInfo('version')
        if oldVersion != curVersion: 
            with open(versionFile, 'wb') as fh: fh.write(curVersion)
            return True
        else: return False
    except: return False

