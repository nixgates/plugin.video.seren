# -*- coding: utf-8 -*-

import copy
import datetime
import json
import sys
from threading import Thread

from resources.lib.common import tools
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.indexers.tvdb import TVDBAPI
from resources.lib.modules import database

sysaddon = sys.argv[0]
syshandle = int(sys.argv[1])
trakt = TraktAPI()
language_code = tools.get_language_code()

class Menus:
    def __init__(self):
        self.itemList = []
        self.threadList = []
        self.direct_episode_threads = []

    ######################################################
    # MENUS
    ######################################################

    def onDeckShows(self):
        hidden_shows = trakt.get_trakt_hidden_items('watched')['shows']
        traktList = trakt.json_response('sync/playback/episodes?extended=full', limit=True)
        if traktList is None:
            return
        traktList = [i for i in traktList if i['show']['ids']['trakt'] not in hidden_shows]
        traktList = sorted(traktList, key=lambda i: tools.datetime_workaround(i['paused_at'][:19],
                                                                              format="%Y-%m-%dT%H:%M:%S",
                                                                              date_only=False), reverse=True)
        filter_list = []
        showList = []
        sort_list = []
        for i in traktList:
            if i['show']['ids']['trakt'] not in filter_list:
                if int(i['progress']) != 0:
                    showList.append(i)
                    filter_list.append(i['show']['ids']['trakt'])
                    sort_list.append(i['show']['ids']['trakt'])

        sort = {'type': 'showInfo', 'id_list': sort_list}
        self.directToEpisodeBuilder(showList, sort=sort)
        tools.closeDirectory('tvshows')

    def discoverShows(self):

        tools.addDirectoryItem(tools.lang(32007).encode('utf-8'), 'showsPopular&page=1', '', '')
        if tools.getSetting('trakt.auth') is not '':
            tools.addDirectoryItem(tools.lang(32008).encode('utf-8'), 'showsRecommended', '', '')
        tools.addDirectoryItem(tools.lang(32009).encode('utf-8'), 'showsTrending&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32067).encode('utf-8'), 'showsNew', '', '')
        tools.addDirectoryItem(tools.lang(32010).encode('utf-8'), 'showsPlayed&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32011).encode('utf-8'), 'showsWatched&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32012).encode('utf-8'), 'showsCollected&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32013).encode('utf-8'), 'showsAnticipated&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32014).encode('utf-8'), 'showsUpdated&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32062).encode('utf-8'), 'showGenres', '', '')
        tools.addDirectoryItem(tools.lang(32016).encode('utf-8'), 'showsSearch', '', '')
        tools.closeDirectory('addons', cacheToDisc=True)

    def myShows(self):
        tools.addDirectoryItem(tools.lang(32063).encode('utf-8'), 'onDeckShows', None, None)
        tools.addDirectoryItem(tools.lang(32017).encode('utf-8'), 'showsMyCollection', '', '')
        tools.addDirectoryItem(tools.lang(32018).encode('utf-8'), 'showsMyWatchlist', '', '')
        tools.addDirectoryItem('Next Up', 'showsNextUp', '', '')
        tools.addDirectoryItem('Unfinished Shows in Collection', 'showsMyProgress', '', '')
        tools.addDirectoryItem('Recent Episodes', 'showsMyRecentEpisodes', '', '')
        tools.addDirectoryItem('My Show Lists', 'myTraktLists&actionArgs=shows', '', '')
        tools.closeDirectory('addons', cacheToDisc=True)

    def myShowCollection(self):
        traktList = trakt.json_response('users/me/collection/shows?extended=full', limit=False)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows', sort='title')

    def myShowWatchlist(self):
        traktList = trakt.json_response('users/me/watchlist/shows?extended=full', limit=False)
        if traktList is None:
            return
        try:
            sort_by = trakt.response_headers['X-Sort-By']
            sort_how = trakt.response_headers['X-Sort-How']
            traktList = trakt.sort_list(sort_by, sort_how, traktList, 'show')
        except:
            tools.log('Failed to sort trakt list by response headers')
            pass
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows')

    def myProgress(self):
        self.threadList = []
        collection = database.get(trakt.json_response, 12, 'users/me/collection/shows?extended=full', limit=False)
        if collection is None:
            return
        for i in collection:
            self.threadList.append(Thread(target=self.traktProgressWorker, args=(i,)))
        self.runThreads()
        progress_report = self.itemList
        self.itemList = []
        unfinished_shows = [i for i in progress_report
                            if i is not None if i['progress']['aired'] > i['progress']['completed']]
        self.showListBuilder(unfinished_shows)
        tools.closeDirectory('tvshows', sort='title')

    def newShows(self):

        hidden = trakt.get_trakt_hidden_items('recommendations')['shows']
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
        hidden_shows = trakt.get_trakt_hidden_items('watched')['shows']
        self.threadList = []
        watched = trakt.json_response('users/me/watched/shows?extended=full', limit=False)
        watched = sorted(watched, key=lambda i: tools.datetime_workaround(i['last_watched_at'][:19],
                                                                          format="%Y-%m-%dT%H:%M:%S",
                                                                          date_only=False), reverse=True)

        if watched is None:
            return
        watch_list = []
        for i in watched:
            if i is not None:
                watch_list.append(i)

        watched = [i for i in watched if i['show']['ids']['trakt'] not in hidden_shows]
        if tools.getSetting('nextup.sort') == '1':
            watched = sorted(watched, key=lambda i: tools.datetime_workaround(i['last_watched_at'][:19],
                                                                              format="%Y-%m-%dT%H:%M:%S",
                                                                              date_only=False), reverse=True)

            sort = {'type': 'showInfo', 'id_list': [i['show']['ids']['trakt'] for i in watched]}
        else:
            sort = None

        for i in watched:
            self.threadList.append(Thread(target=self.traktProgressWorker, args=(i,)))
        self.runThreads()
        self.threadList = []
        next_up = self.itemList

        self.itemList = []
        next_list = []
        for i in next_up:
            try:
                if i['progress']['next_episode'] is not None:
                    next_list.append(i)
            except:
                pass
        next_list = next_list[:50]
        build_list = []

        for i in next_list:
            item = {'show': i['show'], 'episode': i['progress']['next_episode']}
            build_list.append(item)

        self.directToEpisodeBuilder(build_list, sort=sort)

        tools.closeDirectory('episodes')

    def myRecentEpisodes(self):
        hidden_shows = trakt.get_trakt_hidden_items('calendar')['shows']
        datestring = datetime.datetime.today() - datetime.timedelta(days=13)
        trakt_list = database.get(trakt.json_response, 12, 'calendars/my/shows/%s/14?extended=full' %
                                  datestring.strftime('%d-%m-%Y'))
        if trakt_list is None:
            return
        trakt_list = [i for i in trakt_list if i['show']['ids']['trakt'] not in hidden_shows]
        self.directToEpisodeBuilder(trakt_list)
        tools.closeDirectory('episodes')

    def showsPopular(self, page):

        traktList = database.get(trakt.json_response, 12, 'shows/popular?page=%s&extended=full' % page)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'showsPopular&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsRecommended(self):

        traktList = database.get(trakt.json_response, 12, 'recommendations/shows?extended=full',
                                 limit=True, limitOverride=100)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows')

    def showsTrending(self, page):
        traktList = database.get(trakt.json_response, 12, 'shows/trending?page=%s&extended=full' % page)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'showsTrending&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsPlayed(self, page):
        traktList = database.get(trakt.json_response, 12, 'shows/played?page=%s&extended=full' % page)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'showsPlayed&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsWatched(self, page):
        traktList = database.get(trakt.json_response, 12, 'shows/watched?page=%s&extended=full' % page)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'showsWatched&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsCollected(self, page):
        traktList = database.get(trakt.json_response, 12, 'shows/collected?page=%s&extended=full' % page)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'showsCollected&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows', sort='title')

    def showsAnticipated(self, page):
        traktList = database.get(trakt.json_response, 12, 'shows/anticipated?page=%s&extended=full&language=%s'
                                 % (page, language_code))
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'showsAnticipated&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsUpdated(self, page):
        import datetime
        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime('%Y-%m-%d')
        traktList = database.get(trakt.json_response, 12, 'shows/updates/%s?page=%s&extended=full' % (date, page))
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'showsUpdated&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows')

    def showsSearch(self, actionArgs):

        if actionArgs == None:
            k = tools.showKeyboard('', tools.lang(32016).encode('utf-8'))
            k.doModal()
            query = (k.getText() if k.isConfirmed() else None)
            if query == None or query == '':
                return
        else:
            query = actionArgs
        query = tools.deaccentString(query)
        query = tools.quote_plus(query)
        traktList = trakt.json_response('search/show?query=%s&extended=full' % query, limit=True)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows')

    def showSeasons(self, args):

        showInfo = json.loads(tools.unquote(args))

        traktList = database.get(trakt.json_response, 12, 'shows/%s/seasons?extended=full' % showInfo['ids']['trakt'])
        if traktList is None:
            return

        self.seasonListBuilder(traktList, showInfo)

        tools.closeDirectory('seasons')

    def seasonEpisodes(self, args):

        args = json.loads(tools.unquote(args))

        traktList = database.get(trakt.json_response, 6, 'shows/%s/seasons/%s?extended=full' %
                                 (args['showInfo']['ids']['trakt'],
                                  args['seasonInfo']['info']['season']))
        if traktList is None:
            return

        self.episodeListBuilder(traktList, args)
        tools.closeDirectory('episodes', sort='episode')

    def showGenres(self):
        tools.addDirectoryItem(tools.lang(32065).encode('utf-8'), 'showGenresGet', '', '', isFolder=True)
        genres = database.get(trakt.json_response, 24, 'genres/shows')
        if genres is None:
            return
        for i in genres:
            tools.addDirectoryItem(i['name'], 'showGenresGet&actionArgs=%s' % i['slug'], '', '', isFolder=True)
        tools.closeDirectory('addons', cacheToDisc=True)

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
        traktList = database.get(trakt.json_response, 12,
                                 'shows/popular?genres=%s&page=%s&extended=full' % (genre_string, page))
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'),
                               'showGenresGet&actionArgs=%s&page=%s' % (genre_string, page + 1), None, None)
        tools.closeDirectory('tvshows')

    def showsRelated(self, args):
        traktList = database.get(trakt.json_response, 12, 'shows/%s/related?extended=full' % args)
        if traktList is None:
            return
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows')

    ######################################################
    # MENU TOOLS
    ######################################################

    def seasonListBuilder(self, traktList, showInfo, smartPlay=False):
        self.threadList = []

        showInfo['info']['no_seasons'] = len(traktList)

        for item in traktList:

            # if tools.getSetting('general.metalocation') == '1':
            if 1 == 1:
                self.threadList.append(Thread(target=self.tvdbSeasonListWorker, args=(item, showInfo)))
            else:
                self.threadList.append(Thread(target=self.tmdbSeasonListWorker, args=(item, showInfo)))

        self.runThreads()

        if smartPlay is False and tools.getSetting('trakt.auth') != '':
            try:
                traktWatched = trakt.json_response('shows/%s/progress/watched' % showInfo['ids']['trakt'])

            except:
                pass

        self.itemList = [x for x in self.itemList if x is not None]

        self.itemList = sorted(self.itemList, key=lambda k: k['info']['sortseason'])

        for item in self.itemList:
            cm = []
            action = ''

            if item is None: continue

            if smartPlay is False and tools.getSetting('trakt.auth') != '':
                try:
                    for season in traktWatched['seasons']:
                        if int(item['info']['season']) == int(season['number']):
                            if season['completed'] == season['aired']:
                                item['info']['playcount'] = 1
                except:
                    import traceback
                    traceback.print_exc()
                    pass
            try:
                args = {'showInfo': {}, 'seasonInfo': {}}

                action = 'seasonEpisodes'
                args['showInfo'] = showInfo
                args['seasonInfo']['info'] = item['info']
                args['seasonInfo']['art'] = item['art']
                args['seasonInfo']['ids'] = item['ids']
                name = item['info']['season_title']
                args = tools.quote(json.dumps(args, sort_keys=True))
            except:
                import traceback
                traceback.print_exc()
                continue

            if smartPlay is True:
                return args

            if tools.getSetting('trakt.auth') != '':
                cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                           % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

            if tools.context_addon():
                cm = []
            try:
                if tools.kodiVersion > 17:
                    item['info'].pop('no_seasons')
                    item['info'].pop('season_title')
                    item['info'].pop('overview')
                    item['info'].pop('seasonCount')
                    item['info'].pop('episodeCount')
                    item['info'].pop('showaliases')
            except:
                pass
            tools.addDirectoryItem(name, action, item['info'], item['art'], cm=cm,
                                   isFolder=True, isPlayable=False, actionArgs=args,
                                   set_ids=item['ids'])

    def episodeListBuilder(self, traktList, showInfo, smartPlay=False, info_only=False, hide_unaired=False):

        self.threadList = []
        try:
            play_list = []

            if len(traktList) == 0: return

            for item in traktList:

                # if tools.getSetting('general.metalocation') == '1':
                if 1 == 1:
                    self.threadList.append(Thread(target=self.tvdbEpisodeWorker, args=(item, showInfo)))
                else:
                    self.threadList.append(Thread(target=self.tmdbEpisodeWorker, args=(item, showInfo)))

            self.runThreads()
            if smartPlay is False and tools.getSetting('trakt.auth') != '':
                try:
                    traktWatched = trakt.json_response(
                        'shows/%s/progress/watched' % showInfo['showInfo']['ids']['trakt'])
                except:
                    pass
            self.itemList = [x for x in self.itemList if x is not None]
            try:
                self.itemList = sorted(self.itemList, key=lambda k: k['info']['episode'])
            except:
                pass
            if info_only == True:
                return
            for item in self.itemList:
                if hide_unaired:
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
                cm = []
                action = ''
                if item is None: continue
                if smartPlay is False and tools.getSetting('trakt.auth') != '':
                    item['info']['playcount'] = 0
                    try:
                        for season in traktWatched['seasons']:
                            if season['number'] == item['info']['season']:
                                for episode in season['episodes']:
                                    if episode['number'] == item['info']['episode'] and episode['completed'] == True:
                                        item['info']['playcount'] = 1
                    except:
                        pass

                try:
                    args = {'showInfo': {}, 'episodeInfo': {}}

                    if tools.getSetting('smartplay.playlistcreate') == 'true' and smartPlay is False:
                        action = 'smartPlay'
                        playable = False
                    else:
                        playable = True
                        action = 'getSources'
                    args['showInfo'] = showInfo['showInfo']
                    args['episodeInfo']['info'] = item['info']
                    args['episodeInfo']['art'] = item['art']
                    args['episodeInfo']['ids'] = item['ids']
                    name = item['info']['title']

                    args = tools.quote(json.dumps(args, sort_keys=True))

                except:
                    import traceback
                    traceback.print_exc()
                    continue

                cm.append((tools.lang(33022).encode('utf-8'),
                           'PlayMedia(%s?action=getSources&seren_reload=true&actionArgs=%s)' % (sysaddon, args)))

                cm.append((tools.lang(32066).encode('utf-8'),
                           'PlayMedia(%s?action=getSources&source_select=true&actionArgs=%s)' % (sysaddon, args)))

                if tools.getSetting('trakt.auth') != '':
                    cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                               % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

                if tools.context_addon():
                    cm = []

                if tools.getSetting('premiumize.enabled') == 'true' and tools.getSetting('premiumize.pin') != '':
                    cm.append((tools.lang(32068).encode('utf-8'),
                               'XBMC.RunPlugin(%s?action=filePicker&actionArgs=%s)' % (sysaddon, args)))

                if smartPlay is False:
                    tools.addDirectoryItem(name, action, item['info'], item['art'], cm=cm,
                                           isFolder=False, isPlayable=playable, actionArgs=args, set_ids=item['ids'])
                else:
                    play_list.append(tools.addDirectoryItem(name, action, item['info'],
                                                            item['art'], isFolder=False, isPlayable=playable,
                                                            actionArgs=args, smart_play=True, set_ids=item['ids']))

            if smartPlay is True:
                return play_list

        except:
            import traceback
            traceback.print_exc()

    def directToEpisodeBuilder(self, traktList, sort=None):

        self.threadList = []
        traktWatched = trakt.json_response('sync/watched/shows')

        try:
            if len(traktList) == 0: return

            for item in traktList:
                # if tools.getSetting('general.metalocation') == '1':
                if 1 == 1:
                    self.threadList.append(Thread(target=self.tvdbEpisodeWorker, args=(item['episode'], item['show'])))
                else:
                    self.threadList.append(Thread(target=self.tmdbEpisodeWorker, args=(item[0], item[1])))

            self.runThreads()
            self.itemList = [i for i in self.itemList if i is not None]

            if sort is not None:
                sorted_list = []
                for sort_id in sort['id_list']:
                    for menu_item in self.itemList:
                        if menu_item[sort['type']]['ids']['trakt'] == sort_id:
                            sorted_list.append(menu_item)
                self.itemList = sorted_list
            else:
                self.itemList = sorted(self.itemList, key=lambda i: tools.datetime_workaround(i['info']['premiered']),
                                       reverse=True)

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
                cm = []
                action = ''

                if tools.getSetting('trakt.auth') != '':
                    try:
                        item['info']['playcount'] = 0
                        for show in traktWatched:
                            if str(show['show']['ids']['trakt']) == str(item['showInfo']['ids']['trakt']):
                                for season in show['seasons']:
                                    if str(season['number']) == str(item['info']['season']):
                                        for episode in season['episodes']:
                                            if str(episode['number']) == str(item['info']['episode']):
                                                if episode['plays'] > 0:
                                                    item['info']['playcount'] = 1
                    except:
                        pass

                try:
                    args = {'showInfo': {}, 'episodeInfo': {}}

                    if tools.getSetting('smartplay.playlistcreate') == 'true':
                        action = 'smartPlay'
                        playable = False
                    else:
                        playable = True
                        action = 'getSources'

                    args['showInfo'] = item['showInfo']
                    args['episodeInfo']['info'] = item['info']
                    args['episodeInfo']['art'] = item['art']
                    args['episodeInfo']['ids'] = item['ids']
                    name = item['info']['title']

                    args = tools.quote(json.dumps(args, sort_keys=True))

                    cm.append((tools.lang(32069).encode('utf-8'),
                               'XBMC.Container.Update(%s?action=showSeasons&actionArgs=%s)' %
                               (sysaddon, tools.quote(json.dumps(item['showInfo'])))))

                    cm.append((tools.lang(32066).encode('utf-8'),
                               'PlayMedia(%s?action=getSources&source_select=true&actionArgs=%s)' % (sysaddon, args)))

                    cm.append((tools.lang(33022).encode('utf-8'),
                               'PlayMedia(%s?action=getSources&seren_reload=true&actionArgs=%s)' % (sysaddon, args)))

                    if tools.getSetting('trakt.auth') != '':
                        cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                                   % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

                    if tools.context_addon():
                        cm = []

                    if tools.getSetting('premiumize.enabled') == 'true' and tools.getSetting('premiumize.pin') != '':
                        cm.append((tools.lang(32068).encode('utf-8'),
                                   'XBMC.RunPlugin(%s?action=filePicker&actionArgs=%s)' % (sysaddon, args)))

                except:
                    import traceback
                    traceback.print_exc()
                    continue

                tools.addDirectoryItem(name, action, item['info'], item['art'], cm=cm,
                                       isFolder=False, isPlayable=playable, actionArgs=args, set_ids=item['ids'])
        except:
            import traceback
            traceback.print_exc()

    def showListBuilder(self, traktList, forceResume=False, info_only=False):

        self.threadList = []
        try:
            if len(traktList) == 0: return
        except:
            return

        if 'show' in traktList[0]:
            buildList = [i['show'] for i in traktList]
            traktList = buildList

        for item in traktList:

            if tools.getSetting('general.metalocation') == '1':
                self.threadList.append(Thread(target=self.tvdbShowListWorker, args=(item,)))
            else:
                self.threadList.append(Thread(target=self.tmdbShowListWorker, args=(item,)))

        self.runThreads()
        self.itemList = tools.sort_list_items(self.itemList, traktList)
        if tools.getSetting('trakt.auth') != '':
            traktWatched = trakt.json_response('sync/watched/shows?extended=full')

            for listItem in self.itemList:
                try:
                    for show in traktWatched:
                        if show['show']['ids']['trakt'] == listItem['ids']['trakt']:
                            listItem['info']['playcount'] = 1
                            episodes = 0
                            for season in show['seasons']:
                                episodes += len(season['episodes'])
                            if episodes < show['show']['aired_episodes']:
                                listItem['info']['playcount'] = 0
                            break
                except:
                    pass

        for item in self.itemList:
            if item is None: continue
            try:
                args = {}
                cm = []
                action = ''

                # Add Arguments to pass with items
                args['ids'] = item['ids']
                args['info'] = item['info']
                args['art'] = item['art']
                name = item['info']['tvshowtitle']
                args = tools.quote(json.dumps(args, sort_keys=True))

                if info_only == True:
                    return args

                if 'setCast' in item:
                    set_cast = item['setCast']
                else:
                    set_cast = None

                if tools.getSetting('smartplay.clickresume') == 'true' or forceResume is True:
                    action = 'smartPlay'
                else:
                    action = 'showSeasons'

                # Context Menu Items

                cm.append((tools.lang(32070).encode('utf-8'),
                           'XBMC.RunPlugin(%s?action=shufflePlay&actionArgs=%s)' % (sysaddon,
                                                                                    args)))

                cm.append((tools.lang(32020).encode('utf-8'),
                           'Container.Update(%s?action=showsRelated&actionArgs=%s)' % (sysaddon, item['ids']['trakt'])))

                cm.append(
                    (tools.lang(32069).encode('utf-8'), 'XBMC.Container.Update(%s?action=showSeasons&actionArgs=%s)'
                     % (sysaddon, args)))

                if tools.getSetting('trakt.auth') != '':
                    cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                               % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

                if tools.context_addon():
                    cm = []

                try:
                    if tools.kodiVersion > 17:
                        item['info'].pop('seasonCount')
                        item['info'].pop('episodeCount')
                        item['info'].pop('showaliases')
                except:
                    pass

            except:
                import traceback
                traceback.print_exc()
                continue

            tools.addDirectoryItem(name, action, item['info'], item['art'], all_fanart=None, cm=cm,
                                   isFolder=True, isPlayable=False, actionArgs=args, set_cast=set_cast,
                                   set_ids=item['ids'])

    def tmdbAppendShowWorker(self, trakt_object):
        tools.tmdb_sema.acquire()
        episode = database.get(TMDBAPI().directToEpisode, 24, copy.deepcopy(trakt_object))
        self.itemList.append(episode)
        tools.tmdb_sema.release()

    def tmdbShowListWorker(self, trakt_object):
        tools.tmdb_sema.acquire()
        show = database.get(TMDBAPI().showToListItem, 24, copy.deepcopy(trakt_object))
        self.itemList.append(show)
        tools.tmdb_sema.release()

    def tmdbSeasonListWorker(self, trakt_object, showArgs):
        tools.tmdb_sema.acquire()
        season = database.get(TMDBAPI().showSeasonToListItem, 24, copy.deepcopy(trakt_object), copy.deepcopy(showArgs))
        self.itemList.append(season)
        tools.tmdb_sema.release()

    def tmdbEpisodeWorker(self, trakt_object, showArgs):
        tools.tmdb_sema.acquire()
        episode = database.get(TMDBAPI().episodeIDToListItem, 24, copy.deepcopy(trakt_object), copy.deepcopy(showArgs))
        self.itemList.append(episode)
        tools.tmdb_sema.release()

    def tvdbSeasonListWorker(self, trakt_object, showArgs):
        season = database.get(TVDBAPI().seasonIDToListItem, 24, copy.deepcopy(trakt_object), copy.deepcopy(showArgs))
        self.itemList.append(season)

    def tvdbEpisodeWorker(self, trakt_object, showArgs):
        item = database.get(TVDBAPI().episodeIDToListItem, 24, copy.deepcopy(trakt_object), copy.deepcopy(showArgs))
        self.itemList.append(item)

    def tvdbShowListWorker(self, trakt_object):
        self.itemList.append(database.get(TVDBAPI().seriesIDToListItem, 24, copy.deepcopy(trakt_object)))

    def traktProgressWorker(self, trakt_object):
        progress = database.get(TraktAPI().json_response, .5,
                                'shows/%s/progress/watched?extended=full' % trakt_object['show']['ids']['trakt'])
        trakt_object['progress'] = progress
        self.itemList.append(trakt_object)

    def runThreads(self, join=True):
        for thread in self.threadList:
            thread.start()

        if join == True:
            for thread in self.threadList:
                thread.join()
