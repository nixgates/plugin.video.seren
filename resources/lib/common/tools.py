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
import time
import ast

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

tmdb_semaphore = 40

tmdb_sema = threading.Semaphore(tmdb_semaphore)

database_sema = threading.Semaphore(1)

tv_semaphore = 100

tv_sema = threading.Semaphore(tv_semaphore)

tvdb_refreshing = False

tvdb_refresh = ''

viewTypes = {
    'Default': 50,
    'Poster': 51,
    'Icon Wall': 52,
    'Shift': 53,
    'Info Wall': 54,
    'Wide List': 55,
    'Wall': 500,
    'Banner': 501,
    'Fanart': 502,
}

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

addonName = "Seren"

try:

    import xbmcaddon, xbmc, xbmcgui, xbmcplugin, xbmcvfs

    addonInfo = xbmcaddon.Addon().getAddonInfo

    # GLOBAL VARIABLES
    try:
        ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path').decode('utf-8')
    except:
        ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
    GUI_PATH = os.path.join(ADDON_PATH, 'resources', 'lib', 'gui')
    IMAGES_PATH = os.path.join(GUI_PATH, 'images')
    XML_PATH = os.path.join(GUI_PATH, 'xml')

    XBFONT_LEFT = 0x00000000
    XBFONT_RIGHT = 0x00000001
    XBFONT_CENTER_X = 0x00000002
    XBFONT_CENTER_Y = 0x00000004
    XBFONT_TRUNCATED = 0x00000008
    imageControl = xbmcgui.ControlImage
    labelControl = xbmcgui.ControlLabel
    buttonControl = xbmcgui.ControlButton
    listControl = xbmcgui.ControlList
    multi_text = xbmcgui.ControlTextBox
    PANDA_LOGO_PATH = os.path.join(IMAGES_PATH, 'panda.png')

    addonDir = os.path.join(xbmc.translatePath('special://home'), 'addons/plugin.video.%s' % addonName.lower())

    try:
        dataPath = xbmc.translatePath(addonInfo('profile')).decode('utf-8')
    except:
        dataPath = xbmc.translatePath(addonInfo('profile'))

    SETTINGS_PATH = os.path.join(dataPath, 'settings.xml')

    cacheFile = os.path.join(dataPath, 'cache.db')

    torrentScrapeCacheFile = os.path.join(dataPath, 'torrentScrape.db')

    activeTorrentsDBFile = os.path.join(dataPath, 'activeTorrents.db')

    providersDB = os.path.join(dataPath, 'providers.db')

    premiumizeDB = os.path.join(dataPath, 'premiumize.db')

    traktSyncDB = os.path.join(dataPath, 'traktSync.db')

    searchHistoryDB = os.path.join(dataPath, 'search.db')

    kodiVersion = int(xbmc.getInfoLabel("System.BuildVersion")[:2])

    openFile = xbmcvfs.File

    makeFile = xbmcvfs.mkdir

    deleteFile = xbmcvfs.delete

    deleteDir = xbmcvfs.rmdir

    listDir = xbmcvfs.listdir

    execute = xbmc.executebuiltin

    console_mode = False


except:

    sys.path.append(os.path.join(os.curdir, 'mock_kodi'))

    console_mode = True

    import xbmcaddon, xbmc, xbmcgui, xbmcplugin

    try:
        ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path').decode('utf-8')
    except:
        ADDON_PATH = os.getcwd()
    GUI_PATH = os.path.join(ADDON_PATH, 'resources', 'lib', 'gui')
    IMAGES_PATH = os.path.join(GUI_PATH, 'images')
    XML_PATH = os.path.join(GUI_PATH, 'xml')

    XBFONT_LEFT = 0x00000000
    XBFONT_RIGHT = 0x00000001
    XBFONT_CENTER_X = 0x00000002
    XBFONT_CENTER_Y = 0x00000004
    XBFONT_TRUNCATED = 0x00000008
    imageControl = xbmcgui.ControlImage
    labelControl = xbmcgui.ControlLabel
    buttonControl = xbmcgui.ControlButton
    listControl = xbmcgui.ControlList
    multi_text = xbmcgui.ControlTextBox
    PANDA_LOGO_PATH = os.path.join(IMAGES_PATH, 'panda.png')

    addonInfo = xbmcaddon.Addon().getAddonInfo

    kodiVersion = 18

    kodi_base_directory = os.path.abspath(os.path.join(os.getcwd(), '../../'))

    addonDir = os.path.join(kodi_base_directory, 'addons/plugin.video.%s' % addonName.lower())

    dataPath = os.path.join(kodi_base_directory, 'userdata', 'addon_data', 'plugin.video.%s' % addonName.lower())

    SETTINGS_PATH = os.path.join(dataPath, 'settings.xml')

    cacheFile = os.path.join(dataPath, 'cache.db')

    torrentScrapeCacheFile = os.path.join(dataPath, 'torrentScrape.db')

    activeTorrentsDBFile = os.path.join(dataPath, 'activeTorrents.db')

    providersDB = os.path.join(dataPath, 'providers.db')

    premiumizeDB = os.path.join(dataPath, 'premiumize.db')

    traktSyncDB = os.path.join(dataPath, 'traktSync.db')

    searchHistoryDB = os.path.join(dataPath, 'search.db')


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

