# -*- coding: utf-8 -*-

import json
import os
import sys
import threading
import unicodedata

try:
    from urlparse import parse_qsl, parse_qs, unquote, urlparse
    from urllib import urlencode, quote_plus, quote
except:
    from urllib.parse import parse_qsl, urlencode, quote_plus, parse_qs, quote, unquote, urlparse

try:
    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
except:
    pass

tmdb_semaphore = 40

tmdb_sema = threading.Semaphore(tmdb_semaphore)

database_sema = threading.Semaphore(1)

tv_semaphore = 300

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

try:

    import xbmcaddon, xbmc, xbmcgui, xbmcplugin, xbmcvfs

    youtube_url = 'plugin://plugin.video.youtube/play/?video_id=%s'

    kodiGui = xbmcgui

    kodi = xbmc

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

    language = xbmc.getLanguage()

    dialogWindow = kodiGui.WindowDialog

    addon = xbmcaddon.Addon

    addonInfo = xbmcaddon.Addon().getAddonInfo

    openFile = xbmcvfs.File

    makeFile = xbmcvfs.mkdir

    deleteFile = xbmcvfs.delete

    deleteDir = xbmcvfs.rmdir

    listDir = xbmcvfs.listdir

    addonName = "Seren"

    addonDir = os.path.join(xbmc.translatePath('special://home'), 'addons/plugin.video.%s' % addonName.lower())

    try:
        dataPath = xbmc.translatePath(addonInfo('profile')).decode('utf-8')
    except:
        dataPath = xbmc.translatePath(addonInfo('profile'))

    cacheFile = os.path.join(dataPath, 'cache.db')

    torrentScrapeCacheFile = os.path.join(dataPath, 'torrentScrape.db')

    activeTorrentsDBFile = os.path.join(dataPath, 'activeTorrents.db')

    providersDB = os.path.join(dataPath, 'providers.db')

    premiumizeDB = os.path.join(dataPath, 'premiumize.db')

    condVisibility = xbmc.getCondVisibility

    lang = xbmcaddon.Addon().getLocalizedString

    addMenuItem = xbmcplugin.addDirectoryItem

    menuItem = xbmcgui.ListItem

    langString = xbmcaddon.Addon().getLocalizedString

    endDirectory = xbmcplugin.endOfDirectory

    content = xbmcplugin.setContent

    execute = xbmc.executebuiltin

    getSetting = xbmcaddon.Addon().getSetting

    showDialog = xbmcgui.Dialog()

    busyDialog = xbmcgui.DialogBusy()

    progressDialog = xbmcgui.DialogProgress()

    resolvedUrl = xbmcplugin.setResolvedUrl

    showKeyboard = xbmc.Keyboard

    fileBrowser = showDialog.browse

    sortMethod = xbmcplugin.addSortMethod

    playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

    player = xbmc.Player

    kodiVersion = int(xbmc.getInfoLabel("System.BuildVersion")[:2])

except:
    import traceback

    traceback.print_exc()
    pass


def addDirectoryItem(name, query, info, art, cm=[], isPlayable=False, isAction=True, isFolder=True, all_fanart=None,
                     actionArgs=False, smart_play=False, set_cast=False, label2=None, set_ids=None):

    url = '%s?action=%s' % (sysaddon, query) if isAction == True else query
    if actionArgs is not False:
        url += '&actionArgs=%s' % actionArgs
    item = menuItem(label=name)
    if label2 is not None:
        item.setLabel2(label2)
    if isPlayable == True:
        item.setProperty('IsPlayable', 'true')
    if set_cast is not False and 'cast' in info:
        item.setCast(set_cast)
    if set_ids is not None:
        item.setUniqueIDs(set_ids)
    item.addContextMenuItems(cm)
    item.setArt(art)
    item.setInfo('video', info)

    if smart_play is True:
        return [url, item]

    addMenuItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)


def closeDirectory(contentType, viewType='Default', sort=False, cacheToDisc=False):
    if sort == 'title':
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    if sort == 'episode':
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_EPISODE)
    if sort == False:
        sortMethod(syshandle, xbmcplugin.SORT_METHOD_NONE)

    viewType = get_view_type(contentType)

    xbmc.executebuiltin('Container.SetViewMode(%d)' % viewType)

    content(syshandle, contentType)

    endDirectory(syshandle, cacheToDisc=True)


def get_view_type(contentType):
    viewType = 'Default'

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
    return viewType


def busy():
    return execute('ActivateWindow(busydialog)')


def idle():
    return execute('Dialog.Close(busydialog)')


def safeStr(obj):
    try:
        return str(obj)
    except UnicodeEncodeError:
        return obj.encode('ascii', 'ignore').decode('ascii')
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
    text = text.decode('utf-8')
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")
    return str(text)


def colorString(text, color=None):
    try:
        text = text.encode('utf-8')
    except:
        try:
            text = bytes(text).decode('utf-8')
            text = str(text)
        except:
            pass
        pass

    if color is 'default' or color is '' or color is None:
        color = getSetting('general.textColor')
        if color is '':
            color = 'deepskyblue'

    try:
        return '[COLOR ' + str(color) + ']' + text + '[/COLOR]'
    except:
        return '[COLOR ' + str(color) + ']' + text + '[/COLOR]'


def sort_list_items(threadList, originalList):
    sortedList = []

    for o in originalList:
        if o is None:
            continue
        for t in threadList:
            if t is not None:
                if 'ids' in t:
                    if t['ids']['slug'] == o['ids']['slug']:
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


def closeBusyDialog():
    if kodiVersion > 17:
        execute('Dialog.Close(busydialognocancel')
    else:
        execute('Dialog.Close(all,true)')


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
    import datetime
    import time
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
    if condVisibility('System.HasAddon(context.seren)'):
        return True
    else:
        return False


def get_language_code():
    from resources.lib.common import languageCodes
    language_code = 'en'

    for code in languageCodes.isoLangs:
        if languageCodes.isoLangs[code]['name'].lower() == language.lower():
            language_code = code
    # Continue using en until everything is tested to accept other languages
    language_code = 'en'
    return language_code


def paginate_list(list_items, page, limit):
    pages = [list_items[i:i+limit] for i in xrange(0, len(list_items), limit)]
    return pages[page - 1]

def setSetting(id, value):
    xbmcaddon.Addon().setSetting(id, value)
