# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import inspect
import threading
import time
import re
from collections import OrderedDict
from functools import wraps

import requests
import xbmc
import xbmcgui
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import (
    ApiBase,
    handle_single_item_or_list,
    handle_single_item_or_list_threaded,
)
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g
from resources.lib.third_party import pytz

CLOUDFLARE_ERROR_MSG = "Service Unavailable - Cloudflare error"

API_LOCK = threading.Lock()

TRAKT_STATUS_CODES = {
    200: "Success",
    201: "Success - new resource created (POST)",
    204: "Success - no content to return (DELETE)",
    400: "Bad Request - request couldn't be parsed",
    401: "Unauthorized - OAuth must be provided",
    403: "Forbidden - invalid API key or unapproved app",
    404: "Not Found - method exists, but no record found",
    405: "Method Not Found - method doesn't exist",
    409: "Conflict - resource already created",
    412: "Precondition Failed - use application/json content type",
    422: "Unprocessable Entity - validation errors",
    429: "Rate Limit Exceeded",
    500: "Server Error - please open a support issue",
    503: "Service Unavailable - server overloaded (try again in 30s)",
    504: "Service Unavailable - server overloaded (try again in 30s)",
    502: "Unspecified Error",
    520: CLOUDFLARE_ERROR_MSG,
    521: CLOUDFLARE_ERROR_MSG,
    522: CLOUDFLARE_ERROR_MSG,
    524: CLOUDFLARE_ERROR_MSG,
}


def trakt_auth_guard(func):
    """
    Decorator to ensure method will only run if a valid Trakt auth is present
    :param func: method to run
    :return: wrapper method
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Wrapper method
        :param args: method args
        :param kwargs: method kwargs
        :return: method results
        """
        if g.get_setting("trakt.auth"):
            return func(*args, **kwargs)
        elif xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30507)):
            TraktAPI().auth()
        else:
            g.cancel_directory()

    return wrapper


def _log_connection_error(args, kwarg, e):
    g.log("Connection Error to Trakt: {} - {}".format(args, kwarg), "error")
    g.log(e, "error")


def _connection_failure_dialog():
    if (
        g.get_float_setting("general.trakt.failure.timeout") + (2 * 60 * (60 * 60))
        < time.time()
        and not xbmc.Player().isPlaying()
    ):
        xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30025).format("Trakt"))
        g.set_setting("general.trakt.failure.timeout", str(time.time()))


def _reset_trakt_auth():
    settings = ["trakt.refresh", "trakt.auth", "trakt.expires", "trakt.username"]
    for i in settings:
        g.set_setting(i, "")
    xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30578))


def trakt_guard_response(func):
    """
    Decorator for Trakt API requests, handles retries and error responses
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Wrapper method for decorator
        :param args: method args
        :param kwargs: method kwargs
        :return:
        """
        method_class = args[0]
        try:
            response = func(*args, **kwargs)
            if response.status_code in [200, 201, 204]:
                return response

            if (
                response.status_code == 400
                and response.url == "https://api.trakt.tv/oauth/device/token"
            ):
                return response
            if (
                response.status_code == 400
                and response.url == "https://api.trakt.tv/oauth/token"
            ):
                _reset_trakt_auth()
                raise Exception("Unable to refresh Trakt auth")


            if response.status_code == 403:
                g.log("Trakt: invalid API key or unapproved app, resetting auth", "error")
                _reset_trakt_auth()
                g.cancel_directory()
                return None

            if response.status_code == 401:
                if inspect.stack(1)[1][3] == "try_refresh_token":
                    xbmcgui.Dialog().notification(
                        g.ADDON_NAME, g.get_language_string(30373)
                    )
                    g.log(
                        "Attempts to refresh Trakt token have failed. User intervention is required",
                        "error",
                    )
                else:
                    with GlobalLock("trakt.oauth", run_once=True, check_sum=method_class.access_token,
                                    threading_lock=API_LOCK) as lock:
                        if not lock.runned_once():
                            if method_class.refresh_token is not None:
                                method_class.try_refresh_token(True)
                            if (
                                method_class.refresh_token is None
                                and method_class.username is not None
                            ):
                                xbmcgui.Dialog().ok(
                                    g.ADDON_NAME, g.get_language_string(30373)
                                )
                        if method_class.refresh_token is not None:
                            return func(*args, **kwargs)

            g.log(
                "Trakt returned a {} ({}): while requesting {}".format(
                    response.status_code,
                    TRAKT_STATUS_CODES[response.status_code],
                    response.url,
                ),
                "error",
            )
            g.log(response.request.headers)

            return response
        except requests.exceptions.ConnectionError as e:
            _log_connection_error(args, kwargs, e)
            raise
        except Exception as e:
            _connection_failure_dialog()
            _log_connection_error(args, kwargs, e)
            raise

    return wrapper


