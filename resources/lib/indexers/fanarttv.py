# -*- coding: utf-8 -*-
import requests

from resources.lib.common import tools

client_key = tools.getSetting('fanart.apikey')

movies_poster_limit = int(tools.getSetting('movies.poster_limit'))
movies_fanart_limit = int(tools.getSetting('movies.fanart_limit'))
movies_keyart_limit = int(tools.getSetting('movies.keyart_limit'))
movies_characterart_limit = int(tools.getSetting('movies.characterart_limit'))
movies_banner = tools.getSetting('movies.banner')
movies_clearlogo = tools.getSetting('movies.clearlogo')
movies_landscape = tools.getSetting('movies.landscape')
movies_clearart = tools.getSetting('movies.clearart')
movies_discart = tools.getSetting('movies.discart')

tvshows_poster_limit = int(tools.getSetting('tvshows.poster_limit'))
tvshows_fanart_limit = int(tools.getSetting('tvshows.fanart_limit'))
tvshows_keyart_limit = int(tools.getSetting('tvshows.keyart_limit'))
tvshows_characterart_limit = int(tools.getSetting('tvshows.characterart_limit'))
tvshows_banner = tools.getSetting('tvshows.banner')
tvshows_clearlogo = tools.getSetting('tvshows.clearlogo')
tvshows_landscape = tools.getSetting('tvshows.landscape')
tvshows_clearart = tools.getSetting('tvshows.clearart')
season_poster = tools.getSetting('season.poster')
season_banner = tools.getSetting('season.banner')
season_landscape = tools.getSetting('season.landscape')
season_fanart = tools.getSetting('season.fanart')

base_url = "http://webservice.fanart.tv/v3/%s/%s"
api_key = "dfe6380e34f49f9b2b9518184922b49c"
language = tools.get_language_code()


def get_query_lang(art, season_number=None):
    if art is None:
        return []
    try:
        result = [(x['url'], x['likes']) for x in art
                  if (x.get('lang') == language or x.get('lang') == '00' or x.get('lang') == '') and
                  (season_number is None or (x.get('season') is not None and ((int(x['season']) if x['season'] != 'all'
                                                                               else 0) == int(season_number))))]
        result = sorted(result, key=lambda x: int(x[1]), reverse=True)
        result = [x[0].encode('utf-8') for x in result if 'http' in x[0]]
    except:
        result = []

    return result


def get_query(art):
    if art is None:
        return ''
    try:
        result = [(x['url'], x['likes']) for x in art]
        result = [(x[0], x[1]) for x in result]
        result = sorted(result, key=lambda x: int(x[1]), reverse=True)
        result = [x[0] for x in result][0]
        result = result.encode('utf-8')

    except:
        result = ''
    if not 'http' in result:
        result = ''

    return result


def get(remote_id, query, season_number=None):
    art_request = base_url % (query if query == 'movies' or query == 'tv' else 'tv', remote_id)
    headers = {'client-key': client_key, 'api-key': api_key}
    art = requests.get(art_request, headers=headers).json()

    meta = {}
    if query == 'movies':
        if movies_clearlogo == 'true':
            meta.update(create_meta_data(art, 'clearlogo', ['movielogo', 'hdmovielogo'], 1))
        if movies_discart == 'true':
            meta.update(create_meta_data(art, 'discart', ['moviedisc'], 1))
        if movies_clearart == 'true':
            meta.update(create_meta_data(art, 'clearart', ['movieart', 'hdmovieclearart'], 1))
        meta.update(create_meta_data(art, 'characterart', ['characterart'], movies_characterart_limit))
        meta.update(create_meta_data(art, 'poster', ['movieposter'], movies_poster_limit))
        meta.update(create_meta_data(art, 'fanart', ['moviebackground'], movies_fanart_limit))
        if movies_banner == 'true':
            meta.update(create_meta_data(art, 'banner', ['moviebanner'], 1))
        if movies_landscape == 'true':
            meta.update(create_meta_data(art, 'landscape', ['moviethumb'], 1))
    elif query == 'tv':
        if tvshows_clearlogo == 'true':
            meta.update(create_meta_data(art, 'clearlogo', ['hdtvlogo', 'clearlogo'], 1))
        if tvshows_clearart == 'true':
            meta.update(create_meta_data(art, 'clearart', ['hdclearart', 'clearart'], 1))
        meta.update(create_meta_data(art, 'characterart', ['characterart'], tvshows_characterart_limit))
        meta.update(create_meta_data(art, 'keyart', ['tvposter-alt'], tvshows_keyart_limit))
        meta.update(create_meta_data(art, 'poster', ['tvposter'], tvshows_poster_limit))
        meta.update(create_meta_data(art, 'fanart', ['showbackground'], tvshows_fanart_limit))
        if tvshows_banner == 'true':
            meta.update(create_meta_data(art, 'banner', ['tvbanner'], 1))
        if tvshows_landscape == 'true':
            meta.update(create_meta_data(art, 'landscape', ['tvthumb'], 1))
    elif query == 'season':
        if tvshows_clearlogo == 'true':
            meta.update(create_meta_data(art, 'clearlogo', ['hdtvlogo', 'clearlogo'], 1))
        if tvshows_clearart == 'true':
            meta.update(create_meta_data(art, 'clearart', ['hdclearart', 'clearart'], 1))
        meta.update(create_meta_data(art, 'characterart', ['characterart'], tvshows_characterart_limit))
        meta.update(create_meta_data(art, 'keyart', ['tvposter-alt'], tvshows_keyart_limit))
        if season_landscape == 'true':
            meta.update(create_meta_data(art, 'landscape', ['seasonthumb'], 1, season_number))
        if season_banner == 'true':
            meta.update(create_meta_data(art, 'banner', ['seasonbanner'], 1, season_number))
        if season_poster == 'true':
            meta.update(create_meta_data(art, 'poster', ['seasonposter'], tvshows_poster_limit, season_number))
        if season_fanart == 'true':
            meta.update(
                create_meta_data(art, 'fanart', ['showbackground-season'], tvshows_fanart_limit, season_number))
    return meta


def create_meta_data(art, dict_name, art_names, number, season_number=None):
    result = {}
    counter = 0
    art_list = []
    [art_list.extend(filtered) for filtered in [art.get(name) for name in art_names] if filtered is not None]
    for art_item in get_query_lang(art_list, season_number)[:number]:
        if counter == 0:
            result[dict_name] = art_item
        else:
            result['{}{}'.format(dict_name, counter)] = art_item
        counter = counter + 1

    return result
