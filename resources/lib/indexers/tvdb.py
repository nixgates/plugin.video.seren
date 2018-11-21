import requests, json, threading, datetime, time
from resources.lib.common import tools

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
        self.show_cursory = None

        if self.jwToken is not '':
            self.headers['Authorization'] = 'Bearer %s' % self.jwToken
        else:
            self.newToken()
            self.headers['Authorization'] = 'Bearer %s' % self.jwToken

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
            self.newToken()
            self.headers['Authorization'] = 'Bearer %s' % self.jwToken
            response = requests.get(url, headers=self.headers).text
        response = json.loads(response)

        return response

    def renewToken(self):
        url = self.baseUrl + 'refresh_token'
        response = requests.post(url, headers=self.headers)
        response = json.loads(response.text)
        if 'Error' in response:
            self.newToken()
        else:
            self.jwToken = response['token']
        return

    def newToken(self):
        url = self.baseUrl + "login"
        postdata = {"apikey": self.apiKey}
        postdata = json.dumps(postdata)
        headers = self.headers
        if 'Authorization' in headers:
            headers.pop('Authorization')
        response = json.loads(requests.post(url, data=postdata, headers=self.headers).text)
        self.jwToken = response['token']
        tools.setSetting('tvdb.jw', self.jwToken)
        self.headers['Authorization'] = self.jwToken
        tools.log('Refreshed TVDB Token')
        tools.setSetting('tvdb.expiry', str(time.time() + (24 * (60*60))))
        return response

    def seriesIDToListItem(self, trakt_object, info_return=True):
        try:
            tvdbID = trakt_object['ids']['tvdb']
            self.threads.append(threading.Thread(target=self.getShowFanart, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getShowInfo, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getShowPoster, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getEpisodeSummary, args=(tvdbID,)))
            self.threads.append(threading.Thread(target=self.getSeriesCast, args=(tvdbID,)))

            for i in self.threads:
                i.start()
            for i in self.threads:
                i.join()
            item = {'info': None, 'art': None}

            # Set Art
            art = {}
            try:
                art['poster'] = self.art.get('poster')
            except:
                pass
            try:
                art['thumb'] = self.art.get('poster')
            except:
                pass
            try:
                art['landscape'] = self.art.get('fanart')
            except:
                pass
            try:
                art['fanart'] = self.art.get('fanart')
            except:
                pass
            try:
                art['banner'] = self.baseImageUrl + self.info.get('banner', '')
            except:
                pass

            # Set Info
            info = {}
            try:
                info['showaliases'] = self.info.get('aliases')
            except:
                pass
            try:
                info['genre'] = self.info.get('genre')
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
                info['premiered'] = self.info.get('firstAired')
            except:
                pass
            try:
                info['status'] = self.info.get('status')
            except:
                pass
            try:
                info['tvshowtitle'] = self.info.get('seriesName')
            except:
                pass
            try:
                info['year'] = self.info.get('firstAired')[:4]
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
                    self.episode_summary['airedSeasons'].pop(0)
                info['seasonCount'] = len(self.episode_summary['airedSeasons'])
            except:
                pass
            try:
                info['episodeCount'] = self.episode_summary['airedEpisodes']
            except:
                info['episodeCount'] = self.episode_summary['airedEpisodes']
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
                info['country'] = trakt_object['country'].upper()
            except:
                pass

            requirements = ['country', 'tvshowtitle', 'year', 'seasonCount']
            for i in requirements:
                if i not in info:
                    return None

            item['ids'] = trakt_object['ids']
            item['info'] = info
            item['art'] = art
            item['setCast'] = self.cast
            item['trakt_object'] = {}
            item['trakt_object']['shows'] = [trakt_object]

            if info_return is True:
                return item
            else:
                self.show_cursory = item
        except:
            import traceback
            traceback.print_exc()
            self.show_cursory = False
            return None

    def seasonIDToListItem(self, seasonObject, showArgs):

        try:
            arb = seasonObject['number']
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
                tools.log('ERROR TVDB FAILED FOR SEASON ' + str(season), 'error')
                return None

            try:
                item['art']['poster'] = item['art']['thumb'] = self.art['poster']
            except:
                item['art']['poster'] = item['art']['thumb'] = ''

            try:
                item['info']['year'] = int(details.get('firstAired', '0000')[:4])
            except:
                pass
            try:
                item['info']['aired'] = seasonObject['first_aired'][:10]
            except:
                pass
            try:
                item['info']['date'] = seasonObject['first_aired'][:10]
            except:
                pass
            try:
                item['info']['premiered'] = seasonObject['first_aired'][:10]
            except:
                pass
            try:
                item['info']['dateadded'] = seasonObject['first_aired'][:10]
            except:
                pass
            try:
                item['info']['plot'] = item['info']['overview'] = seasonObject['overview']
            except:
                import traceback
                traceback.print_exc()

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
                return None

            try:
                if seasonObject['first_aired'] is None:
                    pass
                else:
                    currentDate = datetime.datetime.today().date()
                    airdate = str(seasonObject['first_aired'][:10])
                    airdate = tools.datetime_workaround(airdate)
                    if airdate > currentDate:
                        item['info']['season_title'] = '[I][COLOR red]%s[/COLOR][/I]' % item['info']['season_title']
            except:
                return None
                pass

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
        if 'showInfo' not in showArgs:
            show_thread = threading.Thread(target=self.seriesIDToListItem, args=(showArgs, False))
            show_thread.daemon = True
            show_thread.start()

        url = "episodes/%s" % trakt_object['ids']['tvdb']
        response = self.get_request(url)['data']

        item = {'info': None, 'art': None}

        art = {}

        try:
            art['thumb'] = self.baseImageUrl + response['filename']
        except:
            pass

        info = {}
        try:
            info['dateadded'] = response['firstAired']
        except:
            pass
        try:
            info['episode'] = info['sortepisode'] = int(response['airedEpisodeNumber'])
        except:
            pass
        try:
            info['season'] = info['sortseason'] = int(response['airedSeason'])
        except:
            pass
        try:
            info['title'] = info['originaltitle'] = response['episodeName']
        except:
            pass
        try:
            info['rating'] = float(response['siteRating'])
        except:
            pass
        try:
            info['premiered'] = response['firstAired']
        except:
            pass
        try:
            info['year'] = int(response['firstAired'][:4])
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
        if 'showInfo' not in showArgs:
            if show_thread.is_alive():
                show_thread.join()
            if self.show_cursory is False or self.show_cursory is None:
                return None
            else:
                showArgs = {'showInfo':{}}
                showArgs['showInfo'] = self.show_cursory
        try:
            info['mpaa'] = showArgs['showInfo']['info']['mpaa']
        except:
            pass
        try:
            art['poster'] = showArgs['showInfo']['art']['poster']
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
        try:
            art['fanart'] = showArgs['showInfo']['art']['fanart']
        except:
            pass

        try:
            currentDate = datetime.datetime.today().date()
            airdate = str(response['firstAired'])
            if airdate == '':
                info['title'] = '[I][COLOR red]%s[/COLOR][/I]' % info['title']
            airdate = tools.datetime_workaround(airdate)
            if airdate > currentDate:
                info['title'] = '[I][COLOR red]%s[/COLOR][/I]' % info['title']
        except:
            import traceback
            traceback.print_exc()
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
            if info[i] == None:
                return None
            if i not in info:
                return None
        return item

    def getShowFanart(self, tvdbID):
        try:
            url = 'series/%s/images/query?keyType=fanart' % tvdbID
            response = self.get_request(url)['data']
            image = response[0]
            for i in response:
                if float(i['ratingsInfo']['average']) > float(image['ratingsInfo']['average']):
                    image = i
                else:
                    continue
            image = self.baseImageUrl + image['fileName']
            self.art['fanart'] = image
        except:
            pass

    def getShowPoster(self, tvdbID):
        try:
            url = 'series/%s/images/query?keyType=poster' % tvdbID
            response = self.get_request(url)['data']
            image = response[0]
            for i in response:
                if float(i['ratingsInfo']['average']) > float(image['ratingsInfo']['average']):
                    image = i
                else:
                    continue
            image = self.baseImageUrl + image['fileName']
            self.art['poster'] = image
        except:
            pass

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

    def getSeasonPoster(self, tvdbID, season):
        try:
            url = 'series/%s/images/query?keyType=season&subKey=%s' % (tvdbID, season)
            response = self.get_request(url)['data']
            image = response[0]
            for i in response:
                if float(i['ratingsInfo']['average']) > float(image['ratingsInfo']['average']):
                    image = i
                else:
                    continue
            image = self.baseImageUrl + image['fileName']
            self.art['poster'] = image
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
                self.cast.append({'name': i['name'], 'role': i['role'], 'image': i['image']})
        except:
            pass
