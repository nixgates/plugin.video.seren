# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import collections
import copy
import datetime
import hashlib
import json
import os
import re
import sys
import time

import xbmc
import xbmcvfs

from resources.lib.third_party import pytz

try:
    from urlparse import parse_qsl, parse_qs, unquote, urlparse, urljoin
    from urllib import urlencode, quote_plus, quote
except ImportError:
    from urllib.parse import (
        parse_qsl,
        urlencode,
        quote_plus,
        parse_qs,
        quote,
        unquote,
        urlparse,
        urljoin,
    )

try:
    basestring = basestring  # noqa # pylint: disable=undefined-variable
    unicode = unicode  # noqa # pylint: disable=undefined-variable
    xrange = xrange  # noqa # pylint: disable=undefined-variable
except NameError:
    basestring = str
    unicode = str
    xrange = range

try:
    FileExistsError = FileExistsError
except NameError:
    FileExistsError = Exception
try:
    WindowsError = WindowsError
except NameError:
    WindowsError = Exception

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

youtube_url = "plugin://plugin.video.youtube/play/?video_id={}"

try:
    xrange = range
except NameError:
    pass

try:
    from collections import Mapping

    mapping_type = Mapping
except ImportError:
    mapping_type = collections.Mapping

DIGIT_REGEX = re.compile(r"\d")
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
SORT_TOKENS = [
    "a ",
    "das ",
    "de ",
    "der ",
    "die ",
    "een ",
    "el ",
    "het ",
    "i ",
    "il ",
    "l'",
    "la ",
    "le ",
    "les ",
    "o ",
    "the ",
]


def copy2clip(txt):
    """
    Takes a text string and attempts to copy it to the clipboard of the device
    :param txt: Text to send to clipboard
    :type txt: str
    :return: None
    :rtype: None
    """
    import subprocess

    platform = sys.platform
    if platform == "win32":
        try:
            cmd = "echo " + txt.strip() + "|clip"
            return subprocess.check_call(cmd, shell=True)
        except Exception as e:
            log("Failure to copy to clipboard, \n{}".format(e), "error")
    elif platform == "linux2":
        try:
            from subprocess import Popen, PIPE

            p = Popen(["xsel", "-pi"], stdin=PIPE)
            p.communicate(input=txt)
        except Exception as e:
            log("Failure to copy to clipboard, \n{}".format(e), "error")


def parse_datetime(string_date, format_string="%Y-%m-%d", date_only=True):
    """
    Attempts to pass over provided string and return a date or datetime object
    :param string_date: String to parse
    :type string_date: str
    :param format_string: Format of str
    :type format_string: str
    :param date_only: Whether to return a date only object or not
    :type date_only: bool
    :return: Datetime.Datetime or Datetime.Date object
    :rtype: object
    """
    if not string_date:
        return None
    try:
        if date_only:
            res = datetime.datetime.strptime(string_date, format_string).date()
        else:
            res = datetime.datetime.strptime(string_date, format_string)
    except TypeError:
        if date_only:
            res = datetime.datetime(*(time.strptime(string_date, format_string)[0:6])).date()
        else:
            res = datetime.datetime(*(time.strptime(string_date, format_string)[0:6]))

    return res


def shortened_debrid(debrid):
    """
    Returns a display like version of provided backend label
    :param debrid: backend debrid label
    :type debrid: str
    :return: shorthand display style debrid label
    :rtype: str
    """
    debrid = debrid.lower()
    if debrid == "premiumize":
        return "PM"
    if debrid == "real_debrid":
        return "RD"
    if debrid == "all_debrid":
        return "AD"
    return ""


def source_size_display(size):
    """
    Converts source size (MB) to (GB) display string
    :param size: Size of source in MB
    :type size: int
    :return: Formatted string for size in GB
    :rtype: str
    """
    size = int(size)
    size = float(size) / 1024
    size = "{0:.2f} GB".format(size)
    return size


def paginate_list(list_items, page, limit):
    """
    Paginate items and returns requested page
    :param list_items: list of items to paginate
    :type list_items: list
    :param page: requested page
    :type page: int
    :param limit: items per page
    :type limit: int
    :return: items on page
    :rtype: list
    """
    pages = [list_items[i: i + limit] for i in xrange(0, len(list_items), limit)]
    if len(pages) > page - 1:
        return pages[page - 1]
    else:
        return []


