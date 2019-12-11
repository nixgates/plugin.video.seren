# -*- coding: utf-8 -*-

import json
import os
import sys
import threading
import unicodedata
import re
import datetime
# Import _strptime to workaround python 2 bug with threads
import _strptime
import string

import time
from xml.etree import ElementTree

try:
    from dateutil import tz
except:
    pass

try:
    from urlparse import parse_qsl, parse_qs, unquote, urlparse
    from urllib import urlencode, quote_plus, quote
except:
    from urllib.parse import parse_qsl, urlencode, quote_plus, parse_qs, quote, unquote, urlparse

try:
    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
except:
    sysaddon = ''
    syshandle = '1'
    pass

SETTINGS_CACHE = {}

tvdb_refreshing = False

tvdb_refresh = ''

trakt_gmt_format = '%Y-%m-%dT%H:%M:%S.000Z'

viewTypes = [
    ('Default', 50),
    ('Poster', 51),
    ('Icon Wall', 52),
    ('Shift', 53),
    ('Info Wall', 54),
    ('Wide List', 55),
    ('Wall', 500),
    ('Banner', 501),
    ('Fanart', 502),
]

colorChart = ['black', 'white', 'whitesmoke', 'gainsboro', 'lightgray', 'silver', 'darkgray', 'gray', 'dimgray',
              'snow', 'floralwhite', 'ivory', 'beige', 'cornsilk', 'antiquewhite', 'bisque', 'blanchedalmond',
              'burlywood', 'darkgoldenrod', 'ghostwhite', 'azure', 'aliveblue', 'lightsaltegray', 'lightsteelblue',
              'powderblue', 'lightblue', 'skyblue', 'lightskyblue', 'deepskyblue', 'dodgerblue', 'royalblue',
              'blue', 'mediumblue', 'midnightblue', 'navy', 'darkblue', 'cornflowerblue', 'slateblue', 'slategray',
              'yellowgreen', 'springgreen', 'seagreen', 'steelblue', 'teal', 'fuchsia', 'deeppink', 'darkmagenta',
              'blueviolet', 'darkviolet', 'darkorchid', 'darkslateblue', 'darkslategray', 'indigo', 'cadetblue',
              'darkcyan', 'darkturquoise', 'turquoise', 'cyan', 'paleturquoise', 'lightcyan', 'mintcream', 'honeydew',
              'aqua', 'aquamarine', 'chartreuse', 'greenyellow', 'palegreen', 'lawngreen', 'lightgreen', 'lime',
              'mediumspringgreen', 'mediumturquoise', 'lightseagreen', 'mediumaquamarine', 'mediumseagreen',
              'limegreen', 'darkseagreen', 'forestgreen', 'green', 'darkgreen', 'darkolivegreen', 'olive', 'olivedab',
              'darkkhaki', 'khaki', 'gold', 'goldenrod', 'lightyellow', 'lightgoldenrodyellow', 'lemonchiffon',
              'yellow', 'seashell', 'lavenderblush', 'lavender', 'lightcoral', 'indianred', 'darksalmon',
              'lightsalmon', 'pink', 'lightpink', 'hotpink', 'magenta', 'plum', 'violet', 'orchid', 'palevioletred',
              'mediumvioletred', 'purple', 'marron', 'mediumorchid', 'mediumpurple', 'mediumslateblue', 'thistle',
              'linen', 'mistyrose', 'palegoldenrod', 'oldlace', 'papayawhip', 'moccasin', 'navajowhite', 'peachpuff',
              'sandybrown', 'peru', 'chocolate', 'orange', 'darkorange', 'tomato', 'orangered', 'red', 'crimson',
              'salmon', 'coral', 'firebrick', 'brown', 'darkred', 'tan', 'rosybrown', 'sienna', 'saddlebrown']

