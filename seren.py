import sys
from resources.lib.common import tools
from resources.lib.modules import database
from resources.lib.gui import windows

params = dict(tools.parse_qsl(sys.argv[2].replace('?','')))

url = params.get('url')

action = params.get('action')

page = params.get('page')

actionArgs = params.get('actionArgs')

pack_select = params.get('packSelect')

silent = params.get('silent')

source_select = params.get('source_select')

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
    movieMenus.Menus().moviesSearch()

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

    import time

    start_time = time.time()

    from resources.lib.modules import player

    try:
        if tools.playList.getposition() == 0:
            display_background = True
        else:
            display_background = False


        background = windows.persistant_background()
        background.setBackground(actionArgs)
        background.setText('Starting Engines')

        if display_background is True:
            background.show()

        from resources.lib.modules import getSources

        source_results, args = database.get(getSources.Sources().doModal, 1, actionArgs)

        if len(source_results) > 0:

            if tools.getSetting('general.playstyle') == '1' or source_select == 'true':

                from resources.lib.modules import sourceSelect
                source_results = sourceSelect.sourceSelect(source_results, args)

            from resources.lib.modules import resolver
            background.setText('Starting Resolver...')
            stream_link = database.get(resolver.Resolver().doModal, 1, source_results, args, pack_select)

            if display_background is True:
                background.close()
            try:
                tools.busyDialog.create()
            except:
                pass

            if stream_link is None:
                try:
                    tools.playList.clear()
                except:
                    pass
                pass
            else:
                player.serenPlayer().play_source(stream_link, args)
        else:
            if display_background is True:
                background.close()
            tools.showDialog.notification(tools.addonName, 'No playable sources found for item', time=5000)
            try:
                tools.closeBusyDialog()
            except:
                pass
    except:
        import traceback
        traceback.print_exc()
        try:
            tools.busyDialog.close()
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
    tvshowMenus.Menus().showsSearch()

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

if action == 'test2':
    #this was just used purely for quick testing and sly jokes to the testing crew
    pass


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
        import traceback
        traceback.print_exc()
        pass

if action == 'resetSilent':
    tools.setSetting('general.tempSilent', 'false')
    tools.showDialog.notification(tools.addonName + ": Silent scrape", 'Silent Scraper Setting has been reset', time=5000)

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

if action == 'installProviders':
    from resources.lib.modules import providerInstaller
    providerInstaller.install_zip(actionArgs)

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