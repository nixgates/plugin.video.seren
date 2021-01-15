# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import threading
import time
import traceback
from collections import OrderedDict
from functools import wraps
from math import sin, pi

import requests
import xbmcgui
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import ApiBase, handle_single_item_or_list
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g


def tvdb_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        method_class = args[0]
        try:
            response = func(*args, **kwarg)
            if response.status_code in [200, 201]:
                return response

            if response.status_code == 401:
                with GlobalLock(
                    "tvdb.oauth", run_once=True, check_sum=method_class.jwToken
                ) as lock:
                    if not lock.runned_once():
                        if method_class.jwToken is not None:
                            method_class.try_refresh_token(True)
                    if method_class.refresh_token is not None:
                        return func(*args, **kwarg)

            g.log(
                "TVDB returned a {} ({}): while requesting {}".format(
                    response.status_code,
                    TVDBAPI.http_codes[response.status_code]
                    if response.status_code != 404
                    else response.json()["Error"],
                    response.url,
                ),
                "warning",
            )
            return None
        except requests.exceptions.ConnectionError:
            return None
        except:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME, g.get_language_string(30025).format("TVDB")
            )
            if g.get_global_setting("run.mode") == "test":
                raise
            return None

    return wrapper


def wrap_tvdb_object(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        return {"tvdb_object": tvdb_art_sorter(func(*args, **kwarg))}

    return wrapper


def tvdb_art_sorter(item):
    if not item or not item.get("art"):
        return item

    for art_type in ["banner", "poster", "fanart"]:
        if art_type not in item.get("art"):
            continue

        item["art"][art_type] = sorted(
            item["art"][art_type], key=lambda k: (k["language"], k["rating"], k["url"]), reverse=True
        )
    return item


class TVDBAPI(ApiBase):
    baseUrl = "https://api.thetvdb.com/"
    normalization = [
        ("imdbId", ("imdbnumber", "imdb_id"), None),
        ("id", "tvdb_id", None),
        (
            None,
            "rating.tvdb",
            (
                ("siteRating", "siteRatingCount"),
                lambda r, c: {"rating": tools.safe_round(r, 2), "votes": c},
            ),
        ),
        ("firstAired", ("premiered", "aired"), lambda t: tools.validate_date(t)),
        ("overview", ("plot", "plotoutline"), None),
        ("mediatype", "mediatype", None),
    ]

    show_normalization = tools.extend_array(
        [
            (
                "firstAired",
                "year",
                lambda t: tools.validate_date(t)[:4]
                if tools.validate_date(t)
                else None,
            ),
            ("status", "status", None),
            ("runtime", "runtime", lambda d: int(d) * 60),
            ("network", "studio", None),
            ("genre", "genre", lambda t: sorted(OrderedDict.fromkeys(t))),
            ("seriesName", ("title", "tvshowtitle"), None),
            ("added", "dateadded", None),
            ("rating", "mpaa", None),
            ("language", "language", None),
            ("aliases", "aliases", None),
            (
                "country",
                "country_origin",
                lambda t: t.upper() if t is not None else None,
            ),
        ],
        normalization,
    )

    episode_normalization = tools.extend_array(
        [
            ("episodeName", "title", None),
            ("seriesId", "tvdb_show_id", None),
            ("airedEpisodeNumber", ("episode", "sortepisode"), None),
            ("airedSeason", ("season", "sortseason"), None),
            ("directors", "director", lambda t: sorted(OrderedDict.fromkeys(t))),
            ("writers", "writer", lambda t: sorted(OrderedDict.fromkeys(t))),
            ("overview", "plot", None),
            ("contentRating", "mpaa", None),
        ],
        normalization,
    )

    meta_objects = {
        "movie": normalization,
        "tvshow": show_normalization,
        "episode": episode_normalization,
    }

    # These are a duplicate of the TMDB codes, should be used as a very rough reference
    # Until we can find a good source from TVDB about their codes we can use this in place
    http_codes = {
        200: "Success",
        201: "Success - new resource created (POST)",
        401: "Returned if your JWT token is missing or expired",
        404: "Returned if the given ID does not exist.",
        409: "Returned if requested record could not be updated/deleted",
        405: "Missing query params are given",
        422: "Invalid query params provided",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    imageBaseUrl = "https://www.thetvdb.com/banners/"
    _threading_lock = threading.Lock()

    art_map = {
        "fanart": "fanart",
        "poster": "poster",
        "season": "poster",
        "seasonwide": "banner",
        "series": "banner",
    }

    supported_languages = [
        {"id": 101, "abbreviation": "aa", "name": "Afaraf", "englishName": "Afar"},
        {
            "id": 102,
            "abbreviation": "ab",
            "name": "аҧсуа бызшәа",
            "englishName": "Abkhaz",
        },
        {
            "id": 103,
            "abbreviation": "af",
            "name": "Afrikaans",
            "englishName": "Afrikaans",
        },
        {"id": 104, "abbreviation": "ak", "name": "Akan", "englishName": "Akan"},
        {"id": 105, "abbreviation": "am", "name": "አማርኛ", "englishName": "Amharic"},
        {"id": 106, "abbreviation": "ar", "name": "العربية", "englishName": "Arabic",},
        {
            "id": 107,
            "abbreviation": "an",
            "name": "aragonés",
            "englishName": "Aragonese",
        },
        {
            "id": 108,
            "abbreviation": "as",
            "name": "অসমীয়া",
            "englishName": "Assamese",
        },
        {
            "id": 109,
            "abbreviation": "av",
            "name": "авар мацӀ",
            "englishName": "Avaric",
        },
        {"id": 110, "abbreviation": "ae", "name": "avesta", "englishName": "Avestan",},
        {
            "id": 111,
            "abbreviation": "ay",
            "name": "aymar aru",
            "englishName": "Aymara",
        },
        {
            "id": 112,
            "abbreviation": "az",
            "name": "azərbaycan dili",
            "englishName": "Azerbaijani",
        },
        {
            "id": 113,
            "abbreviation": "ba",
            "name": "башҡорт теле",
            "englishName": "Bashkir",
        },
        {
            "id": 114,
            "abbreviation": "bm",
            "name": "bamanankan",
            "englishName": "Bambara",
        },
        {
            "id": 115,
            "abbreviation": "be",
            "name": "беларуская мова",
            "englishName": "Belarusian",
        },
        {"id": 116, "abbreviation": "bn", "name": "বাংলা", "englishName": "Bengali",},
        {"id": 117, "abbreviation": "bh", "name": "भोजपुरी", "englishName": "Bihari",},
        {"id": 118, "abbreviation": "bi", "name": "Bislama", "englishName": "Bislama",},
        {
            "id": 119,
            "abbreviation": "bo",
            "name": "བོད་ཡིག",
            "englishName": "Tibetan Standard",
        },
        {
            "id": 120,
            "abbreviation": "bs",
            "name": "bosanski jezik",
            "englishName": "Bosnian",
        },
        {
            "id": 121,
            "abbreviation": "br",
            "name": "brezhoneg",
            "englishName": "Breton",
        },
        {
            "id": 122,
            "abbreviation": "bg",
            "name": "български език",
            "englishName": "Bulgarian",
        },
        {"id": 123, "abbreviation": "ca", "name": "català", "englishName": "Catalan",},
        {"id": 28, "abbreviation": "cs", "name": "čeština", "englishName": "Czech"},
        {
            "id": 124,
            "abbreviation": "ch",
            "name": "Chamoru",
            "englishName": "Chamorro",
        },
        {
            "id": 125,
            "abbreviation": "ce",
            "name": "нохчийн мотт",
            "englishName": "Chechen",
        },
        {
            "id": 126,
            "abbreviation": "cu",
            "name": "ѩзыкъ словѣньскъ",
            "englishName": "Old Church Slavonic",
        },
        {
            "id": 127,
            "abbreviation": "cv",
            "name": "чӑваш чӗлхи",
            "englishName": "Chuvash",
        },
        {
            "id": 128,
            "abbreviation": "kw",
            "name": "Kernewek",
            "englishName": "Cornish",
        },
        {"id": 129, "abbreviation": "co", "name": "corsu", "englishName": "Corsican",},
        {"id": 130, "abbreviation": "cr", "name": "ᓀᐦᐃᔭᐍᐏᐣ", "englishName": "Cree"},
        {"id": 131, "abbreviation": "cy", "name": "Cymraeg", "englishName": "Welsh",},
        {"id": 10, "abbreviation": "da", "name": "dansk", "englishName": "Danish"},
        {"id": 14, "abbreviation": "de", "name": "Deutsch", "englishName": "German",},
        {"id": 132, "abbreviation": "dv", "name": "ދިވެހި", "englishName": "Divehi",},
        {"id": 133, "abbreviation": "dz", "name": "རྫོང་ཁ", "englishName": "Dzongkha",},
        {
            "id": 20,
            "abbreviation": "el",
            "name": "ελληνική γλώσσα",
            "englishName": "Greek",
        },
        {"id": 7, "abbreviation": "en", "name": "English", "englishName": "English",},
        {
            "id": 134,
            "abbreviation": "eo",
            "name": "Esperanto",
            "englishName": "Esperanto",
        },
        {"id": 135, "abbreviation": "et", "name": "eesti", "englishName": "Estonian",},
        {"id": 136, "abbreviation": "eu", "name": "euskara", "englishName": "Basque",},
        {"id": 137, "abbreviation": "ee", "name": "Eʋegbe", "englishName": "Ewe"},
        {
            "id": 138,
            "abbreviation": "fo",
            "name": "føroyskt",
            "englishName": "Faroese",
        },
        {"id": 139, "abbreviation": "fa", "name": "فارسی", "englishName": "Persian",},
        {
            "id": 140,
            "abbreviation": "fj",
            "name": "vosa Vakaviti",
            "englishName": "Fijian",
        },
        {"id": 11, "abbreviation": "fi", "name": "suomi", "englishName": "Finnish"},
        {"id": 17, "abbreviation": "fr", "name": "français", "englishName": "French",},
        {
            "id": 141,
            "abbreviation": "fy",
            "name": "Frysk",
            "englishName": "Western Frisian",
        },
        {"id": 142, "abbreviation": "ff", "name": "Fulfulde", "englishName": "Fula",},
        {
            "id": 143,
            "abbreviation": "gd",
            "name": "Gàidhlig",
            "englishName": "Scottish Gaelic",
        },
        {"id": 144, "abbreviation": "ga", "name": "Gaeilge", "englishName": "Irish",},
        {"id": 145, "abbreviation": "gl", "name": "galego", "englishName": "Galician",},
        {"id": 146, "abbreviation": "gv", "name": "Gaelg", "englishName": "Manx"},
        {"id": 147, "abbreviation": "gn", "name": "Avañe'ẽ", "englishName": "Guaraní",},
        {
            "id": 148,
            "abbreviation": "gu",
            "name": "ગુજરાતી",
            "englishName": "Gujarati",
        },
        {
            "id": 149,
            "abbreviation": "ht",
            "name": "Kreyòl ayisyen",
            "englishName": "Haitian",
        },
        {"id": 150, "abbreviation": "ha", "name": "هَوُسَ", "englishName": "Hausa"},
        {"id": 24, "abbreviation": "he", "name": "עברית", "englishName": "Hebrew"},
        {
            "id": 151,
            "abbreviation": "hz",
            "name": "Otjiherero",
            "englishName": "Herero",
        },
        {"id": 152, "abbreviation": "hi", "name": "हिन्दी", "englishName": "Hindi"},
        {
            "id": 153,
            "abbreviation": "ho",
            "name": "Hiri Motu",
            "englishName": "Hiri Motu",
        },
        {
            "id": 31,
            "abbreviation": "hr",
            "name": "hrvatski jezik",
            "englishName": "Croatian",
        },
        {"id": 19, "abbreviation": "hu", "name": "Magyar", "englishName": "Hungarian",},
        {
            "id": 154,
            "abbreviation": "hy",
            "name": "Հայերեն",
            "englishName": "Armenian",
        },
        {"id": 155, "abbreviation": "ig", "name": "Asụsụ Igbo", "englishName": "Igbo",},
        {"id": 156, "abbreviation": "io", "name": "Ido", "englishName": "Ido"},
        {"id": 157, "abbreviation": "ii", "name": "Nuosuhxop", "englishName": "Nuosu",},
        {
            "id": 158,
            "abbreviation": "iu",
            "name": "ᐃᓄᒃᑎᑐᑦ",
            "englishName": "Inuktitut",
        },
        {
            "id": 159,
            "abbreviation": "ie",
            "name": "Interlingue",
            "englishName": "Interlingue",
        },
        {
            "id": 160,
            "abbreviation": "ia",
            "name": "Interlingua",
            "englishName": "Interlingua",
        },
        {
            "id": 161,
            "abbreviation": "id",
            "name": "Bahasa Indonesia",
            "englishName": "Indonesian",
        },
        {"id": 162, "abbreviation": "ik", "name": "Iñupiaq", "englishName": "Inupiaq",},
        {
            "id": 163,
            "abbreviation": "is",
            "name": "Íslenska",
            "englishName": "Icelandic",
        },
        {"id": 15, "abbreviation": "it", "name": "italiano", "englishName": "Italian",},
        {
            "id": 164,
            "abbreviation": "jv",
            "name": "basa Jawa",
            "englishName": "Javanese",
        },
        {"id": 25, "abbreviation": "ja", "name": "日本語", "englishName": "Japanese"},
        {
            "id": 165,
            "abbreviation": "kl",
            "name": "kalaallisut",
            "englishName": "Kalaallisut",
        },
        {"id": 166, "abbreviation": "kn", "name": "ಕನ್ನಡ", "englishName": "Kannada",},
        {
            "id": 167,
            "abbreviation": "ks",
            "name": "कश्मीरी",
            "englishName": "Kashmiri",
        },
        {
            "id": 168,
            "abbreviation": "ka",
            "name": "ქართული",
            "englishName": "Georgian",
        },
        {"id": 169, "abbreviation": "kr", "name": "Kanuri", "englishName": "Kanuri",},
        {
            "id": 170,
            "abbreviation": "kk",
            "name": "қазақ тілі",
            "englishName": "Kazakh",
        },
        {"id": 171, "abbreviation": "km", "name": "ខ្មែរ", "englishName": "Khmer"},
        {"id": 172, "abbreviation": "ki", "name": "Gĩkũyũ", "englishName": "Kikuyu",},
        {
            "id": 173,
            "abbreviation": "rw",
            "name": "Ikinyarwanda",
            "englishName": "Kinyarwanda",
        },
        {
            "id": 174,
            "abbreviation": "ky",
            "name": "кыргыз тили",
            "englishName": "Kirghiz",
        },
        {"id": 175, "abbreviation": "kv", "name": "коми кыв", "englishName": "Komi",},
        {"id": 176, "abbreviation": "kg", "name": "KiKongo", "englishName": "Kongo",},
        {"id": 32, "abbreviation": "ko", "name": "한국어", "englishName": "Korean"},
        {
            "id": 177,
            "abbreviation": "kj",
            "name": "Kuanyama",
            "englishName": "Kwanyama",
        },
        {"id": 178, "abbreviation": "ku", "name": "Kurdî", "englishName": "Kurdish",},
        {"id": 179, "abbreviation": "lo", "name": "ພາສາລາວ", "englishName": "Lao"},
        {"id": 180, "abbreviation": "la", "name": "latine", "englishName": "Latin"},
        {
            "id": 181,
            "abbreviation": "lv",
            "name": "latviešu valoda",
            "englishName": "Latvian",
        },
        {
            "id": 182,
            "abbreviation": "li",
            "name": "Limburgs",
            "englishName": "Limburgish",
        },
        {"id": 183, "abbreviation": "ln", "name": "Lingála", "englishName": "Lingala",},
        {
            "id": 184,
            "abbreviation": "lt",
            "name": "lietuvių kalba",
            "englishName": "Lithuanian",
        },
        {
            "id": 185,
            "abbreviation": "lb",
            "name": "Lëtzebuergesch",
            "englishName": "Luxembourgish",
        },
        {
            "id": 186,
            "abbreviation": "lu",
            "name": "Luba-Katanga",
            "englishName": "Luba-Katanga",
        },
        {"id": 187, "abbreviation": "lg", "name": "Luganda", "englishName": "Luganda",},
        {
            "id": 188,
            "abbreviation": "mh",
            "name": "Kajin M̧ajeļ",
            "englishName": "Marshallese",
        },
        {
            "id": 189,
            "abbreviation": "ml",
            "name": "മലയാളം",
            "englishName": "Malayalam",
        },
        {"id": 190, "abbreviation": "mr", "name": "मराठी", "englishName": "Marathi",},
        {
            "id": 191,
            "abbreviation": "mk",
            "name": "македонски јазик",
            "englishName": "Macedonian",
        },
        {
            "id": 192,
            "abbreviation": "mg",
            "name": "Malagasy fiteny",
            "englishName": "Malagasy",
        },
        {"id": 193, "abbreviation": "mt", "name": "Malti", "englishName": "Maltese",},
        {
            "id": 194,
            "abbreviation": "mn",
            "name": "монгол",
            "englishName": "Mongolian",
        },
        {
            "id": 195,
            "abbreviation": "mi",
            "name": "te reo Māori",
            "englishName": "Māori",
        },
        {
            "id": 196,
            "abbreviation": "ms",
            "name": "bahasa Melayu",
            "englishName": "Malay",
        },
        {"id": 197, "abbreviation": "my", "name": "Burmese", "englishName": "Burmese",},
        {
            "id": 198,
            "abbreviation": "na",
            "name": "Ekakairũ Naoero",
            "englishName": "Nauru",
        },
        {
            "id": 199,
            "abbreviation": "nv",
            "name": "Diné bizaad",
            "englishName": "Navajo",
        },
        {
            "id": 200,
            "abbreviation": "nr",
            "name": "isiNdebele",
            "englishName": "South Ndebele",
        },
        {
            "id": 201,
            "abbreviation": "nd",
            "name": "isiNdebele",
            "englishName": "North Ndebele",
        },
        {"id": 202, "abbreviation": "ng", "name": "Owambo", "englishName": "Ndonga",},
        {"id": 203, "abbreviation": "ne", "name": "नेपाली", "englishName": "Nepali",},
        {"id": 13, "abbreviation": "nl", "name": "Nederlands", "englishName": "Dutch",},
        {
            "id": 9,
            "abbreviation": "no",
            "name": "Norsk bokmål",
            "englishName": "Norwegian",
        },
        {
            "id": 206,
            "abbreviation": "ny",
            "name": "chiCheŵa",
            "englishName": "Chichewa",
        },
        {"id": 207, "abbreviation": "oc", "name": "occitan", "englishName": "Occitan",},
        {"id": 208, "abbreviation": "oj", "name": "ᐊᓂᔑᓈᐯᒧᐎᓐ", "englishName": "Ojibwe",},
        {"id": 209, "abbreviation": "or", "name": "ଓଡ଼ିଆ", "englishName": "Oriya"},
        {
            "id": 210,
            "abbreviation": "om",
            "name": "Afaan Oromoo",
            "englishName": "Oromo",
        },
        {
            "id": 211,
            "abbreviation": "os",
            "name": "ирон æвзаг",
            "englishName": "Ossetian",
        },
        {"id": 212, "abbreviation": "pa", "name": "ਪੰਜਾਬੀ", "englishName": "Panjabi",},
        {"id": 213, "abbreviation": "pi", "name": "पाऴि", "englishName": "Pāli"},
        {
            "id": 18,
            "abbreviation": "pl",
            "name": "język polski",
            "englishName": "Polish",
        },
        {
            "id": 214,
            "abbreviation": "pt",
            "name": "Português - Portugal",
            "englishName": "Portuguese - Portugal",
        },
        {
            "id": 26,
            "abbreviation": "pt",
            "name": "Português - Brasil",
            "englishName": "Portuguese - Brazil",
        },
        {"id": 215, "abbreviation": "ps", "name": "پښتو", "englishName": "Pashto"},
        {
            "id": 216,
            "abbreviation": "qu",
            "name": "Runa Simi",
            "englishName": "Quechua",
        },
        {
            "id": 217,
            "abbreviation": "rm",
            "name": "rumantsch grischun",
            "englishName": "Romansh",
        },
        {
            "id": 218,
            "abbreviation": "ro",
            "name": "limba română",
            "englishName": "Romanian",
        },
        {
            "id": 219,
            "abbreviation": "rn",
            "name": "Ikirundi",
            "englishName": "Kirundi",
        },
        {
            "id": 22,
            "abbreviation": "ru",
            "name": "русский язык",
            "englishName": "Russian",
        },
        {
            "id": 220,
            "abbreviation": "sg",
            "name": "yângâ tî sängö",
            "englishName": "Sango",
        },
        {
            "id": 221,
            "abbreviation": "sa",
            "name": "संस्कृतम्",
            "englishName": "Sanskrit",
        },
        {"id": 222, "abbreviation": "si", "name": "සිංහල", "englishName": "Sinhala",},
        {
            "id": 30,
            "abbreviation": "sk",
            "name": "slovenčina",
            "englishName": "Slovak",
        },
        {
            "id": 223,
            "abbreviation": "sl",
            "name": "slovenski jezik",
            "englishName": "Slovene",
        },
        {
            "id": 224,
            "abbreviation": "se",
            "name": "Davvisámegiella",
            "englishName": "Northern Sami",
        },
        {
            "id": 225,
            "abbreviation": "sm",
            "name": "gagana fa'a Samoa",
            "englishName": "Samoan",
        },
        {"id": 226, "abbreviation": "sn", "name": "chiShona", "englishName": "Shona",},
        {"id": 227, "abbreviation": "sd", "name": "सिन्धी", "englishName": "Sindhi",},
        {
            "id": 228,
            "abbreviation": "so",
            "name": "Soomaaliga",
            "englishName": "Somali",
        },
        {
            "id": 229,
            "abbreviation": "st",
            "name": "Sesotho",
            "englishName": "Southern Sotho",
        },
        {"id": 16, "abbreviation": "es", "name": "español", "englishName": "Spanish",},
        {
            "id": 230,
            "abbreviation": "sq",
            "name": "gjuha shqipe",
            "englishName": "Albanian",
        },
        {"id": 231, "abbreviation": "sc", "name": "sardu", "englishName": "Sardinian",},
        {
            "id": 232,
            "abbreviation": "sr",
            "name": "српски језик",
            "englishName": "Serbian",
        },
        {"id": 233, "abbreviation": "ss", "name": "SiSwati", "englishName": "Swati",},
        {
            "id": 234,
            "abbreviation": "su",
            "name": "Basa Sunda",
            "englishName": "Sundanese",
        },
        {
            "id": 235,
            "abbreviation": "sw",
            "name": "Kiswahili",
            "englishName": "Swahili",
        },
        {"id": 8, "abbreviation": "sv", "name": "svenska", "englishName": "Swedish",},
        {
            "id": 236,
            "abbreviation": "ty",
            "name": "Reo Tahiti",
            "englishName": "Tahitian",
        },
        {"id": 237, "abbreviation": "ta", "name": "தமிழ்", "englishName": "Tamil"},
        {
            "id": 238,
            "abbreviation": "tt",
            "name": "татар теле",
            "englishName": "Tatar",
        },
        {"id": 239, "abbreviation": "te", "name": "తెలుగు", "englishName": "Telugu",},
        {"id": 240, "abbreviation": "tg", "name": "тоҷикӣ", "englishName": "Tajik"},
        {
            "id": 241,
            "abbreviation": "tl",
            "name": "Wikang Tagalog",
            "englishName": "Tagalog",
        },
        {"id": 242, "abbreviation": "th", "name": "ไทย", "englishName": "Thai"},
        {"id": 243, "abbreviation": "ti", "name": "ትግርኛ", "englishName": "Tigrinya",},
        {
            "id": 244,
            "abbreviation": "to",
            "name": "faka Tonga",
            "englishName": "Tonga",
        },
        {"id": 245, "abbreviation": "tn", "name": "Setswana", "englishName": "Tswana",},
        {"id": 246, "abbreviation": "ts", "name": "Xitsonga", "englishName": "Tsonga",},
        {"id": 247, "abbreviation": "tk", "name": "Türkmen", "englishName": "Turkmen",},
        {"id": 21, "abbreviation": "tr", "name": "Türkçe", "englishName": "Turkish",},
        {"id": 248, "abbreviation": "tw", "name": "Twi", "englishName": "Twi"},
        {"id": 249, "abbreviation": "ug", "name": "Uyƣurqə", "englishName": "Uighur",},
        {
            "id": 250,
            "abbreviation": "uk",
            "name": "українська мова",
            "englishName": "Ukrainian",
        },
        {"id": 251, "abbreviation": "ur", "name": "اردو", "englishName": "Urdu"},
        {"id": 252, "abbreviation": "uz", "name": "Ozbek", "englishName": "Uzbek"},
        {"id": 253, "abbreviation": "ve", "name": "Tshivenḓa", "englishName": "Venda",},
        {
            "id": 254,
            "abbreviation": "vi",
            "name": "Tiếng Việt",
            "englishName": "Vietnamese",
        },
        {"id": 255, "abbreviation": "vo", "name": "Volapük", "englishName": "Volapük",},
        {"id": 256, "abbreviation": "wa", "name": "walon", "englishName": "Walloon",},
        {"id": 257, "abbreviation": "wo", "name": "Wollof", "englishName": "Wolof"},
        {"id": 258, "abbreviation": "xh", "name": "isiXhosa", "englishName": "Xhosa",},
        {"id": 259, "abbreviation": "yi", "name": "ייִדיש", "englishName": "Yiddish",},
        {"id": 260, "abbreviation": "yo", "name": "Yorùbá", "englishName": "Yoruba",},
        {
            "id": 261,
            "abbreviation": "za",
            "name": "Saɯ cueŋƅ",
            "englishName": "Zhuang",
        },
        {
            "id": 27,
            "abbreviation": "zh",
            "name": "大陆简体",
            "englishName": "Chinese - China",
        },
        {"id": 262, "abbreviation": "zu", "name": "isiZulu", "englishName": "Zulu"},
    ]

    def __init__(self):
        self.apiKey = g.get_setting("tvdb.apikey", "43VPI0R8323FB7TI")
        self.jwToken = g.get_setting("tvdb.jw")
        self.tokenExpires = g.get_float_setting("tvdb.expiry")
        self.lang_code = g.get_language_code(False)

        self.languages = (
            [None, self.lang_code]
            if self.lang_code != "en"
            and any(
                self.lang_code == i["abbreviation"] for i in self.supported_languages
            )
            else [None]
        )

        if not self.jwToken:
            self.init_token()
        else:
            self.try_refresh_token()

        self.preferred_artwork_size = g.get_int_setting("artwork.preferredsize")
        self.meta_hash = tools.md5_hash(
            (
                self.lang_code,
                self.art_map,
                self.baseUrl,
                self.imageBaseUrl,
                self.preferred_artwork_size,
            )
        )

    def _get_headers(self, lang=None):
        headers = {"content-type": "application/json"}

        if self.jwToken:
            headers["Authorization"] = "Bearer {}".format(self.jwToken)
        if lang is not None:
            headers["Accept-Language"] = lang
        return headers

    def try_refresh_token(self, force=False):
        if not force and self.tokenExpires >= float(time.time()):
            return
        with GlobalLock(
            self.__class__.__name__, self._threading_lock, True, self.jwToken
        ) as lock:
            if lock.runned_once():
                return
            try:
                g.log("TVDB Token requires refreshing...")
                response = self.session.post(
                    tools.urljoin(self.baseUrl, "refresh_token"),
                    headers=self._get_headers(),
                ).json()
                if "Error" in response:
                    response = self.session.post(
                        self.baseUrl + "login",
                        json={"apikey": self.apiKey},
                        headers=self._get_headers(),
                    ).json()
                self._save_settings(response)
                g.log("Refreshed Tvdbs Token")
            except:
                g.log("Failed to refresh Tvdb Access Token", "error")
                return

    def _save_settings(self, response):
        if "token" in response:
            g.set_setting("tvdb.jw", response["token"])
            self.jwToken = response["token"]
            self.tokenExpires = time.time() + (24 * (60 * 60))
            g.set_setting("tvdb.expiry", str(self.tokenExpires))

    def init_token(self):
        with GlobalLock(self.__class__.__name__, self._threading_lock, True) as lock:
            if lock.runned_once():
                return
            response = self.session.post(
                self.baseUrl + "login",
                json={"apikey": self.apiKey},
                headers=self._get_headers(),
            ).json()
            self._save_settings(response)

    @tvdb_guard_response
    def get(self, url, **params):
        if "language" in params:
            language = params.pop("language")
        else:
            language = None
        return self.session.get(
            self.baseUrl + url,
            params=params,
            headers=self._get_headers(language),
            timeout=3,
        )

    @staticmethod
    def _flatten(response):
        if "data" in response:
            response = response["data"]
        if not response:
            return None
        return response

    def get_json(self, url, **params):
        response = self.get(url, **params)
        if response is None:
            return None
        try:
            return self._handle_response(
                params.get("language"), self._flatten(response.json())
            )
        except (ValueError, AttributeError):
            traceback.print_exc()
            g.log(
                "Failed to receive JSON from Tvdb response - response: {}".format(
                    response
                ),
                "error",
            )
            return None

    @use_cache()
    def get_json_cached(self, url, **params):
        return self.get_json(url, **params)

    @staticmethod
    def _get_all_pages(func, url, **params):
        if "progress" in params:
            progress_callback = params.pop("progress")
        else:
            progress_callback = None
        response = func(url, **params)
        yield response
        if "links" not in response.headers:
            return
        for i in range(2, int(response.headers["X-Pagination-Page-Count"]) + 1):
            if progress_callback is not None:
                progress_callback(
                    (i / (int(response.headers["X-Pagination-Page-Count"]) + 1)) * 100
                )
            params.update({"page": i})
            yield func(url, **params)

    @handle_single_item_or_list
    def _handle_response(self, language, item):
        result = {}
        item = self._try_detect_type(item)
        if "mediatype" not in item:
            return item

        result.update({"art": self._extract_art(item, language)})
        result.update(
            {"info": self._normalize_info(self.meta_objects[item["mediatype"]], item)}
        )
        return result

    @handle_single_item_or_list
    def _handle_cast(self, item):
        if item is None or "name" not in item:
            return {}
        return {
            "name": item["name"],
            "role": item["role"],
            "thumbnail": self._get_absolute_image_path(item["image"]),
            "order": item["sortOrder"],
        }

    @staticmethod
    def _try_detect_type(item):
        if "airedSeasons" in item or "seriesName" in item:
            item.update({"mediatype": "tvshow"})
        elif "episodeName" in item:
            item.update({"mediatype": "episode"})
        return item

    def _extract_art(self, item, language, key_name=None, sub_key=None):
        result = {}
        if item is None:
            return result

        if not isinstance(item, (list, set)):
            if item.get("filename"):
                result.update(
                    {"thumb": self._get_absolute_image_path(item["filename"])}
                )

        if key_name is not None and isinstance(item, (set, list)):
            art = [
                self._get_image(i, self.art_map[key_name], language)
                for i in item
                if "fileName" in i
                and i.get("keyType") == key_name
                and (sub_key is None or i.get("subKey") == str(sub_key))
            ]

            if len(art) > 0:
                result.update({self.art_map[key_name]: art})
        return result

    @staticmethod
    def _get_rating(image):
        if image["ratingsInfo"]["count"]:
            info = image["ratingsInfo"]
            rating = info["average"]
            if info["count"] < 5:
                rating = 5 + (rating - 5) * sin(info["count"] / pi)
            return rating
        else:
            return 5

    @staticmethod
    def _parse_size(image, art_type):
        if art_type in ("series", "seasonwide"):
            return 758
        elif art_type == "season":
            return 1000
        try:
            return int(image["resolution"].split("x")[0 if art_type != "poster" else 1])
        except (ValueError, IndexError):
            return 0

    def _get_image(self, image, art_type, language):
        return {
            "url": self._get_absolute_image_path(image["fileName"]),
            "language": language if language else "en",
            "rating": self._get_rating(image),
            "size": self._parse_size(image, art_type),
        }

    @wrap_tvdb_object
    def get_show(self, tvdb_id):
        item = {}

        art_types = self._get_show_art_types(tvdb_id)
        if art_types:
            art_types = [i for i in art_types if not i.startswith("season")]

        else:
            art_types = []

        thread_pool = ThreadPool()
        thread_pool.put(self._get_series_cast, tvdb_id)
        for language in self.languages:
            thread_pool.put(self._get_show_info, tvdb_id, language)
            for art_type in art_types:
                thread_pool.put(self._get_show_art, tvdb_id, art_type, language)
            item = tools.smart_merge_dictionary(item, thread_pool.wait_completion())
        if not item or len(item.keys()) == 0:
            return None
        return item

    @wrap_tvdb_object
    def get_show_art(self, tvdb_id):
        item = {}

        art_types = self._get_show_art_types(tvdb_id)
        if art_types:
            art_types = [i for i in art_types if not i.startswith("season")]
        else:
            art_types = []

        thread_pool = ThreadPool()
        for language in self.languages:
            for art_type in art_types:
                thread_pool.put(self._get_show_art, tvdb_id, art_type, language)
            item = tools.smart_merge_dictionary(item, thread_pool.wait_completion())
        if not item or len(item.keys()) == 0:
            return None
        return item

    @wrap_tvdb_object
    def get_show_info(self, tvdb_id):
        item = {}
        thread_pool = ThreadPool()
        thread_pool.put(self._get_series_cast, tvdb_id)
        for language in self.languages:
            thread_pool.put(self._get_show_info, tvdb_id, language)
            item = tools.smart_merge_dictionary(item, thread_pool.wait_completion())
        if not item or len(item.keys()) == 0:
            return None
        return item

    @wrap_tvdb_object
    def get_show_rating(self, tvdb_id):
        item = self.get_json(
            "series/{}/filter".format(tvdb_id),
            keys="siteRating,siteRatingCount,seriesName",
        )

        if not item or len(item.keys()) == 0:
            return None

        return {"info": tools.filter_dictionary(item["info"], "rating")}

    @wrap_tvdb_object
    def get_show_cast(self, tvdb_id):
        cast = self._get_series_cast(tvdb_id)
        if cast.get("cast"):
            return cast
        else:
            return None

    @use_cache()
    def _get_show_art_types(self, tvdb_id):
        result = self.get_json("series/{}/images/query/params".format(tvdb_id))
        return (
            result
            if not result
            else sorted([i["keyType"] for i in result if "keyType" in i])
        )

    def _get_show_art(self, tvdb_id, key_type, language):
        return {
            "art": self._extract_art(
                self.get_json(
                    "series/{}/images/query?keyType={}".format(tvdb_id, key_type),
                    language=language,
                ),
                language,
                key_type,
            )
        }

    def _get_show_info(self, tvdb_id, language):
        return self.get_json("series/{}".format(tvdb_id), language=language)

    def _get_series_cast(self, tvdb_id):
        return {
            "cast": self._handle_cast(self.get_json("series/{}/actors".format(tvdb_id)))
        }

    @wrap_tvdb_object
    def get_season_art(self, tvdb_id, season):
        item = {}
        art_types = self._get_show_art_types(tvdb_id)
        if not art_types:
            return None
        art_types = [i for i in art_types if i.startswith("season")]
        thread_pool = ThreadPool()
        for language in self.languages:
            for art_type in art_types:
                thread_pool.put(
                    self._get_season_art, tvdb_id, art_type, season, language
                )
            item = tools.smart_merge_dictionary(item, thread_pool.wait_completion())
        if not item or len(item.keys()) == 0:
            return None
        return item

    def _get_season_art(self, tvdb_id, art_name, season, language):
        return {
            "art": self._extract_art(
                self.get_json_cached(
                    "series/{}/images/query".format(tvdb_id),
                    keyType=art_name,
                    language=language,
                ),
                language,
                art_name,
                season,
            )
        }

    def _get_episode_info(self, tvdb_id, season, episode, language):
        result = self.get_json(
            "series/{}/episodes/query".format(tvdb_id),
            airedSeason=season,
            airedEpisode=episode,
            language=language,
        )

        if result is None:
            return None
        if isinstance(result, (list, set)):
            return next(iter(result))
        return result

    @wrap_tvdb_object
    def get_episode(self, tvdb_id, season, episode):
        item = {}
        thread_pool = ThreadPool()
        for language in self.languages:
            thread_pool.put(self._get_episode_info, tvdb_id, season, episode, language)
            item = tools.smart_merge_dictionary(item, thread_pool.wait_completion())
        if not item or len(item.keys()) == 0:
            return None
        return item

    @wrap_tvdb_object
    def get_episode_rating(self, tvdb_id, season, episode):
        item = self._get_episode_info(tvdb_id, season, episode, None)

        if not item or len(item.keys()) == 0:
            return None

        return {"info": tools.filter_dictionary(item["info"], "rating")}

    def _get_absolute_image_path(self, relative_path):
        if not relative_path:
            return None
        if self.preferred_artwork_size > 1:
            splitted_path = relative_path.split(".")
            relative_path = "{}_t.{}".format(splitted_path[0], splitted_path[1])
        return "/".join([self.imageBaseUrl.strip("/"), relative_path.strip("/")])