try:

    # Standard setup for working within Kodi

    import xbmcaddon, xbmc, xbmcgui, xbmcplugin, xbmcvfs

    addonInfo = xbmcaddon.Addon().getAddonInfo

    addonName = addonInfo('name')

    addonVersion = addonInfo('version')

    try:
        ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path').decode('utf-8')
    except:
        ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')

    addonDir = os.path.join(xbmc.translatePath('special://home'), 'addons/plugin.video.%s' % addonName.lower())

    try:
        dataPath = xbmc.translatePath(addonInfo('profile')).decode('utf-8')
    except:
        dataPath = xbmc.translatePath(addonInfo('profile'))

    kodiVersion = int(xbmc.getInfoLabel("System.BuildVersion")[:2])

    openFile = xbmcvfs.File

    makeFile = xbmcvfs.mkdir

    deleteFile = xbmcvfs.delete

    deleteDir = xbmcvfs.rmdir

    listDir = xbmcvfs.listdir

    file_exists = xbmcvfs.exists

    execute = xbmc.executebuiltin

    console_mode = False


except:

    # Adjust to support running in console mode

    sys.path.append(os.path.join(os.curdir, 'mock_kodi'))

    console_mode = True

    import xbmcaddon, xbmc, xbmcgui, xbmcplugin

    addonInfo = xbmcaddon.Addon().getAddonInfo

    addonName = addonInfo('name')

    addonVersion = addonInfo('version')

    try:
        ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path').decode('utf-8')
    except:
        ADDON_PATH = os.getcwd()

    kodiVersion = 18

    kodi_base_directory = os.path.abspath(os.path.join(os.getcwd(), '../../'))

    addonDir = os.path.join(kodi_base_directory, 'addons/plugin.video.%s' % addonName.lower())

    dataPath = os.path.join(kodi_base_directory, 'userdata', 'addon_data', 'plugin.video.%s' % addonName.lower())


    def execute(url):
        if 'Dialog' in url:
            return
        import re
        url = re.findall(r'.*?\((.*?)\)', url)
        sys.argv = [None, None, url]
        execfile(os.path.abspath(os.path.join(os.getcwd(), 'seren.py')))


    def makeFile(path):
        try:
            file = open(path, 'a+')
            file.close()
        except:
            pass

# GLOBAL VARIABLES

addonInfo = xbmcaddon.Addon().getAddonInfo

SETTINGS_PATH = os.path.join(dataPath, 'settings.xml')

ADVANCED_SETTINGS_PATH = xbmc.translatePath("special://home/userdata/advancedsettings.xml")

cacheFile = os.path.join(dataPath, 'cache.db')
cacheFile_lock = threading.Lock()

torrentScrapeCacheFile = os.path.join(dataPath, 'torrentScrape.db')
torrentScrapeCacheFile_lock = threading.Lock()

activeTorrentsDBFile = os.path.join(dataPath, 'activeTorrents.db')
activeTorrentsDBFile_lock = threading.Lock()

providersDB = os.path.join(dataPath, 'providers.db')
providersDB_lock = threading.Lock()

premiumizeDB = os.path.join(dataPath, 'premiumize.db')
premiumizeDB_lock = threading.Lock()

traktSyncDB = os.path.join(dataPath, 'traktSync.db')
traktSyncDB_lock = threading.Lock()

searchHistoryDB = os.path.join(dataPath, 'search.db')
searchHistoryDB_lock = threading.Lock()

imageControl = xbmcgui.ControlImage
labelControl = xbmcgui.ControlLabel
buttonControl = xbmcgui.ControlButton
listControl = xbmcgui.ControlList
multi_text = xbmcgui.ControlTextBox
groupControl = xbmcgui.ControlGroup

XBFONT_LEFT = 0x00000000
XBFONT_RIGHT = 0x00000001
XBFONT_CENTER_X = 0x00000002
XBFONT_CENTER_Y = 0x00000004
XBFONT_TRUNCATED = 0x00000008

youtube_url = 'plugin://plugin.video.youtube/play/?video_id=%s'

kodiGui = xbmcgui

kodi = xbmc

language = xbmc.getLanguage()

