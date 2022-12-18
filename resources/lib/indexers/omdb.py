import re
from functools import cached_property
from functools import wraps

import xbmcgui

from . import valid_id_or_none
from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import ApiBase
from resources.lib.indexers.apibase import handle_single_item_or_list
from resources.lib.modules.globals import g

OMDB_STATUS_CODES = {
    200: "Success",
    400: "Bad Request ",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    429: "Rate Limit Exceeded",
    500: "Server Error",
    503: "Service Unavailable - server overloaded (try again in 30s)",
    504: "Service Unavailable - server overloaded (try again in 30s)",
}

REMOVE_TEXT_IN_BRACKETS_REGEX = re.compile(r"\(.*?\)")


def omdb_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        import requests

        try:
            response = func(*args, **kwarg)

            if response.status_code in [200, 201, 204]:
                return response

            g.log(
                f"OMDb returned a {response.status_code} ({OMDB_STATUS_CODES[response.status_code]}): while requesting "
                f"{'&'.join(x for x in response.url.split('&') if not x.lower().startswith('apikey'))}",
                "error",
            )

            return None
        except requests.exceptions.ConnectionError as e:
            g.log(f"Connection Error to OMDb: {args} - {kwarg}", "error")
            g.log(e, "error")
            return None
        except Exception:
            xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30024).format("OMDb"))
            if g.get_runtime_setting("run.mode") == "test":
                raise
            else:
                g.log_stacktrace()
            return None

    return wrapper