def italic_string(text):
    """
    Ease of use method to return a italic like ready string for display in Kodi
    :param text: Text to display in italics
    :type text: str
    :return: Formatted string
    :rtype: str
    """
    from resources.lib.modules.globals import g

    return "[I]{}[/I]".format(g.decode_py2(text))


def compare_version_numbers(current, new):
    """
    Comapres provided version numbers and returns True if new version is higher
    :param current: Version number to check against
    :type current: str
    :param new: Remote/New version number to check against
    :type new: str
    :return: True if new version number is higher than the current, else False
    :rtype: bool
    """
    current = current.split(".")
    new = new.split(".")
    step = 0
    if int(current[0]) > int(new[0]):
        return False
    for i in current:
        if int(new[step]) > int(i):
            return True
        if int(i) < int(new[step]):
            return False
        step += 1
    return False


def get_item_information(action_args):
    """
    Ease of use tool to retrieve items meta from TraktSyncDatabase based on action arguments
    :param action_args: action arguments received in call to Seren
    :type action_args: dict
    :return: Metadata for item
    :rtype: dict
    """
    if action_args is None:
        return None
    item_information = {"action_args": action_args}
    if action_args["mediatype"] == "tvshow":
        from resources.lib.database.trakt_sync import shows

        item_information.update(
            shows.TraktSyncDatabase().get_show(action_args["trakt_id"])
        )
        return item_information
    elif action_args["mediatype"] == "season":
        from resources.lib.database.trakt_sync import shows

        item_information.update(
            shows.TraktSyncDatabase().get_season(
                action_args["trakt_id"], action_args["trakt_show_id"]
            )
        )
        return item_information
    elif action_args["mediatype"] == "episode":
        from resources.lib.database.trakt_sync import shows

        item_information.update(
            shows.TraktSyncDatabase().get_episode(
                action_args["trakt_id"], action_args["trakt_show_id"]
            )
        )
        return item_information
    elif action_args["mediatype"] == "movie":
        from resources.lib.database.trakt_sync import movies

        item_information.update(
            movies.TraktSyncDatabase().get_movie(action_args["trakt_id"])
        )
        return item_information


def deconstruct_action_args(action_args):
    """
    Attempts to create a dictionary from the calls action args
    :param action_args: potential url quoted, stringed dict
    :type action_args:  str
    :return: unquoted and loaded dictionary
    :rtype: dict, NoneType
    """
    return json.loads(unquote(action_args))


def construct_action_args(action_args):
    """
    Takes a json capable response, dumps and urlquotes it ready for URL appending
    :param action_args: Valid JSON
    :type action_args: list, dict
    :return: Url quoted response
    :rtype: str
    """
    return quote(json.dumps(action_args, sort_keys=True))


def extend_array(array1, array2):
    """
    Safe combining of two lists
    :param array1: List to combine
    :type array1: list
    :param array2: List to combine
    :type array2: list
    :return: Combined lists
    :rtype: list
    """
    result = []
    if array1 and isinstance(array1, list):
        result.extend(array1)
    if array2 and isinstance(array2, list):
        result.extend(array2)
    return result


def smart_merge_dictionary(dictionary, merge_dict, keep_original=False, extend_array=True):
    """Method for merging large multi typed dictionaries, it has support for handling arrays.

    :param dictionary:Original dictionary to merge the second on into.
    :type dictionary:dict
    :param merge_dict:Dictionary that is used to merge into the original one.
    :type merge_dict:dict
    :param keep_original:Boolean that indicates if there are duplicated values to keep the original one.
    :type keep_original:bool
    :param extend_array:Boolean that indicates if we need to extend existing arrays with the enw values..
    :type extend_array:bool
    :return:Merged dictionary
    :rtype:dict
    """
    if not isinstance(dictionary, dict) or not isinstance(merge_dict, dict):
        return dictionary
    for new_key, new_value in merge_dict.items():
        original_value = dictionary.get(new_key, {})
        if isinstance(new_value, (dict, collections.Mapping)):
            if original_value is None:
                original_value = {}
            new_value = smart_merge_dictionary(original_value, new_value, keep_original)
        else:
            if original_value and keep_original:
                continue
            if extend_array and isinstance(original_value, (list, set)) and isinstance(
                    new_value, (list, set)
            ):
                original_value.extend(x for x in new_value if x not in original_value)
                try:
                    new_value = sorted(original_value)
                except TypeError:  # Sorting of complex array doesn't work.
                    new_value = original_value
                    pass
        if new_value:
            dictionary[new_key] = new_value
    return dictionary


