# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import abc
import os

import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.debrid import premiumize, real_debrid, all_debrid
from resources.lib.modules.globals import g


class Menus:

    def __init__(self):
        self.thread_pool = ThreadPool()
        self.providers = {}
        if g.all_debrid_enabled():
            self.providers.update({'all_debrid': ('All Debrid', AllDebridWalker)})
        if g.premiumize_enabled():
            self.providers.update({'premiumize': ('Premiumize', PremiumizeWalker)})
        if g.real_debrid_enabled():
            self.providers.update({'real_debrid': ('Real Debrid', RealDebridWalker)})
        self.providers.update({'local_downloads': ('Local Downloads', LocalFileWalker)})

    def home(self):
        for key, value in sorted(self.providers.items()):
            args = {'debrid_provider': key, 'id': None}
            g.add_directory_item(value[0], action='myFilesFolder', action_args=args)
        g.close_directory(g.CONTENT_FOLDER, sort='title')

    def my_files_folder(self, args):
        if args.get('id') is None:
            self.providers[args['debrid_provider']][1]().get_init_list()
        else:
            self.providers[args['debrid_provider']][1]().get_folder(args)
        g.close_directory(g.CONTENT_FOLDER, sort='title')

    def my_files_play(self, args):
        self.providers[args['debrid_provider']][1]().play_item(args)


class BaseDebridWalker:
    provider = ''


    @abc.abstractmethod
    def get_init_list(self):
        """
        Return initial listing for menu
        :return:
        """
        pass

    @abc.abstractmethod
    def _is_folder(self, list_item):
        """
        Returns True if item is a folder
        Returns False if items is a playable file_path
        :param list_item:
        :return:
        """
        pass

    @abc.abstractmethod
    def get_folder(self, list_item):
        """
        Creates new Kodi menu list from list_item
        :param list_item:
        :return:
        """
        pass

    def play_item(self, args):
        resolved_link = self.resolve_link(args)
        item = xbmcgui.ListItem(path=resolved_link)
        xbmcplugin.setResolvedUrl(g.PLUGIN_HANDLE, True, item)

    def _format_items(self, items):
        for i in items:
            i.update({'debrid_provider': self.provider})
            if self._is_folder(i):
                is_playable = False
                is_folder = True
                action = 'myFilesFolder'
            else:
                is_folder = False
                is_playable = True
                action = 'myFilesPlay'

            g.add_directory_item(i['name'],
                                 action=action,
                                 is_playable=is_playable,
                                 is_folder=is_folder,
                                 action_args=i)

    @abc.abstractmethod
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
        folder = real_debrid.RealDebrid().torrent_info(list_item['id'])

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
        items = all_debrid.AllDebrid().magnet_status('')['magnets']

        items = [i for i in items if isinstance(i, dict) and i.get('status') == 'Ready']

        for i in items:
            i['name'] = i['filename']
            i['links'] = sorted([l for l in i['links'] if l['files'] and any(ext for ext in g.common_video_extensions if l['filename'].endswith(ext))], key=lambda x: x['filename'])

        self._format_items(d for d in items if d['links'])

    def _is_folder(self, list_item):
        if len(list_item['links']) > 1:
            return True
        else:
            list_item['link'] = list_item['links'][0]
            return False

    def get_folder(self, list_item):
        folder = all_debrid.AllDebrid().magnet_status(list_item['id']).get('magnets', [])
        items = []

        links = [link for link in folder.get('links', [])]

        for link in links:
            item = {
                'name': folder.get('filename'),
                'links': link.get('link'),
                'debrid_provider': self.provider
            }
            items.append(item)

        self._format_items(items)

    def resolve_link(self, list_item):
        return all_debrid.AllDebrid().resolve_hoster(list_item['link'])


class LocalFileWalker(BaseDebridWalker):

    provider = 'local_downloads'
    downloads_folder = g.DOWNLOAD_PATH

    def _get_folder_list(self, path):
        directory_listing = xbmcvfs.listdir(path)
        contents = [tools.ensure_path_is_dir(i) for i in directory_listing[0]] + [i for i in directory_listing[1]]
        return [{'name': i[:-1] if i.endswith('\\') else i,
                 'path': os.path.join(path, i),
                 'debrid_provider': self.provider}
                for i in contents]

    def get_init_list(self):
        self._format_items(self._get_folder_list(self.downloads_folder))

    def _is_folder(self, list_item):
        return list_item['path'].endswith('\\')

    def get_folder(self, list_item):
        self._format_items(self._get_folder_list(list_item['path']))

    def resolve_link(self, list_item):
        return list_item['path']
