# -*- coding: utf-8 -*-

import random
import re

try:import xbmc
except: pass

from requests import Session
from resources.lib.common import tools

try:
    COMMON_VIDEO_EXTENSIONS = xbmc.getSupportedMedia('video').split('|')

    COMMON_VIDEO_EXTENSIONS = [i for i in COMMON_VIDEO_EXTENSIONS if i != '' and i != '.zip']
except:
    pass


BROWSER_AGENTS = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0']

exclusions = ['soundtrack', 'gesproken']


# LEGACY COMPATIBILITY

def getQuality(release_title):
    return get_quality(release_title)

def get_quality(release_title):
    release_title = release_title.lower()
    quality = 'SD'
    if '4k' in release_title:
        quality = '4K'
    if '2160' in release_title:
        quality = '4K'
    if '1080' in release_title:
        quality = '1080p'
    if '720' in release_title:
        quality = '720p'
    if any(i in release_title for i in [' cam ', 'camrip', 'hdcam', 'hd cam', ' ts ', 'hd ts', 'hdts', 'telesync', ' tc ', 'hd tc', 'hdtc', 'telecine', 'xbet']):
        quality = 'CAM'

    return quality

def info_list_to_sorted_dict(info_list):
    info = {}

    info_struct = {
        'videocodec': {
            'AVC': ['x264', 'x 264', 'h264', 'h 264', 'avc'],
            'HEVC': ['x265', 'x 265', 'h265', 'h 265', 'hevc'],
            'XviD': ['xvid'],
            'DivX': ['divx'],
            'WMV': ['wmv']
        },
        'audiocodec': {
            'AAC': ['aac'],
            'DTS': ['dts'],
            'HD-MA': ['hd ma', 'hdma'],
            'ATMOS': ['atmos'],
            'TRUEHD': ['truehd', 'true hd'],
            'DD+': ['ddp', 'dd+', 'eac3'],
            'DD': [' dd ', 'dd2', 'dd5', 'dd7', ' ac3'],
            'MP3': ['mp3'],
            'WMA': [' wma ']
        },

        'audiochannels': {
            '2.0': ['2 0 ', '2 0ch', '2ch'],
            '5.1': ['5 1 ', '5 1ch', '6ch'],
            '7.1': ['7 1 ', '7 1ch', '8ch']
        }

    }

    for property in info_struct.keys():
        for codec in info_struct[property].keys():
            if codec in info_list:
                info[property] = codec
                break
    return info

def getInfo(release_title):
    info = []
    release_title = cleanTitle(release_title)
    #info.video
    if any(i in release_title for i in ['x264', 'x 264', 'h264', 'h 264', 'avc']):
        info.append('AVC')
    if any(i in release_title for i in ['x265', 'x 265', 'h265', 'h 265', 'hevc']):
        info.append('HEVC')
    if any(i in release_title for i in ['xvid']):
        info.append('XVID')
    if any(i in release_title for i in ['divx']):
        info.append('DIVX')
    if any(i in release_title for i in ['mp4']):
        info.append('MP4')
    if any(i in release_title for i in ['wmv']):
        info.append('WMV')
    if any(i in release_title for i in ['mpeg']):
        info.append('MPEG')
    if any(i in release_title for i in ['remux', 'bdremux']):
        info.append('REMUX')
    if any(i in release_title for i in [' hdr ', 'hdr10', 'hdr 10']):
        info.append('HDR')
    if any(i in release_title for i in [' sdr ']):
        info.append('SDR')
    
    #info.audio
    if any(i in release_title for i in ['aac']):
        info.append('AAC')
    if any(i in release_title for i in ['dts']):
        info.append('DTS')
    if any(i in release_title for i in ['hd ma' , 'hdma']):
        info.append('HD-MA')
    if any(i in release_title for i in ['atmos']):
        info.append('ATMOS')
    if any(i in release_title for i in ['truehd', 'true hd']):
        info.append('TRUEHD')
    if any(i in release_title for i in ['ddp', 'dd+', 'eac3']):
        info.append('DD+')
    if any(i in release_title for i in [' dd ', 'dd2', 'dd5', 'dd7', ' ac3']):
        info.append('DD')
    if any(i in release_title for i in ['mp3']):
        info.append('MP3')
    if any(i in release_title for i in [' wma']):
        info.append('WMA')
    
    #info.channels
    if any(i in release_title for i in ['2 0 ', '2 0ch', '2ch']):
        info.append('2.0')
    if any(i in release_title for i in ['5 1 ', '5 1ch', '6ch']):
        info.append('5.1')
    if any(i in release_title for i in ['7 1 ', '7 1ch', '8ch']):
        info.append('7.1')
    
    #info.source 
    # no point at all with WEBRip vs WEB-DL cuz it's always labeled wrong with TV Shows 
    # WEB = WEB-DL in terms of size and quality
    if any(i in release_title for i in ['bluray' , 'blu ray' , 'bdrip', 'bd rip', 'brrip', 'br rip']):
        info.append('BLURAY')
    if any(i in release_title for i in [' web ' , 'webrip' , 'webdl', 'web rip', 'web dl']):
        info.append('WEB')
    if any(i in release_title for i in ['hdrip', 'hd rip']):
        info.append('HDRIP')
    if any(i in release_title for i in ['dvdrip', 'dvd rip']):
        info.append('DVDRIP')
    if any(i in release_title for i in ['hdtv']):
        info.append('HDTV')
    if any(i in release_title for i in ['pdtv']):
        info.append('PDTV')
    if any(i in release_title for i in [' cam ', 'camrip', 'hdcam', 'hd cam', ' ts ', 'hd ts', 'hdts', 'telesync', ' tc ', 'hd tc', 'hdtc', 'telecine', 'xbet']):
        info.append('CAM')
    if any(i in release_title for i in ['dvdscr', ' scr ', 'screener']):
        info.append('SCR')
    if any(i in release_title for i in ['korsub', ' kor ', ' hc']):
        info.append('HC')
    if any(i in release_title for i in ['blurred']):
        info.append('BLUR')
    if any(i in release_title for i in [' 3d']):
        info.append('3D')
        
    return info


