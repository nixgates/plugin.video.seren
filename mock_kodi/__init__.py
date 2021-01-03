# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import functools
import json
import os
import re
import shutil
import sys
import time
import types

import polib

from resources.lib.common import tools

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

import xbmc
import xbmcaddon
import xbmcdrm
import xbmcgui
import xbmcplugin
import xbmcvfs

PYTHON3 = True if sys.version_info.major == 3 else False
PYTHON2 = not PYTHON3

if PYTHON2:
    get_input = raw_input  # noqa
else:
    get_input = input

SUPPORTED_LANGUAGES = {
    "en-de": ("en-de", "eng-deu", "English-Central Europe"),
    "en-aus": ("en-aus", "eng-aus", "English-Australia (12h)"),
    "en-gb": ("en-gb", "eng-gbr", "English-UK (12h)"),
    "en-us": ("en-us", "eng-usa", "English-USA (12h)"),
    "de-de": ("de-de", "ger-deu", "German-Deutschland"),
    "nl-nl": ("nl-nl", "dut-nld", "Dutch-NL"),
}


class Directory:
    """Directory class to keep track of items added to the virtual directory of the mock"""

    def __init__(self):
        pass

    history = []
    items = []
    last_action = ""
    next_action = ""
    content = {}
    sort_method = {}

    def handle_directory(self):
        """
        :return:
        :rtype:
        """
        if not MOCK.INTERACTIVE_MODE:
            return

        while True:

            if self.next_action != self.last_action:
                self.history.append(self.last_action)
                self.last_action = self.next_action

            print("-------------------------------")
            print("-1) Back")
            print(" 0) Home")
            print("-------------------------------")
            for idx, item in enumerate(self.items):
                print(" {}) {}".format(idx + 1, item[1]))

            print("")
            print("Enter Action Number")
            action = get_input()
            if self._try_handle_menu_action(action):
                break
            if self._try_handle_context_menu_action(action):
                break
            if self._try_handle_action(action):
                break
            print("Please enter a valid entry")
            time.sleep(1)

        self.items = []
        self._execute_action()

    def _try_handle_menu_action(self, action):
        try:
            action = int(action) - 1
        except:
            return False
        if action == -2:
            if self.history:
                self.next_action = self.history.pop(-1)
                self.last_action = ""
            return True
        if action == -1:
            self.next_action = ""
            return True
        elif -1 < action < len(self.items):
            self.next_action = self.items[action][0]
            return True
        else:
            return False

    def _try_handle_context_menu_action(self, action):
        get_context_check = re.findall(r"c(\d*)", action)
        if len(get_context_check) == 1:
            item = self.items[int(get_context_check[0]) - 1]
            self.items = []
            for context_item in item[0].cm:
                self.items.append(
                    (context_item[0], re.findall(r".*?\((.*?)\)", context_item[1])[0])
                )
            return True
        return False

    def _try_handle_action(self, action):
        if action.startswith("action"):
            try:
                self.next_action[2] = re.findall(r"action (.*?)$", action)[0]
                return True
            except:
                print("Failed to parse action {}".format(action))
        return False

    def _execute_action(self):
        from resources.lib.modules.globals import g

        g.init_globals(["", 0, self.next_action])
        from resources.lib.modules import router

        router.dispatch(g.REQUEST_PARAMS)

    def get_items_dictionary(self):
        """

        :return:
        :rtype:
        """
        result = json.loads(json.dumps(self.items, cls=JsonEncoder))
        self.items = []
        return result


