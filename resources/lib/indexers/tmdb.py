# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import OrderedDict
from functools import wraps

import requests
import xbmc
import xbmcgui
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from resources.lib.common import tools
from resources.lib.indexers.apibase import ApiBase, handle_single_item_or_list
from resources.lib.modules.globals import g

if g.PYTHON3:
    unicode = str


def tmdb_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        try:
            response = func(*args, **kwarg)
            if response.status_code in [200, 201]:
                return response

            if "Retry-After" in response.headers:
                # API REQUESTS Are not being throttled anymore but we leave it here for if the re-enable it again
                throttle_time = response.headers["Retry-After"]
                g.log(
                    "TMDb Throttling Applied, Sleeping for {} seconds".format(
                        throttle_time
                    ),
                    "",
                )
                xbmc.sleep((int(throttle_time) * 1000) + 1)
                return wrapper(*args, **kwarg)

            g.log(
                "TMDb returned a {} ({}): while requesting {}".format(
                    response.status_code,
                    TMDBAPI.http_codes[response.status_code],
                    response.url,
                ),
                "warning",
            )
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME, g.get_language_string(30025).format("TMDb")
            )
            if g.get_global_setting("run.mode") == "test":
                raise
            return None

    return wrapper


def wrap_tmdb_object(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        return {"tmdb_object": func(*args, **kwarg)}

    return wrapper


class TMDBAPI(ApiBase):
    baseUrl = "https://api.themoviedb.org/3/"
    imageBaseUrl = "https://image.tmdb.org/t/p/"

    normalization = [
        ("overview", ("plot", "overview", "plotoutline"), None),
        ("release_date", ("premiered", "aired"), lambda t: tools.validate_date(t)),
        (
            "keywords",
            "tag",
            lambda t: sorted(OrderedDict.fromkeys(v["name"] for v in t["keywords"])),
        ),
        (
            "genres",
            "genre",
            lambda t: sorted(
                OrderedDict.fromkeys(x.strip() for v in t for x in v["name"].split("&"))
            ),
        ),
        ("certification", "mpaa", None),
        ("imdb_id", ("imdbnumber", "imdb_id"), None),
        (("external_ids", "imdb_id"), ("imdbnumber", "imdb_id"), None),
        ("show_id", "tmdb_show_id", None),
        ("id", "tmdb_id", None),
        ("network", "studio", None),
        ("runtime", "duration", lambda d: d * 60),
        (
            None,
            "rating.tmdb",
            (
                ("vote_average", "vote_count"),
                lambda a, c: {"rating": tools.safe_round(a, 2), "votes": c},
            ),
        ),
        ("tagline", "tagline", None),
        ("status", "status", None),
        ("trailer", "trailer", None),
        ("belongs_to_collection", "set", lambda t: t.get("name") if t else None),
        (
            "production_companies",
            "studio",
            lambda t: sorted(
                OrderedDict.fromkeys(v["name"] if "name" in v else v for v in t)
            ),
        ),
        (
            "production_countries",
            "country",
            lambda t: sorted(
                OrderedDict.fromkeys(v["name"] if "name" in v else v for v in t)
            ),
        ),
        ("aliases", "aliases", None),
        ("mediatype", "mediatype", None),
    ]

    show_normalization = tools.extend_array(
        [
            ("name", ("tite", "tvshowtitle", "sorttitle"), None),
            ("original_name", "originaltitle", None),
            (
                "first_air_date",
                "year",
                lambda t: tools.validate_date(t)[:4]
                if tools.validate_date(t)
                else None,
            ),
            (
                "networks",
                "studio",
                lambda t: sorted(OrderedDict.fromkeys(v["name"] for v in t)),
            ),
            (
                "origin_country",
                "studio",
                lambda t: sorted(
                    OrderedDict.fromkeys(v["name"] if "name" in v else v for v in t)
                ),
            ),
            (
                ("credits", "crew"),
                "director",
                lambda t: sorted(
                    OrderedDict.fromkeys(
                        v["name"] if "name" in v else v
                        for v in t
                        if v.get("job") == "Director"
                    )
                ),
            ),
            (
                ("credits", "crew"),
                "writer",
                lambda t: sorted(
                    OrderedDict.fromkeys(
                        v["name"] if "name" in v else v
                        for v in t
                        if v.get("department") == "Writing"
                    )
                ),
            ),
            (("external_ids", "tvdb_id"), "tvdb_id", None),
            (
                "origin_country",
                "country_origin",
                lambda t: t[0].upper() if t is not None and t[0] is not None else None,
            ),
        ],
        normalization,
    )

    season_normalization = tools.extend_array(
        [
            ("name", ("title", "sorttitle"), None),
            ("season_number", ("season", "sortseason"), None),
            ("episodes", "episode_count", lambda t: len(t) if t is not None else None),
            (
                ("credits", "crew"),
                "director",
                lambda t: sorted(
                    OrderedDict.fromkeys(
                        v["name"] if "name" in v else v
                        for v in t
                        if v.get("job") == "Director"
                    )
                ),
            ),
            (
                ("credits", "crew"),
                "writer",
                lambda t: sorted(
                    OrderedDict.fromkeys(
                        v["name"] if "name" in v else v
                        for v in t
                        if v.get("department") == "Writing"
                    )
                ),
            ),
            (("external_ids", "tvdb_id"), "tvdb_id", None),
        ],
        normalization,
    )

    episode_normalization = tools.extend_array(
        [
            ("name", ("title", "sorttitle"), None),
            ("episode_number", ("episode", "sortepisode"), None),
            ("season_number", ("season", "sortseason"), None),
            (
                "crew",
                "director",
                lambda t: sorted(
                    OrderedDict.fromkeys(
                        v["name"] for v in t if v.get("job") == "Director"
                    )
                ),
            ),
            (
                "crew",
                "writer",
                lambda t: sorted(
                    OrderedDict.fromkeys(
                        v["name"] for v in t if v.get("department") == "Writing"
                    )
                ),
            ),
        ],
        normalization,
    )

    movie_normalization = tools.extend_array(
        [
            ("title", ("title", "sorttitle"), None),
            ("original_title", "originaltitle", None),
            ("premiered", "year", lambda t: t[:4]),
        ],
        normalization,
    )

    meta_objects = {
        "movie": movie_normalization,
        "tvshow": show_normalization,
        "season": season_normalization,
        "episode": episode_normalization,
    }

    http_codes = {
        200: "Success",
        201: "Success - new resource created (POST)",
        401: "Invalid API key: You must be granted a valid key.",
        404: "The resource you requested could not be found.",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    append_to_response = [
        "credits",
        "images",
        "release_dates",
        "content_ratings",
        "external_ids",
        "movie_credits",
        "tv_credits",
        "videos",
        "alternative_titles",
    ]

    def __init__(self):
        self.apiKey = g.get_setting("tmdb.apikey", "9f3ca569aa46b6fb13931ec96ab8ae7e")
        self.lang_code = g.get_language_code()
        self.lang_full_code = g.get_language_code(True)
        self.lang_region_code = self.lang_full_code.split("-")[1]
        if self.lang_region_code == "":
            self.lang_full_code = self.lang_full_code.strip("-")
        self.include_languages = OrderedDict.fromkeys([self.lang_code, "en", "null"])
        self.preferred_artwork_size = g.get_int_setting("artwork.preferredsize")
        self.artwork_size = {}
        self._set_artwork()

        self.art_normalization = [
            ("backdrops", "fanart", None),
            (
                "posters",
                "poster",
                lambda x: x["iso_639_1"] != "xx" and x["iso_639_1"] is not None,
            ),
            (
                "posters",
                "keyart",
                lambda x: x["iso_639_1"] == "xx" or x["iso_639_1"] is None,
            ),
            ("stills", "fanart", None),
        ]

        self.meta_hash = tools.md5_hash(
            (
                self.lang_code,
                self.lang_full_code,
                self.lang_region_code,
                self.include_languages,
                self.preferred_artwork_size,
                self.append_to_response,
                self.baseUrl,
                self.imageBaseUrl,
            )
        )

    def _set_artwork(self):
        if self.preferred_artwork_size == 0:
            self.artwork_size["fanart"] = 2160
            self.artwork_size["poster"] = 780
            self.artwork_size["keyart"] = 780
            self.artwork_size["thumb"] = 780
            self.artwork_size["icon"] = 780
            self.artwork_size["cast"] = 780
        elif self.preferred_artwork_size == 1:
            self.artwork_size["fanart"] = 1280
            self.artwork_size["poster"] = 500
            self.artwork_size["keyart"] = 500
            self.artwork_size["thumb"] = 500
            self.artwork_size["icon"] = 342
            self.artwork_size["cast"] = 500
        elif self.preferred_artwork_size == 2:
            self.artwork_size["fanart"] = 780
            self.artwork_size["poster"] = 342
            self.artwork_size["keyart"] = 342
            self.artwork_size["thumb"] = 300
            self.artwork_size["icon"] = 185
            self.artwork_size["cast"] = 342

    @tmdb_guard_response
    def get(self, url, **params):
        return requests.get(
            tools.urljoin(self.baseUrl, url),
            params=self._add_api_key(params),
            headers={"Accept": "application/json"},
            timeout=3,
        )

    def get_json(self, url, **params):
        response = self.get(url, **params)
        if response is None:
            return None
        return self._handle_response(response.json())

    @wrap_tmdb_object
    def get_movie(self, tmdb_id):
        return self.get_json(
            "movie/{}".format(tmdb_id),
            language=self.lang_full_code,
            append_to_response=",".join(self.append_to_response),
            include_image_language=",".join(self.include_languages),
            region=self.lang_region_code,
        )

    @wrap_tmdb_object
    def get_movie_rating(self, tmdb_id):
        result = tools.filter_dictionary(
            tools.safe_dict_get(self.get_json("movie/{}".format(tmdb_id)), "info"),
            "rating",
        )
        return {"info": result} if result else None

    @wrap_tmdb_object
    def get_movie_cast(self, tmdb_id):
        result = tools.safe_dict_get(
            self.get_json("movie/{}/credits".format(tmdb_id)), "cast"
        )
        return {"cast": result} if result else None

    @wrap_tmdb_object
    def get_movie_art(self, tmdb_id):
        return self.get_json(
            "movie/{}/images".format(tmdb_id),
            include_image_language=",".join(self.include_languages),
        )

    @wrap_tmdb_object
    def get_show(self, tmdb_id):
        return self.get_json(
            "tv/{}".format(tmdb_id),
            language=self.lang_full_code,
            append_to_response=",".join(self.append_to_response),
            include_image_language=",".join(self.include_languages),
            region=self.lang_region_code,
        )

    @wrap_tmdb_object
    def get_show_art(self, tmdb_id):
        return self.get_json(
            "tv/{}/images".format(tmdb_id),
            include_image_language=",".join(self.include_languages),
        )

    @wrap_tmdb_object
    def get_show_rating(self, tmdb_id):
        result = tools.filter_dictionary(
            tools.safe_dict_get(self.get_json("tv/{}".format(tmdb_id)), "info"),
            "rating",
        )
        return {"info": result} if result else None

    @wrap_tmdb_object
    def get_show_cast(self, tmdb_id):
        result = tools.safe_dict_get(
            self.get_json("tv/{}/credits".format(tmdb_id)), "cast"
        )
        return {"cast": result} if result else None

    @wrap_tmdb_object
    def get_season(self, tmdb_id, season):
        return self.get_json(
            "tv/{}/season/{}".format(tmdb_id, season),
            language=self.lang_full_code,
            append_to_response=",".join(self.append_to_response),
            include_image_language=",".join(self.include_languages),
            region=self.lang_region_code,
        )

    @wrap_tmdb_object
    def get_season_art(self, tmdb_id, season):
        return self.get_json(
            "tv/{}/season/{}/images".format(tmdb_id, season),
            include_image_language=",".join(self.include_languages),
        )

    @wrap_tmdb_object
    def get_episode(self, tmdb_id, season, episode):
        return self.get_json(
            "tv/{}/season/{}/episode/{}".format(tmdb_id, season, episode),
            language=self.lang_full_code,
            append_to_response=",".join(self.append_to_response),
            include_image_language=",".join(self.include_languages),
            region=self.lang_region_code,
        )

    @wrap_tmdb_object
    def get_episode_art(self, tmdb_id, season, episode):
        return self.get_json(
            "tv/{}/season/{}/episode/{}/images".format(tmdb_id, season, episode),
            include_image_language=",".join(self.include_languages),
        )

    @wrap_tmdb_object
    def get_episode_rating(self, tmdb_id, season, episode):
        result = tools.filter_dictionary(
            tools.safe_dict_get(
                self.get_json(
                    "tv/{}/season/{}/episode/{}".format(tmdb_id, season, episode)
                ),
                "info",
            ),
            "rating",
        )
        return {"info": result} if result else None

    def _add_api_key(self, params):
        if "api_key" not in params:
            params.update({"api_key": self.apiKey})
        return params

    @handle_single_item_or_list
    def _handle_response(self, item):
        result = {}
        self._try_detect_type(item)
        self._apply_localized_alternative_titles(item)
        self._apply_releases(item)
        self._apply_content_ratings(item)
        self._apply_release_dates(item)
        self._apply_trailers(item)
        result.update({"art": self._handle_artwork(item)})
        result.update({"cast": self._handle_cast(item)})
        if item.get("mediatype"):
            result.update(
                {
                    "info": self._normalize_info(
                        self.meta_objects[item["mediatype"]], item
                    )
                }
            )

        return result

    def _apply_localized_alternative_titles(self, item):
        if "alternative_titles" in item:
            item["aliases"] = []
            for t in item["alternative_titles"].get(
                "titles", item["alternative_titles"].get("results", [])
            ):
                if "iso_3166_1" in t and t["iso_3166_1"] in [
                    self.lang_region_code,
                    "US",
                ]:
                    if t.get("title") not in [None, ""]:
                        item["aliases"].append(t["title"])
                if "iso_3166_1" in t and t["iso_3166_1"] in [self.lang_region_code]:
                    if t.get("title") not in [None, ""] and t.get("type") not in [
                        None,
                        "",
                    ]:
                        item.update({"title": t["title"]})
        return item

    def _apply_trailers(self, item):
        if "videos" not in item:
            return item
        if not TMDBAPI._apply_trailer(item, self.lang_region_code):
            TMDBAPI._apply_trailer(item, "US")

    @staticmethod
    def _apply_trailer(item, region_code):
        for t in sorted(
            item["videos"].get("results", []), key=lambda k: k["size"], reverse=True
        ):
            if (
                "iso_3166_1" in t
                and t["iso_3166_1"] == region_code
                and t["site"] == "YouTube"
                and t["type"] == "Trailer"
            ):
                if t.get("key"):
                    item.update({"trailer": tools.youtube_url.format(t["key"])})
                    return True
        return False

    def _apply_releases(self, item):
        if "releases" not in item:
            return item
        if not TMDBAPI._apply_release(item, self.lang_region_code):
            TMDBAPI._apply_release(item, "US")

    @staticmethod
    def _apply_release(item, region_code):
        for t in item["releases"]["countries"]:
            if "iso_3166_1" in t and t["iso_3166_1"] == region_code:
                if t.get("certification"):
                    item.update({"certification": t["certification"]})
                if t.get("release_date"):
                    item.update({"release_date": t["release_date"]})
                return True
        return False

    def _apply_content_ratings(self, item):
        if "content_ratings" not in item:
            return item
        if not TMDBAPI._apply_content_rating(item, self.lang_region_code):
            TMDBAPI._apply_content_rating(item, "US")
        return item

    @staticmethod
    def _apply_content_rating(item, region_code):
        for rating in item["content_ratings"]["results"]:
            if "iso_3166_1" in rating and rating["iso_3166_1"] == region_code:
                if rating.get("rating"):
                    item.update({"rating": rating["rating"]})
                    return True
        return False

    def _apply_release_dates(self, item):
        if "release_dates" not in item:
            return item
        if not TMDBAPI._apply_release_date(item, self.lang_region_code):
            TMDBAPI._apply_release_date(item, "US")
        return item

    @staticmethod
    def _apply_release_date(item, region_code):
        for rating in item["release_dates"]["results"]:
            if "iso_3166_1" in rating and rating["iso_3166_1"] == region_code:
                if (
                    "release_dates" in rating
                    and rating["release_dates"][0]
                    and rating["release_dates"][0]["certification"]
                ):
                    item.update(
                        {"certification": rating["release_dates"][0]["certification"]}
                    )
                if (
                    "release_dates" in rating
                    and rating["release_dates"][0]
                    and rating["release_dates"][0]["release_date"]
                ):
                    item.update({"rating": rating["release_dates"][0]["release_date"]})
                return True
        return False

    @staticmethod
    def _try_detect_type(item):
        if "still_path" in item:
            item.update({"mediatype": "episode"})
        elif "season_number" in item and "episode_count" in item or "episodes" in item:
            item.update({"mediatype": "season"})
        elif "number_of_seasons" in item:
            item.update({"mediatype": "tvshow"})
        elif "imdb_id" in item:
            item.update({"mediatype": "movie"})
        return item

    def _handle_artwork(self, item):
        result = {}
        if item.get("still_path") is not None:
            result.update(
                {
                    "thumb": self._get_absolute_image_path(
                        item["still_path"],
                        self._create_tmdb_image_size(self.artwork_size["thumb"]),
                    )
                }
            )
        if item.get("backdrop_path") is not None:
            result.update(
                {
                    "fanart": self._get_absolute_image_path(
                        item["backdrop_path"],
                        self._create_tmdb_image_size(self.artwork_size["fanart"]),
                    )
                }
            )
        if item.get("poster_path") is not None:
            result.update(
                {
                    "poster": self._get_absolute_image_path(
                        item["poster_path"],
                        self._create_tmdb_image_size(self.artwork_size["poster"]),
                    )
                }
            )
        images = item.get("images", item)
        for tmdb_type, kodi_type, selector in self.art_normalization:
            if tmdb_type not in images or not images[tmdb_type]:
                continue
            result.update(
                {
                    kodi_type: [
                        {
                            "url": self._get_absolute_image_path(
                                i["file_path"],
                                self._create_tmdb_image_size(
                                    self.artwork_size[kodi_type]
                                ),
                            ),
                            "language": i["iso_639_1"]
                            if i["iso_639_1"] != "xx"
                            else None,
                            "rating": self._normalize_rating(i),
                            "size": int(
                                i["width" if tmdb_type != "posters" else "height"]
                            )
                            if int(i["width" if tmdb_type != "posters" else "height"])
                            < self.artwork_size[kodi_type]
                            else self.artwork_size[kodi_type],
                        }
                        for i in images[tmdb_type]
                        if selector is None or selector(i)
                    ]
                }
            )
        return result

    @staticmethod
    def _create_tmdb_image_size(size):
        if size == 2160 or size == 1080:
            return "original"
        else:
            return "w{}".format(size)

    def _handle_cast(self, item):
        cast = item.get("credits", item)
        if (not cast.get("cast")) and not item.get("guest_stars"):
            return

        return [
            {
                "name": item["name"],
                "role": item["character"],
                "order": idx,
                "thumbnail": self._get_absolute_image_path(
                    item["profile_path"],
                    self._create_tmdb_image_size(self.artwork_size["cast"]),
                ),
            }
            for idx, item in enumerate(
                tools.extend_array(
                    sorted(cast.get("cast", []), key=lambda k: k["order"],),
                    sorted(cast.get("guest_stars", []), key=lambda k: k["order"]),
                )
            )
            if "name" in item and "character" in item and "profile_path" in item
        ]

    @staticmethod
    def _normalize_rating(image):
        if image["vote_count"]:
            rating = image["vote_average"]
            rating = 5 + (rating - 5) * 2
            return rating
        return 5

    def _get_absolute_image_path(self, relative_path, size="orginal"):
        if not relative_path:
            return None
        return "/".join(
            [self.imageBaseUrl.strip("/"), size.strip("/"), relative_path.strip("/")]
        )
