# -*- coding: utf-8 -*-

import random
import re

from requests import Session

COMMON_VIDEO_EXTENSIONS = ['.m4v', '.mkv', '.mka', '.mp4', '.avi', '.mpeg', '.asf', '.flv', '.m4a', '.aac', '.nut',
                           '.ogg']

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


def getQuality(release_title):
    quality = 'SD'
    if '4K' in release_title:
        quality = '4K'
    if '2160p' in release_title:
        quality = '4K'
    if '1080p' in release_title:
        quality = '1080p'
    if ' 1080 ' in release_title:
        quality = '1080p'
    if ' 720 ' in release_title:
        quality = '720p'
    if ' HD ' in release_title:
        quality = '720p'
    if '720p' in release_title:
        quality = '720p'

    return quality


def getInfo(release_title):
    info = []
    release_title = cleanTitle(release_title)
    if any(i in release_title for i in [' x264', '.x264', ' h264', 'h 264']):
        info.append('x264')
    if any(i in release_title for i in [' 3d']):
        info.append('3D')
    if any(i in release_title for i in [' aac']):
        info.append('AAC')
    if any(i in release_title for i in [' dts']):
        info.append('DTS')
    if any(i in release_title for i in [' 5 1', ' 5 1ch', ' 6ch', ' ddp5 1']):
        info.append('DDP5.1')
    if any(i in release_title for i in [' 7 1']):
        info.append('7.1')
    if any(i in release_title for i in ['x265', '.x265', 'hevc', ' h265', '.h265', 'x265', ' h 265']):
        info.append('x265')
    if any(i in release_title for i in [' cam', ' camrip', ' hdcam', ' hd cam']):
        info.append('CAM')
    return info


def cleanTitle(title):
    title = title.lower()
    title = title.replace('-', ' ')
    title = re.sub(r'\:|\\|\/|\,|\!|\(|\)|\'', '', title)
    title = title.replace('_', ' ')
    title = title.replace('?', '')
    title = title.replace('!', '')
    title = title.replace('.', ' ')
    title = title.replace(',', ' ')
    title = title.replace('  ', ' ')
    title = title.replace('  ', ' ')
    title = title.replace('  ', ' ')
    return title


def searchTitleClean(title):
    title = title.lower()
    title = title.replace('-', ' ')
    title = re.sub(r'\:|\\|\/|\,|\!|\(|\)|\'', '', title)
    title = title.replace('.', '')
    title = title.replace('  ', ' ')
    return title


def filterMovieTitle(release_title, movieTitle, year):
    movieTitle = cleanTitle(movieTitle.lower())
    release_title = cleanTitle(release_title.lower())
    string_list = []
    string_list.append('%s (%s)' % (movieTitle, year))
    string_list.append('%s %s' % (movieTitle, year))
    string_list.append('%s.%s' % (movieTitle.replace(' ', '.'), year))

    if any(i in release_title for i in string_list):
        if any(i in release_title for i in exclusions):
            return False
        else:
            if release_title.startswith(movieTitle.split(' ')[0]):
                return True
            else:
                return False
    return False


def filterSeasonPack(simpleInfo, release_title):
    show_title, season, aliasList, year, country = \
        simpleInfo['show_title'], \
        simpleInfo['season_number'], \
        simpleInfo['show_aliases'], \
        simpleInfo['year'], \
        simpleInfo['country']

    stringList = []
    release_title = cleanTitle(release_title)
    if '.' in show_title:
        aliasList.append(cleanTitle(show_title.replace('.', '')))
    show_title = cleanTitle(show_title)
    seasonFill = season.zfill(2)
    aliasList = [searchTitleClean(x) for x in aliasList]

    if '&' in release_title: release_title = release_title.replace('&', 'and')

    stringList.append('%s s%s ' % (show_title, seasonFill))
    stringList.append('%s s%s ' % (show_title, season))
    stringList.append('%s season %s ' % (show_title, seasonFill))
    stringList.append('%s season %s ' % (show_title, season))
    stringList.append('%s %s s%s' % (show_title, year, seasonFill))
    stringList.append('%s %s s%s' % (show_title, year, season))
    stringList.append('%s %s season %s ' % (show_title, year, seasonFill))
    stringList.append('%s %s season %s ' % (show_title, year, season))
    stringList.append('%s %s s%s' % (show_title, country, seasonFill))
    stringList.append('%s %s s%s' % (show_title, country, season))
    stringList.append('%s %s season %s ' % (show_title, country, seasonFill))
    stringList.append('%s %s season %s ' % (show_title, country, season))

    for i in aliasList:
        stringList.append('%s s%s' % (i, seasonFill))
        stringList.append('%s s%s' % (i, season))
        stringList.append('%s season %s ' % (i, seasonFill))
        stringList.append('%s season %s ' % (i, season))

    for x in stringList:
        if '&' in x:
            stringList.append(x.replace('&', 'and'))

    for i in stringList:
        if release_title.startswith(i):
            try:
                temp = re.findall(r'(s\d+e\d+ )', release_title)[0]
            except:
                return True

    return False


