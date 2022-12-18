import copy
import datetime
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping
from functools import total_ordering
from urllib import parse

import xbmc
import xbmcvfs

youtube_url = "plugin://plugin.video.youtube/play/?video_id={}"

DIGIT_REGEX = re.compile(r"\d")
SORT_TOKENS = [
    "a ",
    "an ",
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
SORT_TOKEN_REGEX = re.compile(r"|".join(fr"^{i}" for i in SORT_TOKENS), re.IGNORECASE)

SHORT_MONTH_LOOKUP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


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
            cmd = f"echo {txt.strip()}|clip"
            return subprocess.check_call(cmd, shell=True)
        except Exception as e:
            log(f"Failure to copy to clipboard, \n{e}", "error")
    elif platform.startswith("linux") or platform == "darwin":
        try:
            from subprocess import Popen, PIPE

            cmd = "pbcopy" if platform == "darwin" else ["xsel", "-pi"]
            kwargs = {"stdin": PIPE, "text": True}
            p = Popen(cmd, **kwargs)
            p.communicate(input=str(txt))
        except Exception as e:
            log(f"Failure to copy to clipboard, \n{e}", "error")


def parse_datetime(string_date, date_only=True):
    """
    Attempts to pass over provided string and return a date or datetime object
    :param string_date: String to parse
    :type string_date: str
    :param date_only: Whether to return a date only object or not
    :type date_only: bool
    :return: datetime.datetime object
    :rtype: datetime.datetime
    """
    if not string_date:
        return None

    # Don't use datetime.datetime.strptime()
    # Workaround for python bug caching of strptime in datetime module.
    # Don't just try to detect TypeError because it breaks meta handler lambda calls occasionally, particularly
    # with unix style threading.
    try:
        res = datetime.datetime.fromisoformat(string_date.rstrip("Z"))
    except ValueError:
        try:
            day, month, year = string_date.split(" ", 2)
            month = SHORT_MONTH_LOOKUP[month]
            res = datetime.datetime(year=int(year), month=month, day=int(day))
        except KeyError as ke:
            raise ValueError(f"Invalid short month name: {ke}") from ke

    return res.date() if date_only else res


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
    if debrid == "all_debrid":  # sourcery skip: assign-if-exp
        return "AD"
    else:
        return ""


def source_size_display(size):
    """
    Converts source size (MB) to (GB) display string
    :param size: Size of source in MB
    :type size: int
    :return: Formatted string for size in GB
    :rtype: str
    """
    if size == "Variable":
        return size

    size = int(size)
    size = float(size) / 1024
    return f"{size:.2f} GB"


def bytes_size_display(size):
    """
    Converts source size (bytes) to best fitting *binary* prefix display string
    :param size: Size of source in bytes
    :type size: int
    :return: Formatted string for size with best fitting *binary* prefix suffix
    :rtype: str
    """
    size = float(size)
    suffix = "B"
    if size > 1024:
        size /= 1024
        suffix = "KiB"
    if size > 1024:
        size = size / 1024
        suffix = "MiB"
    if size > 1024:
        size = size / 1024
        suffix = "GiB"
    if size > 1024:
        size = size / 1024
        suffix = "TiB"
    return f"{size:{'.0f' if size.is_integer() else '.2f'}} {suffix}"


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
    if page - 1 > float(len(list_items)) / limit:
        return []
    return list_items[(page - 1) * limit : page * limit]


def italic_string(text):
    """
    Ease of use method to return a italic like ready string for display in Kodi
    :param text: Text to display in italics
    :type text: str
    :return: Formatted string
    :rtype: str
    """

    return f"[I]{text}[/I]"


def compare_version_numbers(current, new, include_same=False):
    """
    Compares provided version numbers and returns True if new version is higher
    If include_same = True will also return true if the new and old versions match
    :param current: Version number to check against
    :type current: str
    :param new: Remote/New version number to check against
    :type new: str
    :param include_same: Whether to additionally return True if versions match
    :type new: bool
    :return: True if new version number is higher than the current, else False
    :rtype: bool
    """
    if include_same and new == current:
        return True

    current = current.split(".")
    new = new.split(".")
    for step, i in enumerate(new):
        if len(current) - 1 < step:
            return True
        if int(current[step]) > int(i):
            return False
        if int(current[step]) < int(i):
            return True
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

        item_information.update(shows.TraktSyncDatabase().get_show(action_args["trakt_id"]))
        return item_information
    elif action_args["mediatype"] == "season":
        from resources.lib.database.trakt_sync import shows

        item_information.update(
            shows.TraktSyncDatabase().get_season(action_args["trakt_id"], action_args["trakt_show_id"])
        )
        return item_information
    elif action_args["mediatype"] == "episode":
        from resources.lib.database.trakt_sync import shows

        item_information.update(
            shows.TraktSyncDatabase().get_episode(action_args["trakt_id"], action_args["trakt_show_id"])
        )
        return item_information
    elif action_args["mediatype"] == "movie":
        from resources.lib.database.trakt_sync import movies

        item_information.update(movies.TraktSyncDatabase().get_movie(action_args["trakt_id"]))
        return item_information


def deconstruct_action_args(action_args):
    """
    Attempts to create a dictionary from the calls action args
    :param action_args: potential url quoted, stringed dict
    :type action_args:  str
    :return: unquoted and loaded dictionary or str if not json
    :rtype: dict, str
    """
    action_args = parse.unquote(action_args)
    try:
        return json.loads(action_args)
    except ValueError:
        return action_args


def construct_action_args(action_args):
    """
    Takes a json capable response, dumps and urlquotes it ready for URL appending
    :param action_args: Valid JSON
    :type action_args: list, dict
    :return: Url quoted response
    :rtype: str
    """
    return parse.quote(json.dumps(action_args, sort_keys=True))


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
        original_value = copy.deepcopy(dictionary.get(new_key))
        if isinstance(new_value, (dict, Mapping)):
            if original_value is None:
                original_value = {}
            new_value = smart_merge_dictionary(original_value, new_value, keep_original, extend_array)
        else:
            if original_value and keep_original:
                continue
            if extend_array and isinstance(original_value, (list, set)) and isinstance(new_value, (list, set)):
                if isinstance(original_value, set):
                    original_value.update(x for x in new_value if x not in original_value)
                    try:
                        new_value = set(sorted(original_value))
                    except TypeError:  # Sorting of complex array doesn't work.
                        new_value = original_value
                else:
                    original_value.extend(x for x in new_value if x not in original_value)
                    try:
                        new_value = sorted(original_value)
                    except TypeError:  # Sorting of complex array doesn't work.
                        new_value = original_value
        if new_value or new_value == 0 or isinstance(new_value, bool):
            # We want to skip empty lists / dicts / sets
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
        return tuple(freeze_object(v) for v in o)

    return o


def serialize_sets(obj):
    return sorted([str(i) for i in obj]) if isinstance(obj, set) else obj


def md5_hash(value):
    """
    Returns MD5 hash of given value
    :param value: object to hash
    :type value: object
    :return: Hexdigest of hash
    :rtype: str
    """
    if isinstance(value, (tuple, dict, list, set)):
        value = json.dumps(value, sort_keys=True, default=serialize_sets)
    return hashlib.md5(str(value).encode("utf-8")).hexdigest()


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
    :return: The started thread
    :rtype: threading.Thread
    """
    from threading import Thread

    thread = Thread(target=target_func, args=args, kwargs=kwargs)
    thread.start()
    return thread


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
        return float(value) if "." in value else int(value.replace(",", ""))
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
    if sys.platform == "win32":
        if not path.endswith("\\"):
            if path.endswith("/"):
                path = path.rstrip("/")
            return f"{path}\\"
    elif not path.endswith("/"):
        return f"{path}/"
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
    place = 10**y
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
    if hasattr(xbmcvfs, "validatePath"):
        path = xbmcvfs.validatePath(path)  # pylint: disable=no-member
    else:
        path = xbmc.validatePath(path)  # pylint: disable=no-member
    return path


def translate_path(path):
    """Validates the path against the running platform and ouputs the clean path.

    :param path:Path to be verified
    :type path:str
    :return:Verified and cleaned path
    :rtype:str
    """
    if hasattr(xbmcvfs, "translatePath"):
        path = xbmcvfs.translatePath(path)  # pylint: disable=no-member
    else:
        path = xbmc.translatePath(path)  # pylint: disable=no-member
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


def makedirs(name, mode=0o777, exist_ok=False):
    """makedirs(name [, mode=0o777][, exist_ok=False])

    Super-mkdir; create a leaf directory and all intermediate ones.  Works like
    mkdir, except that any intermediate path segment (not just the rightmost)
    will be created if it does not exist. If the target directory already
    exists, raise an OSError if exist_ok is False. Otherwise no exception is
    raised.  This is recursive.

    :param name:Name of the directory to be created
    :type name:str
    :param mode:Unix file mode for created directories
    :type mode:int
    :param exist_ok:Boolean to indicate whether is should raise on an exception
    :type exist_ok:bool
    """
    try:
        os.makedirs(name, mode)
    except OSError:
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
    return {k: v for k in keys if (v := dictionary.get(k))} if dictionary else None


def safe_dict_get(dictionary, *path):
    """Safely get the value from a given path taken into account that the path can be none.

    :param dictionary:Dictionary to take the path from
    :type dictionary:dict
    :param path:Collection of items we try to get form the dict.
    :type path:str
    :return:The value for that given path
    :rtype:any
    """
    if not isinstance(dictionary, dict):
        return None
    if not path:
        return dictionary
    result = dictionary

    for element in path:
        if isinstance(result := result.get(element), dict):
            continue
        else:
            break

    result = copy.deepcopy(result)
    return result


@total_ordering
class FixedSortPositionObject:
    """
    A class that always returns equality for a comparison with any other object
    """

    def __lt__(self, other):
        return False

    def __eq__(self, other):
        return True

    def __neg__(self):
        return self