def cleanTitle(title):
    title = clean_title(title)
    return title

def clean_title(title, broken=None):
    title = title.lower()
    # title = tools.deaccentString(title)
    title = tools.strip_non_ascii_and_unprintable(title)

    if broken == 1:
        apostrophe_replacement = ''
    elif broken == 2:
        apostrophe_replacement = ' s'
    else:
        apostrophe_replacement = 's'
    title = title.replace("\\'s", apostrophe_replacement)
    title = title.replace("'s", apostrophe_replacement)
    title = title.replace("&#039;s", apostrophe_replacement)
    title = title.replace(" 039 s", apostrophe_replacement)

    title = re.sub(r'\:|\\|\/|\,|\!|\?|\(|\)|\'|\"|\\|\[|\]|\-|\_|\.', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'\&', 'and', title)

    return title.strip()

def searchTitleClean(title):
    title = title.lower()
    title = title.replace('-', ' ')
    title = re.sub(r'\:|\\|\/|\,|\!|\(|\)|\'', '', title)
    title = title.replace('.', '')
    title = title.replace('  ', ' ')
    return title


def clean_tags(title):
    title = title.lower()

    if title[0] == '[':
        title = title[title.find(']')+1:].strip()
        return clean_tags(title)
    if title[0] == '(':
        title = title[title.find(')')+1:].strip()
        return clean_tags(title)
    if title[0] == '{':
        title = title[title.find('}')+1:].strip()
        return clean_tags(title)

    title = re.sub(r'\(|\)|\[|\]|\{|\}', ' ', title)
    title = re.sub(r'\s+', ' ', title)

    return title

def remove_sep(release_title, title):
    def check_for_sep(t, sep):
        if sep in t and t[t.find(sep)+1:].strip().lower().startswith(title):
            return t[t.find(sep)+1:].strip()
        return t

    release_title = check_for_sep(release_title, '/')
    release_title = check_for_sep(release_title, '-')

    return release_title

def remove_from_title(title, target, clean = True):
    if target == '':
        return title

    title = title.replace(' %s ' % target.lower(), ' ')
    title = title.replace('.%s.' % target.lower(), ' ')
    title = title.replace('+%s+' % target.lower(), ' ')
    title = title.replace('-%s-' % target.lower(), ' ')
    if clean:
        title = clean_title(title) + ' '
    else:
        title = title + ' '

    return re.sub(r'\s+', ' ', title)

def remove_country(title, country, clean = True):
    title = title.lower()
    country = country.lower()

    if country in ['gb', 'uk']:
        title = remove_from_title(title, 'gb', clean)
        title = remove_from_title(title, 'uk', clean)
    else:
        title = remove_from_title(title, country, clean)

    return title