class TraktAPI(ApiBase):
    """
    Class to handle interactions with Trakt API
    """

    ApiUrl = "https://api.trakt.tv/"
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 503, 504, 520, 521, 522, 524],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    _threading_lock = threading.Lock()

    gmt_timezone = pytz.timezone('UTC')
    local_timezone = tools.local_timezone()
    username_setting_key = "trakt.username"

    def __init__(self):
        self.client_id = g.get_setting(
            "trakt.clientid",
            "0c9a30819e4af6ffaf3b954cbeae9b54499088513863c03c02911de00ac2de79",
        )
        self.client_secret = g.get_setting(
            "trakt.secret",
            "bf02417f27b514cee6a8d135f2ddc261a15eecfb6ed6289c36239826dcdd1842",
        )
        self.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        self.access_token = g.get_setting("trakt.auth")
        self.refresh_token = g.get_setting("trakt.refresh")
        self.token_expires = g.get_float_setting("trakt.expires")
        self.default_limit = g.get_int_setting("item.limit")
        self.username = g.get_setting(self.username_setting_key)
        self.try_refresh_token()
        self.progress_dialog = xbmcgui.DialogProgress()
        self.language = g.get_language_code()
        self.country = g.get_language_code(True).split("-")[-1].lower()

        self.meta_hash = tools.md5_hash((self.language, self.ApiUrl, self.username))

        self.TranslationNormalization = [
            ("title", ("title", "originaltitle", "sorttitle"), None),
            ("language", "language", None),
            ("overview", ("plot", "plotoutline"), None),
        ]

        self.Normalization = tools.extend_array(
            [
                ("certification", "mpaa", None),
                ("genres", "genre", None),
                (("ids", "imdb"), ("imdbnumber", "imdb_id"), None),
                (("ids", "trakt"), "trakt_id", None),
                (("ids", "slug"), "trakt_slug", None),
                (("ids", "tvdb"), "tvdb_id", None),
                (("ids", "tmdb"), "tmdb_id", None),
                ("id", "playback_id", None),
                (("show", "ids", "trakt"), "trakt_show_id", None),
                ("network", "studio", None),
                ("runtime", "duration", lambda d: d * 60),
                ("progress", "percentplayed", None),
                (
                    None,
                    "resumetime",
                    (
                        ("runtime", "progress"),
                        lambda d, p: int((float(p / 100) * d))
                        if d is not None and p is not None
                        else 0,
                    ),
                ),
                ("updated_at", "dateadded", lambda t: TraktAPI.gmt_to_local(t)),
                ("last_updated_at", "dateadded", lambda t: TraktAPI.gmt_to_local(t)),
                ("collected_at", "collected_at", lambda t: TraktAPI.gmt_to_local(t)),
                (
                    "last_watched_at",
                    "last_watched_at",
                    lambda t: TraktAPI.gmt_to_local(t),
                ),
                ("paused_at", "paused_at", lambda t: TraktAPI.gmt_to_local(t)),
                (
                    "rating",
                    "rating",
                    lambda t: tools.safe_round(tools.get_clean_number(t), 2),
                ),
                ("votes", "votes", lambda t: tools.get_clean_number(t)),
                (
                    None,
                    "rating.trakt",
                    (
                        ("rating", "votes"),
                        lambda r, v: {
                            "rating": tools.safe_round(tools.get_clean_number(r), 2),
                            "votes": tools.get_clean_number(v),
                        },
                    ),
                ),
                ("tagline", "tagline", None),
                (
                    "trailer",
                    "trailer",
                    lambda t: tools.youtube_url.format(t.split("?v=")[-1])
                    if t
                    else None,
                ),
                ("type", "mediatype", lambda t: t if "show" not in t else "tvshow"),
                ("available_translations", "available_translations", None),
                ("score", "score", None),
                ("action", "action", None),
                ("added", "added", None),
                ("rank", "rank", None),
                ("listed_at", "listed_at", None),
                (
                    "country",
                    "country_origin",
                    lambda t: t.upper() if t is not None else None,
                ),
            ],
            self.TranslationNormalization,
        )

        self.MoviesNormalization = tools.extend_array(
            [
                ("plays", "playcount", None),
                ("year", "year", None),
                ("released", ("premiered", "aired"), lambda t: tools.validate_date(t)),
            ],
            self.Normalization,
        )

        self.ShowNormalization = tools.extend_array(
            [
                ("first_aired", "year", lambda t: TraktAPI.gmt_to_local(t)[:4]),
                ("title", "tvshowtitle", None),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: TraktAPI.gmt_to_local(t),
                ),
                ("status", "status", None),
                ("status", "is_airing", lambda t: not t == "ended"),
            ],
            self.Normalization,
        )

        self.SeasonNormalization = tools.extend_array(
            [
                ("number", ("season", "sortseason"), None),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: TraktAPI.gmt_to_local(t),
                ),
                ("episode_count", "episode_count", None),
                ("aired_episodes", "aired_episodes", None),
            ],
            self.Normalization,
        )

        self.EpisodeNormalization = tools.extend_array(
            [
                ("number", ("episode", "sortepisode"), None),
                ("season", ("season", "sortseason"), None),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: TraktAPI.gmt_to_local(t),
                ),
                ("collected_at", "collected", lambda t: 1),
                ("plays", "playcount", None),
            ],
            self.Normalization,
        )

        self.ListNormalization = [
            ("updated_at", "dateadded", lambda t: TraktAPI.gmt_to_local(t)),
            (("ids", "trakt"), "trakt_id", None),
            (("ids", "slug"), "slug", None),
            ("sort_by", "sort_by", None),
            ("sort_how", "sort_how", None),
            (("user", "ids", "slug"), "username", None),
            ("name", ("name", "title"), None),
            ("type", "mediatype", None),
        ]

        self.MixedEpisodeNormalization = [
            (("show", "ids", "trakt"), "trakt_show_id", None),
            (("episode", "ids", "trakt"), "trakt_id", None),
            ("show", "show", None),
            ("episode", "episode", None),
        ]

        self.MetaObjects = {
            "movie": self.MoviesNormalization,
            "list": self.ListNormalization,
            "show": self.ShowNormalization,
            "season": self.SeasonNormalization,
            "episode": self.EpisodeNormalization,
            "mixedepisode": self.MixedEpisodeNormalization,
        }

        self.MetaCollections = ("movies", "shows", "seasons", "episodes")

    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "trakt-api-key": self.client_id,
            "trakt-api-version": "2",
            "User-Agent": "{} - {}".format(g.ADDON_NAME, g.VERSION)
        }
        if self.access_token:
            headers["Authorization"] = "Bearer {}".format(self.access_token)
        return headers

    def revoke_auth(self):
        """
        Revokes current authorisation if present
        :return:
        """
        url = "oauth/revoke"
        post_data = {"token": self.access_token}
        if self.access_token:
            self.post(url, post_data)
        self._save_settings(
            {
                "access_token": None,
                "refresh_token": None,
                "expires_in": 0,
                "created_at": 0,
            }
        )
        g.set_setting(self.username_setting_key, None)
        from resources.lib.database.trakt_sync import activities

        activities.TraktSyncDatabase().clear_user_information()
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30022))

    def auth(self):
        """
        Performs OAuth with Trakt
        :return: None
        """
        self.username = None
        response = self.post("oauth/device/code", data={"client_id": self.client_id})
        if not response.ok:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30178))
            return
        try:
            response = response.json()
            user_code = response["user_code"]
            device = response["device_code"]
            interval = int(response["interval"])
            expiry = int(response["expires_in"])
            token_ttl = int(response["expires_in"])
        except (KeyError, ValueError):
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30024))
            raise

        tools.copy2clip(user_code)
        self.progress_dialog.create(
            g.ADDON_NAME + ": " + g.get_language_string(30023),
            tools.create_multiline_message(
                line1=g.get_language_string(30019).format(
                    g.color_string(g.color_string("https://trakt.tv/activate"))
                ),
                line2=g.get_language_string(30020).format(g.color_string(user_code)),
                line3=g.get_language_string(30048),
            ),
        )
        failed = False
        self.progress_dialog.update(100)
        while (
            not failed
            and self.username is None
            and not token_ttl <= 0
            and not self.progress_dialog.iscanceled()
        ):
            xbmc.sleep(1000)
            if token_ttl % interval == 0:
                failed = self._auth_poll(device)
            progress_percent = int(float((token_ttl * 100) / expiry))
            self.progress_dialog.update(progress_percent)
            token_ttl -= 1

        self.progress_dialog.close()

    def _auth_poll(self, device):
        response = self.post(
            "oauth/device/token",
            data={
                "code": device,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        if response.status_code == 200:
            response = response.json()
            self._save_settings(response)
            username = self.get_username()
            self.username = username
            self.progress_dialog.close()
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30300))

            # Synchronise Trakt Database with new user
            from resources.lib.database.trakt_sync import activities

            database = activities.TraktSyncDatabase()
            if database.activities["trakt_username"] != username:
                database.clear_user_information(
                    True if database.activities["trakt_username"] else False
                )
                database.flush_activities(False)
                database.set_trakt_user(username)
                xbmc.executebuiltin(
                    'RunPlugin("{}?action=syncTraktActivities")'.format(g.BASE_URL)
                )

            g.set_setting(self.username_setting_key, username)

        elif response.status_code == 404 or response.status_code == 410:
            self.progress_dialog.close()
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30024))
            return True
        elif response.status_code == 409:
            self.progress_dialog.close()
            return True
        elif response.status_code == 429:
            xbmc.sleep(1 * 1000)
        return False

    def _save_settings(self, response):
        if "access_token" in response:
            g.set_setting("trakt.auth", response["access_token"])
            self.access_token = response["access_token"]
        if "refresh_token" in response:
            g.set_setting("trakt.refresh", response["refresh_token"])
            self.refresh_token = response["refresh_token"]
        if "expires_in" in response and "created_at" in response:
            g.set_setting(
                "trakt.expires", str(response["created_at"] + response["expires_in"])
            )
            self.token_expires = float(response["created_at"] + response["expires_in"])

    def try_refresh_token(self, force=False):
        """
        Attempts to refresh current Trakt Auth Token
        :param force: Set to True to avoid Global Lock and forces refresh
        :return: None
        """
        if not force and (
            self.refresh_token is None or self.token_expires >= float(time.time())
        ):
            return
        with GlobalLock(
            self.__class__.__name__, self._threading_lock, True, self.access_token
        ) as lock:
            if lock.runned_once():
                return
            g.log("Trakt Token requires refreshing...")
            response = self.post(
                "/oauth/token",
                {
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                    "grant_type": "refresh_token",
                },
            ).json()
            self._save_settings(response)
            g.log("Refreshed Trakt Token")

    @trakt_guard_response
    def get(self, url, **params):
        """
        Performs a GET request to specified endpoint and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        timeout = params.pop("timeout", 10)
        self._try_add_default_paging(params)
        return self.session.get(
            tools.urljoin(self.ApiUrl, url),
            params=params,
            headers=self._get_headers(),
            timeout=timeout,
        )

    def _try_add_default_paging(self, params):
        if params.pop("no_paging", False):
            params.pop("limit", "")
            params.pop("page", "")
            return
        if "page" not in params and "limit" in params:
            params.update({"page": 1})
        if "page" in params and "limit" not in params:
            params.update({"limit": self.default_limit})

    def get_json(self, url, **params):
        """
        Performs a GET request to specified endpoint, sorts results and returns JSON response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: JSON response
        """
        response = self.get(url=url, **params)
        if response is None:
            return None
        try:
            return self._handle_response(
                self._try_sort(
                    response.headers.get("X-Sort-By"),
                    response.headers.get("X-Sort-How"),
                    response.json(),
                )
            )
        except (ValueError, AttributeError) as e:
            g.log(
                "Failed to receive JSON from Trakt response - response: {} - error - {}".format(
                    response, e
                ),
                "error",
            )
            return None

    def get_json_paged(self, url, **params):
        page = params.pop("page", 1) - 1
        limit = params.pop("limit", self.default_limit)
        result = self.get_json_cached(url, **params)
        if isinstance(result, (set, list)):
            return result[page * limit : (page * limit) + limit]
        return result

    @use_cache()
    def get_cached(self, url, **params):
        """
        Performs a GET request to specified endpoint, caches and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        return self.get(url, **params)

    @handle_single_item_or_list
    def _handle_response(self, item):
        item = self._try_detect_type(item)
        if item.get("type") == "castcrew":
            item.pop("type")
            item = self._handle_response(
                [i.get("movie", i.get("show")) for i in item.pop("cast", [])]
            )
            return item
        item = self._flatten_if_single_type(item)
        item = self._try_detect_type(item)
        if not item.get("type") or item.get("type") not in self.MetaObjects:
            return item
        if item["type"] == "mixedepisode":
            single_type = self._handle_single_type(item)
            [
                single_type.update({meta: self._handle_response(item.pop(meta, {}))})
                for meta in self.MetaObjects
                if meta in item
            ]
            single_type.update(item)
            return single_type
        return self._create_trakt_object(self._handle_single_type(item))

    @staticmethod
    def _create_trakt_object(item):
        result = {"trakt_object": {"info": item}}
        [
            result.update({key: value})
            for key, value in item.items()
            if key.endswith("_id")
        ]
        return result

    def _handle_single_type(self, item):
        translated = self._handle_translation(item)
        collections = {
            key: self._handle_response(translated[key])
            for key in self.MetaCollections
            if key in translated
        }
        normalized = self._normalize_info(self.MetaObjects[item["type"]], translated)
        normalized.update(collections)
        return normalized

    @staticmethod
    def _get_all_pages(func, url, **params):
        if "progress" in params:
            progress_callback = params.pop("progress")
        else:
            progress_callback = None
        response = func(url, **params)
        yield response
        if "X-Pagination-Page-Count" not in response.headers:
            return
        for i in range(2, int(response.headers["X-Pagination-Page-Count"]) + 1):
            params.update({"page": i})
            if "limit" not in params:
                params.update({"limit": int(response.headers["X-Pagination-Limit"])})
            if progress_callback is not None:
                progress_callback(
                    (i / (int(response.headers["X-Pagination-Page-Count"]) + 1)) * 100
                )
            params.update({"page": i})
            if "limit" not in params:
                params.update({"limit": int(response.headers["X-Pagination-Limit"])})
            yield func(url, **params)

    def get_all_pages_json(self, url, **params):
        """
        Iterates of all available pages from a trakt endpoint and yields the normalised results
        :param url: endpoint to call against
        :param params: any params for the url
        :return: Yields trakt pages
        """
        for response in self._get_all_pages(self.get_cached, url, **params):
            yield self._handle_response(
                self._try_sort(
                    response.headers.get("X-Sort-By"),
                    response.headers.get("X-Sort-How"),
                    response.json(),
                )
            )

    @use_cache()
    def get_json_cached(self, url, **params):
        """
        Performs a get request to endpoint, caches and returns a json response from a trakt enpoint
        :param url: URL endpoint to perform request to
        :param params: url parameters
        :return: json response from Trakt
        """
        return self.get_json(url, **params)

    @trakt_guard_response
    def post(self, url, data):
        """
        Performs a post request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :param data: POST Data to send to endpoint
        :return: requests response
        """
        return self.session.post(
            tools.urljoin(self.ApiUrl, url), json=data, headers=self._get_headers()
        )

    def post_json(self, url, data):
        """
        Performs a post request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :param data: POST Data to send to endpoint
        :return: JSON response from trakt endpoint
        """
        return self.post(url, data).json()

    @trakt_guard_response
    def delete_request(self, url):
        """
        Performs a delete request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :return: requests response
        """
        return self.session.delete(
            tools.urljoin(self.ApiUrl, url), headers=self._get_headers()
        )

    @staticmethod
    def _get_display_name(content_type):
        if content_type == "movie":
            return g.get_language_string(30290)
        else:
            return g.get_language_string(30312)

    def get_username(self):
        """
        Fetch current signed in users username
        :return: string username
        """
        user_details = self.get_json("users/me")
        return user_details["username"]

    def _try_sort(self, sort_by, sort_how, items):
        if not isinstance(items, (set, list)):
            return items

        if sort_by is None or sort_how is None:
            return items

        supported_sorts = [
            "added",
            "rank",
            "title",
            "released",
            "runtime",
            "popularity",
            "votes",
            "random",
            "runtime",
            "percentage",
        ]

        if sort_by not in supported_sorts:
            return items

        if sort_by == "added":
            items = sorted(items, key=lambda x: x.get("listed_at"))
        elif sort_by == "rank":
            items = sorted(items, key=lambda x: x.get("rank"), reverse=True)
        elif sort_by == "title":
            items = sorted(items, key=self._title_sorter)
        elif sort_by == "released":
            items = sorted(items, key=self._released_sorter)
        elif sort_by == "runtime":
            items = sorted(items, key=lambda x: x[x["type"]].get("runtime"))
        elif sort_by == "popularity":
            items = sorted(
                items,
                key=lambda x: float(
                    x[x["type"]].get("rating", 0) * int(x[x["type"]].get("votes", 0))
                ),
            )
        elif sort_by == "votes":
            items = sorted(items, key=lambda x: x[x["type"]].get("votes"))
        elif sort_by == "percentage":
            items = sorted(items, key=lambda x: x[x["type"]].get("rating"))
        elif sort_by == "random":
            import random

            random.shuffle(items)

        if sort_how == "desc":
            items.reverse()

        return items

    @staticmethod
    def _title_sorter(item):
        title = re.sub(r"^a |^the |^an ", "", item[item["type"]].get("title", "").lower())

        for i in tools.SORT_TOKENS:
            title.replace(i, "")
        return title

    @staticmethod
    def _released_sorter(item):
        released = item[item["type"]].get("released")
        if not released:
            released = item[item["type"]].get("first_aired")
        if not released:
            released = ""
        return released

    @handle_single_item_or_list
    def _flatten_if_single_type(self, item):
        media_type = item.get("type")
        if media_type and media_type in item:
            key = media_type
        else:
            keys = [meta for meta in self.MetaObjects if meta in item]
            if len(keys) == 1:
                key = keys[0]
            else:
                return item
        if isinstance(item[key], dict):
            item.update(item.pop(key))
            item.update({"type": key})
        return item

    @staticmethod
    @handle_single_item_or_list
    def _try_detect_type(item):
        item_types = [
            ("list", lambda x: "item_count" in x and "sort_by" in x),
            ("mixedepisode", lambda x: "show" in x and "episode" in x),
            ("show", lambda x: "show" in x),
            ("movie", lambda x: "movie" in x),
            (
                "movie",
                lambda x: "title" in x and "year" in x and x["ids"].get("tvdb") is None,
            ),
            ("show", lambda x: "title" in x and "year" in x and x["ids"].get("tvdb")),
            (
                "episode",
                lambda x: "number" in x
                and (
                    "season" in x
                    or ("last_watched_at" in x and "plays" in x)
                    or ("collected_at" in x)
                ),
            ),
            ("season", lambda x: "number" in x),
            ("castcrew", lambda x: "cast" in x and "crew" in x),
        ]
        for item_type in item_types:
            if item_type[1](item):
                item.update({"type": item_type[0]})
                break
        return item

    def get_show_aliases(self, trakt_show_id):
        """
        Fetches aliases for a show
        :param trakt_show_id: Trakt ID of show item
        :return: list of aliases
        """
        return sorted(
            {
                i["title"]
                for i in self.get_json("/shows/{}/aliases".format(trakt_show_id))
                if i["country"] == self.country
            }
        )

    def get_show_translation(self, trakt_id):
        return self._normalize_info(
            self.TranslationNormalization,
            self.get_json("shows/{}/translations/{}".format(trakt_id, self.language))[
                0
            ],
        )

    def get_movie_translation(self, trakt_id):
        return self._normalize_info(
            self.TranslationNormalization,
            self.get_json("movies/{}/translations/{}".format(trakt_id, self.language))[
                0
            ],
        )

    @handle_single_item_or_list_threaded
    def _handle_translation(self, item):
        if "language" in item and item.get("language") == self.language:
            return item

        if "translations" in item:
            for translation in item.get("translations", []):
                self._apply_translation(item, translation)
        return item

    def _apply_translation(self, item, translation):
        if not item or not translation:
            return
        if translation.get("language") == self.language:
            [
                item.update({k: v})
                for k, v in list(translation.items())
                if v
                and str(item.get("number", 0)) not in v
                and item.get("title")
                and str(item.get("number", 0)) not in item.get("title")
            ]

    @staticmethod
    def gmt_to_local(gmt_string):
        """
        Converts a GMT style datetime string to the localtimezone
        :param gmt_string: GMT datetime string
        :return: localized datetime string
        """
        if gmt_string is None:
            return None

        gmt_string = tools.validate_date(gmt_string)

        if not gmt_string:
            return None

        gmt = tools.parse_datetime(gmt_string, tools.DATE_FORMAT, False)
        gmt = TraktAPI.gmt_timezone.localize(gmt)
        gmt = gmt.astimezone(TraktAPI.local_timezone)
        return gmt.strftime(tools.DATE_FORMAT)


