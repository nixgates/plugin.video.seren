# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import abc
import codecs
import collections
import datetime
import pickle
import threading
import time
from functools import reduce, wraps

import xbmc

from resources.lib.common.tools import freeze_object
from resources.lib.database import Database
from resources.lib.modules.globals import g

migrate_db_lock = threading.Lock()

schema = {
    "cache": {
        "columns": collections.OrderedDict(
            [
                ("id", ["TEXT", "PRIMARY KEY"]),
                ("expires", ["INTEGER", "NOT NULL"]),
                ("data", ["PICKLE", "NOT NULL"]),
                ("checksum", ["INTEGER"]),
                ]
            ),
        "table_constraints": ["UNIQUE(id)"],
        "default_seed": [],
        }
    }


class CacheBase(object):
    """
    Base Class for handling cache calls
    """

    def __init__(self):
        self.global_checksum = None
        self.cache_prefix = "seren"
        self._win = g.HOME_WINDOW

    def _create_key(self, value):
        return "{}.{}".format(self.cache_prefix, value)

    @staticmethod
    def _get_timestamp(timedelta=None):
        date_time = datetime.datetime.now()
        if timedelta:
            date_time = date_time + timedelta
        return int(time.mktime(date_time.timetuple()))

    def _get_checksum(self, checksum):
        if not checksum and not self.global_checksum:
            return None
        if self.global_checksum:
            checksum = "{}-{}".format(self.global_checksum, checksum)
        else:
            checksum = str(checksum)
        return reduce(lambda x, y: x + y, map(ord, checksum))

    @abc.abstractmethod
    def get(self, cache_id, checksum=None):
        """
        Method for fetching values from cache locations
        :param cache_id: ID of cache item to fetch
        :type cache_id: str
        :param checksum: Optional checksum to compare against
        :type checksum: str,int
        :return: Value of cache object if valid
        :rtype: Any
        """

    @abc.abstractmethod
    def set(self, cache_id, data, checksum=None, expiration=datetime.timedelta(hours=24)):
        """
        Stores new value in cache location
        :param cache_id: ID of cache to create
        :type cache_id: str
        :param data: value to store in cache
        :type data: Any
        :param checksum: Optional checksum to apply to item
        :type checksum: str,int
        :param expiration: Expiration of cache value in seconds since epoch
        :type expiration: int
        :return: None
        :rtype:
        """

    @abc.abstractmethod
    def do_cleanup(self):
        """
        Process cleaning up expired values from cache locations
        :return:
        :rtype:
        """

    @abc.abstractmethod
    def clear_all(self):
        """
        Drop all values in cache locations
        :return:
        :rtype:
        """


class Cache(CacheBase):
    """
    Ease of use class to handle storing and retrieving from both mem and disk cache
    """

    def __init__(self):
        super(Cache, self).__init__()
        self._exit = False
        self.enable_mem_cache = True
        self._mem_cache = MemCache()
        self._db_cache = DatabaseCache(g.CACHE_DB_PATH, schema, migrate_db_lock)
        self._auto_clean_interval = datetime.timedelta(hours=4)

    def set_auto_clean_interval(self, interval):
        """
        Sets the auto clean interval to 4 hours if not interval is provided else set it to the interval provided
        :param interval: Timedelta hours to set for interval
        :type interval: datetime.timedelta
        :return:
        :rtype:
        """
        self._auto_clean_interval = datetime.timedelta(hours=4) if not interval else interval

    def get(self, cache_id, checksum=None):
        """
        Method for fetching values from cache locations
        :param cache_id: ID of cache item to fetch
        :type cache_id: str
        :param checksum: Optional checksum to compare against
        :type checksum: str,int
        :return: Value of cache object if valid
        :rtype: Any
        """
        checksum = self._get_checksum(checksum)
        result = None
        if self.enable_mem_cache:
            result = self._mem_cache.get(cache_id, checksum)
        if result is None:
            result, expires = self._db_cache.get(cache_id, checksum)
            if result and self.enable_mem_cache:
                self._mem_cache.set(cache_id, result, checksum)
        return result

    def set(
            self, cache_id, data, checksum=None, expiration=datetime.timedelta(hours=24)
            ):
        """
        Stores new value in cache location
        :param cache_id: ID of cache to create
        :type cache_id: str
        :param data: value to store in cache
        :type data: Any
        :param checksum: Optional checksum to apply to item
        :type checksum: str,int
        :param expiration: Expiration of cache value in seconds since epoch
        :type expiration: int
        :return: None
        :rtype:
        """
        checksum = self._get_checksum(checksum)
        if self.enable_mem_cache and not self._exit:
            self._mem_cache.set(cache_id, data, checksum, expiration)
        if not self._exit:
            self._db_cache.set(cache_id, data, checksum, expiration)

    def _cleanup_required_check(self, lastexecuted, cur_time):
        return (eval(lastexecuted) + self._auto_clean_interval) < cur_time

    def check_cleanup(self):
        """
        Check if a cleanup should be run according to auto_clean_interval and process if required
        :return:
        :rtype:
        """
        cur_time = datetime.datetime.now()
        lastexecuted = self._win.getProperty(self._create_key("clean.lastexecuted"))
        if not lastexecuted:
            self._win.setProperty(self._create_key("clean.lastexecuted"), repr(cur_time))
        elif self._cleanup_required_check(lastexecuted, cur_time):
            self.do_cleanup()

    def do_cleanup(self):
        """
        Process cleaning up expired values from cache locations
        :return:
        :rtype:
        """
        if self._exit:
            return
        if self._win.getProperty(self._create_key("clean.busy")):
            return
        self._win.setProperty(self._create_key("clean.busy"), "busy")

        cur_time = datetime.datetime.now()

        self._db_cache.do_cleanup()
        self._mem_cache.do_cleanup()

        self._win.setProperty(self._create_key("clean.lastexecuted"), repr(cur_time))
        self._win.clearProperty(self._create_key("clean.busy"))

    def clear_all(self):
        """
        Drop all values in cache locations
        :return:
        :rtype:
        """
        self._db_cache.clear_all()
        self._mem_cache.clear_all()

    def close(self):
        """
        Close connections to cache location
        :return:
        :rtype:
        """
        self._exit = True
        self._db_cache.close()
        del self._win

    def __del__(self):
        if not self._exit:
            self.close()