dialogWindow = kodiGui.WindowDialog

xmlWindow = kodiGui.WindowXMLDialog

addon = xbmcaddon.Addon

progressDialog = xbmcgui.DialogProgress()

bgProgressDialog = xbmcgui.DialogProgressBG

showDialog = xbmcgui.Dialog()

endDirectory = xbmcplugin.endOfDirectory

condVisibility = xbmc.getCondVisibility

getLangString = xbmcaddon.Addon().getLocalizedString

addMenuItem = xbmcplugin.addDirectoryItem

addMenuItems = xbmcplugin.addDirectoryItems

menuItem = xbmcgui.ListItem

langString = xbmcaddon.Addon().getLocalizedString

content = xbmcplugin.setContent

resolvedUrl = xbmcplugin.setResolvedUrl

showKeyboard = xbmc.Keyboard

fileBrowser = showDialog.browse

sortMethod = xbmcplugin.addSortMethod

abortRequested = xbmc.abortRequested

playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

player = xbmc.Player

homeWindow = xbmcgui.Window(10000)

get_region = xbmc.getRegion

GUI_PATH = os.path.join(ADDON_PATH, 'resources', 'lib', 'gui')

IMAGES_PATH = os.path.join(ADDON_PATH, 'resources', 'images')

SEREN_LOGO_PATH = os.path.join(IMAGES_PATH, 'trans-gold-fox-final.png')

SEREN_FANART_PATH = os.path.join(IMAGES_PATH, 'fanart-fox-gold-final.png')

SKINS_PATH = os.path.join(dataPath, 'skins')

SKINS_DB_PATH = os.path.join(dataPath, 'skins.db')

# COMMON USE UTIlS

def get_video_database_path():
    database_path = os.path.abspath(os.path.join(dataPath, '..', '..', 'Database', ))
    if kodiVersion == 17:
        database_path = os.path.join(database_path, 'MyVideos107.db')
    elif kodiVersion == 18:
        database_path = os.path.join(database_path, 'MyVideos116.db')

    return database_path

def showBusyDialog():
    execute('ActivateWindow(busydialognocancel)')

def lang(language_id):
    text = getLangString(language_id)
    text = text.encode('utf-8', 'replace')
    return text


def addDirectoryItem(name, query, info=None, art=None, cast=None, cm=None, isPlayable=False, isAction=True,
                     isFolder=True,
                     actionArgs=False, label2=None, set_ids=None, bulk_add=False):
    url = '%s?action=%s' % (sysaddon, query) if isAction else query

    if actionArgs is not False:
        url += '&actionArgs=%s' % actionArgs

    item = menuItem(label=name)

    if label2 is not None:
        item.setLabel2(label2)

    if isPlayable:
        item.setProperty('IsPlayable', 'true')
    else:
        item.setProperty('IsPlayable', 'false')

    try:
        if 'UnWatchedEpisodes' in info:
            item.setProperty('UnWatchedEpisodes', str(info['UnWatchedEpisodes']))
        # Check for either to support of old versions
        if 'episodeCount' in info:
            item.setProperty('TotalEpisodes', str(info['episodeCount']))
        if 'episode_count' in info:
            item.setProperty('TotalEpisodes', str(info['episode_count']))
        if 'WatchedEpisodes' in info:
            item.setProperty('WatchedEpisodes', str(info['WatchedEpisodes']))
        if 'season_count' in info:
            item.setProperty('TotalSeasons', str(info['season_count']))
        if 'resumetime' in info:
            if int(info['resumetime']) > 0:
                item.setProperty('resumetime', str(info['resumetime']))
                url += '&resume={}'.format(str(info['resumetime']))
                if 'totaltime' in info:
                    percent_played = int(float(int(info['resumetime']) / int(info['totaltime'])))
                    item.setProperty('percentplayed', str(percent_played))

        # Adding this property causes the bookmark CM items to be added
        # if 'totaltime' in info:
        #     item.setProperty('totaltime', str(info['totaltime']))
    except:
        pass

    if cast is not None:
        item.setCast(cast)

    if set_ids is not None:
        item.setUniqueIDs(set_ids)
        for label, value in set_ids.items():
            item.setProperty('{}_id'.format(label), str(value))

    if cm is None or type(cm) is not []:
        cm = []
    item.addContextMenuItems(cm)

    if art is None or type(art) is not dict:
        art = {}

    if art.get('fanart') is None:
        art['fanart'] = SEREN_FANART_PATH

    item.setArt(art)

    # Clear out keys not relevant to Kodi info labels
    info = clean_info_keys(info)
    item.setInfo('video', info)

    if bulk_add:
        return (url, item, isFolder)
    else:
        addMenuItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)