class SerenStubs:
    @staticmethod
    def create_stubs():
        """Returns the methods used in the new kodistubs monkey patcher

        :return:Dictionary with the stub mapping
        :rtype:dict
        """
        return {
            "xbmc": {
                "getInfoLabel": SerenStubs.xbmc.getInfoLabel,
                "translatePath": SerenStubs.xbmc.translatePath,
                "log": SerenStubs.xbmc.log,
                "getSupportedMedia": SerenStubs.xbmc.getSupportedMedia,
                "getLanguage": SerenStubs.xbmc.getLanguage,
                "getCondVisibility": SerenStubs.xbmc.getCondVisibility,
                "executebuiltin": SerenStubs.xbmc.executebuiltin,
                "PlayList": SerenStubs.xbmc.PlayList,
                "Monitor": SerenStubs.xbmc.Monitor,
                "validatePath": lambda t: t,
                "sleep": lambda t: time.sleep(t / 1000),
            },
            "xbmcaddon": {"Addon": SerenStubs.xbmcaddon.Addon},
            "xbmcgui": {
                "ListItem": SerenStubs.xbmcgui.ListItem,
                "Window": SerenStubs.xbmcgui.Window,
                "Dialog": SerenStubs.xbmcgui.Dialog,
                "DialogBusy": SerenStubs.xbmcgui.DialogBusy,
                "DialogProgress": SerenStubs.xbmcgui.DialogProgress,
                "DialogProgressBG": SerenStubs.xbmcgui.DialogProgressBG,
            },
            "xbmcplugin": {
                "addDirectoryItem": SerenStubs.xbmcplugin.addDirectoryItem,
                "addDirectoryItems": SerenStubs.xbmcplugin.addDirectoryItems,
                "endOfDirectory": SerenStubs.xbmcplugin.endOfDirectory,
                "addSortMethod": SerenStubs.xbmcplugin.addSortMethod,
                "setContent": SerenStubs.xbmcplugin.setContent,
            },
            "xbmcvfs": {
                "File": SerenStubs.xbmcvfs.open,
                "exists": os.path.exists,
                "mkdir": os.mkdir,
                "mkdirs": os.makedirs,
                "rmdir": shutil.rmtree,
                "validatePath": lambda t: t,
            },
        }

    class xbmc:
        """Placeholder for the xbmc stubs"""

        @staticmethod
        def translatePath(path):
            """Returns the translated path"""
            valid_dirs = [
                "xbmc",
                "home",
                "temp",
                "masterprofile",
                "profile",
                "subtitles",
                "userdata",
                "database",
                "thumbnails",
                "recordings",
                "screenshots",
                "musicplaylists",
                "videoplaylists",
                "cdrips",
                "skin",
            ]

            if not path.startswith("special://"):
                return path
            parts = path.split("/")[2:]
            assert len(parts) > 1, "Need at least a single root directory"

            name = parts[0]
            assert name in valid_dirs, "{} is not a valid root dir.".format(name)

            parts.pop(0)  # remove name property

            dir_master = os.path.join(MOCK.PROFILE_ROOT, "userdata")

            tools.makedirs(dir_master, exist_ok=True)

            if name == "xbmc":
                return os.path.join(MOCK.XBMC_ROOT, *parts)
            elif name in ("home", "logpath"):
                if not MOCK.RUN_AGAINST_INSTALLATION and all(
                        x in parts for x in ["addons", "plugin.video.seren"]
                ):
                    return MOCK.PROFILE_ROOT
                return os.path.join(MOCK.PROFILE_ROOT, *parts)
            elif name in ("masterprofile", "profile"):
                return os.path.join(dir_master, *parts)
            elif name == "database":
                return os.path.join(dir_master, "Database", *parts)
            elif name == "thumbnails":
                return os.path.join(dir_master, "Thumbnails", *parts)
            elif name == "musicplaylists":
                return os.path.join(dir_master, "playlists", "music", *parts)
            elif name == "videoplaylists":
                return os.path.join(dir_master, "playlists", "video", *parts)
            else:
                import tempfile

                tempdir = os.path.join(tempfile.gettempdir(), "XBMC", name)
                tools.makedirs(tempdir, exist_ok=True)
                return os.path.join(tempdir, *parts)

        @staticmethod
        def getInfoLabel(value):
            """Returns information about infolabels

            :param value:
            :type value:
            :return:
            :rtype:
            """
            if value == "System.BuildVersion":
                if PYTHON2:
                    return "18"
                if PYTHON3:
                    return "19"
            print("Couldn't find the infolabel")

        @staticmethod
        def getSupportedMedia(media):
            """Returns the supported file types for the specific media as a string"""
            if media == "video":
                return (
                    ".m4v|.3g2|.3gp|.nsv|.tp|.ts|.ty|.strm|.pls|.rm|.rmvb|.mpd|.m3u|.m3u8|.ifo|.mov|.qt|.divx|.xvid|.bivx|.vob|.nrg|.img|.iso|.pva|.wmv"
                    "|.asf|.asx|.ogm|.m2v|.avi|.bin|.dat|.mpg|.mpeg|.mp4|.mkv|.mk3d|.avc|.vp3|.svq3|.nuv|.viv|.dv|.fli|.flv|.rar|.001|.wpl|.zip|.vdr|.dvr"
                    "-ms|.xsp|.mts|.m2t|.m2ts|.evo|.ogv|.sdp|.avs|.rec|.url|.pxml|.vc1|.h264|.rcv|.rss|.mpls|.webm|.bdmv|.wtv|.pvr|.disc "
                )
            elif media == "music":
                return (
                    ".nsv|.m4a|.flac|.aac|.strm|.pls|.rm|.rma|.mpa|.wav|.wma|.ogg|.mp3|.mp2|.m3u|.gdm|.imf|.m15|.sfx|.uni|.ac3|.dts|.cue|.aif|.aiff|.wpl"
                    "|.ape|.mac|.mpc|.mp+|.mpp|.shn|.zip|.rar|.wv|.dsp|.xsp|.xwav|.waa|.wvs|.wam|.gcm|.idsp|.mpdsp|.mss|.spt|.rsd|.sap|.cmc|.cmr|.dmc|.mpt"
                    "|.mpd|.rmt|.tmc|.tm8|.tm2|.oga|.url|.pxml|.tta|.rss|.wtv|.mka|.tak|.opus|.dff|.dsf|.cdda "
                )
            elif media == "picture":
                return ".png|.jpg|.jpeg|.bmp|.gif|.ico|.tif|.tiff|.tga|.pcx|.cbz|.zip|.cbr|.rar|.rss|.webp|.jp2|.apng"
            return ""

        @staticmethod
        def log(msg, level=xbmc.LOGDEBUG):
            """Write a string to XBMC's log file and the debug window"""
            if PYTHON2:
                levels = [
                    "LOGDEBUG",
                    "LOGINFO",
                    "LOGNOTICE",
                    "LOGWARNING",
                    "LOGERROR",
                    "LOGSEVERE",
                    "LOGFATAL",
                    "LOGNONE",
                ]
            else:
                levels = [
                    "LOGDEBUG",
                    "LOGINFO",
                    "LOGWARNING",
                    "LOGERROR",
                    "LOGSEVERE",
                    "LOGFATAL",
                    "LOGNONE",
                ]
            value = "{} - {}".format(levels[level], msg)
            print(value)
            MOCK.LOG_HISTORY.append(value)

        @staticmethod
        def getCondVisibility(value):
            if value == "Window.IsMedia":
                return 0

        @staticmethod
        def getLanguage(format=xbmc.ENGLISH_NAME, region=False):
            """Returns the active language as a string."""
            result = SUPPORTED_LANGUAGES.get(MOCK.KODI_UI_LANGUAGE, ())[format]
            if region:
                return result
            else:
                return result.split("-")[0]

        @staticmethod
        def executebuiltin(function, wait=False):
            """Execute a built in Kodi function"""
            print("EXECUTE BUILTIN: {} wait:{}".format(function, wait))

        class PlayList(xbmc.PlayList):
            def __init__(self, playList):
                self.list = []

            def add(self, url, listitem=None, index=-1):
                self.list.append([url, listitem])

            def getposition(self):
                return 0

            def clear(self):
                self.list.clear()

            def size(self):
                return len(self.list)

        class Monitor:
            def __init__(self, *args, **kwargs):
                pass

            def abortRequested(self):
                return False

            def waitForAbort(self, timeout=0):
                return True

            def onSettingsChanged(self):
                pass

    class xbmcaddon:
        class Addon(xbmcaddon.Addon):
            def __init__(self, addon_id=None):
                self._id = addon_id
                self._config = {}
                self._strings = {}
                self._current_user_settings = {}

            def _load_addon_config(self):
                # Parse the addon config
                try:
                    filepath = os.path.join(MOCK.SEREN_ROOT, "addon.xml")
                    xml = ElementTree.parse(filepath)
                    self._config = xml.getroot()
                    self._id = self.getAddonInfo("id") or self._id
                except ElementTree.ParseError:
                    pass
                except IOError:
                    pass

            def _load_language_string(self):
                only_digits = re.compile(r"\D")

                langfile = self.get_po_location(
                    xbmc.getLanguage(
                        format=xbmc.ISO_639_1,
                        region=True)
                )
                if os.path.exists(langfile):
                    po = polib.pofile(langfile)
                else:
                    po = polib.pofile(self.get_po_location("en-gb"))
                self._strings = {
                    int(only_digits.sub("", entry.msgctxt)): entry.msgstr
                    if entry.msgstr is not None
                    else entry.msgid
                    for entry in po
                }

            def get_po_location(self, language):
                langfile = os.path.join(
                    MOCK.SEREN_ROOT,
                    "resources",
                    "language",
                    "resource.language.{}".format(language).replace("-", "_"),
                    "strings.po",
                )
                return langfile

            def _load_user_settings(self):
                current_settings_file = os.path.join(
                    os.path.join(
                        MOCK.PROFILE_ROOT,
                        "userdata",
                        "addon_data",
                        "plugin.video.seren",
                        "settings.xml",
                    )
                )
                if not os.path.exists(current_settings_file):
                    return
                xml = ElementTree.parse(current_settings_file)
                settings = xml.findall("./setting")
                for node in settings:
                    setting_id = node.get("id")
                    setting_value = node.text
                    item = {"id": setting_id}
                    if setting_value:
                        item["value"] = setting_value
                    self._current_user_settings.update({setting_id: item})

            def getAddonInfo(self, key):
                if not self._config:
                    self._load_addon_config()

                properties = [
                    "author",
                    "changelog",
                    "description",
                    "disclaimer",
                    "fanart",
                    "icon",
                    "id",
                    "name",
                    "path",
                    "profile",
                    "stars",
                    "summary",
                    "type",
                    "version",
                ]
                if key not in properties:
                    raise ValueError("{} is not a valid property.".format(key))
                if key == "profile":
                    return "special://profile/addon_data/{0}/".format(self._id)
                if key == "path":
                    return "special://home/addons/{0}".format(self._id)
                if self._config and key in self._config.attrib:
                    return self._config.attrib[key]
                return None

            def getLocalizedString(self, key):
                if not self._strings:
                    self._load_language_string()

                if key in self._strings:
                    return kodi_to_ansi(self._strings[key])
                print("Cannot find localized string {}".format(key))
                return None

            def getSetting(self, key):
                if not self._current_user_settings:
                    self._load_user_settings()
                if key in self._current_user_settings:
                    return self._current_user_settings[key].get("value")
                return None

            def setSetting(self, key, value):
                if not self._current_user_settings:
                    self._load_user_settings()
                self._current_user_settings.update({key: {"value": str(value)}})

    class xbmcplugin:
        @staticmethod
        def addDirectoryItem(handle, url, listitem, isFolder=False, totalItems=0):
            MOCK.DIRECTORY.items.append((url, listitem, isFolder))

        @staticmethod
        def addDirectoryItems(handle, items, totalItems=0):
            MOCK.DIRECTORY.items.extend(items)

        @staticmethod
        def endOfDirectory(
                handle, succeeded=True, updateListing=False, cacheToDisc=True
        ):
            MOCK.DIRECTORY.handle_directory()

        @staticmethod
        def setContent(handle, content):
            MOCK.DIRECTORY.content = content

        @staticmethod
        def addSortMethod(handle, sortMethod, label2Mask=""):
            MOCK.DIRECTORY.sort_method = sortMethod

    class xbmcgui:
        class ListItem(xbmcgui.ListItem):
            def __init__(
                    self,
                    label="",
                    label2="",
                    iconImage="",
                    thumbnailImage="",
                    path="",
                    offscreen=False,
            ):
                self.contentLookup = None
                self._label = label
                self._label2 = label2
                self._icon = iconImage
                self._thumb = thumbnailImage
                self._path = path
                self._offscreen = offscreen
                self._props = {}
                self._selected = False
                self.cm = []
                self.vitags = {}
                self.art = {}
                self.info = {}
                self.info_type = ""
                self.uniqueIDs = {}
                self.ratings = {}
                self.contentLookup = True
                self.stream_info = {}

            def addContextMenuItems(self, items, replaceItems=False):
                [self.cm.append(i) for i in items]

            def getLabel(self):
                return self._label

            def getLabel2(self):
                return self._label2

            def getProperty(self, key):
                key = key.lower()
                if key in self._props:
                    return self._props[key]
                return ""

            def isSelected(self):
                return self._selected

            def select(self, selected):
                self._selected = selected

            def setArt(self, values):
                if not values:
                    return
                self.art.update(values)

            def setIconImage(self, value):
                self._icon = value

            def setInfo(self, type, infoLabels):
                if type:
                    self.info_type = type
                if isinstance(infoLabels, dict):
                    self.info.update(infoLabels)

            def setLabel(self, label):
                self._label = label

            def setLabel2(self, label):
                self._label2 = label

            def setProperty(self, key, value):
                key = key.lower()
                self._props[key] = value

            def setThumbnailImage(self, value):
                self._thumb = value

            def setCast(self, actors):
                """Set cast including thumbnails. Added in v17.0"""
                pass

            def setUniqueIDs(self, ids, **kwargs):
                self.uniqueIDs.update(ids)

            def setRating(self, rating_type, rating, votes=0, default=False):
                self.ratings.update({rating_type: [rating, votes, default]})

            def setContentLookup(self, enable):
                self.contentLookup = enable

            def addStreamInfo(self, cType, dictionary):
                self.stream_info.update({cType: dictionary})

            def getPath(self):
                return self._path

            def __str__(self):
                return self._label

        class Window(xbmcgui.Window):
            def __init__(self, windowId=0):
                self._props = {}

            def clearProperties(self):
                self._props.clear()

            def clearProperty(self, key):
                key = key.lower()
                if key in self._props:
                    del self._props[key]

            def getProperty(self, key):
                key = key.lower()
                if key in self._props:
                    return self._props[key]
                return None

            def setProperty(self, key, value):
                key = key.lower()
                self._props[key] = value

        class Dialog(xbmcgui.Dialog):
            def notification(
                    self,
                    heading,
                    message,
                    icon=xbmcgui.NOTIFICATION_INFO,
                    time=5000,
                    sound=True,
            ):
                if icon == xbmcgui.NOTIFICATION_WARNING:
                    prefix = "[WARNING]"
                elif icon == xbmcgui.NOTIFICATION_ERROR:
                    prefix = "[ERROR]"
                else:
                    prefix = "[INFO]"
                print("NOTIFICATION: {0} {1}: {2}".format(prefix, heading, message))

            def ok(self, heading, message):
                print("{}: \n{}".format(heading, message))
                return True

            def select(
                    self, heading, list, autoclose=False, preselect=None, useDetails=False
            ):
                print(heading)
                action = None
                for idx, i in enumerate(list):
                    print("{}) {}".format(idx, i))
                while True:
                    try:
                        action = int(get_input())
                    except:
                        break
                if action is None:
                    raise Exception
                print(action)
                return action

            def textviewer(self, heading, text, usemono=False):
                print(heading)
                print(text)

            def yesno(
                    self,
                    heading,
                    message,
                    nolabel="",
                    yeslabel="",
                    customlabel="",
                    autoclose=0,
            ):
                if not MOCK.INTERACTIVE_MODE:
                    return 1
                print("")
                print("{}\n{}".format(heading, message))
                print("1) {}/ 0) {}".format(yeslabel, nolabel))
                action = get_input()
                return action

        class DialogBusy:
            """Show/Hide the progress indicator. Added in v17.0"""

            def create(self):
                print("[BUSY] show")

            def update(self, percent):
                print("[BUSY] update: {0}".format(percent))

            def close(self):
                print("[BUSY] close")

            def iscanceled(self):
                return False

        class DialogProgress(xbmcgui.DialogProgress):
            canceled = False

            def __init__(self):
                self._created = False
                self._heading = None
                self._message = None
                self._percent = -1

            def update(self, percent, message=""):
                if percent:
                    self._percent = percent
                if message:
                    self._message = message
                print(
                    "[PROGRESS] {0}: {1} - {2}%".format(
                        self._heading, self._message, self._percent
                    )
                )

            def create(self, heading, message=""):
                self._created = True
                self._heading = heading
                self._message = message
                self._percent = 0
                print(
                    "[PROGRESS] {0}: {1} - {2}%".format(
                        self._heading, self._message, self._percent
                    )
                )

            def iscanceled(self):
                return self.canceled

            def close(self):
                print("[PROGRESS] closing")

        class DialogProgressBG(xbmcgui.DialogProgressBG):
            def __init__(self):
                self._created = False
                self._heading = ""
                self._message = ""
                self._percent = 0

            def create(self, heading, message=""):
                self._created = True
                self._heading = heading
                self._message = message
                self._percent = 0
                print(
                    "[BACKGROUND] {0}: {1} - {2}%".format(
                        self._heading, self._message, self._percent
                    )
                )

            def close(self):
                self._created = False
                print("[BACKGROUND] closing")

            def update(self, percent=0, heading="", message=""):
                self._percent = percent
                if heading:
                    self._heading = heading
                if message:
                    self._message = message
                print(
                    "[BACKGROUND] {0}: {1} - {2}%".format(
                        self._heading, self._message, self._percent
                    )
                )

            def isFinished(self):
                return not self._created

    class xbmcvfs:
        @staticmethod
        def open(filepath, mode="r"):
            if sys.version_info.major == 3:
                return open(filepath, mode, encoding="utf-8")
            else:
                return open(filepath, mode)