class DatabaseCache(Database, CacheBase):
    """
    Handles disk stored caching
    """

    def __init__(self, db_file, database_layout, threading_lock):
        super(DatabaseCache, self).__init__(db_file, database_layout, threading_lock)
        CacheBase.__init__(self)
        self.cache_table_name = next(iter(database_layout))

    def do_cleanup(self):
        """
        Process cleaning up expired values from cache locations
        :return:
        :rtype:
        """
        monitor = xbmc.Monitor()
        if self._exit or monitor.abortRequested():
            return
        cur_time = datetime.datetime.now()
        if self._win.getProperty(self._create_key("cache.db.clean.busy")):
            return
        self._win.setProperty(self._create_key("cache.db.clean.busy"), "busy")
        query = "DELETE FROM {} where expires < ?".format(self.cache_table_name)
        self.execute_sql(query, (self._get_timestamp(),))
        self.execute_sql("VACUUM")
        self._win.setProperty(self._create_key("cache.mem.clean.busy"), repr(cur_time))
        self._win.clearProperty(self._create_key("cache.mem.clean.busy"))

    def get(self, cache_id, checksum=None):
        """
        Method for fetching values from cache locations
        :param cache_id: ID of cache item to fetch
        :type cache_id: str
        :param checksum: Optional checksum to compare against
        :type checksum: str,int
        :return: Value of cache object if valid
        :rtype: Any
        """
        result = None
        expires = None
        cur_time = self._get_timestamp()
        query = "SELECT expires, data, checksum FROM {} WHERE id = ?".format(
            self.cache_table_name
            )
        cache_data = self.execute_sql(query, (cache_id,)).fetchone()
        if (
                cache_data
                and cache_data["expires"] > cur_time
                and (not checksum or cache_data["checksum"] == checksum)):
            result = cache_data["data"]
        return result, expires

    def set(self, cache_id, data, checksum=None, expiration=datetime.timedelta(hours=24)):
        """
        Stores new value in cache location
        :param cache_id: ID of cache to create
        :type cache_id: str
        :param data: value to store in cache
        :type data: Any
        :param checksum: Optional checksum to apply to item
        :type checksum: str,int
        :param expiration: Expiration of cache value in seconds since epoch
        :type expiration: int
        :return: None
        :rtype:
        """
        expires = self._get_timestamp(expiration)
        query = "INSERT OR REPLACE INTO {}( id, expires, data, checksum) " \
                "VALUES (?, ?, ?, ?)".format(self.cache_table_name)
        self.execute_sql(query, (cache_id, expires, data, checksum))

    def clear_all(self):
        """
        Drop all values in cache locations
        :return:
        :rtype:
        """
        self.rebuild_database()


