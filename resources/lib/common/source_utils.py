"""
Module for common utilities that may be used when working with source items
"""
import contextlib
import re
import string

from resources.lib.modules.globals import g

BROWSER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537."
    "36 Edge/12.246",
    "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) "
    "Version/9.0.2 Safari/601.3.9"
    "Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
]

exclusions = ["soundtrack", "gesproken"]
_APOSTROPHE_SUBS = re.compile(r"\\'s|'s|&#039;s| 039 s")
_SEPARATORS = re.compile(r'[:|/,!?()"[\]\-\\_.{}]|(?<![:|/,!?()"[\]\-\\_.{}\s]dd)\+')
_WHITESPACE = re.compile(r'\s+')
_SINGLE_QUOTE = re.compile(r"['`]")
_AMPERSAND = re.compile(r'&#038;|&amp;|&')
_EPISODE_NUMBERS = re.compile(r'.*((?:s\d+ ?e\d+ )|(?:season ?\d+ ?(?:episode|ep) ?\d+)|(?: \d+ ?x ?\d+ ))')
_ASCII_NON_PRINTABLE = re.compile(fr'[^{re.escape(string.printable)}]')


class CannotGenerateRegexFilterException(Exception):
    """Exception used when there is no valid input for generating the regex filters."""

    pass


def get_quality(release_title):
    """
    Identifies resolution based on release title information
    :param release_title: sources release title
    :return: stringed resolution
    """
    release_title = release_title.lower()

    if any(q in release_title for q in ["720", "72o"]):
        return "720p"
    if any(q in release_title for q in ["1080", "1o80", "108o", "1o8o"]):
        return "1080p"
    if any(q in release_title for q in ["2160", "216o"]):
        return "4K"
    with contextlib.suppress(ValueError, IndexError):
        if not release_title[release_title.index("4k") + 2].isalnum():
            return "4K"
    return "SD"


INFO_STRUCT = {
    "videocodec": {
        "AVC",
        "HEVC",
        "XVID",
        "DIVX",
        "WMV",
        "MP4",
        "MPEG",
        "VP9",
        "AV1",
    },
    "hdrcodec": {
        "DV",
        "HDR",
        "HYBRID",
        "SDR",
    },
    "audiocodec": {
        "AAC",
        "DTS",
        "DTS-HD",
        "DTS-HDHR",
        "DTS-HDMA",
        "DTS-X",
        "ATMOS",
        "TRUEHD",
        "DD+",
        "DD",
        "MP3",
        "WMA",
        "OPUS",
    },
    "audiochannels": {
        "2.0",
        "5.1",
        "7.1",
    },
    "misc": {
        "CAM",
        "HDTV",
        "PDTV",
        "REMUX",
        "HD-RIP",
        "BLURAY",
        "DVDRIP",
        "WEB",
        "HC",
        "SCR",
        "3D",
        "60-FPS"
    },
}


def info_set_to_dict(info_set):
    """
    Converts an info set to a structured dictionary
    :param info_set: info set built with get_info
    :return: structured dictionary
    """
    return {info_prop: sorted(list(info_set & codecs)) for info_prop, codecs in INFO_STRUCT.items()}