def check_title_match(title_parts, release_title, simple_info, is_special=False):
    title = clean_title(' '.join(title_parts)) + ' '
    release_title = clean_tags(release_title)

    country = simple_info.get('country', '')
    title = remove_country(title, country)

    release_title = remove_country(release_title, country, False)
    release_title = remove_from_title(release_title, get_quality(release_title), False)
    release_title = remove_sep(release_title, title)
    release_title = clean_title(release_title) + ' '

    if release_title.startswith(title):
        return True

    year = simple_info.get('year', '')
    release_title = remove_from_title(release_title, year)
    title = remove_from_title(title, year)
    if release_title.startswith(title):
        return True

    if simple_info.get('episode_title', None) is not None:
        show_title = clean_title(title_parts[0]) + ' '
        show_title = remove_from_title(show_title, year)
        episode_title = clean_title(simple_info['episode_title'])
        should_filter_by_title_only = len(episode_title.split(' ')) >= 3 or is_special
        if should_filter_by_title_only and release_title.startswith(show_title) and episode_title in release_title:
            return True

    return False

def filter_movie_title(release_title, movie_title, year):
    release_title = release_title.lower()

    title = clean_title(movie_title)

    title_broken_1 = clean_title(movie_title, broken=1)
    title_broken_2 = clean_title(movie_title, broken=2)
    simple_info =  { 'year': year }

    if not check_title_match([title], release_title, simple_info) and not check_title_match([title_broken_1], release_title, simple_info) and not check_title_match([title_broken_2], release_title, simple_info):
        #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
        return False

    if any(i in release_title for i in exclusions):
        #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
        return False

    if year not in release_title:
        #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
        return False

    if 'xxx' in release_title and 'xxx' not in title:
        #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
        return False

    return True

def filter_season_pack(simple_info, release_title):
    show_title, season, alias_list = \
        simple_info['show_title'], \
        simple_info['season_number'], \
        simple_info['show_aliases']

    titles = list(alias_list)
    titles.insert(0, show_title)

    season_fill = season.zfill(2)
    season_check = 's%s' % season
    season_fill_check = 's%s' % season_fill
    season_full_check = 'season %s' % season
    season_full_fill_check = 'season %s' % season_fill

    string_list = []
    for title in titles:
        string_list.append([title, season_check])
        string_list.append([title, season_fill_check])
        string_list.append([title, season_full_check])
        string_list.append([title, season_full_fill_check])

    episode_number_match = len(re.findall(r'(s\d+ *e\d+ )', release_title.lower())) > 0
    if episode_number_match:
        #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
        return False

    episode_number_match = len(re.findall(r'(season \d+ episode \d+)', release_title.lower())) > 0
    if episode_number_match:
        #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
        return False

    for title_parts in string_list:
        if check_title_match(title_parts, release_title, simple_info):
            return True

    #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
    return False

def filter_single_special_episode(simple_info, release_title):
    if check_title_match([simple_info['episode_title']], release_title, simple_info, is_special=True):
        return True
    #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
    return False

def filter_single_episode(simple_info, release_title):
    show_title, season, episode, alias_list = \
        simple_info['show_title'], \
        simple_info['season_number'], \
        simple_info['episode_number'], \
        simple_info['show_aliases']

    titles = list(alias_list)
    titles.insert(0, show_title)

    season_episode_check = 's%se%s' % (season, episode)
    season_episode_fill_check = 's%se%s' % (season, episode.zfill(2))
    season_fill_episode_fill_check = 's%se%s' % (season.zfill(2), episode.zfill(2))
    season_episode_full_check = 'season %s episode %s' % (season, episode)
    season_episode_fill_full_check = 'season %s episode %s' % (season, episode.zfill(2))
    season_fill_episode_fill_full_check = 'season %s episode %s' % (season.zfill(2), episode.zfill(2))

    string_list = []
    for title in titles:
        string_list.append([title, season_episode_check])
        string_list.append([title, season_episode_fill_check])
        string_list.append([title, season_fill_episode_fill_check])
        string_list.append([title, season_episode_full_check])
        string_list.append([title, season_episode_fill_full_check])
        string_list.append([title, season_fill_episode_fill_full_check])

    for title_parts in string_list:
        if check_title_match(title_parts, release_title, simple_info):
            return True

    #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
    return False


