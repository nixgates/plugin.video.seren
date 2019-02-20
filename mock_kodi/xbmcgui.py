import warnings
import time
import threading

#======================================================================================================================
# API Constants
#======================================================================================================================
ACTION_ANALOG_FORWARD = 113
ACTION_ANALOG_MOVE = 49
ACTION_ANALOG_MOVE_X = 601
ACTION_ANALOG_MOVE_Y = 602
ACTION_ANALOG_REWIND = 114
ACTION_ANALOG_SEEK_BACK = 125
ACTION_ANALOG_SEEK_FORWARD = 124
ACTION_ASPECT_RATIO = 19
ACTION_AUDIO_DELAY = 161
ACTION_AUDIO_DELAY_MIN = 54
ACTION_AUDIO_DELAY_PLUS = 55
ACTION_AUDIO_NEXT_LANGUAGE = 56
ACTION_BACKSPACE = 110
ACTION_BIG_STEP_BACK = 23
ACTION_BIG_STEP_FORWARD = 22
ACTION_BUILT_IN_FUNCTION = 122
ACTION_CALIBRATE_RESET = 48
ACTION_CALIBRATE_SWAP_ARROWS = 47
ACTION_CHANGE_RESOLUTION = 57
ACTION_CHANNEL_DOWN = 185
ACTION_CHANNEL_SWITCH = 183
ACTION_CHANNEL_UP = 184
ACTION_CHAPTER_OR_BIG_STEP_BACK = 98
ACTION_CHAPTER_OR_BIG_STEP_FORWARD = 97
ACTION_CONTEXT_MENU = 117
ACTION_COPY_ITEM = 81
ACTION_CREATE_BOOKMARK = 96
ACTION_CREATE_EPISODE_BOOKMARK = 95
ACTION_CURSOR_LEFT = 120
ACTION_CURSOR_RIGHT = 121
ACTION_CYCLE_SUBTITLE = 99
ACTION_DECREASE_PAR = 220
ACTION_DECREASE_RATING = 137
ACTION_DELETE_ITEM = 80
ACTION_ENTER = 135
ACTION_ERROR = 998
ACTION_FILTER = 233
ACTION_FILTER_CLEAR = 150
ACTION_FILTER_SMS2 = 151
ACTION_FILTER_SMS3 = 152
ACTION_FILTER_SMS4 = 153
ACTION_FILTER_SMS5 = 154
ACTION_FILTER_SMS6 = 155
ACTION_FILTER_SMS7 = 156
ACTION_FILTER_SMS8 = 157
ACTION_FILTER_SMS9 = 158
ACTION_FIRST_PAGE = 159
ACTION_FORWARD = 16
ACTION_GESTURE_BEGIN = 501
ACTION_GESTURE_END = 599
ACTION_GESTURE_NOTIFY = 500
ACTION_GESTURE_PAN = 504
ACTION_GESTURE_ROTATE = 503
ACTION_GESTURE_SWIPE_DOWN = 541
ACTION_GESTURE_SWIPE_DOWN_TEN = 550
ACTION_GESTURE_SWIPE_LEFT = 511
ACTION_GESTURE_SWIPE_LEFT_TEN = 520
ACTION_GESTURE_SWIPE_RIGHT = 521
ACTION_GESTURE_SWIPE_RIGHT_TEN = 530
ACTION_GESTURE_SWIPE_UP = 531
ACTION_GESTURE_SWIPE_UP_TEN = 540
ACTION_GESTURE_ZOOM = 502
ACTION_GUIPROFILE_BEGIN = 204
ACTION_HIGHLIGHT_ITEM = 8
ACTION_INCREASE_PAR = 219
ACTION_INCREASE_RATING = 136
ACTION_INPUT_TEXT = 244
ACTION_JUMP_SMS2 = 142
ACTION_JUMP_SMS3 = 143
ACTION_JUMP_SMS4 = 144
ACTION_JUMP_SMS5 = 145
ACTION_JUMP_SMS6 = 146
ACTION_JUMP_SMS7 = 147
ACTION_JUMP_SMS8 = 148
ACTION_JUMP_SMS9 = 149
ACTION_LAST_PAGE = 160
ACTION_MENU = 163
ACTION_MOUSE_DOUBLE_CLICK = 103
ACTION_MOUSE_DRAG = 106
ACTION_MOUSE_END = 109
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_MOUSE_LONG_CLICK = 108
ACTION_MOUSE_MIDDLE_CLICK = 102
ACTION_MOUSE_MOVE = 107
ACTION_MOUSE_RIGHT_CLICK = 101
ACTION_MOUSE_START = 100
ACTION_MOUSE_WHEEL_DOWN = 105
ACTION_MOUSE_WHEEL_UP = 104
ACTION_MOVE_DOWN = 4
ACTION_MOVE_ITEM = 82
ACTION_MOVE_ITEM_DOWN = 116
ACTION_MOVE_ITEM_UP = 115
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MUTE = 91
ACTION_NAV_BACK = 92
ACTION_NEXT_CHANNELGROUP = 186
ACTION_NEXT_CONTROL = 181
ACTION_NEXT_ITEM = 14
ACTION_NEXT_LETTER = 140
ACTION_NEXT_PICTURE = 28
ACTION_NEXT_SCENE = 138
ACTION_NEXT_SUBTITLE = 26
ACTION_NONE = 0
ACTION_NOOP = 999
ACTION_PAGE_DOWN = 6
ACTION_PAGE_UP = 5
ACTION_PARENT_DIR = 9
ACTION_PASTE = 180
ACTION_PAUSE = 12
ACTION_PLAY = 68
ACTION_PLAYER_FORWARD = 77
ACTION_PLAYER_PLAY = 79
ACTION_PLAYER_PLAYPAUSE = 229
ACTION_PLAYER_REWIND = 78
ACTION_PREVIOUS_CHANNELGROUP = 187
ACTION_PREVIOUS_MENU = 10
ACTION_PREV_CONTROL = 182
ACTION_PREV_ITEM = 15
ACTION_PREV_LETTER = 141
ACTION_PREV_PICTURE = 29
ACTION_PREV_SCENE = 139
ACTION_PVR_PLAY = 188
ACTION_PVR_PLAY_RADIO = 190
ACTION_PVR_PLAY_TV = 189
ACTION_QUEUE_ITEM = 34
ACTION_RECORD = 170
ACTION_RELOAD_KEYMAPS = 203
ACTION_REMOVE_ITEM = 35
ACTION_RENAME_ITEM = 87
ACTION_REWIND = 17
ACTION_ROTATE_PICTURE_CCW = 51
ACTION_ROTATE_PICTURE_CW = 50
ACTION_SCAN_ITEM = 201
ACTION_SCROLL_DOWN = 112
ACTION_SCROLL_UP = 111
ACTION_SELECT_ITEM = 7
ACTION_SETTINGS_LEVEL_CHANGE = 242
ACTION_SETTINGS_RESET = 241
ACTION_SHIFT = 118
ACTION_SHOW_CODEC = 27
ACTION_SHOW_FULLSCREEN = 36
ACTION_SHOW_GUI = 18
ACTION_SHOW_INFO = 11
ACTION_SHOW_OSD = 24
ACTION_SHOW_OSD_TIME = 123
ACTION_SHOW_PLAYLIST = 33
ACTION_SHOW_SUBTITLES = 25
ACTION_SHOW_VIDEOMENU = 134
ACTION_SMALL_STEP_BACK = 76
ACTION_STEP_BACK = 21
ACTION_STEP_FORWARD = 20
ACTION_STEREOMODE_NEXT = 235
ACTION_STEREOMODE_PREVIOUS = 236
ACTION_STEREOMODE_SELECT = 238
ACTION_STEREOMODE_SET = 240
ACTION_STEREOMODE_TOGGLE = 237
ACTION_STEREOMODE_TOMONO = 239
ACTION_STOP = 13
ACTION_SUBTITLE_ALIGN = 232
ACTION_SUBTITLE_DELAY = 162
ACTION_SUBTITLE_DELAY_MIN = 52
ACTION_SUBTITLE_DELAY_PLUS = 53
ACTION_SUBTITLE_VSHIFT_DOWN = 231
ACTION_SUBTITLE_VSHIFT_UP = 230
ACTION_SWITCH_PLAYER = 234
ACTION_SYMBOLS = 119
ACTION_TAKE_SCREENSHOT = 85
ACTION_TELETEXT_BLUE = 218
ACTION_TELETEXT_GREEN = 216
ACTION_TELETEXT_RED = 215
ACTION_TELETEXT_YELLOW = 217
ACTION_TOGGLE_DIGITAL_ANALOG = 202
ACTION_TOGGLE_FULLSCREEN = 199
ACTION_TOGGLE_SOURCE_DEST = 32
ACTION_TOGGLE_WATCHED = 200
ACTION_TOUCH_LONGPRESS = 411
ACTION_TOUCH_LONGPRESS_TEN = 420
ACTION_TOUCH_TAP = 401
ACTION_TOUCH_TAP_TEN = 410
ACTION_TRIGGER_OSD = 243
ACTION_VIS_PRESET_LOCK = 130
ACTION_VIS_PRESET_NEXT = 128
ACTION_VIS_PRESET_PREV = 129
ACTION_VIS_PRESET_RANDOM = 131
ACTION_VIS_PRESET_SHOW = 126
ACTION_VIS_RATE_PRESET_MINUS = 133
ACTION_VIS_RATE_PRESET_PLUS = 132
ACTION_VOLAMP = 90
ACTION_VOLAMP_DOWN = 94
ACTION_VOLAMP_UP = 93
ACTION_VOLUME_DOWN = 89
ACTION_VOLUME_SET = 245
ACTION_VOLUME_UP = 88
ACTION_VSHIFT_DOWN = 228
ACTION_VSHIFT_UP = 227
ACTION_ZOOM_IN = 31
ACTION_ZOOM_LEVEL_1 = 38
ACTION_ZOOM_LEVEL_2 = 39
ACTION_ZOOM_LEVEL_3 = 40
ACTION_ZOOM_LEVEL_4 = 41
ACTION_ZOOM_LEVEL_5 = 42
ACTION_ZOOM_LEVEL_6 = 43
ACTION_ZOOM_LEVEL_7 = 44
ACTION_ZOOM_LEVEL_8 = 45
ACTION_ZOOM_LEVEL_9 = 46
ACTION_ZOOM_LEVEL_NORMAL = 37
ACTION_ZOOM_OUT = 30
ALPHANUM_HIDE_INPUT = 2
CONTROL_TEXT_OFFSET_X = 10
CONTROL_TEXT_OFFSET_Y = 2
ICON_OVERLAY_HD = 6
ICON_OVERLAY_LOCKED = 3
ICON_OVERLAY_NONE = 0
ICON_OVERLAY_RAR = 1
ICON_OVERLAY_UNWATCHED = 4
ICON_OVERLAY_WATCHED = 5
ICON_OVERLAY_ZIP = 2
ICON_TYPE_FILES = 106
ICON_TYPE_MUSIC = 103
ICON_TYPE_NONE = 101
ICON_TYPE_PICTURES = 104
ICON_TYPE_PROGRAMS = 102
ICON_TYPE_SETTINGS = 109
ICON_TYPE_VIDEOS = 105
ICON_TYPE_WEATHER = 107
INPUT_ALPHANUM = 0
INPUT_DATE = 2
INPUT_IPADDRESS = 4
INPUT_NUMERIC = 1
INPUT_PASSWORD = 5
INPUT_TIME = 3
KEY_APPCOMMAND = 53248
KEY_ASCII = 61696
KEY_BUTTON_A = 256
KEY_BUTTON_B = 257
KEY_BUTTON_BACK = 275
KEY_BUTTON_BLACK = 260
KEY_BUTTON_DPAD_DOWN = 271
KEY_BUTTON_DPAD_LEFT = 272
KEY_BUTTON_DPAD_RIGHT = 273
KEY_BUTTON_DPAD_UP = 270
KEY_BUTTON_LEFT_ANALOG_TRIGGER = 278
KEY_BUTTON_LEFT_THUMB_BUTTON = 276
KEY_BUTTON_LEFT_THUMB_STICK = 264
KEY_BUTTON_LEFT_THUMB_STICK_DOWN = 281
KEY_BUTTON_LEFT_THUMB_STICK_LEFT = 282
KEY_BUTTON_LEFT_THUMB_STICK_RIGHT = 283
KEY_BUTTON_LEFT_THUMB_STICK_UP = 280
KEY_BUTTON_LEFT_TRIGGER = 262
KEY_BUTTON_RIGHT_ANALOG_TRIGGER = 279
KEY_BUTTON_RIGHT_THUMB_BUTTON = 277
KEY_BUTTON_RIGHT_THUMB_STICK = 265
KEY_BUTTON_RIGHT_THUMB_STICK_DOWN = 267
KEY_BUTTON_RIGHT_THUMB_STICK_LEFT = 268
KEY_BUTTON_RIGHT_THUMB_STICK_RIGHT = 269
KEY_BUTTON_RIGHT_THUMB_STICK_UP = 266
KEY_BUTTON_RIGHT_TRIGGER = 263
KEY_BUTTON_START = 274
KEY_BUTTON_WHITE = 261
KEY_BUTTON_X = 258
KEY_BUTTON_Y = 259
KEY_INVALID = 65535
KEY_MOUSE_CLICK = 57344
KEY_MOUSE_DOUBLE_CLICK = 57360
KEY_MOUSE_DRAG = 57604
KEY_MOUSE_DRAG_END = 57606
KEY_MOUSE_DRAG_START = 57605
KEY_MOUSE_END = 61439
KEY_MOUSE_LONG_CLICK = 57376
KEY_MOUSE_MIDDLECLICK = 57346
KEY_MOUSE_MOVE = 57603
KEY_MOUSE_NOOP = 61439
KEY_MOUSE_RDRAG = 57607
KEY_MOUSE_RDRAG_END = 57609
KEY_MOUSE_RDRAG_START = 57608
KEY_MOUSE_RIGHTCLICK = 57345
KEY_MOUSE_START = 57344
KEY_MOUSE_WHEEL_DOWN = 57602
KEY_MOUSE_WHEEL_UP = 57601
KEY_TOUCH = 61440
KEY_UNICODE = 61952
KEY_VKEY = 61440
KEY_VMOUSE = 61439
NOTIFICATION_ERROR = 'error'
NOTIFICATION_INFO = 'info'
NOTIFICATION_WARNING = 'warning'
PASSWORD_VERIFY = 1
REMOTE_0 = 58
REMOTE_1 = 59
REMOTE_2 = 60
REMOTE_3 = 61
REMOTE_4 = 62
REMOTE_5 = 63
REMOTE_6 = 64
REMOTE_7 = 65
REMOTE_8 = 66
REMOTE_9 = 67
__author__ = 'Team Kodi <http://kodi.tv>'
__credits__ = 'Team Kodi'
__date__ = 'Sat Oct 24 10:35:41 BST 2015'
__platform__ = 'ALL'
__version__ = '2.23.0'