INFO_TYPES = {
    "AVC": ["x264", "x 264", "h264", "h 264", "avc"],
    "HEVC": ["x265", "x 265", "h265", "h 265", "hevc"],
    "XVID": ["xvid"],
    "DIVX": ["divx"],
    "MP4": ["mp4"],
    "WMV": ["wmv"],
    "MPEG": ["mpeg"],
    "VP9": ["vp9"],
    "AV1": ["av1"],
    "REMUX": ["remux", "bdremux"],
    "DV": [" dv ", "dovi", "dolby vision", "dolbyvision"],
    "HDR": [
        " hdr ",
        "hdr10",
        "hdr 10",
        "uhd bluray 2160p",
        "uhd blu ray 2160p",
        "2160p uhd bluray",
        "2160p uhd blu ray",
        "2160p bluray hevc truehd",
        "2160p bluray hevc dts",
        "2160p bluray hevc lpcm",
        "2160p us bluray hevc truehd",
        "2160p us bluray hevc dts",
    ],
    "SDR": [" sdr"],
    "AAC": ["aac"],
    "DTS-HDMA": ["hd ma", "hdma"],
    "DTS-HDHR": ["hd hr", "hdhr", "dts hr", "dtshr"],
    "DTS-X": ["dtsx", " dts x"],
    "ATMOS": ["atmos"],
    "TRUEHD": ["truehd", "true hd"],
    "DD+": ["ddp", "eac3", " e ac3", " e ac 3", "dd+", "digital plus", "digitalplus"],
    "DD": [" dd ", "dd2", "dd5", "dd7", " ac3", " ac 3", "dolby digital", "dolbydigital", "dolby5"],
    "MP3": ["mp3"],
    "WMA": [" wma"],
    "2.0": ["2 0 ", "2 0ch", "2ch"],
    "5.1": ["5 1 ", "5 1ch", "6ch"],
    "7.1": ["7 1 ", "7 1ch", "8ch"],
    "BLURAY": ["bluray", "blu ray", "bdrip", "bd rip", "brrip", "br rip", "bdmux"],
    "WEB": [" web ", "webrip", "webdl", "web rip", "web dl", "webmux", "dlmux"],
    "HD-RIP": [" hdrip", " hd rip"],
    "DVDRIP": ["dvdrip", "dvd rip"],
    "HDTV": ["hdtv"],
    "PDTV": ["pdtv"],
    "CAM": [
        " cam ",
        "camrip",
        "cam rip",
        "hdcam",
        "hd cam",
        " ts ",
        " ts1",
        " ts7",
        "hd ts",
        "hdts",
        "telesync",
        " tc ",
        " tc1",
        " tc7",
        "hd tc",
        "hdtc",
        "telecine",
        "xbet",
        "hcts",
        "hc ts",
        "hctc",
        "hc tc",
        "hqcam",
        "hq cam",
    ],
    "SCR": ["scr ", "screener"],
    "HC": [
        "korsub",
        " kor ",
        " hc ",
        "hcsub",
        "hcts",
        "hctc",
        "hchdrip",
        "hardsub",
        "hard sub",
        "sub hard",
        "hardcode",
        "hard code",
        "vostfr",
        "vo stfr",
    ],
    "3D": [" 3d", " half ou", " half sbs"],
    "60-FPS": [" 60 fps", " 60fps"]
}


def get_info(release_title):
    """
    Identifies and retrieves a list of information based on release title of source
    :param release_title: Release title of source
    :return: List of info meta
    """
    title = f"{clean_title(release_title)} "
    info = {info_prop for info_prop, string_list in INFO_TYPES.items() if any(i in title for i in string_list)}
    if all(i in info for i in ["SDR", "HDR"]):
        info.remove("HDR")
    elif all(i in title for i in ["2160p", "remux"]) and all(i not in info for i in ["HDR", "SDR"]):
        info.add("HDR")
    elif "DV" in info and "hybrid" in title and all(i not in info for i in ["HDR", "SDR"]):
        info.add("HDR")
    if all(i in info for i in ["HDR", "DV"]) and all(i not in title for i in ["hybrid", " hdr"]):
        info.remove("HDR")
    if all(i in info for i in ["HDR", "DV"]):
        info.add("HYBRID")
    if any(i in info for i in ["HDR", "DV"]) and all(i not in info for i in ["HEVC", "AVC", "AV1", "VP9"]):
        info.add("HEVC")
    if all(i in info for i in ["DD", "DD+"]):
        info.remove("DD")
    elif any(i in title for i in ["dtshd", "dts hd"]) and all(i not in info for i in ["DTS-HDMA", "DTS-HDHR"]):
        info.add("DTS-HD")
    elif " dts" in title and all(i not in info for i in ["DTS-HDMA", "DTS-HDHR", "DTS-X", "DTS-HD"]):
        info.add("DTS")
    if all(i in title for i in ["sub", "forced"]):
        info.add("HC")
    if "opus" in title and "AV1" in info:
        info.add("OPUS")
    return info


