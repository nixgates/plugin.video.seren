import types
from functools import wraps

from resources.lib.common import tools
from resources.lib.modules.exceptions import NormalizationFailure


def handle_single_item_or_list(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if isinstance(args[-1], (list, types.GeneratorType)):
            results = []
            for i in args[-1]:
                try:
                    results.append(func(*args[:-1] + (i,), **kwargs))
                except NormalizationFailure as e:
                    print(e)
                    continue
            return results
        return func(*args, **kwargs)

    return wrapper


class ApiBase:
    @staticmethod
    def _do_transform(info, transform, key, item, value, data_key):
        if info.get(data_key, value) is not None:
            value = ApiBase._when_list_extend(info.get(data_key), transform(info.get(data_key, value)))
        elif isinstance(transform, tuple):
            values = tuple(item[k] for k in transform[0] if k in item)
            if len(values) == len(transform[0]):
                value = ApiBase._when_list_extend(info.get(key), transform[1](*values))
        return value

    @staticmethod
    def _do_transform_single(info, transform, key, item, value, data_key):
        if (value := ApiBase._do_transform(info, transform, key, item, value, data_key)) is not None and value != "":
            info[key] = value

    @staticmethod
    def _do_transform_multiple(info, transform, key, item, value, data_key):
        if (value := ApiBase._do_transform(info, transform, key, item, value, data_key)) is not None and value != "":
            info.update({k: value for k in key})

    @staticmethod
    def _fill_no_transform(key, info, value):
        if isinstance(key, str):
            if (value := ApiBase._when_list_extend(info.get(key), value)) is not None and value != "":
                info[key] = value
        else:
            for info_label in key:
                if (value := ApiBase._when_list_extend(info.get(info_label), value)) is not None and value != "":
                    info[info_label] = value

    @staticmethod
    def _get_value(data_key, info, item):
        if isinstance(data_key, str):
            value = item.get(data_key, info.get(data_key))
        elif data_key:
            value = item
            for subkey in data_key:
                value = value.get(subkey, {})
            value = value or None
        else:
            value = None
        return value

    @staticmethod
    @handle_single_item_or_list
    def _normalize_info(translation, item):
        info = {}
        try:
            for data_key, key, transform in translation:
                value = ApiBase._get_value(data_key, info, item)
                if (value or isinstance(value, (int, float))) and not transform:
                    ApiBase._fill_no_transform(key, info, value)
                if not transform:
                    continue
                if isinstance(key, str):
                    ApiBase._do_transform_single(info, transform, key, item, value, data_key)
                elif isinstance(key, tuple):
                    ApiBase._do_transform_multiple(info, transform, key, item, value, data_key)

        except Exception as e:
            raise NormalizationFailure(f"{e} -\n {translation} - {item}") from e
        return info

    @staticmethod
    def _when_list_extend(possible_array, value):
        result = value
        if isinstance(possible_array, list):
            result = sorted(set(tools.extend_array(possible_array, value)))
        if isinstance(result, list) and len(result) == 0:
            result = None
        return result
