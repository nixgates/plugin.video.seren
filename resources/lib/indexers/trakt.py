import contextlib
import time
from functools import cached_property
from functools import wraps
from urllib import parse

import xbmc
import xbmcgui

from . import valid_id_or_none
from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import ApiBase
from resources.lib.indexers.apibase import handle_single_item_or_list
from resources.lib.modules.exceptions import AuthFailure
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g

CLOUDFLARE_ERROR_MSG = "Service Unavailable - Cloudflare error"

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
    423: "Locked User Account - Contact Trakt support",
    426: "VIP Only - user must upgrade to VIP",
    429: "Rate Limit Exceeded",
    500: "Server Error - please open a support issue",
    502: "Service Unavailable - server overloaded (try again in 30s)",
    503: "Service Unavailable - server overloaded (try again in 30s)",
    504: "Service Unavailable - server overloaded (try again in 30s)",
    520: CLOUDFLARE_ERROR_MSG,
    521: CLOUDFLARE_ERROR_MSG,
    522: CLOUDFLARE_ERROR_MSG,
    524: CLOUDFLARE_ERROR_MSG,
    530: CLOUDFLARE_ERROR_MSG,
}


def _log_connection_error(args, kwarg, e):
    g.log(f"Connection Error to Trakt: {args} - {kwarg}", "error")
    g.log(e, "error")


def _connection_failure_dialog():
    if (
        g.get_float_setting("general.trakt.failure.timeout") + (2 * 60 * (60 * 60)) < time.time()
        and not xbmc.Player().isPlaying()
    ):
        xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30024).format("Trakt"))
        g.set_setting("general.trakt.failure.timeout", str(time.time()))


