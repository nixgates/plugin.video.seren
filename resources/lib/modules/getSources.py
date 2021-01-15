# -*- coding: utf-8 -*-
"""
Handling of scraping and cache checking for sources
"""
from __future__ import absolute_import, division, unicode_literals

import copy
import importlib
import json
import random
import re
import sys
import time
from collections import OrderedDict

import requests
import xbmc
import xbmcgui

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database.skinManager import SkinManager
from resources.lib.database.torrentCache import TorrentCache
from resources.lib.debrid import all_debrid
from resources.lib.debrid import premiumize
from resources.lib.debrid import real_debrid
from resources.lib.gui.windows.get_sources_window import GetSourcesWindow
from resources.lib.gui.windows.manual_caching import ManualCacheWindow
from resources.lib.modules import monkey_requests
from resources.lib.modules import resolver as resolver
from resources.lib.modules.cloud_scrapers import PremiumizeCloudScaper, RealDebridCloudScraper, AllDebridCloudScraper
from resources.lib.modules.globals import g
from resources.lib.modules.source_sorter import SourceSorter

try:
    from importlib import reload as reload_module  # pylint: disable=no-name-in-module
except ImportError:
    # Invalid version of importlib
    from imp import reload as reload_module

approved_qualities = ['4K', '1080p', '720p', 'SD']


