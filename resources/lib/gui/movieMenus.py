# -*- coding: utf-8 -*-

import json
import sys
from threading import Thread

from resources.lib.common import tools
from resources.lib.indexers.imdb import scraper as imdb_scraper
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.modules import database

sysaddon = sys.argv[0];
syshandle = int(sys.argv[1])
trakt = TraktAPI()
tmdbAPI = TMDBAPI()
imdb_scraper = imdb_scraper()


class Menus:
    def __init__(self):
        self.itemList = []
        self.threadList = []
        self.viewType = tools.getSetting('movie.view')

    ######################################################
    # MENUS
    ######################################################

    def onDeckMovies(self):
        traktList = trakt.json_response('sync/playback/movies', limit=True)
        traktList = sorted(traktList, key=lambda i: tools.datetime_workaround(i['paused_at'][:10]))
        movieList = []
        filter_list = []
        for i in traktList:
            if i['movie']['ids']['trakt'] not in filter_list:
                if int(i['progress']) != 0:
                    movieList.append(i)
                    filter_list.append(i['movie']['ids']['trakt'])
        title_appends = {}
        for i in traktList:
            title_appends[i['movie']['ids']['trakt']] = 'Paused (%s%%)' % int(i['progress'])

        self.commonListBuilder(movieList, title_appends=title_appends)
        tools.closeDirectory('movies', viewType=self.viewType)

    def discoverMovies(self):

        tools.addDirectoryItem(tools.lang(32007).encode('utf-8'), 'moviesPopular&page=1', '', '')
        if tools.getSetting('trakt.auth') is not '':
            tools.addDirectoryItem(tools.lang(32008).encode('utf-8'), 'moviesRecommended', '', '')
        tools.addDirectoryItem(tools.lang(32009).encode('utf-8'), 'moviesTrending&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32010).encode('utf-8'), 'moviesPlayed&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32011).encode('utf-8'), 'moviesWatched&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32012).encode('utf-8'), 'moviesCollected&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32013).encode('utf-8'), 'moviesAnticipated&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32015).encode('utf-8'), 'moviesBoxOffice', '', '')
        tools.addDirectoryItem(tools.lang(32014).encode('utf-8'), 'moviesUpdated&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32062).encode('utf-8'), 'movieGenres&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32016), 'moviesSearch', '', '')
        tools.closeDirectory('addons', cacheToDisc=True)

    def myMovies(self):
        tools.addDirectoryItem(tools.lang(32063).encode('utf-8'), 'onDeckMovies', None, None)
        tools.addDirectoryItem(tools.lang(32017).encode('utf-8'), 'moviesMyCollection', '', '')
        tools.addDirectoryItem(tools.lang(32018).encode('utf-8'), 'moviesMyWatchlist', '', '')
        tools.addDirectoryItem(tools.lang(32064).encode('utf-8'), 'myTraktLists&actionArgs=movies', '', '')
        tools.closeDirectory('addons', cacheToDisc=True)

    def myMovieCollection(self):
        try:
            traktList = trakt.json_response('users/me/collection/movies', limit=False)
            self.commonListBuilder(traktList)
            tools.closeDirectory('movies', viewType=self.viewType)
        except:
            import traceback
            traceback.print_exc()

    def myMovieWatchlist(self):
        traktList = trakt.json_response('users/me/watchlist/movies', limit=False)
        try:
            sort_by = trakt.response_headers['X-Sort-By']
            sort_how = trakt.response_headers['X-Sort-How']
            traktList = trakt.sort_list(sort_by, sort_how, traktList, 'show')
        except:
            import traceback
            traceback.print_exc()
            pass

        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesRecommended(self):
        traktList = database.get(trakt.json_response, 12, 'recommendations/movies', limit=True, limitOverride=100)
        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesPopular(self, page):
        traktList = database.get(trakt.json_response, 12, 'movies/popular?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesPopular&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesTrending(self, page):
        traktList = database.get(trakt.json_response, 12, 'movies/trending?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesTrending&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesPlayed(self, page):
        traktList = database.get(trakt.json_response, 12, 'movies/played?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesPlayed&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesWatched(self, page):
        traktList = database.get(trakt.json_response, 12, 'movies/watched?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesWatched&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesCollected(self, page):
        traktList = trakt.json_response('movies/collected?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesCollected&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesAnticipated(self, page):
        traktList = database.get(trakt.json_response, 12, 'movies/anticipated?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesAnticipated&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesBoxOffice(self):
        traktList = database.get(trakt.json_response, 12, 'movies/boxoffice')

        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesUpdated(self, page):
        import datetime
        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime('%Y-%m-%d')
        traktList = trakt.json_response('movies/updates/%s?page=%s' % (date, page))

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesUpdated&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesSearch(self):

        k = tools.showKeyboard('', tools.lang(32016).encode('utf-8'))
        k.doModal()
        query = (k.getText() if k.isConfirmed() else None)
        if query == None or query == '':
            return
        query = tools.deaccentString(query.encode('utf-8'))
        query = tools.quote_plus(query)
        traktList = trakt.json_response('search/movie?query=%s' % query)
        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesRelated(self, args):
        traktList = database.get(trakt.json_response, 12, 'movies/%s/related' % args)
        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def movieGenres(self):
        tools.addDirectoryItem(tools.lang(32065).encode('utf-8'), 'movieGenresGet', '', '', isFolder=True)
        genres = database.get(trakt.json_response, 24, 'genres/movies')
        for i in genres:
            tools.addDirectoryItem(i['name'], 'movieGenresGet&actionArgs=%s' % i['slug'], '', '', isFolder=True)
        tools.closeDirectory('addons', cacheToDisc=True)

    def movieGenresList(self, args, page):
        if page is None:
            page = 1
        if args is None:
            genre_display_list = []
            genre_string = ''
            genres = database.get(trakt.json_response, 24, 'genres/movies')
            for genre in genres:
                genre_display_list.append(genre['name'])
            genre_multiselect = tools.showDialog.multiselect(tools.addonName + ": Genre Selection", genre_display_list)
            if genre_multiselect is None: return
            for selection in genre_multiselect:
                genre_string += ', %s' % genres[selection]['slug']
            genre_string = genre_string[2:]
        else:
            genre_string = tools.unquote(args)

        traktList = trakt.json_response('movies/popular?genres=%s&page=%s' % (genre_string, page))
        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'),
                               'movieGenresGet&actionArgs=%s&page=%s' % (tools.quote(genre_string), int(page) + 1),
                               '', '', isFolder=True)

        tools.closeDirectory('movies', viewType=self.viewType)

    ######################################################
    # MENU TOOLS
    ######################################################

    def commonListBuilder(self, traktList, nextPath=None, title_appends=None):

        if len(traktList) == 0:
            return
        if 'movie' in traktList[0]:
            traktList = [i['movie'] for i in traktList]

        for item in traktList:
            self.threadList.append(Thread(target=self.tmdbListWorker, args=(item,)))

        self.runThreads()

        self.itemList = tools.sort_list_items(self.itemList, traktList)
        if tools.getSetting('trakt.auth') != '':
            traktWatched = trakt.json_response('sync/watched/movies')

            for listItem in self.itemList:
                for i in traktWatched:
                    if i['movie']['ids']['trakt'] == listItem['ids']['trakt']:
                        listItem['info']['playcount'] = i['plays']

        for item in self.itemList:
            try:
                # Add Arguments to pass with item
                args = {}
                args['title'] = item['info']['title']
                args['year'] = item['info']['year']
                args['ids'] = item['ids']
                args['fanart'] = item['art']['fanart']
                args['info'] = item['info']
                args['art'] = item['art']
                name = item['info']['title']

                if title_appends is not None:
                    name = '%s - %s' % (name, title_appends[item['ids']['trakt']])

                item['info']['title'] = item['info']['originaltitle'] = name
                args = tools.quote(json.dumps(args))

                # Begin Building Context Menu Items
                cm = []
                cm.append((tools.lang(32020).encode('utf-8'),
                           'Container.Update(%s?action=moviesRelated&actionArgs=%s)' % (
                           sysaddon, item['ids']['trakt'])))
                cm.append((tools.lang(32066).encode('utf-8'),
                           'PlayMedia(%s?action=getSources&source_select=true&actionArgs=%s)' % (sysaddon, args)))
                cm.append((tools.lang(33022).encode('utf-8'),
                           'PlayMedia(%s?action=getSources&seren_reload=true&actionArgs=%s)' % (sysaddon, args)))

                if tools.getSetting('trakt.auth') != '':
                    cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                               % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))

                if tools.context_addon():
                    cm = []

            except:
                continue

            if item is None: continue
            tools.addDirectoryItem(name, 'getSources', item['info'], item['art'], cm=cm,
                                   isFolder=False, isPlayable=True, actionArgs=args, set_ids=item['ids'])

    def tmdbListWorker(self, trakt_object):
        tools.tmdb_sema.acquire()
        listItem = database.get(tmdbAPI.movieToListItem, 24, trakt_object)
        # Tried to use IMDB as a scraper source. Fuck it was slow
        # listItem = database.get(imdb_scraper.trakt_movie_to_list_item, '24', trakt_object)
        self.itemList.append(listItem)
        tools.tmdb_sema.release()

    def runThreads(self, join=True):
        for thread in self.threadList:
            thread.start()

        if join == True:
            for thread in self.threadList:
                thread.join()
