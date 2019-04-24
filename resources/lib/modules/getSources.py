# -*- coding: utf-8 -*-

import copy
import json
import os
import random
import re
import sys
import threading
import time
import traceback

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.debrid import premiumize
from resources.lib.debrid import real_debrid
from resources.lib.modules import database
from resources.lib.modules import resolver as resolver

sysaddon = sys.argv[0]

approved_qualities = ['4K', '1080p', '720p', 'SD']


class Sources(tools.dialogWindow):
    def __init__(self):
        self.torrent_threads = []
        self.hoster_threads = []
        self.torrentProviders = []
        self.hosterProviders = []
        self.language = 'en'
        self.torrentCacheSources = {}
        self.hosterSources = {}
        self.remainingProviders = []
        self.allTorrents = {}
        self.hosterDomains = {}
        self.torrents_qual_len = [0, 0, 0, 0]
        self.hosters_qual_len = [0, 0, 0, 0]
        self.terminate = False
        self.args = None
        self.trakt_id = ''
        self.silent = False
        self.return_data = (None, None)
        self.basic_windows = True
        self.progress = 1
        self.duplicates_amount = 0
        self.domain_list = []
        self.display_style = 0
        self.background_dialog = None
        text = ''

        background_image = os.path.join(tools.IMAGES_PATH, 'background.png')

        texture_path = os.path.join(tools.IMAGES_PATH, 'texture.png')
        background_diffuse = '0x1FFFFFFF'
        self.canceled = False
        self.perc_on_path = os.path.join(tools.IMAGES_PATH, 'on.png')
        self.perc_off_path = os.path.join(tools.IMAGES_PATH, 'off.png')
        self.texture = tools.imageControl(0, 0, 1280, 720, texture_path)
        self.addControl(self.texture)
        self.background = tools.imageControl(0, 0, 1280, 720, background_image)
        self.background.setColorDiffuse(background_diffuse)

        self.addControl(self.background)

        self.panda_logo = tools.imageControl(605, 330, 70, 60, tools.PANDA_LOGO_PATH)
        self.addControl(self.panda_logo)

        lpx = 570
        lpy = 410

        self.perc10 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc20 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc30 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc40 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc50 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc60 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc70 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc80 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc90 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc100 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)

        self.addControl(self.perc10)
        self.addControl(self.perc20)
        self.addControl(self.perc30)
        self.addControl(self.perc40)
        self.addControl(self.perc50)
        self.addControl(self.perc60)
        self.addControl(self.perc70)
        self.addControl(self.perc80)
        self.addControl(self.perc90)
        self.addControl(self.perc100)

        self.text_label = tools.labelControl(0, 430, 1280, 50, str(text), font='font13',
                                             alignment=tools.XBFONT_CENTER_X)
        self.text_label2 = tools.labelControl(0, 470, 1280, 50, "", font='font13', alignment=tools.XBFONT_CENTER_X)
        self.text_label3 = tools.labelControl(0, 510, 1280, 50, "", font='font13', alignment=tools.XBFONT_CENTER_X)

        self.line1 = ''
        self.line2 = ''
        self.line3 = ''

        self.addControl(self.text_label)
        self.addControl(self.text_label2)
        self.addControl(self.text_label3)

    def getSources(self, args):
        try:
            # Extract arguments from url
            self.args = json.loads(tools.unquote(args))

            tools.log('Starting Scraping', 'debug')

            if 'showInfo' in self.args:
                background = self.args['showInfo']['art'].get('fanart', '')
                self.trakt_id = self.args['showInfo']['ids']['trakt']

                if self.display_style == 1:
                    self.background_dialog.create('%s - S%sE%s' % (self.args['showInfo']['info']['tvshowtitle'],
                                                                   self.args['episodeInfo']['info']['season'],
                                                                   self.args['episodeInfo']['info']['episode'],
                                                                   ))

            else:
                self.trakt_id = self.args['ids']['trakt']
                background = self.args['art'].get('fanart')
                if self.display_style == 1:
                    self.background_dialog.create('%s (%s)' % (self.args['title'], self.args['year']))

            self.setText(tools.lang(32081))
            self.setBackground(background)

            try:
                self.getLocalTorrentResults()
            except:
                pass

            self.updateProgress()

            if not self.prem_terminate():

                self.setText(tools.lang(32082))
                self.initProviders()
                # Load threads for all sources
                for i in self.torrentProviders:
                    self.torrent_threads.append(threading.Thread(target=self.getTorrent, args=(self.args, i)))
                for i in self.hosterProviders:
                    self.hoster_threads.append(threading.Thread(target=self.getHosters, args=(self.args, i)))
                # Shuffle and start scraping threads
                random.shuffle(self.torrent_threads)
                random.shuffle(self.hoster_threads)
                for i in self.torrent_threads:
                    i.start()
                for i in self.hoster_threads:
                    i.start()

                self.setText(tools.lang(32083))


                # Keep alive for gui display and threading
                timeout = int(tools.getSetting('general.timeout'))
                tools.log('Entering Keep Alive', 'info')
                runtime = 0

                while self.progress < 100:

                    tools.log('Remainin Providers %s' % self.remainingProviders)
                    if self.prem_terminate() is True or len(self.remainingProviders) == 0:
                        if runtime > 5:
                            break

                    if self.canceled:
                        break

                    self.updateProgress()
                    # tools.progressDialog.update(progressPercent, line1, line2, line3)
                    try:
                        self.setProgress()
                        self.setText("4K: %s | 1080: %s | 720: %s | SD: %s" % (
                            tools.colorString(self.torrents_qual_len[0] + self.hosters_qual_len[0]),
                            tools.colorString(self.torrents_qual_len[1] + self.hosters_qual_len[1]),
                            tools.colorString(self.torrents_qual_len[2] + self.hosters_qual_len[2]),
                            tools.colorString(self.torrents_qual_len[3] + self.hosters_qual_len[3]),
                        ))
                        self.setText2("Torrents: %s | Cached: %s | Hosters: %s" % (
                            tools.colorString(len([i for i in self.allTorrents])),
                            tools.colorString(len([i for i in self.torrentCacheSources])),
                            tools.colorString(len([i for i in self.hosterSources]))
                        ))
                        if len(self.remainingProviders) > 5:
                            self.setText3("Remaining Providers: %s" % tools.colorString(len(self.remainingProviders)))
                        else:
                            self.setText3(' | '.join([tools.colorString(i.upper()) for i in self.remainingProviders]))
                    except:
                        import traceback
                        traceback.print_exc()

                    # Update Progress
                    time.sleep(1)
                    runtime += 1
                    self.progress = int(100 - float(1 - (runtime / float(timeout))) * 100)

                tools.log('Exited Keep Alive', 'info')

            self.debridHosterDuplicates()

            try: self.torrentCacheSources = [value for key, value in self.torrentCacheSources.iteritems()]
            except: self.torrentCacheSources = [value for key, value in self.torrentCacheSources.items()]
            try: self.allTorrents = [value for key, value in self.allTorrents.iteritems()]
            except: self.allTorrents = [value for key, value in self.allTorrents.items()]

            self.build_cache_assist()

            # Returns empty list if no sources are found, otherwise sort sources
            if len(self.torrentCacheSources) + len(self.hosterSources) == 0:
                try:
                    tools.playList.clear()
                    tools.closeOkDialog()
                except:
                    pass
                if self.silent:
                    tools.showDialog.notification(tools.addonName, tools.lang(32085))

                self.return_data = ([], self.args)
                self.close()
                return

            sorted = self.sortSources(self.torrentCacheSources, self.hosterSources)
            self.return_data = [sorted, self.args]
            self.close()
            return

        except:
            self.close()
            import traceback
            traceback.print_exc()

    def storeTorrentResults(self, trakt_id, torrent_list):

        if len(torrent_list) == 0:
            return
        for torrent in torrent_list:
            database.addTorrent(trakt_id, torrent)

    def getLocalTorrentResults(self):
        local_storage = database.getTorrents(self.trakt_id)
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
                torrent['source'] = '%s (Local Cache)' % torrent['source']
                self.allTorrents.update({torrent['hash']: torrent})

            cached_torrents = TorrentCacheCheck().torrentCacheCheck(relevant_torrents, self.args)
            for torrent in cached_torrents:
                self.torrentCacheSources.update({torrent['hash']: torrent})

    def build_cache_assist(self):
        args = self.args
        if tools.getSetting('general.autocache') == 'false':
            return
        if len(self.allTorrents) == 0:
            return
        if len(self.torrentCacheSources) > 0:
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
            yesno = tools.showDialog.yesno('%s - Cache Assist' % tools.addonName, tools.lang(32086))
            if yesno == 0:
                return
            display_list = ['%sS | %s | %s | %s' %
                            (i['seeds'], tools.color_quality(i['quality']),
                             tools.source_size_display(i['size']),
                             tools.colorString(i['release_title']))
                            for i in self.allTorrents]
            selection = tools.showDialog.select('%s - ' % tools.addonName + tools.lang(32087),
                                                display_list)
            if selection == -1:
                return
            build_list.append(self.allTorrents[selection])

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
        self.hosterDomains = resolver.Resolver().getHosterList()
        self.torrentProviders = torrent_providers
        self.hosterProviders = hoster_providers

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
            if provider_name in self.remainingProviders:
                self.remainingProviders.remove(provider_name)

        try:
            self.remainingProviders.append(provider_name)
            providerModule = __import__('%s.%s' % (provider[0], provider[1]), fromlist=[''])
            provider_source = providerModule.sources()

            if 'episodeInfo' in info:
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
                    torrent_results = provider_source.movie(info['title'], info['year'], info['imdb'])
                except:
                    torrent_results = provider_source.movie(info['title'], info['year'])

            if torrent_results is None:
                self.remainingProviders.remove(provider_name)
                return

            if self.canceled: raise Exception

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
                            torrent['hash'] = re.findall(r'btih:(.*?)\&', torrent['magnet'])[0]
                        torrent['hash'] = torrent['hash'].lower()

                        torrent['size'] = torrent.get('size', '')
                        if torrent['size'] == '':
                            torrent['size'] = 0
                        else:
                            torrent['size'] = self.torrent_filesize(torrent, info)

                        if 'provider_name_override' in torrent:
                            torrent['source'] = torrent['provider_name_override']
                        else:
                            torrent['source'] = provider_name

                    except:
                        import traceback
                        traceback.print_exc()
                        continue

                de_dup = {}

                for i in torrent_results:
                    de_dup.update({i['hash']: i})

                try:torrent_results = [value for key, value in de_dup.iteritems()]
                except:torrent_results = [value for key, value in de_dup.items()]

                start_time = time.time()

                # Check Debrid Providers for cached copies
                self.storeTorrentResults(self.trakt_id, torrent_results)

                if self.canceled: raise Exception
                cached = TorrentCacheCheck().torrentCacheCheck(torrent_results, info)

                for torrent in cached:
                    try:
                        self.torrentCacheSources.update({torrent['hash']: torrent})
                    except AttributeError:
                        break

                for torrent in torrent_results:
                    try:
                        self.allTorrents.update({torrent['hash']: torrent})
                    except AttributeError:
                        break

                tools.log('%s cache check took %s seconds' % (provider_name, time.time() - start_time))

            self.remainingProviders.remove(provider_name)

            return

        except Exception:
            import traceback
            traceback.print_exc()
            try:
                self.remainingProviders.remove(provider_name)
            except:
                pass

            return

    def getHosters(self, info, provider):
        provider_name = provider[1].upper()
        self.remainingProviders.append(provider_name.upper())

        def exit_thread():
            if provider_name in self.remainingProviders:
                self.remainingProviders.remove(provider_name)

        try:
            providerModule = __import__('%s.%s' % (provider[0], provider[1]), fromlist=[''])
            provider_sources = providerModule.source()

            if 'episodeInfo' in info:
                if not getattr(provider_sources, 'tvshow', None):
                    exit_thread()
                    return
                imdb, tvdb, title, localtitle, aliases, year = self.buildHosterVariables(info, 'tvshow')

                if self.canceled:
                    exit_thread()
                    return

                url = provider_sources.tvshow(imdb, tvdb, title, localtitle, aliases, year)

                if self.canceled:
                    exit_thread()
                    return

                imdb, tvdb, title, premiered, season, episode = self.buildHosterVariables(info, 'episode')

                if self.canceled:
                    exit_thread()
                    return

                url = provider_sources.episode(url, imdb, tvdb, title, premiered, season, episode)

                if self.canceled:
                    exit_thread()
                    return

            else:
                if not getattr(provider_sources, 'movie'):
                    exit_thread()
                    return
                imdb, title, localtitle, aliases, year = self.buildHosterVariables(info, 'movie')
                url = provider_sources.movie(imdb, title, localtitle, aliases, year)

            hostDict, hostprDict = self.buildHosterVariables(info, 'sources')

            if self.canceled:
                exit_thread()
                return

            sources = provider_sources.sources(url, hostDict, hostprDict)

            if self.canceled:
                exit_thread()
                return

            if sources is None:
                tools.log('%s: Found No Sources' % provider_name, 'info')
                exit_thread()
                return

            if 'showInfo' in info:
                title = '%s - %s' % (info['showInfo']['info']['tvshowtitle'],
                                     info['episodeInfo']['info']['title'])
            else:
                title = '%s (%s)' % (title, year)

            for source in sources:
                source['type'] = 'hoster'
                source['release_title'] = title
                source['source'] = source['source'].upper().split('.')[0]

                if 'provider' in source:
                    source['source'] = source['provider']

                if 'provider_name_override' in source:
                    source['provider'] = source['provider_name_override']
                else:
                    source['provider'] = provider_name.upper()

                source['info'] = source.get('info', [])
                source['provider_imports'] = provider

            host_domains = [host[0].lower() for provider in self.hosterDomains['premium'].iterkeys()
                     for host in self.hosterDomains['premium'][provider]]
            host_names = [host[1].lower() for provider in self.hosterDomains['premium'].iterkeys()
                     for host in self.hosterDomains['premium'][provider]]

            host_names = list(set(host_names))
            host_domains = list(set(host_domains))

            sources1 = [i for i in sources for host in host_domains if host in i['url']]
            sources2 = [i for i in sources if i['source'].lower() in host_names or i['direct']]

            sources = sources1 + sources2

            for hoster in sources:
                try:
                    self.hosterSources.update({str(hoster['url']): hoster})
                except AttributeError:
                    break

            self.remainingProviders.remove(provider_name.upper())

        except Exception as e:
            exit_thread()
            import traceback
            traceback.print_exc()
            return

        return

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

        p = sorted(p, key=lambda i: i['priority'])

        return p

    def sortSources(self, torrent_list, hoster_list):
        sort_method = int(tools.getSetting('general.sortsources'))

        sortedList = []
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
            size_limit = int(tools.getSetting('general.sizelimit')) * 1024
            torrent_list = [i for i in torrent_list if i.get('size', 0) < size_limit]

        if tools.getSetting('general.265sort') == 'true':
            torrent_list = [i for i in torrent_list if 'x265' in i['info']] + \
                           [i for i in torrent_list if 'x265' not in i['info']]

            hoster_list = [i for i in hoster_list if 'x265' in i['info']] + \
                          [i for i in hoster_list if 'x265' not in i['info']]

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
            sortedList = [i for i in sortedList if 'x265' not in i['info']]

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
        simpleInfo['episode_title'] = info['episodeInfo']['info']['originaltitle']
        simpleInfo['year'] = info['showInfo']['info']['year']
        simpleInfo['season_number'] = str(info['episodeInfo']['info']['season'])
        simpleInfo['episode_number'] = str(info['episodeInfo']['info']['episode'])
        simpleInfo['show_aliases'] = info['showInfo']['info']['showaliases']
        if '.' in simpleInfo['show_title']:
            simpleInfo['show_aliases'].append(source_utils.cleanTitle(simpleInfo['show_title'].replace('.', '')))
        simpleInfo['country'] = info['showInfo']['info']['country']
        simpleInfo['no_seasons'] = str(info['showInfo']['info']['season_count'])
        simpleInfo['absolute_number'] = str(info['episodeInfo']['info'].get('absoluteNumber', ''))
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
            imdb = info['episodeInfo']['ids']['imdb']
            tvdb = info['episodeInfo']['ids']['tvdb']
            title = info['episodeInfo']['info']['title']
            premiered = info['episodeInfo']['info']['premiered']
            season = str(info['episodeInfo']['info']['season'])
            episode = str(info['episodeInfo']['info']['episode'])
            return imdb, tvdb, title, premiered, season, episode
        elif type == 'movie':
            imdb = info['ids']['imdb']
            title = info['title']
            localtitle = info['title']
            aliases = []
            year = info['year']
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
            try: hoster_sources = [value for key, value in hoster_sources.iteritems()]
            except: hoster_sources = [value for key, value in hoster_sources.items()]
            for hoster in self.hosterDomains['premium'][provider]:
                for file in hoster_sources:
                    if hoster[1].lower() == file['source'].lower() or hoster[0].lower() in str(file['url']).lower():
                        source_list.append(file)
                        source_list[-1]['debrid_provider'] = provider
        try: self.hosterSources = [value for key, value in self.hosterSources.iteritems()]
        except: self.hosterSources = [value for key, value in self.hosterSources.items()]
        self.hosterSources += source_list

    def prem_terminate(self):
        if 'episodeInfo' in self.args:
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
                try: sources = [value for key, value in self.torrentCacheSources.iteritems()]
                except: sources = [value for key, value in self.torrentCacheSources.items()]

                # Terminating on Torrents only
                if len([i for i in sources if i['quality'] in prem_resolutions]) >= limit:
                    tools.log('Pre-emptively Terminated', 'info')
                    return True
            if type == 1:
                try: sources = [value for key, value in self.hosterSources.iteritems()]
                except: sources = [value for key, value in self.hosterSources.items()]
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
                episodes = int(info['showInfo']['info']['episode_count']) / int(info['showInfo']['info']['season_count'])
                size = size / episodes
        except:
            size = 0

        return size

    def doModal(self, args):
        try:
            if tools.getSetting('general.tempSilent') == 'true':
                self.silent = True
            try:
                self.display_style = int(tools.getSetting('general.scrapedisplay'))
            except:
                pass

            if not self.silent and self.display_style == 1:
                self.background_dialog = tools.bgProgressDialog()

            thread = threading.Thread(target=self.getSources, args=(args,))
            thread.start()

            if not self.silent:
                if self.display_style == 0:
                    tools.dialogWindow.doModal(self)
                else:
                    thread.join()
            else:
                thread.join()

            return self.return_data
        except:
            import traceback
            traceback.print_exc()
            self.close()

    def is_canceled(self):
        if not self.silent:
            if self.canceled:
                return True

    def onAction(self, action):

        id = action.getId()
        if id == 92 or id == 10:
            self.canceled = True

    def setBackground(self, url):
        if not self.silent:
            if self.display_style == 0:
                self.background.setImage(url)
        pass

    def close(self):
        if not self.silent:
            if self.display_style == 0:
                tools.dialogWindow.close(self)
            elif self.display_style == 1:
                self.background_dialog.close()

    def setText(self, text):
        if self.display_style == 0:
            self.text_label.setLabel(str(text))
        elif self.display_style == 1:
            self.background_dialog.update(self.progress, message=text)

    def setText2(self, text):
        if self.display_style == 0:
            self.text_label2.setLabel(str(text))

    def setText3(self, text):
        if self.display_style == 0:
            self.text_label3.setLabel(str(text))

    def setProgress(self):
        if not self.silent:
            if self.display_style == 0:
                progress = int(self.progress)
                if progress > 10:
                    self.perc10.setImage(self.perc_on_path)
                if progress > 20:
                    self.perc20.setImage(self.perc_on_path)
                if progress > 30:
                    self.perc30.setImage(self.perc_on_path)
                if progress > 40:
                    self.perc40.setImage(self.perc_on_path)
                if progress > 50:
                    self.perc50.setImage(self.perc_on_path)
                if progress > 60:
                    self.perc60.setImage(self.perc_on_path)
                if progress > 70:
                    self.perc70.setImage(self.perc_on_path)
                if progress > 80:
                    self.perc80.setImage(self.perc_on_path)
                if progress > 90:
                    self.perc90.setImage(self.perc_on_path)
                if progress == 100:
                    self.perc100.setImage(self.perc_on_path)
            elif self.display_style == 1:
                self.background_dialog.update(self.progress)

    def clearText(self):
        self.text_label3.setLabel('')
        self.text_label2.setLabel('')
        self.text_label.setLabel('')