#=====================================================================================================================
# API Methods
#=====================================================================================================================
def getCurrentWindowDialogId():
    return 0

def getCurrentWindowId():
    return 10000

#=====================================================================================================================
# API Classes
#=====================================================================================================================
class Dialog(object):
    def browse(self, dtype, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default="", enableMultiple=False):
        return default
    def browseMultiple(self, dtype, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default=""):
        return default
    def browseSingle(self, dtype, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default=""):
        return default
    def input(self, heading, default="", dtype=INPUT_ALPHANUM, option=0, autoclose=False):
        return default
    def multiselect(self, heading, list, autoclose=False):
        return [0]
    def notification(self, heading, message, icon=NOTIFICATION_INFO, time=5000, sound=True):
        if icon == NOTIFICATION_WARNING:
            prefix = "[WARNING]"
        elif icon == NOTIFICATION_ERROR:
            prefix = "[ERROR]"
        else:
            prefix = "[INFO]"
        print(u"NOTIFICATION: {0} {1}: {2}".format(prefix, heading, message))
    def numeric(self, dtype, heading, default=0):
        return default
    def ok(self, heading, *lines):
        output = ""
        print(heading)
        for line in lines:
            print(line)
            output = output + line + "\n"
        tkMessageBox.showinfo(heading, output)
        return True
    def select(self, heading, list, autoclose=False, preselect=None, useDetails=False):
        """preselect and useDetails added in v17.0"""
        return 0
    def textviewer(self, heading, text):
        tkMessageBox.showinfo(heading, text)
    def yesno(self, heading, line1, line2="", line3="", nolabel="No", yeslabel="Yes", autoclose=False):
        print('')
        print(heading)
        print(line1)
        print(line2)
        print(line3)
        print('1) %s/ 0) %s' % (yeslabel, nolabel))
        action = raw_input()
        return action
    def info(self, listitem):
        """Shows the info window for the passed in listitem. Added in v17.0"""
        pass
    def contextmenu(self, list):
        """Shows a context menu of items and returns the selected index, or -1 if cancelled. Added in v17.0"""
        return -1


