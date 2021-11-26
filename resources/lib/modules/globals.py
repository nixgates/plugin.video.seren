# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

# Import Thread lock workaround
# noinspection PyUnresolvedReferences
import _strptime
import json
import os
import re
import traceback
import unicodedata

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from unidecode import unidecode

from resources.lib.common import tools
from resources.lib.modules.settings_cache import PersistedSettingsCache, RuntimeSettingsCache
from resources.lib.third_party import pytz, tzlocal
from resources.lib.third_party.cached_property import cached_property

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

info_dates = [
    "premiered",
    "aired",
    "lastplayed",
    "dateadded",
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
    CONTENT_MENU = ""
    CONTENT_FILES = "files"
    CONTENT_MOVIE = "movies"
    CONTENT_SHOW = "tvshows"
    CONTENT_SEASON = "seasons"
    CONTENT_EPISODE = "episodes"
    CONTENT_GENRES = "genres"
    CONTENT_YEARS = "years"
    MEDIA_MENU = ""
    MEDIA_FOLDER = "file"
    MEDIA_MOVIE = "movie"
    MEDIA_SHOW = "tvshow"
    MEDIA_SEASON = "season"
    MEDIA_EPISODE = "episode"

    DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
    DATE_TIME_FORMAT_ZULU = DATE_TIME_FORMAT + ".000Z"
    DATE_FORMAT = "%Y-%m-%d"

    PYTHON3 = tools.PYTHON3
    UNICODE = tools.unicode
    SEMVER_REGEX = re.compile(r"^((?:\d+\.){2}\d+)")

    def __init__(self):
        self.IS_ADDON_FIRSTRUN = None
        self.ADDON = None
        self.ADDON_DATA_PATH = None
        self.ADDON_ID = None
        self.ADDON_NAME = None
        self.VERSION = None
        self.CLEAN_VERSION = None
        self.USER_AGENT = None
        self.DEFAULT_FANART = None
        self.DEFAULT_ICON = None
        self.NEXT_PAGE_ICON = None
        self.ADDON_USERDATA_PATH = None
        self.SETTINGS_CACHE = None
        self.RUNTIME_SETTINGS_CACHE = None
        self.LANGUAGE_CACHE = {}
        self.PLAYLIST = None
        self.HOME_WINDOW = None
        self.KODI_DATE_LONG_FORMAT = None
        self.KODI_DATE_SHORT_FORMAT = None
        self.KODI_TIME_FORMAT = None
        self.KODI_TIME_NO_SECONDS_FORMAT = None
        self.KODI_FULL_VERSION = None
        self.KODI_VERSION = None
        self.PLATFORM = self._get_system_platform()
        self.UTC_TIMEZONE = pytz.utc
        self.LOCAL_TIMEZONE = None
        self.URL = None
        self.PLUGIN_HANDLE = 0
        self.IS_SERVICE = True
        self.BASE_URL = None
        self.PATH = None
        self.PARAM_STRING = None
        self.REQUEST_PARAMS = None
        self.FROM_WIDGET = False
        self.PAGE = 1

    def __del__(self):
        self.deinit()

    def deinit(self):
        self.ADDON = None
        del self.ADDON
        self.PLAYLIST = None
        del self.PLAYLIST
        self.HOME_WINDOW = None
        del self.HOME_WINDOW

    def init_globals(self, argv=None, addon_id=None):
        self.IS_ADDON_FIRSTRUN = self.IS_ADDON_FIRSTRUN is None
        self.ADDON = xbmcaddon.Addon()
        self.ADDON_ID = addon_id if addon_id else self.ADDON.getAddonInfo("id")
        self.ADDON_NAME = self.ADDON.getAddonInfo("name")
        self.VERSION = self.ADDON.getAddonInfo("version")
        self.CLEAN_VERSION = self.SEMVER_REGEX.findall(self.VERSION)[0]
        self.USER_AGENT = "{} - {}".format(self.ADDON_NAME, self.CLEAN_VERSION)
        self._init_kodi()
        self._init_settings_cache()
        self._init_local_timezone()
        self._init_paths()
        self.DEFAULT_FANART = self.ADDON.getAddonInfo("fanart")
        self.DEFAULT_ICON = self.ADDON.getAddonInfo("icon")
        self.NEXT_PAGE_ICON = self.IMAGES_PATH + "next.png"
        self.init_request(argv)
        self._init_cache()

    def _init_kodi(self):
        self.PLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.HOME_WINDOW = xbmcgui.Window(10000)
        self.KODI_DATE_LONG_FORMAT = xbmc.getRegion("datelong")
        self.KODI_DATE_SHORT_FORMAT = xbmc.getRegion("dateshort")
        self.KODI_TIME_FORMAT = xbmc.getRegion("time")
        self.KODI_TIME_NO_SECONDS_FORMAT = self.KODI_TIME_FORMAT.replace(":%S", "")
        self.KODI_FULL_VERSION = xbmc.getInfoLabel("System.BuildVersion")
        version = re.findall(r'(?:(?:((?:\d+\.?){1,3}\S+))?\s+\(((?:\d+\.?){2,3})\))', self.KODI_FULL_VERSION)
        if version:
            self.KODI_FULL_VERSION = version[0][1]
            if len(version[0][0]) > 1:
                pre_ver = version[0][0][:2]
                full_ver = version[0][1][:2]
                if pre_ver > full_ver:
                    self.KODI_VERSION = int(pre_ver[:2])
                else:
                    self.KODI_VERSION = int(full_ver[:2])
            else:
                self.KODI_VERSION = int(version[0][1][:2])
        else:
            self.KODI_FULL_VERSION = self.KODI_FULL_VERSION.split(' ')[0]
            self.KODI_VERSION = int(self.KODI_FULL_VERSION[:2])

    def _init_settings_cache(self):
        self.RUNTIME_SETTINGS_CACHE = RuntimeSettingsCache()
        self.SETTINGS_CACHE = PersistedSettingsCache()

    def _init_local_timezone(self):
        try:
            timezone_string = self.get_setting("general.localtimezone")
            if timezone_string:
                self.LOCAL_TIMEZONE = pytz.timezone(timezone_string)
        except pytz.UnknownTimeZoneError:
            self.log("Invalid local timezone '{}' in settings.xml".format(timezone_string), "debug")
        except Exception as e:
            self.log("Error using local timezone '{}' in settings.xml: {}".format(timezone_string, e),
                     "warning")
        finally:
            if not self.LOCAL_TIMEZONE or self.LOCAL_TIMEZONE == self.UTC_TIMEZONE:
                self.init_local_timezone()

    def init_local_timezone(self):
        """
        Attempts to detect the local timezone via a variety of approaches
        Initializes LOCAL_TIMEZONE to correct tzinfo value
        If this fails we should just use UTC as lack of any LOCAL_TIMEZONE will cause many failures
        :return: None
        """
        timezone_string = None
        try:
            try:
                response = self.json_rpc("Settings.GetSettingValue", {"setting": "locale.timezone"})
                timezone_string = response.get("value", '')

                self.LOCAL_TIMEZONE = pytz.timezone(timezone_string)
            except pytz.UnknownTimeZoneError:
                if timezone_string:
                    self.log(
                        "Kodi provided an invalid local timezone '{}', trying a different approach".format(
                            timezone_string
                        ),
                        "warning"
                    )
                else:
                    self.log(
                        "Kodi does not support locale.timezone JSON RPC call on your platform, trying a different "
                        "approach",
                        "debug"
                    )
            except Exception as e:
                self.log(
                    "Error detecting local timezone with Kodi, trying a different approach: {}".format(e),
                    "warning"
                )
            # If Kodi detection failed, fall back on tzlocal
            try:
                if not self.LOCAL_TIMEZONE or self.LOCAL_TIMEZONE == self.UTC_TIMEZONE:
                    self.LOCAL_TIMEZONE = tzlocal.get_localzone()
            except Exception as e:
                self.log("Error detecting local timezone with alternative approach: {}".format(e), "warning")
            # If we still don't have a timezone, try manual setting
            try:
                if not self.LOCAL_TIMEZONE or self.LOCAL_TIMEZONE == self.UTC_TIMEZONE:
                    g.set_setting("general.manualtimezone", True)
                    timezone_string = self.get_setting("general.localtimezone")
                    if timezone_string:
                        self.LOCAL_TIMEZONE = pytz.timezone(timezone_string)
                else:
                    g.set_setting("general.manualtimezone", False)
            except pytz.UnknownTimeZoneError:
                self.log("Invalid local timezone '{}' in settings.xml".format(timezone_string), "debug")
            except Exception as e:
                self.log("Error using local timezone '{}' in settings.xml: {}".format(timezone_string, e),
                         "warning")
        finally:
            # If Kodi and tzocal detection fails and we don't have a valid manual setting, fallback to UTC
            if not self.LOCAL_TIMEZONE:
                self.LOCAL_TIMEZONE = self.UTC_TIMEZONE
            if self.LOCAL_TIMEZONE == self.UTC_TIMEZONE:
                self.log(
                    "Unable to detect local timezone, defaulting to UTC for displayed dates/times. "
                    "Note that this does not affect filtering or sorting, only display",
                    "debug"
                )
            self.set_setting("general.localtimezone", self.LOCAL_TIMEZONE.zone)

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
        self.PATH = tools.unquote(self.URL[2])
        try:
            self.PARAM_STRING = argv[2].lstrip('?/')
        except IndexError:
            self.PARAM_STRING = ""
        self.REQUEST_PARAMS = self.legacy_params_converter(
            dict(tools.parse_qsl(self.PARAM_STRING))
        )
        if "action_args" in self.REQUEST_PARAMS:
            self.REQUEST_PARAMS["action_args"] = tools.deconstruct_action_args(
                self.REQUEST_PARAMS["action_args"]
            )
            if isinstance(self.REQUEST_PARAMS["action_args"], dict):
                self.REQUEST_PARAMS["action_args"] = self.legacy_action_args_converter(
                    self.REQUEST_PARAMS["action_args"]
                )
        self.FROM_WIDGET = self.REQUEST_PARAMS.get("from_widget", "true") == "true"
        self.PAGE = int(g.REQUEST_PARAMS.get("page", 1))

    @staticmethod
    def legacy_action_args_converter(action_args):
        if "item_type" not in action_args:
            return action_args

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

        if "show" in action_args["item_type"]:
            action_args["item_type"] = "shows"

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
        self.ADDONS_PATH = tools.translate_path(
            os.path.join("special://home/", "addons/")
        )
        self.ADDON_PATH = tools.translate_path(
            os.path.join(
                "special://home/", "addons/{}".format(self.ADDON_ID.lower())
            )
        )
        self.ADDON_DATA_PATH = tools.translate_path(
            self.ADDON.getAddonInfo("path")
        )  # Addon folder
        self.ADDON_USERDATA_PATH = tools.translate_path(
            "special://profile/addon_data/{}/".format(self.ADDON_ID)
        )  # Addon user data folder
        self.SETTINGS_PATH = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "settings.xml")
        )
        self.ADVANCED_SETTINGS_PATH = tools.translate_path(
            "special://profile/advancedsettings.xml"
        )
        self.KODI_DATABASE_PATH = tools.translate_path("special://database/")
        self.GUI_PATH = tools.translate_path(
            os.path.join(self.ADDON_DATA_PATH, "resources", "lib", "gui")
        )
        self.IMAGES_PATH = self.ADDON.getAddonInfo("path") + "/resources/images/"
        self.GENRES_PATH = self.IMAGES_PATH + "genres/"
        self.SKINS_PATH = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "skins")
        )
        self.CACHE_DB_PATH = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "cache.db")
        )
        self.TORRENT_CACHE = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "torrentCache.db")
        )
        self.TORRENT_ASSIST = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "torentAssist.db")
        )
        self.PROVIDER_CACHE_DB_PATH = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "providers.db")
        )
        self.PREMIUMIZE_DB_PATH = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "premiumize.db")
        )
        self.TRAKT_SYNC_DB_PATH = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "traktSync.db")
        )
        self.SEARCH_HISTORY_DB_PATH = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "search.db")
        )
        self.SKINS_DB_PATH = tools.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "skins.db")
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

    def get_kodi_video_db_connection(self):
        config = self.get_kodi_video_db_config()
        if config["type"] == "sqlite3":
            from resources.lib.database import SQLiteConnection
            return SQLiteConnection(os.path.join(self.KODI_DATABASE_PATH, "{}.db".format(config["database"])))
        elif config["type"] == "mysql":
            from resources.lib.database import MySqlConnection
            return MySqlConnection(config)

    def get_kodi_database_version(self):
        if self.KODI_VERSION == 17:
            return "107"
        elif self.KODI_VERSION == 18:
            return "116"
        elif self.KODI_VERSION == 19:
            return "119"

        raise KeyError("Unsupported kodi version")

    def get_kodi_video_db_config(self):
        result = {
            "type": "sqlite3",
            "database": "MyVideos{}".format(self.get_kodi_database_version())
        }

        if xbmcvfs.exists(self.ADVANCED_SETTINGS_PATH):
            advanced_settings_text = g.read_all_text(self.ADVANCED_SETTINGS_PATH)
            if advanced_settings_text:
                try:
                    advanced_settings = tools.ElementTree.fromstring(advanced_settings_text)
                    settings = advanced_settings.find("videodatabase")
                    if settings:
                        for setting in settings:
                            if setting.tag == 'type':
                                result["type"] = setting.text
                            elif setting.tag == 'host':
                                result["host"] = setting.text
                            elif setting.tag == 'port':
                                result["port"] = setting.text
                            elif setting.tag == 'name':
                                result["database"] = setting.text
                            elif setting.tag == 'user':
                                result["user"] = setting.text
                            elif setting.tag == 'pass':
                                result["password"] = setting.text
                except tools.ElementTree.ParseError as pe:
                    g.log("Failed to parse advanced settings.xml: {}".format(pe), "warning")
        return result

    def clear_kodi_bookmarks(self):
        with self.get_kodi_video_db_connection() as video_database:
            file_ids = [str(i["idFile"]) for i in video_database.fetchall(
                "SELECT * FROM files WHERE strFilename LIKE '%plugin.video.seren%'")]
            if not file_ids:
                return
            video_database.execute_sql(["DELETE FROM {} WHERE idFile IN ({})".format(table, ",".join(file_ids))
                                        for table in ["bookmark", "streamdetails", "files"]])

    # region runtime settings
    def set_runtime_setting(self, setting_id, value):
        """
        Set a runtime setting value

        Lists and Dict may only contain simple types

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param value: The value to store in settings
        :type value: str|unicode|float|int|bool|list|dict
        """
        self.RUNTIME_SETTINGS_CACHE.set_setting(setting_id, value)

    def clear_runtime_setting(self, setting_id):
        """
        Clear a runtime setting from the cache.

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        """
        self.RUNTIME_SETTINGS_CACHE.clear_setting(setting_id)

    def get_runtime_setting(self, setting_id, default_value=None):
        """
        Get a runtime setting value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: str|unicode|float|int|bool
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or None
        :rtype: str|unicode|float|int|bool|list|dict
        """
        return self.RUNTIME_SETTINGS_CACHE.get_setting(setting_id, default_value)

    def get_float_runtime_setting(self, setting_id, default_value=None):
        """
        Get a runtime setting as a float value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: float
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0.0
        :rtype: float
        """
        return self.RUNTIME_SETTINGS_CACHE.get_float_setting(setting_id, default_value)

    def get_int_runtime_setting(self, setting_id, default_value=None):
        """
        Get a runtime setting as an int value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: int
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0
        :rtype: int
        """
        return self.RUNTIME_SETTINGS_CACHE.get_int_setting(setting_id, default_value)

    def get_bool_runtime_setting(self, setting_id, default_value=None):
        """
        Get a runtime setting as a bool value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: bool
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or False
        :rtype: bool
        """
        return self.RUNTIME_SETTINGS_CACHE.get_bool_setting(setting_id, default_value)
    # endregion

    # region KODI setting
    def set_setting(self, setting_id, value):
        """
        Set a setting value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param value: The value to store in settings
        :type value: str|unicode|float|int|bool
        """
        self.SETTINGS_CACHE.set_setting(setting_id, value)

    def clear_setting(self, setting_id):
        """
        Clear a setting from the cache and settings.xml

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        """
        self.SETTINGS_CACHE.clear_setting(setting_id)

    def get_setting(self, setting_id, default_value=None):
        """
        Get a setting value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param default_value:
        :type default_value: str|unicode
        :return: The value of the setting as a string
                 If the setting is not stored, the optional default_value if provided or None
        :rtype: str|unicode
        """
        return self.SETTINGS_CACHE.get_setting(setting_id, default_value)

    def get_float_setting(self, setting_id, default_value=None):
        """
        Get a setting as a float value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: float
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0.0
        :rtype: float
        """
        return self.SETTINGS_CACHE.get_float_setting(setting_id, default_value)

    def get_int_setting(self, setting_id, default_value=None):
        """
        Get a setting as an int value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: int
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0
        :rtype: int
        """
        return self.SETTINGS_CACHE.get_int_setting(setting_id, default_value)

    def get_bool_setting(self, setting_id, default_value=None):
        """
        Get a setting as a bool value

        :param setting_id: The name of the setting
        :type setting_id: str|unicode
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: bool
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or False
        :rtype: bool
        """
        return self.SETTINGS_CACHE.get_bool_setting(setting_id, default_value)
    # endregion

    def get_language_string(self, localization_id, addon=True):
        """
        Gets a localized string from cache if feasible, if not from localization files
        Will retrieve from addon localizations by default but can be requested from Kodi localizations

        :param localization_id: The id of the localization to retrieve
        :type localization_id: int
        :param addon: True to retrieve from addon, False from Kodi localizations.  Default True
        :type addon bool
        :return: The localized text matching the localization_id from the appropriate localization files.
        :rtype: str|unicode
        """
        cache_id = "A" + str(localization_id) if addon else "K" + str(localization_id)
        text = self.LANGUAGE_CACHE.get(cache_id)
        if not text:
            text = self.ADDON.getLocalizedString(localization_id) if addon else xbmc.getLocalizedString(localization_id)
            self.LANGUAGE_CACHE.update({cache_id: text})

        return text

    def get_view_type(self, content_type):
        no_view_type = 0
        view_type = None

        if not self.get_bool_setting("general.viewidswitch"):
            if content_type == self.CONTENT_MENU:
                view_type = self.get_setting("addon.view")
            if content_type == self.CONTENT_SHOW:
                view_type = self.get_setting("show.view")
            if content_type == self.CONTENT_MOVIE:
                view_type = self.get_setting("movie.view")
            if content_type == self.CONTENT_EPISODE:
                view_type = self.get_setting("episode.view")
            if content_type == self.CONTENT_SEASON:
                view_type = self.get_setting("season.view")
            if view_type is not None and view_type.isdigit() and int(view_type) > 0:
                view_name, view_type = viewTypes[int(view_type)]
                return view_type
        else:
            if content_type == self.CONTENT_MENU:
                view_type = self.get_setting("addon.view.id")
            if content_type == self.CONTENT_SHOW:
                view_type = self.get_setting("show.view.id")
            if content_type == self.CONTENT_MOVIE:
                view_type = self.get_setting("movie.view.id")
            if content_type == self.CONTENT_EPISODE:
                view_type = self.get_setting("episode.view.id")
            if content_type == self.CONTENT_SEASON:
                view_type = self.get_setting("season.view.id")
            if view_type is not None and view_type.isdigit() and int(view_type) > 0:
                return int(view_type)

        return no_view_type

    def log(self, msg, level="info"):
        msg = msg
        msg = "{} ({}): {}".format(self.ADDON_NAME.upper(), self.PLUGIN_HANDLE, msg)
        if level == "error":
            xbmc.log(msg, level=xbmc.LOGERROR)
        elif level == "info":
            xbmc.log(msg, level=xbmc.LOGINFO)
        elif level == "notice":
            if self.KODI_VERSION >= 19:
                xbmc.log(msg, level=xbmc.LOGINFO)
            else:
                xbmc.log(msg, level=xbmc.LOGNOTICE)  # pylint: disable=no-member
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
            "{}: {}".format(self.ADDON_NAME, self.get_language_string(30016)), select_list
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
        if color == "default" or not color or color == "inherit":
            color = self.get_user_text_color()

        return "[COLOR {}]{}[/COLOR]".format(color, text)

    def clear_cache(self, silent=False):
        if not silent:
            confirm = xbmcgui.Dialog().yesno(
                self.ADDON_NAME, self.get_language_string(30029)
            )
            if confirm != 1:
                return
        g.CACHE.clear_all()
        g._init_cache()
        self.log(self.ADDON_NAME + ": Cache Cleared", "debug")
        if not silent:
            xbmcgui.Dialog().notification(self.ADDON_NAME, self.get_language_string(30052))

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

    @staticmethod
    def deaccent_string(text):
        """Deaccent the provided text leaving other unicode characters intact
        Example: Mîxéd ДљфӭЖ Tëst -> Mixed ДљфэЖ Test
        :param: text: Text to deaccent
        :type text: str|unicode
        :return: Deaccented string
        :rtype:str|unicode
        """
        nfkd_form = unicodedata.normalize('NFKD', text)  # pylint: disable=c-extension-no-member
        deaccented_text = g.UNICODE("").join(
            [c for c in nfkd_form if not unicodedata.combining(c)]  # pylint: disable=c-extension-no-member
        )
        return deaccented_text

    @staticmethod
    def transliterate_string(text):
        """Transliterate the provided text into ascii equivalents
        Example: 张新成 -> Zhang Xincheng
        Note that this method will remove any extra whitespace leaving only single spaces *between* characters
        :param: text: Text to transliterate
        :type text: str|unicode
        :return: Transliterated string
        :rtype:str|unicode
        """
        transliterted_text = unidecode(text)
        # Remove extra whitespace
        transliterted_text = g.UNICODE(" ").join(transliterted_text.split())
        return transliterted_text

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

    def trigger_widget_refresh(self, if_playing=True):
        """
        Trigger a widget refresh using the update library with an invalid path trick
        Widget refresh will not be attempted if playing if if_playing is False or if another process is waiting to
        refresh widgets.
        The widget refresh will not occur until the user returns to the home window to prevent updating other addon
        containers.

        Care must be taken when executing this method as it will block until the home window becomes available or
        playback is started or if the library is already being scanned
        :param if_playing: Whether to attempt to refresh widgets if playing.  Default: True
        :type if_playing: bool
        """
        player = xbmc.Player()
        if (
                self.get_bool_runtime_setting("widget_refreshing") or
                (player.isPlaying() and not if_playing) or  # Don't wait if we are playing as it will refresh after
                xbmc.getCondVisibility("Library.IsScanningVideo")  # Don't do library update if already scanning library
        ):
            del player
            return
        try:
            g.set_runtime_setting("widget_refreshing", True)
            while not self.abort_requested():
                if xbmcgui.getCurrentWindowId() == 10000:
                    self.log("TRIGGERING WIDGET REFRESH")
                    xbmc.executebuiltin('UpdateLibrary(video,widget_refresh,true)')
                    break
                elif (
                        self.wait_for_abort(0.5) or
                        player.isPlaying() or
                        xbmc.getCondVisibility("Library.IsScanningVideo")
                ):
                    break
        finally:
            del player
            g.clear_runtime_setting("widget_refreshing")

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
            if i not in ["", ".zip", ".rar"]
        ]

    def add_directory_item(self, name, **params):
        menu_item = params.pop("menu_item", {})
        if not isinstance(menu_item, dict):
            menu_item = {}

        item = xbmcgui.ListItem(label=name, offscreen=True)
        item.setContentLookup(False)

        info = menu_item.pop("info", {})
        item.addStreamInfo("video", {})

        if info is None or not isinstance(info, dict):
            info = {}

        self._apply_listitem_properties(item, info)

        if "unwatched_episodes" in menu_item:
            item.setProperty("UnWatchedEpisodes", g.UNICODE(menu_item["unwatched_episodes"]))
        if "watched_episodes" in menu_item:
            item.setProperty("WatchedEpisodes", g.UNICODE(menu_item["watched_episodes"]))
        if menu_item.get("episode_count", 0) \
                and menu_item.get("watched_episodes", 0) \
                and menu_item.get("episode_count", 0) == menu_item.get("watched_episodes", 0):
            info["playcount"] = 1
        if (
                menu_item.get("watched_episodes", 0) == 0
                and menu_item.get("episode_count", 0)
                and menu_item.get("episode_count", 0) > 0
        ):
            item.setProperty("WatchedEpisodes", g.UNICODE(0))
            item.setProperty(
                "UnWatchedEpisodes", g.UNICODE(menu_item.get("episode_count", 0))
            )
        if "episode_count" in menu_item:
            item.setProperty("TotalEpisodes", g.UNICODE(menu_item["episode_count"]))
        if "season_count" in menu_item:
            item.setProperty("TotalSeasons", g.UNICODE(menu_item["season_count"]))
        if (
                "percent_played" in menu_item
                and menu_item.get("percent_played") is not None
        ):
            if float(menu_item.get("percent_played", 0)) > 0:
                item.setProperty("percentplayed", g.UNICODE(menu_item["percent_played"]))
        if "resume_time" in menu_item and menu_item.get("resume_time") is not None:
            if int(menu_item.get("resume_time", 0)) > 0:
                params["resume"] = g.UNICODE(menu_item["resume_time"])
                item.setProperty("resumetime", g.UNICODE(menu_item["resume_time"]))
                # Temporarily disabling total time for pregoress indicators as it breaks resume
                # item.setProperty("totaltime", g.UNICODE(info["duration"]))
        if "play_count" in menu_item and menu_item.get("play_count") is not None:
            info["playcount"] = menu_item["play_count"]
        if "air_date" in menu_item and menu_item.get("air_date") is not None:
            info["premiered"] = menu_item["air_date"]
            info["aired"] = menu_item["air_date"]
        if "description" in params:
            info["plot"] = info["overview"] = info["description"] = params.pop(
                "description", None
            )
        if menu_item.get("user_rating"):
            item.setProperty("userrating", g.UNICODE(menu_item["user_rating"]))

        special_sort = params.pop("special_sort", None)
        if special_sort is not None:
            item.setProperty("SpecialSort", g.UNICODE(special_sort))
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

        for key, value in info.items():
            if key.endswith("_id"):
                item.setProperty(key, g.UNICODE(value))

        media_type = info.get("mediatype", None)
        id_keys = {
            "tmdb_id": "tmdb",
            "imdb_id": "imdb",
            "tvdb_id": "tvdb",
        }
        item.setUniqueIDs(
            {
                unique_id_key: info[
                    "tvshow." + id_key if media_type in ["episode", "season"] else id_key
                ]
                for id_key, unique_id_key in id_keys.items()
                if info.get("tvshow." + id_key if media_type in ["episode", "season"] else id_key)
            }
        )

        for i in info:
            if i.startswith("rating."):
                item.setRating(
                    i.split(".")[1], float(info[i].get("rating", 0.0)), int(info[i].get("votes", 0)), False
                )

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
        except Exception:
            pass

        # Clear out keys not relevant to Kodi info labels
        self.clean_info_keys(info)
        # Only TV shows/seasons/episodes have associated times, movies just have dates.
        if media_type in [g.MEDIA_SHOW, g.MEDIA_SEASON, g.MEDIA_EPISODE]:
            # Convert dates to localtime for display
            self.convert_info_dates(info)

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

        keys_to_remove = [i for i in info_dict if i not in info_labels]
        [info_dict.pop(key) for key in keys_to_remove]

        return info_dict

    def convert_info_dates(self, info_dict):
        if info_dict is None:
            return None

        if not isinstance(info_dict, dict):
            return info_dict

        dates_to_convert = [i for i in info_dict if i in info_dates]
        converted_dates = {key: self.utc_to_local(info_dict.get(key))
                           for key in dates_to_convert if info_dict.get(key)}
        info_dict.update(converted_dates)
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
        self.set_view_type(content_type)

    def set_view_type(self, content_type):
        def _execute_set_view_mode(view):
            xbmc.sleep(200)
            xbmc.executebuiltin("Container.SetViewMode({})".format(view))

        if self.get_bool_setting("general.setViews") and self.is_addon_visible():
            view_type = self.get_view_type(content_type)
            if view_type > 0:
                tools.run_threaded(_execute_set_view_mode, view_type)

    @staticmethod
    def is_addon_visible():
        return xbmc.getCondVisibility("Window.IsMedia")

    def cancel_directory(self):
        xbmcplugin.setContent(self.PLUGIN_HANDLE, g.CONTENT_MENU)
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
            except Exception:
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
            except Exception:
                pass

    def notification(self, heading, message, time=5000, sound=True):
        if self.get_bool_setting("general.disableNotificationSound"):
            sound = False
        dialogue = xbmcgui.Dialog()
        dialogue.notification(heading, message, time=time, sound=sound)
        del dialogue

    def get_keyboard_input(self, heading=None, default=None, hidden=False):
        k = xbmc.Keyboard(default, heading, hidden)
        k.doModal()
        input_value = k.getText() if k.isConfirmed() else None
        if not self.PYTHON3 and input_value:
            input_value = input_value.decode("utf-8")
        del k
        return input_value

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
                "JsonRPC Error {}: {}".format(response["error"]["code"], response["error"]["message"]), "debug"
            )
        return response.get("result", {})

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
        return xbmc.convertLanguage(from_value, xbmc.ISO_639_1)

    @staticmethod
    def _apply_listitem_properties(item, info):
        for i in listitem_properties:
            if isinstance(i[0], tuple):
                value = info
                for subkey in i[0]:
                    value = value.get(subkey, {})
                if value:
                    item.setProperty(i[1], g.UNICODE(value))
            elif i[0] in info:
                item.setProperty(i[1], g.UNICODE(info[i[0]]))

    def create_url(self, base_url, params):
        if params is None:
            return base_url
        if "action_args" in params and isinstance(params["action_args"], dict):
            params["action_args"] = json.dumps(params["action_args"], sort_keys=True)
        params["from_widget"] = "true" if not self.is_addon_visible() else "false"
        return "{}/?{}".format(base_url, tools.urlencode(sorted(params.items())))

    @staticmethod
    def abort_requested():
        monitor = xbmc.Monitor()
        abort_requested = monitor.abortRequested()
        del monitor
        return abort_requested

    @staticmethod
    def wait_for_abort(timeout=1.0):
        monitor = xbmc.Monitor()
        abort_requested = monitor.waitForAbort(timeout)
        del monitor
        return abort_requested

    @staticmethod
    def reload_profile():
        xbmc.executebuiltin('LoadProfile({})'.format(xbmc.getInfoLabel("system.profilename")))

    def validate_date(self, date_string):
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
            result = tools.parse_datetime(date_string, self.DATE_TIME_FORMAT_ZULU, False)
        except ValueError:
            pass

        if not result:
            try:
                result = tools.parse_datetime(date_string, self.DATE_TIME_FORMAT, False)
            except ValueError:
                pass

        if not result:
            try:
                result = tools.parse_datetime(date_string, self.DATE_FORMAT, False)
            except ValueError:
                pass

        if not result:
            try:
                result = tools.parse_datetime(date_string, "%d %b %Y", False)
            except ValueError:
                pass

        if result and result.year > 1900:
            return g.UNICODE(result.strftime(self.DATE_TIME_FORMAT))
        return None

    def utc_to_local(self, utc_string):
        """
        Converts a UTC style datetime string to the local timezone
        :param utc_string: UTC datetime string
        :return: localized datetime string
        """

        utc_string = self.validate_date(utc_string)

        if not utc_string:
            return None

        utc = tools.parse_datetime(utc_string, self.DATE_TIME_FORMAT, False)
        utc = self.UTC_TIMEZONE.localize(utc)
        local_time = utc.astimezone(self.LOCAL_TIMEZONE)
        return local_time.strftime(self.DATE_TIME_FORMAT)


g = GlobalVariables()
