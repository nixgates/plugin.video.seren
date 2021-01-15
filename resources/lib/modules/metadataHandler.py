# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import OrderedDict

from resources.lib.common import tools
from resources.lib.indexers.fanarttv import FanartTv
from resources.lib.indexers.omdb import OmdbApi
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.indexers.tvdb import TVDBAPI
from resources.lib.modules.globals import g


class MetadataHandler(object):
    def __init__(
        self,
        tmdb_api=None,
        tvdb_api=None,
        fanarttv_api=None,
        trakt_api=None,
        omdb_api=None,
    ):
        self.tmdb_api = tmdb_api if tmdb_api else TMDBAPI()
        self.tvdb_api = tvdb_api if tvdb_api else TVDBAPI()
        self.fanarttv_api = fanarttv_api if fanarttv_api else FanartTv()
        self.trakt_api = trakt_api if trakt_api else TraktAPI()
        self.omdb_api = omdb_api if omdb_api else OmdbApi()

        self.lang_code = g.get_language_code()
        self.lang_full_code = g.get_language_code(True)
        self.lang_region_code = self.lang_full_code.split("-")[:1]
        self.allowed_artwork_languages = {None, "en", self.lang_code}
        self.movies_poster_limit = g.get_int_setting("movies.poster_limit", 1)
        self.movies_fanart_limit = g.get_int_setting("movies.fanart_limit", 1)
        self.movies_keyart_limit = g.get_int_setting("movies.keyart_limit", 1)
        self.movies_characterart_limit = g.get_int_setting(
            "movies.characterart_limit", 1
        )
        self.movies_banner = g.get_bool_setting("movies.banner", "true")
        self.movies_clearlogo = g.get_bool_setting("movies.clearlogo", "true")
        self.movies_landscape = g.get_bool_setting("movies.landscape", "true")
        self.movies_clearart = g.get_bool_setting("movies.clearart", "true")
        self.movies_discart = g.get_bool_setting("movies.discart", "true")

        self.tvshows_poster_limit = g.get_int_setting("tvshows.poster_limit", 1)
        self.tvshows_fanart_limit = g.get_int_setting("tvshows.fanart_limit", 1)
        self.tvshows_keyart_limit = g.get_int_setting("tvshows.keyart_limit", 1)
        self.tvshows_characterart_limit = g.get_int_setting(
            "tvshows.characterart_limit", 1
        )
        self.tvshows_banner = g.get_bool_setting("tvshows.banner", "true")
        self.tvshows_clearlogo = g.get_bool_setting("tvshows.clearlogo", "true")
        self.tvshows_landscape = g.get_bool_setting("tvshows.landscape", "true")
        self.tvshows_clearart = g.get_bool_setting("tvshows.clearart", "true")
        self.season_poster = g.get_bool_setting("season.poster", "true")
        self.season_banner = g.get_bool_setting("season.banner", "true")
        self.season_landscape = g.get_bool_setting("season.landscape", "true")
        self.season_fanart = g.get_bool_setting("season.fanart", "true")
        self.episode_fanart = g.get_bool_setting("episode.fanart", "true")
        self.tvshows_preferred_art_source = g.get_int_setting(
            "tvshows.preferedsource", 1
        )
        self.movies_preferred_art_source = g.get_int_setting("movies.preferedsource", 1)
        self.metadata_location = g.get_int_setting("general.metalocation", 1)
        self.preferred_artwork_size = g.get_int_setting("artwork.preferredsize", 1)
        self.show_original_title = g.get_bool_setting(
            "general.meta.showoriginaltitle", False
        )

        self.genres = {
            "action": g.get_language_string(30532),
            "adventure": g.get_language_string(30533),
            "animation": g.get_language_string(30534),
            "anime": g.get_language_string(30535),
            "biography": g.get_language_string(30536),
            "children": g.get_language_string(30537),
            "comedy": g.get_language_string(30538),
            "crime": g.get_language_string(30539),
            "documentary": g.get_language_string(30540),
            "drama": g.get_language_string(30541),
            "family": g.get_language_string(30542),
            "fantasy": g.get_language_string(30543),
            "game-show": g.get_language_string(30544),
            "history": g.get_language_string(30545),
            "holiday": g.get_language_string(30546),
            "home-and-garden": g.get_language_string(30547),
            "horror": g.get_language_string(30548),
            "mini-series": g.get_language_string(30549),
            "music": g.get_language_string(30550),
            "musical": g.get_language_string(30551),
            "mystery": g.get_language_string(30552),
            "news": g.get_language_string(30553),
            "none": g.get_language_string(30554),
            "reality": g.get_language_string(30555),
            "romance": g.get_language_string(30556),
            "science-fiction": g.get_language_string(30557),
            "sci-fi": g.get_language_string(30557),
            "short": g.get_language_string(30558),
            "soap": g.get_language_string(30559),
            "special-interest": g.get_language_string(30560),
            "sporting-event": g.get_language_string(30561),
            "superhero": g.get_language_string(30562),
            "suspense": g.get_language_string(30563),
            "talk-show": g.get_language_string(30564),
            "talkshow": g.get_language_string(30564),
            "thriller": g.get_language_string(30565),
            "tv-movie": g.get_language_string(30566),
            "war": g.get_language_string(30567),
            "western": g.get_language_string(30568),
        }

        self.meta_hash = tools.md5_hash(
            [
                self.lang_code,
                self.movies_poster_limit,
                self.movies_fanart_limit,
                self.movies_keyart_limit,
                self.movies_characterart_limit,
                self.movies_banner,
                self.movies_clearlogo,
                self.movies_landscape,
                self.movies_clearart,
                self.movies_discart,
                self.tvshows_poster_limit,
                self.tvshows_fanart_limit,
                self.tvshows_keyart_limit,
                self.tvshows_characterart_limit,
                self.tvshows_banner,
                self.tvshows_clearlogo,
                self.tvshows_landscape,
                self.tvshows_clearart,
                self.season_poster,
                self.season_banner,
                self.season_landscape,
                self.season_fanart,
                self.episode_fanart,
                self.tvshows_preferred_art_source,
                self.tvshows_preferred_art_source,
                self.metadata_location,
                self.fanarttv_api.fanart_support,
                self.preferred_artwork_size,
                self.show_original_title,
            ]
        )

    # region format art
    def format_db_object(self, db_object):
        return [self.format_meta(i) for i in db_object]

    def format_meta(self, db_object):
        trakt_data = db_object.get("trakt_object")
        tmdb_object = db_object.get("tmdb_object")
        tvdb_object = db_object.get("tvdb_object")
        fanart_object = db_object.get("fanart_object")
        omdb_object = db_object.get("omdb_object")
        show_info = db_object.get("show_info")
        season_info = db_object.get("season_info")
        show_art = db_object.get("show_art")
        season_art = db_object.get("season_art")
        show_cast = db_object.get("show_cast")
        season_cast = db_object.get("season_cast")

        result = {"info": {}, "art": {}, "cast": []}

        result.update(
            self._apply_best_fit_meta_data(
                trakt_data, tmdb_object, tvdb_object, fanart_object, omdb_object
            )
        )

        self._show_season_art_fallback(result, season_art, show_art)
        self._add_season_show_info(result, season_info, show_info)
        self._add_season_show_art(result, season_art, show_art)
        self._add_season_show_cast(result, season_cast, show_cast)
        return result

    @staticmethod
    def _add_season_show_info(result, season_info, show_info):
        if season_info:
            result["info"]["trakt_season_id"] = season_info["trakt_id"]
        if show_info:
            if not result["info"].get("tvshowtitle"):
                result["info"]["tvshowtitle"] = show_info.get("title")
            if not result["info"].get("trakt_show_id"):
                result["info"]["trakt_show_id"] = show_info.get("trakt_id")
            if not result["info"].get("tmdb_show_id"):
                result["info"]["tmdb_show_id"] = show_info.get("tmdb_id")
            if not result["info"].get("tvdb_show_id"):
                result["info"]["tvdb_show_id"] = show_info.get("tvdb_id")
            if not result["info"].get("year"):
                result["info"]["year"] = show_info.get("year")
            result["info"].update(
                {
                    "tvshow.{}".format(key): value
                    for key, value in show_info.items()
                    if key.endswith("_id")
                }
            )

    @staticmethod
    def _add_season_show_cast(result, season_cast, show_cast):
        if season_cast and len(result.get("cast", [])) == 0:
            result["cast"] = season_cast
        if show_cast and len(result.get("cast", [])) == 0:
            result["cast"] = show_cast

    @staticmethod
    def _add_season_show_art(result, season_art, show_art):
        if show_art:
            result["art"].update(
                {"tvshow.{}".format(key): value for key, value in show_art.items()}
            )
        if season_art:
            result["art"].update(
                {
                    "season.{}".format(key): value
                    for key, value in season_art.items()
                    if not key.startswith("tvshow.")
                }
            )

    @staticmethod
    def _show_season_art_fallback(data, season_art, show_art):
        show_season_art_mixin = {}

        MetadataHandler._thumb_fallback(data["art"], data["art"])

        if season_art:
            show_season_art_mixin = tools.smart_merge_dictionary(
                show_season_art_mixin,
                tools.filter_dictionary(season_art, "poster", "fanart", "clearlogo"),
                True,
            )
            MetadataHandler._thumb_fallback(data["art"], season_art)
        if show_art:
            show_season_art_mixin = tools.smart_merge_dictionary(
                show_season_art_mixin,
                tools.filter_dictionary(show_art, "poster", "fanart", "clearlogo"),
                True,
            )
            MetadataHandler._thumb_fallback(data["art"], show_art)

        data["art"] = tools.smart_merge_dictionary(
            data["art"], show_season_art_mixin, True
        )

    @staticmethod
    def _thumb_fallback(art, fallback):
        if not isinstance(art, dict) or not isinstance(fallback, dict):
            return
        if not art.get("thumb") and fallback.get("poster"):
            art.update({"thumb": fallback.get("poster")})
        elif not art.get("thumb") and fallback.get("banner"):
            art.update({"thumb": fallback.get("banner")})

    def _apply_best_fit_meta_data(
        self, trakt_data, tmdb_data, tvdb_data, fanart_object, omdb_object
    ):
        media_type = trakt_data["info"]["mediatype"]
        result = {}

        self._apply_best_fit_info(result, trakt_data, tmdb_data, tvdb_data, omdb_object)
        self._apply_best_fit_cast(result, tmdb_data, tvdb_data)
        self._apply_best_fit_art(
            result, tmdb_data, tvdb_data, fanart_object, media_type
        )

        return result

    def _apply_best_fit_art(
        self, result, tmdb_object, tvdb_object, fanart_object, media_type
    ):
        if tmdb_object:
            result["art"] = tools.smart_merge_dictionary(
                result.get("art", {}),
                tmdb_object.get("art", {}),
                not self._is_tmdb_artwork_selected(media_type),
                False
            )

        if tvdb_object:
            result["art"] = tools.smart_merge_dictionary(
                result.get("art", {}),
                tvdb_object.get("art", {}),
                not self._is_tvdb_artwork_selected(media_type),
                False
            )

        if fanart_object:
            result["art"] = tools.smart_merge_dictionary(
                result.get("art", {}),
                fanart_object.get("art", {}),
                not self._is_fanart_artwork_selected(media_type),
                False
            )

        result["art"] = self._handle_art(media_type, result.get("art", {}))

    def _apply_best_fit_info(
        self, result, trakt_data, tmdb_data, tvdb_data, omdb_object,
    ):
        result.update({"info": trakt_data.get("info")})

        if tmdb_data:
            result["info"] = tools.smart_merge_dictionary(
                result["info"],
                tmdb_data.get("info", {}),
                not self.metadata_location == 1,
            )

        if tvdb_data:
            result["info"] = tools.smart_merge_dictionary(
                result["info"],
                tvdb_data.get("info", {}),
                not self.metadata_location == 2,
            )

        if omdb_object:
            result["info"] = tools.smart_merge_dictionary(
                result["info"], omdb_object.get("info", {}), True
            )

        self._normalize_genres(result)
        self._show_original_title(result)
        self._title_fallback(result)

    def _normalize_genres(self, meta):
        meta["info"]["genre"] = sorted(
            OrderedDict.fromkeys(
                [
                    self.genres.get(i.lower().replace(" ", "-"), i)
                    for i in meta["info"].get("genre", [])
                ]
            )
        )

    def _show_original_title(self, meta):
        if meta["info"].get('originaltitle') and self.show_original_title:
            meta["info"]["sorttitle"] = meta["info"]["title"] = meta["info"].get('originaltitle')

    @staticmethod
    def _title_fallback(meta):
        if not meta["info"].get('title'):
            media_type = meta["info"]["mediatype"]
            title = None
            if media_type == "season":
                title = g.get_language_string(30569).format(meta["info"]["season"])
            if media_type == "episode":
                title = g.get_language_string(30570).format(meta["info"]["episode"])
            if title:
                meta["info"]["sorttitle"] = title
                meta["info"]["title"] = title

    def _apply_best_fit_cast(self, result, tmdb_data, tvdb_data):
        if (
            tmdb_data is not None
            and tmdb_data.get("cast", [])
            and (
                self.metadata_location != 2
                or (
                    self.metadata_location == 2
                    and (not tvdb_data or not tvdb_data.get("cast", []))
                )
            )
        ):
            result["cast"] = tmdb_data.get("cast", [])
        if (
            tvdb_data is not None
            and tvdb_data.get("cast", [])
            and (
                self.metadata_location != 1
                or (
                    self.metadata_location == 1
                    and (not tmdb_data or not tmdb_data.get("cast", []))
                )
            )
        ):
            result["cast"] = tvdb_data.get("cast", [])

    def _is_fanart_artwork_selected(self, media_type):
        return (
            media_type in ["tvshow", "season", "episode"]
            and self.tvshows_preferred_art_source == 0
        ) or (media_type == "movie" and self.movies_preferred_art_source == 0)

    def _is_tmdb_artwork_selected(self, media_type):
        return (
            media_type in ["tvshow", "season", "episode"]
            and self.tvshows_preferred_art_source == 1
        ) or (media_type == "movie" and self.movies_preferred_art_source == 1)

    def _is_tvdb_artwork_selected(self, media_type):
        return (
            media_type in ["tvshow", "season", "episode"]
            and self.tvshows_preferred_art_source == 2
        ) or (media_type == "movie" and self.movies_preferred_art_source == 2)

    def _handle_art(self, media_type, art_data):
        if art_data is None:
            return {}
        [
            art_data.update({k: self._sort_art(self._filter_art(v))})
            for k, v in art_data.items()
            if isinstance(v, (list, set))
        ]

        self._fallback_art_before_handling(art_data)

        if media_type == "movie":
            return self._handle_movie_art(art_data)
        elif media_type == "tvshow":
            return self._handle_show_art(art_data)
        elif media_type == "season":
            return self._handle_season_art(art_data)
        elif media_type == "episode":
            return self._handle_episode_art(art_data)

    @staticmethod
    def _sort_art(art):
        art.sort(key=lambda i: i["url"])
        art.sort(key=lambda i: i["rating"], reverse=True)
        art.sort(key=lambda i: i["size"], reverse=True)
        return art

    def _filter_art(self, art):
        result = []
        for i in art:
            if i["language"] in self.allowed_artwork_languages:
                result.append(i)
        return result

    @staticmethod
    def _fallback_art_before_handling(art):
        if len(art.get("poster", [])) == 0 and len(art.get("keyart", [])) > 0:
            art.update({"poster": art.pop("keyart")})

    @staticmethod
    def _handle_artwork_multis(limit, art_type, art_data):
        data = {}
        for idx in range(0, limit):
            name = art_type if idx == 0 else "{}{}".format(art_type, idx)
            try:
                if not isinstance(art_data[art_type], list):
                    image = art_data[art_type]
                else:
                    image = art_data[art_type][idx]
            except KeyError:
                break
            except IndexError:
                break

            if isinstance(image, dict):
                data[name] = image["url"]
            else:
                data[name] = image
                break
        return data

    def _handle_show_art(self, data):
        result = {}

        result.update(
            self._handle_artwork_multis(self.tvshows_poster_limit, "poster", data)
        )
        result.update(
            self._handle_artwork_multis(self.tvshows_fanart_limit, "fanart", data)
        )
        result.update(
            self._handle_artwork_multis(
                self.tvshows_characterart_limit, "characterart", data
            )
        )
        result.update(
            self._handle_artwork_multis(self.tvshows_keyart_limit, "keyart", data)
        )
        result.update(self._handle_artwork_multis(1, "clearlogo", data))
        result.update(self._handle_artwork_multis(1, "thumb", data))
        result.update(self._handle_artwork_multis(1, "icon", data))

        if self.tvshows_banner:
            result.update(self._handle_artwork_multis(1, "banner", data))
        if self.tvshows_landscape:
            result.update(self._handle_artwork_multis(1, "landscape", data))
        if self.tvshows_clearart:
            result.update(self._handle_artwork_multis(1, "clearart", data))

        return result

    def _handle_movie_art(self, data):
        result = {}

        result.update(
            self._handle_artwork_multis(self.movies_poster_limit, "poster", data)
        )
        result.update(
            self._handle_artwork_multis(self.movies_fanart_limit, "fanart", data)
        )
        result.update(
            self._handle_artwork_multis(
                self.movies_characterart_limit, "characterart", data
            )
        )
        result.update(
            self._handle_artwork_multis(self.movies_keyart_limit, "keyart", data)
        )
        result.update(self._handle_artwork_multis(1, "clearlogo", data))
        result.update(self._handle_artwork_multis(1, "thumb", data))
        result.update(self._handle_artwork_multis(1, "icon", data))

        if self.movies_banner:
            result.update(self._handle_artwork_multis(1, "banner", data))
        if self.movies_landscape:
            result.update(self._handle_artwork_multis(1, "landscape", data))
        if self.movies_discart:
            result.update(self._handle_artwork_multis(1, "discart", data))
        if self.movies_clearart:
            result.update(self._handle_artwork_multis(1, "clearart", data))

        return result

    def _handle_season_art(self, data):
        result = {}
        result.update(self._handle_artwork_multis(1, "thumb", data))
        result.update(self._handle_artwork_multis(1, "icon", data))
        if self.season_poster:
            result.update(
                self._handle_artwork_multis(self.tvshows_poster_limit, "poster", data)
            )
        if self.season_fanart:
            result.update(
                self._handle_artwork_multis(self.tvshows_fanart_limit, "fanart", data)
            )
        if self.season_banner:
            result.update(self._handle_artwork_multis(1, "banner", data))
        if self.season_landscape:
            result.update(self._handle_artwork_multis(1, "landscape", data))
        return result

    def _handle_episode_art(self, data):
        result = {}
        result.update(self._handle_artwork_multis(1, "thumb", data))
        if self.episode_fanart:
            result.update(
                self._handle_artwork_multis(self.tvshows_fanart_limit, "fanart", data)
            )
        return result

    # endregion

    # region update meta
    def update(self, db_object):
        """Checks and updates the requested db_object with the full set of meta data.

        :param db_object:dictionary with the ids and meta from the db.
        :type db_object:dict
        :return:list with the updated db_object
        :rtype:list[dict]
        """
        media_type = MetadataHandler.get_trakt_info(db_object, "mediatype")

        if media_type == "movie":
            self._update_movie(db_object)
        if media_type == "tvshow":
            self._update_tvshow(db_object)
        if media_type == "season":
            self._update_season(db_object)
        if media_type == "episode":
            self._update_episode(db_object)

        self._add_omdb(db_object)
        self._write_log(db_object, media_type)

        return [db_object]

    def _add_omdb(self, db_object):
        if (
            self.omdb_api.omdb_support
            and self._imdb_id_valid(db_object)
            and (self._omdb_needs_update(db_object) or self._force_update(db_object))
        ):
            tools.smart_merge_dictionary(
                db_object, self.omdb_api.get_json(i=db_object.get("imdb_id"))
            )

    def _write_log(self, db_object, media_type):
        if (
            (media_type == "movie" and not db_object.get("tmdb_object"))
            or (
                media_type in ["tvshow", "season", "episode"]
                and not db_object.get("tmdb_object")
                and not db_object.get("tvdb_object")
            )
        ) or (
            self.fanarttv_api.fanart_support and not
            media_type == "episode" and not
            db_object.get("fanart_object")
        ):
            g.log("Failed to lookup meta for {}".format(db_object.get("trakt_id")), "warning")

    # region movie
    def _update_movie(self, db_object):
        self._update_movie_trakt(db_object)
        self._update_movie_tmdb(db_object)
        self._update_movie_fanart(db_object)
        self._update_movie_fallback(db_object)
        self._update_movie_ratings(db_object)
        self._update_movie_cast(db_object)

    def _update_movie_trakt(self, db_object):
        if (
            self.metadata_location == 0
            and tools.safe_dict_get(db_object, "trakt_object", "info")
            and db_object.get("trakt_id")
            and tools.safe_dict_get(db_object, "trakt_object", "info", "language")
            and self.trakt_api.language
            != tools.safe_dict_get(db_object, "trakt_object", "info", "language")
            and tools.safe_dict_get(
                db_object, "trakt_object", "info", "available_translations"
            )
            and self.trakt_api.language
            in tools.safe_dict_get(
                db_object, "trakt_object", "info", "available_translations"
            )
        ):
            db_object["trakt_object"]["info"].update(
                self.trakt_api.get_movie_translation(db_object["trakt_id"])
            )

    def _update_movie_tmdb(self, db_object):
        if (
            (self.metadata_location == 1 or self.movies_preferred_art_source == 1)
            and (self._tmdb_needs_update(db_object) or self._force_update(db_object))
            and self._tmdb_id_valid(db_object)
        ):
            if self.metadata_location == 1:
                tools.smart_merge_dictionary(
                    db_object, self.tmdb_api.get_movie(db_object["tmdb_id"])
                )
            elif self.movies_preferred_art_source == 1:
                tools.smart_merge_dictionary(
                    db_object, self.tmdb_api.get_movie_art(db_object["tmdb_id"])
                )

    def _update_movie_fanart(self, db_object):
        if self.fanarttv_api.fanart_support and (
            self._fanart_needs_update(db_object) or self._force_update(db_object)
        ):
            if self._tmdb_id_valid(db_object):
                tools.smart_merge_dictionary(
                    db_object, self.fanarttv_api.get_movie(db_object.get("tmdb_id"))
                )
            if self._imdb_id_valid(db_object) and self._fanart_needs_update(db_object):
                tools.smart_merge_dictionary(
                    db_object, self.fanarttv_api.get_movie(db_object.get("imdb_id"))
                )

    def _update_movie_fallback(self, db_object):
        if (
            self.movies_preferred_art_source == 0
            and not self._fanart_meta_up_to_par("movie", db_object)
            and self._tmdb_id_valid(db_object)
        ):
            tools.smart_merge_dictionary(
                db_object, self.tmdb_api.get_movie_art(db_object["tmdb_id"])
            )
        if self.movies_preferred_art_source == 1 and not self._tmdb_meta_up_to_par(
            "movie", db_object
        ):
            self._update_movie_fanart(db_object)

    def _update_movie_ratings(self, db_object):
        if not tools.safe_dict_get(
            db_object, "tmdb_object", "info"
        ) and self._tmdb_id_valid(db_object):
            tools.smart_merge_dictionary(
                db_object, self.tmdb_api.get_movie_rating(db_object["tmdb_id"])
            )

    def _update_movie_cast(self, db_object):
        if not tools.safe_dict_get(
            db_object, "tmdb_object", "cast"
        ) and self._tmdb_id_valid(db_object):
            tools.smart_merge_dictionary(
                db_object, self.tmdb_api.get_movie_cast(db_object["tmdb_id"])
            )

    # endregion

    # region tvshow
    def _update_tvshow(self, db_object):
        self._update_tvshow_trakt(db_object)
        self._update_tvshow_tmdb(db_object)
        self._update_tvshow_tvdb(db_object)
        self._update_tvshow_fanart(db_object)
        self._update_tvshow_fallback(db_object)
        self._update_tvshow_rating(db_object)
        self._update_tvshow_cast(db_object)

    def _update_tvshow_trakt(self, db_object):
        if (
            self.metadata_location == 0
            and tools.safe_dict_get(db_object, "trakt_object", "info")
            and db_object.get("trakt_id")
        ):
            if (
                tools.safe_dict_get(db_object, "trakt_object", "info", "language")
                and self.trakt_api.language
                != tools.safe_dict_get(db_object, "trakt_object", "info", "language")
                and tools.safe_dict_get(
                    db_object, "trakt_object", "info", "available_translations"
                )
                and self.trakt_api.language
                in tools.safe_dict_get(
                    db_object, "trakt_object", "info", "available_translations"
                )
            ):
                db_object["trakt_object"]["info"].update(
                    self.trakt_api.get_show_translation(db_object["trakt_id"])
                )

            db_object["trakt_object"]["info"][
                "aliases"
            ] = self.trakt_api.get_show_aliases(db_object["trakt_id"])

    def _update_tvshow_tmdb(self, db_object):
        if (
            (self.metadata_location == 1 or self.tvshows_preferred_art_source == 1)
            and (self._tmdb_needs_update(db_object) or self._force_update(db_object))
            and self._tmdb_id_valid(db_object)
        ):
            if self.metadata_location == 1:
                tools.smart_merge_dictionary(
                    db_object, self.tmdb_api.get_show(db_object["tmdb_id"])
                )
            elif self.tvshows_preferred_art_source == 1:
                tools.smart_merge_dictionary(
                    db_object, self.tmdb_api.get_show_art(db_object["tmdb_id"])
                )

    def _update_tvshow_tvdb(self, db_object):
        if (
            (self.metadata_location == 2 or self.tvshows_preferred_art_source == 2)
            and (self._tvdb_needs_update(db_object) or self._force_update(db_object))
            and self._tvdb_id_valid(db_object)
        ):
            if self.metadata_location == 2:
                tools.smart_merge_dictionary(
                    db_object, self.tvdb_api.get_show(db_object["tvdb_id"])
                )
            elif self.tvshows_preferred_art_source == 2:
                tools.smart_merge_dictionary(
                    db_object, self.tvdb_api.get_show_art(db_object["tvdb_id"])
                )

    def _update_tvshow_fanart(self, db_object):
        if (
            self.fanarttv_api.fanart_support
            and (self._fanart_needs_update(db_object) or self._force_update(db_object))
            and self._tvdb_id_valid(db_object)
        ):
            tools.smart_merge_dictionary(
                db_object, self.fanarttv_api.get_show(db_object.get("tvdb_id"))
            )

    def _update_tvshow_fallback(self, db_object):
        if self._tvdb_id_valid(db_object):
            if (
                self.metadata_location == 1
                and not tools.safe_dict_get(db_object, "tmdb_object", "info")
                and not tools.safe_dict_get(db_object, "tvdb_object", "info")
            ):
                tools.smart_merge_dictionary(
                    db_object, self.tvdb_api.get_show(db_object["tvdb_id"])
                )
            if (
                self.tvshows_preferred_art_source != 2
                and not self._tmdb_meta_up_to_par("tvshow", db_object)
                and not self._tvdb_meta_up_to_par("tvshow", db_object)
            ):
                tools.smart_merge_dictionary(
                    db_object, self.tvdb_api.get_show_art(db_object["tvdb_id"])
                )

        if self._tmdb_id_valid(db_object):
            if (
                self.metadata_location == 2
                and not tools.safe_dict_get(db_object, "tmdb_object", "info")
                and not tools.safe_dict_get(db_object, "tvdb_object", "info")
            ):
                tools.smart_merge_dictionary(
                    db_object, self.tmdb_api.get_show(db_object["tmdb_id"])
                )
            if (
                self.tvshows_preferred_art_source != 1
                and not self._tmdb_meta_up_to_par("tvshow", db_object)
                and not self._tvdb_meta_up_to_par("tvshow", db_object)
            ):
                tools.smart_merge_dictionary(
                    db_object, self.tmdb_api.get_show_art(db_object["tmdb_id"])
                )

    def _update_tvshow_rating(self, db_object):
        if not tools.safe_dict_get(
            db_object, "tmdb_object", "info"
        ) and self._tmdb_id_valid(db_object):
            tools.smart_merge_dictionary(
                db_object, self.tmdb_api.get_show_rating(db_object["tmdb_id"])
            )
        if not tools.safe_dict_get(
            db_object, "tvdb_object", "info"
        ) and self._tvdb_id_valid(db_object):
            tools.smart_merge_dictionary(
                db_object, self.tvdb_api.get_show_rating(db_object["tvdb_id"])
            )

    def _update_tvshow_cast(self, db_object):
        if (
            not tools.safe_dict_get(db_object, "tmdb_object", "cast")
            and self._tmdb_id_valid(db_object)
            and not tools.safe_dict_get(db_object, "tvdb_object", "cast")
        ):
            tools.smart_merge_dictionary(
                db_object, self.tmdb_api.get_show_cast(db_object["tmdb_id"])
            )
        if (
            not tools.safe_dict_get(db_object, "tvdb_object", "cast")
            and self._tvdb_id_valid(db_object)
            and not tools.safe_dict_get(db_object, "tmdb_object", "cast")
        ):
            tools.smart_merge_dictionary(
                db_object, self.tvdb_api.get_show_cast(db_object["tvdb_id"])
            )

    # endregion

    # region season
    def _update_season(self, db_object):
        self._update_season_tmdb(db_object)
        self._update_season_tvdb(db_object)
        self._update_season_fanart(db_object)
        self._update_season_fallback(db_object)

    def _update_season_tmdb(self, db_object):
        if (
            (self.metadata_location == 1 or self.tvshows_preferred_art_source == 1)
            and (self._tmdb_needs_update(db_object) or self._force_update(db_object))
            and self._tmdb_show_id_valid(db_object)
        ):
            if self.metadata_location == 1:
                tools.smart_merge_dictionary(
                    db_object,
                    self.tmdb_api.get_season(
                        db_object["tmdb_show_id"],
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "season"
                        ),
                    ),
                )
            elif self.tvshows_preferred_art_source == 1:
                tools.smart_merge_dictionary(
                    db_object,
                    self.tmdb_api.get_season_art(
                        db_object["tmdb_show_id"],
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "season"
                        ),
                    ),
                )

    def _update_season_tvdb(self, db_object):
        if (
            (
                self.tvshows_preferred_art_source == 2
                or not self._tmdb_meta_up_to_par("season", db_object)
            )
            and (self._tvdb_needs_update(db_object) or self._force_update(db_object))
            and self._tvdb_show_id_valid(db_object)
        ):
            tools.smart_merge_dictionary(
                db_object,
                self.tvdb_api.get_season_art(
                    db_object["tvdb_show_id"],
                    tools.safe_dict_get(db_object, "trakt_object", "info", "season"),
                ),
            )

    def _update_season_fanart(self, db_object):
        if (
            self.fanarttv_api.fanart_support
            and (self._fanart_needs_update(db_object) or self._force_update(db_object))
            and self._tvdb_show_id_valid(db_object)
        ):
            tools.smart_merge_dictionary(
                db_object,
                self.fanarttv_api.get_season(
                    db_object.get("tvdb_show_id"),
                    tools.safe_dict_get(db_object, "trakt_object", "info", "season"),
                ),
            )

    def _update_season_fallback(self, db_object):
        if self._tmdb_show_id_valid(db_object):
            if (
                self.metadata_location == 2
                and not tools.safe_dict_get(db_object, "tmdb_object", "info")
                and not tools.safe_dict_get(db_object, "tvdb_object", "info")
            ):
                tools.smart_merge_dictionary(
                    db_object,
                    self.tmdb_api.get_season(
                        db_object["tmdb_show_id"],
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "season"
                        ),
                    ),
                )
            if (
                self.tvshows_preferred_art_source != 1
                and not self._tmdb_meta_up_to_par("season", db_object)
                and not self._tvdb_meta_up_to_par("season", db_object)
            ):
                tools.smart_merge_dictionary(
                    db_object,
                    self.tvdb_api.get_season_art(
                        db_object["tmdb_show_id"],
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "season"
                        ),
                    ),
                )

        if self._tvdb_show_id_valid(db_object):
            if (
                self.tvshows_preferred_art_source != 2
                and not self._tmdb_meta_up_to_par("season", db_object)
                and not self._tvdb_meta_up_to_par("season", db_object)
            ):
                tools.smart_merge_dictionary(
                    db_object,
                    self.tvdb_api.get_season_art(
                        db_object["tvdb_show_id"],
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "season"
                        ),
                    ),
                )

    # endregion

    # region episode
    def _update_episode(self, db_object):
        self._update_episode_tmdb(db_object)
        self._update_episode_tvdb(db_object)
        self._update_episode_fallback(db_object)
        self._update_episode_rating(db_object)

    def _update_episode_tmdb(self, db_object):
        if (
            (self.metadata_location == 1 or self.tvshows_preferred_art_source == 1)
            and (self._tmdb_needs_update(db_object) or self._force_update(db_object))
            and self._tmdb_show_id_valid(db_object)
        ):
            tools.smart_merge_dictionary(
                db_object,
                self.tmdb_api.get_episode(
                    db_object["tmdb_show_id"],
                    tools.safe_dict_get(db_object, "trakt_object", "info", "season"),
                    tools.safe_dict_get(db_object, "trakt_object", "info", "episode"),
                ),
            )

    def _update_episode_tvdb(self, db_object):
        if (
            (self.metadata_location == 2 or self.tvshows_preferred_art_source == 2)
            and (self._tvdb_needs_update(db_object) or self._force_update(db_object))
            and self._tvdb_show_id_valid(db_object)
        ):
            tools.smart_merge_dictionary(
                db_object,
                self.tvdb_api.get_episode(
                    db_object["tvdb_show_id"],
                    tools.safe_dict_get(db_object, "trakt_object", "info", "season"),
                    tools.safe_dict_get(db_object, "trakt_object", "info", "episode"),
                ),
            )

    def _update_episode_fallback(self, db_object):
        if self._tvdb_show_id_valid(db_object):
            if (
                self.metadata_location == 1
                and not tools.safe_dict_get(db_object, "tmdb_object", "info")
                and not tools.safe_dict_get(db_object, "tvdb_object", "info")
            ):
                tools.smart_merge_dictionary(
                    db_object,
                    self.tvdb_api.get_episode(
                        db_object["tvdb_show_id"],
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "season"
                        ),
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "episode"
                        ),
                    ),
                )

        if self._tmdb_show_id_valid(db_object):
            if (
                self.metadata_location == 2
                and not tools.safe_dict_get(db_object, "tmdb_object", "info")
                and not tools.safe_dict_get(db_object, "tvdb_object", "info")
            ):
                tools.smart_merge_dictionary(
                    db_object,
                    self.tmdb_api.get_episode(
                        db_object["tmdb_show_id"],
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "season"
                        ),
                        tools.safe_dict_get(db_object, "trakt_object", "info", "e"),
                    ),
                )
            if (
                self.tvshows_preferred_art_source != 1
                and not self._tmdb_meta_up_to_par("episode", db_object)
                and not self._tvdb_meta_up_to_par("episode", db_object)
            ):
                tools.smart_merge_dictionary(
                    db_object,
                    self.tmdb_api.get_episode_art(
                        db_object["tmdb_show_id"],
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "season"
                        ),
                        tools.safe_dict_get(
                            db_object, "trakt_object", "info", "episode"
                        ),
                    ),
                )

    def _update_episode_rating(self, db_object):
        if not tools.safe_dict_get(
            db_object, "tmdb_object", "info"
        ) and self._tmdb_show_id_valid(db_object):
            tools.smart_merge_dictionary(
                db_object,
                self.tmdb_api.get_episode_rating(
                    db_object["tmdb_show_id"],
                    tools.safe_dict_get(db_object, "trakt_object", "info", "season"),
                    tools.safe_dict_get(db_object, "trakt_object", "info", "episode"),
                ),
            )
        if not tools.safe_dict_get(
            db_object, "tvdb_object", "info"
        ) and self._tvdb_show_id_valid(db_object):
            tools.smart_merge_dictionary(
                db_object,
                self.tvdb_api.get_episode_rating(
                    db_object["tvdb_show_id"],
                    tools.safe_dict_get(db_object, "trakt_object", "info", "season"),
                    tools.safe_dict_get(db_object, "trakt_object", "info", "episode"),
                ),
            )

    # endregion

    # endregion

    # region needs_update
    def _tmdb_needs_update(self, db_object):
        return not db_object.get("tmdb_object") or (
            db_object.get("tmdb_meta_hash")
            and db_object.get("tmdb_meta_hash") != self.tmdb_api.meta_hash
        )

    def _tvdb_needs_update(self, db_object):
        return not db_object.get("tvdb_object") or (
            db_object.get("tvdb_meta_hash")
            and db_object.get("tvdb_meta_hash") != self.tmdb_api.meta_hash
        )

    def _fanart_needs_update(self, db_object):
        return not db_object.get("fanart_object") or (
            db_object.get("fanart_meta_hash")
            and db_object.get("fanart_meta_hash") != self.fanarttv_api.meta_hash
        )

    def _omdb_needs_update(self, db_object):
        return not db_object.get("omdb_object") or (
            db_object.get("omdb_meta_hash")
            and db_object.get("omdb_meta_hash") != self.omdb_api.meta_hash
        )

    # endregion

    # region is_valid

    @staticmethod
    def _tvdb_id_valid(db_object):
        return db_object.get("tvdb_id") is not None

    def _tvdb_show_id_valid(self, db_object):
        return db_object.get("tvdb_show_id") is not None and self._tvdb_id_valid(
            db_object
        )

    @staticmethod
    def _tmdb_id_valid(db_object):
        return db_object.get("tmdb_id") is not None

    def _tmdb_show_id_valid(self, db_object):
        return db_object.get("tmdb_show_id") is not None and self._tmdb_id_valid(
            db_object
        )

    @staticmethod
    def _imdb_id_valid(db_object):
        return db_object.get("imdb_id") is not None

    # endregion

    @staticmethod
    def _force_update(db_object):
        return db_object.get("NeedsUpdate", "false") == "true"

    def _tmdb_meta_up_to_par(self, media_type, item):
        return self.art_meta_up_to_par(media_type, MetadataHandler.tmdb_object(item))

    def _tvdb_meta_up_to_par(self, media_type, item):
        return self.art_meta_up_to_par(media_type, MetadataHandler.tvdb_object(item))

    def _fanart_meta_up_to_par(self, media_type, item):
        return self.art_meta_up_to_par(media_type, MetadataHandler.fanart_object(item))

    @staticmethod
    def full_meta_up_to_par(media_type, item):
        if tools.safe_dict_get(item, "info", "title"):
            return True
        elif MetadataHandler.art_meta_up_to_par(media_type, item):
            return True
        return False

    @staticmethod
    def art_meta_up_to_par(media_type, item):
        try:
            if not item:
                return False
            if media_type in ["tvshow", "season", "movie"] and not tools.safe_dict_get(item, "art", "poster"):
                return False
            if media_type in ["tvshow", "movie"] and not tools.safe_dict_get(item, "art", "fanart"):
                return False
            if (media_type == "episode") and not tools.safe_dict_get(item, "art", "thumb"):
                return False
            return True
        except KeyError:
            return False

    @staticmethod
    def info(data):
        return data.get("info", {})

    @staticmethod
    def art(data):
        return data.get("art", {})

    @staticmethod
    def cast(data):
        return data.get("cast", {})

    @staticmethod
    def trakt_object(data):
        return data.get("trakt_object", {})

    @staticmethod
    def tmdb_object(data):
        return data.get("tmdb_object", {})

    @staticmethod
    def tvdb_object(data):
        return data.get("tvdb_object", {})

    @staticmethod
    def fanart_object(data):
        return data.get("fanart_object", {})

    @staticmethod
    def omdb_object(data):
        return data.get("omdb_object", {})

    @staticmethod
    def trakt_info(data):
        return MetadataHandler.info(MetadataHandler.trakt_object(data))

    @staticmethod
    def tmdb_info(data):
        return MetadataHandler.info(MetadataHandler.tmdb_object(data))

    @staticmethod
    def tvdb_info(data):
        return MetadataHandler.info(MetadataHandler.tvdb_object(data))

    @staticmethod
    def fanart_info(data):
        return MetadataHandler.info(MetadataHandler.fanart_object(data))

    @staticmethod
    def get_trakt_info(data, key, default=None):
        try:
            return MetadataHandler.trakt_info(data).get(key, default)
        except:
            return default

    @staticmethod
    def get_tmdb_info(data, key, default=None):
        try:
            return MetadataHandler.tmdb_info(data).get(key, default)
        except:
            return default

    @staticmethod
    def get_tvdb_info(data, key, default=None):
        try:
            return MetadataHandler.tvdb_info(data).get(key, default)
        except:
            return default

    @staticmethod
    def get_fanart_info(data, key, default=None):
        try:
            return MetadataHandler.fanart_info(data).get(key, default)
        except:
            return default

    @staticmethod
    def pop_trakt_info(data, key, default=None):
        try:
            return MetadataHandler.trakt_info(data).pop(key, default)
        except:
            return default

    @staticmethod
    def pop_tmdb_info(data, key, default=None):
        try:
            return MetadataHandler.tmdb_info(data).pop(key, default)
        except:
            return default

    @staticmethod
    def pop_tvdb_info(data, key, default=None):
        try:
            return MetadataHandler.tvdb_info(data).pop(key, default)
        except:
            return default

    @staticmethod
    def pop_fanart_info(data, key, default=None):
        try:
            return MetadataHandler.fanart_info(data).pop(key, default)
        except:
            return default

    @staticmethod
    def sort_list_items(db_list, trakt_list):
        return [
            t
            for o in trakt_list
            for t in db_list
            if t
            and o
            and tools.safe_dict_get(t, "info", "trakt_id")
            == tools.safe_dict_get(o, "trakt_id")
        ]