class DialogBusy(object):
    """Show/Hide the progress indicator. Added in v17.0"""
    def create(self):
        print(u"[BUSY] show")
    def update(self, percent):
        print(u"[BUSY] update: {0}".format(percent))
    def close(self):
        print(u"[BUSY] close")
    def iscanceled(self):
        return False

class DialogProgress:
    canceled = False

    def __init__(self):
        pass

    def update(*args, **kwargs):
        print(args)
        print(kwargs)

    def create(self, *args):
        print(args)

    def iscanceled(self):
        return self.canceled

    def close(self):
        print('Dialog Closed')

class DialogProgressBG(object):
    def __init__(self):
        self._created = False
        self._heading = ""
        self._message = ""
        self._percent = 0
    def create(self, heading, message=""):
        self._created = True
        self._heading = heading
        self._message = message
        self._percent = 0
        print(u"[BACKGROUND] {0}: {1} - {2}%".format(self._heading, self._message, self._percent))
    def close(self):
        self._created = False
        print(u"[BACKGROUND] closing")
    def update(self, percent=None, heading=None, message=None):
        if percent is not None:
            self._percent = percent
        if heading is not None:
            self._heading = heading
        if message is not None:
            self._message = message
        print(u"[BACKGROUND] {0}: {1} - {2}%".format(self._heading, self._message, self._percent))
    def isFinished(self):
        return not self._created