def clean_info_keys(info_dict):
    if info_dict is None:
        return None

    if not isinstance(info_dict, dict):
        return info_dict

    keys_to_keep = ['count', 'size', 'date', 'genre', 'country', 'year', 'episode', 'season', 'sortepisode',
                    'sortseason', 'episodeguide', 'showlink', 'top250', 'setid', 'tracknumber', 'rating', 'userrating',
                    'watched', 'playcount', 'overlay', 'cast', 'castandrole', 'director', 'mpaa', 'plot', 'plotoutline',
                    'title', 'originaltitle', 'sorttitle', 'duration', 'studio', 'tagline', 'writer', 'tvshowtitle',
                    'premiered', 'status', 'set', 'setoverview', 'tag', 'imdbnumber', 'code', 'aired', 'credits',
                    'lastplayed', 'album', 'artist', 'votes', 'path', 'trailer', 'dateadded', 'mediatype', 'dbid']

    keys = list(info_dict.keys())

    for i in keys:
        if i.lower() not in keys_to_keep:
            try:
                info_dict.pop(i, None)
            except:
                pass
    return info_dict


def closeDirectory(contentType, sort=False, cache=None):
    if sort == 'title':
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    if sort == 'episode':
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_EPISODE)
    if not sort:
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_NONE)

    viewType = get_view_type(contentType)

    content(syshandle, contentType)

    if getSetting('general.menucaching') == 'true':
        menu_caching = True
    else:
        menu_caching = False

    if not cache is None:
        menu_caching = cache

    endDirectory(syshandle, cacheToDisc=menu_caching)
    xbmc.sleep(200)

    if getSetting('general.setViews') == 'true':
        xbmc.executebuiltin('Container.SetViewMode(%s)' % str(viewType))

def cancel_directory():
    content(syshandle, 'addons')
    endDirectory(syshandle, cacheToDisc=False)

def get_view_type(contentType):
    viewType = 'Default'

    try:
        if contentType == 'addons':
            viewType = getSetting('addon.view')
        if contentType == 'tvshows':
            viewType = getSetting('show.view')
        if contentType == 'movies':
            viewType = getSetting('movie.view')
        if contentType == 'episodes':
            viewType = getSetting('episode.view')
        if contentType == 'seasons':
            viewType = getSetting('season.view')

        viewName, viewType = viewTypes[int(viewType)]

        if getSetting('general.viewidswitch') == 'true':
            if contentType == 'addons':
                viewType = getSetting('addon.view.id')
            if contentType == 'tvshows':
                viewType = getSetting('show.view.id')
            if contentType == 'movies':
                viewType = getSetting('movie.view.id')
            if contentType == 'episodes':
                viewType = getSetting('episode.view.id')
            if contentType == 'seasons':
                viewType = getSetting('season.view.id')

        viewType = int(viewType)
    except:
        pass

    return viewType


def closeAllDialogs():
    execute('Dialog.Close(all,true)')


def closeOkDialog():
    execute('Dialog.Close(okdialog, true)')


def closeBusyDialog():
    if condVisibility('Window.IsActive(busydialog)'):
        execute('Dialog.Close(busydialog)')
    if condVisibility('Window.IsActive(busydialognocancel)'):
        execute('Dialog.Close(busydialognocancel)')


