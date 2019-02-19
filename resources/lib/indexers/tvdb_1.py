import requests
import re
import zipfile
from resources.lib.modules import database
from resources.lib.common import tools
import xml.etree.ElementTree as ET

class TVDBAPI:

    def __init__(self, tvdb_id):
        self.base_url = "http://thetvdb.com/api/1D62F2F90030C444/series/%s/all/%s.zip" % (tvdb_id, 'en')
        self.banner_url = "https://www.thetvdb.com/banners/%s"
        self.series_zip = requests.get(self.base_url).content
        try:
            import StringIO
            self.series_zip = zipfile.ZipFile(StringIO.StringIO(self.series_zip))
        except:
            # Python 3 Support
            import io
            self.series_zip = zipfile.ZipFile(io.BytesIO(self.series_zip))

        self.banners = ET.fromstring('\r'.join(self.series_zip.open('banners.xml').readlines())).findall('Banner')
        self.info = ET.fromstring('\r'.join(self.series_zip.open('%s.xml' % 'en').readlines()))
        self.actors = ET.fromstring('\r'.join(self.series_zip.open('actors.xml').readlines())).findall('Actor')

    def build_info(self):
        pass

    def seriesIDToListItem(self, trakt_object):
        try:
            item = {'info': None, 'art': None}
            if self.info == {}:
                return None
            series_info = self.info.find('Series')
            # Set Art
            art = {}
            try:
                art['poster'] = self.banner_url % series_info.find('poster').text
            except:
                pass
            try:
                art['thumb'] = art['poster']
            except:
                pass
            try:
                art['landscape'] = self.banner_url % series_info.find('fanart').text
            except:
                pass
            try:
                art['fanart'] = art['landscape']
            except:
                pass
            try:
                art['banner'] = self.baseImageUrl % series_info.find('banner').text
            except:
                pass

            # Set Info
            info = {}
            try:
                info['showaliases'] = self.info.get('aliases')
            except:
                pass
            try:
                info['genre'] = series_info.find('Genre').text.split('|')
            except:
                pass
            try:
                info['duration'] = int(series_info.find('Runtime').text) * 60
            except:
                pass
            try:
                info['rating'] = float(series_info.find('Rating').text)
            except:
                pass
            try:
                try:
                    info['premiered'] = trakt_object['first_aired'][:10]
                    if len(info['premiered']) < 10:
                        raise Exception
                except:
                    info['premiered'] = series_info.find('FirstAired').text
            except:
                pass
            try:
                info['status'] = series_info.find('Status').text
            except:
                pass
            try:
                info['tvshowtitle'] = series_info.find('SeriesName').text
            except:
                pass
            try:
                info['year'] = info['premiered'][:4]
            except:
                info['year'] = 0
                pass
            try:
                info['studio'] = series_info.find('Network').text
            except:
                pass
            try:
                info['originaltitle'] = info['tvshowtitle']
            except:
                pass
            try:
                info['plot'] = series_info.find('Overview').text
            except:
                pass
            try:
                info['imdbnumber'] = series_info.find('IMDB_ID').text
            except:
                pass
            try:
                info['trailer'] = tools.youtube_url % trakt_object['trailer'].split('v=')[1]
            except:
                pass
            try:
                info['castandrole'] = [(i.find('Name').text, i.find('Role').text) for i in self.actors]
            except:
                pass
            try:
                if '0' in self.episode_summary['airedSeasons']:
                    self.episode_summary['airedSeasons'].pop(0)
                info['seasonCount'] = len(self.episode_summary['airedSeasons'])
            except:
                info['seasonCount'] = 0
                pass

            try:
                info['episodeCount'] = trakt_object['aired_episodes']
            except:
                info['episodeCount'] = 0
                pass

            try:
                info['mediatype'] = 'tvshow'
            except:
                pass
            try:
                info['mpaa'] = series_info.find('ContentRating').text
            except:
                pass
            try:
                info['country'] = trakt_object.get('country', '').upper()
            except:
                info['country'] = ''
                pass

            requirements = ['country', 'tvshowtitle', 'year', 'seasonCount']
            for i in requirements:
                if i not in info:
                    return None

            item['ids'] = trakt_object['ids']
            item['info'] = info
            item['art'] = art
            item['setCast'] = [{"name": i.find('Name').text, "thumbnail": self.banner_url % i.find('Image').text,
                                "role": i.find('Role').text, 'order': i.find('SortOrder').text} for i in self.actors]
            item['trakt_object'] = {}
            item['trakt_object']['shows'] = [trakt_object]

            return item

        except:
            return None
