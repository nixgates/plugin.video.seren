# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.indexers import trakt_auth_guard
from resources.lib.modules.globals import g


class Menus:

    @staticmethod
    def home():
        g.add_directory_item(g.get_language_string(30000),
                             action='moviesHome',
                             description=g.get_language_string(30364))
        g.add_directory_item(g.get_language_string(30002),
                             action='showsHome',
                             description=g.get_language_string(30365))
        if g.get_setting('trakt.auth'):
            g.add_directory_item(g.get_language_string(30001),
                                 action='myMovies',
                                 description=g.get_language_string(30366))
        if g.get_setting('trakt.auth'):
            g.add_directory_item(g.get_language_string(30003),
                                 action='myShows',
                                 description=g.get_language_string(30367))
        if g.debrid_available():
            g.add_directory_item(g.get_language_string(30173),
                                 action='myFiles',
                                 description=g.get_language_string(30368))
        g.add_directory_item(g.get_language_string(30013),
                             action='searchMenu',
                             description=g.get_language_string(30369))
        g.add_directory_item(g.get_language_string(30027),
                             action='toolsMenu',
                             description=g.get_language_string(30370))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def search_menu():
        if g.get_bool_setting('searchHistory'):
            g.add_directory_item(g.get_language_string(30025),
                                 action='moviesSearchHistory',
                                 description=g.get_language_string(30373))
            g.add_directory_item(g.get_language_string(30026),
                                 action='showsSearchHistory',
                                 description=g.get_language_string(30374))
        else:
            g.add_directory_item(g.get_language_string(30025),
                                 action='moviesSearch',
                                 description=g.get_language_string(30371))
            g.add_directory_item(g.get_language_string(30026),
                                 action='showsSearch',
                                 description=g.get_language_string(30372))

        g.add_directory_item(g.get_language_string(30327),
                             action='movieByActor',
                             description=g.get_language_string(30375))
        g.add_directory_item(g.get_language_string(30328),
                             action='showsByActor',
                             description=g.get_language_string(30376))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def tools_menu():
        g.add_directory_item(g.get_language_string(30037),
                             action='providerTools',
                             description=g.get_language_string(30377))
        if g.debrid_available():
            g.add_directory_item(g.get_language_string(30038),
                                 action='debridServices',
                                 description=g.get_language_string(30378))
        g.add_directory_item(g.get_language_string(30028),
                             action='clearCache',
                             is_folder=False,
                             description=g.get_language_string(30379))
        g.add_directory_item(g.get_language_string(30039),
                             action='clearTorrentCache',
                             is_folder=False,
                             description=g.get_language_string(30380))
        g.add_directory_item(g.get_language_string(30180),
                             action='clearSearchHistory',
                             is_folder=False,
                             description=g.get_language_string(30381))
        g.add_directory_item(g.get_language_string(30040),
                             action='openSettings',
                             is_folder=False,
                             description=g.get_language_string(30382))
        g.add_directory_item(g.get_language_string(30041),
                             action='cleanInstall',
                             is_folder=False,
                             description=g.get_language_string(30383))
        g.add_directory_item(g.get_language_string(30215),
                             action='traktSyncTools',
                             is_folder=True,
                             description=g.get_language_string(30384))
        g.add_directory_item('Download Manager',
                             action='downloadManagerView',
                             is_folder=False,
                             description='View Current Downloads')
        if g.get_bool_setting("skin.testmenu", False):
            g.add_directory_item('Window Tests',
                                 action='testWindows',
                                 description=g.get_language_string(30385))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def provider_menu():
        g.add_directory_item(g.get_language_string(30139),
                             action='manualProviderUpdate',
                             is_folder=False,
                             description=g.get_language_string(30386))
        g.add_directory_item(g.get_language_string(30140),
                             action='manageProviders',
                             is_folder=False,
                             description=g.get_language_string(30387))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    @trakt_auth_guard
    def trakt_sync_tools():
        g.add_directory_item(g.get_language_string(30216),
                             action='flushTraktActivities',
                             is_folder=False,
                             description=g.get_language_string(30388))
        g.add_directory_item(g.get_language_string(30217),
                             action='forceTraktSync',
                             is_folder=False,
                             description=g.get_language_string(30389))
        g.add_directory_item(g.get_language_string(30218),
                             action='rebuildTraktDatabase',
                             is_folder=False,
                             description=g.get_language_string(30390))
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def test_windows():
        g.add_directory_item(g.get_language_string(30462),
                             action='testPlayingNext',
                             is_folder=False,
                             description=g.get_language_string(30391))
        g.add_directory_item(g.get_language_string(30463),
                             action='testStillWatching',
                             is_folder=False,
                             description=g.get_language_string(30392))
        g.add_directory_item(g.get_language_string(30613),
                             action='testGetSourcesWindow',
                             is_folder=False,
                             description=g.get_language_string(30614))
        g.add_directory_item(g.get_language_string(30464),
                             action='testResolverWindow',
                             is_folder=False,
                             description=g.get_language_string(30393))
        g.add_directory_item(g.get_language_string(30465),
                             action='testSourceSelectWindow',
                             is_folder=False,
                             description=g.get_language_string(30394))
        g.add_directory_item(g.get_language_string(30466),
                             action='testManualCacheWindow',
                             is_folder=False,
                             description=g.get_language_string(30460))
        g.add_directory_item(g.get_language_string(30626),
                             action='testDownloadManagerWindow',
                             is_folder=False,
                             description=g.get_language_string(30625))
        g.close_directory(g.CONTENT_MENU)