youtube_url = 'plugin://plugin.video.youtube/play/?video_id=%s'

kodiGui = xbmcgui

kodi = xbmc

language = xbmc.getLanguage()

dialogWindow = kodiGui.WindowDialog

addon = xbmcaddon.Addon

progressDialog = xbmcgui.DialogProgress()

bgProgressDialog = xbmcgui.DialogProgressBG

showDialog = xbmcgui.Dialog()

showBusyDialog = xbmcgui.DialogBusy

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

playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

player = xbmc.Player

def lang(language_id):
    text = getLangString(language_id)
    text = text.encode('utf-8', 'replace')
    text = display_string(text)
    return text

def addDirectoryItem(name, query, info, art, cm=[], isPlayable=False, isAction=True, isFolder=True,
                     actionArgs=False, set_cast=False, label2=None, set_ids=None, bulk_add=False):

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
        if 'episodeCount' in info:
            item.setProperty('TotalEpisodes', str(info['episodeCount']))
        if 'episode_count' in info:
            item.setProperty('TotalEpisodes', str(info['episode_count']))
        if 'WatchedEpisodes' in info:
            item.setProperty('WatchedEpisodes', str(info['WatchedEpisodes']))
        if 'seasonCount' in info:
            item.setProperty('TotalSeasons', str(info['seasonCount']))
    except:
        pass

    if set_cast is not False:
        item.setCast(set_cast)
    if set_ids is not None:
        item.setUniqueIDs(set_ids)

    item.addContextMenuItems(cm)
    item.setArt(art)

    info = clean_info_keys(info)
    item.setInfo('video', info)

    if bulk_add:
        return (url, item, isFolder)
    else:
        addMenuItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)

def clean_info_keys(info_dict):

    keys_to_pop = ['UnWatchedEpisodes', 'episode_count', 'unwatchedepisodes', 'WatchedEpisodes',
                   'seasonCount', 'episodeCount', 'showaliases', 'absoluteNumber', 'no_seasons', 'season_title',
                   'overview']

    for i in keys_to_pop:
        try:
            info_dict.pop(i, None)
        except:
            pass

    return info_dict


def closeDirectory(contentType, sort=False):
    if sort == 'title':
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    if sort == 'episode':
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_EPISODE)
    if not sort:
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_NONE)

    viewType = get_view_type(contentType)

    content(syshandle, contentType)

    endDirectory(syshandle)
    xbmc.sleep(200)

    if getSetting('general.setViews') == 'true':
        xbmc.executebuiltin('Container.SetViewMode(%s)' % str(viewType))


def get_view_type(contentType):
    viewType = 'Default'

    try:
        if contentType == 'tvshows':
            viewType = getSetting('show.view')
        if contentType == 'movies':
            viewType = getSetting('movie.view')
        if contentType == 'episodes':
            viewType = getSetting('episode.view')
        if contentType == 'seasons':
            viewType = getSetting('season.view')

        viewType = viewTypes[viewType]

        if getSetting('general.viewidswitch') == 'true':
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


def closeOkDialog():
    execute('Dialog.Close(okdialog, true)')


def closeBusyDialog():
    execute('Dialog.Close(busydialog)')


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


def deaccentString(text):
    text = u'%s' % text
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text


def colorString(text, color=None):

    if type(text) is not int:
       text = display_string(text)

    if color is 'default' or color is '' or color is None:
        color = getSetting('general.textColor')
        if color is '':
            color = 'deepskyblue'

    return '[COLOR %s]%s[/COLOR]' % (color, text)


def display_string(object):

    if type(object) is str or type(object) is unicode:
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


EPOCH_DATETIME = datetime.datetime(1970, 1, 1)
SECONDS_PER_DAY = 24 * 60 * 60


def utc_to_local_datetime(utc_datetime):
    delta = utc_datetime - EPOCH_DATETIME
    utc_epoch = SECONDS_PER_DAY * delta.days + delta.seconds
    time_struct = time.localtime(utc_epoch)
    dt_args = time_struct[:6] + (delta.microseconds,)
    return datetime.datetime(*dt_args)


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


def shortened_debrid(debrid):
    debrid = debrid.lower()
    if debrid == 'premiumize':
        return 'PM'
    if debrid == 'real_debrid':
        return 'RD'
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
    if condVisibility('System.HasAddon(context.seren)') or not console_mode:
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
    if not console_mode:
        return xbmcaddon.Addon().getSetting(id)

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
    if getSetting('premiumize.pin') != '' and getSetting('premiumize.enabled') == 'true':
        return True
    else:
        return False

def real_debrid_enabled():
    if getSetting('rd.auth') != '' and getSetting('realdebrid.enabled') == 'true':
        return True
    else:
        return False

def italic_string(text):
    return "[I]%s[/I]" % text

fanart_api_key = getSetting('fanart.apikey')


def check_version_numbers(current, new):
    # Compares version numbers and return True if version is newer
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