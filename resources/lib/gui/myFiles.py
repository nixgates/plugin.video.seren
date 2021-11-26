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
        g.close_directory(g.CONTENT_MENU, sort='title')

    def my_files_folder(self, args):
        if args.get('id', args.get('path')) is None:
            self.providers[args['debrid_provider']][1]().get_init_list()
        else:
            self.providers[args['debrid_provider']][1]().get_folder(args)
        g.close_directory(g.CONTENT_MENU, sort='title')

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
                name = i['name']
                is_playable = False
                is_folder = True
                action = 'myFilesFolder'
            else:
                name = "{}  ({})".format(i['name'], tools.bytes_size_display(i['size'])) if i.get("size") else i['name']
                is_folder = False
                is_playable = True
                action = 'myFilesPlay'

            i.pop('links', None)  # De-clutter our action args a bit

            g.add_directory_item(name,
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
        root = real_debrid.RealDebrid().list_torrents()
        items = []

        for i in root:
            if not i['status'] == 'downloaded':
                continue
            item = {
                "id": i['id'],
                "name": i['filename'],
            }
            if len(i['links']) > 1:
                item['links'] = i['links']
            else:
                item['link'] = i['links'][0]
                item['size'] = i['bytes']
            items.append(item)

        self._format_items(items)

    def _is_folder(self, list_item):
        if list_item.get('links'):
            return True
        else:
            return False

    def get_folder(self, list_item):
        folder = real_debrid.RealDebrid().torrent_info(list_item['id'])
        files = [file for file in folder.get("files", []) if file.get("selected") == 1]
        items = []

        for p, i in enumerate(files):
            if not i['selected'] == 1:
                continue
            item = {
                "name": i['path'].split('/')[-1] if i['path'].startswith('/') else i['path'],
                "link": folder['links'][p],
                "size": i.get("bytes", 0)
            }
            items.append(item)

        self._format_items(items)

    def resolve_link(self, list_item):
        return real_debrid.RealDebrid().resolve_hoster(list_item['link'])


class AllDebridWalker(BaseDebridWalker):
    provider = 'all_debrid'

    def get_init_list(self):
        root = all_debrid.AllDebrid().magnet_status(None).get("magnets", [])
        items = []

        for i in root:
            if not (isinstance(i, dict) and i.get('status') == "Ready"):
                continue
            item = {
                "id": i['id'],
                "name": i['filename'],
                "links": sorted(
                    [
                        link
                        for link in i['links']
                        if (
                            len(self._get_lowest_level_filename_for_link_files(link.get("files", []))) == 1
                            and self._get_lowest_level_filename_for_link_files(link.get("files", []))[0].endswith(
                                tuple(g.common_video_extensions)
                            )
                        )
                    ],
                    key=lambda x: x['filename']
                )
            }
            if item.get("links"):
                items.append(item)

        self._format_items(items)

    def _is_folder(self, list_item):
        if list_item.get("links"):
            return True
        else:
            return False

    def get_folder(self, list_item):
        links = all_debrid.AllDebrid().magnet_status(list_item['id']).get("magnets", []).get("links", [])
        items = []

        for l in links:
            filenames = self._get_lowest_level_filename_for_link_files(l.get("files", []))
            if not (len(filenames) == 1 and filenames[0].endswith(tuple(g.common_video_extensions))):
                continue
            item = {
                "name": filenames[0],
                "link": l.get("link"),
                "size": l.get("size", 0)
            }
            items.append(item)

        self._format_items(sorted(items, key=lambda x: x['name']))

    def _get_lowest_level_filename_for_link_files(self, files_item):
        files = []
        for file in files_item if isinstance(files_item, list) else [files_item]:
            entities = file.get('e')
            if entities:
                files.extend(self._get_lowest_level_filename_for_link_files(entities))
            else:
                files.append(file.get('n'))
        return files

    def resolve_link(self, list_item):
        return all_debrid.AllDebrid().resolve_hoster(list_item['link'])


class LocalFileWalker(BaseDebridWalker):
    provider = 'local_downloads'
    downloads_folder = g.DOWNLOAD_PATH

    def _get_folder_list(self, path):
        directory_listing = xbmcvfs.listdir(path)
        contents = [tools.ensure_path_is_dir(i) for i in directory_listing[0]] + [i for i in directory_listing[1]]
        return [{"name": i[:-1] if i.endswith(("\\", "/")) else i,
                 "path": os.path.join(path, i),
                 "size": xbmcvfs.Stat(os.path.join(path, i)).st_size()
                 }
                for i in contents]

    def get_init_list(self):
        self._format_items(self._get_folder_list(self.downloads_folder))

    def _is_folder(self, list_item):
        return list_item['path'].endswith(('\\', '/'))

    def get_folder(self, list_item):
        self._format_items(self._get_folder_list(list_item['path']))

    def resolve_link(self, list_item):
        return list_item['path']