class MonkeyPatchKodiStub:
    """Helper class for Monkey patching kodistubs to add functionality."""

    def __init__(self):
        self._dict = SerenStubs.create_stubs()

    def trace_log(self):
        self._walk_kodi_dependencies(self._trace_log_decorator)

    def monkey_patch(self):
        self._walk_kodi_dependencies(self._monkey_patch)

    def _walk_kodi_dependencies(self, func):
        [
            self._walk_item(i, func)
            for i in [xbmc, xbmcgui, xbmcaddon, xbmcdrm, xbmcplugin, xbmcvfs]
        ]

    def _walk_item(self, item, func, path=None):
        if path is None:
            path = []
        path.append(item.__name__)
        for k, v in vars(item).items():
            if isinstance(v, (types.FunctionType, staticmethod)):
                result = func(path, v)
                if result:
                    setattr(item, k, result)
            if type(v) is type:
                result = func(path, v)
                if result:
                    setattr(item, k, result)
                else:
                    self._walk_item(v, func, path)
        path.pop(-1)

    @staticmethod
    def _trace_log_decorator(path, func):
        """Add trace logging to the function it decorates.

        :param func: Function to decorate
        :type func: types.FunctionType
        :return: Wrapped function
        :rtype: types.FunctionType
        """
        joined_path = ".".join(path)

        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            try:
                if args:
                    print(
                        "Entering: {}.{} with parameters {}".format(
                            joined_path, func.__name__, args
                        )
                    )
                else:
                    print("Entering: {}.{}".format(joined_path, func.__name__))
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(
                        "Exception in {}.{} : {}".format(joined_path, func.__name__, e)
                    )
                    raise e
            finally:
                print("Exiting: {}.{}".format(joined_path, func.__name__))

        return _wrapped

    @staticmethod
    def _decorate(func, patch):
        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            return patch(func(*args, **kwargs))

        return _wrapped

    def _monkey_patch(self, path, item):
        patch = None
        for p in path:
            if patch:
                patch = patch.get(p, {})
            else:
                patch = self._dict.get(p, {})
        patch = patch.get(item.__name__)
        if patch:
            return patch
        elif isinstance(item, types.FunctionType):
            return self._log_not_patched_method(path, item)

    @staticmethod
    def _log_not_patched_method(path, func):
        """Add logging to the function that indicates that there is not mockey patch available.

        :param path: path of the calling method
        :type path: list[string]
        :param func: Function to decorate
        :type func: types.FunctionType
        :return: Wrapped function
        :rtype: types.FunctionType
        """
        joined_path = ".".join(path)

        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            object_type = "method" if isinstance(func, types.FunctionType) else "object"
            print(
                "Call to not patched {}: {}.{}".format(
                    object_type, joined_path, func.__name__
                )
            )
            return func(*args, **kwargs)

        return _wrapped