class Sources(object):
    """
    Handles fetching and processing of available sources for provided meta data
    """

    def __init__(self, item_information):
        self.hash_regex = re.compile(r'btih:(.*?)(?:&|$)')
        self.canceled = False
        self.torrent_cache = TorrentCache()
        self.torrent_threads = ThreadPool(workers=30)
        self.hoster_threads = ThreadPool(workers=30)
        self.adaptive_threads = ThreadPool(workers=30)
        self.item_information = item_information
        self.media_type = self.item_information['info']['mediatype']
        self.torrent_providers = []
        self.hoster_providers = []
        self.adaptive_providers = []
        self.running_providers = []
        self.language = 'en'
        self.sources_information = {
            "adaptiveSources": [],
            "torrentCacheSources": {},
            "hosterSources": {},
            "cloudFiles": [],
            "remainingProviders": [],
            "allTorrents": {},
            "torrents_quality": [0, 0, 0, 0],
            "hosters_quality": [0, 0, 0, 0],
            "cached_hashes": []
        }

        self.hoster_domains = {}
        self.progress = 1
        self.runtime = 0
        self.host_domains = []
        self.host_names = []
        self.timeout = g.get_int_setting('general.timeout')
        self.window = SourceWindowAdapter(self.item_information, self)
        self.session = requests.Session()

        self.silent = g.get_bool_setting('general.tempSilent')

    def get_sources(self):
        """
        Main endpoint to initiate scraping process
        :return: Returns (uncached_sources, sorted playable sources, items metadata)
        :rtype: tuple
        """
        try:
            g.log('Starting Scraping', 'debug')
            g.log("Timeout: {}".format(self.timeout), 'debug')
            g.log("Pre-term-enabled: {}".format(g.get_setting("preem.enabled")), 'debug')
            g.log("Pre-term-limit: {}".format(g.get_setting("preem.limit")), 'debug')
            g.log("Pre-term-movie-res: {}".format(g.get_setting("preem.movieres")), 'debug')
            g.log("Pre-term-show-res: {}".format(g.get_setting("preem.tvres")), 'debug')
            g.log("Pre-term-type: {}".format(g.get_setting("preem.type")), 'debug')
            g.log("Pre-term-cloud-files: {}".format(g.get_setting("preem.cloudfiles")), 'debug')
            g.log("Pre-term-adaptive-files: {}".format(g.get_setting("preem.adaptiveSources")), 'debug')

            self._handle_pre_scrape_modifiers()
            self._get_imdb_info()

            self._check_local_torrent_database()

            self._update_progress()
            if self._prem_terminate():
                return self._finalise_results()

            self._init_providers()

            # Add the users cloud inspection to the threads to be run
            self.torrent_threads.put(self._user_cloud_inspection)

            # Load threads for all sources
            self._create_torrent_threads()
            self._create_hoster_threads()
            self._create_adaptive_threads()

            self.window.create()
            self.window.set_text(g.get_language_string(30055), self.progress, self.sources_information, self.runtime)
            self.window.set_property('process_started', 'true')

            # Keep alive for gui display and threading
            g.log('Entering Keep Alive', 'info')
            start_time = time.time()

            while self.progress < 100 and not g.abort_requested():
                g.log('Remaining Providers {}'.format(self.sources_information["remainingProviders"]))
                if self._prem_terminate() is True or (len(self.sources_information["remainingProviders"]) == 0
                                                      and self.runtime > 5):
                    # Give some time for scrapers to initiate
                    break

                if self.canceled:
                    monkey_requests.PRE_TERM_BLOCK = True
                    break

                self._update_progress()

                try:
                    self.window.set_text("4K: {} | 1080: {} | 720: {} | SD: {}".format(
                        g.color_string(self.sources_information["torrents_quality"][0] +
                                       self.sources_information["hosters_quality"][0]),
                        g.color_string(self.sources_information["torrents_quality"][1] +
                                       self.sources_information["hosters_quality"][1]),
                        g.color_string(self.sources_information["torrents_quality"][2] +
                                       self.sources_information["hosters_quality"][2]),
                        g.color_string(self.sources_information["torrents_quality"][3] +
                                       self.sources_information["hosters_quality"][3]),
                    ), self.progress, self.sources_information, self.runtime)

                except (KeyError, IndexError) as e:
                    g.log('Failed to set window text, {}'.format(e), 'error')

                # Update Progress
                xbmc.sleep(200)
                self.runtime = time.time() - start_time
                self.progress = int(100 - float(1 - (self.runtime / float(self.timeout))) * 100)

            g.log('Exited Keep Alive', 'info')

            return self._finalise_results()

        finally:
            self.window.close()

    def _handle_pre_scrape_modifiers(self):
        """
        Detects preScrape, disables pre-termination and sets timeout to maximum value
        :return:
        :rtype:
        """
        if g.REQUEST_PARAMS.get('action', '') == "preScrape":
            self.silent = True
            self.timeout = 60
            self._prem_terminate = lambda: False  # pylint: disable=method-hidden

    def _create_hoster_threads(self):
        if self._hosters_enabled():
            random.shuffle(self.hoster_providers)
            for i in self.hoster_providers:
                self.hoster_threads.put(self._get_hosters, self.item_information, i)

    def _create_torrent_threads(self):
        if self._torrents_enabled():
            random.shuffle(self.torrent_providers)
            for i in self.torrent_providers:
                self.torrent_threads.put(self._get_torrent, self.item_information, i)

    def _create_adaptive_threads(self):
        for i in self.adaptive_providers:
            self.adaptive_threads.put(self._get_adaptive_sources, self.item_information, i)

    def _check_local_torrent_database(self):
        if g.get_bool_setting('general.torrentCache'):
            self.window.set_text(g.get_language_string(30054), self.progress, self.sources_information, self.runtime)
            self._get_local_torrent_results()

    def _is_playable_source(self):
        source_types = ['cloudFiles', 'adaptiveSources', 'hosterSources', 'torrentCacheSources']
        all_sources = [k for i in [self.sources_information[stype] for stype in source_types] for k in i]
        return False if not len(all_sources) else True

    def _finalise_results(self):
        monkey_requests.allow_provider_requests = False
        self._send_provider_stop_event()

        self._debrid_hoster_duplicates()
        uncached = [i for i in self.sources_information["allTorrents"].values()
                    if i['hash'] not in self.sources_information['cached_hashes']]

        if not self._is_playable_source():
            self._build_cache_assist()
            g.cancel_playback()
            if self.silent:
                g.notification(g.ADDON_NAME, g.get_language_string(30056))
            return uncached, [], self.item_information

        sorted_sources = SourceSorter(self.media_type).sort_sources(
            self.sources_information["torrentCacheSources"].values(),
            self.sources_information['hosterSources'].values(),
            self.sources_information['cloudFiles'])
        sorted_sources = self.sources_information['adaptiveSources'] + sorted_sources
        return uncached, sorted_sources, self.item_information

    def _get_imdb_info(self):
        if self.media_type == 'movie':
            # Confirm movie year against IMDb's information
            resp = self._imdb_suggestions(self.item_information['info']['imdb_id'])
            year = resp.get('y', self.item_information['info']['year'])
            # title = resp['l']
            # if title != self.item_information['info']['title']:
            #     self.item_information['info'].get('aliases', []).append(self.item_information['info']['title'])
            #     self.item_information['info']['title'] = title
            #     self.item_information['info']['originaltitle'] = title
            if year != self.item_information['info']['year']:
                self.item_information['info']['year'] = str(year)

        # else:
        #     resp = self._imdb_suggestions(self.item_information['info']['tvshow.imdb_id'])
        #     year = resp['y']
        #     title = resp['l']
        #     if year != self.item_information['info']['year']:
        #         self.item_information['info']['year'] = str(year)
        #     if self.item_information['info']['tvshowtitle'] != title:
        #         self.item_information['info'].get('aliases', []).append(
        #             self.item_information['info']['tvshowtitle'])
        #         self.item_information['info']['tvshowtitle'] = title
        #         self.item_information['info']['originaltitle'] = title

    def _imdb_suggestions(self, imdb_id):
        try:
            resp = self.session.get('https://v2.sg.media-imdb.com/suggestion/t/{}.json'.format(imdb_id))
            resp = json.loads(resp.text)['d'][0]
            return resp
        except (ValueError, KeyError):
            g.log('Failed to get IMDB suggestion')
            return {}

    def _send_provider_stop_event(self):
        for provider in self.running_providers:
            if hasattr(provider, 'cancel_operations') and callable(provider.cancel_operations):
                provider.cancel_operations()

    @staticmethod
    def _torrents_enabled():
        if (g.get_bool_setting('premiumize.torrents') and g.premiumize_enabled()) \
                or (g.get_bool_setting('rd.torrents') and g.real_debrid_enabled()) \
                or (g.get_bool_setting('alldebrid.torrents') and g.all_debrid_enabled()):
            return True
        else:
            return False

    @staticmethod
    def _hosters_enabled():
        if (g.get_bool_setting('premiumize.hosters') and g.premiumize_enabled()) \
                or (g.get_bool_setting('rd.hosters') and g.real_debrid_enabled()) \
                or (g.get_bool_setting('alldebrid.hosters') and g.all_debrid_enabled()):
            return True
        else:
            return False

    def _store_torrent_results(self, torrent_list):
        if len(torrent_list) == 0:
            return
        self.torrent_cache.add_torrent(self.item_information, torrent_list)

    def _get_local_torrent_results(self):

        local_storage = self.torrent_cache.get_torrents(self.item_information)[:100]

        relevant_torrents = []

        if self.media_type == 'episode':
            torrent_simple_info = self._build_simple_show_info(self.item_information)
            episode_regex = source_utils.get_filter_single_episode_fn(torrent_simple_info)
            show_regex = source_utils.get_filter_show_pack_fn(torrent_simple_info)
            season_regex = source_utils.get_filter_season_pack_fn(torrent_simple_info)

            for torrent in local_storage:
                clean_title = source_utils.clean_title(torrent['release_title'])
                if episode_regex(clean_title) or season_regex(clean_title) or show_regex(clean_title):
                    relevant_torrents.append(torrent)
        else:
            relevant_torrents = local_storage

        if len(relevant_torrents) > 0:
            for torrent in relevant_torrents:
                torrent['provider'] = '{} (Local Cache)'.format(torrent['provider'])

                self.sources_information["allTorrents"].update({torrent['hash']: torrent})

            TorrentCacheCheck(self).torrent_cache_check(relevant_torrents, self.item_information)

    @staticmethod
    def _get_best_torrent_to_cache(sources):
        quality_list = ['1080p', '720p', 'SD']
        sources = [i for i in sources if i.get('seeds', 0) != 0 and i.get("magnet")]

        for quality in quality_list:
            quality_filter = [i for i in sources if i['quality'] == quality]
            if len(quality_filter) > 0:
                packtype_filter = [i for i in quality_filter if
                                   i['package'] == 'show' or i['package'] == 'season']
                sorted_list = sorted(packtype_filter, key=lambda k: k['seeds'], reverse=True)
                if len(sorted_list) > 0:
                    return sorted_list[0]
                else:
                    package_type_list = [i for i in quality_filter if i['package'] == 'single']
                    sorted_list = sorted(package_type_list, key=lambda k: k['seeds'], reverse=True)
                    if len(sorted_list) > 0:
                        return sorted_list[0]

        return None

    def _build_cache_assist(self):
        if len(self.sources_information["allTorrents"]) == 0:
            return
        valid_packages = ['show', 'season', 'single']

        if self.media_type == 'episode' and self.item_information['is_airing']:
            valid_packages.remove('show')
            if int(self.item_information['info']['season']) >= int(
                    self.item_information['season_count']):
                valid_packages.remove('season')

        sources = [i for i in self.sources_information['allTorrents'].values() if i['package'] in valid_packages]

        if g.get_int_setting('general.cacheAssistMode') == 0:
            sources = [self._get_best_torrent_to_cache(sources)]
            if sources:
                action_args = tools.quote(json.dumps(sources))
                xbmc.executebuiltin(
                    'RunPlugin({}?action=cacheAssist&action_args={})'.format(g.BASE_URL, action_args))
        elif not self.silent:
            confirmation = xbmcgui.Dialog().yesno('{} - {}'.format(g.ADDON_NAME, g.get_language_string(30335)),
                                                  g.get_language_string(30057))
            if confirmation:
                window = ManualCacheWindow(*SkinManager().confirm_skin_path('manual_caching.xml'),
                                           item_information=self.item_information, sources=sources)
                window.doModal()
                del window

    def _init_providers(self):
        sys.path.append(g.ADDON_USERDATA_PATH)
        try:
            if g.ADDON_USERDATA_PATH not in sys.path:
                sys.path.append(g.ADDON_USERDATA_PATH)
                providers = importlib.import_module("providers")
            else:
                providers = reload_module(importlib.import_module("providers"))
        except ValueError:
            g.notification(g.ADDON_NAME, g.get_language_string(30477))
            g.log('No providers installed', 'warning')
            return

        providers_dict = providers.get_relevant(self.language)

        torrent_providers = providers_dict['torrent']
        hoster_providers = providers_dict['hosters']
        adaptive_providers = providers_dict['adaptive']

        hoster_providers, torrent_providers = self._remove_duplicate_providers(torrent_providers, hoster_providers)

        self.hoster_domains = resolver.Resolver.get_hoster_list()
        self.torrent_providers = torrent_providers
        self.hoster_providers = hoster_providers
        self.adaptive_providers = adaptive_providers
        self.host_domains = OrderedDict.fromkeys([host[0].lower() for provider in self.hoster_domains['premium'].keys()
                                                  for host in self.hoster_domains['premium'][provider]])
        self.host_names = OrderedDict.fromkeys([host[1].lower() for provider in self.hoster_domains['premium'].keys()
                                                for host in self.hoster_domains['premium'][provider]])

    @staticmethod
    def _remove_duplicate_providers(torrent, hosters):
        temp_list = []
        filter_list = []
        for i in torrent:
            if not i[1] in filter_list:
                temp_list.append(i)
                filter_list.append(i[1])

        torrent = temp_list
        temp_list = []
        for i in hosters:
            if not i[1] in filter_list:
                temp_list.append(i)
                filter_list.append(i[1])

        hosters = temp_list

        return hosters, torrent

    def _exit_thread(self, provider_name):
        if provider_name in self.sources_information["remainingProviders"]:
            self.sources_information["remainingProviders"].remove(provider_name)

    def _process_provider_torrent(self, torrent, provider_name, info):
        torrent['type'] = 'torrent'

        if not torrent.get('info'):
            torrent['info'] = source_utils.get_info(torrent['release_title'])

        torrent['quality'] = torrent.get('quality', '')
        if torrent['quality'] not in approved_qualities:
            torrent['quality'] = source_utils.get_quality(torrent['release_title'])

        torrent['hash'] = torrent.get('hash', self.hash_regex.findall(torrent['magnet'])[0]).lower()
        torrent['size'] = torrent.get('size', 0)
        torrent['size'] = self._torrent_filesize(torrent, info)

        if 'provider_name_override' in torrent:
            torrent['provider'] = torrent['provider_name_override']
        else:
            torrent['provider'] = provider_name

    def _get_adaptive_sources(self, info, provider):
        provider_name = provider[1].upper()
        try:
            self.sources_information["remainingProviders"].append(provider_name)
            provider_module = importlib.import_module('{}.{}'.format(provider[0], provider[1]))
            if not hasattr(provider_module, "sources"):
                g.log('Invalid provider, Source Class missing')
                return
            provider_source = provider_module.sources()

            if not hasattr(provider_source, self.media_type):
                g.log('Skipping provider: {} - Does not support {} types'.format(provider_name, self.media_type),
                      'warning')
                return

            self.running_providers.append(provider_source)

            if self.media_type == 'episode':
                simple_info = self._build_simple_show_info(info)
                results = provider_source.episode(simple_info, info)
            else:
                try:
                    results = provider_source.movie(info['info']['originaltitle'],
                                                    str(info['info']['year']),
                                                    info['info'].get('imdb_id'))
                except TypeError:
                    results = provider_source.movie(info['info']['originaltitle'],
                                                    str(info['info']['year']))

            if results is None:
                self.sources_information["remainingProviders"].remove(provider_name)
                return

            if self.canceled:
                return

            if len(results) > 0:
                # Begin filling in optional dictionary returns
                for result in results:
                    self._process_adaptive_source(result, provider_name, provider)

                self.sources_information['adaptiveSources'] += results

            self.running_providers.remove(provider_source)

            return
        finally:
            self.sources_information["remainingProviders"].remove(provider_name)

    @staticmethod
    def _process_adaptive_source(source, provider_name, provider_module):
        source['type'] = 'Adaptive'
        source['release_title'] = source.get('release_title', provider_name)
        source['source'] = provider_name.upper()
        source['quality'] = 'Variable'
        source['size'] = 'Variable'
        source['info'] = source.get('info', ['Adaptive Stream'])
        source['debrid_provider'] = provider_name
        source['provider_imports'] = provider_module
        source['provider'] = source.get('provider_name_override', provider_name.upper())
        return source

    def _get_torrent(self, info, provider):
        # Extract provider name from Tuple
        provider_name = provider[1].upper()

        # Begin Scraping Torrent Sources
        try:
            self.sources_information["remainingProviders"].append(provider_name)

            provider_module = importlib.import_module('{}.{}'.format(provider[0], provider[1]))
            if not hasattr(provider_module, "sources"):
                g.log('Invalid provider, Source Class missing')
                return
            provider_source = provider_module.sources()

            if not hasattr(provider_source, self.media_type):
                g.log('Skipping provider: {} - Does not support {} types'.format(provider_name, self.media_type),
                      'warning')
                return

            self.running_providers.append(provider_source)

            if self.media_type == 'episode':
                simple_info = self._build_simple_show_info(info)

                torrent_results = provider_source.episode(simple_info, info)
            else:
                try:
                    torrent_results = provider_source.movie(info['info']['originaltitle'],
                                                            str(info['info']['year']),
                                                            info['info'].get('imdb_id'))
                except TypeError:
                    torrent_results = provider_source.movie(info['info']['originaltitle'],
                                                            str(info['info']['year']))

            if torrent_results is None:
                self.sources_information["remainingProviders"].remove(provider_name)
                return

            if self.canceled:
                return

            if len(torrent_results) > 0:
                # Begin filling in optional dictionary returns
                for torrent in torrent_results:
                    self._process_provider_torrent(torrent, provider_name, info)

                torrent_results = {value['hash']: value for value in torrent_results}.values()
                start_time = time.time()

                # Check Debrid Providers for cached copies
                self._store_torrent_results(torrent_results)

                if self.canceled:
                    return

                [self.sources_information["allTorrents"].update({torrent['hash']: torrent})
                 for torrent in torrent_results]

                TorrentCacheCheck(self).torrent_cache_check([i for i in torrent_results], info)

                g.log('{} cache check took {} seconds'.format(provider_name, time.time() - start_time))

            self.running_providers.remove(provider_source)

            return
        finally:
            self.sources_information["remainingProviders"].remove(provider_name)

    def _do_hoster_episode(self, provider_source, provider_name, info):
        if not hasattr(provider_source, 'tvshow'):
            return
        imdb, tvdb, title, localtitle, aliases, year = self._build_hoster_variables(info, 'tvshow')

        if self.canceled:
            self._exit_thread(provider_name)
            return

        url = provider_source.tvshow(imdb, tvdb, title, localtitle, aliases, year)

        if self.canceled:
            self._exit_thread(provider_name)
            return

        imdb, tvdb, title, premiered, season, episode = self._build_hoster_variables(info, 'episode')

        if self.canceled:
            self._exit_thread(provider_name)
            return

        url = provider_source.episode(url, imdb, tvdb, title, premiered, season, episode)

        if self.canceled:
            self._exit_thread(provider_name)
            return

        return url

    def _do_hoster_movie(self, provider_source, provider_name, info):
        if not getattr(provider_source, 'movie'):
            self._exit_thread(provider_name)
            return
        imdb, title, localtitle, aliases, year = self._build_hoster_variables(info, 'movie')
        return provider_source.movie(imdb, title, localtitle, aliases, year)

    def _get_hosters(self, info, provider):
        provider_name = provider[1].upper()
        self.sources_information["remainingProviders"].append(provider_name.upper())
        try:
            provider_module = importlib.import_module('{}.{}'.format(provider[0], provider[1]))
            if hasattr(provider_module, "source"):
                provider_class = provider_module.source()
            else:
                self._exit_thread(provider_name)
                return

            self.running_providers.append(provider_class)

            if self.media_type == 'episode':
                sources = self._do_hoster_episode(provider_class, provider_name, info)
            else:
                sources = self._do_hoster_movie(provider_class, provider_name, info)

            if not sources:
                self._exit_thread(provider_name)
                return

            host_dict, hostpr_dict = self._build_hoster_variables(info, 'sources')

            if self.canceled:
                self._exit_thread(provider_name)
                return

            sources = provider_class.sources(sources, host_dict, hostpr_dict)

            if not sources:
                g.log('{}: Found No Sources'.format(provider_name), 'info')
                return

            if self.media_type == 'episode':
                title = '{} - {}'.format(self.item_information['info']['tvshowtitle'],
                                         self.item_information['info']['title'])
            else:
                title = '{} ({})'.format(self.item_information['info']['title'], self.item_information['info']['year'])

            for source in sources:
                source['type'] = 'hoster'
                source['release_title'] = source.get('release_title', title)
                source['source'] = source['source'].upper().split('.')[0]
                source['size'] = source.get('size', '0')
                source['info'] = source.get('info', [])
                source['provider_imports'] = provider
                source['provider'] = source.get('provider_name_override', provider_name.upper())

            sources1 = [i for i in sources for host in self.host_domains if host in i['url']]
            sources2 = [i for i in sources if i['source'].lower() in self.host_names or i['direct']]

            sources = sources1 + sources2

            for hoster in sources:
                try:
                    self.sources_information["hosterSources"].update({str(hoster['url']): hoster})
                except AttributeError:
                    break

            self._exit_thread(provider_name)

        finally:
            try:
                self.sources_information["remainingProviders"].remove(provider_name)
            except ValueError:
                pass

    def _user_cloud_inspection(self):
        self.sources_information["remainingProviders"].append("Cloud Inspection")
        try:
            thread_pool = ThreadPool()
            if self.media_type == "episode":
                simple_info = self._build_simple_show_info(self.item_information)
            else:
                simple_info = None

            cloud_scrapers = [
                {"setting": "premiumize.cloudInspection", "provider": PremiumizeCloudScaper,
                 "enabled": g.premiumize_enabled()},
                {"setting": "rd.cloudInspection", "provider": RealDebridCloudScraper,
                 "enabled": g.real_debrid_enabled()},
                {"setting": "alldebrid.cloudInspection", "provider": AllDebridCloudScraper,
                 "enabled": g.all_debrid_enabled()},
            ]

            for cloud_scraper in cloud_scrapers:
                if cloud_scraper["enabled"] and g.get_bool_setting(cloud_scraper["setting"]):
                    thread_pool.put(cloud_scraper["provider"](self._prem_terminate).get_sources, self.item_information,
                                    simple_info)

            sources = thread_pool.wait_completion()
            self.sources_information["cloudFiles"] = sources if sources else []

        finally:
            self.sources_information["remainingProviders"].remove("Cloud Inspection")

    @staticmethod
    def _color_number(number):

        if int(number) > 0:
            return g.color_string(number, 'green')
        else:
            return g.color_string(number, 'red')

    def _update_progress(self):
        list1 = [
            len([key for key, value in self.sources_information["torrentCacheSources"].items() if
                 value['quality'] == '4K']),
            len([key for key, value in self.sources_information["torrentCacheSources"].items() if
                 value['quality'] == '1080p']),
            len([key for key, value in self.sources_information["torrentCacheSources"].items() if
                 value['quality'] == '720p']),
            len([key for key, value in self.sources_information["torrentCacheSources"].items() if
                 value['quality'] == 'SD']),
        ]

        self.sources_information["torrents_quality"] = list1

        list2 = [
            len([key for key, value in self.sources_information["hosterSources"].items() if
                 value['quality'] == '4K']),
            len([key for key, value in self.sources_information["hosterSources"].items() if
                 value['quality'] == '1080p']),
            len([key for key, value in self.sources_information["hosterSources"].items() if
                 value['quality'] == '720p']),
            len([key for key, value in self.sources_information["hosterSources"].items() if
                 value['quality'] == 'SD']),

        ]
        self.sources_information["hosters_quality"] = list2

        # string1 = u'{} - 4K: {} | 1080: {} | 720: {} | SD: {}'.format(g.get_language_string(30058),
        #                                                              self._color_number(list1[0]),
        #                                                              self._color_number(list1[1]),
        #                                                              self._color_number(list1[2]),
        #                                                              self._color_number(list1[3]))
        # string2 = u'{} - 4k: {} | 1080: {} | 720: {} | SD: {}'.format(g.get_language_string(30059),
        #                                                              self._color_number(list2[0]),
        #                                                              self._color_number(list2[1]),
        #                                                              self._color_number(list2[2]),
        #                                                              self._color_number(list2[3]))
        #
        # string4 = '{} - 4k: 0 | 1080: 0 | 720: 0 | SD: 0'.format(g.get_language_string(30060))
        # provider_string = ', '.join(g.color_string(i for i in self.sources_information["remainingProviders"]))
        # string3 = '{} - {}'.format(g.get_language_string(30061), provider_string[2:])
        # return [string1, string2, string3, string4]

    @staticmethod
    def _build_simple_show_info(info):
        simple_info = {'show_title': info['info'].get('tvshowtitle', ''),
                       'episode_title': info['info'].get('originaltitle', ''),
                       'year': str(info['info'].get('year', '')),
                       'season_number': str(info['info']['season']),
                       'episode_number': str(info['info']['episode']),
                       'show_aliases': info['info'].get('aliases', []),
                       'country': info['info'].get('country_origin', ''),
                       'no_seasons': str(info.get('season_count', '')),
                       'absolute_number': str(info.get('absoluteNumber', '')),
                       'is_airing': info.get('is_airing', False),
                       'no_episodes': str(info.get('episode_count', '')),
                       'isanime': False}

        if '.' in simple_info['show_title']:
            simple_info['show_aliases'].append(source_utils.clean_title(simple_info['show_title'].replace('.', '')))
        if any(x in i.lower() for i in info['info'].get('genre', ['']) for x in ['anime', 'animation']):
            simple_info['isanime'] = True

        return simple_info

    def _build_hoster_variables(self, info, media_type):

        info = copy.deepcopy(info)

        if media_type == 'tvshow':
            imdb = info['info'].get('imdb_id')
            tvdb = info['info'].get('tvdb_id')
            title = info['info'].get('tvshowtitle')
            localtitle = ''
            aliases = info['info'].get('aliases', [])
            if '.' in title:
                aliases.append(source_utils.clean_title(title.replace('.', '')))
            year = str(info['info']['year'])
            return imdb, tvdb, title, localtitle, aliases, year

        elif media_type == 'episode':
            imdb = info['info'].get('imdb_id')
            tvdb = info['info'].get('tvdb_id')
            title = info['info'].get('title')
            premiered = info['info'].get('premiered')
            season = str(info['info'].get('season'))
            episode = str(info['info'].get('episode'))
            return imdb, tvdb, title, premiered, season, episode
        elif media_type == 'movie':
            imdb = info['info'].get('imdb_id')
            title = info['info'].get('originaltitle')
            localtitle = info['info'].get('title')
            aliases = info['info'].get('aliases', [])
            year = str(info['info'].get('year'))
            return imdb, title, localtitle, aliases, year
        elif media_type == 'sources':
            hostpr_dict = [host[0]
                           for debrid in self.hoster_domains['premium'].values()
                           for host in debrid]
            host_dict = self.hoster_domains['free']
            return host_dict, hostpr_dict

    def _debrid_hoster_duplicates(self):
        if len(self.sources_information["hosterSources"]) == 0:
            return

        updated_sources = {}
        for provider in self.hoster_domains['premium'].keys():
            hoster_sources = copy.deepcopy(self.sources_information["hosterSources"]).values()
            for hoster in self.hoster_domains['premium'][provider]:
                for file in hoster_sources:
                    if hoster[1].lower() == file['source'].lower() or hoster[0].lower() in str(file['url']).lower():
                        file['debrid_provider'] = provider
                        updated_sources.update({provider: file})
        self.sources_information["hosterSources"].update(updated_sources)

    def _get_pre_term_min(self):
        if self.media_type == 'episode':
            prem_min = g.get_int_setting('preem.tvres') + 1
        else:
            prem_min = g.get_int_setting('preem.movieres') + 1
        return prem_min

    def _get_sources_by_resolution(self, resolutions, source_type):
        return [i for i in self.sources_information[source_type].values()
                if i and
                'quality' in i and
                any(i['quality'].lower() == r.lower() for r in resolutions)]

    def _prem_terminate(self):  # pylint: disable=method-hidden
        if self.canceled:
            monkey_requests.PRE_TERM_BLOCK = True
            return True

        if g.get_bool_setting('preem.cloudfiles') and len(self.sources_information["cloudFiles"]) > 0:
            monkey_requests.PRE_TERM_BLOCK = True
            return True
        if g.get_bool_setting('preem.adaptiveSources') and len(self.sources_information["adaptiveSources"]) > 0:
            monkey_requests.PRE_TERM_BLOCK = True
            return True
        if not g.get_bool_setting('preem.enabled'):
            return False

        prem_min = self._get_pre_term_min()
        pre_term_log_string = 'Pre-emptively Terminated'

        approved_resolutions = source_utils.get_accepted_resolution_list()
        approved_resolutions.reverse()
        prem_resolutions = approved_resolutions[:prem_min]
        limit = g.get_int_setting('preem.limit')
        preem_type = g.get_int_setting('preem.type')
        try:
            if preem_type == 0 and len(self._get_sources_by_resolution(prem_resolutions, "torrentCacheSources")) >= limit:
                g.log(pre_term_log_string, 'info')
                monkey_requests.PRE_TERM_BLOCK = True
                return True
            if preem_type == 1 and len(self._get_sources_by_resolution(prem_resolutions, "hosterSources")) >= limit:
                g.log(pre_term_log_string, 'info')
                monkey_requests.PRE_TERM_BLOCK = True
                return True
            if preem_type == 2:
                # Terminating on both hosters and torrents
                sources = self._get_sources_by_resolution(prem_resolutions, "hosterSources")
                sources.append(self._get_sources_by_resolution(prem_resolutions, "torrentCacheSources"))

                if len(sources) >= limit:
                    g.log(pre_term_log_string, 'info')
                    monkey_requests.PRE_TERM_BLOCK = True
                    return True

        except (ValueError, KeyError, IndexError):
            pass

        return False

    @staticmethod
    def _torrent_filesize(torrent, info):

        if not torrent.get('size', 0):
            return 0
        size = int(torrent['size'])

        if torrent['package'] == 'show':
            size = size / int(info['show_episode_count'])
        elif torrent['package'] == 'season':
            size = size / int(info['episode_count'])
        return size


