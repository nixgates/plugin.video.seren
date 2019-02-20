# -*- coding: utf-8 -*-
import os, sys
import errno
import tempfile
import time
import warnings
from threading import Thread, Lock
from Tkinter import Tk, Label
#=====================================================================================================================
# API Constants
#=====================================================================================================================
CAPTURE_FLAG_CONTINUOUS = 1
CAPTURE_FLAG_IMMEDIATELY = 2
CAPTURE_STATE_DONE = 3
CAPTURE_STATE_FAILED = 4
CAPTURE_STATE_WORKING = 0
DRIVE_NOT_READY = 1
ENGLISH_NAME = 2
ISO_639_1 = 0
ISO_639_2 = 1
LOGDEBUG = 0
LOGERROR = 4
LOGFATAL = 6
LOGINFO = 1
LOGNONE = 7
LOGNOTICE = 2
LOGSEVERE = 5
LOGWARNING = 3
PLAYER_CORE_AUTO = 0
PLAYER_CORE_DVDPLAYER = 1
PLAYER_CORE_MPLAYER = 2
PLAYER_CORE_PAPLAYER = 3
PLAYLIST_MUSIC = 0
PLAYLIST_VIDEO = 1
SERVER_AIRPLAYSERVER = 2
SERVER_EVENTSERVER = 6
SERVER_JSONRPCSERVER = 3
SERVER_UPNPRENDERER = 4
SERVER_UPNPSERVER = 5
SERVER_WEBSERVER = 1
SERVER_ZEROCONF = 7
TRAY_CLOSED_MEDIA_PRESENT = 96
TRAY_CLOSED_NO_MEDIA = 64
TRAY_OPEN = 16
__author__ = 'Team Kodi <http://kodi.tv>'
__credits__ = 'Team Kodi'
__date__ = 'Sat Oct 24 10:35:29 BST 2015'
__platform__ = 'ALL'
__version__ = '2.23.0'
abortRequested = False

#=====================================================================================================================
# API Methods
#=====================================================================================================================
def audioResume():
    """Resume Audio engine"""
    pass

def audioSuspend():
    """Suspend Audio engine"""
    pass

def convertLanguage(language, format=ENGLISH_NAME):
    """Returns the given language converted to the given format as a string"""
    return ""

def enableNavSounds(yesNo):
    """Enables/Disables nav sounds"""
    pass

def executeJSONRPC(jsonrpccommand):
    """Execute an JSONRPC command"""
    return None

def executebuiltin(function, *args):

    """Execute a built in Kodi function"""
    try:
        print('Executing built in command')
        if '?' in function:
            sys.argv = [None, None, function.split('?')[1]]
        execfile(os.path.abspath(os.path.join(os.getcwd(), 'seren.py')))
    except:
        import traceback
        traceback.print_exc()
        pass

def executescript(script):
    """Execute a python script"""
    print("EXECUTE SCRIPT: {0}".format(script))

def getCacheThumbName():
    """Returns a thumb cache filename"""
    return ""

def getCleanMovieTitle(path, usefoldername=False):
    """getCleanMovieTitle"""
    pass

def getCondVisibility(condition):
    return False

def getDVDState():
    """Returns the dvd state as an integer"""
    return TRAY_CLOSED_MEDIA_PRESENT

def getFreeMem():
    """Returns the amount of free memory in MB as an integer"""
    return 0

def getGlobalIdleTime():
    """Returns the elapsed idle time in seconds as an integer."""
    return 0

def getIPAddress():
    """Returns the current ip address as a string."""
    return "127.0.0.1"

def getInfoImage(infotag):
    """Returns a filename including path to the InfoImage's thumbnail as a string"""
    return ""

def getInfoLabel(infotag):
    """Returns an InfoLabel as a string"""
    return ""

def getLanguage(format=ENGLISH_NAME, region=""):
    """Returns the active language as a string."""
    return ""

def getLocalizedString(id):
    """Returns a localized 'unicode string'"""
    return u""

def getRegion(id):
    """Returns your regions setting as a string for the specified id"""
    return ""

def getSkinDir():
    """Returns the active skin directory as a string"""
    return ""

def getSupportedMedia(media):
    """Returns the supported file types for the specific media as a string"""
    if media == "video":
        return ".m4v|.3g2|.3gp|.nsv|.tp|.ts|.ty|.strm|.pls|.rm|.rmvb|.mpd|.m3u|.m3u8|.ifo|.mov|.qt|.divx|.xvid|.bivx|.vob|.nrg|.img|.iso|.pva|.wmv|.asf|.asx|.ogm|.m2v|.avi|.bin|.dat|.mpg|.mpeg|.mp4|.mkv|.mk3d|.avc|.vp3|.svq3|.nuv|.viv|.dv|.fli|.flv|.rar|.001|.wpl|.zip|.vdr|.dvr-ms|.xsp|.mts|.m2t|.m2ts|.evo|.ogv|.sdp|.avs|.rec|.url|.pxml|.vc1|.h264|.rcv|.rss|.mpls|.webm|.bdmv|.wtv|.pvr|.disc"
    elif media == "music":
        return ".nsv|.m4a|.flac|.aac|.strm|.pls|.rm|.rma|.mpa|.wav|.wma|.ogg|.mp3|.mp2|.m3u|.gdm|.imf|.m15|.sfx|.uni|.ac3|.dts|.cue|.aif|.aiff|.wpl|.ape|.mac|.mpc|.mp+|.mpp|.shn|.zip|.rar|.wv|.dsp|.xsp|.xwav|.waa|.wvs|.wam|.gcm|.idsp|.mpdsp|.mss|.spt|.rsd|.sap|.cmc|.cmr|.dmc|.mpt|.mpd|.rmt|.tmc|.tm8|.tm2|.oga|.url|.pxml|.tta|.rss|.wtv|.mka|.tak|.opus|.dff|.dsf|.cdda"
    elif media == "picture":
        return ".png|.jpg|.jpeg|.bmp|.gif|.ico|.tif|.tiff|.tga|.pcx|.cbz|.zip|.cbr|.rar|.rss|.webp|.jp2|.apng"
    return ""

