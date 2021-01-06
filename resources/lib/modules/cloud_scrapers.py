# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.common import source_utils
from resources.lib.debrid.all_debrid import AllDebrid
from resources.lib.debrid.premiumize import Premiumize
from resources.lib.debrid.real_debrid import RealDebrid
from resources.lib.indexers.apibase import ApiBase
from resources.lib.modules.globals import g


class CloudScraper(ApiBase, object):

    def __init__(self, terminate_check):
        self.terminate_check = terminate_check
        self.api_adapter = None
        self.language = 'en'
        self.media_type = ''
        self.item_information = {}
        self.simple_show_info = None
        self.debrid_provider = ''
        self.episode_regex = None
        self.season_regex = None
        self.show_regex = None
        self._source_normalization = ()
        self._file_normalization = ()

    def _build_regex(self):
        self.episode_regex = source_utils.get_filter_single_episode_fn(self.simple_show_info)
        self.show_regex = source_utils.get_filter_show_pack_fn(self.simple_show_info)
        self.season_regex = source_utils.get_filter_season_pack_fn(self.simple_show_info)

    def _generate_regex(self):
        self.regex = source_utils.get_filter_single_episode_fn(self.simple_show_info)

    def get_sources(self, item_information, simple_show_info=None):

        if not self._is_enabled():
            return []
        self.item_information = item_information
        self.media_type = self.item_information['info']['mediatype']

        if simple_show_info is not None:
            self.simple_show_info = simple_show_info
            self._build_regex()

        cloud_items = self._fetch_cloud_items()

        if type(cloud_items) != list:
            g.log('There was a faliure at the API level getting the cloud files from {}'.format(self.debrid_provider),
                  'error')
            return []

        cloud_items = [self._normalize_item(i) for i in cloud_items if not self.terminate_check()]
        cloud_items = [i for i in cloud_items if self._is_valid_pack(i) if not self.terminate_check()]
        cloud_items = self._identify_items(cloud_items)
        cloud_items = [self._source_to_file(i) for i in cloud_items if not self.terminate_check()]
        cloud_items = [i for i in cloud_items if i]
        cloud_items = self._apply_general_filter(cloud_items)
        cloud_items = self._finalise_identified_items(cloud_items)
        g.log('{} cloud scraper found {} source'.format(self.debrid_provider, len(cloud_items)), 'info')
        return cloud_items

    def _normalize_item(self, item):
        return self._normalize_info(self._source_normalization, item)

    @staticmethod
    def _apply_general_filter(cloud_items):
        return [i for i in cloud_items if any(i['release_title'].endswith(ext) for ext in g.common_video_extensions)]

    def _identify_items(self, cloud_items):
        sources = []

        if self.media_type == 'episode':
            for item in cloud_items:
                release_title = source_utils.clean_title(item["release_title"])
                if self.episode_regex(release_title) or \
                        self.show_regex(release_title) or \
                        self.season_regex(release_title):
                    sources.append(item)

        else:
            simple_info = {'year': self.item_information.get('info', {}).get('year'),
                           'title': self.item_information.get('info').get('title')}
            for item in cloud_items:
                if source_utils.filter_movie_title(None, source_utils.clean_title(item['release_title']),
                                                   self.item_information['info']['title'],
                                                   simple_info):
                    sources.append(item)

            return sources

        return sources

    def _source_to_file(self, source):
        return source

    def _fetch_cloud_items(self):
        """
        Calls the api adapter and returns the api response
        :return:
        """
        return []

    def _finalise_identified_items(self, items):
        for item in items:
            item.update({
                'quality': source_utils.get_quality(item['release_title']),
                'language': self.language,
                'provider': 'Cloud',
                'type': 'cloud',
                'info': source_utils.get_info(item['release_title']),
                'debrid_provider': self.debrid_provider,
            })

        return items

    @staticmethod
    def _get_clean_title(item):
        return source_utils.clean_title(item.get('release_title', ''))

    def _is_valid_pack(self, item):
        clean_title = self._get_clean_title(item)
        if self.media_type == 'episode':
            if self.episode_regex(clean_title) or self.season_regex(clean_title) or self.show_regex(clean_title):
                return True
            else:
                return False
        else:
            # Always return true on a movie item as packs do not count
            return True

    def _is_enabled(self):
        return False


class PremiumizeCloudScaper(CloudScraper, ApiBase):

    def __init__(self, terminate_flag):
        super(PremiumizeCloudScaper, self).__init__(terminate_flag)
        self.api_adapter = Premiumize()
        self.debrid_provider = 'premiumize'
        self._source_normalization = (
            ('name', 'release_title', None),
            ('id', 'url', None),
            ('size', 'size', lambda k: (int(k) / 1024) / 1024)
        )

    def _fetch_cloud_items(self):
        return source_utils.filter_files_for_resolving(self.api_adapter.list_folder_all(), self.item_information)

    def _is_valid_pack(self, item):
        return True

    def _is_enabled(self):
        return g.premiumize_enabled()


class RealDebridCloudScraper(CloudScraper):

    def __init__(self, terminate_flag):
        super(RealDebridCloudScraper, self).__init__(terminate_flag)
        self.api_adapter = RealDebrid()
        self.debrid_provider = 'real_debrid'
        self._source_normalization = (
            ('path', 'release_title', lambda k: k.lower().split('/')[-1]),
            ('bytes', 'size', lambda k: (k / 1024) / 1024),
            ('size', 'size', None),
            ('filename', 'release_title', None),
            ('id', 'id', None),
            ('links', 'links', None),
            ('selected', 'selected', None)
        )

    def _fetch_cloud_items(self):
        return self.api_adapter.list_torrents()

    def _source_to_file(self, source):
        if "links" not in source:
            return None
        source_files = self._normalize_item(self.api_adapter.torrent_info(source['id'])['files'])
        source_files = [i for i in source_files if i["selected"]]
        [file.update({'idx': idx}) for idx, file in enumerate(source_files)]
        source_files = self._identify_items(source_files)
        [file.update({'url': source['links'][file['idx']]}) for file in source_files]
        return source_files[0] if source_files else None

    def _is_enabled(self):
        return g.real_debrid_enabled()

class AllDebridCloudScraper(CloudScraper):

    def __init__(self, terminate_flag):
        super(AllDebridCloudScraper, self).__init__(terminate_flag)
        self.api_adapter = AllDebrid()
        self.debrid_provider = 'all_debrid'
        self._source_normalization = (
            ("size", "size", lambda k: (k / 1024) / 1024),
            ("filename", ["release_title", "path"], None),
            ("id", "id", None),
            ("link", ["link", "url"], None),
        )

    def _fetch_cloud_items(self):
        magnets = [m for m in self.api_adapter.saved_magnets() if m['status'] == 'Ready']
        return [i for link_list in magnets for i in link_list['links']] + self.api_adapter.saved_links()['links']

    def _is_valid_pack(self, item):
        return True

    def _is_enabled(self):
        return g.all_debrid_enabled()