def cancelPlayback():
    playList.clear()
    resolvedUrl(syshandle, False, menuItem())
    closeOkDialog()


def safeStr(obj):
    try:
        return str(obj)
    except UnicodeEncodeError:
        return obj.encode('utf-8', 'ignore').decode('ascii', 'ignore')
    except:
        return ""


def log(msg, level='info'):
    msg = safeStr(msg)
    msg = addonName.upper() + ': ' + msg
    if level == 'error':
        xbmc.log(msg, level=xbmc.LOGERROR)
    elif level == 'info':
        xbmc.log(msg, level=xbmc.LOGINFO)
    elif level == 'notice':
        xbmc.log(msg, level=xbmc.LOGNOTICE)
    elif level == 'warning':
        xbmc.log(msg, level=xbmc.LOGWARNING)
    else:
        xbmc.log(msg)


def colorPicker():
    selectList = []
    for i in colorChart:
        selectList.append(colorString(i, i))
    color = showDialog.select(addonName + lang(32021), selectList)
    if color == -1:
        return
    setSetting('general.textColor', colorChart[color])
    setSetting('general.displayColor', colorChart[color])
    execute('Addon.OpenSettings(%s)' % addonInfo('id'))


def deaccentString(text):
    try:
        try:
            text = u'%s' % text.decode('utf-8')
        except:
            text = u'%s' % text.encode('utf-8')
    except UnicodeDecodeError:
        text = u'%s' % text
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text


def strip_non_ascii_and_unprintable(text):
    result = ''.join(char for char in text if char in string.printable)
    return result.encode('ascii', errors='ignore').decode('ascii', errors='ignore')


def get_user_text_color():
    color = getSetting('general.textColor')
    if color == '' or color == 'None':
        color = 'deepskyblue'

    return color


def colorString(text, color=None):
    if type(text) is not int:
        text = display_string(text)

    if color is 'default' or color is '' or color is None:
        color = get_user_text_color()

    return '[COLOR %s]%s[/COLOR]' % (color, text)


def display_string(object):
    try:
        if type(object) is str or type(object) is unicode:
            return deaccentString(object)
    except NameError:
        if type(object) is str:
            return deaccentString(object)
    if type(object) is int:
        return '%s' % object
    if type(object) is bytes:
        object = ''.join(chr(x) for x in object)
        return object


def sort_list_items(threadList, originalList):
    sortedList = []

    for o in originalList:
        if o is None:
            continue
        for t in threadList:
            if t is not None:
                if 'ids' in t:
                    if t['ids']['trakt'] == o['ids']['trakt']:
                        sortedList.append(t)
                else:
                    continue
            else:
                continue
    return sortedList


def metaFile():
    return os.path.join(xbmcaddon.Addon('plugin.video.%s' % addonName.lower()).getAddonInfo('path'), 'resources',
                        'cache', 'meta.db')


def clearCache():
    confirm = showDialog.yesno(addonName, lang(32043))
    if confirm is 1:
        from resources.lib.modules import database
        database.cache_clear_all()
        log(addonName + ': Cache Cleared', 'debug')
    else:
        pass


def returnUrl(item):
    return quote_plus(json.dumps(item))


def remove_duplicate_dicts(src_lst, ignored_keys):
    filtered = {tuple((k, d[k]) for k in sorted(d) if k not in ignored_keys): d for d in src_lst}
    dst_lst = list(filtered.values())
    return dst_lst


import subprocess


def copy2clip(txt):
    platform = sys.platform

    if platform == 'win32':
        try:
            cmd = 'echo ' + txt.strip() + '|clip'
            return subprocess.check_call(cmd, shell=True)
            pass
        except:
            pass
    elif platform == 'linux2':
        try:
            from subprocess import Popen, PIPE

            p = Popen(['xsel', '-pi'], stdin=PIPE)
            p.communicate(input=txt)
        except:
            pass
    else:
        pass
    pass


