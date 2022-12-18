from functools import cached_property
from functools import wraps
from urllib import parse

import xbmcgui

from . import valid_id_or_none
from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import ApiBase
from resources.lib.indexers.apibase import handle_single_item_or_list
from resources.lib.modules.globals import g


def tmdb_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        import requests

        try:
            response = func(*args, **kwarg)
            if response.status_code in [200, 201]:
                return response

            g.log(
                f"TMDb returned a {response.status_code} ({TMDBAPI.http_codes[response.status_code]}): while requesting {'&'.join(x for x in response.url.split('&') if not x.lower().startswith('api_key'))}",
                "warning" if response.status_code != 404 else "debug",
            )

            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30024).format("TMDb"))
            if g.get_runtime_setting("run.mode") == "test":
                raise
            else:
                g.log_stacktrace()
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
        ("release_date", ("premiered", "aired"), lambda t: g.validate_date(t)),
        (
            "keywords",
            "tag",
            lambda t: sorted({v["name"] for v in t["keywords"]}),
        ),
        (
            "genres",
            "genre",
            lambda t: sorted({x.strip() for v in t for x in v["name"].split("&")}),
        ),
        ("certification", "mpaa", None),
        ("imdb_id", ("imdbnumber", "imdb_id"), lambda i: valid_id_or_none(i)),
        (("external_ids", "imdb_id"), ("imdbnumber", "imdb_id"), lambda i: valid_id_or_none(i)),
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
            lambda t: sorted({v["name"] if "name" in v else v for v in t}),
        ),
        (
            "production_countries",
            "country",
            lambda t: sorted({v["name"] if "name" in v else v for v in t}),
        ),
        ("aliases", "aliases", None),
        ("mediatype", "mediatype", None),
    ]

    show_normalization = tools.extend_array(
        [
            ("name", ("title", "tvshowtitle", "sorttitle"), None),
            ("original_name", "originaltitle", None),
            ("first_air_date", "year", lambda t: g.validate_date(t)[:4] if g.validate_date(t) else None),
            (
                "networks",
                "studio",
                lambda t: sorted({v["name"] for v in t}),
            ),
            (
                ("credits", "crew"),
                "director",
                lambda t: sorted({v["name"] if "name" in v else v for v in t if v.get("job") == "Director"}),
            ),
            (
                ("credits", "crew"),
                "writer",
                lambda t: sorted({v["name"] if "name" in v else v for v in t if v.get("department") == "Writing"}),
            ),
            (("external_ids", "tvdb_id"), "tvdb_id", lambda i: valid_id_or_none(i)),
            (
                "origin_country",
                "country_origin",
                lambda t: t[0].upper() if type(t) == list and len(t) > 0 and t[0] is not None else None,
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
                lambda t: sorted({v["name"] if "name" in v else v for v in t if v.get("job") == "Director"}),
            ),
            (
                ("credits", "crew"),
                "writer",
                lambda t: sorted({v["name"] if "name" in v else v for v in t if v.get("department") == "Writing"}),
            ),
            (("external_ids", "tvdb_id"), "tvdb_id", lambda i: valid_id_or_none(i)),
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
                lambda t: sorted({v["name"] for v in t if v.get("job") == "Director"}),
            ),
            (
                "crew",
                "writer",
                lambda t: sorted({v["name"] for v in t if v.get("department") == "Writing"}),
            ),
        ],
        normalization,
    )

    movie_normalization = tools.extend_array(
        [
            ("title", ("title", "sorttitle"), None),
            ("original_title", "originaltitle", None),
            (
                ("release_dates", "results"),
                "releases",
                lambda r: tools.merge_dicts(
                    *(i['release_dates'] for i in ApiBase._normalize_info(TMDBAPI.release_dates_normalization, r))
                ),
            ),
            ("premiered", "year", lambda t: g.validate_date(t)[:4] if g.validate_date(t) else None),
        ],
        normalization,
    )

    release_dates_normalization = [
        (
            None,
            "release_dates",
            (
                ("iso_3166_1", "release_dates"),
                lambda c, r: {
                    c.upper(): ApiBase._normalize_info(
                        TMDBAPI.release_normalization, [dict(rel, country=c.upper()) for rel in r]
                    )
                },
            ),
        )
    ]

    release_normalization = [
        ("country", "country", None),
        ("release_date", "release_date", lambda r: g.validate_date(r)),
        ("type", "release_type", lambda rt: TMDBAPI.release_type.get(rt, "unknown")),
        ("certification", "mpaa", None),
    ]

    release_type = {1: "premiere", 2: "limited", 3: "theatrical", 4: "digital", 5: "physical", 6: "tv"}

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
        429: "Too Many Requests.",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }

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
        self.include_languages = [self.lang_code, "en", "null"] if self.lang_code != "en" else ["en", "null"]

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
            (
                "logos",
                "clearlogo",
                lambda x: x["iso_639_1"] != "xx" and x["iso_639_1"] is not None,
            ),
            ("stills", "fanart", None),
        ]

    @cached_property
    def meta_hash(self):
        return tools.md5_hash(
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

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 503, 504, 520, 521, 522, 524],
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    def _set_artwork(self):
        if self.preferred_artwork_size == 0:
            self._set_artwork_sizes("original", "original", "original", "original")
        elif self.preferred_artwork_size == 1:
            self._set_artwork_sizes(1280, 500, 500, 342)
        elif self.preferred_artwork_size == 2:
            self._set_artwork_sizes(780, 342, 300, 185)

    def _set_artwork_sizes(self, fanart, poster, thumb, icon):
        self.artwork_size.update(
            {
                "fanart": fanart,
                "poster": poster,
                "clearlogo": poster,
                "keyart": poster,
                "thumb": thumb,
                "icon": icon,
                "cast": poster,
            }
        )

    @tmdb_guard_response
    def get(self, url, **params):
        timeout = params.pop("timeout", 10)
        return self.session.get(
            parse.urljoin(self.baseUrl, url),
            params=self._add_api_key(params),
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

    def get_json(self, url, **params):
        response = self.get(url, **params)
        return None if response is None else self._handle_response(response.json())

    @use_cache()
    def get_json_cached(self, url, **params):
        response = self.get(url, **params)
        return None if response is None else self._handle_response(response.json())

    @wrap_tmdb_object
    def get_movie(self, tmdb_id):
        return self.get_json_cached(
            f"movie/{tmdb_id}",
            language=self.lang_full_code,
            append_to_response=",".join(self.append_to_response),
            include_image_language=",".join(self.include_languages),
            region=self.lang_region_code,
        )

    @wrap_tmdb_object
    def get_movie_rating(self, tmdb_id):
        result = tools.filter_dictionary(
            tools.safe_dict_get(self.get_json_cached(f"movie/{tmdb_id}"), "info"),
            "rating.tmdb",
        )
        return {"info": result} if result else None

    @wrap_tmdb_object
    def get_movie_cast(self, tmdb_id):
        result = tools.safe_dict_get(self.get_json_cached(f"movie/{tmdb_id}/credits"), "cast")
        return {"cast": result} if result else None

    @wrap_tmdb_object
    def get_movie_art(self, tmdb_id):
        return self.get_json_cached(
            f"movie/{tmdb_id}/images",
            include_image_language=",".join(self.include_languages),
        )

    @wrap_tmdb_object
    def get_show(self, tmdb_id):
        return self.get_json_cached(
            f"tv/{tmdb_id}",
            language=self.lang_full_code,
            append_to_response=",".join(self.append_to_response),
            include_image_language=",".join(self.include_languages),
            region=self.lang_region_code,
        )

    @wrap_tmdb_object
    def get_show_art(self, tmdb_id):
        return self.get_json_cached(
            f"tv/{tmdb_id}/images",
            include_image_language=",".join(self.include_languages),
        )

    @wrap_tmdb_object
    def get_show_rating(self, tmdb_id):
        result = tools.filter_dictionary(
            tools.safe_dict_get(self.get_json_cached(f"tv/{tmdb_id}"), "info"),
            "rating.tmdb",
        )
        return {"info": result} if result else None

    @wrap_tmdb_object
    def get_show_cast(self, tmdb_id):
        result = tools.safe_dict_get(self.get_json_cached(f"tv/{tmdb_id}/credits"), "cast")
        return {"cast": result} if result else None

    @wrap_tmdb_object
    def get_season(self, tmdb_id, season):
        return self.get_json_cached(
            f"tv/{tmdb_id}/season/{season}",
            language=self.lang_full_code,
            append_to_response=",".join(self.append_to_response),
            include_image_language=",".join(self.include_languages),
            region=self.lang_region_code,
        )

    @wrap_tmdb_object
    def get_season_art(self, tmdb_id, season):
        return self.get_json_cached(
            f"tv/{tmdb_id}/season/{season}/images",
            include_image_language=",".join(self.include_languages),
        )

    @wrap_tmdb_object
    def get_episode(self, tmdb_id, season, episode):
        return self.get_json_cached(
            f"tv/{tmdb_id}/season/{season}/episode/{episode}",
            language=self.lang_full_code,
            append_to_response=",".join(self.append_to_response),
            include_image_language=",".join(self.include_languages),
            region=self.lang_region_code,
        )

    @wrap_tmdb_object
    def get_episode_art(self, tmdb_id, season, episode):
        return self.get_json_cached(
            f"tv/{tmdb_id}/season/{season}/episode/{episode}/images",
            include_image_language=",".join(self.include_languages),
        )

    @wrap_tmdb_object
    def get_episode_rating(self, tmdb_id, season, episode):
        result = tools.filter_dictionary(
            tools.safe_dict_get(
                self.get_json_cached(f"tv/{tmdb_id}/season/{season}/episode/{episode}"),
                "info",
            ),
            "rating.tmdb",
        )
        return {"info": result} if result else None

    def _add_api_key(self, params):
        if "api_key" not in params:
            params.update({"api_key": self.apiKey})
        return params

    @handle_single_item_or_list
    def _handle_response(self, item):
        self._try_detect_type(item)
        self._apply_localized_alternative_titles(item)
        self._apply_content_ratings(item)
        self._apply_release_dates(item)
        self._apply_trailers(item)
        result = {"art": self._handle_artwork(item), "cast": self._handle_cast(item)}
        if item.get("mediatype"):
            result["info"] = self._normalize_info(self.meta_objects[item["mediatype"]], item)

        return result

    def _apply_localized_alternative_titles(self, item):
        if alternative_titles := item.get("alternative_titles"):
            country_set = {self.lang_region_code, "US"}
            item["aliases"] = [
                title
                for t in alternative_titles.get("titles", alternative_titles.get("results", []))
                if t.get("iso_3166_1") in country_set and (title := t.get("title"))
            ]

    def _apply_trailers(self, item):
        if "videos" not in item:
            return item
        if not TMDBAPI._apply_trailer(item, self.lang_region_code):
            TMDBAPI._apply_trailer(item, "US")

    @staticmethod
    def _apply_trailer(item, region_code):
        if trailer_keys := sorted(
            [
                t
                for t in item["videos"].get("results", [])
                if t.get("iso_3166_1") == region_code
                and t.get("site") == "YouTube"
                and t.get("type") == "Trailer"
                and t.get("key")
            ],
            key=lambda k: k["size"],
            reverse=True,
        ):
            item["trailer"] = tools.youtube_url.format(trailer_keys[0]["key"])
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
            if rating.get("iso_3166_1") == region_code and (content_rating := rating.get("rating")):
                item["certification"] = content_rating
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
                    item.update({"certification": rating["release_dates"][0]["certification"]})
                if (
                    "release_dates" in rating
                    and rating["release_dates"][0]
                    and rating["release_dates"][0]["release_date"]
                ):
                    item.update({"release_date": g.validate_date(rating["release_dates"][0]["release_date"])})
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
            result["thumb"] = self._get_absolute_image_path(
                item["still_path"],
                self._create_tmdb_image_size(self.artwork_size["thumb"]),
            )

        if item.get("backdrop_path") is not None:
            result["fanart"] = self._get_absolute_image_path(
                item["backdrop_path"],
                self._create_tmdb_image_size(self.artwork_size["fanart"]),
            )

        if item.get("poster_path") is not None:
            result["poster"] = self._get_absolute_image_path(
                item["poster_path"],
                self._create_tmdb_image_size(self.artwork_size["poster"]),
            )

        images = item.get("images", item)
        for tmdb_type, kodi_type, selector in self.art_normalization:
            if tmdb_type not in images or not images[tmdb_type]:
                continue
            result[kodi_type] = [
                {
                    "url": self._get_absolute_image_path(
                        i["file_path"],
                        self._create_tmdb_image_size(self.artwork_size[kodi_type]),
                    ),
                    "language": i["iso_639_1"] if i["iso_639_1"] != "xx" else None,
                    "rating": self._normalize_rating(i),
                    "size": self._extract_size(tmdb_type, kodi_type, i),
                }
                for i in images[tmdb_type]
                if selector is None or selector(i)
            ]

        return result

    def _extract_size(self, tmdb_type, kodi_type, item):
        size = int(item["width" if tmdb_type != "posters" else "height"])

        if self.artwork_size[kodi_type] == "original" or size < self.artwork_size[kodi_type]:
            return size
        else:
            return self.artwork_size[kodi_type]

    @staticmethod
    def _create_tmdb_image_size(size):
        return "original" if size == "original" else f"w{size}"

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
                    sorted(
                        cast.get("cast", []),
                        key=lambda k: k["order"],
                    ),
                    sorted(cast.get("guest_stars", []), key=lambda k: k["order"]),
                )
            )
            if "name" in item and "character" in item and "profile_path" in item
        ]

    @staticmethod
    def _normalize_rating(image):
        return 5 + (image["vote_average"] - 5) * 2 if image["vote_count"] else 5

    def _get_absolute_image_path(self, relative_path, size="original"):
        if not relative_path:
            return None
        if relative_path.lower().endswith(".svg"):
            relative_path = f"{relative_path[:-4]}.png"
        return "/".join([self.imageBaseUrl.strip("/"), size.strip("/"), relative_path.strip("/")])
