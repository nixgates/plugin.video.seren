# -*- coding: utf-8 -*-

import json
import sys


def dispatch(params):
    from resources.lib.common import tools
    from resources.lib.modules import database

    tools.SETTINGS_CACHE = {}

    try:

        url = params.get('url')

        action = params.get('action')

        page = params.get('page')

        actionArgs = params.get('actionArgs')

        pack_select = params.get('packSelect')

        source_select = params.get('source_select')

        seren_reload = True if params.get('seren_reload') == 'true' and tools.playList.getposition() == 0 else False

        resume = params.get('resume')

        forceresumeoff = True if params.get('forceresumeoff') == 'true' else False

        forceresumeon = True if params.get('forceresumeon') == 'true' else False

        smartPlay = True if params.get('smartPlay') == 'true' else False

    except:

        print('Welcome to console mode')
        print('Command Help:')
        print('   - Menu Number: opens the relevant menu page')
        print('   - shell: opens a interactive python shell within Seren')
        print('   - action xxx: run a custom Seren URL argument')

        url = ''

        action = None

        page = ''

        actionArgs = ''

        pack_select = ''

        source_select = ''

        seren_reload = ''

        resume = None

        forceresumeoff = True if params.get('forceresumeoff') == 'true' else False

        forceresumeon = True if params.get('forceresumeon') == 'true' else False

        smartPlay = True if params.get('smartPlay') == 'true' else False

    tools.log('Seren, Running Path - Action: %s, actionArgs: %s' % (action, actionArgs))

    if action is None:
        from resources.lib.gui import homeMenu

        homeMenu.Menus().home()

    if action == 'smartPlay':
        from resources.lib.modules import smartPlay
        # if 'resume' not in actionArgs:
        #     actionArgs = json.loads(actionArgs)
        #     actionArgs['resume'] = sys.argv[3].split(':')[-1]
        #     actionArgs = tools.quote(json.dumps(actionArgs, sort_keys=True))
        smartPlay.SmartPlay(actionArgs).fill_playlist()

    if action == 'playbackResume':
        from resources.lib.modules import smartPlay
        smart = smartPlay.SmartPlay(actionArgs)
        smart.workaround()

    if action == 'moviesHome':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().discoverMovies()

    if action == 'moviesPopular':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesPopular(page)

    if action == 'moviesTrending':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesTrending(page)

    if action == 'moviesPlayed':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesPlayed(page)

    if action == 'moviesWatched':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesWatched(page)

    if action == 'moviesCollected':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesCollected(page)

    if action == 'moviesAnticipated':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesAnticipated(page)

    if action == 'moviesBoxOffice':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesBoxOffice()

    if action == 'moviesUpdated':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesUpdated(page)

    if action == 'moviesRecommended':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesRecommended()

    if action == 'moviesSearch':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesSearch(actionArgs)

    if action == 'moviesSearchResults':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesSearchResults(actionArgs)

    if action == 'moviesSearchHistory':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesSearchHistory()

    if action == 'myMovies':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().myMovies()

    if action == 'moviesMyCollection':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().myMovieCollection()

    if action == 'moviesMyWatchlist':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().myMovieWatchlist()

    if action == 'moviesRelated':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().moviesRelated(actionArgs)

    if action == 'colorPicker':
        tools.colorPicker()

    if action == 'authTrakt':
        from resources.lib.indexers import trakt

        trakt.TraktAPI().auth()

    if action == 'revokeTrakt':
        from resources.lib.indexers import trakt

        trakt.TraktAPI().revokeAuth()

    if action == 'getSources':

        try:

            item_information = tools.get_item_information(actionArgs)
            #
            # This tomfoolery here is the new workaround for Seren to skip the building playlist window

            if tools.getSetting('smartplay.playlistcreate') == 'true' or smartPlay:

                if tools.playList.size() > 0:
                    playlist_uris = [tools.playList[i].getPath() for i in range(tools.playList.size())]
                else:
                    playlist_uris = []

                if ('showInfo' in item_information and tools.playList.size() == 0) \
                        or not any(sys.argv[2] in i for i in playlist_uris):

                    try:
                        name = item_information['info']['title']
                        item = tools.addDirectoryItem(name,
                                                      'getSources',
                                                      item_information['info'],
                                                      item_information['art'],
                                                      item_information['cast'],
                                                      isFolder=False,
                                                      isPlayable=True,
                                                      actionArgs=actionArgs,
                                                      bulk_add=True,
                                                      set_ids=item_information['ids'])
                        tools.cancelPlayback()
                        tools.playList.add(url=sys.argv[0] + sys.argv[2], listitem=item[1])
                        tools.player().play(tools.playList)
                        return
                    except:
                        import traceback
                        traceback.print_exc()
                        return

            bookmark_style = tools.getSetting('general.bookmarkstyle')

            if tools.playList.size() == 1 and resume is not None and bookmark_style != '2' and not forceresumeoff:

                if bookmark_style == '0' and not forceresumeon:
                    import datetime
                    selection = tools.showDialog.contextmenu([
                        '{} {}'.format(tools.lang(32092), datetime.timedelta(seconds=int(resume))),
                        tools.lang(40350)
                    ])
                    if selection == -1:
                        tools.cancelPlayback()
                        sys.exit()
                    elif selection != 0:
                        resume = None
            else:
                resume = None

            # Assume if we couldn't get information using the normal method, that it's the legacy method
            if item_information is None:
                item_information = actionArgs

            if not tools.premium_check():
                tools.showDialog.ok(tools.addonName, tools.lang(40146), tools.lang(40147))
                return None

            if tools.playList.getposition() == 0 and tools.getSetting('general.scrapedisplay') == '0':
                display_background = True
            else:
                display_background = False

            from resources.lib.modules.skin_manager import SkinManager

            if display_background:
                from resources.lib.gui.windows.persistent_background import PersistentBackground
                background = PersistentBackground(*SkinManager().confirm_skin_path('persistent_background.xml'),
                                                  actionArgs=actionArgs)
                background.setText(tools.lang(32045))
                background.show()

            from resources.lib.modules import getSources

            uncached_sources, source_results, args = database.get(getSources.getSourcesHelper,
                                                                  1,
                                                                  actionArgs,
                                                                  seren_reload=seren_reload,
                                                                  seren_sources=True)
            if len(source_results) <= 0:
                tools.showDialog.notification(tools.addonName, tools.lang(32047), time=5000)
                return

            if 'showInfo' in item_information:
                source_select_style = 'Episodes'
            else:
                source_select_style = 'Movie'

            if tools.getSetting('general.playstyle%s' % source_select_style) == '1' or source_select == 'true':

                try:
                    background.setText(tools.lang(40135))
                except:
                    pass

                from resources.lib.modules import sourceSelect

                stream_link = sourceSelect.sourceSelect(uncached_sources, source_results, actionArgs)

                if stream_link is None:
                    tools.showDialog.notification(tools.addonName, tools.lang(32047), time=5000)
                    raise Exception
                if not stream_link:
                    # user has backed out of source select, don't show no playable sources notification
                    raise Exception
            else:
                try:
                    background.setText(tools.lang(32046))
                except:
                    pass

                from resources.lib.modules import resolver

                resolver_window = resolver.Resolver(*SkinManager().confirm_skin_path('resolver.xml'),
                                                    actionArgs=actionArgs)

                stream_link = database.get(resolver_window.doModal, 1,
                                           source_results, args, pack_select,
                                           seren_reload=seren_reload)
                del resolver_window

                if stream_link is None:
                    tools.closeBusyDialog()
                    tools.showDialog.notification(tools.addonName, tools.lang(32047), time=5000)
                    raise Exception

            tools.showBusyDialog()
            try:
                background.close()
            except:
                pass
            try:
                del background
            except:
                pass

            from resources.lib.modules import player

            # if 'resume' not in actionArgs:
            #     actionArgs = json.loads(actionArgs)
            #     actionArgs['resume'] = sys.argv[3].split(':')[-1]
            #     actionArgs = json.dumps(actionArgs, sort_keys=True)

            player.serenPlayer().play_source(stream_link, actionArgs, resume_time=resume, params=params)

        except:
            import traceback
            traceback.print_exc()
            # Perform cleanup and make sure all open windows close and playlist is cleared
            try:
                tools.closeBusyDialog()
            except:
                pass
            try:
                background.close()
            except:
                pass
            try:
                del background
            except:
                pass
            try:
                resolver_window.close()
            except:
                pass
            try:
                del resolver_window
            except:
                pass
            try:
                tools.playList.clear()
            except:
                pass
            try:
                tools.closeOkDialog()
            except:
                pass
            try:
                tools.cancelPlayback()
            except:
                pass

    if action == 'preScrape':

        from resources.lib.modules.skin_manager import SkinManager

        try:
            item_information = tools.get_item_information(actionArgs)

            if 'showInfo' in item_information:
                source_select_style = 'Episodes'
            else:
                source_select_style = 'Movie'

            from resources.lib.modules import getSources

            uncached_sources, source_results, args = database.get(getSources.getSourcesHelper,
                                                                  1,
                                                                  actionArgs,
                                                                  seren_reload=seren_reload,
                                                                  seren_sources=True)

            if tools.getSetting('general.playstyle%s' % source_select_style) == '0':
                from resources.lib.modules import resolver

                resolver_window = resolver.Resolver(*SkinManager().confirm_skin_path('resolver.xml'),
                                                                                     actionArgs=actionArgs)
                database.get(resolver_window.doModal, 1, source_results, args, pack_select, seren_reload=seren_reload)

            tools.setSetting(id='general.tempSilent', value='false')
        except:
            tools.setSetting(id='general.tempSilent', value='false')
            import traceback

            traceback.print_exc()
            pass

        tools.log('Pre-scraping completed')

    if action == 'authRealDebrid':
        from resources.lib.debrid import real_debrid

        real_debrid.RealDebrid().auth()

    if action == 'showsHome':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().discoverShows()

    if action == 'myShows':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().myShows()

    if action == 'showsMyCollection':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().myShowCollection()

    if action == 'showsMyWatchlist':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().myShowWatchlist()

    if action == 'showsMyProgress':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().myProgress()

    if action == 'showsMyRecentEpisodes':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().myRecentEpisodes()

    if action == 'showsPopular':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsPopular(page)

    if action == 'showsRecommended':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsRecommended()

    if action == 'showsTrending':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsTrending(page)

    if action == 'showsPlayed':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsPlayed(page)

    if action == 'showsWatched':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsWatched(page)

    if action == 'showsCollected':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsCollected(page)

    if action == 'showsAnticipated':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsAnticipated(page)

    if action == 'showsUpdated':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsUpdated(page)

    if action == 'showsSearch':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsSearch(actionArgs)

    if action == 'showsSearchResults':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsSearchResults(actionArgs)

    if action == 'showsSearchHistory':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showSearchHistory()

    if action == 'showSeasons':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showSeasons(actionArgs)

    if action == 'seasonEpisodes':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().seasonEpisodes(actionArgs)

    if action == 'showsRelated':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsRelated(actionArgs)

    if action == 'showYears':
        from resources.lib.gui import tvshowMenus
        tvshowMenus.Menus().showYears(actionArgs, page)

    if action == 'searchMenu':
        from resources.lib.gui import homeMenu

        homeMenu.Menus().searchMenu()

    if action == 'toolsMenu':
        from resources.lib.gui import homeMenu

        homeMenu.Menus().toolsMenu()

    if action == 'clearCache':
        from resources.lib.common import tools

        tools.clearCache()

    if action == 'traktManager':
        from resources.lib.indexers import trakt

        trakt.TraktAPI().traktManager(actionArgs)

    if action == 'onDeckShows':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().onDeckShows()

    if action == 'onDeckMovies':
        from resources.lib.gui.movieMenus import Menus

        Menus().onDeckMovies()

    if action == 'cacheAssist':
        from resources.lib.modules import cacheAssist

        cacheAssist.CacheAssit(actionArgs)

    if action == 'tvGenres':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showGenres()

    if action == 'showGenresGet':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showGenreList(actionArgs, page)

    if action == 'movieGenres':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movieGenres()

    if action == 'movieGenresGet':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movieGenresList(actionArgs, page)

    if action == 'filePicker':
        from resources.lib.modules import smartPlay

        smartPlay.SmartPlay(actionArgs).torrent_file_picker()

    if action == 'shufflePlay':
        from resources.lib.modules import smartPlay

        try:
            smartPlay.SmartPlay(actionArgs).shufflePlay()
        except:
            import traceback
            traceback.print_exc()
            pass

    if action == 'resetSilent':
        tools.setSetting('general.tempSilent', 'false')
        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40296)), tools.lang(32048), time=5000)

    if action == 'clearTorrentCache':
        from resources.lib.modules import database

        database.torrent_cache_clear()

    if action == 'openSettings':
        tools.execute('Addon.OpenSettings(%s)' % tools.addonInfo('id'))

    if action == 'myTraktLists':
        from resources.lib.indexers import trakt

        trakt.TraktAPI().myTraktLists(actionArgs)

    if action == 'traktList':
        from resources.lib.indexers import trakt

        trakt.TraktAPI().getListItems(actionArgs, page)

    if action == 'nonActiveAssistClear':
        from resources.lib.gui import debridServices

        debridServices.Menus().assist_non_active_clear()

    if action == 'debridServices':
        from resources.lib.gui import debridServices

        debridServices.Menus().home()

    if action == 'cacheAssistStatus':
        from resources.lib.gui import debridServices

        debridServices.Menus().get_assist_torrents()

    if action == 'premiumizeTransfers':
        from resources.lib.gui import debridServices

        debridServices.Menus().list_premiumize_transfers()

    if action == 'showsNextUp':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().myNextUp()

    if action == 'runMaintenance':
        from resources.lib.common import maintenance

        maintenance.run_maintenance()

    if action == 'providerTools':
        from resources.lib.gui import homeMenu

        homeMenu.Menus().providerMenu()

    if action == 'adjustProviders':
        tools.log('adjustProviders endpoint has been deprecated')
        return
        # from resources.lib.modules import customProviders
        #
        # customProviders.providers().adjust_providers(actionArgs)

    if action == 'adjustPackage':
        tools.log('adjustPackage endpoint has been deprecated')
        return
        # DEPRECATED
        # from resources.lib.modules import customProviders
        #
        # customProviders.providers().adjust_providers(actionArgs, package_disable=True)

    if action == 'installProviders':
        from resources.lib.modules import customProviders

        customProviders.providers().install_package(actionArgs)

    if action == 'uninstallProviders':
        from resources.lib.modules import customProviders

        customProviders.providers().uninstall_package()

    if action == 'showsNew':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().newShows()

    if action == 'realdebridTransfers':
        from resources.lib.gui import debridServices

        debridServices.Menus().list_RD_transfers()

    if action == 'cleanInstall':
        from resources.lib.common import maintenance

        maintenance.wipe_install()

    if action == 'buildPlaylistWorkaround':
        from resources.lib.modules import smartPlay
        smartPlay.SmartPlay(actionArgs).resume_playback()

    if action == 'premiumizeCleanup':
        from resources.lib.common import maintenance

        maintenance.premiumize_transfer_cleanup()

    if action == 'test2':
        pass

    if action == 'manualProviderUpdate':
        from resources.lib.modules import customProviders

        customProviders.providers().manual_update()

    if action == 'clearSearchHistory':
        from resources.lib.modules import database

        database.clearSearchHistory()

    if action == 'externalProviderInstall':
        from resources.lib.modules import customProviders

        confirmation = tools.showDialog.yesno(tools.addonName, tools.lang(40117))
        if confirmation == 0:
            sys.exit()

        customProviders.providers().install_package(1, url=url)

    if action == 'externalProviderUninstall':
        from resources.lib.modules import customProviders

        confirmation = tools.showDialog.yesno(tools.addonName, tools.lang(40119) % url)
        if confirmation == 0:
            sys.exit()

        customProviders.providers().uninstall_package(package=url, silent=False)

    if action == 'showsNetworks':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsNetworks()

    if action == 'showsNetworkShows':
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().showsNetworkShows(actionArgs, page)

    if action == 'movieYears':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movieYears()

    if action == 'movieYearsMovies':
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movieYearsMovies(actionArgs, page)

    if action == 'syncTraktActivities':
        from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase
        TraktSyncDatabase().sync_activities()

    if action == 'traktSyncTools':
        from resources.lib.gui import homeMenu
        homeMenu.Menus().traktSyncTools()

    if action == 'flushTraktActivities':
        from resources.lib.modules import trakt_sync
        trakt_sync.TraktSyncDatabase().flush_activities()

    if action == 'flushTraktDBMeta':
        from resources.lib.modules import trakt_sync
        trakt_sync.TraktSyncDatabase().clear_all_meta()

    if action == 'myFiles':
        from resources.lib.gui import myFiles
        myFiles.Menus().home()

    if action == 'myFilesFolder':
        from resources.lib.gui import myFiles
        myFiles.Menus().myFilesFolder(actionArgs)

    if action == 'myFilesPlay':
        from resources.lib.gui import myFiles
        myFiles.Menus().myFilesPlay(actionArgs)

    if action == 'forceTraktSync':
        from resources.lib.modules import trakt_sync
        from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase
        trakt_sync.TraktSyncDatabase().flush_activities()
        TraktSyncDatabase().sync_activities()

    if action == 'rebuildTraktDatabase':
        from resources.lib.modules.trakt_sync import TraktSyncDatabase
        TraktSyncDatabase().re_build_database()

    if action == 'myUpcomingEpisodes':
        from resources.lib.gui import tvshowMenus
        tvshowMenus.Menus().myUpcomingEpisodes()

    if action == 'myWatchedEpisodes':
        from resources.lib.gui import tvshowMenus
        tvshowMenus.Menus().myWatchedEpisodes(page)

    if action == 'myWatchedMovies':
        from resources.lib.gui import movieMenus
        movieMenus.Menus().myWatchedMovies(page)

    if action == 'showsByActor':
        from resources.lib.gui import tvshowMenus
        tvshowMenus.Menus().showsByActor(actionArgs)

    if action == 'movieByActor':
        from resources.lib.gui import movieMenus
        movieMenus.Menus().moviesByActor(actionArgs)

    if action == 'playFromRandomPoint':
        from resources.lib.modules import smartPlay
        smartPlay.SmartPlay(actionArgs).play_from_random_point()

    if action == 'refreshProviders':
        from resources.lib.modules.customProviders import providers
        providers().update_known_providers()

    if action == 'installSkin':
        from resources.lib.modules.skin_manager import SkinManager
        SkinManager().install_skin()

    if action == 'uninstallSkin':
        from resources.lib.modules.skin_manager import SkinManager
        SkinManager().uninstall_skin()

    if action == 'switchSkin':
        from resources.lib.modules.skin_manager import SkinManager
        SkinManager().switch_skin()

    if action == 'manageProviders':
        tools.showBusyDialog()
        from resources.lib.gui.windows.custom_providers import CustomProviders
        from resources.lib.modules.skin_manager import SkinManager
        CustomProviders(*SkinManager().confirm_skin_path('custom_providers.xml')).doModal()

    if action == 'flatEpisodes':
        from resources.lib.gui.tvshowMenus import Menus
        Menus().flat_episode_list(actionArgs)

    if action =='runPlayerDialogs':
        from resources.lib.modules.player import PlayerDialogs
        try:
            PlayerDialogs().display_dialog()
        except:
            import traceback
            traceback.print_exc()

    if action == 'authAllDebrid':
        from resources.lib.debrid.all_debrid import AllDebrid
        AllDebrid().auth()

    if action == 'checkSkinUpdates':
        from resources.lib.modules.skin_manager import SkinManager
        SkinManager().check_for_updates()

    if action == 'authPremiumize':
        from resources.lib.debrid.premiumize import Premiumize
        Premiumize().auth()