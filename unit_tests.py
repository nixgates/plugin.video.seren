import seren
import os
from resources.lib.common import tools

tools.enable_unit_tests()

# Run in unit test mode
seren.tools.unit_test_mode = True
episode_object = tools.quote('{"episode": 6, "item_type": "episode", "season": 8, "trakt_id": 1390}')
season_object = tools.quote('{"item_type": "season", "season": 8, "trakt_id": 1390}')
show_object = tools.quote('{"item_type": "show", "trakt_id": 1390}')
movie_object = tools.quote('{"item_type": "movie", "trakt_id": 190430}')
log_path = os.path.join(os.getcwd(), 'unit_tests.txt')

if os.path.exists(log_path):
    os.remove(log_path)

def raise_unit_exception():
    import traceback
    log(traceback.format_exc(), 'error')

def log(results, level):
    msg = '[%s] %s' % (level.upper(), results)
    print(msg)
    with open(os.path.join(os.getcwd(), 'unit_tests.txt'), 'w+') as log_file:
        log_file.write(msg + '\n')


def run_action(action, args={}):

    args['unit_tests'] = True
    args['action'] = action

    return seren.api(args)

def run_menu_check(menu_endpoint, args={}, item_length=0, label_check=None):

    item_length = item_length - 1
    items = run_action(menu_endpoint, args)
    if menu_endpoint == '':
        menu_endpoint = 'Home Menu'
    try:
        if len(items) > item_length:
            if label_check:
                for i in items:
                    if not i.label == label_check:
                        raise Exception
            log('%s : OK' % menu_endpoint, 'info')
    except:
        log('%s : FAILURE' % menu_endpoint, 'error')

    return items

# Common Exceptions

class ScrapingException(Exception):

    def __init__(self):
        raise_unit_exception()

class ResolvingException(Exception):
    pass


class SourceSelectException(Exception):
    pass

def home_menu_check():
    run_menu_check('')

# Confirm arbitrary menus return items
def arb_menus_check():
    run_menu_check('searchMenu')
    run_menu_check('toolsMenu')

def confirm_requests_cache():

    def fake_input():
        import random
        faked_input = random.randint(1, 9999999)
        return faked_input

    run_action('clearCache')

    from resources.lib.modules import database

    random_value_input = database.get(fake_input, 24)

    # Allow the table to be built
    import time
    time.sleep(1)

    random_value_check = database.get(fake_input, 24)

    if random_value_input != random_value_check:
        log('Requests Cache Insert: FAILED', 'error')
        return

    time.sleep(1)
    run_action('clearCache')

    random_value_check = database.get(fake_input, 24)

    if random_value_check == random_value_input:
        log('Requests Cache Clear: FAILED', 'error')
        return

    run_action('clearCache')

    log('Requests Cache: OK', 'info')

# Confirm Movie Menus return items
def movie_menu_checks():

    run_menu_check('moviesHome')
    run_menu_check('moviesPopular', {'page': 1})
    run_menu_check('moviesTrending', {'page': 1})
    run_menu_check('moviesPlayed', {'page': 1})
    run_menu_check('moviesWatched', {'page': 1})
    run_menu_check('moviesCollected', {'page': 1})
    run_menu_check('moviesAnticipated', {'page': 1})
    run_menu_check('moviesBoxOffice', {'page': 1})
    run_menu_check('moviesUpdated', {'page': 1})
    run_menu_check('moviesRecommended', {'page': 1})
    run_menu_check('moviesSearch', {'actionArgs': 'Deadpool'})
    run_menu_check('moviesSearchHistory')
    run_menu_check('myMovies')
    run_menu_check('moviesMyCollection')
    run_menu_check('moviesMyWatchlist')
    run_menu_check('moviesRelated', {'actionArgs': movie_object})
    run_menu_check('onDeckMovies')
    run_menu_check('movieGenres')
    run_menu_check('movieGenresGet', {'actionArgs': 'comedy', 'page': 1})
    run_menu_check('movieYears')
    run_menu_check('movieYearsMovies', {'actionArgs': '2019', 'page': 1})
    run_menu_check('movieByActor', {'actionArgs': 'tom-cruise'})

