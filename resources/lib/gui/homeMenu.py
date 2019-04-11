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
        tools.addDirectoryItem(tools.lang(32041), 'toolsMenu', '', '')
        # tools.addDirectoryItem('Test2', 'test2', None, None, isFolder=True)
        tools.closeDirectory('addons')

    def searchMenu(self):

        if tools.getSetting('searchHistory') == 'false':
            tools.addDirectoryItem(tools.lang(32039), 'moviesSearch', '', '')
        else:
            tools.addDirectoryItem(tools.lang(32039), 'moviesSearchHistory', '', '')

        if tools.getSetting('searchHistory') == 'false':
            tools.addDirectoryItem(tools.lang(32040), 'showsSearch', '', '')
        else:
            tools.addDirectoryItem(tools.lang(32040), 'showsSearchHistory', '', '')
        tools.closeDirectory('addons')

    def toolsMenu(self):

        tools.addDirectoryItem(tools.lang(32053), 'providerTools', None, None)
        if tools.getSetting('premiumize.enabled') == 'true' or tools.getSetting('realdebrid.enabled') == 'true':
            tools.addDirectoryItem(tools.lang(32054), 'debridServices', None, None)
        tools.addDirectoryItem(tools.lang(32042), 'clearCache', '', '', isFolder=False)
        tools.addDirectoryItem(tools.lang(32055), 'clearTorrentCache', '', '', isFolder=False)
        # tools.addDirectoryItem('Reset Silent Scrape Setting', 'resetSilent', '', '', isFolder=False)
        tools.addDirectoryItem(tools.lang(32056), 'openSettings', '', '', isFolder=False)
        tools.addDirectoryItem(tools.lang(32057), 'cleanInstall', None, None, isFolder=False)
        tools.addDirectoryItem('Trakt Sync Tools', 'traktSyncTools', None, None, isFolder=True)
        tools.closeDirectory('addons')

    def providerMenu(self):

        tools.addDirectoryItem(tools.lang(40082), 'manualProviderUpdate', None, None)
        tools.addDirectoryItem(tools.lang(40071), 'installProviders', None, None)
        tools.addDirectoryItem(tools.lang(40072), 'uninstallProviders', None, None)
        tools.addDirectoryItem(tools.lang(40073), 'adjustPackage&actionArgs=disabled', None, None)
        tools.addDirectoryItem(tools.lang(40074), 'adjustPackage&actionArgs=enabled', None, None)
        tools.addDirectoryItem(tools.lang(40076), 'adjustProviders&actionArgs=disabled', None, None)
        tools.addDirectoryItem(tools.lang(40077), 'adjustProviders&actionArgs=enabled', None, None)
        tools.closeDirectory('addons')

    def traktSyncTools(self):
        tools.addDirectoryItem('Flush activities', 'flushTraktActivities', None, None, isFolder=False)
        tools.addDirectoryItem('Force Sync Activites', 'forceTraktSync', None, None, isFolder=False)
        tools.addDirectoryItem('Clear all meta', 'flushTraktDBMeta', None, None, isFolder=False)
        tools.addDirectoryItem('Re-Build Database', 'rebuildTraktDatabase', None, None, isFolder=False)
        tools.closeDirectory('addons')



def runTest():
    pass



