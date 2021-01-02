# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

# This whole file is for backwards compatibility
import datetime
import sqlite3

import xbmcvfs

from resources.lib.modules.globals import g


def cache_get(key):
    return g.CACHE.get(key)


def cache_insert(key, value, expiration=datetime.timedelta(hours=24)):
    g.CACHE.set(key, value, expiration=expiration)


def get(func, duration, *args, **kwargs):
    method_class = args[0]
    method_class_name = method_class.__class__.__name__
    cache_str = "{}.{}".format(method_class_name, func.__name__)
    for item in args[1:]:
        cache_str += ".{}".format(item)
    cache_str = cache_str.lower()
    cached_data = g.CACHE.get(cache_str)
    global_cache_ignore = False
    ignore_cache = kwargs.pop("seren_reload", kwargs.get("ignore_cache", False))
    overwrite_cache = kwargs.pop("overwrite_cache", False)
    if cached_data is not None and ignore_cache and not global_cache_ignore:
        return cached_data
    else:
        result = func(*args, **kwargs)
        if not ignore_cache or overwrite_cache:
            g.CACHE.set(
                cache_str, result, expiration=datetime.timedelta(hours=duration)
            )
        return result


def _get_connection_cursor(file_path):
    conn = _get_connection(file_path)
    return conn.cursor()


def _get_connection(file_path):
    xbmcvfs.mkdirs(g.ADDON_USERDATA_PATH)
    conn = sqlite3.connect(file_path)
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    return conn


def clear_local_bookmarks():
    cursor = _get_connection_cursor(g.get_video_database_path())
    cursor.execute("SELECT * FROM files WHERE strFilename LIKE '%plugin.video.seren%'")
    file_ids = [str(i["idFile"]) for i in cursor.fetchall()]
    for table in ["bookmark", "streamdetails", "files"]:
        cursor.execute(
            "DELETE FROM {} WHERE idFile IN ({})".format(table, ",".join(file_ids))
        )
    cursor.connection.commit()
    cursor.close()
