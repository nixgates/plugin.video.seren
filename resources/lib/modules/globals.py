# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

# Import Thread lock workaround
# noinspection PyUnresolvedReferences
import _strptime
import json
import os
import sys
import time
import traceback
import unicodedata

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.common import tools
from resources.lib.third_party.cached_property import cached_property

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

viewTypes = [
    ("Default", 50),
    ("Poster", 51),
    ("Icon Wall", 52),
    ("Shift", 53),
    ("Info Wall", 54),
    ("Wide List", 55),
    ("Wall", 500),
    ("Banner", 501),
    ("Fanart", 502),
]

colorChart = [
    "black",
    "white",
    "whitesmoke",
    "gainsboro",
    "lightgray",
    "silver",
    "darkgray",
    "gray",
    "dimgray",
    "snow",
    "floralwhite",
    "ivory",
    "beige",
    "cornsilk",
    "antiquewhite",
    "bisque",
    "blanchedalmond",
    "burlywood",
    "darkgoldenrod",
    "ghostwhite",
    "azure",
    "aliveblue",
    "lightsaltegray",
    "lightsteelblue",
    "powderblue",
    "lightblue",
    "skyblue",
    "lightskyblue",
    "deepskyblue",
    "dodgerblue",
    "royalblue",
    "blue",
    "mediumblue",
    "midnightblue",
    "navy",
    "darkblue",
    "cornflowerblue",
    "slateblue",
    "slategray",
    "yellowgreen",
    "springgreen",
    "seagreen",
    "steelblue",
    "teal",
    "fuchsia",
    "deeppink",
    "darkmagenta",
    "blueviolet",
    "darkviolet",
    "darkorchid",
    "darkslateblue",
    "darkslategray",
    "indigo",
    "cadetblue",
    "darkcyan",
    "darkturquoise",
    "turquoise",
    "cyan",
    "paleturquoise",
    "lightcyan",
    "mintcream",
    "honeydew",
    "aqua",
    "aquamarine",
    "chartreuse",
    "greenyellow",
    "palegreen",
    "lawngreen",
    "lightgreen",
    "lime",
    "mediumspringgreen",
    "mediumturquoise",
    "lightseagreen",
    "mediumaquamarine",
    "mediumseagreen",
    "limegreen",
    "darkseagreen",
    "forestgreen",
    "green",
    "darkgreen",
    "darkolivegreen",
    "olive",
    "olivedab",
    "darkkhaki",
    "khaki",
    "gold",
    "goldenrod",
    "lightyellow",
    "lightgoldenrodyellow",
    "lemonchiffon",
    "yellow",
    "seashell",
    "lavenderblush",
    "lavender",
    "lightcoral",
    "indianred",
    "darksalmon",
    "lightsalmon",
    "pink",
    "lightpink",
    "hotpink",
    "magenta",
    "plum",
    "violet",
    "orchid",
    "palevioletred",
    "mediumvioletred",
    "purple",
    "marron",
    "mediumorchid",
    "mediumpurple",
    "mediumslateblue",
    "thistle",
    "linen",
    "mistyrose",
    "palegoldenrod",
    "oldlace",
    "papayawhip",
    "moccasin",
    "navajowhite",
    "peachpuff",
    "sandybrown",
    "peru",
    "chocolate",
    "orange",
    "darkorange",
    "tomato",
    "orangered",
    "red",
    "crimson",
    "salmon",
    "coral",
    "firebrick",
    "brown",
    "darkred",
    "tan",
    "rosybrown",
    "sienna",
    "saddlebrown",
]

info_labels = [
    "genre",
    "country",
    "year",
    "episode",
    "season",
    "sortepisode",
    "sortseason",
    "episodeguide",
    "showlink",
    "top250",
    "setid",
    "tracknumber",
    "rating",
    "userrating",
    "watched",
    "playcount",
    "overlay",
    "castandrole",
    "director",
    "mpaa",
    "plot",
    "plotoutline",
    "title",
    "originaltitle",
    "sorttitle",
    "duration",
    "studio",
    "tagline",
    "writer",
    "tvshowtitle",
    "premiered",
    "status",
    "set",
    "setoverview",
    "tag",
    "imdbnumber",
    "code",
    "aired",
    "credits",
    "lastplayed",
    "album",
    "artist",
    "votes",
    "path",
    "trailer",
    "dateadded",
    "mediatype",
    "dbid",
]