class ListItem(object):
    def __init__(self, label="", label2="", iconImage="", thumbnailImage="", path=""):
        self._label = label
        self._label2 = label2
        self._icon = iconImage
        self._thumb = thumbnailImage
        self._path = path
        self._props = {}
        self._selected = False
        self.cm = []
        self.vitags = {}
        self.art = {}
        self.info = {}
        self.info_type = ''
        self.uniqueIDs = {}

    def addContextMenuItems(self, list, replaceItems=False):
        for i in list:
            self.cm.append(i)
        pass
    def addStreamInfo(self, streamtype, values):
        pass
    def getLabel(self):
        return self._label
    def getLabel2(self):
        return self._label2
    def getMusicInfoTag(self):
        pass
    def getProperty(self, key):
        key = key.lower()
        if key in self._props:
            return self._props[key]
        return ""
    def getVideoInfoTag(self):
        pass
    def getdescription(self):
        warnings.warn("getdescription deprecated in v17.0.", category=DeprecationWarning)
        return self._label
    def getduration(self):
        warnings.warn("getduration deprecated in v17.0. Use InfoTagMusic instead", category=DeprecationWarning)
        return "0"
    def getfilename(self):
        warnings.warn("getfilename deprecated in v17.0.", category=DeprecationWarning)
        return self._path
    def isSelected(self):
        return self._selected
    def select(self, selected):
        self._selected = selected
    def setArt(self, values):
        if values == None:
            return
        self.art.update(values)
        pass
    def setContentLookup(self, enable):
        pass
    def setIconImage(self, value):
        self._icon = value
    def setInfo(self, infotype, infoLabels):
        if infotype is None or infoLabels is None:
            return
        self.info_type = infotype
        self.info.update(infoLabels)
        pass
    def setLabel(self, label):
        self._label = label
    def setLabel2(self, label):
        self._label2 = label
    def setMimeType(self, mimetype):
        pass
    def setProperty(self, key, value):
        key = key.lower()
        self._props[key] = value
    def setSubtitles(self, list):
        warnings.warn("setSubtitles deprecated in v17.0", category=DeprecationWarning)
    def setThumbnailImage(self, value):
        self._thumb = value

    def getArt(self, key):
        """Returns a listitem art path as a string, similar to infolabel. Added in v17.0"""
        return ""
    def getPath(self):
        """Returns the path of this listitem. Added in v17.0"""
        return self._path
    def setCast(self, actors):
        """Set cast including thumbnails. Added in v17.0"""
        pass
    def setUniqueIDs(self, ids):
        self.uniqueIDs.update(ids)
        pass

    def __str__(self):
        return self._label.encode('utf-8')

