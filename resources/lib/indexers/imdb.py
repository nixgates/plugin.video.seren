# -*- coding: utf-8 -*-

import re
import threading
import traceback

import requests
from bs4 import BeautifulSoup, SoupStrainer

from resources.lib.common import tools
from resources.lib.indexers import fanarttv

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


class IMDBScraper:
    def __init__(self):
        self.base_url = 'https://www.imdb.com/'
        self.title_url = 'title/%s'
        self.season_url = '{}/episodes?season=%s'.format(self.title_url)
        self.fanart_url = '{}/mediaindex?refine=publicity'.format(self.title_url)
        self.trailer_url = 0
        self.art = {}
        self.info = {}
        self.episode_summary = {}
        self.cast = []
        if tools.fanart_api_key == '':
            self.fanart_support = False
        else:
            self.fanart_support = True
        self.threads = []

    def _amazon_image_enlarger(self, url):
        if url is not None and 'm.media-amazon.com' in url:
            try:
                splittend_url = url.split("@.")
                media_info = splittend_url[1].split('_')
                dymensions = media_info[3].split(',')

                if dymensions[3] in media_info[2]:
                    media_info[2] = media_info[2].replace(dymensions[3], str(int(dymensions[3]) * 10))
                else:
                    media_info[2] = media_info[2].replace(dymensions[2], str(int(dymensions[2]) * 10))
                dymensions[3] = str(int(dymensions[3]) * 10)
                dymensions[2] = str(int(dymensions[2]) * 10)
                media_info[3] = ','.join(dymensions)
                splittend_url[1] = '_'.join(media_info)
                return "@.".join(splittend_url)
            except:
                return url
        else:
            return url
        pass

    def showToListItem(self, trakt_object):
        response = requests.get(self.base_url + self.title_url % trakt_object['ids']['imdb'])
        details = BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer('div', {'id': 'pagecontent'}))

        tvdbID = trakt_object['ids']['tvdb']
        if self.fanart_support:
            self.threads.append(threading.Thread(target=self.getFanartTVShow, args=(tvdbID,)))

        [i.start() for i in self.threads]
        [i.join() for i in self.threads]

        item = {'info': None, 'art': None}

        # Set Info
        info = {}
        title_wrapper = details.find('div', {'class': 'title_wrapper'})
        try:
            info['genre'] = [genre.text for genre in title_wrapper.find_all('a', href=True)
                             if 'title?genres=' in genre['href']]
        except:
            pass

        try:
            info['rating'] = float(details.find('div', {'class': 'ratingValue'}).find('span').text)
        except:
            pass

        try:
            info['mpaa'] = trakt_object['certification']
        except:
            pass

        try:
            info['studio'] = trakt_object['network']
        except:
            pass

        try:
            info['tvshowtitle'] = info['originaltitle'] = title_wrapper.find('h1').text.strip()
        except:
            pass

        try:
            duration = details.find('div', {'class': 'subtext'}).find('time').text.strip()
            if 'h' in duration:
                duration = duration.split('h')
                duration[0] = int(duration[0].strip('h')) * 60
                duration[1] = re.findall(r'\d{1,2}', duration[1])[0]
                duration[1] = int(duration[1])
                duration = duration[0] + duration[1]
            else:
                duration = int(duration.strip('min'))
            info['duration'] = duration
        except:
            pass

        title_details = details.find('div', {'id': 'titleDetails'})
        try:
            aired = title_details.find_all('div', {'class': 'txt-block'})[3].text
            aired = aired.split(':')[1]
            aired = aired.split('(')[0].strip()
            aired = aired.split(' ')
            aired[0] = aired[0].zfill(2)
            aired = tools.datetime_workaround('%s %s %s' % (aired[0], aired[1], aired[2]), '%d %B %Y')
            info['premiered'] = trakt_object['first_aired']
            info['year'] = aired.strftime('%Y')
        except:
            pass

        try:
            info['showaliases'] = [title_details.find_all('div', {'class': 'txt-block'})[4].contents[2].strip()]
        except:
            pass

        try:
            info['country'] = \
                title_details.find_all('div', {'class': 'txt-block'})[1].contents[3]['href'].strip().split('=')[
                    1].upper()
        except:
            pass

        try:
            info['plot'] = details.find('div', {'id': 'titleStoryLine'}).find_all('span')[1].text.strip()
        except:
            pass

        try:
            info['imdbnumber'] = trakt_object['ids']['imdb']
        except:
            pass

        try:
            info['trailer'] = tools.youtube_url % trakt_object['trailer'].split('v=')[1]
        except:
            pass

        # Set Crew/Cast Info
        try:
            crew_table = details.find('table', {'class': 'cast_list'})
            rows = crew_table.find_all('tr')
            self.cast = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) > 1:
                    self.cast.append({'name': cells[1].find('a').text.encode('utf-8').strip(),
                                      'role': cells[3].find('a').text.encode('utf-8').strip(),
                                      'thumbnail': self._amazon_image_enlarger(
                                          cells[0].find('img', src=True).get('loadlate'))})
        except:
            pass
        try:
            info['episode_count'] = re.findall(r'(\d{1,3})', details.find('span', {'class': 'bp_sub_heading'}).text)[0]
        except:
            info['episode_count'] = 0
            pass

        try:
            info['status'] = trakt_object['status']
        except:
            pass

        try:
            season_urls = [i['href'] for i in
                           details.find('div', {'class': 'seasons-and-year-nav'})
                               .find_all('a', href=True) if 'episodes?season' in i['href']]

            info['season_count'] = len(season_urls)
        except:
            traceback.print_exc()
            info['season_count'] = 0
            pass

        # Begin Scraping Artwork
        if 'poster' not in self.art:
            self.art['poster'] = self._amazon_image_enlarger(details.find('div', {'class': 'poster'})
                                                             .find('img')['src'])
        if 'fanart' not in self.art:
            self.art['fanart'] = self._amazon_image_enlarger(details.find('div', {'class': 'mediastrip'})
                                                             .find('img', src=True).get('loadlate'))

        requirements = ['country', 'tvshowtitle', 'year', 'season_count']
        for i in requirements:
            if i not in info:
                return None

        info['mediatype'] = 'tvshow'
        item['ids'] = trakt_object['ids']
        item['info'] = info
        item['art'] = self.art
        item['cast'] = self.cast
        item['trakt_object'] = {}
        item['trakt_object']['shows'] = [trakt_object]

        item['art']['thumb'] = item['art'].get('poster', '')

        return item

    def showSeasonToListItem(self, trakt_object, show_meta):
        try:
            item = {'info': show_meta['info'], 'art': show_meta['art']}
            season = trakt_object['number']

            response = requests.get(
                self.base_url + self.season_url % (show_meta['ids']['imdb'], trakt_object['season']))
            details = BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer('div', {'id': 'pagecontent'}))

            if details is None:
                return None
            try:
                item['info']['studio'] = show_meta['info'].get('studio')
            except:
                pass
            try:
                item['art']['poster'] = item['art']['thumb'] = self.art.get('poster', '')
                if item['art']['poster'] == '' or item['art']['poster'] is None:
                    item['art']['poster'] = item['art']['thumb'] = show_meta['art']['poster']
            except:
                item['art']['poster'] = item['art']['thumb'] = ''

            try:
                episode = details.find('div', {'class': 'list detail eplist'}).find_all('div', recursive=False)[0]
                aired = episode.find('div', {'class': 'airdate'}).text.strip()
                aired = aired.split(' ')
                aired[0] = aired[0].zfill(2)
                aired = tools.datetime_workaround('%s %s %s' % (aired[0], aired[1].rstrip('.'), aired[2]), '%d %b %Y')
                item['info']['aired'] = aired
                item['year'] = aired[:4]
            except:
                pass
            try:
                item['info']['episode_count'] = trakt_object['episode_count']
            except:
                item['info']['episode_count'] = 0
                pass
            try:
                item['info']['aired_episodes'] = trakt_object['aired_episodes']
            except:
                item['info']['aired_episodes'] = 0
                pass
            try:
                item['info']['premiered'] = trakt_object['first_aired']
            except:
                pass
            try:
                item['info']['plot'] = item['info']['overview'] = trakt_object['overview']
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
                item['info']['season_title'] = trakt_object['title']
            except:
                pass

            if item['info']['season_title'] == '':
                import traceback
                traceback.print_exc()
                return None

            item['info']['mediatype'] = 'season'
            item['ids'] = trakt_object['ids']
            item['trakt_object'] = {}
            item['trakt_object']['seasons'] = [trakt_object]
            item['showInfo'] = show_meta

            item['art']['thumb'] = item['art'].get('poster', '')

        except:
            import traceback
            traceback.print_exc()
            return None

        return item

    def episodeIDToListItem(self, trakt_object, show_meta):
        response = requests.get(
            self.base_url + self.season_url % (show_meta['showInfo']['ids']['imdb'], trakt_object['season']))
        details = BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer('div', {'id': 'pagecontent'}))

        item = {'info': None, 'art': None}

        art = {}

        info = {}

        try:
            info['episode'] = info['sortepisode'] = int(trakt_object['number'])
            episode = details.find('div', {'class': 'list detail eplist'}).find_all('div', recursive=False)[
                int(trakt_object['number']) - 1]
        except:
            return

        try:
            info['season'] = info['sortseason'] = trakt_object['season']
        except:
            pass
        try:
            info['title'] = info['originaltitle'] = tools.unquote(episode.find('a', {'itemprop': 'name'}).text.strip())
            if info['title'] is None:
                return None
        except:
            pass
        try:
            info['rating'] = float(episode.find('span', {'class': 'ipl-rating-star__rating'}).text.strip())
        except:
            pass

        try:
            info['premiered'] = trakt_object['first_aired']
        except:
            info['premiered'] = ''

        try:
            aired = episode.find('div', {'class': 'airdate'}).text.strip()
            aired = aired.split(' ')
            aired[0] = aired[0].zfill(2)
            aired = tools.datetime_workaround('%s %s %s' % (aired[0], aired[1].rstrip('.'), aired[2]), '%d %b %Y')
            info['aired'] = aired.strftime('%Y-%m-%d')
        except:
            info['aired'] = ''
            pass

        try:
            info['year'] = trakt_object['aired'][:4]
        except:
            pass
        try:
            info['plot'] = episode.find('div', {'itemprop': 'description'}).text.strip()
        except:
            pass
        try:
            info['imdbnumber'] = episode.find('div', {'class': 'wtw-option-standalone'})['data-tconst']
        except:
            pass
        try:
            info['studio'] = show_meta['showInfo']['info'].get('studio')
        except:
            pass
        try:
            info['mpaa'] = show_meta['showInfo']['info'].get('mpaa')
        except:
            pass
        try:
            art = show_meta['showInfo']['art']
        except:
            pass

        try:
            art['thumb'] = self._amazon_image_enlarger(episode.find('img', src=True)['src'].strip())
        except:
            art['thumb'] = art['fanart']
            pass
        try:
            info['tvshowtitle'] = show_meta['showInfo']['info']['tvshowtitle']
        except:
            pass
        try:
            info['genre'] = show_meta['showInfo']['info']['genre']
        except:
            pass
        try:
            info['duration'] = show_meta['showInfo']['info']['duration']
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
        item['cast'] = show_meta['showInfo'].get('cast', [])
        item['trakt_object'] = {}
        item['trakt_object']['episodes'] = [trakt_object]
        item['showInfo'] = show_meta['showInfo']

        requirements = ['title', 'season', 'episode']
        for i in requirements:
            if info.get(i, None) is None:
                return None
            if i not in info:
                return None
        return item
        pass

    def movieToListItem(self, trakt_object):
        try:
            response = requests.get(self.base_url + self.title_url % trakt_object['ids']['imdb'])
            details = BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer('div', {'id': 'pagecontent'}))

            item = {'info': None, 'art': None}

            imdbID = trakt_object['ids']['imdb']
            if self.fanart_support:
                self.threads.append(threading.Thread(target=self.getFanartTVMovie, args=(imdbID,)))

            # Set Info
            info = {}
            title_wrapper = details.find('div', {'class': 'title_wrapper'})
            try:
                info['genre'] = [genre.text for genre in title_wrapper.find_all('a', href=True)
                                 if 'title?genres=' in genre['href']]
            except:
                pass

            try:
                info['rating'] = float(details.find('div', {'class': 'ratingValue'}).find('span').text)
            except:
                pass

            try:
                title = title_wrapper.find('h1').text
                title = tools.unquote(title).split('(')[0]
                info['title'] = info['originaltitle'] = title.strip()
            except:
                return None

            try:
                duration = details.find('div', {'class': 'subtext'}).find('time').text.strip()
                if 'h' in duration:
                    duration = duration.split('h')
                    duration[0] = int(duration[0].strip('h')) * 60
                    duration[1] = re.findall(r'\d{1,2}', duration[1])[0]
                    duration[1] = int(duration[1])
                    duration = duration[0] + duration[1]
                else:
                    duration = int(duration.strip('min'))
                info['duration'] = duration
            except:
                pass

            try:
                tag = details.find('div', {'id': 'titleStoryLine'}).find('div', {'class': 'txt-block'}).text
                tag = tag.split('\n')[2]
                info['tagline'] = tag.strip()
            except:
                pass

            title_details = details.find('div', {'id': 'titleDetails'})
            try:
                aired = title_details.find_all('div', {'class': 'txt-block'})[3].text
                aired = aired.split(':')[1]
                aired = aired.split('(')[0].strip()
                aired = aired.split(' ')
                aired[0] = aired[0].zfill(2)
                aired = tools.datetime_workaround('%s %s %s' % (aired[0], aired[1], aired[2]), '%d %B %Y')
                info['premiered'] = aired.strftime('%Y-%m-%d')
                info['year'] = aired.strftime('%Y')
            except:
                pass
            try:
                info['aliases'] = [title_details.find_all('div', {'class': 'txt-block'})[4].contents[2].strip()]
            except:
                pass

            try:
                info['country'] = title_details.find_all('div', {'class': 'txt-block'})[1].contents[3]['href'].strip() \
                    .split('=')[1].upper()
            except:
                pass
            try:
                info['plot'] = details.find('div', {'id': 'titleStoryLine'}).find_all('span')[1].text.strip()
            except:
                pass

            try:
                info['imdbnumber'] = trakt_object['ids']['imdb']
            except:
                pass

            try:
                info['trailer'] = tools.youtube_url % trakt_object['trailer'].split('v=')[1]
            except:
                pass

            try:
                info['mpaa'] = trakt_object['certification']
            except:
                pass

            # Set Crew/Cast Info
            try:
                crew_table = details.find('table', {'class': 'cast_list'})
                rows = crew_table.find_all('tr')
                self.cast = []
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) > 1:
                        self.cast.append({'mame': cells[1].find('a').text.encode('utf-8').strip(),
                                          'role': cells[3].find('a').text.encode('utf-8').strip(),
                                          'thumbnail': self._amazon_image_enlarger(
                                              cells[0].find('img', src=True).get('loadlate'))})
            except:
                pass

            # Begin Scraping Artwork
            if 'poster' not in self.art:
                self.art['poster'] = self._amazon_image_enlarger(
                    details.find('div', {'class': 'poster'}).find('img')['src'])
            if 'fanart' not in self.art:
                self.art['fanart'] = self._amazon_image_enlarger(details.find('div', {'class': 'mediastrip'})
                                                                 .find('img', src=True).get('loadlate'))

            info['mediatype'] = 'movie'
            info['mpaa'] = ''

            item['ids'] = trakt_object['ids']
            item['info'] = info
            item['art'] = self.art
            item['cast'] = self.cast
            item['trakt_object'] = {}
            item['trakt_object']['movies'] = [trakt_object]

            return item

        except:
            import traceback
            traceback.print_exc()
            return None

    def getFanartTVShow(self, tvdb_id):
        try:
            artwork = fanarttv.get(tvdb_id, 'tv')
            self.art.update(artwork)
        except:
            pass

    def getFanartTVMovie(self, imdb_id):
        try:
            artwork = fanarttv.get(imdb_id, 'movie')
            self.art.update(artwork)
        except:
            pass
