# -*- coding: utf-8 -*-
__metaclass__ = type

import copy
import json
import random
import re
import sys
import threading
import time

import requests

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.debrid import premiumize
from resources.lib.debrid import real_debrid
from resources.lib.debrid import all_debrid
from resources.lib.gui.windows.get_sources_window import GetSources as DisplayWindow
from resources.lib.modules import database
from resources.lib.modules import resolver as resolver
from resources.lib.modules.skin_manager import SkinManager

sysaddon = sys.argv[0]

approved_qualities = ['4K', '1080p', '720p', 'SD']


class CancelProcess(Exception):
    pass


def getSourcesHelper(actionArgs):
    sources_window = Sources(*SkinManager().confirm_skin_path('get_sources.xml'),
                             actionArgs=actionArgs)
    sources = sources_window.doModal()
    try:
        del sources_window
    except:
        pass
    return sources


class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        try:
            super(Sources, self).__init__(xml_file, location, actionArgs)
        except:
            self.args = actionArgs
            self.item_information = tools.get_item_information(actionArgs)
            self.canceled = False

        self.torrent_threads = []
        self.hoster_threads = []
        self.torrentProviders = []
        self.hosterProviders = []
        self.language = 'en'
        self.torrentCacheSources = {}
        self.hosterSources = {}
        self.cloud_files = []
        self.remainingProviders = []
        self.allTorrents = {}
        self.hosterDomains = {}
        self.torrents_qual_len = [0, 0, 0, 0]
        self.hosters_qual_len = [0, 0, 0, 0]
        self.terminate = False
        self.trakt_id = ''
        self.silent = False
        self.return_data = (None, None, None)
        self.basic_windows = True
        self.progress = 1
        self.duplicates_amount = 0
        self.domain_list = []
        self.display_style = 0
        self.background_dialog = None

        self.torrent_semaphore = threading.Semaphore(20)
        self.hoster_semaphore = threading.Semaphore(30)

        self.line1 = ''
        self.line2 = ''
        self.line3 = ''

        self.host_domains = []
        self.host_names = []

    def getSources(self, args):
        try:
            # Extract arguments from url

            self.args = tools.get_item_information(args)
            if self.args is None:
                # Support old format of URLs
                self.args = json.loads(tools.unquote(args))
                self.args['info'] = self.args['episodeInfo'].pop('info')

            tools.log('Starting Scraping', 'debug')

            if 'showInfo' in self.args:
                self.trakt_id = self.args['showInfo']['ids']['trakt']

                if self.display_style == 1 and not self.silent:
                    self.background_dialog.create('%s - S%sE%s' % (self.args['showInfo']['info']['tvshowtitle'],
                                                                   self.args['info']['season'],
                                                                   self.args['info']['episode'],
                                                                   ))

            else:
                self.trakt_id = self.args['ids']['trakt']

                if self.display_style == 1 and not self.silent:
                    self.background_dialog.create('%s (%s)' % (self.args['info']['title'],
                                                               self.args['info']['year']))

            if not 'showInfo' in self.args:
                # Confirm movie year against IMDb's information

                try:
                    resp = requests.get('https://v2.sg.media-imdb.com/suggestion/t/%s.json' % self.args['ids']['imdb'])
                    year = json.loads(resp.text)['d'][0]['y']
                    if year != self.args['info']['year']:
                        self.args['info']['year'] = str(year)
                except:
                    pass

            else:
                try:
                    imdb = self.args['showInfo']['info']['imdbnumber']
                    resp = requests.get('https://v2.sg.media-imdb.com/suggestion/t/%s.json' % imdb)
                    resp = json.loads(resp.text)['d'][0]
                    year = resp['y']
                    title = resp['l']

                    if year != self.args['info']['year']:
                        self.args['showInfo']['info']['year'] = str(year)
                    if self.args['showInfo']['info']['tvshowtitle'] != title:
                        self.args['showInfo']['info']['showaliases'].append(
                            self.args['showInfo']['info']['tvshowtitle'])
                        self.args['showInfo']['info']['tvshowtitle'] = title
                        self.args['showInfo']['info']['originaltitle'] = title
                        self.args['info']['tvshowtitle'] = title
                except:
                    pass

            try:
                if tools.getSetting('general.torrentCache') == 'true':
                    self.setText(tools.lang(32081))
                    self.getLocalTorrentResults()
            except:
                import traceback
                traceback.print_exc()
                pass

            try:
                self.updateProgress()
            except:
                pass

            if not self.prem_terminate():

                self.setText(tools.lang(32082))
                self.initProviders()

                # Add the users cloud inspection to the threads to be run
                self.hoster_threads.append(threading.Thread(target=self.user_cloud_inspection))

                # Load threads for all sources
                if self._torrents_enabled():
                    for i in self.torrentProviders:
                        self.torrent_threads.append(threading.Thread(target=self.getTorrent, args=(self.args, i)))
                if self._hosters_enabled():
                    for i in self.hosterProviders:
                        self.hoster_threads.append(threading.Thread(target=self.getHosters, args=(self.args, i)))

                # Shuffle and start scraping threads
                random.shuffle(self.torrent_threads)
                random.shuffle(self.hoster_threads)
                for i in self.torrent_threads:
                    i.start()
                for i in self.hoster_threads:
                    i.start()

                self.setProperty('process_started', 'true')

                # Keep alive for gui display and threading
                timeout = int(tools.getSetting('general.timeout'))
                tools.log('Entering Keep Alive', 'info')
                start_time = time.time()
                runtime = 0

                while self.progress < 100:

                    tools.log('Remainin Providers %s' % self.remainingProviders)
                    if self.prem_terminate() is True or len(self.remainingProviders) == 0:
                        # Give some time for scrapers to initiate
                        if runtime > 5:
                            break

                    if self.canceled:
                        break

                    try:
                        self.updateProgress()
                    except:
                        pass

                    try:
                        self.setProgress()
                        self.setText("4K: %s | 1080: %s | 720: %s | SD: %s" % (
                            tools.colorString(self.torrents_qual_len[0] + self.hosters_qual_len[0]),
                            tools.colorString(self.torrents_qual_len[1] + self.hosters_qual_len[1]),
                            tools.colorString(self.torrents_qual_len[2] + self.hosters_qual_len[2]),
                            tools.colorString(self.torrents_qual_len[3] + self.hosters_qual_len[3]),
                        ))

                    except:
                        import traceback
                        traceback.print_exc()

                    # Update Progress
                    time.sleep(.200)
                    runtime = time.time() - start_time
                    self.progress = int(100 - float(1 - (runtime / float(timeout))) * 100)

                tools.log('Exited Keep Alive', 'info')

            self.debridHosterDuplicates()

            try:
                self.torrentCacheSources = [value for key, value in self.torrentCacheSources.iteritems()]
            except:
                self.torrentCacheSources = [value for key, value in self.torrentCacheSources.items()]
            try:
                self.allTorrents = [value for key, value in self.allTorrents.iteritems()]
            except:
                self.allTorrents = [value for key, value in self.allTorrents.items()]

            self.build_cache_assist()

            # Returns empty list if no sources are found, otherwise sort sources
            cached = [i['hash'] for i in self.torrentCacheSources]
            uncached = [i for i in self.allTorrents if i['hash'] not in cached]

            if len(self.torrentCacheSources) + len(self.hosterSources) + len(self.cloud_files) == 0:
                try:
                    tools.cancelPlayback()
                except:
                    pass
                if self.silent:
                    tools.showDialog.notification(tools.addonName, tools.lang(32085))

                self.return_data = (uncached, [], self.args)
                self.close()
                return

            sorted = self.sortSources(self.torrentCacheSources, self.hosterSources)

            self.return_data = [uncached, sorted, self.args]
            self.close()
            return

        except:
            self.close()
            import traceback
            traceback.print_exc()

    def _torrents_enabled(self):
        if (tools.getSetting('premiumize.torrents') == 'true' and tools.premiumize_enabled())\
                or (tools.getSetting('rd.torrents') == 'true' and tools.real_debrid_enabled())\
                or (tools.getSetting('alldebrid.torrents') == 'true' and tools.all_debrid_enabled()):
            return True
        else:
            return False

    def _hosters_enabled(self):
        if (tools.getSetting('premiumize.hosters') == 'true' and tools.premiumize_enabled())\
                or (tools.getSetting('rd.hosters') == 'true' and tools.real_debrid_enabled())\
                or (tools.getSetting('alldebrid.hosters') == 'true' and tools.all_debrid_enabled()):
            return True
        else:
            return False


    def storeTorrentResults(self, torrent_list):

        try:
            if len(torrent_list) == 0:
                return

            database.addTorrent(self.item_information, torrent_list)
        except:
            pass

    def getLocalTorrentResults(self):

        local_storage = database.getTorrents(self.item_information)

        relevant_torrents = []

        if 'showInfo' in self.args:
            simple_info = self.buildSimpleShowInfo(self.args)
            for torrent in local_storage:
                if source_utils.filter_single_episode(simple_info, torrent['release_title']):
                    relevant_torrents.append(torrent)
                elif source_utils.filter_season_pack(simple_info, torrent['release_title']):
                    relevant_torrents.append(torrent)
                elif source_utils.filter_show_pack(simple_info, torrent['release_title']):
                    relevant_torrents.append(torrent)
        else:
            relevant_torrents = local_storage

        if len(relevant_torrents) > 0:
            for torrent in relevant_torrents:
                torrent['provider'] = '%s (Local Cache)' % torrent['provider']

                self.allTorrents.update({torrent['hash']: torrent})

            cached_torrents = TorrentCacheCheck().torrentCacheCheck(relevant_torrents, self.args)
            for torrent in cached_torrents:
                self.torrentCacheSources.update({torrent['hash'] + torrent['debrid_provider']: torrent})

    def build_cache_assist(self):

        args = self.item_information

        if tools.getSetting('general.autocache') == 'false':
            return
        if len(self.allTorrents) == 0:
            return
        if len(self.torrentCacheSources) > 0:
            return
        if len(self.cloud_files) > 0:
            return

        build_list = []

        if tools.getSetting('general.cacheAssistMode') == "0":
            quality_list = ['1080p', '720p', 'SD']

            for quality in quality_list:
                if len(build_list) > 0: break
                quality_filter = [i for i in self.allTorrents if i['quality'] == quality]
                if len(quality_filter) > 0:
                    packtype_filter = [i for i in quality_filter if
                                       i['package'] == 'show' or i['package'] == 'season']
                    sorted_list = sorted(packtype_filter, key=lambda k: k['seeds'], reverse=True)
                    if len(sorted_list) > 0:
                        build_list.append(sorted_list[0])
                        break
                    else:
                        package_type_list = [i for i in quality_filter if i['package'] == 'single']
                        sorted_list = sorted(package_type_list, key=lambda k: k['seeds'], reverse=True)
                        if sorted_list > 0:
                            build_list.append(sorted_list[0])
        else:

            if self.silent is True:
                return

            yesno = tools.showDialog.yesno('%s - %s' % (tools.addonName, tools.lang(40307)), tools.lang(32086))
            if yesno == 0:
                return

            sorted_list = sorted(self.allTorrents, key=lambda i: i['seeds'], reverse=True)
            display_list = ['%sS | %s | %s | %s' %
                            (i['seeds'], tools.color_quality(i['quality']),
                             tools.source_size_display(i['size']),
                             tools.colorString(i['release_title']))
                            for i in sorted_list]

            selection = tools.showDialog.select('%s - ' % tools.addonName + tools.lang(32087),
                                                display_list)
            if selection == -1:
                return

            build_list.append(sorted_list[selection])

        if len(build_list) > 0:
            actionArgs = {'torrent_list': build_list, 'args': args}
            actionArgs = tools.quote(json.dumps(actionArgs))
            tools.execute('RunPlugin(%s?action=cacheAssist&actionArgs=%s)' % (sysaddon, actionArgs))

        return

    def initProviders(self):
        sys.path.append(tools.dataPath)
        import providers
        sourceList = providers.get_relevant(self.language)

        torrent_providers = sourceList[0]
        hoster_providers = sourceList[1]

        hoster_providers, torrent_providers = self.remove_duplicate_providers(torrent_providers, hoster_providers)

        self.hosterDomains = resolver.Resolver(*SkinManager().confirm_skin_path('resolver.xml')).getHosterList()
        self.torrentProviders = torrent_providers
        self.hosterProviders = hoster_providers
        self.host_domains = list(set([host[0].lower() for provider in self.hosterDomains['premium'].iterkeys()
                                      for host in self.hosterDomains['premium'][provider]]))
        self.host_names = list(set([host[1].lower() for provider in self.hosterDomains['premium'].iterkeys()
                                    for host in self.hosterDomains['premium'][provider]]))

    def remove_duplicate_providers(self, torrent, hosters):

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

    def getTorrent(self, info, provider):
        # Extract provider name from Tuple
        provider_name = provider[1].upper()

        # Begin Scraping Torrent Sources

        def exit_thread():
            self.torrent_semaphore.release()
            if provider_name in self.remainingProviders:
                self.remainingProviders.remove(provider_name)

        try:
            self.remainingProviders.append(provider_name)
            self.torrent_semaphore.acquire()
            providerModule = __import__('%s.%s' % (provider[0], provider[1]), fromlist=[''])
            provider_source = providerModule.sources()

            if 'showInfo' in info:
                if not getattr(provider_source, 'episode', None):
                    exit_thread()
                    return
                simpleInfo = self.buildSimpleShowInfo(info)
                torrent_results = provider_source.episode(simpleInfo, info)

            else:
                if not getattr(provider_source, 'movie', None):
                    exit_thread()
                    return
                try:
                    torrent_results = provider_source.movie(info['info']['title'],
                                                            info['info']['year'],
                                                            info['ids']['imdb'])
                except:
                    torrent_results = provider_source.movie(info['info']['title'],
                                                            info['info']['year'], )

            if torrent_results is None:
                self.remainingProviders.remove(provider_name)
                return

            if self.canceled: raise CancelProcess

            if len(torrent_results) > 0:
                # Begin filling in optional dictionary returns
                for torrent in torrent_results:
                    try:
                        torrent['type'] = 'torrent'
                        torrent['info'] = torrent.get('info', '')
                        if torrent['info'] == '':
                            torrent['info'] = source_utils.getInfo(torrent['release_title'])

                        torrent['quality'] = torrent.get('quality', '')
                        if torrent['quality'] not in approved_qualities:
                            torrent['quality'] = source_utils.getQuality(torrent['release_title'])

                        torrent['hash'] = torrent.get('hash', '')
                        if torrent['hash'] == '':
                            torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0]
                        torrent['hash'] = torrent['hash'].lower()

                        torrent['size'] = torrent.get('size', 0)
                        if torrent['size'] == '':
                            torrent['size'] = 0

                        torrent['size'] = self.torrent_filesize(torrent, info)

                        if 'provider_name_override' in torrent:
                            torrent['provider'] = torrent['provider_name_override']
                        else:
                            torrent['provider'] = provider_name

                    except:
                        import traceback
                        traceback.print_exc()
                        continue

                de_dup = {}

                for i in torrent_results:
                    de_dup.update({i['hash']: i})

                try:
                    torrent_results = [value for key, value in de_dup.iteritems()]
                except:
                    torrent_results = [value for key, value in de_dup.items()]

                start_time = time.time()

                # Check Debrid Providers for cached copies
                self.storeTorrentResults(torrent_results)

                if self.canceled: raise CancelProcess
                cached = TorrentCacheCheck().torrentCacheCheck(torrent_results, info)

                for torrent in cached:
                    try:
                        # Compare and combine source meta
                        tor_key = torrent['hash'] + torrent['debrid_provider']
                        if tor_key in self.torrentCacheSources:
                            c_size = self.torrentCacheSources[tor_key].get('size', 0)
                            n_size = torrent.get('size', 0)
                            info = torrent.get('info', [])

                            if c_size < n_size:
                                self.torrentCacheSources.update({tor_key: torrent})

                            self.torrentCacheSources[tor_key]['info'] += [i for i in info
                                                                          if i not in
                                                                          self.torrentCacheSources[tor_key]
                                                                              .get('info', [])]
                        else:
                            self.torrentCacheSources.update({tor_key: torrent})
                    except AttributeError:
                        break

                for torrent in torrent_results:
                    try:
                        self.allTorrents.update({torrent['hash']: torrent})
                    except AttributeError:
                        break

                tools.log('%s cache check took %s seconds' % (provider_name, time.time() - start_time))

            return

        except CancelProcess:
            try:
                self.remainingProviders.remove(provider_name)
            except:
                pass
            return

        except:
            import traceback
            traceback.print_exc()
            try:
                self.remainingProviders.remove(provider_name)
            except:
                pass

        finally:
            try:
                self.remainingProviders.remove(provider_name)
            except:
                pass
            try:
                self.torrent_semaphore.release()
            except:
                pass

    def getHosters(self, info, provider):
        provider_name = provider[1].upper()
        self.remainingProviders.append(provider_name.upper())

        self.hoster_semaphore.acquire()

        try:
            if self.canceled:
                return
            providerModule = __import__('%s.%s' % (provider[0], provider[1]), fromlist=[''])
            provider_sources = providerModule.source()

            if 'showInfo' in info:
                if not getattr(provider_sources, 'tvshow', None):
                    return
                imdb, tvdb, title, localtitle, aliases, year = self.buildHosterVariables(info, 'tvshow')

                if self.canceled:
                    return

                url = provider_sources.tvshow(imdb, tvdb, title, localtitle, aliases, year)

                if self.canceled:
                    return

                imdb, tvdb, title, premiered, season, episode = self.buildHosterVariables(info, 'episode')

                if self.canceled:
                    return

                url = provider_sources.episode(url, imdb, tvdb, title, premiered, season, episode)

                if self.canceled:
                    return

            else:
                if not getattr(provider_sources, 'movie'):
                    return
                imdb, title, localtitle, aliases, year = self.buildHosterVariables(info, 'movie')
                url = provider_sources.movie(imdb, title, localtitle, aliases, year)

            hostDict, hostprDict = self.buildHosterVariables(info, 'sources')

            if self.canceled:
                return

            sources = provider_sources.sources(url, hostDict, hostprDict)

            if self.canceled:
                return

            if sources is None:
                tools.log('%s: Found No Sources' % provider_name, 'info')
                return

            if 'showInfo' in info:
                title = '%s - %s' % (info['showInfo']['info']['tvshowtitle'],
                                     info['info']['title'])
            else:
                title = '%s (%s)' % (title, year)

            for source in sources:
                source['type'] = 'hoster'
                source['release_title'] = source.get('release_title', title)
                source['source'] = source['source'].upper().split('.')[0]
                source['size'] = source.get('size', '0')
                source['info'] = source.get('info', [])
                source['provider_imports'] = provider

                if 'provider_name_override' in source:
                    source['provider'] = source['provider_name_override']
                else:
                    source['provider'] = provider_name.upper()

            sources1 = [i for i in sources for host in self.host_domains if host in i['url']]
            sources2 = [i for i in sources if i['source'].lower() in self.host_names or i['direct']]

            sources = sources1 + sources2

            for hoster in sources:
                try:
                    self.hosterSources.update({str(hoster['url']): hoster})
                except AttributeError:
                    break

        except:
            import traceback
            traceback.print_exc()
            return

        finally:
            try:
                self.remainingProviders.remove(provider_name)
            except:
                pass
            try:
                self.hoster_semaphore.release()
            except:
                pass

        return

    def user_cloud_inspection(self):
        self.remainingProviders.append('Cloud Inspection')
        threads = []

        if tools.premiumize_enabled() and tools.getSetting('premiumize.cloudInspection') == 'true':
            threads.append(threading.Thread(target=self.premiumize_cloud_inspection))

        if tools.real_debrid_enabled() and tools.getSetting('rd.cloudInspection') == 'true':
            threads.append(threading.Thread(target=self.rd_cloud_inspection))

        for i in threads:
            i.start()

        for i in threads:
            i.join()

        self.remainingProviders.remove('Cloud Inspection')

    def rd_cloud_inspection(self):

        torrents = real_debrid.RealDebrid().list_torrents()

        if 'showInfo' in self.args:
            torrent_simple_info = self.buildSimpleShowInfo(self.args)
            for i in torrents:
                if self.prem_terminate():
                    return
                if source_utils.filter_show_pack(torrent_simple_info, i['filename']) \
                        or source_utils.filter_season_pack(torrent_simple_info, i['filename']) \
                        or source_utils.filter_single_episode(torrent_simple_info, i['filename']):

                    torrent_info = real_debrid.RealDebrid().torrentInfo(i['id'])

                    if not any(tor_file['path'].lower().endswith(extension) for extension in
                               source_utils.COMMON_VIDEO_EXTENSIONS for tor_file in
                               [selected for selected in torrent_info['files'] if selected['selected'] == 1]):
                        continue

                    for f_index, torrent_file in enumerate([cloud_file for cloud_file in torrent_info['files']
                                                            if cloud_file['selected'] == 1]):
                        name = torrent_file['path']
                        if name.startswith('/'):
                            name = name.split('/')[-1]

                        if source_utils.filter_single_episode(torrent_simple_info, name):
                            self.cloud_files.append(
                                {
                                    'quality': source_utils.getQuality(i['filename']),
                                    'language': self.language,
                                    'url': torrent_info['links'][f_index],
                                    'provider': 'Cloud',
                                    'type': 'cloud',
                                    'release_title': i['filename'],
                                    'info': source_utils.getInfo(i['filename']),
                                    'debrid_provider': 'real_debrid',
                                    'size': (torrent_file['bytes'] / 1024) / 1024
                                }
                            )
                            break

        else:

            for i in torrents:
                if self.prem_terminate(): return
                if source_utils.filter_movie_title(i['filename'], self.args['info']['title'],
                                                   self.args['info']['year']):

                    torrent_info = real_debrid.RealDebrid().torrentInfo(i['id'])

                    if not any(tor_file['path'].lower().endswith(extension) for extension in
                               source_utils.COMMON_VIDEO_EXTENSIONS for tor_file in
                               [selected for selected in torrent_info['files'] if selected['selected'] == 1]):
                        continue

                    for f_index, torrent_file in enumerate([cloud_file for cloud_file in torrent_info['files']
                                                            if cloud_file['selected'] == 1]):
                        self.cloud_files.append({
                            'quality': source_utils.getQuality(i['filename']),
                            'language': self.language,
                            'url': torrent_info['links'][f_index],
                            'provider': 'Cloud',
                            'type': 'cloud',
                            'release_title': i['filename'],
                            'info': source_utils.getInfo(i['filename']),
                            'debrid_provider': 'real_debrid',
                            'size': (torrent_file['bytes'] / 1024) / 1024
                        })
                        break
                    continue

    def premiumize_cloud_inspection(self):
        cloud_items = premiumize.Premiumize().list_folder_all('')

        cloud_items = [i for i in cloud_items
                       if any(i['name'].endswith(ext) for ext in source_utils.COMMON_VIDEO_EXTENSIONS)]

        if 'showInfo' in self.args:
            torrent_simple_info = self.buildSimpleShowInfo(self.args)
            for item in cloud_items:
                if source_utils.filter_single_episode(torrent_simple_info, item['name']):
                    self._add_premiumize_cloud_item(item)
        else:
            for item in cloud_items:
                if source_utils.filter_movie_title(item['name'],
                                                   self.args['info']['title'],
                                                   self.args['info']['year']):
                    self._add_premiumize_cloud_item(item)

    def _add_premiumize_cloud_item(self, item):
        self.cloud_files.append({
            'quality': source_utils.getQuality(item['name']),
            'language': self.language,
            'url': item['id'],
            'provider': 'Cloud',
            'type': 'cloud',
            'release_title': item['name'],
            'info': source_utils.getInfo(item['name']),
            'debrid_provider': 'premiumize',
            'size': (int(item['size']) / 1024) / 1024
        })

    def resolutionList(self):
        resolutions = []

        max_res = int(tools.getSetting('general.maxResolution'))
        if max_res == 3 or max_res < 3:
            resolutions.append('SD')
        if max_res < 3:
            resolutions.append('720p')
        if max_res < 2:
            resolutions.append('1080p')
        if max_res < 1:
            resolutions.append('4K')

        return resolutions

    def debrid_priority(self):
        p = []

        if tools.getSetting('premiumize.enabled') == 'true':
            p.append({'slug': 'premiumize', 'priority': int(tools.getSetting('premiumize.priority'))})
        if tools.getSetting('realdebrid.enabled') == 'true':
            p.append({'slug': 'real_debrid', 'priority': int(tools.getSetting('rd.priority'))})
        if tools.getSetting('alldebrid.enabled') == 'true':
            p.append({'slug': 'all_debrid', 'priority': int(tools.getSetting('alldebrid.priority'))})

        p = sorted(p, key=lambda i: i['priority'])

        return p

    def sortSources(self, torrent_list, hoster_list):
        sort_method = int(tools.getSetting('general.sortsources'))

        sortedList = []

        for i in self.cloud_files:
            sortedList.append(i)

        resolutions = self.resolutionList()

        resolutions.reverse()

        if tools.getSetting('general.sizesort') == 'true':
            torrent_list = sorted(torrent_list, key=lambda k: k['size'], reverse=True)
        else:
            random.shuffle(torrent_list)

        if tools.getSetting('general.disable3d') == 'true':
            torrent_list = [i for i in torrent_list if '3D' not in i['info']]
            hoster_list = [i for i in hoster_list if '3D' not in i['info']]

        if tools.getSetting('general.disablelowQuality') == 'true':
            torrent_list = [i for i in torrent_list if 'CAM' not in i['info']]
            hoster_list = [i for i in hoster_list if 'CAM' not in i['info']]

        if tools.getSetting('general.enablesizelimit') == 'true':
            if 'showInfo' in self.args:
                size_limit = int(tools.getSetting('general.sizelimit.episode')) * 1024
            else:
                size_limit = int(tools.getSetting('general.sizelimit.movie')) * 1024
            torrent_list = [i for i in torrent_list if i.get('size', 0) < size_limit]

        if tools.getSetting('general.265sort') == 'true':
            torrent_list = [i for i in torrent_list if 'HEVC' in i['info']] + \
                           [i for i in torrent_list if 'HEVC' not in i['info']]

            hoster_list = [i for i in hoster_list if 'HEVC' in i['info']] + \
                          [i for i in hoster_list if 'HEVC' not in i['info']]

        if tools.getSetting('general.lowQualitysort') == 'true':
            torrent_list = [i for i in torrent_list if 'CAM' not in i['info']] + \
                           [i for i in torrent_list if 'CAM' in i['info']]

            hoster_list = [i for i in hoster_list if 'CAM' not in i['info']] + \
                          [i for i in hoster_list if 'CAM' in i['info']]

        random.shuffle(hoster_list)

        debrid_priorities = self.debrid_priority()

        for resolution in resolutions:
            if sort_method == 0 or sort_method == 2:
                for debrid in debrid_priorities:
                    for torrent in torrent_list:
                        if debrid['slug'] == torrent['debrid_provider']:
                            if torrent['quality'] == resolution:
                                sortedList.append(torrent)

            if sort_method == 1 or sort_method == 2:
                for debrid in debrid_priorities:
                    for file in hoster_list:
                        if 'debrid_provider' in file:
                            if file['debrid_provider'] == debrid['slug']:
                                if file['quality'] == resolution:
                                    sortedList.append(file)

                for file in hoster_list:
                    if 'debrid_provider' not in file:
                        if file['quality'] == resolution:
                            sortedList.append(file)

        if sort_method == 1:
            for resolution in resolutions:
                for debrid in debrid_priorities:
                    for torrent in torrent_list:
                        if torrent['debrid_provider'] == debrid['slug']:
                            if torrent['quality'] == resolution:
                                sortedList.append(torrent)

        if sort_method == 0:
            for resolution in resolutions:
                for debrid in debrid_priorities:
                    for file in hoster_list:
                        if 'debrid_provider' in file:
                            if file['debrid_provider'] == debrid['slug']:
                                if file['quality'] == resolution:
                                    sortedList.append(file)

                for file in hoster_list:
                    try:
                        if 'debrid_provider' not in file and file['direct'] is True:
                            if file['quality'] == resolution:
                                sortedList.append(file)
                    except:
                        continue

        if tools.getSetting('general.disable265') == 'true':
            sortedList = [i for i in sortedList if 'HEVC' not in i['info']]

        if tools.getSetting('general.hidesd') == 'true':
            sortedList = [i for i in sortedList if i['quality'] != 'SD']

        return sortedList

    def colorNumber(self, number):

        if int(number) > 0:
            return tools.colorString(number, 'green')
        else:
            return tools.colorString(number, 'red')

    def updateProgress(self):

        try:
            list1 = [
                len([key for key, value in self.torrentCacheSources.iteritems() if value['quality'] == '4K']),
                len([key for key, value in self.torrentCacheSources.iteritems() if value['quality'] == '1080p']),
                len([key for key, value in self.torrentCacheSources.iteritems() if value['quality'] == '720p']),
                len([key for key, value in self.torrentCacheSources.iteritems() if value['quality'] == 'SD']),
            ]
        except:
            # Python 3 compatibility
            list1 = [
                len([key for key, value in self.torrentCacheSources.items() if value['quality'] == '4K']),
                len([key for key, value in self.torrentCacheSources.items() if value['quality'] == '1080p']),
                len([key for key, value in self.torrentCacheSources.items() if value['quality'] == '720p']),
                len([key for key, value in self.torrentCacheSources.items() if value['quality'] == 'SD']),
            ]

        self.torrents_qual_len = list1

        try:
            list2 = [
                len([key for key, value in self.hosterSources.iteritems() if value['quality'] == '4K']),
                len([key for key, value in self.hosterSources.iteritems() if value['quality'] == '1080p']),
                len([key for key, value in self.hosterSources.iteritems() if value['quality'] == '720p']),
                len([key for key, value in self.hosterSources.iteritems() if value['quality'] == 'SD']),

            ]
        except:
            list2 = [
                len([key for key, value in self.hosterSources.items() if value['quality'] == '4K']),
                len([key for key, value in self.hosterSources.items() if value['quality'] == '1080p']),
                len([key for key, value in self.hosterSources.items() if value['quality'] == '720p']),
                len([key for key, value in self.hosterSources.items() if value['quality'] == 'SD']),

            ]
        self.hosters_qual_len = list2

        string1 = '%s - 4K: %s | 1080: %s | 720: %s | SD: %s' % (tools.lang(32088),
                                                                 self.colorNumber(list1[0]),
                                                                 self.colorNumber(list1[1]),
                                                                 self.colorNumber(list1[2]),
                                                                 self.colorNumber(list1[3]))

        string2 = '%s - 4k: %s | 1080: %s | 720: %s | SD: %s' % (tools.lang(32089),
                                                                 self.colorNumber(list2[0]),
                                                                 self.colorNumber(list2[1]),
                                                                 self.colorNumber(list2[2]),
                                                                 self.colorNumber(list2[3]))

        string4 = '%s - 4k: 0 | 1080: 0 | 720: 0 | SD: 0' % tools.lang(32090)
        providerString = ''
        for i in self.remainingProviders:
            providerString += ', ' + tools.colorString(str(i))
        string3 = '%s - %s' % (tools.lang(32091), providerString[2:])

        return [string1, string2, string3, string4]

    def buildSimpleShowInfo(self, info):

        simpleInfo = {}
        simpleInfo['show_title'] = info['showInfo']['info']['originaltitle']
        simpleInfo['episode_title'] = info['info']['originaltitle']
        simpleInfo['year'] = info['showInfo']['info']['year']
        simpleInfo['season_number'] = str(info['info']['season'])
        simpleInfo['episode_number'] = str(info['info']['episode'])
        simpleInfo['show_aliases'] = info['showInfo']['info']['showaliases']
        if '.' in simpleInfo['show_title']:
            simpleInfo['show_aliases'].append(source_utils.cleanTitle(simpleInfo['show_title'].replace('.', '')))
        simpleInfo['country'] = info['showInfo']['info']['country']
        simpleInfo['no_seasons'] = str(info['showInfo']['info']['season_count'])
        simpleInfo['absolute_number'] = str(info['info'].get('absoluteNumber', ''))
        simpleInfo['isanime'] = False

        if any(x in i.lower() for i in info['showInfo']['info'].get('genre', ['']) for x in ['anime', 'animation']):
            simpleInfo['isanime'] = True

        return simpleInfo

    def buildHosterVariables(self, info, type):

        info = copy.deepcopy(info)

        if type == 'tvshow':
            imdb = info['showInfo']['ids']['imdb']
            tvdb = info['showInfo']['ids']['tvdb']
            title = info['showInfo']['info']['tvshowtitle']
            localtitle = ''
            aliases = info['showInfo']['info']['showaliases']
            if '.' in title:
                aliases.append(source_utils.cleanTitle(title.replace('.', '')))
            year = info['showInfo']['info']['year']
            return imdb, tvdb, title, localtitle, aliases, year

        elif type == 'episode':
            imdb = info['ids']['imdb']
            tvdb = info['ids']['tvdb']
            title = info['info']['title']
            premiered = info['info']['premiered']
            season = str(info['info']['season'])
            episode = str(info['info']['episode'])
            return imdb, tvdb, title, premiered, season, episode
        elif type == 'movie':
            imdb = info['ids']['imdb']
            title = info['info']['title']
            localtitle = info['info']['title']
            aliases = info['info']['aliases']
            year = info['info']['year']
            return imdb, title, localtitle, aliases, year
        elif type == 'sources':
            hostprDict = [host[0]
                          for debrid in self.hosterDomains['premium'].itervalues()
                          for host in debrid]
            hostDict = self.hosterDomains['free']
            return hostDict, hostprDict

    def debridHosterDuplicates(self):

        if len(self.hosterSources) == 0: return

        source_list = []
        providers = [i for i in self.hosterDomains['premium'].iterkeys()]

        for provider in providers:
            hoster_sources = copy.deepcopy(self.hosterSources)
            try:
                hoster_sources = [value for key, value in hoster_sources.iteritems()]
            except:
                hoster_sources = [value for key, value in hoster_sources.items()]
            for hoster in self.hosterDomains['premium'][provider]:
                for file in hoster_sources:
                    if hoster[1].lower() == file['source'].lower() or hoster[0].lower() in str(file['url']).lower():
                        source_list.append(file)
                        source_list[-1]['debrid_provider'] = provider
        try:
            self.hosterSources = [value for key, value in self.hosterSources.iteritems()]
        except:
            self.hosterSources = [value for key, value in self.hosterSources.items()]
        self.hosterSources += source_list

    def prem_terminate(self):
        if tools.getSetting('preem.cloudfiles') == 'true':
            if len(self.cloud_files) > 0:
                return True

        if 'showInfo' in self.args:
            prem_min = int(tools.getSetting('preem.tvres')) + 1
        else:
            prem_min = int(tools.getSetting('preem.movieres')) + 1
        if tools.getSetting('preem.enabled') == 'false':
            return False

        prem_resolutions = ['4K', '1080p', '720p', 'SD']

        approved_resolutions = self.resolutionList()
        prem_resolutions = prem_resolutions[:prem_min]
        prem_resolutions = [resolution for resolution in prem_resolutions if resolution in approved_resolutions]
        limit = int(tools.getSetting('preem.limit'))
        type = int(tools.getSetting('preem.type'))
        try:
            if type == 0:
                try:
                    sources = [value for key, value in self.torrentCacheSources.iteritems()]
                except:
                    sources = [value for key, value in self.torrentCacheSources.items()]

                # Terminating on Torrents only
                if len([i for i in sources if i['quality'] in prem_resolutions]) >= limit:
                    tools.log('Pre-emptively Terminated', 'info')
                    return True
            if type == 1:
                try:
                    sources = [value for key, value in self.hosterSources.iteritems()]
                except:
                    sources = [value for key, value in self.hosterSources.items()]
                # Terminating on Hosters only
                if len([i for i in sources if i['quality'] in prem_resolutions]) >= limit:
                    tools.log('Pre-emptively Terminated', 'info')
                    return True
            if type == 2:
                # Terminating on both hosters and torrents
                try:
                    sources = [value for key, value in self.hosterSources.iteritems()]
                    sources += [value for key, value in self.torrentCacheSources.iteritems()]
                except:
                    sources = [value for key, value in self.hosterSources.items()]
                    sources += [value for key, value in self.torrentCacheSources.items()]

                if len([i for i in sources if i['quality'] in prem_resolutions]) >= limit:
                    tools.log('Pre-emptively Terminated', 'info')
                    return True
        except:
            pass

        return False

    def torrent_filesize(self, torrent, info):

        try:
            if torrent['size'] is None:
                return 0
            size = int(torrent['size'])
            if size == 0:
                return size
            if torrent['package'] == 'show':
                size = size / int(info['showInfo']['info']['episode_count'])
            if torrent['package'] == 'season':
                episodes = int(info['showInfo']['info']['episode_count']) / int(
                    info['showInfo']['info']['season_count'])
                size = size / episodes
        except:
            size = 0

        return size