def strip_non_ascii_and_unprintable(text):
    """
    Stirps non ascii and unprintable characters from string
    :param text: text to clean
    :return: cleaned text
    """
    return _ASCII_NON_PRINTABLE.sub("", text)


def clean_title(title, broken=None):
    """
    Returns a cleaned version of the provided title
    :param title: title to be cleaned
    :param broken: set to 1 to remove apostophes, 2 to replace with spaces
    :return: cleaned title
    """
    title = g.deaccent_string(title)
    title = strip_non_ascii_and_unprintable(title)
    title = title.lower()

    apostrophe_replacement = "s"
    if broken == 1:
        apostrophe_replacement = ""
    elif broken == 2:
        apostrophe_replacement = " s"

    title = _APOSTROPHE_SUBS.sub(apostrophe_replacement, title)

    title = _SINGLE_QUOTE.sub("", title)
    title = _SEPARATORS.sub(" ", title)
    title = _WHITESPACE.sub(" ", title)
    title = _AMPERSAND.sub("and", title)

    return title.strip()


def remove_from_title(title, target, clean=True):
    """
    Strips provided string from given title
    :param title: release title
    :param target: the string to be stripped
    :param clean: if true, performs a title clean
    :return: stripped title
    """
    if not target:
        return title

    title = title.replace(f" {str(target).lower()} ", " ")
    title = title.replace(f".{str(target).lower()}.", " ")
    title = title.replace(f"+{str(target).lower()}+", " ")
    title = title.replace(f"-{str(target).lower()}-", " ")
    if clean:
        title = f"{clean_title(title)} "
    else:
        title += " "

    return re.sub(r"\s+", " ", title)


def remove_country(title, country, clean=True):
    """
    Strips country from title
    :param title: title to strip from
    :param country: country of item
    :param clean: set to True if the title should be cleaned as well
    :return: processed title
    """
    title = title.lower()
    if title is None or country is None:
        return title

    if isinstance(country, (list, set)):
        for c in country:
            title = _remove_country(clean, c.lower(), title)
    else:
        title = _remove_country(clean, country.lower(), title)

    return title


def _remove_country(clean, country, title):
    if country in ["gb", "uk"]:
        title = remove_from_title(title, "gb", clean)
        title = remove_from_title(title, "uk", clean)
    else:
        title = remove_from_title(title, country, clean)
    return title


def _get_regex_pattern(titles, suffixes_list, non_escaped_suffixes=None):
    pattern = r"^(?:"
    for title in titles:
        title = title.strip()
        if len(title) > 0:
            pattern += f"{re.escape(title)} |"
    pattern = f"{pattern[:-1]})+(?:"
    for suffix in suffixes_list:
        suffix = suffix.strip()
        if len(suffix) > 0:
            pattern += f"{re.escape(suffix)}|"
    if non_escaped_suffixes:
        for suffix in non_escaped_suffixes:
            pattern += f"{suffix}|"
    pattern = f"{pattern[:-1]})+"
    return re.compile(pattern)


def check_title_match(title_parts, release_title, simple_info):
    """
    Performs cleaning of title and attempts to do a simple matching of title
    :param title_parts: stringed/listed version of title
    :param release_title: sources release title
    :param simple_info: simplified meta data of item
    :return:
    """
    title = f"{clean_title(' '.join(title_parts))} "

    country = simple_info.get("country", "")
    year = simple_info.get("year", "")
    title = remove_country(title, country)
    title = remove_from_title(title, year)

    return release_title.startswith(title)


