import json
import sys
import threading

from resources.lib.common import tools, source_utils
from resources.lib.debrid import premiumize, real_debrid

try:
    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
except:
    pass

class Menus:

    def __init__(self):
        self.threads = []
        self.premiumize_files = []
        self.real_debrid_files = []

    def home(self):
        if tools.premiumize_enabled():
            self.threads.append(threading.Thread(target=self.thread_worker, args=(self.get_premiumize_files, '')))

        if tools.real_debrid_enabled():
            self.threads.append(threading.Thread(target=self.thread_worker, args=(self.get_real_debrid_files,)))

        self.run_threads()

        for file in self.real_debrid_files:
            file.update({'debrid_provider': 'real_debrid'})
            if len(file['links']) > 1:
                isPlayable = False
                isFolder = True
                action = 'myFilesFolder'
            else:
                isPlayable = True
                isFolder = False
                action = 'myFilesPlay'
                file['link'] = file['links'][0]
            actionArgs = json.dumps(file)
            tools.addDirectoryItem(file['filename'], action, None, None, isPlayable=isPlayable, isFolder=isFolder,
                                   actionArgs=actionArgs)

        for file in self.premiumize_files:
            file.update({'debrid_provider': 'premiumize'})
            actionArgs = json.dumps(file)
            if file['type'] == 'folder':
                isPlayable = False
                isFolder = True
                action = 'myFilesFolder'
            else:
                isPlayable = True
                isFolder = False
                action = 'myFilesPlay'

            tools.addDirectoryItem(file['name'], action, None, None, isPlayable=isPlayable, isFolder=isFolder,
                                   actionArgs=actionArgs)

        tools.closeDirectory('addon')

    def myFilesFolder(self, args):
        args = json.loads(args)
        if args['debrid_provider'] == 'real_debrid':
            self.get_real_debrid_folder(args)
        elif args['debrid_provider'] == 'premiumize':
            self.get_premiumize_folder(args)

    def myFilesPlay(self, args):
        args = json.loads(args)

        if args['debrid_provider'] == 'real_debrid':
            resolved_link = real_debrid.RealDebrid().unrestrict_link(args['link'])
        elif args['debrid_provider'] == 'premiumize':
            resolved_link = args['link']
        else:
            raise IncorrectDebridProvider

        item = tools.menuItem(path=resolved_link)

        tools.resolvedUrl(syshandle, True, item)

    def get_real_debrid_folder(self, args):
        internal_files = real_debrid.RealDebrid().torrentInfo(args['id'])
        selected_files = [i for i in internal_files['files'] if i['selected'] == 1]

        for idx, file in enumerate(selected_files):
            file['link'] = internal_files['links'][idx]
        try:
            selected_files = sorted(selected_files, key=lambda i: i['path'])
        except:
            import traceback
            traceback.print_exc()

        for file in selected_files:
            file.update({'debrid_provider': 'real_debrid'})
            args = json.dumps(file)
            name = file['path']
            if name.startswith('/'):
                name = name.split('/')[-1]
            tools.addDirectoryItem(name, 'myFilesPlay', None, None, isPlayable=True, isFolder=False,
                                   actionArgs=args)

        tools.closeDirectory('video')

    def get_premiumize_folder(self, args):
        internal_files = premiumize.PremiumizeFunctions().list_folder(args['id'])
        for file in internal_files:
            file.update({'debrid_provider': 'premiumize'})
            actionArgs = json.dumps(file)
            if file['type'] == 'folder':
                isPlayable = False
                isFolder = True
                action = 'myFilesFolder'
            else:
                if not any(file['name'].endswith(ext) for ext in source_utils.COMMON_VIDEO_EXTENSIONS):
                    continue
                isPlayable = True
                isFolder = False
                action = 'myFilesPlay'

            tools.addDirectoryItem(file['name'], action, None, None, isPlayable=isPlayable, isFolder=isFolder,
                                   actionArgs=actionArgs)

        tools.closeDirectory('addons')

    def get_real_debrid_files(self):
        torrents = real_debrid.RealDebrid().list_torrents()
        torrents = [i for i in torrents if i['status'] == 'downloaded']
        self.real_debrid_files = torrents

    def get_premiumize_files(self, folder_id):
        self.premiumize_files = premiumize.PremiumizeFunctions().list_folder(folder_id)

    def run_threads(self):

        for i in self.threads:
            i.start()

        for i in self.threads:
            i.join()

        self.threads = []

    def thread_worker(self, target, *args):
        target(*args)

class IncorrectDebridProvider(Exception):
    pass