def filter_show_pack(simple_info, release_title):
    release_title = clean_title(release_title.lower().replace('the complete', '').replace('complete', ''))
    season = simple_info['season_number']
    alias_list = [clean_title(x) for x in simple_info['show_aliases']]
    alias_list = list(alias_list)
    if '.' in simple_info['show_title']:
        alias_list.append(clean_title(simple_info['show_title'].replace('.', '')))
    show_title = clean_title(simple_info['show_title'])

    no_seasons = simple_info['no_seasons']
    all_seasons = '1'
    country = simple_info['country']
    year = simple_info['year']
    season_count = 1
    append_list = []

    while season_count <= int(season):
        season_count += 1
        all_seasons += ' %s' % str(season_count)

    string_list = ['%s season %s' % (show_title, all_seasons),
                  '%s %s' % (show_title, all_seasons),
                  '%s season 1 %s ' % (show_title, no_seasons),
                  '%s seasons 1 %s ' % (show_title, no_seasons),
                  '%s seasons 1 to %s' % (show_title, no_seasons),
                  '%s season s01 s%s' % (show_title, no_seasons.zfill(2)),
                  '%s seasons s01 s%s' % (show_title, no_seasons.zfill(2)),
                  '%s seasons s01 to s%s' % (show_title, no_seasons.zfill(2)),
                  '%s series' % show_title,
                  '%s season s%s complete' % (show_title, season.zfill(2)),
                  '%s seasons 1 thru %s' % (show_title, no_seasons),
                  '%s seasons 1 thru %s' % (show_title, no_seasons.zfill(2)),
                  '%s season %s' % (show_title, all_seasons)
                  ]

    season_count = int(season)

    while int(season_count) <= int(no_seasons):
        s00 = '%s s01 s%s' % (show_title, str(season_count).zfill(2))
        season = '%s seasons 1 %s' % (show_title, str(season_count))
        seasons = '%s season 1 %s' % (show_title, str(season_count))
        if release_title == s00:
            return True
        if release_title == season:
            return True
        if release_title == seasons:
            return True
        season_count = season_count + 1

    while int(season_count) <= int(no_seasons):
        string_list.append('%s s01 s%s' % (show_title, str(season_count).zfill(2)))
        string_list.append('%s seasons 1 %s ' % (show_title, str(season_count)))
        string_list.append('%s season 1 %s ' % (show_title, str(season_count)))
        season_count = season_count + 1

    for i in string_list:
        append_list.append(i.replace(show_title, '%s %s' % (show_title, country)))

    string_list += append_list
    append_list = []

    for i in string_list:
        append_list.append(i.replace(show_title, '%s %s' % (show_title, year)))

    string_list += append_list
    append_list = []

    for i in string_list:
        for alias in alias_list:
            append_list.append(i.replace(show_title, alias))

    string_list += append_list

    for x in string_list:
        if '&' in x:
            string_list.append(x.replace('&', 'and'))

    for i in string_list:
        if release_title.startswith(i):
            return True

    #tools.log('%s - %s' % (inspect.stack()[0][3], release_title), 'notice')
    return False


class serenRequests(Session):
    def __init__(self, *args, **kwargs):
        super(serenRequests, self).__init__(*args, **kwargs)
        if "requests" in self.headers["User-Agent"]:
            # Spoof common and random user agent
            self.headers["User-Agent"] = random.choice(BROWSER_AGENTS)

def is_file_ext_valid(file_name):
    if '.' + file_name.split('.')[-1] not in COMMON_VIDEO_EXTENSIONS:
        return False

    return True

def get_best_match(dict_key, dictionary_list, item_information):
    regex = get_cache_check_reg(item_information)

    files = []

    for i in dictionary_list:
        path = cleanTitle(i[dict_key].split('/')[-1].replace('&', ' ').lower())
        i['regex_matches'] = regex.findall(path)
        files.append(i)

    files = [i for i in files if len(i['regex_matches']) > 0]

    if len(files) == 0:
        return None

    files = sorted(files, key=lambda x: len(' '.join(x['regex_matches'])), reverse=True)

    return files[0]

def clear_extras_by_string(args, string, folder_details):

    if string not in clean_title(args['info']['title']) \
            and string not in clean_title(args['showInfo']['info']['tvshowtitle']) \
            and int(args['info']['season']) != 0:
        folder_details = [i for i in folder_details if
                          string not in
                          cleanTitle(i['path'].replace('/', ' ')[-1].replace('&', ' ').lower())]
        folder_details = [i for i in folder_details if not any(True for folder in i['path'].split('/')
                                                               if string.lower() == folder.lower())]
        return [i for i in folder_details if string not in i['path']]