class TorrentCacheCheck:
    def __init__(self, scraper_class):
        self.premiumize_cached = []
        self.realdebrid_cached = []
        self.all_debrid_cached = []
        self.threads = ThreadPool()

        self.episode_strings = None
        self.season_strings = None
        self.scraper_class = scraper_class
        self.rd_api = real_debrid.RealDebrid()

    def store_torrent(self, torrent):
        """
        Pushes cached torrents back up to the calling class
        :param torrent: Torrent to return
        :type torrent: dict
        :return: None
        :rtype: None
        """
        try:
            sources_information = self.scraper_class.sources_information
            # Compare and combine source meta
            tor_key = torrent['hash'] + torrent['debrid_provider']
            sources_information['cached_hashes'].append(torrent['hash'])
            if tor_key in sources_information["torrentCacheSources"]:
                c_size = sources_information["torrentCacheSources"][tor_key].get('size', 0)
                n_size = torrent.get('size', 0)
                info = torrent.get('info', [])

                if c_size < n_size:
                    sources_information["torrentCacheSources"].update({tor_key: torrent})

                    sources_information["torrentCacheSources"][tor_key]['info'] \
                        .extend([i for i in info if
                                 i not in sources_information["torrentCacheSources"][tor_key].get('info', [])])
            else:
                sources_information["torrentCacheSources"].update({tor_key: torrent})
        except AttributeError:
            return

    def torrent_cache_check(self, torrent_list, info):
        """
        Run cache check threads for given torrents
        :param torrent_list: List of torrents to check
        :type torrent_list: list
        :param info: Metadata on item to check
        :type info: dict
        :return: None
        :rtype: None
        """
        if g.real_debrid_enabled() and g.get_bool_setting('rd.torrents'):
            self.threads.put(self._realdebrid_worker, copy.deepcopy(torrent_list), info)

        if g.premiumize_enabled() and g.get_bool_setting('premiumize.torrents'):
            self.threads.put(self._premiumize_worker, copy.deepcopy(torrent_list))

        if g.all_debrid_enabled() and g.get_bool_setting('alldebrid.torrents'):
            self.threads.put(self._all_debrid_worker, copy.deepcopy(torrent_list))
        self.threads.wait_completion()

    def _all_debrid_worker(self, torrent_list):

        try:
            api = all_debrid.AllDebrid()

            if len(torrent_list) == 0:
                return

            cache_check = api.check_hash([i['hash'] for i in torrent_list])

            if not cache_check:
                return

            for idx, i in enumerate(torrent_list):
                try:
                    if cache_check['magnets'][idx]['instant'] is True:
                        i['debrid_provider'] = 'all_debrid'
                        self.store_torrent(i)
                except KeyError:
                    g.log('KeyError in AllDebrid Cache check worker. '
                          'Failed to walk AllDebrid cache check response, check your auth and account status', 'error')
                    return
        except:
            g.log_stacktrace()

    def _realdebrid_worker(self, torrent_list, info):

        try:
            hash_list = [i['hash'] for i in torrent_list]
            api = real_debrid.RealDebrid()
            real_debrid_cache = api.check_hash(hash_list)

            for i in torrent_list:
                try:
                    if 'rd' not in real_debrid_cache.get(i['hash'], {}):
                        continue
                    if len(real_debrid_cache[i['hash']]['rd']) >= 1:
                        if self.scraper_class.media_type == 'episode':
                            self._handle_episode_rd_worker(i, real_debrid_cache, info)
                        else:
                            self._handle_movie_rd_worker(i, real_debrid_cache)
                except KeyError:
                    pass
        except:
            g.log_stacktrace()

    def _handle_movie_rd_worker(self, source, real_debrid_cache):
        for storage_variant in real_debrid_cache[source['hash']]['rd']:
            if not self.rd_api.is_streamable_storage_type(storage_variant):
                continue
            else:
                source['debrid_provider'] = 'real_debrid'
                self.store_torrent(source)

    def _handle_episode_rd_worker(self, source, real_debrid_cache, info):
        for storage_variant in real_debrid_cache[source['hash']]['rd']:

            if not self.rd_api.is_streamable_storage_type(storage_variant):
                continue

            if source_utils.get_best_episode_match('filename', storage_variant.values(), info):
                source['debrid_provider'] = 'real_debrid'
                self.store_torrent(source)
                break

    def _premiumize_worker(self, torrent_list):
        try:
            hash_list = [i['hash'] for i in torrent_list]
            if len(hash_list) == 0:
                return
            premiumize_cache = premiumize.Premiumize().hash_check(hash_list)
            premiumize_cache = premiumize_cache['response']
            count = 0
            for i in torrent_list:
                if premiumize_cache[count] is True:
                    i['debrid_provider'] = 'premiumize'
                    self.store_torrent(i)
                count += 1
        except:
            g.log_stacktrace()

