# -*- coding: utf-8 -*-

import sys, os, xbmc
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

        tools.addDirectoryItem(tools.lang(32001).encode('utf-8'), 'moviesHome', None, os.path.join(tools.IMAGES_PATH, "movies.png"))
        tools.addDirectoryItem(tools.lang(32003).encode('utf-8'), 'showsHome', None, os.path.join(tools.IMAGES_PATH, "tvshows.png"))
        if trakt:
            tools.addDirectoryItem(tools.lang(32002).encode('utf-8'), 'myMovies', None, os.path.join(tools.IMAGES_PATH, "trakt.png"))
            tools.addDirectoryItem(tools.lang(32004).encode('utf-8'), 'myShows', None, os.path.join(tools.IMAGES_PATH, "trakt.png"))
        tools.addDirectoryItem(tools.lang(32016).encode('utf-8'), 'searchMenu', None, os.path.join(tools.IMAGES_PATH, "search.png"))
        tools.addDirectoryItem(tools.lang(32041).encode('utf-8'), 'toolsMenu', '', os.path.join(tools.IMAGES_PATH, "tools.png"))
        #tools.addDirectoryItem('Test2', 'test2', None, None, isFolder=True)
        tools.closeDirectory('addons', cacheToDisc=True)

    def searchMenu(self):
        tools.addDirectoryItem(tools.lang(32039).encode('utf-8'), 'moviesSearch', '', '')
        tools.addDirectoryItem(tools.lang(32040).encode('utf-8'), 'showsSearch', '', '')
        tools.closeDirectory('addons', cacheToDisc=True)

    def toolsMenu(self):
        tools.addDirectoryItem(tools.lang(32053).encode('utf-8'), 'providerTools', None, None)
        if tools.getSetting('premiumize.enabled') == 'true' or tools.getSetting('realdebrid.enabled') == 'true':
            tools.addDirectoryItem(tools.lang(32054).encode('utf-8'), 'debridServices', None, None)
        tools.addDirectoryItem(tools.lang(32042).encode('utf-8'), 'clearCache', '', '', isFolder=False)
        tools.addDirectoryItem(tools.lang(32055).encode('utf-8'), 'clearTorrentCache', '', '', isFolder=False)
        #tools.addDirectoryItem('Reset Silent Scrape Setting', 'resetSilent', '', '', isFolder=False)
        tools.addDirectoryItem(tools.lang(32056).encode('utf-8'), 'openSettings', '', '', isFolder=False)
        tools.addDirectoryItem(tools.lang(32057).encode('utf-8'), 'cleanInstall', None, None, isFolder=False)
        tools.closeDirectory('addons', cacheToDisc=True)

    def providerMenu(self):
        tools.addDirectoryItem(tools.lang(40082).encode('utf-8'), 'manualProviderUpdate', None, None)
        tools.addDirectoryItem(tools.lang(40071).encode('utf-8'), 'installProviders', None, None)
        tools.addDirectoryItem(tools.lang(40072).encode('utf-8'), 'uninstallProviders', None, None)
        tools.addDirectoryItem(tools.lang(40073).encode('utf-8'), 'adjustPackage&actionArgs=disabled', None, None)
        tools.addDirectoryItem(tools.lang(40074).encode('utf-8'), 'adjustPackage&actionArgs=enabled', None, None)
        tools.addDirectoryItem(tools.lang(40076).encode('utf-8'), 'adjustProviders&actionArgs=disabled', None, None)
        tools.addDirectoryItem(tools.lang(40077).encode('utf-8'), 'adjustProviders&actionArgs=enabled', None, None)
        tools.closeDirectory('addons', cacheToDisc=True)


def runTest():
    pass



