import sys, json, datetime, copy
from resources.lib.common import tools
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.indexers.tvdb import TVDBAPI
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.modules import database
from threading import Thread

sysaddon = sys.argv[0]
syshandle = int(sys.argv[1])
trakt = TraktAPI()

class Menus:

    def __init__(self):
        self.itemList = []
        self.threadList = []
        self.direct_episode_threads = []
        self.viewType = tools.getSetting('show.view')

    ######################################################
    # MENUS
    ######################################################

    def onDeckShows(self):
        traktList = [i['show'] for i in trakt.json_response('sync/playback/episodes?extended=full', limit=True)]
        showList = []
        for i in traktList:
            if i not in showList:
                showList.append(i)
        if tools.getSetting('smartplay.clickresume') == 'false' and tools.getSetting('smartPlay.deckresume') == 'true':
            forceResume = True
        else:
            forceResume = False
        self.showListBuilder(showList, forceResume=forceResume)
        tools.closeDirectory('tvshows', viewType=self.viewType)

    def discoverShows(self):

        tools.addDirectoryItem(tools.lang(32007), 'showsPopular&page=1', '', '')
        if tools.getSetting('trakt.auth') is not '':
            tools.addDirectoryItem(tools.lang(32008), 'showsRecommended', '', '')
        tools.addDirectoryItem(tools.lang(32009), 'showsTrending&page=1', '', '')
        tools.addDirectoryItem('New Shows', 'showsNew', '', '')
        tools.addDirectoryItem(tools.lang(32010), 'showsPlayed&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32011), 'showsWatched&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32012), 'showsCollected&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32013), 'showsAnticipated&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32014), 'showsUpdated&page=1', '', '')
        tools.addDirectoryItem('Genres', 'showGenres', '', '')
        tools.addDirectoryItem(tools.lang(32016), 'showsSearch', '', '')
        tools.closeDirectory('addons')

    def myShows(self):
        tools.addDirectoryItem(tools.lang(32017), 'showsMyCollection', '', '')
        tools.addDirectoryItem(tools.lang(32018), 'showsMyWatchlist', '', '')
        tools.addDirectoryItem('Next Up', 'showsNextUp', '', '')
        tools.addDirectoryItem('Unfinished Shows in Collection', 'showsMyProgress', '', '')
        tools.addDirectoryItem('Recent Episodes', 'showsMyRecentEpisodes', '', '')
        tools.addDirectoryItem('My Show Lists', 'myTraktLists&actionArgs=shows', '', '')
        tools.closeDirectory('addons')

    def myShowCollection(self):
        traktList = trakt.json_response('users/me/collection/shows?extended=full', limit=False)
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows', viewType=self.viewType, sort='title')

    def myShowWatchlist(self):
        traktList = trakt.json_response('users/me/watchlist/shows?extended=full', limit=False)
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows', viewType=self.viewType, sort='title')

    def myProgress(self):
        self.threadList = []
        collection = trakt.json_response('users/me/collection/shows?extended=full', limit=False)
        for i in collection:
            self.threadList.append(Thread(target=self.traktProgressWorker, args=(i,)))
        self.runThreads()
        progress_report = self.itemList
        self.itemList = []
        unfinished_shows = [i for i in progress_report
                            if i is not None if i['progress']['aired'] > i['progress']['completed']]
        self.showListBuilder(unfinished_shows)
        tools.closeDirectory('tvshows', viewType=self.viewType, sort='title')

    def newShows(self):
        datestring = datetime.datetime.today() - datetime.timedelta(days=30)
        trakt_list = trakt.json_response('calendars/all/shows/new/%s/30?extended=full' %
                                         datestring.strftime('%d-%m-%Y'))
        if len(trakt_list) > 40:
            trakt_list = trakt_list[:40]
        self.showListBuilder(trakt_list)
        tools.closeDirectory('tvshows', viewType=self.viewType)


    def myNextUp(self,):
        page=2
        self.threadList = []
        watched = database.get(trakt.json_response, .5, 'users/me/watched/shows?extended=full', limit=False)

        if watched is None:
            watched = trakt.json_response('users/me/watched/shows?extended=full', limit=False)
        watched = [i for i in watched if i is not None if 'show' in i]
        watched = watched[:100]
        for i in watched:
            self.threadList.append(Thread(target=self.traktProgressWorker, args=(i,)))
        self.runThreads()
        self.threadList = []
        next_up = self.itemList

        self.itemList = []
        next_up = [i for i in next_up if i is not None if i['progress']['next_episode'] is not None]
        build_list = []

        for i in next_up:
            item = {'show': i['show'], 'episode': i['progress']['next_episode']}
            build_list.append(item)

        self.directToEpisodeBuilder(build_list)

        tools.closeDirectory('tvshows', viewType=self.viewType)

    def myRecentEpisodes(self):
        datestring = datetime.datetime.today() - datetime.timedelta(days=7)
        trakt_list = trakt.json_response('calendars/my/shows/%s/7?extended=full' % datestring.strftime('%d-%m-%Y'))
        if len(trakt_list) > 100:
            trakt_list = trakt_list[:100]
        self.directToEpisodeBuilder(trakt_list)
        tools.closeDirectory('tvshows', viewType=self.viewType)

    def showsPopular(self, page):

        traktList = trakt.json_response('shows/popular?page=%s&extended=full' % page)

        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'showsPopular&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows',  viewType=self.viewType)

    def showsRecommended(self):

        traktList = trakt.json_response('recommendations/shows?extended=full', limit=True, limitOverride=100)
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows',  viewType=self.viewType)

    def showsTrending(self, page):
        traktList = trakt.json_response('shows/trending?page=%s&extended=full' % page)

        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'showsTrending&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows',  viewType=self.viewType)

    def showsPlayed(self, page):
        traktList = trakt.json_response('shows/played?page=%s&extended=full' % page)

        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'showsPlayed&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows',  viewType=self.viewType)

    def showsWatched(self, page):
        traktList = trakt.json_response('shows/watched?page=%s&extended=full' % page)

        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'showsWatched&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows',  viewType=self.viewType)

    def showsCollected(self, page):
        traktList = trakt.json_response('shows/collected?page=%s&extended=full' % page)

        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'showsCollected&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows',  viewType=self.viewType, sort='title')

    def showsAnticipated(self, page):
        traktList = trakt.json_response('shows/anticipated?page=%s&extended=full' % page)

        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'showsAnticipated&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows',  viewType=self.viewType)

    def showsUpdated(self, page):
        import datetime
        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime('%Y-%m-%d')
        traktList = trakt.json_response('shows/updates/%s?page=%s&extended=full' % (date, page))

        self.showListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'showsUpdated&page=%s' % (int(page) + 1), '', '')
        tools.closeDirectory('tvshows',  viewType=self.viewType)

    def showsSearch(self):

        k = tools.showKeyboard('', tools.lang(32016))
        k.doModal()
        query = (k.getText() if k.isConfirmed() else None)
        if query == None or query == '':
            return
        query = tools.deaccentString(query)
        query = tools.quote_plus(query)
        traktList = trakt.json_response('search/show?query=%s&extended=full' % query, limit=True)
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows',  viewType=self.viewType)

    def showSeasons(self, args):

        showInfo = json.loads(tools.unquote(args))

        traktList = trakt.json_response('shows/%s/seasons?extended=full' % showInfo['ids']['trakt'])

        self.seasonListBuilder(traktList, showInfo)

        tools.closeDirectory('seasons',  viewType=self.viewType, sort='title')

    def seasonEpisodes(self, args):

        args = json.loads(tools.unquote(args))

        traktList = trakt.json_response('shows/%s/seasons/%s?extended=full' % (args['showInfo']['ids']['trakt'],
                                                                 args['seasonInfo']['info']['season']))

        self.episodeListBuilder(traktList, args)
        tools.closeDirectory('episodes', viewType=self.viewType, sort='episode')

    def showGenres(self):
        tools.addDirectoryItem('Multi Select...', 'showGenresGet', '', '', isFolder=True)
        genres = database.get(trakt.json_response, 24, 'genres/shows')
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
        traktList = trakt.json_response('shows/popular?genres=%s&page=%s&extended=full' % (genre_string, page))
        self.showListBuilder(traktList)
        tools.addDirectoryItem('Next', 'showGenresGet&actionArgs=%s&page=%s' % (genre_string, page+1), None, None)
        tools.closeDirectory('videos', viewType=self.viewType)

    def showsRelated(self, args):
        traktList = trakt.json_response('shows/%s/related?extended=full' % args)
        self.showListBuilder(traktList)
        tools.closeDirectory('tvshows', viewType=self.viewType)

    ######################################################
    # MENU TOOLS
    ######################################################

    def seasonListBuilder(self, traktList, showInfo, smartPlay=False):
        self.threadList = []

        showInfo['info']['no_seasons'] = len(traktList)

        for item in traktList:

            if tools.getSetting('general.metalocation') == '1':
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

        #self.itemList = sorted(self.itemList, key=lambda k: k['info']['sortseason'])

        for item in self.itemList:
            cm = []
            action = ''

            if item is None: continue

            if smartPlay is False and tools.getSetting('trakt.auth') != '':
                try:
                    for season in traktWatched['seasons']:
                        if item['info']['season'] == str(season['number']):
                            if season['completed'] == season['aired']:
                                item['info']['playcount'] = 1
                except:
                    pass
            try:
                cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s&type=episode)'
                           % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))
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

            tools.addDirectoryItem(name, action, item['info'], item['art'], cm=cm,
                                   isFolder=True, isPlayable=False, actionArgs=args)


    def episodeListBuilder(self, traktList, showInfo, smartPlay=False, info_only=False):
        self.threadList = []
        try:
            play_list = []

            if len(traktList) == 0: return

            if len(traktList) == 1:
                self.tmdbEpisodeWorker(traktList[0], showInfo)
            else:
                for item in traktList:

                    if tools.getSetting('general.metalocation') == '1':
                        self.threadList.append(Thread(target=self.tvdbEpisodeWorker, args=(item, showInfo)))
                    else:
                        self.threadList.append(Thread(target=self.tmdbEpisodeWorker, args=(item, showInfo)))

            self.runThreads()
            if smartPlay is False and tools.getSetting('trakt.auth') != '':
                try:
                    traktWatched = trakt.json_response('shows/%s/progress/watched' % showInfo['showInfo']['ids']['trakt'])
                except:
                    pass
            self.itemList = [x for x in self.itemList if x is not None]
            try:self.itemList = sorted(self.itemList, key=lambda k: k['info']['episode'])
            except:pass
            if info_only == True:
                return
            for item in self.itemList:
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

                    cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                               % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))


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
                    cm.append(('Torrent file select',
                               'XBMC.RunPlugin(%s?action=filePicker&actionArgs=%s)' % (sysaddon, args)))
                    cm.append(('Source Select',
                               'PlayMedia(%s?action=getSources&source_select=true&actionArgs=%s)' % (sysaddon, args)))
                except:
                    import traceback
                    traceback.print_exc()
                    continue

                if smartPlay is False:
                    tools.addDirectoryItem(name, action, item['info'], item['art'], cm=cm,
                                           isFolder=False, isPlayable=playable, actionArgs=args)
                else:
                    play_list.append(tools.addDirectoryItem(name, action, item['info'],
                                                            item['art'], isFolder=False, isPlayable=playable,
                                                            actionArgs=args, smart_play=True))

            if smartPlay is True:
                return play_list

        except:
            import traceback
            traceback.print_exc()


    def directToEpisodeBuilder(self, traktList):

        self.threadList = []
        traktWatched = trakt.json_response('sync/watched/shows')

        try:
            if len(traktList) == 0: return

            for item in traktList:
                if tools.getSetting('general.metalocation') == '1':
                    self.threadList.append(Thread(target=self.tvdbEpisodeWorker, args=(item['episode'], item['show'])))
                else:
                    self.threadList.append(Thread(target=self.tmdbEpisodeWorker, args=(item[0], item[1])))

            self.runThreads()
            self.itemList = [i for i in self.itemList if i is not None]
            self.itemList = sorted(self.itemList, key=lambda i: tools.datetime_workaround(i['info']['premiered']))
            self.itemList.reverse()
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

                cm.append(('Trakt Manager',
                           'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                           % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

                cm.append(('Browse Show',
                           'XBMC.Container.Update(%s?action=showSeasons&actionArgs=%s)' %
                           (sysaddon, tools.quote(json.dumps(item['showInfo'])))))

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
                    name = "%s: %sx%s %s" % (tools.colorString(args['showInfo']['info']['tvshowtitle']),
                                             str(item['info']['season']).zfill(2),
                                             str(item['info']['episode']).zfill(2),
                                             item['info']['title'].encode('utf-8'))
                    item['info']['title'] = item['info']['originaltitle'] = name

                    args = tools.quote(json.dumps(args, sort_keys=True))
                    cm.append(('Torrent file select',
                               'RunPlugin(%s?action=filePicker&actionArgs=%s)' % (sysaddon, args)))
                    cm.append(('Source Select',
                               'PlayMedia(%s?action=getSources&source_select=true&actionArgs=%s)' % (sysaddon, args)))

                except:
                    import traceback
                    traceback.print_exc()
                    continue

                tools.addDirectoryItem(name, action, item['info'], item['art'], cm=cm,
                                       isFolder=False, isPlayable=playable, actionArgs=args)
        except:
            import traceback
            traceback.print_exc()

    def showListBuilder(self, traktList, forceResume=False, info_only=False):
        self.threadList = []
        try:
            if len(traktList) == 0: return
        except: return

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

                cm.append(('Shuffle Play', 'XBMC.RunPlugin(%s?action=shufflePlay&actionArgs=%s)' % (sysaddon,
                                                                                                    args)))

                if tools.getSetting('smartplay.clickresume') == 'true' or forceResume is True:
                    action = 'smartPlay'
                    cm.append(('Expand Show', 'XBMC.Container.Update(%s?action=showSeasons&actionArgs=%s)'
                               % (sysaddon, args)))
                else:
                    action = 'showSeasons'

                # Context Menu Items
                cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                           % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))
                cm.append((tools.lang(32020),
                           'Container.Update(%s?action=showsRelated&actionArgs=%s)' % (sysaddon, item['ids']['trakt'])))
            except:
                import traceback
                traceback.print_exc()
                continue

            tools.addDirectoryItem(name, action, item['info'], item['art'], all_fanart=None, cm=cm,
                                   isFolder=True, isPlayable=False, actionArgs=args, set_cast=set_cast)

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
        progress = database.get(TraktAPI().json_response, .5, 'shows/%s/progress/watched?extended=full' % trakt_object['show']['ids']['trakt'])
        trakt_object['progress'] = progress
        self.itemList.append(trakt_object)

    def runThreads(self, join=True):
        for thread in self.threadList:
            thread.start()

        if join == True:
            for thread in self.threadList:
                thread.join()