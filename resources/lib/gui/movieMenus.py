# -*- coding: utf-8 -*-

import json
import sys

import datetime
from resources.lib.common import tools
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.modules import database
from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase

try:
    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
except:
    sysaddon = ''
    syshandle = ''

trakt = TraktAPI()
tmdbAPI = TMDBAPI()

trakt_database = TraktSyncDatabase()


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
        tools.closeDirectory('movies')

    def discoverMovies(self):

        tools.addDirectoryItem(tools.lang(32007), 'moviesPopular&page=1')
        if tools.getSetting('trakt.auth') is not '':
            tools.addDirectoryItem(tools.lang(32008), 'moviesRecommended')
        tools.addDirectoryItem(tools.lang(32009), 'moviesTrending&page=1')
        tools.addDirectoryItem(tools.lang(32010), 'moviesPlayed&page=1')
        tools.addDirectoryItem(tools.lang(32011), 'moviesWatched&page=1')
        tools.addDirectoryItem(tools.lang(32012), 'moviesCollected&page=1')
        tools.addDirectoryItem(tools.lang(32013), 'moviesAnticipated&page=1')
        tools.addDirectoryItem(tools.lang(32015), 'moviesBoxOffice')
        tools.addDirectoryItem(tools.lang(32014), 'moviesUpdated&page=1')
        tools.addDirectoryItem(tools.lang(32062), 'movieGenres&page=1')
        tools.addDirectoryItem(tools.lang(40123), 'movieYears')
        tools.addDirectoryItem(tools.lang(40151), 'movieByActor')

        # tools.addDirectoryItem('Years', 'movieYears')
        if tools.getSetting('searchHistory') == 'false':
            tools.addDirectoryItem(tools.lang(32016), 'moviesSearch', isFolder=True, isPlayable=False)
        else:
            tools.addDirectoryItem(tools.lang(32016), 'moviesSearchHistory')
        tools.closeDirectory('addons')

    def myMovies(self):
        tools.addDirectoryItem(tools.lang(32063), 'onDeckMovies', None, None)
        tools.addDirectoryItem(tools.lang(32017), 'moviesMyCollection')
        tools.addDirectoryItem(tools.lang(32018), 'moviesMyWatchlist')
        tools.addDirectoryItem(tools.lang(32064), 'myTraktLists&actionArgs=movies')
        tools.closeDirectory('addons')

    def myMovieCollection(self):

        try:
            trakt_list = trakt_database.get_collected_movies()
            trakt_list = [{'ids': {'trakt': i['trakt_id']}} for i in trakt_list]
            self.commonListBuilder(trakt_list)
            tools.closeDirectory('movies', sort='title')
        except:
            import traceback
            traceback.print_exc()

    def myMovieWatchlist(self):
        trakt_list = trakt.json_response('users/me/watchlist/movies', limit=False)
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
        tools.closeDirectory('movies')

    def moviesRecommended(self):
        trakt_list = database.get(trakt.json_response, 12, 'recommendations/movies?ignore_collected=true',
                                  limit=True, limitOverride=100)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.closeDirectory('movies')

    def moviesPopular(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/popular?page=%s' % page)

        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'moviesPopular&page=%s' % (int(page) + 1),
                               isFolder=True)
        tools.closeDirectory('movies')

    def moviesTrending(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/trending?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'moviesTrending&page=%s' % (int(page) + 1),
                               isFolder=True)
        tools.closeDirectory('movies')

    def moviesPlayed(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/played?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'moviesPlayed&page=%s' % (int(page) + 1),
                               isFolder=True)
        tools.closeDirectory('movies')

    def moviesWatched(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/watched?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'moviesWatched&page=%s' % (int(page) + 1),
                               isFolder=True)
        tools.closeDirectory('movies')

    def moviesCollected(self, page):
        trakt_list = trakt.json_response('movies/collected?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'moviesCollected&page=%s' % (int(page) + 1),
                               isFolder=True)
        tools.closeDirectory('movies')

    def moviesAnticipated(self, page):
        trakt_list = database.get(trakt.json_response, 12, 'movies/anticipated?page=%s' % page)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'moviesAnticipated&page=%s' % (int(page) + 1),
                               isFolder=True)
        tools.closeDirectory('movies')

    def moviesBoxOffice(self):
        trakt_list = database.get(trakt.json_response, 12, 'movies/boxoffice')
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.closeDirectory('movies')

    def moviesUpdated(self, page):
        import datetime
        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime('%Y-%m-%d')
        trakt_list = trakt.json_response('movies/updates/%s?page=%s' % (date, page))
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.addDirectoryItem(tools.lang(32019), 'moviesUpdated&page=%s' % (int(page) + 1),
                               isFolder=True)
        tools.closeDirectory('movies')

    def moviesSearchHistory(self):
        history = database.getSearchHistory('movie')
        tools.addDirectoryItem(tools.lang(40141), 'moviesSearch', isFolder=True, isPlayable=False)
        tools.addDirectoryItem(tools.lang(40140), 'clearSearchHistory', isFolder=False, isPlayable=False)

        for i in history:
            tools.addDirectoryItem(i, 'moviesSearchResults&actionArgs=%s' % i)
        tools.closeDirectory('addon')

    def moviesSearch(self, actionArgs=None):

        if actionArgs == None:
            k = tools.showKeyboard('', tools.lang(32016))
            k.doModal()
            query = (k.getText() if k.isConfirmed() else None)
            del k
            if query == None or query == '':
                return
        else:
            query = actionArgs

        query = query.decode('utf-8')
        database.addSearchHistory(query, 'movie')
        query = tools.deaccentString(tools.display_string(query))
        query = tools.quote(query)

        self.moviesSearchResults(query)

    def moviesSearchResults(self, query):
        query = tools.quote_plus(tools.unquote(query))
        trakt_list = trakt.json_response('search/movie?query=%s' % query)
        if trakt_list is None:
            return
        self.commonListBuilder([movie for movie in trakt_list if float(movie['score']) > 0])
        tools.closeAllDialogs()
        tools.closeDirectory('movies')

    def moviesRelated(self, args):
        trakt_list = database.get(trakt.json_response, 12, 'movies/%s/related' % args)
        if trakt_list is None:
            return
        self.commonListBuilder(trakt_list)
        tools.closeDirectory('movies')

    def movieYears(self):
        from datetime import datetime
        year = int(datetime.today().year)
        years = []
        for i in range(year - 100, year + 1):
            years.append(i)
        years = sorted(years, reverse=True)
        for i in years:
            tools.addDirectoryItem(str(i), 'movieYearsMovies&actionArgs=%s&page=1' % i)
        tools.closeDirectory('addons')

    def movieYearsMovies(self, year, page):

        trakt_list = database.get(trakt.json_response, 24, 'movies/popular?years=%s&page=%s' % (year, page))

        if trakt_list is None:
            return

        self.commonListBuilder(trakt_list)

        tools.addDirectoryItem(tools.lang(32019), 'movieYearsMovies&page=%s&actionArgs=%s' %
                               (int(page) + 1, year))
        tools.closeDirectory('movies')

    def moviesByActor(self, actionArgs):

        if actionArgs == None:
            k = tools.showKeyboard('', tools.lang(32016))
            k.doModal()
            query = (k.getText() if k.isConfirmed() else None)
            if query == None or query == '':
                return
        else:
            query = tools.unquote(actionArgs)

        database.addSearchHistory(query, 'movieActor')
        query = tools.deaccentString(query)
        query = query.replace(' ', '-')
        query = tools.quote_plus(query)

        trakt_list = trakt.json_response('people/%s/movies' % query, limit=True)

        try:
            trakt_list = trakt_list['cast']
        except:
            import traceback
            traceback.print_exc()
            trakt_list = []

        trakt_list = [i['movie'] for i in trakt_list]

        self.commonListBuilder(trakt_list)

        tools.closeDirectory('tvshows')

    def movieGenres(self):
        tools.addDirectoryItem(tools.lang(32065), 'movieGenresGet', isFolder=True)
        genres = database.get(trakt.json_response, 24, 'genres/movies')
        if genres is None:
            return
        for i in genres:
            tools.addDirectoryItem(i['name'], 'movieGenresGet&actionArgs=%s' % i['slug'], isFolder=True)
        tools.closeDirectory('addons')

    def movieGenresList(self, args, page):
        if page is None:
            page = 1
        if args is None:
            genre_display_list = []
            genre_string = ''
            genres = database.get(trakt.json_response, 24, 'genres/movies')
            for genre in genres:
                genre_display_list.append(genre['name'])
            genre_multiselect = tools.showDialog.multiselect('{}: {}'.format(tools.addonName, tools.lang(40298)),
                                                             genre_display_list)
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
        tools.addDirectoryItem(tools.lang(32019),
                               'movieGenresGet&actionArgs=%s&page=%s' % (tools.quote(genre_string), int(page) + 1),
                               isFolder=True)

        tools.closeDirectory('movies')

    ######################################################
    # MENU TOOLS
    ######################################################

    def commonListBuilder(self, trakt_list, info_return=False):

        if len(trakt_list) == 0:
            return
        if 'movie' in trakt_list[0]:
            trakt_list = [i['movie'] for i in trakt_list]

        self.itemList = trakt_database.get_movie_list(trakt_list)

        self.itemList = [x for x in self.itemList if x is not None and 'info' in x]
        self.itemList = tools.sort_list_items(self.itemList, trakt_list)

        list_items = []

        for item in self.itemList:
            try:

                name = tools.display_string(item['info']['title'])

                if not self.is_aired(item['info']):
                    if tools.getSetting('general.hideUnAired') == 'true':
                        continue
                    name = tools.colorString(name, 'red')
                    name = tools.italic_string(name)

                args = {'trakt_id': item['ids']['trakt'], 'item_type': 'movie'}
                args = tools.quote(json.dumps(args, sort_keys=True))

            except:
                import traceback
                traceback.print_exc()
                continue

            if item is None:
                continue

            item['info']['title'] = item['info']['originaltitle'] = name
            list_items.append(tools.addDirectoryItem(name, 'getSources', item['info'], item['art'], item['cast'],
                                                     isFolder=False, isPlayable=True, actionArgs=args,
                                                     set_ids=item['ids'], bulk_add=True))

        if info_return:
            return list_items

        tools.addMenuItems(syshandle, list_items, len(list_items))

    def runThreads(self, join=True):
        for thread in self.threadList:
            thread.start()

        if join == True:
            for thread in self.threadList:
                thread.join()

    def is_aired(self, info):
        try:
            try:
                air_date = info['aired']
            except:
                air_date = info['premiered']

            if tools.getSetting('general.datedelay') == 'true':
                air_date = tools.datetime_workaround(air_date, '%Y-%m-%d', date_only=True)
                air_date += datetime.timedelta(days=1)
            else:
                air_date = tools.datetime_workaround(air_date, '%Y-%m-%d', date_only=True)

            if air_date > datetime.date.today():
                return False

            else:
                return True
        except:
            # Assume an item is aired if we do not have any information on it
            return True
