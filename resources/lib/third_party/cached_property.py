# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import threading


class cached_property(object):
    """
    A threadsafe cached_property implementation.
    """

    def __init__(self, func):
        self.__doc__ = getattr(func, "__doc__")
        self.func = func
        self.lock = threading.RLock()

    def __get__(self, obj, cls):
        if obj is None:
            return self

        obj_dict = obj.__dict__
        name = self.func.__name__
        try:
            # Return the cached value if already cached
            return obj_dict[name]
        except KeyError:
            with self.lock:
                try:
                    # check if the value was computed before the lock was acquired
                    return obj_dict[name]
                except KeyError:
                    # if not, do the calculation and release the lock
                    return obj_dict.setdefault(name, self.func(obj))
