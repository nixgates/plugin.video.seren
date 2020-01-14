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
            self.providers.update({'all_debrid': ('All Debrid', AllDebridWalker)})
        if tools.premiumize_enabled():
            self.providers.update({'premiumize': ('Premiumize', PremiumizeWalker)})
        if tools.real_debrid_enabled():
            self.providers.update({'real_debrid': ('Real Debrid', RealDebridWalker)})


    def home(self):
        for i in self.providers:
            args = {'debrid_provider': i, 'id': None}
            tools.addDirectoryItem(self.providers[i][0], 'myFilesFolder', isPlayable=False, isFolder=True,
                                   actionArgs=json.dumps(args))

        tools.closeDirectory('addons', sort='title')

    def myFilesFolder(self, args):
        args = json.loads(args)
        if args['id'] is None:
            self.providers[args['debrid_provider']][1]().get_init_list()
        else:
            self.providers[args['debrid_provider']][1]().get_folder(args)
        tools.closeDirectory('addons', sort='title')

    def myFilesPlay(self, args):
        args = json.loads(args)
        self.providers[args['debrid_provider']][1]().play_item(args)


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
            art = {'thumb': 'None', 'poster': 'None'}

            actionArgs = json.dumps(i)
            tools.addDirectoryItem(i['name'], action, art=art, isPlayable=isPlayable, isFolder=isFolder,
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
            count += 1

        self._format_items(items)

    def resolve_link(self, list_item):
        return real_debrid.RealDebrid().resolve_hoster(list_item['link'])


class AllDebridWalker(BaseDebridWalker):

    provider = 'all_debrid'

    def get_init_list(self):
        items = all_debrid.AllDebrid().magnet_status('')

        items = [value for key, value in items.items() if type(value) == dict and value['status'] == 'Ready']

        for i in items:
            i['name'] = i['filename']

        self._format_items(items)

    def _is_folder(self, list_item):
        try:
            if len(list_item['links']) > 1:
                return True
            else:
                try:
                    list_item['link'] = [key for key, value in list_item['links'].iteritems()][0]
                except:
                    list_item['link'] = [key for key, value in list_item['links'].items()][0]
                return False
        except:
            return False

    def get_folder(self, list_item):
        folder = all_debrid.AllDebrid().magnet_status(list_item['id'])
        items = []

        try:
            links = [item for item in list_item['links'].iteritems()]
        except:
            links = [link for link in folder['links'].items()]

        for key, value in links:
            item = {}
            item['name'] = value
            item['links'] = {key: value}
            item['debrid_provider'] = self.provider
            items.append(item)

        self._format_items(items)

    def resolve_link(self, list_item):
        return all_debrid.AllDebrid().resolve_hoster(list_item['link'])


class IncorrectDebridProvider(Exception):
    pass