def log(msg, level=LOGDEBUG):
    """Write a string to XBMC's log file and the debug window"""
    levels = [
        'LOGDEBUG',
        'LOGINFO',
        'LOGNOTICE',
        'LOGWARNING',
        'LOGERROR',
        'LOGSEVERE',
        'LOGFATAL',
        'LOGNONE',
    ]
    print('%s - %s' % (levels[level], msg))

def makeLegalFilename(filename, fatX=True):
    """Returns a legal filename or path as a string"""
    return filename

def playSFX(filename, useCached=False):
    """Plays a wav file by filename"""
    pass

def restart():
    """Restart the htpc"""
    pass

def shutdown():
    """Shutdown the htpc"""
    pass
def skinHasImage(image):
    """Returns True if the image file exists in the skin"""
    return True

def sleep(value):
    """Sleeps for 'time' msec"""
    time.sleep(value / float(1000)) #xbmc.sleep is in milliseconds

def startServer(typ, bStart, bWait=True):
    """start or stop a server"""
    return False

def stopSFX():
    """Stops wav file"""
    pass

def translatePath(path):
    """Returns the translated path"""
    valid_dirs = ['xbmc', 'home', 'temp', 'masterprofile', 'profile',
                  'subtitles', 'userdata', 'database', 'thumbnails',
                  'recordings', 'screenshots', 'musicplaylists',
                  'videoplaylists', 'cdrips', 'skin', ]

    assert path.startswith('special://'), 'Not a valid special:// path.'
    parts = path.split('/')[2:]
    assert len(parts) > 1, 'Need at least a single root directory'

    name = parts[0]
    assert name in valid_dirs, '%s is not a valid root dir.' % name

    parts.pop(0) #remove name property

    # map in base folders
    dir_xbmc = os.path.dirname(os.path.abspath(__file__)) #note: this is the root of the MOCK, not the plugin
    dir_home = os.path.expanduser("~")
    if sys.platform == "win32":
        dir_home = os.path.join(dir_home, "AppData", "Roaming", "Kodi")
    else:
        dir_home = os.path.join(dir_home, ".kodi")
    dir_master = os.path.join(dir_home, "userdata")

    if not os.path.exists(dir_master):
        os.makedirs(dir_master)

    if name == 'xbmc':
        return os.path.join(dir_xbmc, *parts)
    elif name == 'home' or name == 'logpath':
        return os.path.join(dir_home, *parts)
    elif name == 'masterprofile' or name == 'profile':
        return os.path.join(dir_master, *parts)
    elif name == 'database':
        return os.path.join(dir_master, "Database", *parts)
    elif name == 'thumbnails':
        return os.path.join(dir_master, "Thumbnails", *parts)
    elif name == 'musicplaylists':
        return os.path.join(dir_master, "playlists", "music", *parts)
    elif name == 'videoplaylists':
        return os.path.join(dir_master, "playlists", "video", *parts)
    else:
        tempdir = os.path.join(tempfile.gettempdir(), 'XBMC', name)
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        return os.path.join(tempdir, *parts)

def validatePath(path):
    """Returns the validated path"""
    return path

#=====================================================================================================================
# API Classes
#=====================================================================================================================
class Keyboard(object):
    input_text = ''

    def __init__(self, default='', heading='', hidden=False):
        pass
    def doModal(self, autoclose=False):
        self.input_text = raw_input('Input Text')
        pass
    def getText(self):
        return self.input_text
    def isConfirmed(self):
        return True
    def setDefault(self, default):
        pass
    def setHeading(self, heading):
        pass
    def setHiddenInput(self, hidden):
        pass

class Monitor(object):
    _abort = False
    def __init__(self):
        self._root = Tk()
        self._root.title("Monitor")
        Label(self._root, text="Close window to simulate abort").pack()
        t = Thread(target=self._gui_thread)
        t.start()
    def _gui_thread(self):
        self._root.mainloop()
        self._abort = True
    def abortRequested(self):
        return self._abort
    def waitForAbort(self, timeout=0):
        if self._abort:
            return True
        time.sleep(timeout)

class Player(object):
    def __init__(self):
        pass
    def disableSubtitles(self):
        warnings.warn("Removed in v17.0", category=DeprecationWarning)
    def getAvailableAudioStreams(self):
        pass
    def getAvailableSubtitleStreams(self):
        pass
    def getMusicInfoTag(self):
        pass
    def getPlayingFile(self):
        pass
    def getRadioRDSInfoTag(self):
        pass
    def getSubtitles(self):
        return ""
    def getTime(self):
        pass
    def getTotalTime(self):
        pass
    def getVideoInfoTag(self):
        pass
    def isPlaying(self):
        return False
    def isPlayingAudio(self):
        return False
    def isPlayingRDS(self):
        return False
    def isPlayingVideo(self):
        return False
    def pause(self):
        pass
    def play(self, item="", listitem=None, windowed=False, startpos=-1):
        pass
    def playnext(self):
        pass
    def playprevious(self):
        pass
    def playselected(self):
        pass
    def seekTime(self):
        pass
    def setAudioStream(self, stream):
        pass
    def setSubtitleStream(self, stream):
        pass
    def setSubtitles(self):
        pass
    def showSubtitles(self, visible):
        pass
    def stop(self):
        pass

class PlayList(list):

    def __init__(self, video):
        pass

    def getposition(self):
        return 0

    def clear(self):
        pass