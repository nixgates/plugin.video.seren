# -*- coding: utf-8 -*-

import sys
from resources.lib.common import tools
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.indexers.tmdb import TMDBAPI

try:
    sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
except:
    pass

trakt = TraktAPI()
tmdbAPI = TMDBAPI()

class Menus:

    def home(self):
        if tools.getSetting('trakt.auth') is not '':
            trakt = True
        else:
            trakt = False

        tools.addDirectoryItem(tools.lang(32001), 'moviesHome', None, None)
        tools.addDirectoryItem(tools.lang(32003), 'showsHome', None, None)
        if trakt:
            tools.addDirectoryItem(tools.lang(32002), 'myMovies', None, None)
        if trakt:
            tools.addDirectoryItem(tools.lang(32004), 'myShows', None, None)
        if tools.premiumize_enabled() or tools.real_debrid_enabled():
            tools.addDirectoryItem(tools.lang(40126), 'myFiles', None, None)
        tools.addDirectoryItem(tools.lang(32016), 'searchMenu', None, None)
        tools.addDirectoryItem(tools.lang(32041), 'toolsMenu')
        # tools.addDirectoryItem('Test2', 'test2', None, None, isFolder=True)
        tools.closeDirectory('addons')

    def searchMenu(self):

        if tools.getSetting('searchHistory') == 'false':
            tools.addDirectoryItem(tools.lang(32039), 'moviesSearch', isFolder=True, isPlayable=False)
        else:
            tools.addDirectoryItem(tools.lang(32039), 'moviesSearchHistory')

        if tools.getSetting('searchHistory') == 'false':
            tools.addDirectoryItem(tools.lang(32040), 'showsSearch', isFolder=True, isPlayable=False)
        else:
            tools.addDirectoryItem(tools.lang(32040), 'showsSearchHistory')
            
        tools.addDirectoryItem(tools.lang(40346), 'movieByActor')
        tools.addDirectoryItem(tools.lang(40347), 'showsByActor')
        
        tools.closeDirectory('addons')

    def toolsMenu(self):

        tools.addDirectoryItem(tools.lang(32053), 'providerTools', None, None)
        if tools.getSetting('premiumize.enabled') == 'true' or tools.getSetting('realdebrid.enabled') == 'true':
            tools.addDirectoryItem(tools.lang(32054), 'debridServices', None, None)
        tools.addDirectoryItem(tools.lang(32042), 'clearCache', isFolder=False)
        tools.addDirectoryItem(tools.lang(32055), 'clearTorrentCache', isFolder=False)
        tools.addDirectoryItem(tools.lang(40140), 'clearSearchHistory', isFolder=False)
        tools.addDirectoryItem(tools.lang(32056), 'openSettings', isFolder=False)
        tools.addDirectoryItem(tools.lang(32057), 'cleanInstall', None, None, isFolder=False)
        tools.addDirectoryItem(tools.lang(40177), 'traktSyncTools', None, None, isFolder=True)
        tools.closeDirectory('addons')

    def providerMenu(self):

        tools.addDirectoryItem(tools.lang(40082), 'manualProviderUpdate', None, None)
        tools.addDirectoryItem(tools.lang(40083), 'manageProviders', None, None)
        tools.closeDirectory('addons')

    def traktSyncTools(self):
        tools.addDirectoryItem(tools.lang(40178), 'flushTraktActivities', None, None, isFolder=False)
        tools.addDirectoryItem(tools.lang(40179), 'forceTraktSync', None, None, isFolder=False)
        tools.addDirectoryItem(tools.lang(40180), 'flushTraktDBMeta', None, None, isFolder=False)
        tools.addDirectoryItem(tools.lang(40181), 'rebuildTraktDatabase', None, None, isFolder=False)
        tools.closeDirectory('addons')
