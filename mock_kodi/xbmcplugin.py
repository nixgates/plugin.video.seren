import sys
import os
import re

#======================================================================================================================
# API Constants
#======================================================================================================================
SORT_METHOD_ALBUM = 14
SORT_METHOD_ALBUM_IGNORE_THE = 15
SORT_METHOD_ARTIST = 11
SORT_METHOD_ARTIST_IGNORE_THE = 13
SORT_METHOD_BITRATE = 42
SORT_METHOD_CHANNEL = 40
SORT_METHOD_COUNTRY = 17
SORT_METHOD_DATE = 3
SORT_METHOD_DATEADDED = 21
SORT_METHOD_DATE_TAKEN = 43
SORT_METHOD_DRIVE_TYPE = 6
SORT_METHOD_DURATION = 8
SORT_METHOD_EPISODE = 24
SORT_METHOD_FILE = 5
SORT_METHOD_FULLPATH = 34
SORT_METHOD_GENRE = 16
SORT_METHOD_LABEL = 1
SORT_METHOD_LABEL_IGNORE_FOLDERS = 35
SORT_METHOD_LABEL_IGNORE_THE = 2
SORT_METHOD_LASTPLAYED = 36
SORT_METHOD_LISTENERS = 38
SORT_METHOD_MPAA_RATING = 30
SORT_METHOD_NONE = 0
SORT_METHOD_PLAYCOUNT = 37
SORT_METHOD_PLAYLIST_ORDER = 23
SORT_METHOD_PRODUCTIONCODE = 28
SORT_METHOD_PROGRAM_COUNT = 22
SORT_METHOD_SIZE = 4
SORT_METHOD_SONG_RATING = 29
SORT_METHOD_STUDIO = 32
SORT_METHOD_STUDIO_IGNORE_THE = 33
SORT_METHOD_TITLE = 9
SORT_METHOD_TITLE_IGNORE_THE = 10
SORT_METHOD_TRACKNUM = 7
SORT_METHOD_UNSORTED = 39
SORT_METHOD_VIDEO_RATING = 19
SORT_METHOD_VIDEO_RUNTIME = 31
SORT_METHOD_VIDEO_SORT_TITLE = 26
SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE = 27
SORT_METHOD_VIDEO_TITLE = 25
SORT_METHOD_VIDEO_USER_RATING = 20
SORT_METHOD_VIDEO_YEAR = 18
__author__ = 'Team Kodi <http://kodi.tv>'
__credits__ = 'Team Kodi'
__date__ = 'Sat Oct 24 10:35:45 BST 2015'
__platform__ = 'ALL'
__version__ = '2.23.0'

class directory:
    print('Creating New Directory')
    history = []
    items = []
    last_action = ''

    def closeDirectory(self):
        print('OUTER LOOP')
        while True:
            print('loop')
            print('-------------------------------')
            print('-1) Back')
            print(' 0) Home')
            print('-------------------------------')
            for idx, item in enumerate(self.items):
                print(' %s) %s' % (idx + 1, item[0]))
            try:
                print('')
                print("Enter Action Number")
                action = raw_input()
                sys.argv = ['', 0, None]
                try:
                    action = int(action) - 1
                    if action == -2:
                        if len(self.history) > 0:
                            sys.argv = ['', 0, self.history.pop(-1)]
                            self.last_action = ''
                        return
                    elif action == -1:
                        sys.argv = ['', 0, '']
                    else:
                        sys.argv = ['', 0, self.items[action][1]]

                except:
                    action = str(action)
                    print('STRING ACTION')
                    print(action)
                    if action.startswith('action'):
                        try:
                            action = re.findall(r'action (.*?)$', action)[0]
                            sys.argv = ['', 0, action]
                        except:
                            print('failed')

                    elif action == 'shell':
                        print('RUN SHELL')
                        import code
                        variables = globals().copy()
                        variables.update(locals())
                        try:
                            shell = code.InteractiveConsole(variables)
                            shell.interact()
                        except:
                            self.items = []
                            self.history.append(self.last_action)
                            execfile(os.path.abspath(os.path.join(os.getcwd(), 'seren.py')))

                    else:
                        raise Exception

                break
            except:
                import traceback
                traceback.print_exc()
                import time
                time.sleep(10)
                print('Please enter a valid entry')

        self.items = []
        if self.last_action != '':
            self.history.append(self.last_action)
            self.last_action = sys.argv[2]
        execfile(os.path.abspath(os.path.join(os.getcwd(), 'seren.py')))

DIRECTORY = directory()

#=====================================================================================================================
# API Methods
#=====================================================================================================================
def addDirectoryItem(handle, url, listitem, isFolder=False, totalItems=0):
    global DIRECTORY_ITEMS
    DIRECTORY.items.append((listitem, url, isFolder))
    pass

def addDirectoryItems(handle, items, totalItems=0):
    pass

def addSortMethod(handle, sortMethod, label2Mask="D"):
    pass

def endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True):
    DIRECTORY.closeDirectory()
    pass

def getSetting(handle, key):
    return ""

def setContent(handle, content):
    return ""

def setPluginCategory(handle, category):
    pass

def setPluginFanart(handle, image, color1, color2, color3):
    pass

def setProperty(handle, key, value):
    pass

def setResolvedUrl(handle, succeeded, listitem):
    pass

def setSetting(handle, id, value):
    pass