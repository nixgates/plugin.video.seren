from resources.lib.indexers import trakt_auth_guard
from resources.lib.modules.globals import g


class Menus:
    @staticmethod
    def home():
        g.add_directory_item(
            g.get_language_string(30000),
            action='moviesHome',
            description=g.get_language_string(30364),
            menu_item=g.create_icon_dict("movies", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30002),
            action='showsHome',
            description=g.get_language_string(30365),
            menu_item=g.create_icon_dict("shows", g.ICONS_PATH),
        )
        if g.get_setting('trakt.auth'):
            g.add_directory_item(
                g.get_language_string(30001),
                action='myMovies',
                description=g.get_language_string(30366),
                menu_item=g.create_icon_dict("movies_trakt", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30003),
                action='myShows',
                description=g.get_language_string(30367),
                menu_item=g.create_icon_dict("shows_trakt", g.ICONS_PATH),
            )
        if g.debrid_available():
            g.add_directory_item(
                g.get_language_string(30173),
                action='myFiles',
                description=g.get_language_string(30368),
                menu_item=g.create_icon_dict("cloud_files", g.ICONS_PATH),
            )
        g.add_directory_item(
            g.get_language_string(30013),
            action='searchMenu',
            description=g.get_language_string(30369),
            menu_item=g.create_icon_dict("search", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30027),
            action='toolsMenu',
            description=g.get_language_string(30370),
            menu_item=g.create_icon_dict("tools", g.ICONS_PATH),
        )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def search_menu():
        if g.get_bool_setting('searchHistory'):
            g.add_directory_item(
                g.get_language_string(30025),
                action='moviesSearchHistory',
                description=g.get_language_string(30373),
                menu_item=g.create_icon_dict("movies_search", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30026),
                action='showsSearchHistory',
                description=g.get_language_string(30374),
                menu_item=g.create_icon_dict("shows_search", g.ICONS_PATH),
            )
        else:
            g.add_directory_item(
                g.get_language_string(30025),
                action='moviesSearch',
                description=g.get_language_string(30371),
                menu_item=g.create_icon_dict("movies_search", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30026),
                action='showsSearch',
                description=g.get_language_string(30372),
                menu_item=g.create_icon_dict("shows_search", g.ICONS_PATH),
            )

        g.add_directory_item(
            g.get_language_string(30327),
            action='movieByActor',
            description=g.get_language_string(30375),
            menu_item=g.create_icon_dict("movies_actor", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30328),
            action='showsByActor',
            description=g.get_language_string(30376),
            menu_item=g.create_icon_dict("shows_actor", g.ICONS_PATH),
        )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def tools_menu():
        g.add_directory_item(
            g.get_language_string(30037),
            action='providerTools',
            description=g.get_language_string(30377),
            menu_item=g.create_icon_dict("tools", g.ICONS_PATH),
        )
        if g.debrid_available():
            g.add_directory_item(
                g.get_language_string(30038),
                action='debridServices',
                description=g.get_language_string(30378),
                menu_item=g.create_icon_dict("cloud", g.ICONS_PATH),
            )
        g.add_directory_item(
            g.get_language_string(30028),
            action='clearCache',
            is_folder=False,
            description=g.get_language_string(30379),
            menu_item=g.create_icon_dict("clear_cache", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30039),
            action='clearTorrentCache',
            is_folder=False,
            description=g.get_language_string(30380),
            menu_item=g.create_icon_dict("clear_cache", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30180),
            action='clearSearchHistory',
            is_folder=False,
            description=g.get_language_string(30381),
            menu_item=g.create_icon_dict("clear_search", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30040),
            action='openSettings',
            is_folder=False,
            description=g.get_language_string(30382),
            menu_item=g.create_icon_dict("settings", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30041),
            action='cleanInstall',
            is_folder=False,
            description=g.get_language_string(30383),
            menu_item=g.create_icon_dict("clear", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30215),
            action='traktSyncTools',
            is_folder=True,
            description=g.get_language_string(30384),
            menu_item=g.create_icon_dict("trakt", g.ICONS_PATH),
        )
        g.add_directory_item(
            'Download Manager',
            action='downloadManagerView',
            is_folder=False,
            description='View Current Downloads',
            menu_item=g.create_icon_dict("download", g.ICONS_PATH),
        )
        if g.get_bool_setting("skin.testmenu", False):
            g.add_directory_item(
                'Window Tests',
                action='testWindows',
                description=g.get_language_string(30385),
                menu_item=g.create_icon_dict("test", g.ICONS_PATH),
            )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def provider_menu():
        g.add_directory_item(
            g.get_language_string(30139),
            action='manualProviderUpdate',
            is_folder=False,
            description=g.get_language_string(30386),
            menu_item=g.create_icon_dict("providers_update", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30140),
            action='manageProviders',
            is_folder=False,
            description=g.get_language_string(30387),
            menu_item=g.create_icon_dict("providers", g.ICONS_PATH),
        )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    @trakt_auth_guard
    def trakt_sync_tools():
        g.add_directory_item(
            g.get_language_string(30216),
            action='flushTraktActivities',
            is_folder=False,
            description=g.get_language_string(30388),
            menu_item=g.create_icon_dict("trakt_reset", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30217),
            action='forceTraktSync',
            is_folder=False,
            description=g.get_language_string(30389),
            menu_item=g.create_icon_dict("trakt_sync", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30218),
            action='rebuildTraktDatabase',
            is_folder=False,
            description=g.get_language_string(30390),
            menu_item=g.create_icon_dict("trakt_rebuild", g.ICONS_PATH),
        )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def test_windows():
        g.add_directory_item(
            g.get_language_string(30462),
            action='testPlayingNext',
            is_folder=False,
            description=g.get_language_string(30391),
            menu_item=g.create_icon_dict("test", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30463),
            action='testStillWatching',
            is_folder=False,
            description=g.get_language_string(30392),
            menu_item=g.create_icon_dict("test", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30613),
            action='testGetSourcesWindow',
            is_folder=False,
            description=g.get_language_string(30614),
            menu_item=g.create_icon_dict("test", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30464),
            action='testResolverWindow',
            is_folder=False,
            description=g.get_language_string(30393),
            menu_item=g.create_icon_dict("test", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30465),
            action='testSourceSelectWindow',
            is_folder=False,
            description=g.get_language_string(30394),
            menu_item=g.create_icon_dict("test", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30466),
            action='testManualCacheWindow',
            is_folder=False,
            description=g.get_language_string(30460),
            menu_item=g.create_icon_dict("test", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30626),
            action='testDownloadManagerWindow',
            is_folder=False,
            description=g.get_language_string(30625),
            menu_item=g.create_icon_dict("test", g.ICONS_PATH),
        )
        g.close_directory(g.CONTENT_MENU)