class MemCache(CacheBase):
    """
    Handles in memory caching
    """

    def __init__(self):
        super(MemCache, self).__init__()
        self._exit = False
        self._index_key = self._create_key("cache.index")
        self._index = set()
        self._get_index()

    def _get_index(self):
        index = self._win_get_property(self._index_key)
        if index:
            self._index = eval(index)

    def _save_index(self):
        if not g.PYTHON3:
            cached_string = repr(self._index).encode("utf-8")
            self._win.setProperty(self._index_key.encode("utf-8"), cached_string)
        else:
            cached_string = repr(self._index)
            self._win.setProperty(self._index_key, cached_string)

    def get(self, cache_id, checksum=None):
        """
        Method for fetching values from cache locations
        :param cache_id: ID of cache item to fetch
        :type cache_id: str
        :param checksum: Optional checksum to compare against
        :type checksum: str,int
        :return: Value of cache object if valid
        :rtype: Any
        """
        result = None
        cached = self._win_get_property(cache_id)
        cur_time = self._get_timestamp()
        if cached:
            cached = pickle.loads(codecs.decode(cached.encode(), "base64"))
            if cached[0] > cur_time:
                if not checksum or checksum == cached[2]:
                    return cached[1]
        return result

    def _win_get_property(self, key):
        return g.encode_py2(self._win.getProperty(key))

    def set(
            self, cache_id, data, checksum=None, expiration=datetime.timedelta(hours=24)
            ):
        """
        Stores new value in cache location
        :param cache_id: ID of cache to create
        :type cache_id: str
        :param data: value to store in cache
        :type data: Any
        :param checksum: Optional checksum to apply to item
        :type checksum: str,int
        :param expiration: Expiration of cache value in seconds since epoch
        :type expiration: int
        :return: None
        :rtype:
        """
        expires = self._get_timestamp(expiration)
        cached = (expires, data, checksum)
        self._win.setProperty(
            g.encode_py2(cache_id),
            g.encode_py2(codecs.encode(pickle.dumps(cached), "base64").decode()),
            )
        self._get_index()
        self._index.add((cache_id, expires))
        self._save_index()

    def do_cleanup(self):
        """
        Process cleaning up expired values from cache locations
        :return:
        :rtype:
        """
        if self._exit:
            return
        self._get_index()
        cur_time = datetime.datetime.now()
        cur_timestamp = self._get_timestamp()
        if self._win.getProperty(self._create_key("cache.mem.clean.busy")):
            return
        self._win.setProperty(self._create_key("cache.mem.clean.busy"), "busy")

        self._get_index()
        for cache_id, expires in self._index:
            if expires < cur_timestamp:
                self._win.clearProperty(g.encode_py2(cache_id))

        self._win.setProperty(self._create_key("cache.mem.clean.busy"), repr(cur_time))
        self._win.clearProperty(self._create_key("cache.mem.clean.busy"))

    def clear_all(self):
        """
        Drop all values in cache locations
        :return:
        :rtype:
        """
        self._get_index()
        for cache_id, expires in self._index:
            self._win.clearProperty(g.encode_py2(cache_id))

    def close(self):
        self._exit = True


def use_cache(cache_hours=12):
    """
    Ease of use decorator to automate caching of method calls
    :param cache_hours: Hours to cache return value for
    :type cache_hours: int
    :return: Functions return value
    :rtype: Any
    """

    def _get_checksum(class_name, func_name):
        relative_methods = {"TraktAPI": {"get_json_cached": ("item.limit",)}}

        settings = relative_methods.get(class_name, {}).get(func_name, [])
        checksum = ""
        for setting in settings:
            checksum += g.get_setting(setting)

        return checksum

    def _decorator(func):
        @wraps(func)
        def _decorated(*args, **kwargs):
            method_class = args[0]
            try:
                global_cache_ignore = g.get_global_setting("ignore.cache") == "true"
            except:
                global_cache_ignore = False
            checksum = _get_checksum(method_class.__class__.__name__, func.__name__)
            ignore_cache = kwargs.pop("ignore_cache", False)
            if ignore_cache or global_cache_ignore:
                return func(*args, **kwargs)
            overwrite_cache = kwargs.pop("overwrite_cache", False)
            hours = kwargs.pop("cache_hours", cache_hours)
            cache_str = "{}.{}.{}.{}".format(
                method_class.__class__.__name__,
                func.__name__,
                hash(freeze_object(args[1:])),
                hash(freeze_object(kwargs)))
            cached_data = g.CACHE.get(cache_str, checksum=checksum)
            if cached_data is None or overwrite_cache:
                fresh_result = func(*args, **kwargs)
                if not fresh_result or \
                        (func.__name__ == "get_sources" and len(fresh_result[1]) == 0):
                    return
                try:
                    g.CACHE.set(
                        cache_str,
                        fresh_result,
                        expiration=datetime.timedelta(hours=hours),
                        checksum=checksum,
                        )
                except TypeError as e:
                    pass
                return fresh_result
            else:
                return cached_data

        return _decorated

    return _decorator