class TraktManager(TraktAPI):
    """
    Handles manual user interactions to the Trakt API
    """

    def __init__(self, item_information):
        super(TraktManager, self).__init__()
        trakt_id = item_information["trakt_id"]
        item_type = item_information["action_args"]["mediatype"].lower()
        display_type = self._get_display_name(item_type)

        self._confirm_item_information(item_information)

        self.dialog_list = []

        self._handle_watched_options(item_information, item_type)
        self._handle_collected_options(item_information, trakt_id, display_type)
        self._handle_watchlist_options(item_type)

        standard_list = [
            g.get_language_string(30307),
            g.get_language_string(30308),
            g.get_language_string(30309).format(display_type),
            g.get_language_string(30310),
        ]

        for i in standard_list:
            self.dialog_list.append(i)

        self._handle_progress_option(item_type, trakt_id)

        selection = xbmcgui.Dialog().select(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            self.dialog_list,
        )

        if selection == -1:
            return

        thread = ThreadPool()

        options = {
            g.get_language_string(30301).format(display_type): {
                "method": self._add_to_collection,
                "info_key": "info",
            },
            g.get_language_string(30302).format(display_type): {
                "method": self._remove_from_collection,
                "info_key": "info",
            },
            g.get_language_string(30303): {
                "method": self._add_to_watchlist,
                "info_key": "info",
            },
            g.get_language_string(30304): {
                "method": self._remove_from_watchlist,
                "info_key": "info",
            },
            g.get_language_string(30305): {
                "method": self._mark_watched,
                "info_key": "info",
            },
            g.get_language_string(30306): {
                "method": self._mark_unwatched,
                "info_key": "info",
            },
            g.get_language_string(30307): {
                "method": self._add_to_list,
                "info_key": "info",
            },
            g.get_language_string(30308): {
                "method": self._remove_from_list,
                "info_key": "info",
            },
            g.get_language_string(30309).format(display_type): {
                "method": self._hide_item,
                "info_key": "action_args",
            },
            g.get_language_string(30310): {
                "method": self._refresh_meta_information,
                "info_key": "info",
            },
            g.get_language_string(30311): {
                "method": self._remove_playback_history,
                "info_key": "info",
            },
        }

        selected_option = self.dialog_list[selection]
        if selected_option not in options:
            return
        else:
            selected_option = options[selected_option]

        thread.put(
            selected_option["method"], item_information[selected_option["info_key"]]
        )
        thread.wait_completion()

    def _handle_watchlist_options(self, item_type):
        if item_type not in ["season", "episode"]:
            self.dialog_list += [
                g.get_language_string(30303),
                g.get_language_string(30304),
            ]

    def _handle_progress_option(self, item_type, trakt_id):
        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase

        if item_type not in ["show", "season"] and TraktSyncDatabase().get_bookmark(
            trakt_id
        ):
            self.dialog_list.append(g.get_language_string(30311))

    def _handle_collected_options(self, item_information, trakt_id, display_type):
        if item_information["info"]["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            collection = [
                i["trakt_id"] for i in TraktSyncDatabase().get_all_collected_movies()
            ]
            if trakt_id in collection:
                self.dialog_list.append(
                    g.get_language_string(30302).format(display_type)
                )
            else:
                self.dialog_list.append(
                    g.get_language_string(30301).format(display_type)
                )
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            collection = TraktSyncDatabase().get_collected_shows(force_all=True)
            collection = [i for i in collection if i is not None]
            collection = OrderedDict.fromkeys([i["trakt_id"] for i in collection])
            trakt_id = self._get_show_id(item_information["info"])
            if trakt_id in collection:
                self.dialog_list.append(
                    g.get_language_string(30302).format(display_type)
                )
            else:
                self.dialog_list.append(
                    g.get_language_string(30301).format(display_type)
                )

    def _handle_watched_options(self, item_information, item_type):
        if item_type in ["movie", "episode"]:
            if item_information["play_count"] > 0:
                self.dialog_list.append(g.get_language_string(30306))
            else:
                self.dialog_list.append(g.get_language_string(30305))
        else:
            if item_information.get("unwatched_episodes", 0) > 0:
                self.dialog_list.append(g.get_language_string(30305))
            else:
                self.dialog_list.append(g.get_language_string(30306))

    @staticmethod
    def _confirm_item_information(item_information):
        if item_information is None:
            raise TypeError("Invalid item information passed to Trakt Manager")

    @staticmethod
    def _refresh_meta_information(trakt_object):
        from resources.lib.database import trakt_sync

        trakt_sync.TraktSyncDatabase().clear_specific_item_meta(
            trakt_object["trakt_id"], trakt_object["mediatype"]
        )
        g.container_refresh()
        g.trigger_widget_refresh()

    @staticmethod
    def _confirm_marked_watched(response, type):
        if response["added"][type] > 0:
            return True
        else:
            g.notification(
                "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
                g.get_language_string(30314),
            )
            g.log("Failed to mark item as watched\nTrakt Response: {}".format(response))

            return False

    @staticmethod
    def _confirm_marked_unwatched(response, type):

        if response["deleted"][type] > 0:
            return True
        else:
            g.notification(
                "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
                g.get_language_string(30314),
            )
            g.log(
                "Failed to mark item as unwatched\nTrakt Response: {}".format(response)
            )
            return False

    @staticmethod
    def _info_to_trakt_object(item_information, force_show=False):
        if force_show and item_information["mediatype"] in ("season", "episode"):
            ids = [{"ids": {"trakt": item_information["trakt_show_id"]}}]
            return {"shows": ids}
        ids = [{"ids": {"trakt": item_information["trakt_id"]}}]
        if item_information["mediatype"] == "movie":
            return {"movies": ids}
        elif item_information["mediatype"] == "season":
            return {"seasons": ids}
        elif item_information["mediatype"] == "tvshow":
            return {"shows": ids}
        elif item_information["mediatype"] == "episode":
            return {"episodes": ids}

    @staticmethod
    def _get_show_id(item_information):
        if item_information["mediatype"] != "tvshow":
            trakt_id = item_information["trakt_show_id"]
        else:
            trakt_id = item_information["trakt_id"]
        return trakt_id

    def _mark_watched(self, item_information, silent=False):

        response = self.post_json(
            "sync/history", self._info_to_trakt_object(item_information)
        )

        if item_information["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            if not self._confirm_marked_watched(response, "movies"):
                return
            TraktSyncDatabase().mark_movie_watched(item_information["trakt_id"])
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            if not self._confirm_marked_watched(response, "episodes"):
                return
            if item_information["mediatype"] == "episode":
                TraktSyncDatabase().mark_episode_watched(
                    item_information["trakt_show_id"],
                    item_information["season"],
                    item_information["episode"],
                )
            elif item_information["mediatype"] == "season":
                show_id = item_information["trakt_show_id"]
                season_no = item_information["season"]
                TraktSyncDatabase().mark_season_watched(show_id, season_no, 1)
            elif item_information["mediatype"] == "tvshow":
                TraktSyncDatabase().mark_show_watched(item_information["trakt_id"], 1)

        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            g.get_language_string(30315),
        )
        if not silent:
            g.container_refresh()
            g.trigger_widget_refresh()

    def _mark_unwatched(self, item_information):
        response = self.post_json(
            "sync/history/remove", self._info_to_trakt_object(item_information)
        )

        if item_information["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            if not self._confirm_marked_unwatched(response, "movies"):
                return
            TraktSyncDatabase().mark_movie_unwatched(item_information["trakt_id"])

        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            if not self._confirm_marked_unwatched(response, "episodes"):
                return
            if item_information["mediatype"] == "episode":
                TraktSyncDatabase().mark_episode_unwatched(
                    item_information["trakt_show_id"],
                    item_information["season"],
                    item_information["episode"],
                )
            elif item_information["mediatype"] == "season":
                show_id = item_information["trakt_show_id"]
                season_no = item_information["season"]
                TraktSyncDatabase().mark_season_watched(show_id, season_no, 0)
            elif item_information["mediatype"] == "tvshow":
                TraktSyncDatabase().mark_show_watched(item_information["trakt_id"], 0)

        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase

        TraktSyncDatabase().remove_bookmark(item_information["trakt_id"])

        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            g.get_language_string(30316),
        )
        g.container_refresh()
        g.trigger_widget_refresh()

    def _add_to_collection(self, item_information):
        self.post("sync/collection", self._info_to_trakt_object(item_information, True))

        if item_information["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            TraktSyncDatabase().mark_movie_collected(item_information["trakt_id"])
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            trakt_id = self._get_show_id(item_information)
            TraktSyncDatabase().mark_show_collected(trakt_id, 1)

        g.trigger_widget_refresh()
        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            g.get_language_string(30317),
        )

    def _remove_from_collection(self, item_information):

        self.post(
            "sync/collection/remove", self._info_to_trakt_object(item_information, True)
        )

        if item_information["mediatype"] == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            TraktSyncDatabase().mark_movie_uncollected(item_information["trakt_id"])
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            trakt_id = self._get_show_id(item_information)
            TraktSyncDatabase().mark_show_collected(trakt_id, 0)

        g.container_refresh()
        g.trigger_widget_refresh()
        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            g.get_language_string(30318),
        )

    def _add_to_watchlist(self, item_information):
        self.post("sync/watchlist", self._info_to_trakt_object(item_information, True))
        g.trigger_widget_refresh()
        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            g.get_language_string(30319),
        )

    def _remove_from_watchlist(self, item_information):
        self.post(
            "sync/watchlist/remove", self._info_to_trakt_object(item_information, True)
        )
        g.container_refresh()
        g.trigger_widget_refresh()
        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            g.get_language_string(30320),
        )

    def _add_to_list(self, item_information):
        from resources.lib.modules.metadataHandler import MetadataHandler

        get = MetadataHandler.get_trakt_info
        lists = self.get_json("users/me/lists")
        selection = xbmcgui.Dialog().select(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30323)),
            [get(i, "name") for i in lists],
        )
        if selection == -1:
            return
        selection = lists[selection]
        self.post_json(
            "users/me/lists/{}/items".format(selection["trakt_id"]),
            self._info_to_trakt_object(item_information, True),
        )
        g.trigger_widget_refresh()
        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            g.get_language_string(30321).format(get(selection, "name")),
        )

    def _remove_from_list(self, item_information):
        from resources.lib.modules.metadataHandler import MetadataHandler

        get = MetadataHandler.get_trakt_info
        lists = self.get_json("users/me/lists")
        selection = xbmcgui.Dialog().select(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30323)),
            [get(i, "name") for i in lists],
        )
        if selection == -1:
            return
        selection = lists[selection]
        self.post_json(
            "users/me/lists/{}/items/remove".format(selection["trakt_id"]),
            self._info_to_trakt_object(item_information, True),
        )
        g.container_refresh()
        g.trigger_widget_refresh()
        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30313)),
            g.get_language_string(30322).format(get(selection, "name")),
        )

    def _hide_item(self, item_information):
        from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase

        sections = ["progress_watched", "calendar"]
        sections_display = [g.get_language_string(30324), g.get_language_string(30325)]
        selection = xbmcgui.Dialog().select(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30326)),
            sections_display,
        )
        if selection == -1:
            return
        section = sections[selection]

        self.post_json(
            "users/hidden/{}".format(section),
            self._info_to_trakt_object(item_information, True),
        )

        if item_information["mediatype"] == "movie":
            TraktSyncDatabase().add_hidden_item(
                item_information["trakt_id"], "movie", section
            )
        else:
            TraktSyncDatabase().add_hidden_item(
                item_information["trakt_id"], "tvshow", section
            )

        g.container_refresh()
        g.trigger_widget_refresh()
        g.notification(
            g.ADDON_NAME,
            g.get_language_string(30327).format(sections_display[selection]),
        )

    def _remove_playback_history(self, item_information):
        media_type = "movie"

        if item_information["mediatype"] != "movie":
            media_type = "episode"

        progress = self.get_json("sync/playback/{}".format(media_type + "s"))
        if len(progress) == 0:
            return
        if media_type == "movie":
            progress_ids = [
                i["playback_id"]
                for i in progress
                if i["trakt_id"] == item_information["trakt_id"]
            ]
        else:
            progress_ids = [
                i["id"]
                for i in progress
                if i["episode"]["trakt_id"] == item_information["trakt_id"]
            ]

        for i in progress_ids:
            self.delete_request("sync/playback/{}".format(i))

        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase

        TraktSyncDatabase().remove_bookmark(item_information["trakt_id"])

        g.container_refresh()
        g.trigger_widget_refresh()
        g.notification(g.ADDON_NAME, g.get_language_string(30328))