class MockKodi:
    """KODIStub mock helper"""

    def __init__(self):
        self.XBMC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        self.PROFILE_ROOT = os.path.abspath(os.path.join(self.XBMC_ROOT, "../"))
        self.SEREN_ROOT = self.PROFILE_ROOT
        self.KODI_UI_LANGUAGE = os.environ.get("KODI_UI_LANGUAGE", "en-gb")
        self.INTERACTIVE_MODE = (
                os.environ.get("SEREN_INTERACTIVE_MODE", False) == "True"
        )
        self.RUN_AGAINST_INSTALLATION = (
                os.environ.get("SEREN_RUN_AGAINST_INSTALLATION", False) == "True"
        )
        if self.RUN_AGAINST_INSTALLATION and os.path.exists(
                self.get_kodi_installation()
        ):
            self.PROFILE_ROOT = self.get_kodi_installation()
            self.SEREN_ROOT = os.path.join(
                self.PROFILE_ROOT, "addons", "plugin.video.seren"
            )

        self.DIRECTORY = Directory()
        self.LOG_HISTORY = []
        self._monkey_patcher = MonkeyPatchKodiStub()
        # self._monkey_patcher.trace_log()
        self._monkey_patcher.monkey_patch()

    @staticmethod
    def get_kodi_installation():
        """

        :return:
        :rtype:
        """
        dir_home = os.path.expanduser("~")
        if sys.platform == "win32":
            return os.path.join(dir_home, "AppData", "Roaming", "Kodi")
        return os.path.join(dir_home, ".kodi")


