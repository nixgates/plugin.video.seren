import requests, re
from bs4 import BeautifulSoup
from resources.lib.common import tools

class scraper:

    def __init__(self):
        self.base_url = 'https://www.imdb.com/'
        self.title_url = 'title/%s'
        self.cast_url = '/fullcredits'
        self.fanart_url = '/mediaindex?refine=publicity'
        self.trailer_url = 0

    def trakt_movie_to_list_item(self, trakt_object):
        response = requests.get(self.base_url + self.title_url % trakt_object['ids']['imdb'])
        details = BeautifulSoup(response.text, 'html.parser')

        item = {'info': None, 'art': None}

        # Set Info
        info = {}
        try:
            info['genre'] = []
        except:
            pass

        try:
            info['rating'] = float(details.find('div', {'class': 'ratingValue'}).find('span').text)
        except:
            pass

        try:
            title = details.find('div', {'class': 'title_wrapper'}).find('h1').text
            title = tools.unquote(title).split('(')[0]
            info['title'] = info['originaltitle'] = title.encode('utf-8')
        except:
            return None

        try:
            duration = details.find('div', {'class': 'subtext'}).text
            duration = duration.split('|')[1].strip(' ')
            if 'h' in duration:
                duration = duration.split('h')
                duration[0] = int(duration[0].strip('h')) * 60
                duration[1] = re.findall(r'\d\d', duration[1])[0]
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
            info['tagline'] = tag.encode('utf-8')
        except:
            pass

        try:
            aired = details.find('div', {'class': 'subtext'}).find_all('a')[2].text
            aired = aired.split('(')[0]
            aired = aired.split(' ')
            aired[0] = aired[0].zfill(2)
            aired = tools.datetime_workaround('%s %s %s' % (aired[0], aired[1], aired[2]), '%d %B %Y')
            info['aired'] = info['premiered'] = aired.strftime('%Y-%m-%d')
            info['year'] = aired.strftime('%Y')
        except:
            pass

        try:
            info['plot'] = details.find('div', {'id': 'titleStoryLine'}).find_all('span')[1].text
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
            info['castandrole'] = [()]
        except:
            pass

        #Begin Scraping Artwork
        art = {}

        try:
            art['poster'] = details.find('div', {'class': 'poster'}).find('img')['src']
        except:
            pass

        try:
            art['fanart'] = ''
        except:
            pass


        info['mediatype'] = 'movie'
        info['mpaa'] = ''

        # Set Crew/Cast Info
        # director = None
        # for person in details['credits']['crew']:
        #     if person.get('job') == 'Director':
        #         director = person.get('name')
        #
        # if not director == None:
        #     info['director'] = director
        #
        # try:
        #     info['cast'] = [i['name'] for i in details['credits']['cast']]
        # except:
        #     pass

        item['ids'] = trakt_object['ids']
        item['info'] = info
        item['art'] = art
        item['trakt_object'] = {}
        item['trakt_object']['movies'] = [trakt_object]

        return item