listitem_properties = [
    ("awards", "Awards"),
    ("oscar_wins", "Oscar_Wins"),
    ("oscar_nominations", "Oscar_Nominations"),
    ("award_wins", "Award_Wins"),
    ("award_nominations", "Award_Nominations"),
    ("metacritic_rating", "Metacritic_Rating"),
    (("rating.tmdb", "rating"), "TMDb_Rating"),
    (("rating.tmdb", "votes"), "TMDb_Votes"),
    (("rating.tvdb", "rating"), "Tvdb_Rating"),
    (("rating.tvdb", "votes"), "Tvdb_Votes"),
    (("rating.imdb", "rating"), "IMDb_Rating"),
    (("rating.imdb", "votes"), "IMDb_Votes"),
    (("rating.trakt", "rating"), "Trakt_Rating"),
    (("rating.trakt", "votes"), "Trakt_Votes"),
    ("rottentomatoes_rating", "RottenTomatoes_Rating"),
    ("rottentomatoes_image", "RottenTomatoes_Image"),
    ("rottentomatoes_reviewstotal", "RottenTomatoes_ReviewsTotal"),
    ("rottentomatoes_reviewsfresh", "RottenTomatoes_ReviewsFresh"),
    ("rottentomatoes_reviewsrotten", "RottenTomatoes_ReviewsRotten"),
    ("rottentomatoes_consensus", "RottenTomatoes_Consensus"),
    ("rottentomatoes_usermeter", "RottenTomatoes_UserMeter"),
    ("rottentomatoes_userreviews", "RottenTomatoes_UserReviews"),
]


