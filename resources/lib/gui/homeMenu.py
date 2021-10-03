# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.indexers.trakt import trakt_auth_guard
from resources.lib.modules.globals import g


class Menus:

    @staticmethod
    def home():
        g.add_directory_item(g.get_language_string(30000),
                             action='moviesHome',
                             description=g.get_language_string(30386))
        g.add_directory_item(g.get_language_string(30002),
                             action='showsHome',
                             description=g.get_language_string(30387))
        if g.get_setting('trakt.auth'):
            g.add_directory_item(g.get_language_string(30001),
                                 action='myMovies',
                                 description=g.get_language_string(30388))
        if g.get_setting('trakt.auth'):
            g.add_directory_item(g.get_language_string(30003),
                                 action='myShows',
                                 description=g.get_language_string(30389))
        if g.debrid_available():
            g.add_directory_item(g.get_language_string(30186),
                                 action='myFiles',
                                 description=g.get_language_string(30390))
        g.add_directory_item(g.get_language_string(30013),
                             action='searchMenu',
                             description=g.get_language_string(30391))
        g.add_directory_item(g.get_language_string(30027),
                             action='toolsMenu',
                             description=g.get_language_string(30392))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def search_menu():
        if g.get_bool_setting('searchHistory'):
            g.add_directory_item(g.get_language_string(30025),
                                 action='moviesSearchHistory',
                                 description=g.get_language_string(30395))
            g.add_directory_item(g.get_language_string(30026),
                                 action='showsSearchHistory',
                                 description=g.get_language_string(30396))
        else:
            g.add_directory_item(g.get_language_string(30025),
                                 action='moviesSearch',
                                 description=g.get_language_string(30393))
            g.add_directory_item(g.get_language_string(30026),
                                 action='showsSearch',
                                 description=g.get_language_string(30394))

        g.add_directory_item(g.get_language_string(30348),
                             action='movieByActor',
                             description=g.get_language_string(30397))
        g.add_directory_item(g.get_language_string(30349),
                             action='showsByActor',
                             description=g.get_language_string(30398))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def tools_menu():
        g.add_directory_item(g.get_language_string(30037),
                             action='providerTools',
                             description=g.get_language_string(30399))
        if g.debrid_available():
            g.add_directory_item(g.get_language_string(30038),
                                 action='debridServices',
                                 description=g.get_language_string(30400))
        g.add_directory_item(g.get_language_string(30028),
                             action='clearCache',
                             is_folder=False,
                             description=g.get_language_string(30401))
        g.add_directory_item(g.get_language_string(30039),
                             action='clearTorrentCache',
                             is_folder=False,
                             description=g.get_language_string(30402))
        g.add_directory_item(g.get_language_string(30193),
                             action='clearSearchHistory',
                             is_folder=False,
                             description=g.get_language_string(30403))
        g.add_directory_item(g.get_language_string(30040),
                             action='openSettings',
                             is_folder=False,
                             description=g.get_language_string(30404))
        g.add_directory_item(g.get_language_string(30041),
                             action='cleanInstall',
                             is_folder=False,
                             description=g.get_language_string(30405))
        g.add_directory_item(g.get_language_string(30228),
                             action='traktSyncTools',
                             is_folder=True,
                             description=g.get_language_string(30406))
        g.add_directory_item('Download Manager',
                             action='downloadManagerView',
                             is_folder=False,
                             description='View Current Downloads')
        if g.get_bool_setting("skin.testmenu", False):
            g.add_directory_item('Window Tests',
                                 action='testWindows',
                                 description=g.get_language_string(30407))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def provider_menu():
        g.add_directory_item(g.get_language_string(30146),
                             action='manualProviderUpdate',
                             is_folder=False,
                             description=g.get_language_string(30408))
        g.add_directory_item(g.get_language_string(30147),
                             action='manageProviders',
                             is_folder=False,
                             description=g.get_language_string(30409))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    @trakt_auth_guard
    def trakt_sync_tools():
        g.add_directory_item(g.get_language_string(30229),
                             action='flushTraktActivities',
                             is_folder=False,
                             description=g.get_language_string(30410))
        g.add_directory_item(g.get_language_string(30230),
                             action='forceTraktSync',
                             is_folder=False,
                             description=g.get_language_string(30411))
        g.add_directory_item(g.get_language_string(30231),
                             action='rebuildTraktDatabase',
                             is_folder=False,
                             description=g.get_language_string(30412))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def test_windows():
        g.add_directory_item(g.get_language_string(30486),
                             action='testPlayingNext',
                             is_folder=False,
                             description=g.get_language_string(30413))
        g.add_directory_item(g.get_language_string(30487),
                             action='testStillWatching',
                             is_folder=False,
                             description=g.get_language_string(30414))
        g.add_directory_item(g.get_language_string(30488),
                             action='testResolverWindow',
                             is_folder=False,
                             description=g.get_language_string(30415))
        g.add_directory_item(g.get_language_string(30489),
                             action='testSourceSelectWindow',
                             is_folder=False,
                             description=g.get_language_string(30416))
        g.add_directory_item(g.get_language_string(30490),
                             action='testManualCacheWindow',
                             is_folder=False,
                             description=g.get_language_string(30484))
        g.close_directory(g.CONTENT_MENU)
