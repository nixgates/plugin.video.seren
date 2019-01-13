# -*- coding: utf-8 -*-

import sys

from resources.lib.common import tools
from resources.lib.gui import windows
from resources.lib.modules import database

params = dict(tools.parse_qsl(sys.argv[2].replace('?', '')))

url = params.get('url')

action = params.get('action')

page = params.get('page')

actionArgs = params.get('actionArgs')

pack_select = params.get('packSelect')

silent = params.get('silent')

source_select = params.get('source_select')

seren_reload = params.get('seren_reload')

if seren_reload == 'true':
    seren_reload = True

if action == None:
    from resources.lib.gui import homeMenu

    homeMenu.Menus().home()

if action == 'smartPlay':
    from resources.lib.modules import smartPlay

    smart = smartPlay.SmartPlay(actionArgs)
    smart.smart_play_show()

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
        if tools.playList.getposition() == 0:
            display_background = True
        else:
            display_background = False

        background = windows.persistant_background()
        background.setBackground(actionArgs)
        background.setText(tools.lang(32045).encode('utf-8'))

        if display_background:
            background.show()

        from resources.lib.modules import getSources

        sources_window = getSources

        source_results, args = database.get(sources_window.Sources().doModal, 1, actionArgs, seren_reload=seren_reload)

        try:
            del sources_window
        except:
            pass

        if len(source_results) > 0:

            if tools.getSetting('general.playstyle') == '1' or source_select == 'true':
                from resources.lib.modules import sourceSelect

                source_results = sourceSelect.sourceSelect(source_results, args)

            from resources.lib.modules import resolver

            background.setText(tools.lang(32046).encode('utf-8'))
            resolver_window = resolver
            stream_link = database.get(resolver_window.Resolver().doModal, 1, source_results, args, pack_select,
                                       seren_reload=seren_reload)
            del resolver_window

            if display_background is True:
                background.close()
                del background

            if stream_link is None:
                try:
                    tools.playList.clear()
                except:
                    pass
                pass
            else:
                from resources.lib.modules import player

                player.serenPlayer().play_source(stream_link, args)
        else:
            tools.closeBusyDialog()
            tools.playList.clear()
            if display_background is True:
                background.close()
                del background
            tools.showDialog.notification(tools.addonName, tools.lang(32047).encode('utf-8'), time=5000)

    except:
        # Perform cleanup and make sure all open windows close and playlist is cleared
        import traceback

        traceback.print_exc()
        tools.closeBusyDialog()
        try:
            display_background.close()
            del display_background
        except:
            pass

        try:
            sources_window.close()
            del sources_window
        except:
            pass

        try:
            resolver_window.close()
            del resolver_window
        except:
            pass

        try:
            tools.playList.clear()
        except:
            pass

if action == 'preScrape':
    tools.log('Started Pre-scraping')
    try:
        from resources.lib.modules import getSources

        source_results, args = database.get(getSources.Sources().doModal, 1, actionArgs)

        if tools.getSetting('general.playstyle') == '0':
            from resources.lib.modules import resolver

            stream_link = database.get(resolver.Resolver().doModal, 1, source_results, args, pack_select)

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

if action == 'showSeasons':
    from resources.lib.gui import tvshowMenus

    tvshowMenus.Menus().showSeasons(actionArgs)

if action == 'seasonEpisodes':
    from resources.lib.gui import tvshowMenus

    tvshowMenus.Menus().seasonEpisodes(actionArgs)

if action == 'showsRelated':
    from resources.lib.gui import tvshowMenus

    tvshowMenus.Menus().showsRelated(actionArgs)

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

if action == 'traktOnDeckHome':
    from resources.lib.gui import homeMenu

    homeMenu.Menus().traktOnDeck()

if action == 'onDeckShows':
    from resources.lib.gui import tvshowMenus

    tvshowMenus.Menus().onDeckShows()

if action == 'onDeckMovies':
    from resources.lib.gui.movieMenus import Menus

    Menus().onDeckMovies()

if action == 'cacheAssist':
    from resources.lib.modules import cacheAssist

    cacheAssist.CacheAssit(actionArgs)

if action == 'showGenres':
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
        smart = smartPlay.SmartPlay(actionArgs).shufflePlay()
    except:
        pass

if action == 'resetSilent':
    tools.setSetting('general.tempSilent', 'false')
    tools.showDialog.notification(tools.addonName + ": Silent scrape", tools.lang(32048).encode('utf-8'), time=5000)

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
    from resources.lib.modules import customProviders

    customProviders.providers().adjust_providers(actionArgs)

if action == 'adjustPackage':
    from resources.lib.modules import customProviders

    customProviders.providers().adjust_providers(actionArgs, package_disable=True)

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

if action == 'buildPlaylist':

    # This is a nasty workaround for Kodi 18 Skin Widgets
    import json
    from resources.lib.gui import tvshowMenus

    actionArgs = json.loads(tools.unquote(actionArgs))
    playlist = tvshowMenus.Menus().episodeListBuilder(actionArgs['playlist'], actionArgs['info_dictionary'],
                                                      smartPlay=True, hide_unaired=True)

    for i in playlist:
        tools.playList.add(url=i[0], listitem=i[1])

    tools.player().play(tools.playList)

if action == 'premiumizeCleanup':
    from resources.lib.common import maintenance

    maintenance.premiumize_transfer_cleanup()

if action == 'test2':
    pass

if action == 'manualProviderUpdate':
    from resources.lib.modules import customProviders

    customProviders.providers().manual_update()

if action == 'movieYears':
    from resources.lib.gui import movieMenus
    menus = movieMenus.Menus()
    menus.moviesYears()
