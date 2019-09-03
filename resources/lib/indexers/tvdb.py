# -*- coding: utf-8 -*-
import copy
import json
import threading
import time
import traceback

import requests
from math import pi, sin

from resources.lib.common import tools
from resources.lib.indexers import fanarttv, tmdb
from resources.lib.modules import database


class TVDBAPI:
    def __init__(self):
        self.apiKey = tools.getSetting('tvdb.apikey')
        if self.apiKey == '':
            self.apiKey = "43VPI0R8323FB7TI"

        self.baseUrl = 'https://api.thetvdb.com/'
        self.jwToken = tools.getSetting('tvdb.jw')
        self.headers = {'Content-Type': 'application/json'}
        self.art = {}
        self.info = {}
        self.episode_summary = {}
        self.cast = []
        self.baseImageUrl = 'https://www.thetvdb.com/banners/'
        self.threads = []
        self.fanartart = {}

        self.tvshows_poster_limit = int(tools.getSetting('tvshows.poster_limit'))
        self.tvshows_fanart_limit = int(tools.getSetting('tvshows.fanart_limit'))
        self.tvshows_keyart_limit = int(tools.getSetting('tvshows.keyart_limit'))
        self.tvshows_characterart_limit = int(tools.getSetting('tvshows.characterart_limit'))
        self.tvshows_banner = tools.getSetting('tvshows.banner')
        self.season_poster = tools.getSetting('season.poster')
        self.season_banner = tools.getSetting('season.banner')
        self.season_landscape = tools.getSetting('season.landscape')
        self.season_fanart = tools.getSetting('season.fanart')
        self.episode_fanart = tools.getSetting('episode.fanart')

        self.tvshows_prefer_fanart = tools.getSetting('tvshows.preferedsource') == '0'

        if tools.fanart_api_key == '':
            self.fanart_support = False
        else:
            self.fanart_support = True

        if self.jwToken is not '':
            self.headers['Authorization'] = 'Bearer %s' % self.jwToken
        else:
            self.newToken()
            self.headers['Authorization'] = 'Bearer %s' % self.jwToken

    # I know this looks ridiculous. But this will limit TVDBAPI class instances from spawning massive amounts of
    # Token refreshes and will also reduce the chance greatly that Kodi will drop the addon settings due to threading
    def refresh_lock(self):
        if not tools.tvdb_refreshing:
            return False
        for i in range(0, 5):
            if tools.tvdb_refresh == '':
                time.sleep(1)
            else:
                self.jwToken = tools.tvdb_refresh
                return True

    def post_request(self, url, postData):
        return database.get(self._post_request, 12, url, postData)

    def _post_request(self, url, postData):
        postData = json.dumps(postData)
        url = self.baseUrl + url
        response = requests.post(url, data=postData, headers=self.headers).text
        if 'Not Authorized' in response:
            self.renewToken()
            self.headers['Authorization'] = 'Bearer %s' % self.jwToken
            response = requests.post(url, data=postData, headers=self.headers).text
        response = json.loads(response)

        return response

    def get_request(self, url):
        url = self.baseUrl + url
        response = requests.get(url, headers=self.headers).text
        if 'not authorized' in response.lower():
            self.renewToken()
            self.headers['Authorization'] = 'Bearer %s' % self.jwToken
            response = requests.get(url, headers=self.headers).text
        response = json.loads(response)

        return response

    def renewToken(self):

        refresh_lock = self.refresh_lock()
        if not refresh_lock:
            tools.tvdb_refreshing = True
        else:
            return
        url = self.baseUrl + 'refresh_token'
        response = requests.post(url, headers=self.headers)
        response = json.loads(response.text)

        if 'Error' in response:
            self.newToken(True)
        else:
            self.jwToken = response['token']
            tools.tvdb_refresh = self.jwToken
            tools.setSetting('tvdb.jw', self.jwToken)
            tools.setSetting('tvdb.expiry', str(time.time() + (24 * (60 * 60))))
        return

    def newToken(self, ignore_lock=False):

        refresh_lock = self.refresh_lock()
        if not refresh_lock:
            tools.tvdb_refreshing = True
        else:
            return
        url = self.baseUrl + "login"
        postdata = {"apikey": self.apiKey}
        postdata = json.dumps(postdata)
        headers = self.headers
        if 'Authorization' in headers:
            headers.pop('Authorization')
        response = json.loads(requests.post(url, data=postdata, headers=self.headers).text)
        self.jwToken = response['token']
        tools.tvdb_refresh = self.jwToken
        tools.setSetting('tvdb.jw', self.jwToken)
        self.headers['Authorization'] = self.jwToken
        tools.log('Refreshed TVDB Token')
        tools.setSetting('tvdb.expiry', str(time.time() + (24 * (60 * 60))))
        return response

    def seriesIDToListItem(self, trakt_object):
        try:
            tvdbID = trakt_object['ids']['tvdb']
            if self.fanart_support:
                self.threads.append(threading.Thread(target=self.getFanartTV, args=(tvdbID,)))

            self.threads.append(
                threading.Thread(target=self.getShowArt, args=(tvdbID, 'fanart', self.tvshows_fanart_limit)))
            self.threads.append(
                threading.Thread(target=self.getShowArt, args=(tvdbID, 'poster', self.tvshows_poster_limit)))

            self.threads.append(threading.Thread(target=self.getShowInfo, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getEpisodeSummary, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getSeriesCast, args=(tvdbID,)))

            [i.start() for i in self.threads]
            [i.join() for i in self.threads]

            item = {'info': None, 'art': None}
            if self.info == {}:
                return None

            # Set Art
            art = {}
            art.update(self.fanartart)
            art.update(self.art)
            if self.tvshows_prefer_fanart:
                try:
                    for i in range(0, self.tvshows_poster_limit):
                        name = 'poster' if i == 0 else 'poster{}'.format(i)
                        art[name] = self.fanartart.get(name, self.art.get(name, ''))
                    art['thumb'] = art['poster']
                except:
                    pass
                try:
                    for i in range(0, self.tvshows_fanart_limit):
                        name = 'fanart' if i == 0 else 'fanart{}'.format(i)
                        art[name] = self.fanartart.get(name, self.art.get(name, ''))
                except:
                    pass

                try:
                    if self.tvshows_banner == 'true':
                        art['banner'] = self.art.get('banner', self.baseImageUrl + self.info.get('banner', ''))
                        if art['banner'] == self.baseImageUrl:
                            art['banner'] = ''
                except:
                    pass

            # Set Info
            info = {}
            try:
                info['showaliases'] = self.info.get('aliases')
            except:
                pass
            try:
                info['genre'] = [genre.title() for genre in trakt_object['genres']]
            except:
                pass
            try:
                info['duration'] = int(self.info.get('runtime')) * 60
            except:
                pass
            try:
                info['rating'] = self.info.get('siteRating')
            except:
                pass
            try:
                info['premiered'] = trakt_object['first_aired']
            except:
                info['premiered'] = ''
                pass
            try:
                info['status'] = self.info.get('status')
            except:
                pass
            try:
                info['tvshowtitle'] = self.info['seriesName']
                if info['tvshowtitle'] is None:
                    info['tvshowtitle'] = trakt_object['title']
                if info['tvshowtitle'] is None:
                    return None
            except:
                return None
            try:
                info['year'] = str(trakt_object['year'])
            except:
                info['year'] = 0
                pass
            try:
                info['studio'] = self.info.get('network')
            except:
                pass
            try:
                info['originaltitle'] = self.info.get('seriesName')
            except:
                pass
            try:
                info['plot'] = self.info.get('overview')
            except:
                pass
            try:
                info['imdbnumber'] = self.info.get('imdbId')
            except:
                pass
            try:
                info['trailer'] = tools.youtube_url % trakt_object['trailer'].split('v=')[1]
            except:
                pass

            try:
                if '0' in self.episode_summary['airedSeasons']:
                    self.episode_summary['airedSeasons'].remove('0')
                info['season_count'] = len(self.episode_summary['airedSeasons'])
            except:
                info['season_count'] = 0
                pass

            try:
                info['episode_count'] = trakt_object['aired_episodes']
            except:
                info['episode_count'] = 0
                pass

            try:
                info['mediatype'] = 'tvshow'
            except:
                pass
            try:
                info['mpaa'] = self.info.get('rating')
            except:
                pass
            try:
                info['country'] = trakt_object.get('country', '').upper()
            except:
                info['country'] = ''
                pass

            requirements = ['country', 'tvshowtitle', 'year', 'season_count']
            for i in requirements:
                if i not in info:
                    return None

            item['ids'] = trakt_object['ids']
            item['info'] = info
            item['art'] = art
            item['cast'] = self.cast
            item['trakt_object'] = {}
            item['trakt_object']['shows'] = [trakt_object]

            item['art']['thumb'] = item['art'].get('poster', '')

            return item
        except:
            return None

    def seasonIDToListItem(self, seasonObject, showArgs):

        try:
            item = {'info': copy.deepcopy(showArgs['info']), 'art': copy.deepcopy(showArgs['art'])}
            tvdbID = showArgs['ids']['tvdb']
            season = seasonObject['number']

            if self.fanart_support:
                self.threads.append(threading.Thread(target=self.getFanartTVSeason, args=(tvdbID, season)))

            self.threads.append(threading.Thread(target=self.getSeasonInfo, args=(tvdbID, season)))

            if self.season_poster == 'true':
                self.threads.append(
                    threading.Thread(target=self.getSeasonArt, args=(tvdbID, 'poster', 'season', season,
                                                                     self.tvshows_poster_limit)))

            if self.season_banner == 'true':
                self.threads.append(
                    threading.Thread(target=self.getSeasonArt, args=(tvdbID, 'banner', 'seasonwide', season, 1)))

            [i.start() for i in self.threads]
            [i.join() for i in self.threads]

            details = self.info

            if details is None:
                return None

            item['art'].update(self.fanartart)
            item['art'].update(self.art)

            if self.tvshows_prefer_fanart:
                try:
                    if self.season_poster == 'true':
                        for i in range(0, self.tvshows_poster_limit):
                            name = 'poster' if i == 0 else 'poster{}'.format(i)
                            item['art'][name] = self.fanartart.get(name, self.art.get(name, item['art'].get(name, '')))
                except:
                    pass
                try:
                    if self.season_fanart == 'true':
                        for i in range(0, self.tvshows_fanart_limit):
                            name = 'fanart' if i == 0 else 'fanart{}'.format(i)
                            item['art'][name] = self.fanartart.get(name, item['art'].get(name, ''))
                except:
                    pass
                try:
                    if self.season_landscape == 'true':
                        item['art']['landscape'] = self.fanartart.get('landscape', item['art']['landscape'])
                except:
                    pass
                try:
                    if self.season_banner == 'true':
                        item['art']['banner'] = self.fanartart.get('banner', item['art'].get('banner', ''))
                except:
                    pass
            try:
                item['info']['studio'] = showArgs['info'].get('studio')
            except:
                pass
            try:
                item['info']['year'] = int(details.get('firstAired', '0000')[:4])
            except:
                pass
            try:
                item['info']['aired'] = seasonObject['first_aired']
            except:
                pass
            try:
                item['info']['episode_count'] = seasonObject['episode_count']
            except:
                item['info']['episode_count'] = 0
                pass
            try:
                item['info']['aired_episodes'] = seasonObject['aired_episodes']
            except:
                item['info']['aired_episodes'] = 0
                pass
            try:
                item['info']['premiered'] = seasonObject['first_aired']
            except:
                pass
            try:
                item['info']['plot'] = item['info']['overview'] = seasonObject['overview']
            except:
                pass

            try:
                item['info']['season'] = season
            except:
                pass

            try:
                item['info']['sortseason'] = season
            except:
                pass

            try:
                item['info']['season_title'] = seasonObject['title']
            except:
                pass

            if item['info']['season_title'] == '':
                return None

            item['info']['mediatype'] = 'season'
            item['ids'] = seasonObject['ids']
            item['cast'] = showArgs['cast']
            item['trakt_object'] = {}
            item['trakt_object']['seasons'] = [seasonObject]
            item['showInfo'] = showArgs

            item['art']['thumb'] = item['art'].get('poster', '')

        except:
            return None

        return item

    def episodeIDToListItem(self, trakt_object, showArgs):
        url = "episodes/%s" % trakt_object['ids']['tvdb']
        response = self.get_request(url)['data']

        item = {'info': None, 'art': None}

        art = copy.deepcopy(showArgs['seasonInfo']['art'])

        info = {}
        try:
            info['episode'] = info['sortepisode'] = int(response['airedEpisodeNumber'])
        except:
            pass
        try:
            info['absoluteNumber'] = int(response['absoluteNumber'])
        except:
            pass
        try:
            info['season'] = info['sortseason'] = int(response['airedSeason'])
        except:
            pass
        try:
            info['title'] = info['originaltitle'] = response.get('episodeName')
            if info['title'] is None:
                return None
        except:
            pass
        try:
            info['rating'] = float(response['siteRating'])
        except:
            pass

        try:
            info['premiered'] = trakt_object['first_aired']
            info['aired'] = trakt_object['first_aired']
        except:
            info['premiered'] = ''
            info['aired'] = ''

        try:
            info['year'] = trakt_object['first_aired'][:4]
        except:
            pass
        try:
            info['plot'] = response['overview']
        except:
            pass
        try:
            info['imdbnumber'] = response['imdbId']
        except:
            pass
        try:
            info['studio'] = showArgs['showInfo']['info'].get('studio')
        except:
            pass
        try:
            info['mpaa'] = showArgs['showInfo']['info']['mpaa']
        except:
            pass

        try:
            if self.episode_fanart == 'true':
                art.update(tmdb.TMDBAPI().getEpisodeFanartArt(trakt_object, showArgs))
        except:
            pass
        try:
            art['thumb'] = self.baseImageUrl + response['filename']
            if art['thumb'] == self.baseImageUrl:
                art['thumb'] = art['fanart']
            art['landscape'] = art['thumb']
        except:
            pass
        try:
            info['tvshowtitle'] = showArgs['showInfo']['info']['tvshowtitle']
        except:
            pass
        try:
            info['genre'] = showArgs['showInfo']['info']['genre']
        except:
            pass
        try:
            info['duration'] = showArgs['showInfo']['info']['duration']
        except:
            pass

        info['trailer'] = ''
        info['mediatype'] = 'episode'
        item['ids'] = trakt_object['ids']
        item['info'] = info
        item['art'] = art
        item['cast'] = showArgs['showInfo']['cast']
        item['trakt_object'] = {}
        item['trakt_object']['episodes'] = [trakt_object]
        item['showInfo'] = showArgs['showInfo']

        requirements = ['title', 'season', 'episode']
        for i in requirements:
            if info.get(i, None) == None:
                return None
            if i not in info:
                return None
        return item

    def getShowArt(self, tvdbID, keyType, number):
        try:
            url = 'series/{}/images/query?keyType={}'.format(tvdbID, keyType)
            response = self.get_request(url)
            return self._extract_art(response['data'], keyType, number)
        except:
            pass

    def _extract_art(self, response, dict_name, number):
        images = [(self.baseImageUrl + x['fileName'],
                   x['ratingsInfo']['average'] if x['ratingsInfo']['count'] >= 5 else 5 + (
                               x['ratingsInfo']['average'] - 5) * sin(x['ratingsInfo']['count'] / pi))
                  for x in response if x['languageId'] == 7]
        images = sorted(images, key=lambda x: int(x[1]), reverse=True)

        counter = 0
        for i in images[:number]:
            self.art[dict_name if counter == 0 else '{}{}'.format(dict_name, counter)] = i[0]
            counter = counter + 1

    def getShowInfo(self, tvdbID):
        try:
            url = 'series/%s' % tvdbID
            response = self.get_request(url)['data']
            self.info = response
        except:
            pass

    def getEpisodeSummary(self, tvdbID):
        try:
            url = 'series/%s/episodes/summary' % tvdbID
            response = self.get_request(url)['data']
            self.episode_summary = response
        except:
            pass

    def getSeasonArt(self, tvdbID, dict_name, art_name, season, number):
        try:
            url = 'series/{}/images/query?keyType={}&subKey={}'.format(tvdbID, art_name, season)
            response = self.get_request(url)
            return self._extract_art(response['data'], dict_name, number)
        except:
            pass

    def getSeasonInfo(self, tvdbID, season):
        try:
            url = 'series/%s/episodes/query?airedSeason=%s' % (tvdbID, season)
            response = self.get_request(url)['data'][0]
            self.info = response
        except:
            pass

    def getSeriesCast(self, tvdbID):
        try:
            url = 'series/%s/actors' % tvdbID
            actors = self.get_request(url)['data']
            actors = sorted(actors, key=lambda k: k['sortOrder'])

            for i in actors:
                self.cast.append({'name': i['name'], 'role': i['role'], 'thumbnail': self.baseImageUrl + i['image']})
        except:
            pass

    def getFanartTV(self, tvdb_id):
        try:
            artwork = fanarttv.get(tvdb_id, 'tv')
            self.fanartart.update(artwork)
        except:
            pass

    def getFanartTVSeason(self, tvdb_id, season):
        try:
            artwork = fanarttv.get(tvdb_id, 'season', season)
            self.fanartart.update(artwork)
        except:
            pass