def get_cache_check_reg(args):

    episodeInfo = args['info']
    show_title = clean_title(args['showInfo']['info']['tvshowtitle'])
    country = args['showInfo']['info'].get('country', ' ').lower()
    year = args['showInfo']['info'].get('year', ' ')
    episode_title = cleanTitle(episodeInfo['title'])
    season = str(episodeInfo['season'])
    episode = str(episodeInfo['episode'])

    if episode_title == show_title\
            or len(re.findall(r'^\d+$', episode_title)) > 0:
        episode_title = None

    reg_string = '(?#SHOW TITLE)(?:%s)' \
                 '? ?' \
                 '(?#COUNTRY)(?:%s)' \
                 '? ?' \
                 '(?#YEAR)(?:%s)' \
                 '? ?(?:(?:s?|\[?)0?' \
                 '(?#SEASON)%s' \
                 '[x .e]|(?:season 0?' \
                 '(?#SEASON)%s ' \
                 '(?:episode )|(?: ep)))(?:\d\de)?0?' \
                 '(?#EPSIDOE)%s' \
                 '(?:e\d\d)?\]? '

    reg_string = reg_string % (show_title, country, year, season, season, episode)

    if episode_title:
        reg_string += '|{eptitle}'.format(eptitle=episode_title)

    return re.compile(reg_string)

def torrentCacheStrings(args, strict=False):

    episodeInfo = args['info']
    show_title = args['showInfo']['info']['tvshowtitle']
    episode_title = cleanTitle(episodeInfo['title'])
    season_number = str(episodeInfo['season'])
    episode_number = str(episodeInfo['episode'])
    episodeStrings = ['s%se%s ' % (season_number.zfill(2), episode_number.zfill(2)),
                      's%se%se%s ' % (season_number.zfill(2), episode_number.zfill(2),
                                     str(int(episode_number) + 1).zfill(2)),
                      's%se%se%s ' % (season_number.zfill(2), str(int(episode_number) - 1).zfill(2),
                                     episode_number.zfill(2)),
                      's%se%s ' % (season_number, episode_number.zfill(2)),
                      's%se%s ' % (season_number.zfill(2), episode_number),
                      's%se%s ' % (season_number, episode_number),
                      '%sx%s ' % (season_number, episode_number),
                      '%sx%s ' % (season_number.zfill(2), episode_number.zfill(2)),
                      '%sx%s ' % (season_number, episode_number.zfill(2)),
                      '[%s %s] ' % (season_number.zfill(2), episode_number),
                      '[%s %s] ' % (season_number, episode_number.zfill(2)),
                      '[%s %s] ' % (season_number, episode_number),
                      '[%sx%s] ' % (season_number.zfill(2), episode_number),
                      '[%sx%s] ' % (season_number, episode_number.zfill(2)),
                      '[%sx%s] ' % (season_number, episode_number),
                      '%s%s ' % (season_number, episode_number.zfill(2)),
                      '%s%s ' % (season_number.zfill(2), episode_number.zfill(2)),
                      '%s.%s ' % (season_number, episode_number.zfill(2)),
                      '%s.%s ' % (season_number.zfill(2), episode_number),
                      '%s.%s ' % (season_number.zfill(2), episode_number.zfill(2)),
                      ]
    if not clean_title(episode_title) == clean_title(show_title):
        if not len(re.findall(r'^[0-9]+$', clean_title(episode_title))) > 0:
            episodeStrings.append('%s ' % clean_title(episode_title))

    if strict == False:
        relaxed_strings = [
            'episode %s ' % episode_number.zfill(2),
            'episode %s ' % episode_number,
            ' ep%s ' % episode_number,
            ' ep%s ' % episode_number.zfill(2),
            ]
        episodeStrings += relaxed_strings

    if any(x in i for i in args['showInfo']['info'].get('genre', []) for x in ['anime', 'animation']):
        episodeStrings.append(' %s ' % args['info']['absoluteNumber'])

    if episode_number == '1' and season_number == '1':
        episodeStrings.append('pilot')

    seasonStrings = ['season %s' % season_number,
                     'season %s' % season_number.zfill(2),
                     's%s' % season_number,
                     's%s' % season_number.zfill(2),
                     'series %s' % season_number.zfill(2),
                     'series %s' % season_number
                     ]

    return episodeStrings, seasonStrings


def de_string_size(size):
    try:
        if 'Mib' in size:
            size = int(size.replace('MB', '').replace(' ', '').split('.')[0])
            return size
        if 'GiB' in size:
            size = float(size.replace('GiB', ''))
            size = int(size * 1024)
            return size
        if 'GB' in size:
            size = float(size.replace('GB', ''))
            size = int(size * 1024)
            return size
        if 'MB' in size:
            size = int(size.replace('MB', '').replace(' ', '').split('.')[0])
            return size
    except:
        return 0
