# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import re
from collections import OrderedDict
from functools import wraps

import requests
import xbmcgui
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from resources.lib.third_party import xml_to_dict

try:
    import xml.etree.cElementTree as ElementTree
except:
    import xml.etree.ElementTree as ElementTree

from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import ApiBase, handle_single_item_or_list
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


def omdb_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        try:
            response = func(*args, **kwarg)

            if response.status_code in [200, 201, 204]:
                return response

            g.log(
                "OMDb returned a {} ({}): while requesting {}".format(
                    response.status_code,
                    OMDB_STATUS_CODES[response.status_code],
                    response.url,
                ),
                "error",
            )

            return None
        except requests.exceptions.ConnectionError as e:
            g.log("Connection Error to OMDb: {} - {}".format(args, kwarg), "error")
            g.log(e, "error")
            return None
        except:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME, g.get_language_string(30025).format("OMDb")
            )
            if g.get_global_setting("run.mode") == "test":
                raise
            return None

    return wrapper


def wrap_omdb_object(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        return {"omdb_object": func(*args, **kwarg)}

    return wrapper


class OmdbApi(ApiBase):
    ApiUrl = "https://www.omdbapi.com/"
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.1,
        status_forcelist=[500, 503, 504, 520, 521, 522, 524],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    def __init__(self):
        self.api_key = g.get_setting("omdb.apikey", None)
        self.omdb_support = False if not self.api_key else True
        self.meta_hash = tools.md5_hash((self.omdb_support, self.ApiUrl))

        self.normalization = [
            (
                "@title",
                ("title", "originaltitle", "sorttitle"),
                lambda d: d if not self._is_value_none(d) else None,
            ),
            ("@rated", "mpaa", lambda d: d if not self._is_value_none(d) else None),
            (
                "@released",
                ("premiered", "aired"),
                lambda d: tools.validate_date(d)
                if not self._is_value_none(d)
                else None,
            ),
            (
                "@runtime",
                "duration",
                lambda d: int(d[:-4]) * 60 if not self._is_value_none(d) else None,
            ),
            (
                "@genre",
                "genre",
                lambda d: sorted(
                    OrderedDict.fromkeys({x.strip() for x in d.split(",")})
                )
                if not self._is_value_none(d)
                else None,
            ),
            (
                "@director",
                "director",
                lambda d: sorted(
                    OrderedDict.fromkeys(
                        {re.sub(r"\(.*?\)", "", x).strip() for x in d.split(",")}
                    )
                )
                if not self._is_value_none(d)
                else None,
            ),
            (
                "@writer",
                "writer",
                lambda d: sorted(
                    OrderedDict.fromkeys(
                        {re.sub(r"\(.*?\)", "", x).strip() for x in d.split(",")}
                    )
                )
                if not self._is_value_none(d)
                else None,
            ),
            ("@plot", ("plot", "overview", "plotoutline"), None),
            (
                "@country",
                "country",
                lambda d: d if not self._is_value_none(d) else None,
            ),
            ("@imdbID", ("imdbnumber", "imdb_id"), None),
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
            (
                "@Production",
                "studio",
                lambda d: d if not self._is_value_none(d) else None,
            ),
            ("@awards", "awards", lambda d: d if not self._is_value_none(d) else None),
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
                lambda d: self._extract_awards(
                    d, ("wins &", "nominations"), ("", "nominations")
                ),
            ),
            (
                "@metascore",
                "metacritic_rating",
                lambda d: d if not self._is_value_none(d) else None,
            ),
            (
                "@tomatoMeter",
                "rottentomatoes_rating",
                lambda d: d if not self._is_value_none(d) else None,
            ),
            (
                "@tomatoImage",
                "rottentomatoes_image",
                lambda d: d if not self._is_value_none(d) else None,
            ),
            (
                "@tomatoReviews",
                "rottentomatoes_reviewstotal",
                lambda d: tools.get_clean_number(d)
                if not self._is_value_none(d)
                else None,
            ),
            (
                "@tomatoFresh",
                "rottentomatoes_reviewsfresh",
                lambda d: tools.get_clean_number(d)
                if not self._is_value_none(d)
                else None,
            ),
            (
                "@tomatoRotten",
                "rottentomatoes_reviewsrotten",
                lambda d: tools.get_clean_number(d)
                if not self._is_value_none(d)
                else None,
            ),
            (
                "@tomatoConsensus",
                "rottentomatoes_consensus",
                lambda d: d if not self._is_value_none(d) else None,
            ),
            (
                "@tomatoUserMeter",
                "rottentomatoes_usermeter",
                lambda d: d if not self._is_value_none(d) else None,
            ),
            (
                "@tomatoUserReviews",
                "rottentomatoes_userreviews",
                lambda d: tools.get_clean_number(d)
                if not self._is_value_none(d)
                else None,
            ),
        ]

    def _extract_awards(self, value, *params):
        try:
            if self._is_value_none(value):
                return None
        except AttributeError:
            return None
        for i in params:
            exp = i[0] + "(.+?)" + i[1]
            try:
                result = re.search(exp, value).group(1).strip()
                if not self._is_value_none(result):
                    return result
            except AttributeError:
                continue
        return None

    @staticmethod
    def _is_value_none(value):
        if value in ["N/A", "0.0", "0", 0, 0.0, None]:
            return True
        else:
            return False

    @omdb_guard_response
    def get(self, **params):
        params.update({"tomatoes": "True"})
        params.update({"plot": "full"})
        params.update({"r": "xml"})
        params.update({"apikey": self.api_key})
        return self.session.get(self.ApiUrl, params=params, timeout=10)

    @wrap_omdb_object
    def get_json(self, **params):
        response = self.get(**params)
        if response is None:
            return None
        try:
            if not response.content:
                return None
            return self._handle_response(
                xml_to_dict.parse(response.text).get("root", {}).get("movie")
            )
        except (ValueError, AttributeError):
            g.log_stacktrace()
            g.log(
                "Failed to receive JSON from OMDb response - response: {}".format(
                    response
                ),
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
            if "series" == item["type"]:
                item.update({"mediatype": "tvshow"})
            else:
                item.update({"mediatype": item["type"]})
        return item
