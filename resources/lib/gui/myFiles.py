import json
import sys

from resources.lib.common import tools
from resources.lib.debrid import premiumize, real_debrid, all_debrid
from resources.lib.common.worker import ThreadPool

try:
    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
except:
    pass

class Menus:

    def __init__(self):
        self.threads = []
        self.menu_list = []
        self.thread_pool = ThreadPool()
        self.providers = {}
        if tools.all_debrid_enabled():
            self.providers.update({'all_debrid': AllDebridWalker})
        if tools.premiumize_enabled():
            self.providers.update({'premiumize': PremiumizeWalker})
        if tools.real_debrid_enabled():
            self.providers.update({'real_debrid': RealDebridWalker})


    def home(self):
        for key, value in self.providers.iteritems():
            self.thread_pool.put(value().get_init_list)

        self.thread_pool.wait_completion()

        tools.closeDirectory('addons', sort='title')

    def myFilesFolder(self, args):
        args = json.loads(args)
        self.providers[args['debrid_provider']]().get_folder(args)
        tools.closeDirectory('files', sort='title')

    def myFilesPlay(self, args):
        args = json.loads(args)
        self.providers[args['debrid_provider']]().play_item(args)


class BaseDebridWalker:

    provider = ''

    def get_init_list(self):
        """
        Return initial listing for menu
        :return:
        """
        pass

    def _is_folder(self, list_item):
        """
        Returns True if item is a folder
        Returns False if items is a playable file
        :param list_item:
        :return:
        """
        pass

    def get_folder(self, list_item):
        """
        Creates new Kodi menu list from list_item
        :param list_item:
        :return:
        """

    def play_item(self, args):
        resolved_link = self.resolve_link(args)
        item = tools.menuItem(path=resolved_link)

        tools.resolvedUrl(syshandle, True, item)

    def _format_items(self, items):
        for i in items:
            i.update({'debrid_provider': self.provider})
            if self._is_folder(i):
                isPlayable = False
                isFolder = True
                action = 'myFilesFolder'
            else:
                isPlayable = True
                isFolder = False
                action = 'myFilesPlay'

            actionArgs = json.dumps(i)
            tools.addDirectoryItem(i['name'], action, isPlayable=isPlayable, isFolder=isFolder,
                                   actionArgs=tools.quote(actionArgs))

    def resolve_link(self, args):
        """
        Returns playable link from arguments
        :param args:
        :return:
        """


class PremiumizeWalker(BaseDebridWalker):

    provider = 'premiumize'

    def get_init_list(self):
        items = premiumize.Premiumize().list_folder('')
        self._format_items(items)

    def _is_folder(self, list_item):
        if list_item['type'] == 'folder':
            return True
        else:
            return False

    def get_folder(self, list_item):
        items = premiumize.Premiumize().list_folder(list_item['id'])
        self._format_items(items)

    def resolve_link(self, list_item):
        return list_item['link']


class RealDebridWalker(BaseDebridWalker):

    provider = 'real_debrid'

    def get_init_list(self):
        items = real_debrid.RealDebrid().list_torrents()

        items = [i for i in items if i['status'] == 'downloaded']
        for i in items:
            i['name'] = i['filename']
        self._format_items(items)

    def _is_folder(self, list_item):
        if len(list_item['links']) > 1:
            return True
        else:
            list_item['link'] = list_item['links'][0]
            return False

    def get_folder(self, list_item):
        folder = real_debrid.RealDebrid().torrentInfo(list_item['id'])
        items = folder['files']
        items = [i for i in items if i['selected'] == 1]
        count = 0
        for i in items:
            i['name'] = i['path']
            if i['name'].startswith('/'):
                i['name'] = i['name'].split('/')[-1]
            i['links'] = [folder['links'][count]]
        self._format_items(items)

    def resolve_link(self, list_item):
        return real_debrid.RealDebrid().resolve_hoster(list_item['link'])


class AllDebridWalker(BaseDebridWalker):

    provider = 'all_debrid'

    def get_init_list(self):
        items = all_debrid.AllDebrid().magnet_status('')
        for i in items:
            i['name'] = i['filename']
        self._format_items(items)

    def _is_folder(self, list_item):
        if len(list_item['links']) > 1:
            return True
        else:
            return False

    def get_folder(self, list_item):
        folder = all_debrid.AllDebrid().magnet_status(list_item['id'])
        items = []
        for key, value in folder['links']:
            item = {}
            item['name'] = value
            item['link'] = key
            item['debrid_provider'] = self.provider
        self._format_items(items)

    def resolve_link(self, list_item):
        return real_debrid.RealDebrid().resolve_hoster(list_item['link'])


class IncorrectDebridProvider(Exception):
    pass
