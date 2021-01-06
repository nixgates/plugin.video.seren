# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from functools import wraps

import requests
import xbmcgui
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import ApiBase, handle_single_item_or_list
from resources.lib.modules.globals import g


def fanart_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        try:
            response = func(*args, **kwarg)
            if response.status_code in [200, 201]:
                return response

            g.log('FanartTv returned a {} ({}): while requesting {}'.format(response.status_code,
                                                                            FanartTv.http_codes[response.status_code],
                                                                            response.url), 'error')
            return None
        except requests.exceptions.ConnectionError:
            return None
        except:
            xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30025).format('Fanart'))
            if g.get_global_setting("run.mode") == "test":
                raise
            return None

    return wrapper


def wrap_fanart_object(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        return {'fanart_object': func(*args, **kwarg)}

    return wrapper


class FanartTv(ApiBase):
    base_url = "http://webservice.fanart.tv/v3/"
    api_key = "dfe6380e34f49f9b2b9518184922b49c"
    session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))

    http_codes = {
        200: 'Success',
        404: 'Not Found'
    }
    normalization = [('name', ('title', 'sorttitle'), None),
                     ('tmdb_id', 'tmdb_id', None),
                     ('imdb_id', 'imdb_id', None),
                     ('art', 'art', None)
                     ]

    show_normalization = tools.extend_array([
        ('thetvdb_id', 'tvdb_id', None),
    ], normalization)
    meta_objects = {'movie': normalization,
                    'season': show_normalization,
                    'tvshow': show_normalization}

    def __init__(self):
        self.language = g.get_language_code()
        self.client_key = g.get_setting('fanart.apikey')
        self.fanart_support = False if not self.client_key else True
        self.headers = {'client-key': self.client_key, 'api-key': self.api_key}

        self.meta_hash = tools.md5_hash(
            [self.language, self.fanart_support, self.normalization, self.show_normalization, self.meta_objects,
             self.base_url])

    @staticmethod
    def build_image(url, art, image):
        result = {'url': url,
                  'rating': 5.25 + int(image['likes']) / float(5.0),
                  'size': FanartTv._get_image_size(art),
                  'language': FanartTv._get_image_language(art, image)}
        return result

    @staticmethod
    def _get_image_size(art):
        if art in ('hdtvlogo', 'hdclearart', 'hdmovielogo', 'hdmovieclearart'):
            return 800
        elif art in ('clearlogo', 'clearart', 'movielogo', 'movieart', 'musiclogo'):
            return 400
        elif art in ('tvbanner', 'seasonbanner', 'moviebanner'):
            return 1000
        elif art in ('showbackground', 'moviebackground'):
            return 1920
        elif art in ('tvposter', 'seasonposter', 'movieposter'):
            return 1426
        elif art in ('tvthumb', 'seasonthumb'):
            return 500
        elif art == 'characterart':
            return 512
        elif art == 'moviethumb':
            return 1000
        return 0

    @staticmethod
    def _get_image_language(art, image):
        if 'lang' not in image:
            return None
        return image['lang'] if image['lang'] not in ('', '00') else None

    @fanart_guard_response
    def get(self, url, **params):
        if not self.fanart_support:
            return None
        return self.session.get(tools.urljoin(self.base_url, url), params=params, headers=self.headers, timeout=3)

    def get_json(self, url, **params):
        if not self.fanart_support:
            return None
        response = self.get(url)
        if response is None:
            return None
        try:
            return self._handle_response(response.json(), params.pop('type'), params.pop('season', None))
        except (ValueError, AttributeError):
            g.log('Failed to receive JSON from FanartTv response - response: {}'.format(response), 'error')
            return None

    @wrap_fanart_object
    def get_movie(self, tmdb_id):
        if not self.fanart_support:
            return None
        return self.get_json('movies/{}'.format(tmdb_id), type='movie')

    @wrap_fanart_object
    def get_show(self, tvdb_id):
        if not self.fanart_support:
            return None
        return self.get_json('tv/{}'.format(tvdb_id), type='tvshow')

    @use_cache()
    @wrap_fanart_object
    def get_season(self, tvdb_id, season):
        return self.get_json('tv/{}'.format(tvdb_id), type='season', season=season)

    @handle_single_item_or_list
    def _handle_response(self, response, type, season):
        result = {}
        result.update({'art': self._handle_art(response, type, season)})
        result.update({'info': self._normalize_info(self.meta_objects[type], response)})
        return result

    def _handle_art(self, item, type, season=None):
        meta = {}
        if type == 'movie':
            meta.update(self.create_meta_data(item, 'clearlogo', ['movielogo', 'hdmovielogo']))
            meta.update(self.create_meta_data(item, 'discart', ['moviedisc']))
            meta.update(self.create_meta_data(item, 'clearart', ['movieart', 'hdmovieclearart']))
            meta.update(self.create_meta_data(item, 'characterart', ['characterart']))
            meta.update(self.create_meta_data(item, 'keyart', ['movieposter'],
                                              selector=lambda n, i: self._get_image_language(n, i) is None))
            meta.update(self.create_meta_data(item, 'poster', ['movieposter'],
                                              selector=lambda n, i: self._get_image_language(n, i) is not None))
            meta.update(self.create_meta_data(item, 'fanart', ['moviebackground']))
            meta.update(self.create_meta_data(item, 'banner', ['moviebanner']))
            meta.update(self.create_meta_data(item, 'landscape', ['moviethumb']))
        elif type == 'tvshow':
            meta.update(self.create_meta_data(item, 'clearlogo', ['hdtvlogo', 'clearlogo']))
            meta.update(self.create_meta_data(item, 'clearart', ['hdclearart', 'clearart']))
            meta.update(self.create_meta_data(item, 'characterart', ['characterart']))
            meta.update(self.create_meta_data(item, 'keyart', ['tvposter'],
                                              selector=lambda n, i: self._get_image_language(n, i) is None))
            meta.update(self.create_meta_data(item, 'poster', ['tvposter'],
                                              selector=lambda n, i: self._get_image_language(n, i) is not None))
            meta.update(self.create_meta_data(item, 'fanart', ['showbackground']))
            meta.update(self.create_meta_data(item, 'banner', ['tvbanner']))
            meta.update(self.create_meta_data(item, 'landscape', ['tvthumb']))
        elif type == 'season':
            meta.update(self.create_meta_data(item, 'clearlogo', ['hdtvlogo', 'clearlogo'], season))
            meta.update(self.create_meta_data(item, 'clearart', ['hdclearart', 'clearart'], season))
            meta.update(self.create_meta_data(item, 'characterart', ['characterart'], season))
            meta.update(self.create_meta_data(item, 'landscape', ['seasonthumb'], season))
            meta.update(self.create_meta_data(item, 'banner', ['seasonbanner'], season))
            meta.update(self.create_meta_data(item, 'poster', ['seasonposter'], season,
                                              lambda n, i: self._get_image_language(n, i) is not None))
            meta.update(self.create_meta_data(item, 'keyart', ['seasonposter'], season,
                                              lambda n, i: self._get_image_language(n, i) is None))
            meta.update(self.create_meta_data(item, 'fanart', ['showbackground-season'], season))
        return meta

    def create_meta_data(self, art, dict_name, art_names, season=None, selector=None):
        art_list = []
        for art_item, name in [(art.get(name), name) for name in art_names]:
            if art_item is None:
                continue
            art_list.extend(self.build_image(item['url'], name, item) for item in art_item
                            if (selector is None or selector(name, item)) and (season is None or
                                                                               item.get('season', 'all') == 'all' or
                                                                               int(item.get('season', 0)) == season))
        if len(art_list) > 0:
            return {dict_name: art_list}
        else:
            return {}