def check_episode_number_match(release_title):
    """
    Confirms that the release title contains an season and episode number
    :param release_title: Release title of source
    :return: True if present else False
    """
    return _EPISODE_NUMBERS.match(release_title) is not None


def check_episode_title_match(show_titles, release_title, simple_info):
    """
    Simplified loose title matching for episode items
    :param show_titles: tv show titles
    :param release_title: release title of source
    :param simple_info: simplified meta data
    :return: True if match found else False
    """
    release_title = clean_title(release_title)
    if simple_info.get("episode_title", None) is not None:
        episode_title = clean_title(simple_info["episode_title"])
        if len(episode_title.split(" ")) >= 3 and episode_title in release_title:
            for title in show_titles:
                if release_title.startswith(clean_title(title)):
                    return True
    return False


def filter_movie_title(org_release_title, release_title, movie_title, simple_info):
    """
    More complex matching of titles for movie items
    :param org_release_title: Original release title of source
    :param release_title: Sources release title
    :param movie_title: Title of Movie
    :param simple_info: Simplified meta data
    :return: True if match found, else False
    """
    year = simple_info.get("year")
    if not year:
        return False
    if org_release_title is not None and year not in org_release_title:
        return False

    title = clean_title(movie_title)
    release_title = clean_title(release_title)

    if "season" in release_title and "season" not in title:
        return False
    if check_episode_number_match(release_title):
        return False

    title_broken_1 = clean_title(movie_title, broken=1)
    title_broken_2 = clean_title(movie_title, broken=2)

    return (
        check_title_match([title], release_title, simple_info)
        or check_title_match([title_broken_1], release_title, simple_info)
        or check_title_match([title_broken_2], release_title, simple_info)
    )


def clean_title_with_simple_info(title, simple_info):
    """
    Cleaning of title and stripping of some known meta data
    :param title: identified title
    :param simple_info: simplified metadata
    :return: cleaned title
    """
    title = f"{clean_title(title)} "
    country = simple_info.get("country", "")
    title = remove_country(title, country)
    year = simple_info.get("year", "")
    title = remove_from_title(title, year)
    title = _WHITESPACE.sub(" ", title)
    return title.rstrip()


def get_filter_single_episode_fn(simple_info):
    """
    Constructs and returns a method to match episode titles
    :param simple_info: simplified metadata
    :return: method that can be used to match titles
    """
    try:
        show_title, season, episode, alias_list = (
            simple_info["show_title"],
            simple_info["season_number"],
            simple_info["episode_number"],
            simple_info["show_aliases"],
        )
    except KeyError:
        raise CannotGenerateRegexFilterException("simple_info must contain (show_title, season_number, episode_number)")

    titles = list(alias_list)
    titles.insert(0, show_title)

    clean_titles = []
    for title in titles:
        clean_titles.append(re.escape(clean_title_with_simple_info(title, simple_info)))

    pattern = r"^(?:{titles})+ ?(?:{year})? ?(?:s0?{ss}e0?{ep}(?: |e\d\d?)|season\ 0?{ss}\ episode\ 0?{ep})+".format(
        titles=" ?|".join(clean_titles),
        year=re.escape(simple_info["year"]),
        ss=re.escape(season),
        ep=re.escape(episode),
    )
    regex = re.compile(pattern)

    def filter_fn(release_title):
        """
        Method to match release titles with supplied metadata
        :param release_title: source release title
        :return: True if match found, else False
        """
        release_title = clean_title(release_title)
        if regex.match(release_title):
            return True

        return check_episode_title_match(clean_titles, release_title, simple_info)

    return filter_fn