def freeze_object(o):
    """
    Takes in a iterable object, freezes all dicts, tuples lists/sets
    :param o: Object to free
    :type o: dict/set/list/tuple
    :return: Hashable object
    :rtype: tuple, frozenset
    """
    if isinstance(o, dict):
        return frozenset({k: freeze_object(v) for k, v in o.items()}.items())

    if isinstance(o, (set, tuple, list)):
        return tuple([freeze_object(v) for v in o])

    return o


def md5_hash(value):
    """
    Returns MD5 hash of given value
    :param value: object to hash
    :type value: object
    :return: Hexdigest of hash
    :rtype: str
    """
    return hashlib.md5(str(repr(value)).encode()).hexdigest()


# Re-added for provider backwards compatibility support
def log(msg, level):
    """
    Legacy compat method to log message
    :param msg: Message to write to log
    :type msg: str
    :param level: Log level
    :type level: str
    :return: None
    :rtype: None
    """
    from resources.lib.modules.globals import g

    g.log(msg, level)


def run_threaded(target_func, *args, **kwargs):
    """
    Ease of use method to spawn a new thread and run without joining
    :param target_func: function to run
    :type target_func: Any
    :param args: tuple of arguments to pass through to function
    :type args: (int) - > None
    :param kwargs: dictionary of kwargs to pass to function
    :type kwargs: (int) - > None
    :return: None
    :rtype: None
    """
    from threading import Thread

    thread = Thread(target=target_func, args=args, kwargs=kwargs)
    thread.start()


def get_clean_number(value):
    """
    De-strings stringed int/float and returns respective type
    :param value: Stringed value of an integer or float
    :type value: str
    :return: Converted int or float or None if value error
    :rtype: int, float, None
    """
    if isinstance(value, (int, float)):
        return value
    try:
        if "." in value:
            return float(value)
        else:
            return int(value.replace(",", ""))
    except ValueError:
        return None


def ensure_path_is_dir(path):
    """
    Ensure provided path string will work for kodi methods involving directories
    :param path: Path to directory
    :type path: str
    :return: Formatted path
    :rtype: str
    """
    if not path.endswith("\\") and sys.platform == "win32":
        if path.endswith("/"):
            path = path.split("/")[0]
        return path + "\\"
    elif not path.endswith("/") and sys.platform == "linux2":
        return path + "/"
    return path


def safe_round(x, y=0):
    """PY2 and PY3 equal rounding, its up to 15 digits behind the comma.

    :param x: value to round
    :type x: float
    :param y: decimals behind the comma
    :type y: int
    :return: rounded value
    :rtype: float
    """
    place = 10 ** y
    rounded = (int(x * place + 0.5 if x >= 0 else -0.5)) / place
    if rounded == int(rounded):
        rounded = int(rounded)
    return rounded


def safe_dict_update(dictionary, value):
    """Checks the value against not valid types to update the dictionary

    :param dictionary:dictionary to update
    :type dictionary:dict
    :param value:value to update the supplied dictionary
    :type value:dict
    :return:updated dictionary
    :rtype:dict
    """
    if dictionary is None:
        return dictionary
    if value and isinstance(value, dict):
        dictionary.update(copy.deepcopy(value))
    return dictionary


def is_stub():
    """Checks if the current loaded xbmc lib is from kodistubs

    :return:True or False indicating if this is a kodistub
    :rtype:bool
    """
    return hasattr(xbmc, "__kodistubs__")


