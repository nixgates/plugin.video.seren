# -*- coding: utf-8 -*-

import datetime
import json
import requests
import threading
import time

from resources.lib.common import tools
from resources.lib.indexers import fanarttv

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

        if tools.fanart_api_key == '': self.fanart_support = False
        else: self.fanart_support = True

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
        if not ignore_lock:
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

            self.threads.append(threading.Thread(target=self.getShowFanart, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getShowPoster, args=(tvdbID,)))

            self.threads.append(threading.Thread(target=self.getShowInfo, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getEpisodeSummary, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getSeriesCast, args=(tvdbID,)))

            for i in self.threads:
                i.start()
            for i in self.threads:
                i.join()

            item = {'info': None, 'art': None}
            if self.info == {}:
                return None
            # Set Art
            art = {}
            try:
                if self.fanart_support:
                    art['landscape'] = self.art.get('landscape')
                if art['landscape'] == '':
                    art['landscape'] = self.art.get('fanart')
            except:
                pass
            try:
                art['poster'] = self.art.get('poster')
            except:
                pass
            try:
                art['thumb'] = self.art.get('poster')
            except:
                pass
            try:
                art['fanart'] = self.art.get('fanart')
            except:
                pass
            try:
                art['clearart'] = self.art.get('clearart')
            except:
                pass
            try:
                art['clearlogo'] = self.art.get('clearlogo')
            except:
                pass

            try:
                art['banner'] = self.baseImageUrl + self.info.get('banner', '')
                if art['banner'] == self.baseImageUrl:
                    art['banner'] = 0
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
                info['year'] = self.info.get('firstAired')[:4]
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
                info['imdbnumber'] = self.info.get('imdb_id')
            except:
                pass
            try:
                info['trailer'] = tools.youtube_url % trakt_object['trailer'].split('v=')[1]
            except:
                pass
            try:
                info['castandrole'] = [(i['name'], i['role']) for i in self.cast]
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
            item['setCast'] = self.cast
            item['trakt_object'] = {}
            item['trakt_object']['shows'] = [trakt_object]


            return item
        except:
            return None

    def seasonIDToListItem(self, seasonObject, showArgs):

        try:
            item = {'info': showArgs['info'], 'art': showArgs['art']}
            tvdbID = showArgs['ids']['tvdb']
            season = seasonObject['number']

            self.threads.append(threading.Thread(target=self.getSeasonInfo, args=(tvdbID, season)))
            self.threads.append(threading.Thread(target=self.getSeasonPoster, args=(tvdbID, season)))

            for i in self.threads:
                i.start()
            for i in self.threads:
                i.join()

            details = self.info

            if details == None:
                return None
            try:
                item['info']['studio'] = showArgs['info'].get('studio')
            except:
                pass
            try:
                item['art']['poster'] = item['art']['thumb'] = self.art.get('poster', '')
                if item['art']['poster'] == '' or item['art']['poster'] is None:
                    item['art']['poster'] = item['art']['thumb'] = showArgs['art']['poster']
            except:
                item['art']['poster'] = item['art']['thumb'] = ''

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
            try:
                item['info']['castandrole'] = showArgs['info']['castandrole']
            except:
                pass
            if item['info']['season_title'] == '':
                import traceback
                traceback.print_exc()
                return None

            item['info']['mediatype'] = 'season'
            item['ids'] = seasonObject['ids']
            item['trakt_object'] = {}
            item['trakt_object']['seasons'] = [seasonObject]
            item['showInfo'] = showArgs

        except:
            import traceback
            traceback.print_exc()
            return None

        return item

    def episodeIDToListItem(self, trakt_object, showArgs):

        url = "episodes/%s" % trakt_object['ids']['tvdb']
        response = self.get_request(url)['data']

        item = {'info': None, 'art': None}

        art = {}

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
            art = showArgs['showInfo']['art']
        except:
            pass
        try:
            art['thumb'] = self.baseImageUrl + response['filename']
            if art['thumb'] == self.baseImageUrl:
                art['thumb'] = art['fanart']
        except:
            pass
        try:
            info['castandrole'] = showArgs['showInfo']['info']['castandrole']
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
        try:
            art['landscape'] = art['thumb']
        except:
            pass

        info['trailer'] = ''
        info['mediatype'] = 'episode'
        item['ids'] = trakt_object['ids']
        item['info'] = info
        item['art'] = art
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

    def getShowFanart(self, tvdbID):
        tools.tv_sema.acquire()
        try:
            url = 'series/%s/images/query?keyType=fanart' % tvdbID
            response = self.get_request(url)['data']
            try:
                image = [i for i in response if i['languageId'] == 7][0]
            except:
                image = response[0]
            for i in [k for k in response if k['languageId'] == 7]:
                if float(i['ratingsInfo']['average']) > float(image['ratingsInfo']['average']):
                    image = i
                else:
                    continue
            image = self.baseImageUrl + image['fileName']
            if image == self.baseImageUrl:
                image = 0
            self.art['fanart'] = image
        except:
            pass

        tools.tv_sema.release()

    def getShowPoster(self, tvdbID):
        tools.tv_sema.acquire()
        try:
            url = 'series/%s/images/query?keyType=poster' % tvdbID
            response = self.get_request(url)['data']
            try:
                image = [i for i in response if i['languageId'] == 7][0]
            except:
                image = response[0]
            for i in [k for k in response if k['languageId'] == 7]:
                if float(i['ratingsInfo']['average']) > float(image['ratingsInfo']['average']):
                    image = i
                else:
                    continue
            image = self.baseImageUrl + image['fileName']
            if image == self.baseImageUrl:
                image = 0
            self.art['poster'] = image
        except:
            pass

        tools.tv_sema.release()

    def getShowInfo(self, tvdbID):
        tools.tv_sema.acquire()
        try:
            url = 'series/%s' % tvdbID
            response = self.get_request(url)['data']
            self.info = response
        except:
            pass

        tools.tv_sema.release()

    def getEpisodeSummary(self, tvdbID):
        tools.tv_sema.acquire()
        try:
            url = 'series/%s/episodes/summary' % tvdbID
            response = self.get_request(url)['data']
            self.episode_summary = response
        except:
            pass

        tools.tv_sema.release()

    def getSeasonPoster(self, tvdbID, season):
        tools.tv_sema.acquire()
        try:
            url = 'series/%s/images/query?keyType=season&subKey=%s' % (tvdbID, season)
            response = self.get_request(url)['data']
            try:
                image = [i for i in response if i['languageId'] == 7][0]
            except:
                image = response[0]
            for i in [k for k in response if k['languageId'] == 7]:
                if float(i['ratingsInfo']['average']) > float(image['ratingsInfo']['average']):
                    image = i
                else:
                    continue
            image = self.baseImageUrl + image['fileName']
            if image == self.baseImageUrl:
                image = 0
            self.art['poster'] = image
        except:
            import traceback
            traceback.print_exc()
            pass

        tools.tv_sema.release()

    def getSeasonInfo(self, tvdbID, season):
        tools.tv_sema.acquire()
        try:
            url = 'series/%s/episodes/query?airedSeason=%s' % (tvdbID, season)
            response = self.get_request(url)['data'][0]
            self.info = response
        except:
            import traceback
            traceback.print_exc()
            pass

        tools.tv_sema.release()

    def getSeriesCast(self, tvdbID):
        tools.tv_sema.acquire()
        try:
            url = 'series/%s/actors' % tvdbID
            actors = self.get_request(url)['data']
            actors = sorted(actors, key=lambda k: k['sortOrder'])

            for i in actors:
                self.cast.append({'name': i['name'], 'role': i['role'], 'image': i['image']})
        except:
            pass

        tools.tv_sema.release()

    def getFanartTV(self, imdb_id):
        tools.tv_sema.acquire()
        try:
            artwork = fanarttv.get(imdb_id, 'tv')
            artwork.pop('poster')
            artwork.pop('fanart')
            artwork.pop('banner')
            self.art.update(artwork)
        except:
            import traceback
            traceback.print_exc()
            pass

        tools.tv_sema.release()