def datetime_workaround(string_date, format="%Y-%m-%d", date_only=True):
    if string_date == '':
        return None
    try:
        if date_only:
            res = datetime.datetime.strptime(string_date, format).date()
        else:
            res = datetime.datetime.strptime(string_date, format)
    except TypeError:
        if date_only:
            res = datetime.datetime(*(time.strptime(string_date, format)[0:6])).date()
        else:
            res = datetime.datetime(*(time.strptime(string_date, format)[0:6]))

    return res


def gmt_to_local(gmt_string, format=None, date_only=False):
    try:
        local_timezone = tz.tzlocal()
        gmt_timezone = tz.gettz('GMT')
        if format is None:
            format = trakt_gmt_format
        GMT = datetime_workaround(gmt_string, format, date_only)
        GMT = GMT.replace(tzinfo=gmt_timezone)
        GMT = GMT.astimezone(local_timezone)
        return GMT.strftime(format)
    except:
        return gmt_string


def clean_air_dates(info):
    try:
        air_date = info.get('premiered')
        if air_date != '' and air_date is not None:
            info['aired'] = gmt_to_local(info['aired'])[:10]
    except KeyError:
        pass
    except:
        info['aired'] = info['aired'][:10]
    try:
        air_date = info.get('premiered')
        if air_date != '' and air_date is not None:
            info['premiered'] = gmt_to_local(info['premiered'])[:10]
    except KeyError:
        pass
    except:
        info['premiered'] = info['premiered'][:10]

    return info


def shortened_debrid(debrid):
    debrid = debrid.lower()
    if debrid == 'premiumize':
        return 'PM'
    if debrid == 'real_debrid':
        return 'RD'
    if debrid == 'all_debrid':
        'ALLDEBRID'
    return ''


def source_size_display(size):
    size = int(size)
    size = float(size) / 1024
    size = "{0:.2f} GB".format(size)
    return size


def color_quality(quality):
    color = 'darkred'

    if quality == '4K':
        color = 'lime'
    if quality == '1080p':
        color = 'greenyellow'
    if quality == '720p':
        color = 'sandybrown'
    if quality == 'SD':
        color = 'red'

    return colorString(quality, color)


def context_addon():
    if condVisibility('System.HasAddon(context.seren)'):
        return True
    else:
        return False


def get_language_code():
    from resources.lib.common import languageCodes

    for code in languageCodes.isoLangs:
        if languageCodes.isoLangs[code]['name'].lower() == language.lower():
            language_code = code
    # Continue using en until everything is tested to accept other languages
    language_code = 'en'
    return language_code


def paginate_list(list_items, page, limit):
    pages = [list_items[i:i + limit] for i in xrange(0, len(list_items), limit)]
    return pages[page - 1]


def setSetting(id, value):
    if not console_mode:
        return xbmcaddon.Addon().setSetting(id, value)

    loaded = False

    while loaded == False:

        # Pull information from settings file
        settings_file = open(SETTINGS_PATH, mode='r')
        lines = settings_file.readlines()
        settings_file.close()
        join_lines = ''.join(lines)

        # Make sure the information is complete before loading it
        if len(lines) > 0 and "</settings>" in join_lines and \
                len(re.findall(r'<settings version="2">|<settings>', join_lines)) > 0:
            loaded = True

    edited = False

    # Begin Making Edits
    while edited == False:
        try:
            settings_file = open(SETTINGS_PATH, mode='w')
            update = []
            for i in lines:
                if 'id="%s"' % id in i:
                    if '<settings version="2"' in join_lines:
                        update.append(re.sub(r'><|>.*?<', '>%s<' % value, i))
                    else:
                        update.append(re.sub(r'value=".*?"', 'value="%s"' % value, i))
                else:
                    update.append(i)
            settings_file.writelines(update)
            settings_file.flush()
            settings_file.close()
            edited = True

        except:
            # Something went wrong with editing the file
            # Try again after a brief timeout
            import random
            import time
            time.sleep(float(random.randint(50, 100) / 100))


