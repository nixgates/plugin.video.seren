# -*- coding: utf-8 -*-

from resources.lib.common import tools
import requests

client_key = tools.getSetting('fanart.apikey')
base_url = "http://webservice.fanart.tv/v3/%s/%s"
api_key = "dfe6380e34f49f9b2b9518184922b49c"
language = tools.get_language_code()

def get_query_lang(art):
    if art is None: return ''
    try:
        result = [(x['url'], x['likes']) for x in art if x.get('lang') == language]
        result = [(x[0], x[1]) for x in result]
        result = sorted(result, key=lambda x: int(x[1]), reverse=True)
        result = [x[0] for x in result][0]
        result = result

    except:
        result = ''
    if not 'http' in result: result = ''

    return result

def get_query(art):
    if art is None: return ''
    try:
        result = [(x['url'], x['likes']) for x in art]
        result = [(x[0], x[1]) for x in result]
        result = sorted(result, key=lambda x: int(x[1]), reverse=True)
        result = [x[0] for x in result][0]
        result = result.encode('utf-8')

    except:
        result = ''
    if not 'http' in result: result = ''

    return result

def get(remote_id, query):

    art = base_url % (query, remote_id)
    headers = {'client-key': client_key, 'api-key': api_key}

    art = requests.get(art, headers=headers).json()

    if query == 'movies':

        meta = {'poster': get_query_lang(art.get('movieposter')),
                'fanart': get_query_lang(art.get('moviebackground')),
                'banner': get_query_lang(art.get('moviebanner')),
                'clearlogo': get_query_lang(art.get('movielogo', []) + art.get('hdmovielogo', [])),
                'landscape': get_query_lang(art.get('moviethumb'))}

    else:

        meta = {'poster': get_query_lang(art.get('tvposter')),
                'fanart': get_query_lang(art.get('showbackground')),
                'banner': get_query_lang(art.get('tvbanner')),
                'clearart': get_query_lang(art.get('clearart', []) + art.get('hdclearart', [])),
                'clearlogo': get_query_lang(art.get('hdtvlogo', []) + art.get('clearlogo', [])),
                'landscape': get_query_lang(art.get('tvthumb'))}

    return meta
