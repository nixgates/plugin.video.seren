import sys, json
from resources.lib.common import tools
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.indexers.imdb import scraper as imdb_scraper
from resources.lib.modules import database
from threading import Thread

sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
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
        traktList = [i['movie'] for i in trakt.json_response('sync/playback/movies', limit=True)]
        showList = []
        for i in traktList:
            if i not in showList:
                showList.append(i)
        self.commonListBuilder(showList)
        tools.closeDirectory('movies', viewType=self.viewType)


    def discoverMovies(self):

        tools.addDirectoryItem(tools.lang(32007), 'moviesPopular&page=1', '', '')
        if tools.getSetting('trakt.auth') is not '':
            tools.addDirectoryItem(tools.lang(32008), 'moviesRecommended', '', '')
        tools.addDirectoryItem(tools.lang(32009), 'moviesTrending&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32010), 'moviesPlayed&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32011), 'moviesWatched&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32012), 'moviesCollected&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32013), 'moviesAnticipated&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32015), 'moviesBoxOffice', '', '')
        tools.addDirectoryItem(tools.lang(32014), 'moviesUpdated&page=1', '', '')
        tools.addDirectoryItem('Genres', 'movieGenres&page=1', '', '')
        tools.addDirectoryItem(tools.lang(32016), 'moviesSearch', '', '')
        tools.closeDirectory('addons')

    def myMovies(self):
        tools.addDirectoryItem(tools.lang(32017), 'moviesMyCollection', '', '')
        tools.addDirectoryItem(tools.lang(32018), 'moviesMyWatchlist', '', '')
        tools.addDirectoryItem('My Movie Lists', 'myTraktLists&actionArgs=movies', '', '')
        tools.closeDirectory('addons', viewType=self.viewType)

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
        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesRecommended(self):
        traktList = trakt.json_response('recommendations/movies', limit=True, limitOverride=100)
        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesPopular(self, page):
        traktList = trakt.json_response('movies/popular?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'moviesPopular&page=%s' % (int(page) + 1), '', '', isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesTrending(self, page):
        traktList = trakt.json_response('movies/trending?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'moviesTrending&page=%s' % (int(page) + 1), '', '', isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesPlayed(self, page):
        traktList = trakt.json_response('movies/played?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'moviesPlayed&page=%s' % (int(page) + 1), '', '', isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesWatched(self, page):
        traktList = trakt.json_response('movies/watched?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'moviesWatched&page=%s' % (int(page) + 1), '', '', isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesCollected(self, page):
        traktList = trakt.json_response('movies/collected?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'moviesCollected&page=%s' % (int(page) + 1), '', '', isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesAnticipated(self, page):
        traktList = trakt.json_response('movies/anticipated?page=%s' % page)

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'moviesAnticipated&page=%s' % (int(page) + 1), '', '', isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesBoxOffice(self):
        traktList = trakt.json_response('movies/boxoffice')

        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesUpdated(self, page):
        import datetime
        date = datetime.date.today() - datetime.timedelta(days=31)
        date = date.strftime('%Y-%m-%d')
        traktList = trakt.json_response('movies/updates/%s?page=%s' % (date, page))

        self.commonListBuilder(traktList)
        tools.addDirectoryItem(tools.lang(32019), 'moviesUpdated&page=%s' % (int(page) + 1), '', '', isFolder=True)
        tools.closeDirectory('movies', viewType=self.viewType)

    def moviesSearch(self):

        k = tools.showKeyboard('', tools.lang(32016))
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
        traktList = trakt.json_response('movies/%s/related' % args)
        self.commonListBuilder(traktList)
        tools.closeDirectory('movies', viewType=self.viewType)

    def movieGenres(self):
        tools.addDirectoryItem('Multi Select...', 'movieGenresGet', '', '', isFolder=True)
        genres = database.get(trakt.json_response, 24, 'genres/movies')
        for i in genres:
            tools.addDirectoryItem(i['name'], 'movieGenresGet&actionArgs=%s' % i['slug'], '', '', isFolder=True)
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
            genre_multiselect = tools.showDialog.multiselect(tools.addonName + ": Genre Selection", genre_display_list)
            if genre_multiselect is None: return
            for selection in genre_multiselect:
                genre_string += ', %s' % genres[selection]['slug']
            genre_string = genre_string[2:]
        else:
            genre_string = tools.unquote(args)

        traktList = trakt.json_response('movies/popular?genres=%s&page=%s' % (genre_string, page))
        self.commonListBuilder(traktList)
        tools.addDirectoryItem('Next', 'movieGenresGet&actionArgs=%s&page=%s' % (tools.quote(genre_string), int(page)+1),
                               '', '', isFolder=True)
        tools.closeDirectory('videos', viewType=self.viewType)

    ######################################################
    # MENU TOOLS
    ######################################################

    def commonListBuilder(self, traktList, nextPath=None):
        import traceback

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
                #Add Arguments to pass with item
                args = {}
                args['title'] = item['info']['title']
                args['year'] = item['info']['year']
                args['ids'] = item['ids']
                args['fanart'] = item['art']['fanart']
                args['info'] = item['info']
                args['art'] = item['art']
                name = '%s (%s)' % (item['info']['title'], item['info']['year'])

                args = tools.quote(json.dumps(args))

                # Begin Building Context Menu Items
                cm = []
                cm.append((tools.lang(32020), 'Container.Update(%s?action=moviesRelated&actionArgs=%s)' % (sysaddon, item['ids']['trakt'])))
                cm.append(('Source Select', 'PlayMedia(%s?action=getSources&source_select=true&actionArgs=%s)' % (sysaddon, args)))
                cm.append(('Trakt Manager', 'RunPlugin(%s?action=traktManager&actionArgs=%s)'
                           % (sysaddon, tools.quote(json.dumps(item['trakt_object'])))))
            except:
                continue

            if item is None: continue
            tools.addDirectoryItem(name, 'getSources', item['info'], item['art'], cm=cm,
                                   isFolder=False, isPlayable=True, actionArgs=args)


    def tmdbListWorker(self, trakt_object):
        tools.tmdb_sema.acquire()
        listItem = database.get(tmdbAPI.movieToListItem, '24', trakt_object)
        #Tried to use IMDB as a scraper source. Fuck it was slow
        #listItem = database.get(imdb_scraper.trakt_movie_to_list_item, '24', trakt_object)
        self.itemList.append(listItem)
        tools.tmdb_sema.release()

    def runThreads(self, join=True):
        for thread in self.threadList:
            thread.start()

        if join == True:
            for thread in self.threadList:
                thread.join()