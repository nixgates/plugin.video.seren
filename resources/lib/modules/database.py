# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

# This whole file is for backwards compatibility
import datetime

from resources.lib.modules.globals import g


def cache_get(key):
    value = g.CACHE.get(key)
    return value if not value == g.CACHE.NOT_CACHED else None


def cache_insert(key, value, expiration=None):
    if expiration is None:
        expiration = datetime.timedelta(hours=24)
    if value:
        g.CACHE.set(key, value, expiration=expiration)


def get(func, duration, *args, **kwargs):
    method_class = args[0]
    method_class_name = method_class.__class__.__name__
    cache_str = "{}.{}".format(method_class_name, func.__name__)
    for item in args[1:]:
        cache_str += ".{}".format(item)
    cache_str = cache_str.lower()
    cached_data = g.CACHE.get(cache_str)
    if cached_data == g.CACHE.NOT_CACHED:
        cached_data = None
    global_cache_ignore = False
    ignore_cache = kwargs.pop("seren_reload", kwargs.get("ignore_cache", False))
    overwrite_cache = kwargs.pop("overwrite_cache", False)
    if cached_data is not None and ignore_cache and not global_cache_ignore:
        return cached_data
    else:
        result = func(*args, **kwargs)
        if result and (not ignore_cache or overwrite_cache):
            g.CACHE.set(
                cache_str, result, expiration=datetime.timedelta(hours=duration)
            )
        return result