class HosterCacheCheck:
    def __init__(self):
        return

        # I broke this bad, maybe let me get my shit together and sort it out at a later date lol
        # I Removed it, I don't even want to look at it.


class TorrentCacheCheck:
    def __init__(self):
        self.premiumizeCached = []
        self.realdebridCached = []
        self.all_debridCached = []
        self.threads = []

        self.episodeStrings = None
        self.seasonStrings = None

    def torrentCacheCheck(self, torrent_list, info):

        if tools.getSetting('realdebrid.enabled') == 'true' and \
                tools.getSetting('rd.torrents') == 'true':
            self.threads.append(
                threading.Thread(target=self.realdebridWorker, args=(copy.deepcopy(torrent_list), info)))

        if tools.getSetting('premiumize.enabled') == 'true' and \
                tools.getSetting('premiumize.torrents') == 'true':
            self.threads.append(threading.Thread(target=self.premiumizeWorker, args=(copy.deepcopy(torrent_list),)))

        if tools.getSetting('alldebrid.enabled') == 'true' and \
                tools.getSetting('alldebrid.torrents') == 'true':
            self.threads.append(threading.Thread(target=self.all_debrid_worker, args=(copy.deepcopy(torrent_list),)))

        for i in self.threads:
            i.start()
        for i in self.threads:
            i.join()

        cachedList = self.realdebridCached + self.premiumizeCached + self.all_debridCached
        return cachedList

    def all_debrid_worker(self, torrent_list):

        api = all_debrid.AllDebrid()
        hash_list = [i['hash'] for i in torrent_list]

        if len(hash_list) == 0:
            return

        cache_check = api.check_hash(hash_list)

        if not cache_check['success']:
            return

        cache_list = []
        count = 0

        for i in torrent_list:
            if cache_check['data'][count]['instant'] is True:
                i['debrid_provider'] = 'all_debrid'
                cache_list.append(i)
            count += 1

        self.all_debridCached = cache_list


    def _real_debrid_confirm_media(self, storage_variant):
        keys = list(storage_variant.keys())
        all_extensions = [storage_variant[key]['filename'] for key in keys]
        all_extensions = ['.' + filename.split('.')[-1] for filename in all_extensions]
        for ext in all_extensions:
            if ext not in source_utils.COMMON_VIDEO_EXTENSIONS:
                return False

        return True

    def _real_debrid_check_files(self, storage_variant):
        for key in storage_variant.keys():
            file_name = storage_variant[key]['filename']
            file_name = file_name.replace(source_utils.get_quality(file_name), '')
            file_name = source_utils.cleanTitle(file_name)
            if any(source_utils.cleanTitle(episodeString) in source_utils.cleanTitle(file_name)
                   for episodeString in self.episodeStrings):
                return True

    def realdebridWorker(self, torrent_list, info):
        try:
            if 'showInfo' in info:
                self.episodeStrings, self.seasonStrings = source_utils.torrentCacheStrings(info)
            cache_list = []

            hash_list = [i['hash'] for i in torrent_list]

            if len(hash_list) == 0:
                return

            realDebridCache = real_debrid.RealDebrid().checkHash(hash_list)

            for i in torrent_list:
                try:
                    if 'rd' not in realDebridCache.get(i['hash'], {}):
                        continue
                    if len(realDebridCache[i['hash']]['rd']) >= 1:
                        if 'showInfo' in info:
                            for storage_variant in realDebridCache[i['hash']]['rd']:

                                if not self._real_debrid_confirm_media(storage_variant):
                                    continue

                                if self._real_debrid_check_files(storage_variant):
                                    cache_list.append(i)
                                    cache_list[-1]['debrid_provider'] = 'real_debrid'
                                    break
                        else:
                            for storage_variant in realDebridCache[i['hash']]['rd']:
                                if not self._real_debrid_confirm_media(storage_variant):
                                    continue
                                else:
                                    cache_list.append(i)
                                    cache_list[-1]['debrid_provider'] = 'real_debrid'
                except:
                    import traceback
                    traceback.print_exc()
                    pass

            self.realdebridCached = cache_list

        except:
            import traceback
            traceback.print_exc()

    def premiumizeWorker(self, torrent_list):
        try:

            hash_list = [i['hash'] for i in torrent_list]
            if len(hash_list) == 0:
                return
            premiumizeCache = premiumize.Premiumize().hash_check(hash_list)
            premiumizeCache = premiumizeCache['response']
            cache_list = []
            count = 0
            for i in torrent_list:
                if premiumizeCache[count] is True:
                    i['debrid_provider'] = 'premiumize'
                    cache_list.append(i)
                count += 1

            self.premiumizeCached = cache_list

        except:
            import traceback
            traceback.print_exc()
            pass
