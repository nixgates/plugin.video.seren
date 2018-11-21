import requests, json
from time import sleep
from resources.lib.common import tools
from datetime import datetime

class TMDBAPI:
    def __init__(self):
        self.apiKey = tools.getSetting('tmdb.apikey')
        if self.apiKey == '':
            self.apiKey = "9f3ca569aa46b6fb13931ec96ab8ae7e"
        self.baseUrl = "https://api.themoviedb.org/3/"
        self.posterPath = "https://image.tmdb.org/t/p/w500"
        self.thumbPath = "https://image.tmdb.org/t/p/w500"
        self.backgroundPath = "https://image.tmdb.org/t/p/w1280"

    def get_request(self, url):
        if '?' not in url:
            url += "?"
        else:
            url += "&"

        if 'api_key' not in url:
            url += "api_key=%s" % self.apiKey
            url = self.baseUrl + url

        try:
            response = requests.get(url)
        except requests.exceptions.ConnectionError:
            tools.showDialog.ok(tools.addonName, tools.lang(32028))
            return

        if '200' in str(response):
            return json.loads(response.text)
        elif 'Retry-After' in response.headers:
            # API REQUESTS ARE BEING THROTTLED, INTRODUCE WAIT TIME
            throttleTime = response.headers['Retry-After']
            tools.log('TMDB Throttling Applied, Sleeping for %s seconds' % throttleTime, '')
            sleep(int(throttleTime) + 1)
            return self.get_request(url)
        else:
            tools.log('Get request failed to TMDB URL: %s' % url, 'error')
            tools.log('TMDB Response: %s' % response.text, 'error')
            return None

    def showSeasonToListItem(self, seasonObject, showArgs):

        try:
            item = {'info': showArgs['info'], 'art': showArgs['art']}

            url = 'tv/%s/season/%s?&append_to_response=credits,videos' % (str(showArgs['ids']['tmdb']), str(seasonObject['number']))

            details = self.get_request(url)

            if details == None:
                tools.log('ERROR TMDB FAILED FOR SEASON ID ' + str(seasonObject['tmdb']), 'error')
                return None
            try:
                currentDate = datetime.today().date()
                airdate = str(details['air_date'])
                airdate = tools.datetime_workaround(airdate)
            except:
                pass
            try:
                if airdate > currentDate:
                    return
            except:
                pass
            try:item['art']['poster'] = self.posterPath + str(details.get('poster_path', ''))
            except:item['art']['poster'] = ''
            try:item['art']['thumb'] = self.posterPath + details.get('poster_path', ' ')
            except:item['art']['thumb'] = ''
            try:
                if details.get('overview', '') is not '':
                    item['info']['plot'] = item['info']['plotoutline'] = details.get('overview', '')
            except:pass
            try:item['info']['aired'] = details.get('air_date', '')
            except:pass
            try:item['info']['premiered'] = details.get('air_date', '')
            except:pass
            try:item['info']['year'] = int(details.get('air_date','0000')[:4])
            except:pass
            try:item['info']['sortseason'] = str(details.get('season_number', ''))
            except:pass
            try:item['info']['season'] = str(details.get('season_number', ''))
            except:pass
            try:item['info']['season_title'] = str(details.get('name', ''))
            except:pass
            try:item['info']['trailer'] = tools.youtube_url % [i for i in details['videos']['results'] if i['site'] == 'YouTube'][0]['key']
            except:pass
            director = None
            for person in details['credits']['crew']:
                if person.get('job') == 'Director':
                    director = person.get('name')

            if not director == None:
                item['info']['director'] = director

            try:
                item['info']['cast'] = [i['name'] for i in details['credits']['cast']]
            except:
                pass

            item['info']['mediatype'] = 'season'
            item['ids'] = seasonObject['ids']
            item['trakt_object'] = {}
            item['trakt_object']['seasons'] = [seasonObject]

        except:
            import traceback
            traceback.print_exc()
            return None

        return item


    def movieToListItem(self, trakt_object):

        try:
            if trakt_object['ids']['tmdb'] is None:
                return None

            url = 'movie/%s?&append_to_response=credits,videos' % str(trakt_object['ids']['tmdb'])
            details = self.get_request(url)
            if details == None:
                tools.log('ERROR TMDB FAILED FOR MOVIEID ' + str(trakt_object['ids']['tmdb']), 'error')
                return None

            item = {'info': None, 'art': None}

            # Set Art
            art = {}
            try:art['poster'] = self.posterPath + str(details.get('poster_path', ''))
            except:pass
            try:art['thumb'] = self.thumbPath + str(details.get('backdrop_path', ''))
            except: pass
            try: art['landscape'] = self.backgroundPath + str(details.get('backdrop_path', ''))
            except: pass
            try: art['fanart'] = self.backgroundPath + str(details.get('backdrop_path', ''))
            except: pass

            # Set Info
            info = {}
            try:
                info['genre'] = []

                if 'genres' in details:
                    for i in details['genres']:
                        info['genre'].append(i.get('name'))
            except: pass

            try:info['rating'] = float(details.get('vote_average'))
            except: pass

            try:info['title'] = details.get('title')
            except: return None

            try:info['year'] = details.get('release_date')[:4]
            except:return None

            try:info['duration'] = details.get('runtime')
            except:pass

            if info['duration'] is not None:
                info['duration'] = int(info['duration']) * 60
            else:
                info['duration'] = 0

            try:info['originaltitle'] = details.get('original_title')
            except:pass

            try:info['tagline'] = details.get('tagline')
            except:pass

            try:info['aired'] = details.get('first_air_date', '')
            except:pass

            try:info['premiered'] = details.get('first_air_date', '')
            except:pass

            try:info['plot'] = details.get('overview')
            except:pass

            try:info['imdbnumber'] = details.get('imdb_id')
            except:pass

            try:info['trailer'] = tools.youtube_url % [i for i in details['videos']['results'] if i['site'] == 'YouTube'][0]['key']
            except:pass

            try:info['castandrole'] = [(i['name'],i['character']) for i in details['credits']['cast']]
            except:pass

            info['mediatype'] = 'movie'
            info['mpaa'] = ''

            # Set Crew/Cast Info
            director = None
            for person in details['credits']['crew']:
                if person.get('job') == 'Director':
                    director = person.get('name')

            if not director == None:
                info['director'] = director

            try:info['cast'] = [i['name'] for i in details['credits']['cast']]
            except:pass

            item['ids'] = trakt_object['ids']
            item['info'] = info
            item['art'] = art
            item['trakt_object'] = {}
            item['trakt_object']['movies'] = [trakt_object]
            return item

        except:
            return None

    def showToListItem(self, traktItem):

        try:
            if traktItem['ids']['tmdb'] is None:
                return None

            url = 'tv/%s?&append_to_response=credits,alternative_titles,videos,content_ratings,images' % traktItem['ids']['tmdb']
            details = self.get_request(url)

            if details.get('status_code') == 34:
                return None

            if details is None:
                return None

            parsed_info = self.parseShowInfo(details, traktItem)
            return parsed_info
        except:
            return None

    def parseShowInfo(self, details, trakt_info):
        try:

            item = {'info': None, 'art': None}

            # Set Art
            art = {}
            try: art['poster'] = self.posterPath + details.get('poster_path', ' ')
            except:pass

            try: art['thumb'] = self.posterPath + details.get('poster_path', ' ')
            except: pass

            try: art['landscape'] = self.backgroundPath + details.get('backdrop_path', ' ')
            except: pass

            try: art['fanart'] = self.backgroundPath + details.get('backdrop_path', ' ')
            except: pass

            art['banner'] = ''

            # Set Info
            info = {}

            try:info['showaliases'] = [alias['title'] for alias in details['alternative_titles']['results']]
            except:pass

            try:info['trailer'] = tools.youtube_url % [i for i in details['videos']['results'] if i['site'] == 'YouTube'][0]['key']
            except:pass

            try:info['genre'] = [str(i['name']) for i in details.get('genres', [])]
            except:pass

            try:info['duration'] = int(details.get('episode_run_time', '')[0]) * 60
            except:pass

            try:info['rating'] = float(details.get('vote_average', float(0.0)))
            except:pass

            try:info['aired'] = details.get('first_air_date', '')
            except:pass

            try:info['premiered'] = details.get('first_air_date', '')
            except:pass

            try:info['year'] = int(details.get('first_air_date', '0000')[:4])
            except:pass

            try:info['status'] = details.get('status', '')
            except:pass

            try:info['tvshowtitle'] = details.get('name')
            except:pass

            try:info['year'] = int(details.get('first_air_date', '')[:4])
            except:pass

            try:info['country'] = details['origin_country'][0]
            except:pass

            try:info['originaltitle'] = details.get('name')
            except:pass

            try:info['plot'] = details.get('overview', '')
            except:pass

            try:info['imdbnumber'] = trakt_info['ids']['imdb']
            except:pass

            info['mediatype'] = 'tvshow'

            try:info['mpaa'] = [i['rating'] for i in details['content_ratings']['results'] if i['iso_3166_1'] == 'US'][0]
            except:pass

            try:info['seasonCount'] = details.get('number_of_seasons', '')
            except:return None

            try:info['tag'] = [i['name'] for i in details['keywords']['results']]
            except:pass

            try:info['castandrole'] = [(i['name'],i['character']) for i in details['credits']['cast']]
            except:pass

            if len(info['showaliases']) == 0:
                info['showaliases'].append('%s %s' % (info['originaltitle'], info['year']))

            try:item['all_fanart'] = [{'image':self.backgroundPath + i['file_path']}
                                      for i in details['images']['backdrops']]
            except:item['all_fanart'] = None

            # Set Crew/Cast Info
            director = None
            for person in details['credits']['crew']:
                if person.get('job') == 'Director':
                    director = person.get('name')

            if not director is None:
                info['director'] = director

            try:info['cast'] = [i['name'] for i in details['credits']['cast']]
            except:pass

            item['ids'] = trakt_info['ids']
            item['info'] = info
            item['art'] = art
            item['trakt_object'] = {}
            item['trakt_object']['shows'] = [trakt_info]

            return item
        except:
            import traceback
            traceback.print_exc()
            return None

    def episodeIDToListItem(self, traktInfo, showArgs):
        try:
            if showArgs['showInfo']['ids']['tmdb'] is None:
                return None

            url = 'tv/%s/season/%s/episode/%s?&append_to_response=credits,videos' % (showArgs['showInfo']['ids']['tmdb'],
                                                  traktInfo['season'],
                                                  traktInfo['number'])
            response = self.get_request(url)

            if response.get('status_code') == 34:
                return None


            parsed_info = self.parseEpisodeInfo(response, traktInfo, showArgs)

            return parsed_info
        except:
            return None

    def parseEpisodeInfo(self, response, traktInfo, showArgs):
        try:
            if "status_code" in response:
                if response["status_code"] == 34: return None

            try:response['name'] = tools.deaccentString(response['name'])
            except: pass
            try:
                currentDate = datetime.today().date()
                airdate = str(response['air_date'])
                airdate = tools.datetime_workaround(airdate)
            except:
                pass
            try:
                if airdate > currentDate:
                    return
            except:
                pass
            item = {'info': None, 'art': None}

            art = {}
            try:art['poster'] = showArgs['seasonInfo']['art']['poster']
            except:art['poster'] = showArgs['showInfo']['art']['poster']
            try:art['thumb'] = self.thumbPath + response.get('still_path', '')
            except:pass
            try:art['landscape'] = showArgs['showInfo']['art']['landscape']
            except:pass
            try:art['fanart'] = showArgs['showInfo']['art']['fanart']
            except:pass

            info = {}

            try:info['trailer'] = tools.youtube_url % [i for i in response['videos']['results'] if i['site'] == 'YouTube'][0]['key']
            except:pass
            try:info['duration'] = showArgs['showInfo']['info'].get('duration')
            except:pass
            try:info['episode'] = response.get('episode_number', '')
            except:pass
            try:info['season'] = response.get('season_number', '')
            except:pass
            try:info['sortepisode'] = response.get('episode_number', '')
            except:pass
            try:info['sortseason'] = response.get('season_number', '')
            except:pass
            try:info['genre'] = showArgs['showInfo']['info']['genre']
            except:pass
            try:info['title'] = info['sorttitle'] = info['originaltitle'] = tools.deaccentString(response['name'])
            except: return None
            try:info['rating'] = response.get('vote_average', '')
            except:pass
            try:info['aired'] = response.get('air_date', '')
            except:
                import traceback
                traceback.print_exc()
                pass
            try:info['premiered'] = response.get('air_date', '')
            except:pass
            try:info['year'] = int(response.get('air_date', '0000')[:4])
            except:pass
            try:info['tvshowtitle'] = showArgs['showInfo']['info']['tvshowtitle']
            except:pass
            try:info['year'] = response.get('firstAired', '')[:4]
            except:pass

            try:info['plot'] = response.get('overview', '')
            except:pass
            try:info['imdbnumber'] = showArgs['showInfo']['ids']['imdb']
            except:pass
            try:info['mediatype'] = 'episode'
            except:pass
            try:info['mpaa'] = showArgs['showInfo']['info']['mpaa']
            except:pass

            try:info['castandrole'] = [(i['name'],i['character']) for i in response['credits']['cast']]
            except:pass

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

