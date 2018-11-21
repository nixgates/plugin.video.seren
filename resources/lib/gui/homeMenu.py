import sys
from resources.lib.common import tools
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.indexers.tmdb import TMDBAPI

sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
trakt = TraktAPI()
tmdbAPI = TMDBAPI()

class Menus:

    def home(self):
        if tools.getSetting('trakt.auth') is not '':
            trakt = True
        else:
            trakt = False

        if trakt:
            tools.addDirectoryItem('Continue Watching', 'traktOnDeckHome', None, None)
        tools.addDirectoryItem(tools.lang(32001), 'moviesHome', None, None)
        tools.addDirectoryItem(tools.lang(32003), 'showsHome', None, None)
        if trakt:
            tools.addDirectoryItem(tools.lang(32002), 'myMovies', None, None)
        if trakt:
            tools.addDirectoryItem(tools.lang(32004), 'myShows', None, None)
        tools.addDirectoryItem(tools.lang(32016), 'searchMenu', None, None)
        tools.addDirectoryItem(tools.lang(32041), 'toolsMenu', '', '')
        #tools.addDirectoryItem('Test2', 'test2', None, None, isFolder=True)
        tools.closeDirectory('addons')

    def searchMenu(self):
        tools.addDirectoryItem(tools.lang(32039), 'moviesSearch', '', '')
        tools.addDirectoryItem(tools.lang(32040), 'showsSearch', '', '')
        tools.closeDirectory('addons')

    def toolsMenu(self):
        tools.addDirectoryItem('Provider Tools', 'providerTools', None, None)
        if tools.getSetting('premiumize.enabled') == 'true' or tools.getSetting('realdebrid.enabled') == 'true':
            tools.addDirectoryItem('Debrid Services', 'debridServices', None, None)
        tools.addDirectoryItem(tools.lang(32042), 'clearCache', '', '', isFolder=False)
        tools.addDirectoryItem('Clear Local Torrent cache', 'clearTorrentCache', '', '', isFolder=False)
        #tools.addDirectoryItem('Reset Silent Scrape Setting', 'resetSilent', '', '', isFolder=False)
        tools.addDirectoryItem('Open Settings Menu', 'openSettings', '', '', isFolder=False)
        tools.addDirectoryItem('Wipe Addon Data', 'cleanInstall', None, None, isFolder=False)
        tools.closeDirectory('addons')

    def providerMenu(self):
        tools.addDirectoryItem('Install Provider Package', 'installProviders', None, None)
        tools.addDirectoryItem('Uninstall Provider Package', 'uninstallProviders', None, None)
        tools.addDirectoryItem('Enable Providers', 'adjustProviders&actionArgs=disabled', None, None)
        tools.addDirectoryItem('Disable Providers', 'adjustProviders&actionArgs=enabled', None, None)
        tools.closeDirectory('addons')

    def traktOnDeck(self):
        tools.addDirectoryItem('Movies', 'onDeckMovies', None, None)
        tools.addDirectoryItem('Shows', 'onDeckShows', None, None)
        tools.closeDirectory('addons')

def runTest():
    pass