def get_filter_season_pack_fn(simple_info):
    """
    Constructs and returns a method to match season pack titles
    :param simple_info: simplified metadata
    :return: method that can be used to match titles
    """
    show_title, season, alias_list = (
        simple_info["show_title"],
        simple_info["season_number"],
        simple_info["show_aliases"],
    )

    titles = list(alias_list)
    titles.insert(0, show_title)

    season_fill = season.zfill(2)
    season_check = f"s{season}"
    season_fill_check = f"s%{season_fill}"
    season_full_check = f"season {season}"
    season_full_fill_check = f"season {season_fill}"

    clean_titles = []
    for title in titles:
        clean_titles.append(clean_title_with_simple_info(title, simple_info))

    suffixes = [
        season_check,
        season_fill_check,
        season_full_check,
        season_full_fill_check,
    ]
    regex_pattern = _get_regex_pattern(clean_titles, suffixes)

    def filter_fn(release_title):
        """
        Method to match release titles with supplied metadata
        :param release_title: source release title
        :return: True if match found, else False
        """
        episode_number_match = check_episode_number_match(release_title)
        if episode_number_match:
            return False

        return bool(re.match(regex_pattern, release_title))

    return filter_fn


def get_filter_show_pack_fn(simple_info):
    """
    Constructs and returns a method to match show pack titles
    :param simple_info: simplified metadata
    :return: method that can be used to match titles
    """
    show_title, season, alias_list, no_seasons, country, year = (
        simple_info["show_title"],
        simple_info["season_number"],
        simple_info["show_aliases"],
        simple_info["no_seasons"],
        simple_info["country"],
        simple_info["year"],
    )

    titles = list(alias_list)
    titles.insert(0, show_title)
    for idx, title in enumerate(titles):
        titles[idx] = clean_title_with_simple_info(title, simple_info)

    all_season_ranges = []
    all_seasons = "1 "
    season_count = 2
    while season_count <= int(no_seasons):
        all_season_ranges.append(f"{all_seasons}and {season_count}")
        all_seasons += f"{season_count} "
        all_season_ranges.append(all_seasons)
        season_count += 1

    all_season_ranges = [x for x in all_season_ranges if season in x]

    def get_pack_names(release_title):
        """
        Method to match release titles with supplied metadata
        :param release_title: source release title
        :return: True if match found, else False
        """
        no_seasons_fill = no_seasons.zfill(2)
        no_seasons_minus_one = str(int(no_seasons) - 1)
        no_seasons_minus_one_fill = no_seasons_minus_one.zfill(2)

        results = [
            f'all {no_seasons} seasons',
            f'all {no_seasons_fill} seasons',
            f'all {no_seasons_minus_one} seasons',
            f'all {no_seasons_minus_one_fill} seasons',
            f"all of serie {no_seasons} seasons",
            f"all of serie {no_seasons_fill} seasons",
            f"all of serie {no_seasons_minus_one} seasons",
            f"all of serie {no_seasons_minus_one_fill} seasons",
            f"all torrent of serie {no_seasons} seasons",
            f"all torrent of serie {no_seasons_fill} seasons",
            f"all torrent of serie {no_seasons_minus_one} seasons",
            f"all torrent of serie {no_seasons_minus_one_fill} seasons",
        ]

        for season_range in all_season_ranges:
            results.append(f"{season_range}")
            results.append(f"season {season_range}")
            results.append(f"seasons {season_range}")

        if "series" not in release_title:
            results.append("series")

        if 'boxset' not in release_title:
            results.append('boxset')

        if 'collection' not in release_title:
            results.append('collection')

        return results

    def get_pack_names_range(last_season):
        """
        Constructs a list of season range strings for regex
        :param last_season: stringed season number
        :return: list of strings for regex comparison
        """
        last_season_fill = last_season.zfill(2)

        return [
            f"{last_season} seasons",
            f"{last_season_fill} seasons",
            f"season 1 {last_season}",
            f"season 01 {last_season_fill}",
            f"season1 {last_season}",
            f"season01 {last_season_fill}",
            f"season 1 to {last_season}",
            f"season 01 to {last_season_fill}",
            f"season 1 thru {last_season}",
            f"season 01 thru {last_season_fill}",
            f"seasons 1 {last_season}",
            f"seasons 01 {last_season_fill}",
            f"seasons1 {last_season}",
            f"seasons01 {last_season_fill}",
            f"seasons 1 to {last_season}",
            f"seasons 01 to {last_season_fill}",
            f"seasons 1 thru {last_season}",
            f"seasons 01 thru {last_season_fill}",
            f"full season 1 {last_season}",
            f"full season 01 {last_season_fill}",
            f"full season1 {last_season}",
            f"full season01 {last_season_fill}",
            f"full season 1 to {last_season}",
            f"full season 01 to {last_season_fill}",
            f"full season 1 thru {last_season}",
            f"full season 01 thru {last_season_fill}",
            f"full seasons 1 {last_season}",
            f"full seasons 01 {last_season_fill}",
            f"full seasons1 {last_season}",
            f"full seasons01 {last_season_fill}",
            f"full seasons 1 to {last_season}",
            f"full seasons 01 to {last_season_fill}",
            f"full seasons 1 thru {last_season}",
            f"full seasons 01 thru {last_season_fill}",
            f"s1 {last_season}",
            f"s1 s{last_season}",
            f"s01 {last_season_fill}",
            f"s01 s{last_season_fill}",
            f"s1 to {last_season}",
            f"s1 to s{last_season}",
            f"s01 to {last_season_fill}",
            f"s01 to s{last_season_fill}",
            f"s1 thru {last_season}",
            f"s1 thru s{last_season}",
            f"s01 thru {last_season_fill}",
            f"s01 thru s{last_season_fill}",
        ]

    suffixes = get_pack_names(show_title)
    seasons_count = int(season)
    while seasons_count <= int(no_seasons):
        suffixes += get_pack_names_range(str(seasons_count))
        seasons_count += 1

    non_escaped_suffixes = [
        "(?!season)(?<!season)complete",
    ]

    regex_pattern = _get_regex_pattern(titles, suffixes, non_escaped_suffixes=non_escaped_suffixes)

    def filter_fn(release_title):
        """
        Method to match release titles with supplied metadata
        :param release_title: source release title
        :return: True if match found, else False
        """
        episode_number_match = check_episode_number_match(release_title)
        if episode_number_match:
            return False

        return bool(re.match(regex_pattern, release_title))

    return filter_fn