def filterSingleEpisode(simpleInfo, release_title):
    show_title, season, episode, aliasList, year, country = \
        simpleInfo['show_title'], \
        simpleInfo['season_number'], \
        simpleInfo['episode_number'], \
        simpleInfo['show_aliases'], \
        simpleInfo['year'], \
        simpleInfo['country']
    stringList = []
    if '.' in show_title:
        aliasList.append(cleanTitle(show_title.replace('.', '')))
    release_title = cleanTitle(release_title)
    show_title = cleanTitle(show_title)
    seasonFill = season.zfill(2)
    episodeFill = episode.zfill(2)
    aliasList = [searchTitleClean(x) for x in aliasList]
    for x in aliasList:
        if '&' in x:
            aliasList.append(x.replace('&', 'and'))

    stringList.append('%s s%se%s' % (show_title, seasonFill, episodeFill))
    stringList.append('%s %s s%se%s' % (show_title, year, seasonFill, episodeFill))
    stringList.append('%s %s s%se%s' % (show_title, country, seasonFill, episodeFill))

    for i in aliasList:
        stringList.append('%s s%se%s' % (cleanTitle(i), seasonFill, episodeFill))
        stringList.append('%s %s s%se%s' % (cleanTitle(i), year, seasonFill, episodeFill))
        stringList.append('%s %s s%se%s' % (cleanTitle(i), country, seasonFill, episodeFill))

    for x in stringList:
        if '&' in x:
            stringList.append(x.replace('&', 'and'))

    for i in stringList:
        if release_title.startswith(cleanTitle(i)):
            return True

    return False


def filterShowPack(simpleInfo, release_title):
    release_title = cleanTitle(release_title.lower().replace('the complete', '').replace('complete', ''))
    season = simpleInfo['season_number']
    aliasList = [searchTitleClean(x) for x in simpleInfo['show_aliases']]
    if '.' in simpleInfo['show_title']:
        aliasList.append(cleanTitle(simpleInfo['show_title'].replace('.', '')))
    showTitle = cleanTitle(simpleInfo['show_title'])

    no_seasons = simpleInfo['no_seasons']
    all_seasons = '1'
    country = simpleInfo['country']
    year = simpleInfo['year']
    season_count = 1
    append_list = []

    while season_count <= int(season):
        season_count += 1
        all_seasons += ' %s' % str(season_count)

    stringList = ['%s season %s' % (showTitle, all_seasons),
                  '%s %s' % (showTitle, all_seasons),
                  '%s season 1 %s ' % (showTitle, no_seasons),
                  '%s seasons 1 %s ' % (showTitle, no_seasons),
                  '%s seasons 1 to %s' % (showTitle, no_seasons),
                  '%s season s01 s%s' % (showTitle, no_seasons.zfill(2)),
                  '%s seasons s01 s%s' % (showTitle, no_seasons.zfill(2)),
                  '%s seasons s01 to s%s' % (showTitle, no_seasons.zfill(2)),
                  '%s series' % showTitle,
                  '%s season s%s complete' % (showTitle, season.zfill(2)),
                  '%s seasons 1 thru %s' % (showTitle, no_seasons),
                  '%s seasons 1 thru %s' % (showTitle, no_seasons.zfill(2)),
                  '%s season %s' % (showTitle, all_seasons)
                  ]

    season_count = int(season)

    while int(season_count) <= int(no_seasons):
        stringList.append('%s seasons 1 %s' % (showTitle, str(season_count)))
        stringList.append('%s season 1 %s' % (showTitle, str(season_count)))
        season_count = season_count + 1

    for i in stringList:
        append_list.append(i.replace(showTitle, '%s %s' % (showTitle, country)))

    stringList += append_list
    append_list = []

    for i in stringList:
        append_list.append(i.replace(showTitle, '%s %s' % (showTitle, year)))

    stringList += append_list
    append_list = []

    for i in stringList:
        for alias in aliasList:
            append_list.append(i.replace(showTitle, alias))

    stringList += append_list

    for x in stringList:
        if '&' in x:
            stringList.append(x.replace('&', 'and'))

    for i in stringList:
        if release_title.startswith(i):
            return True


class serenRequests(Session):
    def __init__(self, *args, **kwargs):
        super(serenRequests, self).__init__(*args, **kwargs)
        if "requests" in self.headers["User-Agent"]:
            # Spoof common and random user agent
            self.headers["User-Agent"] = random.choice(BROWSER_AGENTS)


def torrentCacheStrings(args):
    episodeInfo = args['episodeInfo']['info']
    episode_title = cleanTitle(episodeInfo['title'])
    season_number = str(episodeInfo['season'])
    episode_number = str(episodeInfo['episode'])
    episodeStrings = ['s%se%s ' % (season_number.zfill(2), episode_number.zfill(2)),
                      's%se%s ' % (season_number, episode_number.zfill(2)),
                      's%se%s ' % (season_number.zfill(2), episode_number),
                      's%se%s ' % (season_number, episode_number),
                      'episode %s ' % episode_number.zfill(2),
                      'episode %s ' % episode_number,
                      '%sx%s ' % (season_number, episode_number),
                      '%sx%s ' % (season_number.zfill(2), episode_number.zfill(2)),
                      '%sx%s ' % (season_number, episode_number.zfill(2)),
                      '[%s %s]' % (season_number.zfill(2), episode_number),
                      '[%s %s]' % (season_number, episode_number.zfill(2)),
                      '[%s %s]' % (season_number, episode_number),
                      '[%sx%s]' % (season_number.zfill(2), episode_number),
                      '[%sx%s]' % (season_number, episode_number.zfill(2)),
                      '[%sx%s]' % (season_number, episode_number),
                      ' %s' % cleanTitle(episode_title),
                      ' ep%s' % episode_number,
                      ' ep%s' % episode_number.zfill(2),
                      '%s%s ' % (season_number, episode_number.zfill(2)),
                      '%s%s ' % (season_number.zfill(2), episode_number.zfill(2)),
                      '%s.%s ' % (season_number, episode_number.zfill(2)),
                      '%s.%s ' % (season_number.zfill(2), episode_number),
                      '%s.%s ' % (season_number.zfill(2), episode_number.zfill(2)),
                      ]

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
        if 'GB' in size:
            size = float(size.replace('GB', ''))
            size = int(size * 1024)
            return size
        if 'MB' in size:
            size = int(size.replace('MB', '').replace(' ', '').split('.')[0])
            return size
    except:
        return 0