def validate_path(path):
    """Returns the translated path.

    :param path:Path to format
    :type path:str
    :return:Translated path
    :rtype:str
    """
    if hasattr(xbmc, "validatePath"):
        path = xbmc.validatePath(path)  # pylint: disable=no-member
    else:
        path = xbmcvfs.validatePath(path)  # pylint: disable=no-member
    return path


def translate_path(path):
    """Validates the path against the running platform and ouputs the clean path.

    :param path:Path to be verified
    :type path:str
    :return:Verified and cleaned path
    :rtype:str
    """
    if hasattr(xbmc, "translatePath"):
        path = xbmc.translatePath(path)  # pylint: disable=no-member
    else:
        path = xbmcvfs.translatePath(path)  # pylint: disable=no-member
    return path


def create_multiline_message(line1=None, line2=None, line3=None, *lines):
    """Creates a message from the supplied lines

    :param line1:Line 1
    :type line1:str
    :param line2:Line 2
    :type line2:str
    :param line3: Line3
    :type line3:str
    :param lines:List of additional lines
    :type lines:list[str]
    :return:New message wit the combined lines
    :rtype:str
    """
    result = []
    if line1:
        result.append(line1)
    if line2:
        result.append(line2)
    if line3:
        result.append(line3)
    if lines:
        result.extend(l for l in lines if l)
    return "\n".join(result)


def validate_date(date_string):
    """Validates the path and returns only the date portion, if it invalidates it just returns none.

    :param date_string:string value with a supposed date.
    :type date_string:str
    :return:formatted datetime or none
    :rtype:str
    """
    result = None
    if not date_string:
        return date_string

    try:
        result = parse_datetime(date_string, "%Y-%m-%d", False)
    except ValueError:
        pass

    if not result:
        try:
            result = parse_datetime(date_string, DATE_FORMAT, False)
        except ValueError:
            pass

    if not result:
        try:
            result = parse_datetime(date_string, "%d %b %Y", False)
        except ValueError:
            pass

    if result and result.year > 1900:
        return result.strftime(DATE_FORMAT)
    return None


def makedirs(name, mode=0o777, exist_ok=False):
    """makedirs(name [, mode=0o777][, exist_ok=False])

    Super-mkdir; create a leaf directory and all intermediate ones.  Works like
    mkdir, except that any intermediate path segment (not just the rightmost)
    will be created if it does not exist. If the target directory already
    exists, raise an OSError if exist_ok is False. Otherwise no exception is
    raised.  This is recursive.

    :param name:Name of the directory to be created
    :type name:str|unicode
    :param mode:Unix file mode for created directories
    :type mode:int
    :param exist_ok:Boolean to indicate whether is should raise on an exception
    :type exist_ok:bool
    """
    try:
        os.makedirs(name, mode)
    except (OSError, FileExistsError, WindowsError):
        if not exist_ok:
            raise


def merge_dicts(*dict_args):
    """
    Given any number of dictionaries, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dictionaries.
    """
    result = {}
    for dictionary in dict_args:
        safe_dict_update(result, dictionary)
    return result


def filter_dictionary(dictionary, *keys):
    """Filters the dictionary with the supplied args

    :param dictionary:Dictionary to filter
    :type dictionary:dict
    :param keys:Keys to filter on
    :type keys:any
    :return:Filtered dictionary
    :rtype:dict
    """
    if not dictionary:
        return None

    return {k: v for k, v in dictionary.items() if any(k.startswith(x) for x in keys)}


def safe_dict_get(dictionary, *path):
    """Safely get the value from a given path taken into account taht the path can be none.

    :param dictionary:Dictionary to take the path from
    :type dictionary:dict
    :param path:Collection of items we try to get form the dict.
    :type path:str
    :return:The value for that given path
    :rtype:any
    """
    if len(path) == 0:
        return dictionary
    current_path = path[0]
    if dictionary is None or not isinstance(dictionary, dict):
        return None

    result = dictionary.get(current_path)
    if isinstance(result, dict):
        return safe_dict_get(result, *path[1:])
    else:
        return dictionary.get(current_path)


def local_timezone():
    if time.daylight:
        offsetHour = time.altzone / 3600
    else:
        offsetHour = time.timezone / 3600
    return pytz.timezone('Etc/GMT%+d' % offsetHour)