def wrap_omdb_object(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        return {"omdb_object": func(*args, **kwarg)}

    return wrapper


class OmdbApi(ApiBase):
    ApiUrl = "https://www.omdbapi.com/"

    def __init__(self):
        self.api_key = g.get_setting("omdb.apikey", None)
        self.omdb_support = bool(self.api_key)

        self.normalization = [
            ("@title", ("title", "sorttitle"), lambda d: None if self._is_value_none(d) else d),
            ("@rated", "mpaa", lambda d: None if self._is_value_none(d) else d),
            ("@released", ("premiered", "aired"), lambda d: None if self._is_value_none(d) else g.validate_date(d)),
            (
                "@runtime",
                "duration",
                lambda d: int(d[:-4]) * 60 if not self._is_value_none(d) and len(d) > 4 and d[:-4].isdigit() else None,
            ),
            (
                "@genre",
                "genre",
                lambda d: None if self._is_value_none(d) else sorted({x.strip() for x in d.split(",")}),
            ),
            (
                "@director",
                "director",
                lambda d: None
                if self._is_value_none(d)
                else sorted({REMOVE_TEXT_IN_BRACKETS_REGEX.sub("", x).strip() for x in d.split(",")}),
            ),
            (
                "@writer",
                "writer",
                lambda d: None
                if self._is_value_none(d)
                else sorted({REMOVE_TEXT_IN_BRACKETS_REGEX.sub("", x).strip() for x in d.split(",")}),
            ),
            ("@plot", ("plot", "overview", "plotoutline"), None),
            ("@country", "country", lambda d: None if self._is_value_none(d) else d),
            ("@imdbID", ("imdbnumber", "imdb_id"), lambda i: valid_id_or_none(i)),
            (
                None,
                "rating.imdb",
                (
                    ("@imdbRating", "@imdbVotes"),
                    lambda a, c: {
                        "rating": tools.safe_round(tools.get_clean_number(a), 2),
                        "votes": tools.get_clean_number(c),
                    }
                    if not self._is_value_none(a) and not self._is_value_none(c)
                    else None,
                ),
            ),
            ("@Production", "studio", lambda d: None if self._is_value_none(d) else d),
            ("@awards", "awards", lambda d: None if self._is_value_none(d) else d),
            (
                "@awards",
                "oscar_wins",
                lambda d: self._extract_awards(d, ("Won", "Oscar")),
            ),
            (
                "@awards",
                "oscar_nominations",
                lambda d: self._extract_awards(d, ("Nominated for", "Oscar")),
            ),
            (
                "@awards",
                "award_wins",
                lambda d: self._extract_awards(d, ("Another", "wins"), ("", "wins")),
            ),
            (
                "@awards",
                "award_nominations",
                lambda d: self._extract_awards(d, ("wins &", "nominations"), ("", "nominations")),
            ),
            ("@metascore", "metacritic_rating", lambda d: None if self._is_value_none(d) else d),
            ("@tomatoMeter", "rottentomatoes_rating", lambda d: None if self._is_value_none(d) else d),
            ("@tomatoImage", "rottentomatoes_image", lambda d: None if self._is_value_none(d) else d),
            (
                "@tomatoReviews",
                "rottentomatoes_reviewstotal",
                lambda d: None if self._is_value_none(d) else tools.get_clean_number(d),
            ),
            (
                "@tomatoFresh",
                "rottentomatoes_reviewsfresh",
                lambda d: None if self._is_value_none(d) else tools.get_clean_number(d),
            ),
            (
                "@tomatoRotten",
                "rottentomatoes_reviewsrotten",
                lambda d: None if self._is_value_none(d) else tools.get_clean_number(d),
            ),
            ("@tomatoConsensus", "rottentomatoes_consensus", lambda d: None if self._is_value_none(d) else d),
            ("@tomatoUserMeter", "rottentomatoes_usermeter", lambda d: None if self._is_value_none(d) else d),
            (
                "@tomatoUserReviews",
                "rottentomatoes_userreviews",
                lambda d: None if self._is_value_none(d) else tools.get_clean_number(d),
            ),
        ]

    @cached_property
    def meta_hash(self):
        return tools.md5_hash((self.omdb_support, self.ApiUrl))

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[500, 503, 504, 520, 521, 522, 524],
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    def _extract_awards(self, value, *params):
        if self._is_value_none(value):
            return None
        for i in params:
            exp = f"{i[0]}(.+?){i[1]}"
            try:
                result = re.search(exp, value)[1].strip()
                if not self._is_value_none(result):
                    return result
            except TypeError:
                continue
        return None

    @staticmethod
    def _is_value_none(value):
        return value in ["", "N/A", "0.0", "0", 0, 0.0, None]

    @omdb_guard_response
    def get(self, **params):
        params["tomatoes"] = "True"
        params["plot"] = "full"
        params["r"] = "xml"
        params["apikey"] = self.api_key
        timeout = params.pop("timeout", 10)
        return self.session.get(self.ApiUrl, params=params, timeout=timeout)

    @wrap_omdb_object
    def get_json(self, **params):
        from resources.lib.third_party import xml_to_dict
        from xml.parsers.expat import ExpatError  # pylint: disable=no-name-in-module

        response = self.get(**params)
        if response is None:
            return None
        try:
            if not response.content:
                return None
            parsed = xml_to_dict.parse(response.text)
            if parsed.get("root", {}).get("@response", {}) == "False":
                return None
            elif parsed.get("root", {}).get("error", {}):
                return None

            return self._handle_response(parsed.get("root", {}).get("movie"))
        except (ValueError, AttributeError, ExpatError):
            g.log_stacktrace()
            g.log(
                f"Failed to receive JSON from OMDb response - response: {response}",
                "error",
            )
            return None

    @handle_single_item_or_list
    def _handle_response(self, item):
        if item is None:
            return None
        item = self._try_detect_type(item)
        return {"info": self._normalize_info(self.normalization, item)}

    @use_cache()
    def get_json_cached(self, **params):
        return self.get_json(**params)

    @staticmethod
    @handle_single_item_or_list
    def _try_detect_type(item):
        if "type" in item:
            if item["type"] == "series":
                item.update({"mediatype": "tvshow"})
            else:
                item.update({"mediatype": item["type"]})
        return item
