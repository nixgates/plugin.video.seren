# -*- coding: utf-8 -*-
import copy
import json
import threading
import traceback
from datetime import datetime
from time import sleep

import requests

from resources.lib.common import tools
from resources.lib.indexers import fanarttv


class TMDBAPI:
    def __init__(self):
        self.apiKey = tools.getSetting('tmdb.apikey')
        if self.apiKey == '':
            self.apiKey = "9f3ca569aa46b6fb13931ec96ab8ae7e"
        self.baseUrl = "https://api.themoviedb.org/3/"
        self.posterPath = "https://image.tmdb.org/t/p/w500"
        self.thumbPath = "https://image.tmdb.org/t/p/w500"
        self.backgroundPath = "https://image.tmdb.org/t/p/w1280"

        self.movies_poster_limit = int(tools.getSetting('movies.poster_limit'))
        self.movies_fanart_limit = int(tools.getSetting('movies.fanart_limit'))
        self.movies_landscape = bool(tools.getSetting('movies.landscape'))

        self.tvshows_poster_limit = int(tools.getSetting('tvshows.poster_limit'))
        self.tvshows_landscape = tools.getSetting('tvshows.landscape')
        self.season_poster = tools.getSetting('season.poster')
        self.episode_fanart = bool(tools.getSetting('episode.fanart'))

        self.tvshows_prefer_fanart = tools.getSetting('tvshows.preferedsource') == '0'
        self.movies_prefer_fanart = tools.getSetting('movies.preferedsource') == '0'
        self.request_response = None
        self.threads = []

        self.art = {}
        self.fanartart = {}
        self.info = {}
        self.episode_summary = {}
        self.cast = []
        if not tools.fanart_api_key == '':
            self.fanarttv = True
        else:
            self.fanarttv = False

    def get_request(self, url):
        try:
            if '?' not in url:
                url += "?"
            else:
                url += "&"

            if 'api_key' not in url:
                url += "api_key=%s" % self.apiKey
                url = self.baseUrl + url

            try:
                try:
                    response = requests.get(url)
                except requests.exceptions.SSLError:
                    response = requests.get(url, verify=False)
            except requests.exceptions.ConnectionError:
                tools.showDialog.notification(tools.addonName, tools.lang(32028))
                return

            if '200' in str(response):
                response = json.loads(response.text)
                self.request_response = response
                return response
            elif 'Retry-After' in response.headers:
                # API REQUESTS ARE BEING THROTTLED, INTRODUCE WAIT TIME
                throttleTime = response.headers['Retry-After']
                tools.log('TMDB Throttling Applied, Sleeping for %s seconds' % throttleTime, '')
                sleep(int(throttleTime) + 1)
                return self.get_request(url)
            else:
                return None
        except:
            import traceback
            traceback.print_exc()

    def get_TMDB_Fanart_Threaded(self, tmdb_url, fanart_args):

        self.threads.append(threading.Thread(target=self.get_request, args=(tmdb_url,)))

        if self.fanarttv:
            self.threads.append(threading.Thread(target=self.getFanartTVMovie, args=fanart_args))

        for thread in self.threads:
            thread.start()

        for thread in self.threads:
            thread.join()

    def showSeasonToListItem(self, seasonObject, showArgs):

        try:
            self.art = copy.deepcopy(showArgs['art'])
            item = {'info': copy.deepcopy(showArgs['info'])}

            url = 'tv/%s/season/%s?&append_to_response=credits,videos,images&language=en-US' % (
                str(showArgs['ids']['tmdb']), str(seasonObject['number']))

            self.get_TMDB_Fanart_Threaded(url, (showArgs['ids']['tmdb'],))

            details = self.request_response

            if details is None:
                return None

            try:
                currentDate = datetime.today().date()
                airdate = str(details['air_date'])
                airdate = tools.datetime_workaround(airdate)

                if airdate > currentDate:
                    return
            except:
                pass

            try:
                if self.season_poster == 'true':
                    self.art['poster'] = self.posterPath + str(details.get('poster_path', ''))
                    self.art['thumb'] = self.posterPath + str(details.get('poster_path', ''))
            except:
                pass

            try:
                count = 0
                for i in details['images']['posters'][:self.tvshows_poster_limit]:
                    self.art.update({'poster{}'.format(count if count > 0 else ''): self.backgroundPath + i['file_path']})
                    count = count + 1
            except:
                pass

            if self.tvshows_prefer_fanart:
                try:
                    if self.season_poster == 'true':
                        self.art['poster'] = self.fanartart.get('poster', self.posterPath + str(details.get('poster_path', '')))
                        self.art['thumb'] = self.fanartart.get('thumb',
                                                               self.posterPath + str(details.get('poster_path', '')))
                except:
                    pass

                try:
                    count = 0
                    for i in details['images']['posters'][:self.tvshows_poster_limit]:
                        dict_name = 'poster{}'.format(count if count > 0 else '')
                        self.art.update({dict_name: self.fanartart.get(dict_name, self.backgroundPath + i['file_path'])})
                        count = count + 1
                except:
                    pass

            try:
                if details.get('overview', '') is not '':
                    item['info']['plot'] = item['info']['plotoutline'] = details.get('overview', '')
            except:
                pass
            try:
                item['info']['aired'] = details.get('air_date', '')
            except:
                import traceback
                traceback.print_exc()
                pass
            try:
                item['info']['premiered'] = details.get('air_date', '')
            except:
                import traceback
                traceback.print_exc()
                pass
            try:
                item['info']['year'] = details.get('air_date', '0000')[:4]
            except:
                pass
            try:
                item['info']['sortseason'] = str(details.get('season_number', ''))
            except:
                pass
            try:
                item['info']['season'] = str(details.get('season_number', ''))
            except:
                pass
            try:
                item['info']['season_title'] = str(details.get('name', ''))
            except:
                pass
            try:
                item['info']['trailer'] = tools.youtube_url % \
                                          [i for i in details['videos']['results'] if i['site'] == 'YouTube'][0]['key']
            except:
                pass
            try:
                item['info']['episode_count'] = len(details['episodes'])
            except:
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
                item['info']['season_title'] = seasonObject['title']
            except:
                pass

            if item['info']['season_title'] == '':
                return None

            director = None

            for person in details['credits']['crew']:
                if person.get('job') == 'Director':
                    director = person.get('name')

            if not director is None:
                item['info']['director'] = director

            try:
                item['cast'] = [{'name': i['name'], 'role': i['character'], 'thumbnail': '{}{}'
                    .format(self.backgroundPath, i['profile_path'])}
                                for i in details['credits']['cast']]
            except:
                pass

            item['info']['mediatype'] = 'season'
            item['ids'] = seasonObject['ids']
            item['trakt_object'] = {}
            item['trakt_object']['seasons'] = [seasonObject]
            item['art'] = self.art
            item['info']['mediatype'] = 'season'
            item['showInfo'] = showArgs

            item['art']['thumb'] = item['art'].get('poster', '')

        except:
            import traceback
            traceback.print_exc()
            return None

        return item

    def movieToListItem(self, trakt_object):

        try:

            if trakt_object['ids']['tmdb'] is None:
                return None

            url = 'movie/%s?&append_to_response=credits,videos,release_dates,images&language=en-US' % str(trakt_object['ids']['tmdb'])

            self.get_TMDB_Fanart_Threaded(url, (trakt_object['ids']['tmdb'],))

            details = self.request_response

            if details is None:
                return None

            item = {'info': None, 'art': None}

            # Set Art

            self.art.update(self.fanartart)
            try:
                if self.movies_landscape:
                    self.art['landscape'] = self.backgroundPath + str(details.get('backdrop_path', ''))
            except:
                pass
            try:
                self.art['poster'] = self.backgroundPath + str(details.get('poster_path', ''))
                self.art['thumb'] = self.art['poster']
            except:
                pass
            try:
                self.art['fanart'] = self.backgroundPath + str(details.get('backdrop_path', ''))
            except:
                pass

            try:
                count = 0
                for i in details['images']['backdrops'][:self.movies_fanart_limit]:
                    self.art.update(
                        {'fanart{}'.format(count if count > 0 else ''): self.backgroundPath + i['file_path']})
                    count = count + 1
            except:
                pass

            try:
                count = 0
                for i in details['images']['posters'][:self.movies_poster_limit]:
                    self.art.update(
                        {'poster{}'.format(count if count > 0 else ''): self.backgroundPath + i['file_path']})
                    count = count + 1
            except:
                pass

            if self.movies_prefer_fanart:
                try:
                    if self.movies_landscape:
                        self.art['landscape'] = self.fanartart.get('landscape',
                                                             self.backgroundPath + str(
                                                                 details.get('backdrop_path', '')))
                except:
                    pass
                try:
                    self.art['poster'] = self.fanartart.get('poster',
                                                      self.backgroundPath + str(details.get('poster_path', '')))
                    self.art['thumb'] = self.fanartart['poster']
                except:
                    pass
                try:
                    self.art['fanart'] = self.fanartart.get('fanart',
                                                      self.backgroundPath + str(details.get('backdrop_path', '')))
                except:
                    pass

                try:
                    count = 0
                    for i in details['images']['backdrops'][:self.movies_fanart_limit]:
                        dict_name = 'fanart{}'.format(count if count > 0 else '')
                        self.art.update(
                            {dict_name: self.fanartart.get(dict_name, self.backgroundPath + i['file_path'])})
                        count = count + 1
                except:
                    pass

                try:
                    count = 0
                    for i in details['images']['posters'][:self.movies_poster_limit]:
                        dict_name = 'poster{}'.format(count if count > 0 else '')
                        self.art.update(
                            {dict_name: self.fanartart.get(dict_name, self.backgroundPath + i['file_path'])})
                        count = count + 1
                except:
                    pass

            # Set Info
            info = {}
            try:
                info['genre'] = []

                if 'genres' in details:
                    for i in details['genres']:
                        info['genre'].append(i.get('name'))
            except:
                pass
            try:
                mpaa = details.get('release_dates')['results']
                mpaa = [i for i in mpaa if i['iso_3166_1'] == 'US']
                mpaa = mpaa[0].get('release_dates')[0].get('certification')
                info['mpaa'] = str(mpaa)
            except:
                pass

            try:
                info['rating'] = float(details.get('vote_average'))
            except:
                pass

            try:
                info['title'] = details.get('title')
            except:
                return None

            try:
                info['year'] = details.get('release_date')[:4]
            except:
                return None

            try:
                info['duration'] = details.get('runtime')
                info['duration'] = int(info['duration']) * 60
            except:
                info['duration'] = 0

            try:
                info['originaltitle'] = details.get('original_title')
            except:
                pass

            try:
                info['tagline'] = details.get('tagline')
            except:
                pass

            try:
                info['aired'] = details.get('release_date', '')
            except:
                pass

            try:
                info['premiered'] = details.get('release_date', '')
            except:
                pass

            try:
                info['plot'] = details.get('overview')
            except:
                pass

            try:
                info['imdbnumber'] = details.get('imdb_id')
            except:
                pass

            try:
                info['trailer'] = tools.youtube_url % \
                                  [i for i in details['videos']['results'] if i['site'] == 'YouTube'][0]['key']
            except:
                pass

            try:
                info['aliases'] = [i['title'] for i in details['alternative_titles']['titles']]
            except:
                info['aliases'] = []

            info['mediatype'] = 'movie'

            # Set Crew/Cast Info
            director = None
            for person in details['credits']['crew']:
                if person.get('job') == 'Director':
                    director = person.get('name')

            if not director is None:
                info['director'] = director

            try:
                item['cast'] = [{'name': i['name'], 'role': i['character'], 'thumbnail': '{}{}'
                    .format(self.backgroundPath, i['profile_path'])} for i in details['credits']['cast']]
            except:
                pass

            item['ids'] = trakt_object['ids']
            item['info'] = info
            item['art'] = self.art
            item['trakt_object'] = {}
            item['trakt_object']['movies'] = [trakt_object]
            return item

        except:
            import traceback
            traceback.print_exc()
            return None

    def showToListItem(self, traktItem):

        try:
            if traktItem['ids']['tmdb'] is None:
                return None

            url = 'tv/%s?&append_to_response=credits,alternative_titles,videos,content_ratings,images&language=en-US' % \
                  traktItem['ids']['tmdb']

            self.get_TMDB_Fanart_Threaded(url, (traktItem['ids']['tmdb'],))

            details = self.request_response

            if details is None:
                return None

            parsed_info = self.parseShowInfo(details, traktItem)
            return parsed_info
        except:
            return None

    def parseShowInfo(self, details, trakt_info):
        try:

            item = {'info': None}

            self.art.update(self.fanartart)
            # Set Art
            try:
                self.art['poster'] = self.posterPath + str(details.get('poster_path', ''))
            except:
                pass

            try:
                self.art['fanart'] = self.backgroundPath + str(details.get('backdrop_path', ''))
            except:
                pass

            try:
                self.art['thumb'] = self.posterPath + str(details.get('poster_path', ''))
            except:
                pass

            try:
                if self.tvshows_landscape == 'true':
                    self.art['landscape'] = self.backgroundPath + str(details.get('backdrop_path', ''))
            except:
                pass

            try:
                count = 0
                for i in details['images']['backdrops'][:self.movies_fanart_limit]:
                    dict_name = 'fanart{}'.format(count if count > 0 else '')
                    self.art.update({dict_name: self.backgroundPath + i['file_path']})
                    count = count + 1
            except:
                pass

            try:
                count = 0
                for i in details['images']['posters'][:self.movies_poster_limit]:
                    dict_name = 'poster{}'.format(count if count > 0 else '')
                    self.art.update({dict_name: self.backgroundPath + i['file_path']})
                    count = count + 1
            except:
                pass

            if self.tvshows_prefer_fanart:
                # Set Art
                try:
                    self.art['poster'] = self.fanartart.get('poster',
                                                      self.posterPath + str(details.get('poster_path', '')))
                except:
                    pass

                try:
                    self.art['fanart'] = self.fanartart.get('fanart',
                                                      self.backgroundPath + str(details.get('backdrop_path', '')))
                except:
                    pass

                try:
                    self.art['thumb'] = self.fanartart.get('thumb',
                                                     self.posterPath + str(details.get('poster_path', '')))
                except:
                    pass

                try:
                    if self.tvshows_landscape == 'true' :
                        self.art['landscape'] = self.fanartart.get('landscape',
                                                             self.backgroundPath + str(
                                                                 details.get('backdrop_path', '')))
                except:
                    pass

                try:
                    count = 0
                    for i in details['images']['backdrops'][:self.movies_fanart_limit]:
                        dict_name = 'fanart{}'.format(count if count > 0 else '')
                        self.art.update(
                            {dict_name: self.fanartart.get(dict_name, self.backgroundPath + i['file_path'])})
                        count = count + 1
                except:
                    pass

                try:
                    count = 0
                    for i in details['images']['posters'][:self.movies_poster_limit]:
                        dict_name = 'poster{}'.format(count if count > 0 else '')
                        self.art.update(
                            {dict_name: self.fanartart.get(dict_name, self.backgroundPath + i['file_path'])})
                        count = count + 1
                except:
                    pass

            # Set Info
            info = {}

            try:
                info['showaliases'] = [alias['title'] for alias in details['alternative_titles']['results']]
            except:
                pass

            try:
                info['trailer'] = tools.youtube_url % \
                                  [i for i in details['videos']['results'] if i['site'] == 'YouTube'][0]['key']
            except:
                pass

            try:
                info['genre'] = [str(i['name']).title() for i in details.get('genres', [])]
            except:
                pass

            try:
                info['duration'] = int(details.get('episode_run_time', '')[0]) * 60
            except:
                pass

            try:
                info['rating'] = float(details.get('vote_average', float(0.0)))
            except:
                pass

            try:
                info['aired'] = details.get('first_air_date', '')
            except:
                pass

            try:
                info['premiered'] = trakt_info['first_aired']
            except:
                pass

            try:
                info['year'] = details.get('first_air_date', '0000')[:4]
            except:
                pass

            try:
                info['status'] = details.get('status', '')
            except:
                pass

            try:
                info['tvshowtitle'] = details.get('name')
            except:
                pass

            try:
                info['country'] = details['origin_country'][0]
            except:
                pass

            try:
                info['originaltitle'] = details.get('name')
            except:
                pass

            try:
                info['plot'] = details.get('overview', '')
            except:
                pass

            try:
                info['imdbnumber'] = trakt_info['ids']['imdb']
            except:
                pass

            try:
                info['episode_count'] = trakt_info['aired_episodes']
            except:
                info['episode_count'] = 0
                pass

            info['mediatype'] = 'tvshow'

            try:
                info['mpaa'] = [i['rating'] for i in details['content_ratings']['results'] if i['iso_3166_1'] == 'US'][
                    0]
            except:
                pass

            try:
                info['season_count'] = details.get('number_of_seasons', '')
            except:
                return None

            try:
                info['tag'] = [i['name'] for i in details['keywords']['results']]
            except:
                pass

            try:
                info['studio'] = details.get('networks', None)[0]['name']
            except:
                info['studio'] = ''

            # Set Crew/Cast Info
            director = None
            for person in details['credits']['crew']:
                if person.get('job') == 'Director':
                    director = person.get('name')

            if not director is None:
                info['director'] = director

            try:
                item['cast'] = [{'name': i['name'], 'role': i['character'], 'thumbnail': '{}{}'
                    .format(self.backgroundPath, i['profile_path'])} for i in details['credits']['cast']]
            except:
                pass

            item['ids'] = trakt_info['ids']
            item['info'] = info
            item['art'] = self.art
            item['trakt_object'] = {}
            item['trakt_object']['shows'] = [trakt_info]

            item['art']['thumb'] = item['art'].get('poster', '')

            return item
        except:
            import traceback
            traceback.print_exc()
            return None

    def episodeIDToListItem(self, traktInfo, showArgs):
        try:
            if showArgs['showInfo']['ids']['tmdb'] is None:
                return None

            url = 'tv/%s/season/%s/episode/%s?&append_to_response=credits,videos,images&language=en-US' % (
                showArgs['showInfo']['ids']['tmdb'],
                traktInfo['season'],
                traktInfo['number'])
            response = self.get_request(url)

            if response.get('status_code') == 34:
                return None

            parsed_info = self.parseEpisodeInfo(response, traktInfo, showArgs)

            return parsed_info
        except:
            return None

    def getEpisodeFanartArt(self, traktInfo, showArgs):
        try:
            if showArgs['showInfo']['ids']['tmdb'] is None:
                return {}

            url = 'tv/%s/season/%s/episode/%s/images&language=en-US' % (
                showArgs['showInfo']['ids']['tmdb'],
                traktInfo['season'],
                traktInfo['number'])
            response = self.get_request(url)

            if response.get('status_code') == 34:
                return {}

            return self.parseEpisodeFanart(response)
        except:
            return {}

    def parseEpisodeFanart(self, response):
        art = {}
        counter = 0
        for still in response.joins()['stills']:
            art['fanart{}'.format(counter if counter > 0 else '')] = self.backgroundPath + still['file_path']
            counter = counter + 1

    def parseEpisodeInfo(self, response, traktInfo, showArgs):
        try:
            if "status_code" in response:
                if response["status_code"] == 34: return None

            try:
                response['name'] = tools.deaccentString(response['name'])
            except:
                pass
            try:
                currentDate = datetime.today().date()
                airdate = str(response['air_date'])
                airdate = tools.datetime_workaround(airdate)
                if airdate > currentDate:
                    return
            except:
                pass

            item = {'info': None, 'art': None}

            art = copy.deepcopy(showArgs['seasonInfo']['art'])
            try:
                if self.episode_fanart == 'true':
                    art.update(self.parseEpisodeFanart(response))

                art['landscape'] = self.backgroundPath + response.get('still_path', '')
                art['thumb'] = self.thumbPath + response.get('still_path', '')
            except:
                pass

            info = {}

            try:
                info['trailer'] = tools.youtube_url % \
                                  [i for i in response['videos']['results'] if i['site'] == 'YouTube'][0]['key']
            except:
                pass
            try:
                info['duration'] = showArgs['showInfo']['info'].get('duration')
            except:
                pass
            try:
                info['episode'] = response.get('episode_number', '')
            except:
                pass
            try:
                info['season'] = response.get('season_number', '')
            except:
                pass
            try:
                info['sortepisode'] = response.get('episode_number', '')
            except:
                pass
            try:
                info['sortseason'] = response.get('season_number', '')
            except:
                pass
            try:
                info['genre'] = showArgs['showInfo']['info']['genre']
            except:
                pass
            try:
                info['title'] = info['sorttitle'] = info['originaltitle'] = tools.deaccentString(response['name'])
            except:
                return None
            try:
                info['rating'] = response.get('vote_average', '')
            except:
                pass
            try:
                info['aired'] = traktInfo['first_aired']
            except:
                import traceback
                traceback.print_exc()
                pass
            try:
                info['premiered'] = traktInfo['first_aired']
            except:
                pass
            try:
                info['year'] = response.get('air_date', '0000')[:4]
            except:
                pass
            try:
                info['tvshowtitle'] = showArgs['showInfo']['info']['tvshowtitle']
            except:
                pass
            try:
                info['year'] = response.get('firstAired', '')[:4]
            except:
                pass

            try:
                info['plot'] = response.get('overview', '')
            except:
                pass
            try:
                info['imdbnumber'] = showArgs['showInfo']['ids']['imdb']
            except:
                pass
            try:
                info['mediatype'] = 'episode'
            except:
                pass
            try:
                info['mpaa'] = showArgs['showInfo']['info']['mpaa']
            except:
                pass

            try:
                item['cast'] = [{'name': i['name'], 'role': i['character'], 'thumbnail': '{}{}'
                    .format(self.backgroundPath, i['profile_path'])}
                                for i in response['credits']['cast']]
            except:
                item['cast'] = []
                pass

            item['ids'] = traktInfo['ids']
            item['info'] = info
            item['art'] = art
            item['showInfo'] = showArgs['showInfo']
            item['trakt_object'] = {}
            item['trakt_object']['episodes'] = [traktInfo]

            return item

        except:
            import traceback
            traceback.print_exc()
            return None

    def directToEpisode(self, traktObject):
        show_info = self.showToListItem(traktObject['show'])
        episode_info = self.episodeIDToListItem(show_info, traktObject['episode'])
        episode_info['showInfo'] = show_info

        return episode_info

    def getFanartTVShow(self, tvdb_id):
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

    def getFanartTVMovie(self, tmdb_id):
        try:
            artwork = fanarttv.get(tmdb_id, 'movies')
            self.fanartart.update(artwork)
        except:
            traceback.print_exc()
            pass