def is_file_ext_valid(file_name):
    """
    Checks if the video file type is supported by Kodi
    :param file_name: name/path of file
    :return: True if video file is expected to be supported else False
    """
    return file_name.endswith(g.common_video_extensions)


def _full_meta_episode_regex(args):
    """
    Takes an episode items full meta and returns a regex object to use in title matching
    :param args: Full meta of episode item
    :return: compiled regex object
    """
    episode_info = args["info"]
    show_title = clean_title(episode_info["tvshowtitle"])
    country = episode_info.get("country", "")
    if isinstance(country, (list, set)):
        country = '|'.join(country)
    country = country.lower()
    year = episode_info.get("year", "")
    episode_title = clean_title(episode_info.get("title", ""))
    season = str(episode_info.get("season", ""))
    episode = str(episode_info.get("episode", ""))

    if episode_title == show_title or len(re.findall(r"^\d+$", episode_title)) > 0:
        episode_title = None

    reg_string = (
        r"(?#SHOW TITLE)(?:{show_title})"
        r"? ?"
        r"(?#COUNTRY)(?:{country})"
        r"? ?"
        r"(?#YEAR)(?:{year})"
        r"? ?"
        r"(?:(?:[s[]?)0?"
        r"(?#SEASON){season}"
        r"[x .e]|(?:season 0?"
        r"(?#SEASON){season} "
        r"(?:episode )|(?: ep ?)))(?:\d?\d?e)?0?"
        r"(?#EPISODE){episode}"
        r"(?:e\d\d)?\]? "
    )

    reg_string = reg_string.format(show_title=show_title, country=country, year=year, season=season, episode=episode)

    if episode_title:
        reg_string += f"|{episode_title}"

    reg_string = reg_string.replace("*", ".")

    return re.compile(reg_string)