def getSetting(id):
    if id in SETTINGS_CACHE:
        return SETTINGS_CACHE[id]

    if not console_mode:
        setting_value = xbmcaddon.Addon().getSetting(id)
        SETTINGS_CACHE.update({id: setting_value})

        return setting_value

    try:
        settings = open(SETTINGS_PATH, 'r')
        value = ' '.join(settings.readlines())
        value.strip('\n')
        settings.close()
        value = re.findall(r'id=\"%s\".*?>(.*?)<|id=\"%s\" value=\"(.*?)\" \/>' % (id, id), value)[0]
        value = [i for i in value if i is not ''][0]
        return value
    except:
        return ''


def premiumize_enabled():
    if getSetting('premiumize.token') != '' and getSetting('premiumize.enabled') == 'true':
        return True
    else:
        return False


def real_debrid_enabled():
    if getSetting('rd.auth') != '' and getSetting('realdebrid.enabled') == 'true':
        return True
    else:
        return False

def all_debrid_enabled():
    if getSetting('alldebrid.token') != '' and getSetting('alldebrid.enabled') == 'true':
        return True
    else:
        return False


def italic_string(text):
    return "[I]%s[/I]" % text


fanart_api_key = getSetting('fanart.apikey')


def check_version_numbers(current, new):
    # Compares version numbers and return True if new version is newer
    current = current.split('.')
    new = new.split('.')
    step = 0
    for i in current:
        if int(new[step]) > int(i):
            return True
        if int(i) == int(new[step]):
            step += 1
            continue

    return False


def trigger_widget_refresh():
    # Force an update of widgets to occur
    log('FORCE REFRESHING WIDGETS')
    timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    homeWindow.setProperty("widgetreload", timestr)
    homeWindow.setProperty('widgetreload-tvshows', timestr)
    homeWindow.setProperty('widgetreload-episodes', timestr)
    homeWindow.setProperty('widgetreload-movies', timestr)


def get_item_information(actionArgs):
    actionArgs = unquote(actionArgs)

    try:
        actionArgs = json.loads(actionArgs)
    except:
        log('Unable to load dict')
        return None

    if actionArgs['item_type'] == 'show':
        from resources.lib.modules.trakt_sync import shows
        item_information = shows.TraktSyncDatabase().get_single_show(actionArgs['trakt_id'])
        return item_information
    if actionArgs['item_type'] == 'season':
        from resources.lib.modules.trakt_sync import shows
        item_information = shows.TraktSyncDatabase().get_single_season(actionArgs['trakt_id'],
                                                                       actionArgs['season'])
        return item_information
    if actionArgs['item_type'] == 'episode':
        from resources.lib.modules.trakt_sync import shows
        item_information = shows.TraktSyncDatabase().get_single_episode(actionArgs['trakt_id'],
                                                                        actionArgs['season'],
                                                                        actionArgs['episode'])
        return item_information
    if actionArgs['item_type'] == 'movie':
        from resources.lib.modules.trakt_sync import movies
        item_information = movies.TraktSyncDatabase().get_movie(actionArgs['trakt_id'])
        return item_information


def premium_check():
    if playList.getposition() == 0 \
            and not premiumize_enabled() \
            and not real_debrid_enabled() \
            and not all_debrid_enabled():
        return False
    else:
        return True


def get_advanced_setting(*args):
    defaults = {
        ("video", "playcountminimumpercent"): 90,
        ("video", "ignoresecondsatstart"): 180,
        ("video", "ignorepercentatend"): 8
    }

    try:
        root = ElementTree.parse(ADVANCED_SETTINGS_PATH).getroot()
    except (ElementTree.ParseError, IOError):
        return defaults.get(args)
    elem = root.find("./{}".format("/".join(args)))
    return elem.text if elem else defaults.get(args)


def container_refresh():
    return execute('Container.Refresh')


def try_release_lock(lock):
    if lock.locked():
        lock.release()