class SourceWindowAdapter(object):
    """
    Class to handle different window style for scraper module
    """

    def __init__(self, item_information, scraper_sclass):
        self.trakt_id = 0
        self.silent = g.get_bool_setting('general.tempSilent')

        try:
            self.display_style = g.get_int_setting('general.scrapedisplay')
        except ValueError:
            self.display_style = 0
        self.item_information = item_information
        self.media_type = self.item_information['info']['mediatype']
        self.background_dialog = None
        self.dialog = None
        self.scraper_class = scraper_sclass

    def create(self):
        if self.silent:
            return
        if self.display_style == 1:
            self.background_dialog = xbmcgui.DialogProgressBG()
            if self.media_type == 'episode':
                self.trakt_id = self.item_information['trakt_id']
                self.background_dialog.create('{} - S{}E{}'.format(self.item_information['info']['tvshowtitle'],
                                                                   self.item_information['info']['season'],
                                                                   self.item_information['info']['episode']
                                                                   ))
            else:
                self.trakt_id = self.item_information['trakt_id']
                self.background_dialog.create('{} ({})'.format(self.item_information['info']['title'],
                                                               self.item_information['info']['year']))
            g.close_busy_dialog()
        elif self.display_style == 0:
            self.dialog = GetSourcesWindow(*SkinManager().confirm_skin_path('get_sources.xml'),
                                           item_information=self.item_information)
            self.dialog.set_scraper_class(self.scraper_class)
            self.dialog.show()

    def set_text(self, text, progress, sources_information, runtime):
        if self.silent:
            return
        if self.display_style == 0 and self.dialog:
            if text is not None:
                self.dialog.set_property('notification_text', text)
            self.dialog.update_properties(sources_information)
            self.dialog.set_property('progress', str(progress))
            self.dialog.set_property('runtime', str(runtime))
        elif self.display_style == 1 and self.background_dialog:
            self.background_dialog.update(progress, message=text)

    def set_property(self, key, value):
        if self.silent:
            return
        if self.display_style == 0 and self.dialog:
            self.dialog.set_property(key, str(value))
        elif self.display_style == 1:
            return

    def set_progress(self, progress):
        if self.silent:
            return
        if self.display_style == 0 and self.dialog:
            self.dialog.set_property('progress', str(progress))
        elif self.display_style == 1 and self.background_dialog:
            self.background_dialog.update(progress)

    def close(self):
        if self.silent:
            return
        if self.display_style == 0 and self.dialog:
            self.dialog.close()
            del self.dialog
        elif self.display_style == 1 and self.background_dialog:
            self.background_dialog.close()