def show_menu_checks():
    run_menu_check('showsHome')
    run_menu_check('myShows')
    run_menu_check('showsMyCollection')
    run_menu_check('showsMyWatchlist')
    run_menu_check('showsMyProgress')
    run_menu_check('showsMyRecentEpisodes')
    run_menu_check('showsPopular', {'page': 1})
    run_menu_check('showsRecommended')
    run_menu_check('showsTrending', {'page': 1})
    run_menu_check('showsPlayed', {'page': 1})
    run_menu_check('showsWatched', {'page': 1})
    run_menu_check('showsCollected', {'page': 1})
    run_menu_check('showsAnticipated', {'page': 1})
    run_menu_check('showsUpdated', {'page': 1})
    run_menu_check('showsSearch', {'actionArgs': 'Game Of Thrones'})
    run_menu_check('showsSearchHistory')
    run_menu_check('showSeasons', {'actionArgs': show_object})
    run_menu_check('seasonEpisodes', {'actionArgs': season_object})
    run_menu_check('showsRelated', {'actionArgs': show_object})
    run_menu_check('showYears', {'actionArgs': '2019'})
    run_menu_check('showYears', {'actionArgs': '2019'})

# Confirm Scraping/Resolving of Episode Items

def source_tests():
    try:
        scrape_failures = False
        resolve_failures = False
        tools.setSetting('general.tempSilent', 'true')
        tools.setSetting('general.playstyleEpisodes', 1)
        tools.setSetting('preem.enabled', 'false')
        tools.setSetting('preem.cloudfiles', 'false')
        run_action('clearTorrentCache')

        from resources.lib.modules import getSources
        uncached_sources, source_results, args = getSources.Sources().doModal(episode_object)

        if len(source_results) == 0:
            scrape_failures = True
            log('Scraping: FAILED', 'error')
            return

        if len([i for i in source_results if i['debrid_provider'] == 'premiumize']) > 0:
            log('Premiumize Cache Check: OK', 'info')
        else:
            scrape_failures = True
            log('Premiumize Cache Check: FAILED', 'error')

        if len([i for i in source_results if i['debrid_provider'] == 'real_debrid']) > 0:
            log('Real Debrid Cache Check: OK', 'info')
        else:
            scrape_failures = True
            log('Real Debrid Cache Check: FAILED', 'error')

        if len([i for i in source_results if i['source'] == 'Real Debrid Cloud']) > 0:
            log('Real Debrid Cloud Scraping: OK', 'info')
        else:
            scrape_failures = True
            log('Real Debrid Cloud Scraping: FAILED', 'error')

        if len([i for i in source_results if i['source'] == 'Premiumize Cloud']) > 0:
            log('Premiumize Cloud Scraping: OK', 'info')
        else:
            scrape_failures = True
            log('Premiumize Cloud Scraping: FAILED', 'error')

        if not scrape_failures:
            log('Episode Scraping: OK', 'info')
        else:
            log('Episode Scraping: FAILED', 'error')

        rd_sources = [i for i in source_results if
                      i['debrid_provider'] == 'real_debrid' and
                      i['source'] != 'Real Debrid Cloud']

        from resources.lib.modules import resolver
        stream_link = resolver.Resolver().doModal(rd_sources, args, False)

        if stream_link is None:
            log('Real Debrid Resolving: Failed', 'error')
            resolve_failures = True
        else:
            log('Real Debrid Resolving: OK', 'info')

        prem_sources = [i for i in source_results if
                        i['debrid_provider'] == 'premiumize' and
                        i['source'] != 'Pemiumize Cloud']

        from resources.lib.modules import resolver

        stream_link = resolver.Resolver().doModal(prem_sources, args, False)

        if stream_link is None:
            log('Premiumize Resolving: Failed', 'error')
            resolve_failures = True
        else:
            log('Premiumize Resolving: OK', 'info')

        if not resolve_failures:
            log('Episode Resolving: OK', 'info')
        else:
            log('Episode Resolving: Failed', 'error')

        uncached_sources, source_results, args = getSources.Sources().doModal(movie_object)

        if len(source_results) == 0:
            log('Movie Scraping: Failed', 'error')
        else:
            log('Movie Scraping: OK', 'info')

        tools.setSetting('general.tempSilent', 'false')
    except:
        tools.setSetting('general.tempSilent', 'false')
        ScrapingException()

confirm_requests_cache()
arb_menus_check()
movie_menu_checks()
show_menu_checks()
source_tests()