def _reset_trakt_auth(notify=True):
    settings = ["trakt.refresh", "trakt.auth", "trakt.expires", "trakt.username"]
    for i in settings:
        g.clear_setting(i)
    if notify:
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30536))


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
        method_class._load_settings()
        import requests

        try:
            response = func(*args, **kwargs)
            if response.status_code in [200, 201, 204]:
                return response

            if response.status_code == 400 and response.url == "https://api.trakt.tv/oauth/device/token":
                return response
            if response.status_code == 400 and response.url == "https://api.trakt.tv/oauth/token":
                _reset_trakt_auth()
                raise AuthFailure("Unable to refresh Trakt auth")

            if response.status_code == 403:
                g.log("Trakt: invalid API key or unapproved app, resetting auth", "error")
                _reset_trakt_auth()
                g.cancel_directory()
                return None

            if response.status_code == 401:
                import inspect

                if inspect.stack(1)[1][3] == "try_refresh_token":
                    xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30340))
                    g.log(
                        "Attempts to refresh Trakt token have failed. User intervention is required",
                        "error",
                    )
                else:
                    with contextlib.suppress(RanOnceAlready):
                        with GlobalLock("trakt.oauth", run_once=True, check_sum=method_class.access_token):
                            if method_class.refresh_token is not None:
                                method_class.try_refresh_token(True)
                            if method_class.refresh_token is None and method_class.username is not None:
                                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30340))
                    if method_class.refresh_token is not None:
                        return func(*args, **kwargs)

            if response.status_code == 423:
                xbmcgui.Dialog().notification(g.ADDON_NAME, TRAKT_STATUS_CODES.get(response.status_code))
                g.log(
                    "Locked User Account - Contact Trakt support",
                    "error",
                )

            g.log(
                f"Trakt returned a {response.status_code} "
                f"({TRAKT_STATUS_CODES.get(response.status_code, '*Unknown status code*')}): "
                f"while requesting {response.url}",
                "error",
            )

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

    username_setting_key = "trakt.username"

    TranslationNormalization = [
        ("title", ("title", "originaltitle", "sorttitle"), None),
        ("language", "language", None),
        ("overview", ("plot", "plotoutline"), None),
    ]

    ReleaseNormalization = [
        ("country", "country", lambda c: c.upper()),
        ("release_date", "release_date", lambda rd: g.validate_date(rd)),
        ("release_type", "release_type", None),
        ("certification", "mpaa", None),
    ]

    UserRatingNormalization = [
        (
            "rating",
            "user_rating",
            lambda t: tools.safe_round(tools.get_clean_number(t), 2),
        ),
        ("rated_at", "rated_at", lambda t: g.validate_date(t)),
    ]

    PlayBackNormalization = [
        ("progress", "percentplayed", None),
        ("paused_at", "paused_at", lambda t: g.validate_date(t)),
        ("id", "playback_id", None),
    ]

    PlayBackHistoryNormalization = [
        ("action", "action", None),
        ("watched_at", "watched_at", lambda t: g.validate_date(t)),
        ("id", "playback_id", None),
    ]

    CalendarNormalization = [("first_aired", "first_aired", lambda t: g.validate_date(t))]

    Normalization = tools.extend_array(
        [
            ("certification", "mpaa", None),
            ("genres", "genre", None),
            (("ids", "imdb"), ("imdbnumber", "imdb_id"), lambda i: valid_id_or_none(i)),
            (("ids", "trakt"), "trakt_id", None),
            (("ids", "slug"), "trakt_slug", None),
            (("ids", "tvdb"), "tvdb_id", lambda i: valid_id_or_none(i)),
            (("ids", "tmdb"), "tmdb_id", lambda i: valid_id_or_none(i)),
            ("playback_id", "playback_id", None),
            (("show", "ids", "trakt"), "trakt_show_id", None),
            ("network", "studio", lambda n: [n]),
            ("runtime", "duration", lambda d: d * 60),
            ("progress", "percentplayed", None),
            ("percentplayed", "percentplayed", None),
            ("updated_at", "dateadded", lambda t: g.validate_date(t)),
            ("last_updated_at", "dateadded", lambda t: g.validate_date(t)),
            ("last_watched_at", "last_watched_at", lambda t: g.validate_date(t)),
            ("watched_at", "watched_at", lambda t: g.validate_date(t)),
            ("paused_at", "paused_at", lambda t: g.validate_date(t)),
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
                lambda t: tools.youtube_url.format(t.split("?v=")[-1]) if t else None,
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
            ("user_rating", "user_rating", None),
            ("rated_at", "rated_at", None),
        ],
        TranslationNormalization,
    )

    MoviesNormalization = tools.extend_array(
        [
            ("plays", "playcount", None),
            ("year", "year", None),
            ("released", ("premiered", "aired"), lambda t: g.validate_date(t)),
            ("collected_at", "collected_at", lambda t: g.validate_date(t)),
        ],
        Normalization,
    )

    ShowNormalization = tools.extend_array(
        [
            ("status", "status", None),
            ("status", "is_airing", lambda t: not t == "ended"),
            ("title", "tvshowtitle", None),
            ("first_aired", "year", lambda t: g.validate_date(t)[:4] if g.validate_date(t) else None),
            (
                "first_aired",
                ("premiered", "aired"),
                lambda t: g.validate_date(t),
            ),
            ("last_collected_at", "last_collected_at", lambda t: g.validate_date(t)),
        ],
        Normalization,
    )

    SeasonNormalization = tools.extend_array(
        [
            ("number", ("season", "sortseason"), None),
            ("episode_count", "episode_count", None),
            ("aired_episodes", "aired_episodes", None),
            ("first_aired", "year", lambda t: g.validate_date(t)[:4] if g.validate_date(t) else None),
            (
                "first_aired",
                ("premiered", "aired"),
                lambda t: g.validate_date(t),
            ),
            ("last_collected_at", "last_collected_at", lambda t: g.validate_date(t)),
        ],
        Normalization,
    )

    EpisodeNormalization = tools.extend_array(
        [
            ("number", ("episode", "sortepisode"), None),
            ("season", ("season", "sortseason"), None),
            ("collected_at", "collected", lambda t: 1),
            ("plays", "playcount", None),
            ("first_aired", "year", lambda t: g.validate_date(t)[:4] if g.validate_date(t) else None),
            (
                "first_aired",
                ("premiered", "aired"),
                lambda t: g.validate_date(t),
            ),
            ("collected_at", "collected_at", lambda t: g.validate_date(t)),
        ],
        Normalization,
    )

    ListNormalization = [
        ("updated_at", "dateadded", lambda t: g.validate_date(t)),
        (("ids", "trakt"), "trakt_id", None),
        (("ids", "slug"), "slug", None),
        ("sort_by", "sort_by", None),
        ("sort_how", "sort_how", None),
        (("user", "ids", "slug"), "username", None),
        ("name", ("name", "title"), None),
        ("type", "mediatype", None),
    ]

    MixedEpisodeNormalization = [
        (("show", "ids", "trakt"), "trakt_show_id", None),
        (("episode", "ids", "trakt"), "trakt_id", None),
    ]

    MixedSeasonNormalization = [
        (("show", "ids", "trakt"), "trakt_show_id", None),
        (("season", "ids", "trakt"), "trakt_id", None),
    ]

    MetaNormalization = {
        "movie": MoviesNormalization,
        "list": ListNormalization,
        "show": ShowNormalization,
        "season": SeasonNormalization,
        "episode": EpisodeNormalization,
        "mixedepisode": MixedEpisodeNormalization,
        "mixedseason": MixedSeasonNormalization,
        "playback": PlayBackNormalization,
        "playbackhistory": PlayBackHistoryNormalization,
        "user_rating": UserRatingNormalization,
        "calendar": CalendarNormalization,
        "releases": ReleaseNormalization,
    }

    MetaObjects = ("movie", "tvshow", "show", "season", "episode", "list")

    MetaCollections = ("movies", "shows", "seasons", "episodes", "cast")

    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0
        self.username = None
        self._load_settings()
        self.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        self.try_refresh_token()
        self.language = g.get_language_code()
        self.country = g.get_language_code(True).split("-")[-1].lower()

    @cached_property
    def meta_hash(self):
        return tools.md5_hash((self.language, self.ApiUrl, self.username))

    @cached_property
    def trakt_db(self):
        from resources.lib.database import trakt_sync

        return trakt_sync.TraktSyncDatabase()

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(
            total=4,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524, 530],
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    # region Auth
    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "trakt-api-key": self.client_id,
            "trakt-api-version": "2",
            "User-Agent": g.USER_AGENT,
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def revoke_auth(self):
        """
        Revokes current authorisation if present
        :return:
        """
        post_data = {"token": self.access_token, "client_id": self.client_id, "client_secret": self.client_secret}
        if self.access_token:
            url = "oauth/revoke"
            self.post(url, post_data)
        _reset_trakt_auth(notify=False)
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0
        self.username = None
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30021))

    def auth(self):
        """
        Performs OAuth with Trakt
        :return: None
        """
        self.username = None
        response = self.post("oauth/device/code", data={"client_id": self.client_id})
        if not response.ok:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30162))
            return
        try:
            response = response.json()
            user_code = response["user_code"]
            device = response["device_code"]
            interval = int(response["interval"])
            expiry = int(response["expires_in"])
            token_ttl = int(response["expires_in"])
        except (KeyError, ValueError):
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30023))
            raise

        tools.copy2clip(user_code)
        failed = False
        try:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(
                f"{g.ADDON_NAME}: {g.get_language_string(30022)}",
                tools.create_multiline_message(
                    line1=g.get_language_string(30018).format(g.color_string("https://trakt.tv/activate")),
                    line2=g.get_language_string(30019).format(g.color_string(user_code)),
                    line3=g.get_language_string(30047),
                ),
            )
            progress_dialog.update(100)
            while not failed and self.username is None and token_ttl > 0 and not progress_dialog.iscanceled():
                xbmc.sleep(1000)
                if token_ttl % interval == 0:
                    failed = self._auth_poll(device)
                progress_percent = int(float((token_ttl * 100) / expiry))
                progress_dialog.update(progress_percent)
                token_ttl -= 1

            progress_dialog.close()
        finally:
            del progress_dialog

        if not failed:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30273))
            self._sync_trakt_user_data_if_required()

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
            return self._auth_success(response)
        elif response.status_code in [404, 410]:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30023))
            return True
        elif response.status_code == 409:
            return True
        elif response.status_code == 429:
            xbmc.sleep(1 * 1000)
        return False

    def _auth_success(self, response):
        response = response.json()
        self._save_settings(response)
        username = self.get_username()
        self.username = username
        g.set_setting(self.username_setting_key, username)
        return False

    def _sync_trakt_user_data_if_required(self):
        # Synchronise Trakt Database with new user
        from resources.lib.database.trakt_sync import activities

        database = activities.TraktSyncDatabase()
        if database.activities["trakt_username"] != self.username:
            database.clear_user_information(bool(database.activities["trakt_username"]))
            database.flush_activities(False)
            database.set_trakt_user(self.username)
            xbmc.executebuiltin(f'RunPlugin("{g.BASE_URL}?action=syncTraktActivities")')

    def try_refresh_token(self, force=False):
        """
        Attempts to refresh current Trakt Auth Token
        :param force: Set to True to force refresh
        :return: None
        """
        if not self.refresh_token:
            return
        if not force and self.token_expires > float(time.time()):
            return

        try:
            with GlobalLock(self.__class__.__name__, True, self.access_token):
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
        except RanOnceAlready:
            self._load_settings()
            return

    # endregion

    # region settings
    def _save_settings(self, response):
        if "access_token" in response:
            g.set_setting("trakt.auth", response["access_token"])
            self.access_token = response["access_token"]
        if "refresh_token" in response:
            g.set_setting("trakt.refresh", response["refresh_token"])
            self.refresh_token = response["refresh_token"]
        if "expires_in" in response and "created_at" in response:
            g.set_setting("trakt.expires", str(response["created_at"] + response["expires_in"]))
            self.token_expires = float(response["created_at"] + response["expires_in"])

    def _load_settings(self):
        self.client_id = g.get_setting(
            "trakt.clientid",
            "0c9a30819e4af6ffaf3b954cbeae9b54499088513863c03c02911de00ac2de79",
        )
        self.client_secret = g.get_setting(
            "trakt.secret",
            "bf02417f27b514cee6a8d135f2ddc261a15eecfb6ed6289c36239826dcdd1842",
        )
        self.access_token = g.get_setting("trakt.auth")
        self.refresh_token = g.get_setting("trakt.refresh")
        self.token_expires = g.get_float_setting("trakt.expires")
        self.default_limit = g.get_int_setting("item.limit")
        self.username = g.get_setting(self.username_setting_key)

    # endregion

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
        self._clean_params(params)
        return self.session.get(
            parse.urljoin(self.ApiUrl, url),
            params=params,
            headers=self._get_headers(),
            timeout=timeout,
        )

    def _try_add_default_paging(self, params):
        if "page" not in params and "limit" in params:
            params.update({"page": 1})
        if "page" in params and "limit" not in params:
            params.update({"limit": self.default_limit})

    @staticmethod
    def _clean_params(params):
        if "hide_watched" in params:
            del params["hide_watched"]
        if "hide_unaired" in params:
            del params["hide_unaired"]
        if "no_paging" in params:
            del params["no_paging"]
        if "pull_all" in params:
            del params["pull_all"]

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
                f"Failed to receive JSON from Trakt response - response: {response} - error - {e}",
                "error",
            )
            return None

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
        item = self._try_flatten_if_single_type(item)

        if isinstance(item, list):
            return self._handle_response(item)

        if not item.get("type") or item.get("type") not in self.MetaNormalization:
            return item

        if item["type"].startswith("mixed"):
            return self._handle_mixed_type(item)

        result = self._handle_single_type(item)
        return (
            self._create_trakt_object(result)
            if result.get("type", result.get("mediatype")) in self.MetaObjects
            else result
        )

    @staticmethod
    def _create_trakt_object(item):
        result = {"trakt_object": {"info": item}}
        [result.update({key: value}) for key, value in item.items() if key.endswith("_id")]
        return result

    def _handle_single_type(self, item):
        translated = self._handle_translation(item)
        collections = {key: self._handle_response(translated[key]) for key in self.MetaCollections if key in translated}
        normalized = self._normalize_info(self.MetaNormalization[item["type"]], translated)
        normalized.update(collections)
        return normalized

    def _handle_mixed_type(self, item):
        mixed_type = item["type"].replace("mixed", "")
        result = self._handle_single_type(item)
        [
            result.update({meta: self._handle_response(item.pop(meta, {}))})
            for meta in self.MetaNormalization
            if meta in item
        ]
        single_type = self._try_detect_type(item)
        single_type = self._handle_single_type(single_type)
        result.update(single_type)
        result[mixed_type]["trakt_object"]["info"].update(single_type)
        result[mixed_type]["trakt_object"]["info"].update({"trakt_show_id": result.get("trakt_show_id")})
        return result

    @staticmethod
    def _get_all_pages(func, url, **params):
        progress_callback = params.pop("progress", None)
        response = func(url, **params)
        yield response
        if "X-Pagination-Page-Count" not in response.headers:
            return
        for i in range(2, int(response.headers["X-Pagination-Page-Count"]) + 1):
            params["page"] = i
            if "limit" not in params:
                params["limit"] = int(response.headers["X-Pagination-Limit"])
            if callable(progress_callback):
                progress_callback(  # pylint: disable=not-callable
                    (i / (int(response.headers["X-Pagination-Page-Count"]) + 1)) * 100
                )
            yield func(url, **params)

    def get_all_pages_json(self, url, **params):
        """
        Iterates of all available pages from a trakt endpoint and yields the normalised results
        :param url: endpoint to call against
        :param params: any params for the url
        :return: Yields trakt pages
        """
        ignore_cache = params.pop("ignore_cache", False)
        get_method = self.get if ignore_cache else self.get_cached

        for response in self._get_all_pages(get_method, url, **params):
            if not response:
                return
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
        return self.session.post(parse.urljoin(self.ApiUrl, url), json=data, headers=self._get_headers())

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
        return self.session.delete(parse.urljoin(self.ApiUrl, url), headers=self._get_headers())

    def get_username(self):
        """
        Fetch current signed in users username
        :return: string username
        """
        user_details = self.get_json("users/me")
        return user_details["username"]

    # region Sorting
    def _try_sort(self, sort_by, sort_how, items):
        if not items or not isinstance(items, (set, list)):
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
            "watched",
            "collected",
            "my_rating",
        ]

        if sort_by not in supported_sorts:
            g.log(f"Error sorting trakt response: Unsupported sort_by ({sort_by})", "error")
            return items

        if sort_by == "added":
            items = sorted(items, key=lambda x: x.get("listed_at"))
        elif sort_by == "rank":
            items = sorted(items, key=lambda x: x.get("rank"))
        elif sort_by == "title":
            items = sorted(items, key=self._title_sorter)
        elif sort_by == "released":
            items = sorted(items, key=self._released_sorter)
        elif sort_by == "runtime":
            items = sorted(items, key=lambda x: x[x["type"]].get("runtime"))
        elif sort_by == "popularity":
            items = sorted(
                items,
                key=lambda x: float(x[x["type"]].get("rating", 0) * int(x[x["type"]].get("votes", 0))),
            )
        elif sort_by == "votes":
            items = sorted(items, key=lambda x: x[x["type"]].get("votes"))
        elif sort_by == "percentage":
            items = sorted(items, key=lambda x: x[x["type"]].get("rating"))
        elif sort_by == "random":
            import random

            random.shuffle(items)
        elif sort_by == "watched":
            items = self._watched_sort(items)
        elif sort_by == "collected":
            items = self._collected_sort(items)
        elif sort_by == "my_rating":
            items = self._rating_sort(items)

        if sort_how == "desc":
            items.reverse()

        return items

    @staticmethod
    def _title_sorter(item):
        return tools.SORT_TOKEN_REGEX.sub("", item[item["type"]].get("title", "").lower())

    @staticmethod
    def _released_sorter(item):
        if item_type := item.get("type"):
            return item[item_type].get("released") or item[item_type].get("first_aired") or ""
        return ""

    def __get_sorted_items(self, sort_field, item_type, items, default_sort_key):
        sort_items = self.trakt_db.fetchall(
            f"""
            SELECT trakt_id, COALESCE({sort_field}, {repr(default_sort_key)}) AS {sort_field}
            FROM {item_type}s
            WHERE trakt_id IN ({','.join(map(lambda i: str(i[item_type]['ids']['trakt']), items))})
            """
        )
        sort_items = {i['trakt_id']: i[sort_field] for i in sort_items}
        return sorted(items, key=lambda i: sort_items.get(i[item_type]["ids"]["trakt"], default_sort_key))

    def _watched_sort(self, items):
        item_type = items[0]["type"]
        return self.__get_sorted_items("last_watched_at", item_type, items, "")

    def _collected_sort(self, items):
        item_type = items[0]["type"]
        collected_field = "last_collected_at" if item_type in ["show", "season"] else "collected_at"
        return self.__get_sorted_items(collected_field, item_type, items, "")

    def _rating_sort(self, items):
        item_type = items[0]["type"]
        return self.__get_sorted_items("user_rating", item_type, items, 0)

    # endregion

    @handle_single_item_or_list
    def _try_flatten_if_single_type(self, item):
        media_type = item.get("type")
        if media_type and media_type in item:
            key = media_type
        else:
            keys = [meta for meta in self.MetaNormalization if meta in item]
            if len(keys) == 1:
                key = keys[0]
            else:
                return item

        if isinstance(item[key], dict):
            single_item = item.pop(key)
            if media_type and media_type in self.MetaNormalization:
                item = self._normalize_info(self.MetaNormalization[media_type], item)
            item.update(single_item)
            item.update({"type": key})
        elif isinstance(item[key], list):
            return item[key]
        return item

    @handle_single_item_or_list
    def _try_detect_type(self, item):
        item_types = [
            ("list", lambda x: "item_count" in x and "sort_by" in x),
            ("mixedepisode", lambda x: "show" in x and "episode" in x),
            ("mixedseason", lambda x: "show" in x and "season" in x),
            (
                "movie",
                lambda x: "title" in x and "year" in x and "network" not in x,
            ),
            ("show", lambda x: "title" in x and "year" in x and "network" in x),
            (
                "episode",
                lambda x: "number" in x
                and ("season" in x or ("last_watched_at" in x and "plays" in x) or ("collected_at" in x)),
            ),
            ("season", lambda x: "number" in x),
            ("playback", lambda x: "paused_at" in x),
            ("playbackhistory", lambda x: "action" in x),
            ("user_rating", lambda x: "rated_at" in x),
            ("calendar", lambda x: "first_aired" in x),
            ("cast", lambda x: "cast" in x),
            ("genre", lambda x: "name" in x and "slug" in x),
            ("network", lambda x: "name" in x),
            ("alias", lambda x: "title" in x and "country" in x),
            ("translation", lambda x: "title" in x and "language" in x),
            ("people", lambda x: "character" in x and "characters" in x),
            ("anticipated", lambda x: "list_count" in x),
            ("box_office", lambda x: "revenue" in x),
            ("collected", lambda x: "watcher_count" in x and "collected_count" in x and "play_count" in x),
            ("lists", lambda x: "like_count" in x and "comment_count" in x),
            ("updated", lambda x: "updated_at" in x and ("movie" in x or "show" in x)),
            ("trending", lambda x: "watchers" in x),
            ("sync_activities", lambda x: "all" in x),
            ("sync_watched", lambda x: "last_watched_at" in x),
            ("sync_collected", lambda x: "last_collected_at" in x),
            ("releases", lambda x: "country" in x and "release_date" in x),
        ]
        for item_type in item_types:
            if item_type[1](item):
                item.update({"type": item_type[0]})
                break
        if "type" not in item:
            g.log(f"Error detecting trakt item type for: {item}", "error")
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
                for i in self.get_json_cached(f"/shows/{trakt_show_id}/aliases")
                if i["country"] in [self.country, 'us']
            }
        )

    def get_show_translation(self, trakt_id):
        return self._normalize_info(
            self.TranslationNormalization,
            self.get_json_cached(f"shows/{trakt_id}/translations/{self.language}")[0],
        )

    def get_movie_translation(self, trakt_id):
        return self._normalize_info(
            self.TranslationNormalization,
            self.get_json_cached(f"movies/{trakt_id}/translations/{self.language}")[0],
        )

    @handle_single_item_or_list
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

    def get_movie_release_info(self, trakt_id):
        release_list = self.get_json_cached(f"movies/{trakt_id}/releases")
        return {
            country.upper(): [i for i in release_list if i['country'] == country]
            for country in {c['country'] for c in release_list}
        }