def get_best_episode_match(dict_key, dictionary_list, item_information):
    """
    Attempts to identify the best matching file/s for a given item and list of source files
    :param dict_key: internal key of dictionary in dictionary list to run checks against
    :param dictionary_list: list of dictionaries containing source title
    :param item_information: full meta of episode object
    :return: dictionaries that best matched requested episode
    """
    regex = _full_meta_episode_regex(item_information)
    files = []

    for i in dictionary_list:
        i.update({"regex_matches": regex.findall(clean_title(i[dict_key].split("/")[-1].replace("&", " ").lower()))})
        files.append(i)
    files = [i for i in files if len(i["regex_matches"]) > 0]

    if not files:
        return None

    files = sorted(files, key=lambda x: len(" ".join(x["regex_matches"])), reverse=True)

    return files[0]


def clear_extras_by_string(args, extra_string, folder_details):
    """
    Strips source files that are identified to contain files related to show/movie extras
    :param args: full metadata of requested playback item
    :param extra_string: string used to identify bad source files
    :param folder_details: normalised list of source files
    :return: cleaned list of folder items
    """
    keys_to_confirm_against = ["title", "tvshowtitle"]
    if int(args["info"].get("season", 1)) == 0:
        return folder_details
    for key in keys_to_confirm_against:
        if extra_string in args["info"].get(key, ""):
            return []

    folder_details = [
        i for i in folder_details if extra_string not in clean_title(i["path"].split("/")[-1].replace("&", " ").lower())
    ]
    folder_details = [
        i
        for i in folder_details
        if not any(True for folder in i["path"].split("/") if extra_string.lower() == folder.lower())
    ]

    return [i for i in folder_details if extra_string not in i["path"]]


def filter_files_for_resolving(folder_details, args):
    """
    Ease of use method to filter common strings with clear_extras_by_string
    :param folder_details: normalised list of source files
    :param args: full meta of requested playback item
    :return: cleaned list of folder items
    """
    folder_details = clear_extras_by_string(args, "extras", folder_details)
    folder_details = clear_extras_by_string(args, "specials", folder_details)
    folder_details = clear_extras_by_string(args, "featurettes", folder_details)
    folder_details = clear_extras_by_string(args, "deleted scenes", folder_details)
    folder_details = clear_extras_by_string(args, "sample", folder_details)
    return folder_details


def de_string_size(size):
    """
    Attempts to take a stringed size eg(1GB) and return a integer size in MB
    :param size: identified size
    :type size: str
    :return: size in MB if string can be converted else None
    :rtype int|None:
    """
    if "GB" in size:
        size = float(size.replace("GB", ""))
        return int(size * 1024)
    if "MB" in size:
        size = int(size.replace("MB", "").replace(" ", "").split(".")[0])
        return size
    if "KB" in size:
        size = float(size.replace("KB", ""))
        return int(size * 0.001)
    if "MiB" in size:
        size = int(size.replace("MiB", "").replace(" ", "").split(".")[0])
        return size
    if "GiB" in size:
        size = float(size.replace("GiB", ""))
        return int(size * 1024)
    if "KiB" in size:
        size = float(size.replace("KiB", ""))
        return int(size * 0.001024)


def get_accepted_resolution_set():
    """
    Fetches set of accepted resolutions per settings
    :return: set of resolutions
    :rtype set
    """
    resolutions = ["4K", "1080p", "720p", "SD"]
    max_res = g.get_int_setting("general.maxResolution")
    min_res = g.get_int_setting("general.minResolution")

    return set(resolutions[max_res : min_res + 1])
