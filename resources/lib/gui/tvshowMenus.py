# -*- coding: utf-8 -*-

import datetime
import json
import sys
from threading import Thread

from resources.lib.common import tools
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.modules import database
from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
from resources.lib.modules.trakt_sync.hidden import TraktSyncDatabase as HiddenDatabase
from resources.lib.common import maintenance

try:
    from Queue import Queue
except:
    from queue import Queue

sysaddon = sys.argv[0]
try:
    syshandle = int(sys.argv[1])
except:
    syshandle = ''
trakt = TraktAPI()
language_code = tools.get_language_code()


class Menus:
    def __init__(self):
        self.itemList = []
        self.threadList = []
        self.direct_episode_threads = []
        self.title_appends = tools.getSetting('general.appendtitles')
        self.task_queue = Queue(40)

    ######################################################
    # MENUS
    ######################################################

    def onDeckShows(self):
        hidden_shows = HiddenDatabase().get_hidden_items('progress_watched', 'shows')
        trakt_list = trakt.json_response('sync/playback/episodes?extended=full', limit=True)
        if trakt_list is None:
            return
        trakt_list = [i for i in trakt_list if i['show']['ids']['trakt'] not in hidden_shows]
        trakt_list = sorted(trakt_list, key=lambda i: tools.datetime_workaround(i['paused_at'][:19],
                                                                                format="%Y-%m-%dT%H:%M:%S",
                                                                                date_only=False), reverse=True)
        filter_list = []
        showList = []
        sort_list = []
        for i in trakt_list:
            if i['show']['ids']['trakt'] not in filter_list:
                if int(i['progress']) != 0:
                    showList.append(i)
                    filter_list.append(i['show']['ids']['trakt'])
                    sort_list.append(i['show']['ids']['trakt'])

        sort = {'type': 'showInfo', 'id_list': sort_list}
        self.mixedEpisodeBuilder(showList, sort=sort)
        tools.closeDirectory('tvshows')

    def discoverShows(self):

        tools.addDirectoryItem(tools.lang(32007), 'showsPopular&page=1', '', '')
        if tools.getSetting('trakt.auth') is not '':
            tools.addDirectoryItem(tools.lang(32008), 'showsRecommended', '', '')
        tools.addDirectoryItem(tools.lang(32009), 'showsTrending&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32067), 'showsNew', '', '')
        tools.addDirectoryItem(tools.lang(32010), 'showsPlayed&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32011), 'showsWatched&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32012), 'showsCollected&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32013), 'showsAnticipated&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32014), 'showsUpdated&page=1', '', '')
        tools.addDirectoryItem(tools.lang(40121), 'showsNetworks', '', '')
        tools.addDirectoryItem(tools.lang(40123), 'showYears', '', '')
        tools.addDirectoryItem(tools.lang(32062), 'tvGenres', '', '')
        # show genres is now labeled as tvGenres to support genre icons in skins
        if tools.getSetting('searchHistory') == 'false':
            tools.addDirectoryItem(tools.lang(32016), 'showsSearch', '', '')
        else:
            tools.addDirectoryItem(tools.lang(32016), 'showsSearchHistory', '', '')
        tools.closeDirectory('addons')

    def myShows(self):
        tools.addDirectoryItem(tools.lang(32063), 'onDeckShows', None, None)
        tools.addDirectoryItem(tools.lang(32017), 'showsMyCollection', '', '')
        tools.addDirectoryItem(tools.lang(32018), 'showsMyWatchlist', '', '')
        tools.addDirectoryItem('Next Up', 'showsNextUp', '', '')
        tools.addDirectoryItem('Unfinished Shows in Collection', 'showsMyProgress', '', '')
        tools.addDirectoryItem('Recent Episodes', 'showsMyRecentEpisodes', '', '')
        tools.addDirectoryItem('My Show Lists', 'myTraktLists&actionArgs=shows', '', '')
        tools.closeDirectory('addons')

    def myShowCollection(self):
        trakt_list = TraktSyncDatabase().get_collected_episodes()
        trakt_list = [i for i in trakt_list if i is not None]
        trakt_list = list(set([i['show_id'] for i in trakt_list]))
        trakt_list = [{'ids': {'trakt': i}} for i in trakt_list]
        trakt_list = [i for i in trakt_list if i is not None]
        if trakt_list is None:
            return
        self.showListBuilder(trakt_list)
        tools.closeDirectory('tvshows', sort='title')

    def myShowWatchlist(self):
        trakt_list = trakt.json_response('users/me/watchlist/shows?extended=full', limit=False)
        if trakt_list is None:
            return
        try:
            sort_by = trakt.response_headers['X-Sort-By']
            sort_how = trakt.response_headers['X-Sort-How']
            trakt_list = trakt.sort_list(sort_by, sort_how, trakt_list, 'show')
        except:
            tools.log('Failed to sort trakt list by response headers')
            pass
        self.showListBuilder(trakt_list)
        tools.closeDirectory('tvshows')

    def myProgress(self):

        collected_episodes = TraktSyncDatabase().get_collected_episodes()
        collection = list(set([i['show_id'] for i in collected_episodes]))

        unfinished = []
        watched_episodes = TraktSyncDatabase().get_watched_episodes()

        if len(collection) == 0:
            return

        for show_id in collection:
            collected_episodes = [i for i in collected_episodes if i['show_id'] == show_id]
            show_watched_episodes = [i for i in watched_episodes if i['show_id'] == show_id]
            if len(show_watched_episodes) >= len(collected_episodes):
                unfinished.append({'ids': {'trakt': show_id}})

        self.showListBuilder(unfinished)
        tools.closeDirectory('tvshows', sort='title')

    def newShows(self):

        hidden = HiddenDatabase().get_hidden_items('recommendations', 'shows')
        datestring = datetime.datetime.today() - datetime.timedelta(days=29)
        trakt_list = database.get(trakt.json_response, 12, 'calendars/all/shows/new/%s/30?'
                                                           'extended=full'
                                                           '&language=%s' %
                                  (datestring.strftime('%d-%m-%Y'), language_code))

        if trakt_list is None:
            return
        # For some reason trakt messes up their list and spits out tons of duplicates so we filter it
        duplicate_filter = []
        temp_list = []
        for i in trakt_list:
            if not i['show']['ids']['tvdb'] in duplicate_filter:
                duplicate_filter.append(i['show']['ids']['tvdb'])
                temp_list.append(i)

        trakt_list = temp_list

        trakt_list = [i for i in trakt_list if i['show']['ids']['trakt'] not in hidden]

        if len(trakt_list) > 40:
            trakt_list = trakt_list[:40]
        self.showListBuilder(trakt_list)
        tools.closeDirectory('tvshows')

    def myNextUp(self, ):

        hidden_shows = HiddenDatabase().get_hidden_items('progress_watched', 'shows')

        watched = TraktSyncDatabase().get_watched_shows()
        watched = [i['trakt_id'] for i in watched]
        watched = [i for i in watched if i not in hidden_shows]

        self._start_queue_workers()
        for i in watched:
            self.task_queue.put((self.traktProgressWorker, (i,)), True)
        self._finish_queue_workers()

        self.threadList = []
        next_up = self.itemList
        next_up = [i for i in next_up if i is not None]
        if len(next_up) == 0:
            return
        self.itemList = []
        next_list = []

        if tools.getSetting('nextup.sort') == '1':
            next_up = sorted(next_up, key=lambda k: k['last_watched_at'], reverse=True)
            sort = {'type': 'showInfo', 'id_list': [i['show']['ids']['trakt'] for i in next_up]}
        else:
            sort = None

        for i in next_up:
            try:
                next_episode = i['next_episode']
                if next_episode is None:
                    continue
                next_list.append({'show': i['show'], 'episode': i['next_episode']})
            except:
                import traceback
                traceback.print_exc()
                pass

        self.mixedEpisodeBuilder(next_list, sort=sort, hide_watched=True)
        tools.closeDirectory('episodes')

    def myRecentEpisodes(self):
        hidden_shows = HiddenDatabase().get_hidden_items('calendar', 'shows')
        datestring = datetime.datetime.today() - datetime.timedelta(days=13)
        trakt_list = database.get(trakt.json_response, 12, 'calendars/my/shows/%s/14?extended=full' %
                                  datestring.strftime('%d-%m-%Y'))
        if trakt_list is None:
            return
        trakt_list = [i for i in trakt_list if i['show']['ids']['trakt'] not in hidden_shows]
        self.mixedEpisodeBuilder(trakt_list)
        tools.closeDirectory('episodes')

    def showsNetworks(self):
        trakt_list = database.get(trakt.json_response, 24, 'networks')

        if trakt_list is None:
            return
        list_items = []
        for i in trakt_list:
            list_items.append(tools.addDirectoryItem(i['name'], 'showsNetworkShows&actionArgs=%s&page=1' % i['name'],
                                                     '', '', bulk_add=True))
        tools.addMenuItems(syshandle, list_items, len(list_items))
        tools.closeDirectory('addons')

    def showsNetworkShows(self, network, page):

        trakt_list = database.get(trakt.json_response, 24, 'shows/trending?networks=%s&page=%s' % (network, page))

        if trakt_list is None:
            return

        self.showListBuilder(trakt_list)

        if len(trakt_list) == int(tools.getSetting('item.limit')):
            tools.addDirectoryItem(tools.lang(32019), 'showsNetworkShows&actionArgs=%s&page=%s' %
                                   (network, int(page) + 1), '', '')

        tools.closeDirectory('tvshows')

    def showsPopular(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'shows/popular?page=%s&extended=full' % page)

        if trakt_list is None:
            return

        self.showListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'showsPopular&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsRecommended(self):
        trakt_list = database.get(trakt.json_response, 12, 'recommendations/shows?extended=full',
                                  limit=True, limitOverride=100)
        if trakt_list is None:
            return
        self.showListBuilder(trakt_list)
        tools.closeDirectory('tvshows')

    def showsTrending(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'shows/trending?page=%s&extended=full' % page)
        if trakt_list is None:
            return
        self.showListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'showsTrending&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsPlayed(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'shows/played?page=%s&extended=full' % page)
        if trakt_list is None:
            return
        self.showListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'showsPlayed&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsWatched(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'shows/watched?page=%s&extended=full' % page)
        if trakt_list is None:
            return
        self.showListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'showsWatched&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsCollected(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'shows/collected?page=%s&extended=full' % page)
        if trakt_list is None:
            return
        self.showListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'showsCollected&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsAnticipated(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'shows/anticipated?page=%s&extended=full&language=%s'
                                  % (page, language_code))
        if trakt_list is None:
            return
        self.showListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'showsAnticipated&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsUpdated(self, page):
        import datetime
        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime('%Y-%m-%d')
        trakt_list = database.get(trakt.json_response, 12, 'shows/updates/%s?page=%s&extended=full' % (date, page))
        if trakt_list is None:
            return
        self.showListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'showsUpdated&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showSearchHistory(self):
        history = database.getSearchHistory('show')
        tools.addDirectoryItem('New Show Search...', 'showsSearch', '', '')
        tools.addDirectoryItem('Clear Search History...', 'clearSearchHistory', '', '', isFolder=True)

        for i in history:
            tools.addDirectoryItem(i, 'showsSearch&actionArgs=%s' % i, '', '')
        tools.closeDirectory('addon')

    def showsSearch(self, actionArgs):

        if actionArgs == None:
            k = tools.showKeyboard('', tools.lang(32016))
            k.doModal()
            query = (k.getText() if k.isConfirmed() else None)
            if query == None or query == '':
                return
        else:
            query = actionArgs

        database.addSearchHistory(query, 'show')
        query = tools.deaccentString(query)
        query = tools.quote_plus(query)

        trakt_list = trakt.json_response('search/show?query=%s&extended=full' % query, limit=True)
        if trakt_list is None:
            return

        self.showListBuilder(trakt_list)
        tools.closeDirectory('tvshows')

    def showSeasons(self, args):

        show_info = json.loads(tools.unquote(args))

        self.seasonListBuilder(show_info['ids']['trakt'])

        tools.closeDirectory('seasons')

    def seasonEpisodes(self, args):

        args = json.loads(tools.unquote(args))

        show_id = args['showInfo']['ids']['trakt']
        season_number = args['seasonInfo']['info']['season']

        self.episodeListBuilder(show_id, season_number)
        tools.closeDirectory('episodes', sort='episode')

    def showGenres(self):
        tools.addDirectoryItem(tools.lang(32065), 'showGenresGet', '', '', isFolder=True)
        genres = database.get(trakt.json_response, 24, 'genres/shows')

        if genres is None:
            return

        for i in genres:
            tools.addDirectoryItem(i['name'], 'showGenresGet&actionArgs=%s' % i['slug'], '', '', isFolder=True)
        tools.closeDirectory('addons')

    def showGenreList(self, args, page):
        if page is None:
            page = 1

        if args is None:
            genre_display_list = []
            genre_string = ''
            genres = database.get(trakt.json_response, 24, 'genres/shows')

            for genre in genres:
                genre_display_list.append(genre['name'])
            genre_multiselect = tools.showDialog.multiselect(tools.addonName + ": Genre Selection", genre_display_list)

            if genre_multiselect is None: return
            for selection in genre_multiselect:
                genre_string += ', %s' % genres[selection]['slug']
            genre_string = genre_string[2:]

        else:
            genre_string = args

        page = int(page)
        trakt_list = database.get(trakt.json_response, 12,
                                  'shows/popular?genres=%s&page=%s&extended=full' % (genre_string, page))
        if trakt_list is None:
            return

        self.showListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019),
                               'showGenresGet&actionArgs=%s&page=%s' % (genre_string, page + 1), None, None)
        tools.closeDirectory('tvshows')

    def showsRelated(self, args):
        trakt_list = database.get(trakt.json_response, 12, 'shows/%s/related?extended=full' % args)
        if trakt_list is None:
            return

        self.showListBuilder(trakt_list)
        tools.closeDirectory('tvshows')

    def showYears(self, year=None, page=None):
        if year is None:
            current_year = int(tools.datetime_workaround(datetime.datetime.today().strftime('%Y-%m-%d')).year)
            all_years = reversed([year for year in range(1900, current_year+1)])
            menu_items = []
            for year in all_years:
                menu_items.append(tools.addDirectoryItem(str(year), 'showYears&actionArgs=%s' % year, '', '',
                                  bulk_add=True))
            tools.addMenuItems(syshandle, menu_items, len(menu_items))
            tools.closeDirectory('tvshows')
        else:
            if page is None:
                page = 1

            trakt_list = trakt.json_response('shows/popular?years=%s&page=%s' % (year, page))
            self.showListBuilder(trakt_list)
            tools.addDirectoryItem(tools.lang(32019),
                                   'showYears&actionArgs=%s&page=%s' % (year, page + 1), None, None)
            tools.closeDirectory('tvshows')


    ######################################################
    # MENU TOOLS
    ######################################################

    def seasonListBuilder(self, show_id, smartPlay=False):

        self.itemList = TraktSyncDatabase().get_season_list(show_id)

        self.itemList = [x for x in self.itemList if x is not None and 'info' in x]

        self.itemList = sorted(self.itemList, key=lambda k: k['info']['season'])

        hide_specials = False

        if tools.getSetting('general.hideSpecials') == 'true':
            hide_specials = True

        item_list = []

        for item in self.itemList:

            try:
                if hide_specials and int(item['info']['season']) == 0:
                    continue

                if self.date_delay(item['info']):
                    continue

                args = {'showInfo': {}, 'seasonInfo': {}}

                action = 'seasonEpisodes'
                args['showInfo'] = item['showInfo']
                args['seasonInfo']['info'] = item['info']
                args['seasonInfo']['art'] = item['art']
                args['seasonInfo']['ids'] = item['ids']
                item['trakt_object']['show_id'] = item['showInfo']['ids']['trakt']
                name = item['info']['season_title']
                args = tools.quote(json.dumps(args, sort_keys=True))
            except:
                import traceback
                traceback.print_exc()
                continue

            if smartPlay is True:
                return args

            cm = []
            if tools.getSetting('trakt.auth') != '':
                cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                           % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

            if tools.context_addon():
                cm = []

            item_list.append(tools.addDirectoryItem(name, action, item['info'], item['art'], cm=cm, isFolder=True,
                                                    isPlayable=False, actionArgs=args, set_ids=item['ids'],
                                                    bulk_add=True))

        tools.addMenuItems(syshandle, item_list, len(item_list))

    def episodeListBuilder(self, show_id, season_number, smartPlay=False):

        try:
            item_list = []

            self.itemList = TraktSyncDatabase().get_season_episodes(show_id, season_number)
            self.itemList = [x for x in self.itemList if x is not None and 'info' in x]

            try:
                self.itemList = sorted(self.itemList, key=lambda k: k['info']['episode'])
            except:
                pass

            for item in self.itemList:

                cm = []

                try:
                    args = {'showInfo': {}, 'episodeInfo': {}}

                    if tools.getSetting('smartplay.playlistcreate') == 'true' and smartPlay is False:
                        action = 'smartPlay'
                        playable = False
                    else:
                        playable = True
                        action = 'getSources'

                    if self.date_delay(item['info']):
                        continue

                    args['showInfo'] = item['showInfo']
                    args['episodeInfo']['info'] = item['info']
                    args['episodeInfo']['art'] = item['art']
                    args['episodeInfo']['ids'] = item['ids']
                    name = item['info']['title']

                    args = tools.quote(json.dumps(args, sort_keys=True))

                except:
                    import traceback
                    traceback.print_exc()
                    continue


                cm.append((tools.lang(33022),
                           'PlayMedia(%s?action=getSources&seren_reload=true&actionArgs=%s)' % (sysaddon, args)))

                cm.append((tools.lang(32066),
                           'PlayMedia(%s?action=getSources&source_select=true&actionArgs=%s)' % (sysaddon, args)))

                if tools.getSetting('trakt.auth') != '':
                    cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                               % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

                if tools.context_addon():
                    cm = []

                if tools.getSetting('premiumize.enabled') == 'true' and tools.getSetting('premiumize.pin') != '':
                    cm.append((tools.lang(32068),
                               'XBMC.RunPlugin(%s?action=filePicker&actionArgs=%s)' % (sysaddon, args)))

                item_list.append(tools.addDirectoryItem(name, action, item['info'], item['art'], isFolder=False,
                                                        isPlayable=playable, actionArgs=args, bulk_add=True,
                                                        set_ids=item['ids'], cm=cm))

            if smartPlay is True:
                return item_list
            else:
                tools.addMenuItems(syshandle, item_list, len(item_list))

        except:
            import traceback
            traceback.print_exc()

    def mixedEpisodeBuilder(self, trakt_list, sort=None, hide_watched=False, smartPlay=False):

        self.threadList = []

        try:
            if len(trakt_list) == 0: return

            self.itemList = TraktSyncDatabase().get_episode_list(trakt_list)

            self.itemList = [x for x in self.itemList if x is not None and 'info' in x]
            self.itemList = [i for i in self.itemList if 'info' in i and i['info'].get('premiered', None) is not None]
            if sort is None:
                self.itemList = sorted(self.itemList, key=lambda i: tools.datetime_workaround(i['info']['premiered']),
                                       reverse=True)
            elif sort is not False:
                sort_list = []
                for trakt_id in sort['id_list']:
                    try:
                        item = [i for i in self.itemList if i[sort['type']]['ids']['trakt'] == trakt_id][0]
                        sort_list.append(item)
                    except:
                        continue
                self.itemList = sort_list

            item_list = []

            for item in self.itemList:
                if item is None:
                    continue
                try:
                    currentDate = datetime.datetime.today().date()
                    airdate = item['info']['premiered']
                    if airdate == '':
                        continue
                    airdate = tools.datetime_workaround(airdate)
                    if airdate > currentDate:
                        continue
                except:
                    import traceback
                    traceback.print_exc()
                    pass

                if item['info'].get('title', '') == '':
                    continue

                if hide_watched and item['info']['playcount'] != 0:
                    continue

                if self.date_delay(item['info']):
                    continue

                cm = []

                try:
                    args = {'showInfo': {}, 'episodeInfo': {}}

                    if tools.getSetting('smartplay.playlistcreate') == 'true' and not smartPlay:
                        action = 'smartPlay'
                        playable = False
                    else:
                        playable = True
                        action = 'getSources'

                    args['showInfo'] = item['showInfo']
                    args['episodeInfo']['info'] = item['info']
                    args['episodeInfo']['art'] = item['art']
                    args['episodeInfo']['ids'] = item['ids']

                    name = tools.display_string(item['info']['title'])

                    if self.title_appends == 'true':
                        name = "%s: %sx%s %s" % (tools.colorString(args['showInfo']['info']['tvshowtitle']),
                                                 tools.display_string(item['info']['season']).zfill(2),
                                                 tools.display_string(item['info']['episode']).zfill(2),
                                                 tools.display_string(item['info']['title']))

                    args = tools.quote(json.dumps(args, sort_keys=True))

                    cm.append((tools.lang(32069),
                               'XBMC.Container.Update(%s?action=showSeasons&actionArgs=%s)' %
                               (sysaddon, tools.quote(json.dumps(str(item['showInfo']))))))

                    cm.append((tools.lang(32066),
                               'PlayMedia(%s?action=getSources&source_select=true&actionArgs=%s)' % (sysaddon, args)))

                    cm.append((tools.lang(33022),
                               'PlayMedia(%s?action=getSources&seren_reload=true&actionArgs=%s)' % (sysaddon, args)))

                    if tools.getSetting('trakt.auth') != '':
                        cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                                   % (sysaddon, tools.quote(json.dumps(str(item['trakt_object']))))))

                    if tools.context_addon():
                        cm = []

                    if tools.getSetting('premiumize.enabled') == 'true' and tools.getSetting('premiumize.pin') != '':
                        cm.append((tools.lang(32068),
                                   'XBMC.RunPlugin(%s?action=filePicker&actionArgs=%s)' % (sysaddon, args)))

                    item['info']['title'] = item['info']['originaltitle'] = name

                    item_list.append(tools.addDirectoryItem(name, action, item['info'], item['art'], isFolder=False,
                                                            isPlayable=playable, actionArgs=args, bulk_add=True,
                                                            set_ids=item['ids'], cm=cm))


                except:
                    import traceback
                    traceback.print_exc()
                    continue

            if smartPlay is True:
                return item_list
            else:
                tools.addMenuItems(syshandle, item_list, len(item_list))

        except:
            import traceback
            traceback.print_exc()

    def showListBuilder(self, trakt_list, forceResume=False, info_only=False):

        try:
            if len(trakt_list) == 0:
                return
        except:
            return

        if 'show' in trakt_list[0]:
            trakt_list = [i['show'] for i in trakt_list]

        show_ids = [i['ids']['trakt'] for i in trakt_list]

        self.itemList = TraktSyncDatabase().get_show_list(show_ids)
        self.itemList = [x for x in self.itemList if x is not None and 'info' in x]
        self.itemList = tools.sort_list_items(self.itemList, trakt_list)

        item_list = []

        for item in self.itemList:
            try:
                args = {}
                cm = []

                # Add Arguments to pass with items
                args['ids'] = item['ids']
                args['info'] = item['info']
                args['art'] = item['art']

                name = tools.display_string(item['info']['tvshowtitle'])
                args = tools.quote(json.dumps(args, sort_keys=True))

                if info_only == True:
                    return args

                if self.date_delay(item['info']):
                    continue

                if 'setCast' in item:
                    set_cast = item['setCast']
                else:
                    set_cast = False

                if tools.getSetting('smartplay.clickresume') == 'true' or forceResume is True:
                    action = 'smartPlay'
                else:
                    action = 'showSeasons'

                # Context Menu Items

                cm.append((tools.lang(32070),
                           'XBMC.PlayMedia(%s?action=shufflePlay&actionArgs=%s)' % (sysaddon, args)))

                cm.append((tools.lang(32020),
                           'Container.Update(%s?action=showsRelated&actionArgs=%s)' % (sysaddon, item['ids']['trakt'])))

                cm.append((tools.lang(32069),
                           'XBMC.Container.Update(%s?action=showSeasons&actionArgs=%s)' % (sysaddon, args)))

                if tools.getSetting('trakt.auth') != '':
                    cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                               % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

                if tools.context_addon():
                    cm = []


            except:
                import traceback
                traceback.print_exc()
                continue

            item_list.append(tools.addDirectoryItem(name, action, item['info'], item['art'], cm=cm, isFolder=True,
                                                    isPlayable=False, actionArgs=args, bulk_add=True, set_cast=set_cast,
                                                    set_ids=item['ids']))

        tools.addMenuItems(syshandle, item_list, len(item_list))


    def traktProgressWorker(self, show_id):
        try:
            progress = TraktAPI().json_response('shows/%s/progress/watched?extended=full' % show_id)
            progress.update({'show': {'ids': {'trakt': show_id}}})
            self.itemList.append(progress)
        except:
            self.itemList.append(None)

    def runThreads(self, join=True):
        for thread in self.threadList:
            thread.start()

        if join == True:
            for thread in self.threadList:
                thread.join()

    def _start_queue_workers(self):

        self.queue_finished = False

        for i in range(40):
            self.threadList.append(Thread(target=self._queue_worker))

        for i in self.threadList:
            i.start()

    def _finish_queue_workers(self):

        self.queue_finished = True

        for i in self.threadList:
            i.join()

        self.threadList = []

    def _queue_worker(self):
        while not self.task_queue.empty() or not self.queue_finished:
            try:
                target = self.task_queue.get(timeout=3)
            except:
                continue
            try:
                target[0](*target[1])
            except:
                pass

    def date_delay(self, info):
        try:
            if tools.getSetting('general.datedelay') == 'true':
                air_date = info['aired']
                air_date = tools.datetime_workaround(air_date, '%Y-%m-%d', date_only=True)
                air_date += datetime.timedelta(days=1)
                if air_date > datetime.date.today():
                    print('Skipping %s - %s.%s' % (info['tvshowtitle'], info['season'], info['episode']))
                    return True
                else:
                    return False
            else:
                return False
        except:
            return False