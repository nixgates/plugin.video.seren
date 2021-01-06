# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc
import xbmcgui

"""
    Dispatch module
"""
from resources.lib.modules.globals import g
from resources.lib.modules.exceptions import NoPlayableSourcesException


def dispatch(params):
    url = params.get("url")
    action = params.get("action")
    action_args = params.get("action_args")
    pack_select = params.get("packSelect")
    source_select = params.get("source_select") == "true"
    overwrite_cache = params.get("seren_reload") == "true"
    resume = params.get("resume")
    force_resume_check = params.get("forceresumecheck") == "true"
    force_resume_off = params.get("forceresumeoff") == "true"
    force_resume_on = params.get("forceresumeon") == "true"
    smart_url_arg = params.get("smartPlay") == "true"
    mediatype = params.get("mediatype")
    endpoint = params.get("endpoint")

    g.log("Seren, Running Path - {}".format(g.REQUEST_PARAMS))

    if action is None:
        from resources.lib.gui import homeMenu

        homeMenu.Menus().home()

    if action == "genericEndpoint":
        if mediatype == "movies":
            from resources.lib.gui.movieMenus import Menus
        else:
            from resources.lib.gui.tvshowMenus import Menus
        Menus().generic_endpoint(endpoint)

    elif action == "forceResumeShow":
        from resources.lib.modules import smartPlay
        from resources.lib.common import tools

        smartPlay.SmartPlay(tools.get_item_information(action_args)).resume_show()

    elif action == "moviesHome":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().discover_movies()

    elif action == "moviesUpdated":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_updated()

    elif action == "moviesRecommended":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_recommended()

    elif action == "moviesSearch":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_search(action_args)

    elif action == "moviesSearchResults":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_search_results(action_args)

    elif action == "moviesSearchHistory":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_search_history()

    elif action == "myMovies":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().my_movies()

    elif action == "moviesMyCollection":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().my_movie_collection()

    elif action == "moviesMyWatchlist":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().my_movie_watchlist()

    elif action == "moviesRelated":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_related(action_args)

    elif action == "colorPicker":
        g.color_picker()

    elif action == "authTrakt":
        from resources.lib.indexers import trakt

        trakt.TraktAPI().auth()

    elif action == "revokeTrakt":
        from resources.lib.indexers import trakt

        trakt.TraktAPI().revoke_auth()

    elif action == "getSources":
        from resources.lib.modules.smartPlay import SmartPlay
        from resources.lib.common import tools
        from resources.lib.modules import helpers

        item_information = tools.get_item_information(action_args)
        smart_play = SmartPlay(item_information)
        background = None
        resolver_window = None

        try:
            # Check to confirm user has a debrid provider authenticated and enabled
            if not g.premium_check():
                xbmcgui.Dialog().ok(
                    g.ADDON_NAME,
                    tools.create_multiline_message(
                        line1=g.get_language_string(30208),
                        line2=g.get_language_string(30209),
                    ),
                )
                return None

            # workaround for widgets not generating a playlist on playback request
            play_list = smart_play.playlist_present_check(smart_url_arg)

            if play_list:
                g.log("Cancelling non playlist playback", "warning")
                xbmc.Player().play(g.PLAYLIST)
                return

            resume_time = smart_play.handle_resume_prompt(
                resume, force_resume_off, force_resume_on, force_resume_check
            )
            background = helpers.show_persistent_window_if_required(item_information)
            sources = helpers.SourcesHelper().get_sources(
                action_args, overwrite_cache=overwrite_cache
            )

            if sources is None:
                return
            if item_information["info"]["mediatype"] == "episode":
                source_select_style = "Episodes"
            else:
                source_select_style = "Movie"

            if (
                g.get_int_setting("general.playstyle{}".format(source_select_style))
                == 1
                or source_select
            ):

                if background:
                    background.set_text(g.get_language_string(30198))
                from resources.lib.modules import sourceSelect

                stream_link = sourceSelect.source_select(
                    sources[0], sources[1], item_information
                )
            else:
                if background:
                    background.set_text(g.get_language_string(30032))
                stream_link = helpers.Resolverhelper().resolve_silent_or_visible(
                    sources[1], sources[2], pack_select
                )
                if stream_link is None:
                    g.close_busy_dialog()
                    g.notification(
                        g.ADDON_NAME, g.get_language_string(30033), time=5000
                    )

            g.show_busy_dialog()

            if background:
                background.close()
                del background

            if not stream_link:
                raise NoPlayableSourcesException

            from resources.lib.modules import player

            player.SerenPlayer().play_source(
                stream_link, item_information, resume_time=resume_time
            )

        except NoPlayableSourcesException:
            try:
                background.close()
                del background
            except (UnboundLocalError, AttributeError):
                pass
            try:
                resolver_window.close()
                del resolver_window
            except (UnboundLocalError, AttributeError):
                pass

            g.cancel_playback()

    elif action == "preScrape":

        from resources.lib.database.skinManager import SkinManager
        from resources.lib.modules import helpers

        try:
            from resources.lib.common import tools

            item_information = tools.get_item_information(action_args)

            if item_information["info"]["mediatype"] == "episode":
                source_select_style = "Episodes"
            else:
                source_select_style = "Movie"

            sources = helpers.SourcesHelper().get_sources(action_args)
            if (
                g.get_int_setting("general.playstyle{}".format(source_select_style))
                == 0
                and sources
            ):
                from resources.lib.modules import resolver

                helpers.Resolverhelper().resolve_silent_or_visible(
                    sources[1], sources[2], pack_select
                )
        finally:
            g.set_setting("general.tempSilent", "false")

        g.log("Pre-scraping completed")

    elif action == "authRealDebrid":
        from resources.lib.debrid import real_debrid

        real_debrid.RealDebrid().auth()

    elif action == "showsHome":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().discover_shows()

    elif action == "myShows":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_shows()

    elif action == "showsMyCollection":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_shows_collection()

    elif action == "showsMyWatchlist":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_shows_watchlist()

    elif action == "showsMyProgress":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_show_progress()

    elif action == "showsMyRecentEpisodes":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_recent_episodes()

    elif action == "showsRecommended":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_recommended()

    elif action == "showsUpdated":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_updated()

    elif action == "showsSearch":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_search(action_args)

    elif action == "showsSearchResults":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_search_results(action_args)

    elif action == "showsSearchHistory":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_search_history()

    elif action == "showSeasons":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().show_seasons(action_args)

    elif action == "seasonEpisodes":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().season_episodes(action_args)

    elif action == "showsRelated":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_related(action_args)

    elif action == "showYears":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_years(action_args)

    elif action == "searchMenu":
        from resources.lib.gui import homeMenu

        homeMenu.Menus().search_menu()

    elif action == "toolsMenu":
        from resources.lib.gui import homeMenu

        homeMenu.Menus().tools_menu()

    elif action == "clearCache":
        from resources.lib.common import tools

        g.clear_cache()

    elif action == "traktManager":
        from resources.lib.indexers import trakt
        from resources.lib.common import tools

        trakt.TraktManager(tools.get_item_information(action_args))

    elif action == "onDeckShows":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().on_deck_shows()

    elif action == "onDeckMovies":
        from resources.lib.gui.movieMenus import Menus

        Menus().on_deck_movies()

    elif action == "cacheAssist":
        from resources.lib.modules.cacheAssist import CacheAssistHelper

        CacheAssistHelper().auto_cache(action_args)

    elif action == "tvGenres":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_genres()

    elif action == "showGenresGet":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_genre_list(action_args)

    elif action == "movieGenres":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_genres()

    elif action == "movieGenresGet":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_genre_list(action_args)

    elif action == "shufflePlay":
        from resources.lib.modules import smartPlay

        smartPlay.SmartPlay(action_args).shuffle_play()

    elif action == "resetSilent":
        g.set_setting("general.tempSilent", "false")
        g.notification(
            "{}: {}".format(g.ADDON_NAME, g.get_language_string(30329)),
            g.get_language_string(30034),
            time=5000,
        )

    elif action == "clearTorrentCache":
        from resources.lib.database.torrentCache import TorrentCache

        TorrentCache().clear_all()

    elif action == "openSettings":
        xbmc.executebuiltin("Addon.OpenSettings({})".format(g.ADDON_ID))

    elif action == "myTraktLists":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().my_trakt_lists(mediatype)

    elif action == "myLikedLists":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().my_liked_lists(mediatype)

    elif action == "TrendingLists":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().trending_lists(mediatype)

    elif action == "PopularLists":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().popular_lists(mediatype)

    elif action == "traktList":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().get_list_items()

    elif action == "nonActiveAssistClear":
        from resources.lib.gui import debridServices

        debridServices.Menus().assist_non_active_clear()

    elif action == "debridServices":
        from resources.lib.gui import debridServices

        debridServices.Menus().home()

    elif action == "cacheAssistStatus":
        from resources.lib.gui import debridServices

        debridServices.Menus().get_assist_torrents()

    elif action == "premiumize_transfers":
        from resources.lib.gui import debridServices

        debridServices.Menus().list_premiumize_transfers()

    elif action == "showsNextUp":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_next_up()

    elif action == "runMaintenance":
        from resources.lib.common import maintenance

        maintenance.run_maintenance()

    elif action == "providerTools":
        from resources.lib.gui import homeMenu

        homeMenu.Menus().provider_menu()

    elif action == "installProviders":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        ProviderInstallManager().install_package(action_args)

    elif action == "uninstallProviders":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        ProviderInstallManager().uninstall_package()

    elif action == "showsNew":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_new()

    elif action == "realdebridTransfers":
        from resources.lib.gui import debridServices

        debridServices.Menus().list_rd_transfers()

    elif action == "cleanInstall":
        from resources.lib.common import maintenance

        maintenance.wipe_install()

    elif action == "premiumizeCleanup":
        from resources.lib.common import maintenance

        maintenance.premiumize_transfer_cleanup()

    elif action == "manualProviderUpdate":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        ProviderInstallManager().manual_update()

    elif action == "clearSearchHistory":
        from resources.lib.database.searchHistory import SearchHistory

        SearchHistory().clear_search_history(mediatype)

    elif action == "externalProviderInstall":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        confirmation = xbmcgui.Dialog().yesno(
            g.ADDON_NAME, g.get_language_string(30182)
        )
        if confirmation == 0:
            return
        ProviderInstallManager().install_package(1, url=url)

    elif action == "externalProviderUninstall":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        confirmation = xbmcgui.Dialog().yesno(
            g.ADDON_NAME, g.get_language_string(30184).format(url)
        )
        if confirmation == 0:
            return
        ProviderInstallManager().uninstall_package(package=url, silent=False)

    elif action == "showsNetworks":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_networks()

    elif action == "showsNetworkShows":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_networks_results(action_args)

    elif action == "movieYears":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_years()

    elif action == "movieYearsMovies":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movie_years_results(action_args)

    elif action == "syncTraktActivities":
        from resources.lib.database.trakt_sync.activities import TraktSyncDatabase

        TraktSyncDatabase().sync_activities()

    elif action == "traktSyncTools":
        from resources.lib.gui import homeMenu

        homeMenu.Menus().trakt_sync_tools()

    elif action == "flushTraktActivities":
        from resources.lib.database import trakt_sync

        trakt_sync.TraktSyncDatabase().flush_activities()

    elif action == "flushTraktDBMeta":
        from resources.lib.database import trakt_sync

        trakt_sync.TraktSyncDatabase().clear_all_meta()

    elif action == "myFiles":
        from resources.lib.gui import myFiles

        myFiles.Menus().home()

    elif action == "myFilesFolder":
        from resources.lib.gui import myFiles

        myFiles.Menus().my_files_folder(action_args)

    elif action == "myFilesPlay":
        from resources.lib.gui import myFiles

        myFiles.Menus().my_files_play(action_args)

    elif action == "forceTraktSync":
        from resources.lib.database.trakt_sync.activities import TraktSyncDatabase

        trakt_db = TraktSyncDatabase()
        trakt_db.flush_activities()
        trakt_db.sync_activities()

    elif action == "rebuildTraktDatabase":
        from resources.lib.database.trakt_sync import TraktSyncDatabase

        TraktSyncDatabase().re_build_database()

    elif action == "myUpcomingEpisodes":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_upcoming_episodes()

    elif action == "myWatchedEpisodes":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_watched_episode()

    elif action == "myWatchedMovies":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().my_watched_movies()

    elif action == "showsByActor":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_by_actor(action_args)

    elif action == "movieByActor":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_by_actor(action_args)

    elif action == "playFromRandomPoint":
        from resources.lib.modules import smartPlay

        smartPlay.SmartPlay(action_args).play_from_random_point()

    elif action == "refreshProviders":
        from resources.lib.modules.providers import CustomProviders

        providers = CustomProviders()
        providers.update_known_providers()
        providers.poll_database()

    elif action == "installSkin":
        from resources.lib.database.skinManager import SkinManager

        SkinManager().install_skin()

    elif action == "uninstallSkin":
        from resources.lib.database.skinManager import SkinManager

        SkinManager().uninstall_skin()

    elif action == "switchSkin":
        from resources.lib.database.skinManager import SkinManager

        SkinManager().switch_skin()

    elif action == "manageProviders":
        g.show_busy_dialog()
        from resources.lib.gui.windows.provider_packages import ProviderPackages
        from resources.lib.database.skinManager import SkinManager

        window = ProviderPackages(
            *SkinManager().confirm_skin_path("provider_packages.xml")
        )
        window.doModal()
        del window

    elif action == "flatEpisodes":
        from resources.lib.gui.tvshowMenus import Menus

        Menus().flat_episode_list(action_args)

    elif action == "runPlayerDialogs":
        from resources.lib.modules.player import PlayerDialogs

        PlayerDialogs().display_dialog()

    elif action == "authAllDebrid":
        from resources.lib.debrid.all_debrid import AllDebrid

        AllDebrid().auth()

    elif action == "checkSkinUpdates":
        from resources.lib.database.skinManager import SkinManager

        SkinManager().check_for_updates()

    elif action == "authPremiumize":
        from resources.lib.debrid.premiumize import Premiumize

        Premiumize().auth()

    elif action == "testWindows":
        from resources.lib.gui.homeMenu import Menus

        Menus().test_windows()

    elif action == "testPlayingNext":
        from resources.lib.gui import mock_windows

        mock_windows.mock_playing_next()

    elif action == "testStillWatching":
        from resources.lib.gui import mock_windows

        mock_windows.mock_still_watching()

    elif action == "testResolverWindow":
        from resources.lib.gui import mock_windows

        mock_windows.mock_resolver()

    elif action == "testSourceSelectWindow":
        from resources.lib.gui import mock_windows

        mock_windows.mock_source_select()

    elif action == "testManualCacheWindow":
        from resources.lib.gui import mock_windows

        mock_windows.mock_cache_assist()

    elif action == "showsPopularRecent":
        from resources.lib.gui.tvshowMenus import Menus

        Menus().shows_popular_recent()

    elif action == "showsTrendingRecent":
        from resources.lib.gui.tvshowMenus import Menus

        Menus().shows_trending_recent()

    elif action == "moviePopularRecent":
        from resources.lib.gui.movieMenus import Menus

        Menus().movie_popular_recent()

    elif action == "movieTrendingRecent":
        from resources.lib.gui.movieMenus import Menus

        Menus().movie_trending_recent()

    elif action == "setDownloadLocation":
        from resources.lib.modules.download_manager import set_download_location

        set_download_location()

    elif action == "downloadManagerView":
        from resources.lib.gui.windows.download_manager import DownloadManager
        from resources.lib.database.skinManager import SkinManager

        window = DownloadManager(
            *SkinManager().confirm_skin_path("download_manager.xml")
        )
        window.doModal()
        del window

    elif action == "longLifeServiceManager":
        from resources.lib.modules.providers.service_manager import (
            ProvidersServiceManager,
        )

        ProvidersServiceManager().run_long_life_manager()

    elif action == "showsRecentlyWatched":
        from resources.lib.gui.tvshowMenus import Menus

        Menus().shows_recently_watched()

    elif action == "toggleLanguageInvoker":
        from resources.lib.common.maintenance import toggle_reuselanguageinvoker
        toggle_reuselanguageinvoker()