class HosterCacheCheck:
    def __init__(self):
        return

        # I broke this bad, maybe let me get my shit together and sort it out at a later date lol
        # I Removed it, I don't even want to look at it.


class TorrentCacheCheck:
    def __init__(self):
        self.premiumizeCached = []
        self.realdebridCached = []
        self.threads = []

    def torrentCacheCheck(self, torrent_list, info):

        if tools.getSetting('realdebrid.enabled') == 'true' and \
                        tools.getSetting('rd.torrents') == 'true':
            self.threads.append(
                threading.Thread(target=self.realdebridWorker, args=(copy.deepcopy(torrent_list), info)))

        if tools.getSetting('premiumize.enabled') == 'true' and \
                        tools.getSetting('premiumize.torrents') == 'true':
            self.threads.append(threading.Thread(target=self.premiumizeWorker, args=(copy.deepcopy(torrent_list),)))

        for i in self.threads:
            i.start()
        for i in self.threads:
            i.join()

        cachedList = self.realdebridCached + self.premiumizeCached
        return cachedList

    def realdebridWorker(self, torrent_list, info):
        try:
            cache_list = []

            hash_list = [i['hash'] for i in torrent_list]

            if len(hash_list) == 0:
                return

            realDebridCache = real_debrid.RealDebrid().checkHash(hash_list)

            for i in torrent_list:
                try:
                    if 'rd' in realDebridCache[i['hash']] and len(realDebridCache[i['hash']]['rd']) >= 1:
                        if 'episodeInfo' in info:
                            episodeStrings, seasonStrings = source_utils.torrentCacheStrings(info)
                            for storage_variant in realDebridCache[i['hash']]['rd']:
                                keys = list(storage_variant.keys())
                                for key in keys:
                                    filename = storage_variant[key]['filename']
                                    if any(source_utils.cleanTitle(episodeString) in source_utils.cleanTitle(filename)
                                           for episodeString in episodeStrings):
                                        if any(filename.lower().endswith(extension) for extension in
                                               source_utils.COMMON_VIDEO_EXTENSIONS):
                                            cache_list.append(i)
                                            cache_list[-1]['debrid_provider'] = 'real_debrid'
                                            break
                        else:
                            if len(realDebridCache[i['hash']]['rd']) == 1:
                                i['debrid_provider'] = 'real_debrid'
                                cache_list.append(i)

                except:
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
            premiumizeCache = premiumize.PremiumizeBase().hash_check(hash_list)
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
