# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.indexers.trakt import trakt_auth_guard
from resources.lib.modules.globals import g


class Menus:

    @staticmethod
    def home():
        g.add_directory_item(g.get_language_string(30000),
                             action='moviesHome',
                             description=g.get_language_string(30397))
        g.add_directory_item(g.get_language_string(30002),
                             action='showsHome',
                             description=g.get_language_string(30398))
        if g.get_setting('trakt.auth'):
            g.add_directory_item(g.get_language_string(30001),
                                 action='myMovies',
                                 description=g.get_language_string(30399))
        if g.get_setting('trakt.auth'):
            g.add_directory_item(g.get_language_string(30003),
                                 action='myShows',
                                 description=g.get_language_string(30400))
        if g.debrid_available():
            g.add_directory_item(g.get_language_string(30190),
                                 action='myFiles',
                                 description=g.get_language_string(30401))
        g.add_directory_item(g.get_language_string(30013),
                             action='searchMenu',
                             description=g.get_language_string(30402))
        g.add_directory_item(g.get_language_string(30028),
                             action='toolsMenu',
                             description=g.get_language_string(30403))
        g.close_directory(g.CONTENT_FOLDER)

    @staticmethod
    def search_menu():
        if g.get_bool_setting('searchHistory'):
            g.add_directory_item(g.get_language_string(30026),
                                 action='moviesSearchHistory',
                                 description=g.get_language_string(30406))
            g.add_directory_item(g.get_language_string(30027),
                                 action='showsSearchHistory',
                                 description=g.get_language_string(30407))
        else:
            g.add_directory_item(g.get_language_string(30026),
                                 action='moviesSearch',
                                 description=g.get_language_string(30404))
            g.add_directory_item(g.get_language_string(30027),
                                 action='showsSearch',
                                 description=g.get_language_string(30405))

        g.add_directory_item(g.get_language_string(30358),
                             action='movieByActor',
                             description=g.get_language_string(30408))
        g.add_directory_item(g.get_language_string(30359),
                             action='showsByActor',
                             description=g.get_language_string(30409))
        g.close_directory(g.CONTENT_FOLDER)

    @staticmethod
    def tools_menu():
        g.add_directory_item(g.get_language_string(30038),
                             action='providerTools',
                             description=g.get_language_string(30410))
        if g.debrid_available():
            g.add_directory_item(g.get_language_string(30039),
                                 action='debridServices',
                                 description=g.get_language_string(30411))
        g.add_directory_item(g.get_language_string(30029),
                             action='clearCache',
                             is_folder=False,
                             description=g.get_language_string(30412))
        g.add_directory_item(g.get_language_string(30040),
                             action='clearTorrentCache',
                             is_folder=False,
                             description=g.get_language_string(30413))
        g.add_directory_item(g.get_language_string(30202),
                             action='clearSearchHistory',
                             is_folder=False,
                             description=g.get_language_string(30414))
        g.add_directory_item(g.get_language_string(30041),
                             action='openSettings',
                             is_folder=False,
                             description=g.get_language_string(30415))
        g.add_directory_item(g.get_language_string(30042),
                             action='cleanInstall',
                             is_folder=False,
                             description=g.get_language_string(30416))
        g.add_directory_item(g.get_language_string(30237),
                             action='traktSyncTools',
                             is_folder=True,
                             description=g.get_language_string(30417))
        # g.add_directory_item('Window Tests',
        #                      action='testWindows',
        #                      description=g.get_language_string(30418))
        g.add_directory_item('Download Manager',
                             action='downloadManagerView',
                             description='View Current Downloads')
        g.close_directory(g.CONTENT_FOLDER)

    @staticmethod
    def provider_menu():
        g.add_directory_item(g.get_language_string(30150),
                             action='manualProviderUpdate',
                             is_folder=False,
                             description=g.get_language_string(30419))
        g.add_directory_item(g.get_language_string(30151),
                             action='manageProviders',
                             is_folder=False,
                             description=g.get_language_string(30420))
        g.close_directory(g.CONTENT_FOLDER)

    @staticmethod
    @trakt_auth_guard
    def trakt_sync_tools():
        g.add_directory_item(g.get_language_string(30238),
                             action='flushTraktActivities',
                             is_folder=False,
                             description=g.get_language_string(30421))
        g.add_directory_item(g.get_language_string(30239),
                             action='forceTraktSync',
                             is_folder=False,
                             description=g.get_language_string(30422))
        g.add_directory_item(g.get_language_string(30240),
                             action='flushTraktDBMeta',
                             is_folder=False,
                             description=g.get_language_string(30423))
        g.add_directory_item(g.get_language_string(30241),
                             action='rebuildTraktDatabase',
                             is_folder=False,
                             description=g.get_language_string(30424))
        g.close_directory(g.CONTENT_FOLDER)

    @staticmethod
    def test_windows():
        g.add_directory_item(g.get_language_string(30498),
                             action='testPlayingNext',
                             is_folder=False,
                             description=g.get_language_string(30425))
        g.add_directory_item(g.get_language_string(30499),
                             action='testStillWatching',
                             is_folder=False,
                             description=g.get_language_string(30426))
        g.add_directory_item(g.get_language_string(30500),
                             action='testResolverWindow',
                             is_folder=False,
                             description=g.get_language_string(30427))
        g.add_directory_item(g.get_language_string(30501),
                             action='testSourceSelectWindow',
                             is_folder=False,
                             description=g.get_language_string(30428))
        g.add_directory_item(g.get_language_string(30502),
                             action='testManualCacheWindow',
                             is_folder=False,
                             description=g.get_language_string(30496))
        g.close_directory(g.CONTENT_FOLDER)