class Window(object):
    "The window class allows creating a window, or can be used for quick messages and notifications"
    def __init__(self, windowId = 0):
        self._props = {}

    def addControl(self, Control):
        pass
    def addControls(self, List):
        pass
    def clearProperties(self):
        self._props.clear()
    def clearProperty(self, key):
        key = key.lower()
        if key in self._props:
            del self._props[key]
    def close(self):
        pass
    def doModal(self):
        pass
    def getControl(self, controlId):
        pass
    def getFocus(self):
        pass
    def getHeight(self):
        return 0
    def getProperty(self, key):
        key = key.lower()
        if key in self._props:
            return self._props[key]
        return ""
    def getResolution(self):
        return 0
    def getWidth(self):
        return 0
    def removeControl(self, Control):
        pass
    def removeControls(self, List):
        pass
    def setCoordinateResolution(self, resolution):
        pass
    def setFocus(self, Focus):
        pass
    def setFocusId(self, id):
        pass
    def setProperty(self, key, value):
        key = key.lower()
        self._props[key] = value
    def show(self):
        pass


class WindowDialog:

    stop_display = False
    info = []

    def __init__(self, *args, **kwargs):
        self.info.append(args + (kwargs,))
        pass

    def doModal(self, *args, **kwargs):
        self.info.append(args + (kwargs,))
        self.console_show()
        pass

    def addControl(self, *args, **kwargs):
        self.info.append(args + (kwargs,))
        pass

    def show(self, *args, **kwargs):
        thread = threading.Thread(target=self.console_show)

    def console_show(self):
        while not self.stop_display:
            print([k for i in self.info for k in i])
            time.sleep(1)

    def close(self):
        self.stop_display = True

class ControlImage:

    def __init__(self, *args, **kwargs):
        pass

    def setColorDiffuse(self, *args, **kwargs):
        pass

    def setImage(self, *args, **kwargs):
        pass

    def __str__(self):
        return ''


class ControlLabel:
    label = []

    def __init__(self, *args, **kwargs):
        pass

    def setLabel(self, *args, **kwargs):
        self.label = args
        print(self.label)

    def __str__(self):
        return str(self.label)

class ControlButton:

    def __init__(self, *args, **kwargs):
        pass

class ControlList:

    def __init__(self, *args, **kwargs):
        pass

class ControlTextBox:

    def __init__(self, *args, **kwargs):
        pass

