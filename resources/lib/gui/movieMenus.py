# -*- coding: utf-8 -*-

import json
import sys
from threading import Thread

from resources.lib.common import tools
from resources.lib.indexers.imdb import scraper as imdb_scraper
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.modules import database

try:
    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
except:
    sysaddon = ''
    syshandle = ''

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
        if traktList is None:
            return

        trakt_list = sorted(traktList, key=lambda i: tools.datetime_workaround(i['paused_at'][:19],
                                                                              format="%Y-%m-%dT%H:%M:%S",
                                                                              date_only=False), reverse=True)
        movie_list = []
        filter_list = []
        for i in trakt_list:
            if i['movie']['ids']['trakt'] not in filter_list:
                if int(i['progress']) != 0:
                    movie_list.append(i)
                    filter_list.append(i['movie']['ids']['trakt'])

        self.commonListBuilder(movie_list)
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
        #tools.addDirectoryItem('Years', 'movieYears', '', '')
        if tools.getSetting('searchHistory') == 'false':
            tools.addDirectoryItem(tools.lang(32016), 'moviesSearch', '', '')
        else:
            tools.addDirectoryItem(tools.lang(32016), 'moviesSearchHistory', '', '')
        tools.closeDirectory('addons', cacheToDisc=True)

    def myMovies(self):
        tools.addDirectoryItem(tools.lang(32063).encode('utf-8'), 'onDeckMovies', None, None)
        tools.addDirectoryItem(tools.lang(32017).encode('utf-8'), 'moviesMyCollection', '', '')
        tools.addDirectoryItem(tools.lang(32018).encode('utf-8'), 'moviesMyWatchlist', '', '')
        tools.addDirectoryItem(tools.lang(32064).encode('utf-8'), 'myTraktLists&actionArgs=movies', '', '')
        tools.closeDirectory('addons', cacheToDisc=True)

    def myMovieCollection(self):
        try:
            trakt_list = trakt.json_response('users/me/collection/movies?extended=full', limit=False)
            if trakt_list is None:
                return
            self.commonListBuilder(trakt_list)
            tools.closeDirectory('movies', viewType=self.viewType)
        except:
            import traceback
            traceback.print_exc()

    def myMovieWatchlist(self):
        trakt_list = trakt.json_response('users/me/watchlist/movies?extended=full&extended=full', limit=False)
        if trakt_list is None:
            return
        try:
            sort_by = trakt.response_headers['X-Sort-By']
            sort_how = trakt.response_headers['X-Sort-How']
            trakt_list = trakt.sort_list(sort_by, sort_how, trakt_list, 'movie')
        except:
            import traceback
            traceback.print_exc()
            pass

        self.commonListBuilder(trakt_list)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesRecommended(self):
        trakt_list = database.get(trakt.json_response, 12, 'recommendations/movies', limit=True, limitOverride=100)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesPopular(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/popular?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesPopular&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesTrending(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/trending?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesTrending&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesPlayed(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/played?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesPlayed&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesWatched(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/watched?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesWatched&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesCollected(self, page):
        trakt_list = trakt.json_response('movies/collected?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesCollected&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesAnticipated(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/anticipated?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesAnticipated&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesBoxOffice(self):
        trakt_list = database.get(trakt.json_response, 12, 'movies/boxoffice')
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesUpdated(self, page):
        import datetime
        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime('%Y-%m-%d')
        trakt_list = trakt.json_response('movies/updates/%s?page=%s' % (date, page))
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'), 'moviesUpdated&page=%s' % (int(page) + 1), '', '',
                               isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesSearchHistory(self):
        history = database.getSearchHistory('movie')
        tools.addDirectoryItem('New Movie Search...', 'moviesSearch', '', '')
        tools.addDirectoryItem('Clear Search History...', 'clearSearchHistory', '', '', isFolder=False)

        for i in history:
            tools.addDirectoryItem(i, 'moviesSearch&actionArgs=%s' % i, '', '')
        tools.closeDirectory('addon')


    def moviesSearch(self, actionArgs=None):

        if actionArgs == None:
            k = tools.showKeyboard('', tools.lang(32016).encode('utf-8'))
            k.doModal()
            query = (k.getText() if k.isConfirmed() else None)
            if query == None or query == '':
                return
        else:
            query = actionArgs

        database.addSearchHistory(query, 'movie')
        query = tools.deaccentString(query.encode('utf-8'))
        query = tools.quote_plus(query)
        trakt_list = trakt.json_response('search/movie?query=%s' % query)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesRelated(self, args):
        trakt_list = database.get(trakt.json_response, 12, 'movies/%s/related' % args)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesYears(self):
        from datetime import datetime
        year = int(datetime.today().year)
        years = []
        for i in range(year-100, year+1):
            years.append(i)
        years = sorted(years, reverse=True)
        for i in years:
            tools.addDirectoryItem(str(i), '', '', '')
        tools.closeDirectory('addons', cacheToDisc=True)

    def movieGenres(self):
        tools.addDirectoryItem(tools.lang(32065).encode('utf-8'), 'movieGenresGet', '', '', isFolder=True)
        genres = database.get(trakt.json_response, 24, 'genres/movies')
        if genres is None:
            return
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

        trakt_list = trakt.json_response('movies/popular?genres=%s&page=%s' % (genre_string, page))

        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019).encode('utf-8'),
                               'movieGenresGet&actionArgs=%s&page=%s' % (tools.quote(genre_string), int(page) + 1),
                               '', '', isFolder=True)

        tools.closeDirectory('movies', viewType=self.viewType)

    ######################################################
    # MENU TOOLS
    ######################################################

    def commonListBuilder(self, trakt_list, nextPath=None):

        if len(trakt_list) == 0:
            return
        if 'movie' in trakt_list[0]:
            trakt_list = [i['movie'] for i in trakt_list]

        for item in trakt_list:
            self.threadList.append(Thread(target=self.tmdbListWorker, args=(item,)))

        self.runThreads()

        self.itemList = tools.sort_list_items(self.itemList, trakt_list)
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
                args['imdb'] = item['info']['imdbnumber']
                args['tagline'] = item['info']['tagline']
                args['plot'] = item['info']['plot']
                args['rating'] = item['info']['rating']
                args['duration'] = item['info']['duration']
                name = item['info']['title']

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
                import traceback
                traceback.print_exc()
                continue

            if item is None: continue
            tools.addDirectoryItem(name, 'getSources', item['info'], item['art'], cm=cm,
                                   isFolder=False, isPlayable=True, actionArgs=args, set_ids=item['ids'])

    def tmdbListWorker(self, trakt_object):
        tools.tmdb_sema.acquire()
        listItem = database.get(TMDBAPI().movieToListItem, 24, trakt_object)
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