MOCK = MockKodi()


class JsonEncoder(json.JSONEncoder):
    """Json encoder for serialising all objects"""

    def default(self, o):
        """

        :param o:
        :type o:
        :return:
        :rtype:
        """
        return o.__dict__


def kodi_to_ansi(string):
    """

    :param string:
    :type string:
    :return:
    :rtype:
    """
    if string is None:
        return None
    string = string.replace("[B]", "\033[1m")
    string = string.replace("[/B]", "\033[21m")
    string = string.replace("[I]", "\033[3m")
    string = string.replace("[/I]", "\033[23m")
    string = string.replace("[COLOR gray]", "\033[30;1m")
    string = string.replace("[COLOR red]", "\033[31m")
    string = string.replace("[COLOR green]", "\033[32m")
    string = string.replace("[COLOR yellow]", "\033[33m")
    string = string.replace("[COLOR blue]", "\033[34m")
    string = string.replace("[COLOR purple]", "\033[35m")
    string = string.replace("[COLOR cyan]", "\033[36m")
    string = string.replace("[COLOR white]", "\033[37m")
    string = string.replace("[/COLOR]", "\033[39;0m")
    return string


class MockKodiUILanguage(object):
    def __init__(self, new_language):
        self.new_language = new_language
        self.original_language = MOCK.KODI_UI_LANGUAGE

    def __enter__(self):
        MOCK.KODI_UI_LANGUAGE = self.new_language
        return self.new_language

    def __exit__(self, exc_type, exc_val, exc_tb):
        MOCK.KODI_UI_LANGUAGE = self.original_language