class GlobalVariables(object):
    CONTENT_FOLDER = "files"
    CONTENT_MOVIE = "movies"
    CONTENT_SHOW = "tvshows"
    CONTENT_SEASON = "seasons"
    CONTENT_EPISODE = "episodes"
    CONTENT_GENRES = "genres"
    CONTENT_YEARS = "years"

    PYTHON3 = True if sys.version_info.major == 3 else False

    def __init__(self):
        self.IS_ADDON_FIRSTRUN = None
        self.ADDON = None
        self.ADDON_DATA_PATH = None
        self.ADDON_ID = None
        self.ADDON_NAME = None
        self.VERSION = None
        self.DEFAULT_FANART = None
        self.DEFAULT_ICON = None
        self.ADDON = xbmcaddon.Addon()
        self.ADDON_ID = self.ADDON.getAddonInfo("id")
        self.ADDON_NAME = self.ADDON.getAddonInfo("name")
        self.ADDON_USERDATA_PATH = None
        self.SETTINGS_CACHE = {}
        self.LANGUAGE_CACHE = {}
        self.PLAYLIST = None
        self.HOME_WINDOW = None
        self.KODI_VERSION = None
        self.PLATFORM = self._get_system_platform()

    def init_globals(self, argv=None, addon_id=None):
        self.IS_ADDON_FIRSTRUN = self.IS_ADDON_FIRSTRUN is None
        self.SETTINGS_CACHE = {}
        self.LANGUAGE_CACHE = {}
        self.ADDON = xbmcaddon.Addon()
        self.ADDON_ID = addon_id if addon_id else self.ADDON.getAddonInfo("id")
        self.ADDON_NAME = self.ADDON.getAddonInfo("name")
        self.VERSION = self.ADDON.getAddonInfo("version")
        self.DEFAULT_FANART = self.ADDON.getAddonInfo("fanart")
        self.DEFAULT_ICON = self.ADDON.getAddonInfo("icon")
        self._init_kodi()
        self._init_paths()
        self.init_request(argv)
        self._init_cache()

    def _init_kodi(self):
        self.PLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.HOME_WINDOW = xbmcgui.Window(10000)
        self.KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion")[:2])

    @staticmethod
    def _get_system_platform():
        """
        get platform on which xbmc run
        """
        platform = "unknown"
        if xbmc.getCondVisibility("system.platform.linux"):
            platform = "linux"
        elif xbmc.getCondVisibility("system.platform.xbox"):
            platform = "xbox"
        elif xbmc.getCondVisibility("system.platform.windows"):
            if "Users\\UserMgr" in os.environ.get("TMP"):
                platform = "xbox"
            else:
                platform = "windows"
        elif xbmc.getCondVisibility("system.platform.osx"):
            platform = "osx"

        return platform

    def _init_cache(self):
        from resources.lib.database.cache import Cache

        self.CACHE = Cache()

    # region global settings
    @staticmethod
    def _global_setting_key(setting_id):
        return "seren.setting.{}".format(setting_id)

    def get_global_setting(self, setting_id):
        try:
            return eval(
                self.HOME_WINDOW.getProperty(self._global_setting_key(setting_id))
            )
        except:
            return None

    def set_global_setting(self, setting_id, value):
        return self.HOME_WINDOW.setProperty(
            self._global_setting_key(setting_id), repr(value)
        )

    def add_dictionary_to_window(self, key_prepend, dictionary):
        for k, v in list(dictionary.items()):
            key = "{}.{}".format(key_prepend, str(k))
            if isinstance(v, dict):
                self.add_dictionary_to_window(key, v)
            else:
                self.HOME_WINDOW.setProperty(key, repr(v))

    def remove_dictionary_from_window(self, key_prepend, dictionary):
        for k, v in list(dictionary.items()):
            key = "{}_{}".format(key_prepend, str(k))
            if isinstance(v, dict):
                self.remove_dictionary_from_window(key, v)
            else:
                self.HOME_WINDOW.clearProperty(key)

    # endregion

    def init_request(self, argv):
        if argv is None:
            return

        self.URL = tools.urlparse(argv[0])
        try:
            self.PLUGIN_HANDLE = int(argv[1])
            self.IS_SERVICE = False
        except IndexError:
            self.PLUGIN_HANDLE = 0
            self.IS_SERVICE = True

        if self.URL[1] != "":
            self.BASE_URL = "{scheme}://{netloc}".format(
                scheme=self.URL[0], netloc=self.URL[1]
            )
        else:
            self.BASE_URL = ""
        self.PATH = self.decode_py2(tools.unquote(self.URL[2]))
        try:
            self.PARAM_STRING = argv[2].lstrip('?/')
        except IndexError:
            self.PARAM_STRING = ""
        self.REQUEST_PARAMS = self.legacy_params_converter(
            dict(tools.parse_qsl(self.PARAM_STRING))
        )
        if "action_args" in self.REQUEST_PARAMS:
            try:
                self.REQUEST_PARAMS["action_args"] = tools.deconstruct_action_args(
                    self.REQUEST_PARAMS["action_args"]
                )
            except:
                pass
            if isinstance(self.REQUEST_PARAMS["action_args"], dict):
                self.REQUEST_PARAMS["action_args"] = self.legacy_action_args_converter(
                    self.REQUEST_PARAMS["action_args"]
                )
        self.FROM_WIDGET = self.REQUEST_PARAMS.get("from_widget", "true") == "true"
        self.PAGE = int(g.REQUEST_PARAMS.get("page", 1))

    @staticmethod
    def legacy_action_args_converter(action_args):
        if "item_type" in action_args:
            if "season" in action_args["item_type"]:
                from resources.lib.database.trakt_sync import shows

                action_args.update(
                    shows.TraktSyncDatabase().get_season_action_args(
                        action_args["trakt_id"], action_args["season"]
                    )
                )
            if "episode" in action_args["item_type"]:
                from resources.lib.database.trakt_sync import shows

                action_args.update(
                    shows.TraktSyncDatabase().get_episode_action_args(
                        action_args["trakt_id"],
                        action_args["season"],
                        action_args["episode"],
                    )
                )
            action_args["mediatype"] = action_args.pop("item_type")
        return action_args

    @staticmethod
    def legacy_params_converter(params):
        if "actionArgs" in params:
            params["action_args"] = params.pop("actionArgs")
        if "action" in params:
            if "moviesTrending" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "trending"
                params["mediatype"] = "movies"
            if "moviesPopular" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "popular"
                params["mediatype"] = "movies"
            if "moviesWatched" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "watched"
                params["mediatype"] = "movies"
            if "moviesCollected" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "collected"
                params["mediatype"] = "movies"
            if "moviesAnticipated" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "anticipated"
                params["mediatype"] = "movies"
            if "moviesBoxOffice" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "boxoffice"
                params["mediatype"] = "movies"
            if "showsTrending" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "trending"
                params["mediatype"] = "shows"
            if "showsPopular" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "popular"
                params["mediatype"] = "shows"
            if "showsWatched" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "watched"
                params["mediatype"] = "shows"
            if "showsCollected" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "collected"
                params["mediatype"] = "shows"
            if "showsAnticipated" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "anticipated"
                params["mediatype"] = "shows"
            if "showsBoxOffice" == params["action"]:
                params["action"] = "genericEndpoint"
                params["endpoint"] = "boxoffice"
                params["mediatype"] = "shows"
        return params

    def _init_paths(self):
        self.ADDONS_PATH = self.decode_py2(
            tools.translate_path(os.path.join("special://home/", "addons/"))
        )
        self.ADDON_PATH = self.decode_py2(
            tools.translate_path(
                os.path.join(
                    "special://home/", "addons/{}".format(self.ADDON_ID.lower())
                )
            )
        )
        self.ADDON_DATA_PATH = self.decode_py2(
            tools.translate_path(self.ADDON.getAddonInfo("path"))
        )  # Addon folder
        self.ADDON_USERDATA_PATH = self.decode_py2(
            tools.translate_path(
                "special://profile/addon_data/{}/".format(self.ADDON_ID)
            )
        )  # Addon user data folder
        self.SETTINGS_PATH = self.decode_py2(
            tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "settings.xml"))
        )
        self.ADVANCED_SETTINGS_PATH = self.decode_py2(
            tools.translate_path("special://home/userdata/advancedsettings.xml")
        )
        self.GUI_PATH = self.decode_py2(
            tools.translate_path(
                os.path.join(self.ADDON_DATA_PATH, "resources", "lib", "gui")
            )
        )
        self.IMAGES_PATH = self.decode_py2(
            tools.translate_path(
                os.path.join(self.ADDON_DATA_PATH, "resources", "images")
            )
        )
        self.SKINS_PATH = self.decode_py2(
            tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "skins"))
        )
        self.CACHE_DB_PATH = self.decode_py2(
            tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "cache.db"))
        )
        self.TORRENT_CACHE = self.decode_py2(
            tools.translate_path(
                os.path.join(self.ADDON_USERDATA_PATH, "torrentCache.db")
            )
        )
        self.TORRENT_ASSIST = self.decode_py2(
            tools.translate_path(
                os.path.join(self.ADDON_USERDATA_PATH, "torentAssist.db")
            )
        )
        self.PROVIDER_CACHE_DB_PATH = self.decode_py2(
            tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "providers.db"))
        )
        self.PREMIUMIZE_DB_PATH = self.decode_py2(
            tools.translate_path(
                os.path.join(self.ADDON_USERDATA_PATH, "premiumize.db")
            )
        )
        self.TRAKT_SYNC_DB_PATH = self.decode_py2(
            tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "traktSync.db"))
        )
        self.SEARCH_HISTORY_DB_PATH = self.decode_py2(
            tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "search.db"))
        )
        self.SKINS_DB_PATH = self.decode_py2(
            tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "skins.db"))
        )
        self._confirm_and_init_download_path()

    def _confirm_and_init_download_path(self):
        self.DOWNLOAD_PATH = self.get_setting("download.location")
        if self.DOWNLOAD_PATH == "userdata" or self.DOWNLOAD_PATH is None:
            self.DOWNLOAD_PATH = tools.ensure_path_is_dir(
                os.path.join(g.ADDON_USERDATA_PATH, "Downloads")
            )
        if not xbmcvfs.exists(self.DOWNLOAD_PATH):
            xbmcvfs.mkdirs(self.DOWNLOAD_PATH)

    def get_video_database_path(self):
        database_path = os.path.abspath(
            os.path.join(self.ADDON_DATA_PATH, "..", "..", "Database",)
        )
        if self.KODI_VERSION == 17:
            database_path = os.path.join(database_path, "MyVideos107.db")
        elif self.KODI_VERSION >= 18:
            database_path = os.path.join(database_path, "MyVideos116.db")

        return database_path

    def decode_py2(self, value):
        if not self.PYTHON3 and isinstance(value, tools.basestring):
            return self.encode_py2(value).decode("utf-8")
        return value

    def encode_py2(self, value):
        if not value:
            return value
        if not self.PYTHON3 and isinstance(value, tools.unicode):
            return value.encode("utf-8")
        return value

    # region KODI setting
    def set_setting(self, setting_id, value):
        self.SETTINGS_CACHE.update({setting_id: value})
        return self.ADDON.setSetting(setting_id, value)

    def get_setting(self, setting_id, default_value=None):
        value = self.SETTINGS_CACHE.get(setting_id, self.ADDON.getSetting(setting_id))
        if value is None or value == "" and default_value:
            return default_value
        else:
            self.SETTINGS_CACHE.update({setting_id: value})
            return value

    def get_float_setting(self, setting_id, default_value=None):
        try:
            return float(self.get_setting(setting_id, default_value))
        except:
            if default_value is not None:
                return default_value
            else:
                return 0

    def get_int_setting(self, setting_id, default_value=None):
        try:
            return int(self.get_setting(setting_id, default_value))
        except:
            if default_value is not None:
                return default_value
            else:
                return 0

    def get_bool_setting(self, setting_id, default_value=None):
        try:
            return self.get_setting(setting_id, default_value) == "true"
        except:
            if default_value is not None:
                return default_value
            else:
                return False

    # endregion

    def get_language_string(self, language_id):
        text = self.LANGUAGE_CACHE.get(
            language_id, self.ADDON.getLocalizedString(language_id)
        )
        self.LANGUAGE_CACHE.update({language_id: text})
        return self.decode_py2(text)

    def get_view_type(self, content_type):
        view_type = 0

        if not self.get_bool_setting("general.viewidswitch"):
            if content_type == self.CONTENT_FOLDER:
                view_type = self.get_setting("addon.view")
            if content_type == self.CONTENT_SHOW:
                view_type = self.get_setting("show.view")
            if content_type == self.CONTENT_MOVIE:
                view_type = self.get_setting("movie.view")
            if content_type == self.CONTENT_EPISODE:
                view_type = self.get_setting("episode.view")
            if content_type == self.CONTENT_SEASON:
                view_type = self.get_setting("season.view")
            if view_type > 0:
                view_name, view_type = viewTypes[int(view_type)]
                return view_type
        else:
            if content_type == self.CONTENT_FOLDER:
                view_type = self.get_setting("addon.view.id")
            if content_type == self.CONTENT_SHOW:
                view_type = self.get_setting("show.view.id")
            if content_type == self.CONTENT_MOVIE:
                view_type = self.get_setting("movie.view.id")
            if content_type == self.CONTENT_EPISODE:
                view_type = self.get_setting("episode.view.id")
            if content_type == self.CONTENT_SEASON:
                view_type = self.get_setting("season.view.id")
            if view_type > 0:
                view_type = int(view_type)
                return view_type

        return view_type

    def log(self, msg, level="info"):
        msg = g.encode_py2(g.decode_py2(msg))
        msg = "{}: {}".format(self.ADDON_NAME.upper(), msg)
        if level == "error":
            xbmc.log(msg, level=xbmc.LOGERROR)
        elif level == "info":
            xbmc.log(msg, level=xbmc.LOGINFO)
        elif level == "notice":
            if self.KODI_VERSION >= 19:
                xbmc.log(msg, level=xbmc.LOGINFO)
            else:
                xbmc.log(msg, level=xbmc.LOGNOTICE)# pylint: disable=no-member
        elif level == "warning":
            xbmc.log(msg, level=xbmc.LOGWARNING)
        else:
            xbmc.log(msg)

    def log_stacktrace(self):
        """Gets the latest traceback stacktrace and logs it."""
        self.log(traceback.format_exc(), "error")

    def color_picker(self):
        """Method that generates color list and handles the popup."""
        select_list = [self.color_string("inherit")]
        for i in colorChart:
            select_list.append(self.color_string(i, i))
        color = xbmcgui.Dialog().select(
            "{}: {}".format(self.ADDON_NAME, self.get_language_string(30017)), select_list
        )
        if color == -1: 
            return
        if color == 0:
            self.set_setting("general.textColor", "inherit")
            self.set_setting("general.displayColor", "inherit")
        else:
            color -= 1
            self.set_setting("general.textColor", colorChart[color])
            self.set_setting("general.displayColor", colorChart[color])
        xbmc.executebuiltin("Addon.OpenSettings({})".format(self.ADDON_ID))

    @staticmethod
    def _try_get_color_from_skin():
        skin_dir = xbmc.getSkinDir()
        skin_color = None
        if not skin_dir:
            return None
        skin_theme = xbmc.getInfoLabel("Skin.CurrentTheme")
        if not skin_theme:
            return None
        skin_theme = skin_theme.lower()
        if skin_dir == "skin.confluence":
            skin_color = "FFEB9E17"
        elif skin_dir == "skin.estuary":
            if "brown" in skin_theme:
                skin_color = "FFFF4400"
            elif "charcoal" in skin_theme:
                skin_color = "FF11E7B1"
            elif "chartreuse" in skin_theme:
                skin_color = "FF24C6C9"
            elif "concrete" in skin_theme:
                skin_color = "FFFF8C00"
            elif "default" in skin_theme:
                skin_color = "FF11E7B1"
            elif "gold" in skin_theme:
                skin_color = "FFFFF000"
            elif "green" in skin_theme:
                skin_color = "FF14D519"
            elif "maroon" in skin_theme:
                skin_color = "FF24C6C9"
            elif "midnight" in skin_theme:
                skin_color = "FF5BE5EE"
            elif "orange" in skin_theme:
                skin_color = "FFFFF100"
            elif "pink" in skin_theme:
                skin_color = "FF94D800"
            elif "rose" in skin_theme:
                skin_color = "FFFF0261"
            elif "teal" in skin_theme:
                skin_color = "FFC67F03"
            elif "violet" in skin_theme:
                skin_color = "FFFF0054"
        elif skin_dir == "skin.estouchy":
            skin_color = "FF11E7B1"
        elif skin_dir == "skin.arctic.horizon":
            skin_color = "ff0385b5"
        elif skin_dir == "skin.arctic.zephyr":
            skin_color = "ff0385b5"
        elif skin_dir == "skin.arctic.zephyr.2":
            skin_color = "ff0385b5"
        elif skin_dir == "skin.aura":
            skin_color = "ff0385b5 "
        elif skin_dir == "skin.eminence.2":
            skin_color = "ff287ba8"
        elif skin_dir == "skin.eminence":
            if "crimson" in skin_theme:
                skin_color = "ffdc143c"
            elif "emerald" in skin_theme:
                skin_color = "ff46b995"
            elif "lilac" in skin_theme:
                skin_color = "ffa682a6"
            elif "lime" in skin_theme:
                skin_color = "FFb5e533"
            elif "magenta" in skin_theme:
                skin_color = "FFe533b5"
            elif "orange" in skin_theme:
                skin_color = "ffd76c38"
            elif "default" in skin_theme:
                skin_color = "FF33b5e5"
        elif skin_dir == "skin.aura":
            skin_color = "ffededed"
        elif skin_dir == "skin.fuse.neue":
            skin_color = "ffe53564"
        elif skin_dir == "skin.auramod":
            skin_color = "ffededed"

        result = xbmc.getInfoLabel(
            "Skin.String({})".format("focuscolor.name")  # jurial based skins.
        )
        return result if result else skin_color

    def get_user_text_color(self):
        """Get the user selected color setting when nothing is selecting it returns
        the default value (deepskyblue) or the default form the installed skin.

        :return:Selected color from the user or the default from the skin or the Seren default (deepskyblue)
        :rtype:str
        """
        color = self.get_setting("general.displayColor")
        skin_color = self._try_get_color_from_skin()
        if not color or color == "None":
            if not skin_color:
                color = "deepskyblue"
            else:
                color = skin_color
        if color == "inherit":
            color = skin_color
        if not color:
            color = "deepskyblue"
        return color

    def color_string(self, text, color=None):
        """Method that wraps the the text with the supplied color, or takes the user default.

        :param text:Text that needs to be wrapped
        :type text:str|int|float
        :param color:Color name used in the Kodi color tag
        :type color:str
        :return:Text wrapped in a Kodi color tag.
        :rtype:str
        """
        if not isinstance(text, (int, float)):
            text = self.display_string(text)

        if color == "default" or not color or color == "inherit":
            color = self.get_user_text_color()

        return "[COLOR {}]{}[/COLOR]".format(color, text)

    def clear_cache(self):
        confirm = xbmcgui.Dialog().yesno(
            self.ADDON_NAME, self.get_language_string(30030)
        )
        if confirm != 1:
            return
        g.CACHE.clear_all()
        g._init_cache()
        self.log(self.ADDON_NAME + ": Cache Cleared", "debug")
        xbmcgui.Dialog().notification(self.ADDON_NAME, self.get_language_string(30053))

    def cancel_playback(self):
        self.PLAYLIST.clear()
        xbmcplugin.setResolvedUrl(
            self.PLUGIN_HANDLE, False, xbmcgui.ListItem(offscreen=True)
        )
        self.close_busy_dialog()
        self.close_all_dialogs()

    def show_busy_dialog(self):
        xbmc.executebuiltin("ActivateWindow(busydialognocancel)")

    def close_all_dialogs(self):
        xbmc.executebuiltin("Dialog.Close(all,true)")

    def close_ok_dialog(self):
        xbmc.executebuiltin("Dialog.Close(okdialog, true)")

    def close_busy_dialog(self):
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        xbmc.executebuiltin("Dialog.Close(busydialognocancel)")

    def display_string(self, value):
        if isinstance(value, (tools.basestring, tools.unicode)):
            return self.deaccent_string(value)
        if isinstance(value, int):
            return "{}".format(value)
        if isinstance(value, bytes):
            return "".join(chr(x) for x in value)
        return value

    def deaccent_string(self, text):
        text = self.decode_py2(text)
        text = unicodedata.normalize("NFD", text)
        text = text.encode("ascii", "ignore")
        text = text.decode("utf-8")
        return str(text)

    def premium_check(self):
        if self.PLAYLIST.getposition() <= 0 and not self.debrid_available():
            return False
        else:
            return True

    def debrid_available(self):
        return (
            self.premiumize_enabled()
            or self.real_debrid_enabled()
            or self.all_debrid_enabled()
        )

    def premiumize_enabled(self):
        if self.get_setting("premiumize.token") != "" and self.get_bool_setting(
            "premiumize.enabled"
        ):
            return True
        else:
            return False

    def real_debrid_enabled(self):
        if self.get_setting("rd.auth") and self.get_bool_setting("realdebrid.enabled"):
            return True
        else:
            return False

    def all_debrid_enabled(self):
        if self.get_setting("alldebrid.apikey") != "" and self.get_bool_setting(
            "alldebrid.enabled"
        ):
            return True
        else:
            return False

    def container_refresh(self):
        return xbmc.executebuiltin("Container.Refresh")

    def trigger_widget_refresh(self):
        # Force an update of widgets to occur
        self.log("FORCE REFRESHING WIDGETS")
        timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
        self.HOME_WINDOW.setProperty("widgetreload", timestr)
        self.HOME_WINDOW.setProperty("widgetreload-tvshows", timestr)
        self.HOME_WINDOW.setProperty("widgetreload-episodes", timestr)
        self.HOME_WINDOW.setProperty("widgetreload-movies", timestr)

    def get_language_code(self, region=None):
        if region:
            lang = xbmc.getLanguage(xbmc.ISO_639_1, True)
            if lang.lower() == "en-de":
                lang = "en-gb"
            lang = lang.split("-")
            if len(lang) > 1:
                lang = "{}-{}".format(lang[0].lower(), lang[1].upper())
                return lang
        return xbmc.getLanguage(xbmc.ISO_639_1, False)

    @cached_property
    def common_video_extensions(self):
        return [
            i
            for i in xbmc.getSupportedMedia("video").split("|")
            if i != "" and i != ".zip"
        ]

    def add_directory_item(self, name, **params):
        [params.update({key: g.encode_py2(value)}) for key, value in params.items()]
        menu_item = params.pop("menu_item", {})
        if not isinstance(menu_item, dict):
            menu_item = {}

        if "info" in menu_item:
            [
                menu_item["info"].update({key: value.decode("utf-8")})
                for key, value in menu_item["info"].items()
                if isinstance(value, bytes)
            ]

        item = xbmcgui.ListItem(label=name, offscreen=True)
        item.setContentLookup(False)
        item.addStreamInfo("video", {})
        info = menu_item.pop("info", {})

        if info is None or not isinstance(info, dict):
            info = {}

        self._apply_listitem_properties(item, info)

        if "unwatched_episodes" in menu_item:
            item.setProperty("UnWatchedEpisodes", str(menu_item["unwatched_episodes"]))
        if "watched_episodes" in menu_item:
            item.setProperty("WatchedEpisodes", str(menu_item["watched_episodes"]))
        if menu_item.get("episode_count", 0) > 0 and menu_item.get(
            "episode_count", 0
        ) == menu_item.get("watched_episodes", 0):
            info["playcount"] = 1
        if (
            menu_item.get("watched_episodes", 0) == 0
            and menu_item.get("episode_count", 0) > 0
        ):
            item.setProperty("WatchedEpisodes", str(0))
            item.setProperty(
                "UnWatchedEpisodes", str(menu_item.get("episode_count", 0))
            )
        if "episode_count" in menu_item:
            item.setProperty("TotalEpisodes", str(menu_item["episode_count"]))
        if "season_count" in menu_item:
            item.setProperty("TotalSeasons", str(menu_item["season_count"]))
        if (
            "percent_played" in menu_item
            and menu_item.get("percent_played") is not None
        ):
            if float(menu_item.get("percent_played", 0)) > 0:
                item.setProperty("percentplayed", str(menu_item["percent_played"]))
        if "resume_time" in menu_item and menu_item.get("resume_time") is not None:
            if int(menu_item.get("resume_time", 0)) > 0:
                params["resume"] = str(menu_item["resume_time"])
                item.setProperty("resumetime", str(menu_item["resume_time"]))
        if "play_count" in menu_item and menu_item.get("play_count") is not None:
            info["playcount"] = menu_item["play_count"]
        if "description" in params:
            info["plot"] = info["overview"] = info["description"] = params.pop(
                "description", None
            )
        if "special_sort" in params:
            item.setProperty("SpecialSort", str(params["special_sort"]))
        label2 = params.pop("label2", None)
        if label2 is not None:
            item.setLabel2(label2)

        if params.pop("is_playable", False):
            item.setProperty("IsPlayable", "true")
            is_folder = params.pop("is_folder", False)
        else:
            item.setProperty("IsPlayable", "false")
            is_folder = params.pop("is_folder", True)

        cast = menu_item.get("cast", [])
        if cast is None or not isinstance(cast, (set, list)):
            cast = []
        item.setCast(cast)

        [
            item.setProperty(key, str(value))
            for key, value in info.items()
            if key.endswith("_id")
        ]
        item.setUniqueIDs(
            {
                id_: info[i]
                for i in info.keys()
                for id_ in ["imdb", "tvdb", "tmdb", "anidb"]
                if i == "{}_id".format(id_)
            }
        )
        [
            item.setRating(
                i.split(".")[1], float(info[i].get("rating", 0.0)), int(info[i].get("votes", 0)), False
            )
            for i in info.keys()
            if i.startswith("rating.")
        ]

        cm = params.pop("cm", [])
        if cm is None or not isinstance(cm, (set, list)):
            cm = []
        item.addContextMenuItems(cm)

        art = menu_item.pop("art", {})
        if art is None or not isinstance(art, dict):
            art = {}
        if (
            art.get("fanart", art.get("season.fanart", art.get("tvshow.fanart", None)))
            is None
        ) and not self.get_bool_setting("general.fanart.fallback", False):
            art["fanart"] = self.DEFAULT_FANART
        if (
            art.get("poster", art.get("season.poster", art.get("tvshow.poster", None)))
            is None
        ):
            art["poster"] = self.DEFAULT_ICON
        if art.get("icon") is None:
            art["icon"] = self.DEFAULT_FANART
        if art.get("thumb") is None:
            art["thumb"] = ""
        try:
            item.setArt(art)
        except:
            pass

        # Clear out keys not relevant to Kodi info labels
        self.clean_info_keys(info)

        item.setInfo("video", info)

        bulk_add = params.pop("bulk_add", False)
        url = self.create_url(self.BASE_URL, params)
        if bulk_add:
            return url, item, is_folder
        else:
            xbmcplugin.addDirectoryItem(
                handle=self.PLUGIN_HANDLE, url=url, listitem=item, isFolder=is_folder
            )

    def add_menu_items(self, item_list):
        xbmcplugin.addDirectoryItems(self.PLUGIN_HANDLE, item_list, len(item_list))

    @staticmethod
    def clean_info_keys(info_dict):
        if info_dict is None:
            return None

        if not isinstance(info_dict, dict):
            return info_dict

        keys_to_remove = [i for i in info_dict.keys() if i not in info_labels]
        [info_dict.pop(key) for key in keys_to_remove]

        return info_dict

    def close_directory(self, content_type, sort=False, cache=False):
        if sort == "title":
            xbmcplugin.addSortMethod(
                self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE
            )
        if sort == "episode":
            xbmcplugin.addSortMethod(self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
        if not sort:
            xbmcplugin.addSortMethod(self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.setContent(self.PLUGIN_HANDLE, content_type)
        menu_caching = self.get_bool_setting("general.menucaching") or cache
        xbmcplugin.endOfDirectory(self.PLUGIN_HANDLE, cacheToDisc=menu_caching)
        tools.run_threaded(self.set_view_type, content_type)

    def set_view_type(self, content_type):
        if self.get_bool_setting("general.setViews") and self.is_addon_visible():
            view_type = self.get_view_type(content_type)
            if view_type > 0:
                xbmc.sleep(200)
                xbmc.executebuiltin("Container.SetViewMode({})".format(view_type))

    def is_addon_visible(self):
        return xbmc.getCondVisibility("Window.IsMedia") == 1

    def cancel_directory(self):
        xbmcplugin.setContent(self.PLUGIN_HANDLE, g.CONTENT_FOLDER)
        xbmcplugin.endOfDirectory(self.PLUGIN_HANDLE, cacheToDisc=False)

    def read_all_text(self, file_path):
        try:
            f = xbmcvfs.File(file_path, "r")
            return f.read()
        except IOError:
            return None
        finally:
            try:
                f.close()
            except:
                pass

    def write_all_text(self, file_path, content):
        try:
            f = xbmcvfs.File(file_path, "w")
            return f.write(content)
        except IOError:
            return None
        finally:
            try:
                f.close()
            except:
                pass

    def notification(self, heading, message, time=5000, sound=True):
        if self.get_bool_setting("general.disableNotificationSound"):
            sound = False
        return xbmcgui.Dialog().notification(heading, message, time=time, sound=sound)

    def json_rpc(self, method, params=None):
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1,
            "params": params or {},
        }
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request_data)))
        if "error" in response:
            self.log(
                "{}: {}".format(response["error"]["code"], response["error"]["message"])
            )
        return response["result"]

    def get_kodi_subtitle_languages(self, iso_format=False):
        subtitle_language = self.json_rpc(
            "Settings.GetSettingValue", {"setting": "subtitles.languages"}
        )
        if iso_format:
            return [self.convert_language_iso(x) for x in subtitle_language["value"]]
        else:
            return [x for x in subtitle_language["value"]]

    def get_kodi_preferred_subtitle_language(self, iso_format=False):
        subtitle_language = self.json_rpc(
            "Settings.GetSettingValue", {"setting": "locale.subtitlelanguage"}
        )
        if subtitle_language["value"] in ["forced_only", "original", "default", "none"]:
            return subtitle_language["value"]
        if iso_format:
            return self.convert_language_iso(subtitle_language["value"])
        else:
            return subtitle_language["value"]

    def convert_language_iso(self, from_value):
        return xbmc.convertLanguage(self.decode_py2(from_value), xbmc.ISO_639_1)

    @staticmethod
    def _apply_listitem_properties(item, info):
        for i in listitem_properties:
            if isinstance(i[0], tuple):
                value = info
                for subkey in i[0]:
                    value = value.get(subkey, {})
                if value:
                    item.setProperty(i[1], str(g.encode_py2(value)))
            elif i[0] in info:
                item.setProperty(i[1], str(g.encode_py2(info[i[0]])))

    def create_url(self, base_url, params):
        if params is None:
            return base_url
        if "action_args" in params and isinstance(params["action_args"], dict):
            params["action_args"] = json.dumps(params["action_args"], sort_keys=True)
        params["from_widget"] = "true" if not self.is_addon_visible() else "false"
        sep = "/" if not self.is_addon_visible() else ""
        return "{}{}?{}".format(base_url, sep, tools.urlencode(sorted(params.items())))

    @staticmethod
    def abort_requested():
        return xbmc.Monitor().abortRequested()

    @staticmethod
    def reload_profile():
        xbmc.executebuiltin('LoadProfile({})'.format(xbmc.getInfoLabel("system.profilename")))


g = GlobalVariables()
