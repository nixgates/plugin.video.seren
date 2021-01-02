# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import types
from collections import OrderedDict
from functools import wraps

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.modules.exceptions import NormalizationFailure
from resources.lib.modules.globals import g

if g.PYTHON3:
    basestring = str


def handle_single_item_or_list(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if isinstance(args[-1], list) or isinstance(args[-1], types.GeneratorType):
            results = []
            for i in args[-1]:
                try:
                    results.append(func(*args[:-1] + (i,), **kwargs))
                except NormalizationFailure as e:
                    g.log(e, "error")
                    continue
            return results
        return func(*args, **kwargs)

    return wrapper


def handle_single_item_or_list_threaded(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        pool = ThreadPool()
        if isinstance(args[-1], list) or isinstance(args[-1], types.GeneratorType):
            [pool.put(func, *args[:-1] + (i,), **kwargs) for i in args[-1]]
            return pool.wait_completion()
        else:
            return func(*args, **kwargs)

    return wrapper


class ApiBase(object):
    @staticmethod
    def _do_transform_single(info, transform, key, item, value):
        if info.get(key, value):
            value = ApiBase._when_list_extend(
                info.get(key), transform(info.get(key, value))
            )
        elif isinstance(transform, tuple):
            values = tuple(item[k] for k in transform[0] if k in item)
            if len(values) == len(transform[0]):
                value = ApiBase._when_list_extend(info.get(key), transform[1](*values))
        if value is not None and value != "":
            info[key] = value

    @staticmethod
    def _do_transform_multiple(info, transform, key, item, value, data_key):
        if info.get(data_key, value):
            value = ApiBase._when_list_extend(
                info.get(data_key), transform(info.get(data_key, value))
            )
        elif isinstance(transform, tuple):
            values = tuple(item[k] for k in transform[0] if k in item)
            if len(values) == len(transform[0]):
                value = ApiBase._when_list_extend(info.get(key), transform[1](*values))
        [info.update({k: value}) for k in key if value is not None and value != ""]

    @staticmethod
    def _fill_no_transform(key, info, value):
        if isinstance(key, basestring):
            value = ApiBase._when_list_extend(info.get(key), value)
            if value is not None and value != "":
                info[key] = value
        else:
            for info_label in key:
                value = ApiBase._when_list_extend(info.get(info_label), value)
                if value is not None and value != "":
                    info[info_label] = value

    @staticmethod
    def _get_value(data_key, info, item):
        if isinstance(data_key, basestring):
            value = item.get(data_key, info.get(data_key))
        elif data_key:
            value = item
            for subkey in data_key:
                value = value.get(subkey, {})
        else:
            value = None
        return value

    @handle_single_item_or_list
    def _normalize_info(self, translation, item):
        info = {}
        try:
            for data_key, key, transform in translation:
                value = self._get_value(data_key, info, item)
                if (value or isinstance(value, (int, float))) and not transform:
                    self._fill_no_transform(key, info, value)
                if not transform:
                    continue
                if isinstance(key, basestring):
                    self._do_transform_single(info, transform, key, item, value)
                elif isinstance(key, tuple):
                    self._do_transform_multiple(
                        info, transform, key, item, value, data_key
                    )

        except Exception as e:
            raise NormalizationFailure("{} -\n {} - {}".format(e, translation, item))
        return info

    @staticmethod
    def _when_list_extend(possible_array, value):
        result = value
        if isinstance(possible_array, list):
            result = sorted(
                OrderedDict.fromkeys(tools.extend_array(possible_array, value))
            )
        if isinstance(result, list) and len(result) == 0:
            result = None
        return result
