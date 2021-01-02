# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.common import tools
from resources.lib.database.torrentAssist import TorrentAssist
from resources.lib.modules.globals import g


class Menus:

    def __init__(self):
        self.view_type = g.CONTENT_FOLDER
        self.torrent_assist = TorrentAssist()

    def home(self):
        g.add_directory_item(g.get_language_string(30242), action='cacheAssistStatus')
        if g.get_bool_setting('premiumize.enabled'):
            g.add_directory_item(g.get_language_string(30243), action='premiumize_transfers')
        if g.get_bool_setting('realdebrid.enabled'):
            g.add_directory_item(g.get_language_string(30244), action='realdebridTransfers')
        g.close_directory(self.view_type)

    def get_assist_torrents(self):
        g.add_directory_item(g.get_language_string(30245), action='nonActiveAssistClear')
        torrent_list = self.torrent_assist.get_assist_torrents()
        if torrent_list is not None:

            for i in torrent_list:
                debrid = tools.shortened_debrid(i['provider'])
                title = g.color_string('{} - {} - {}% : {}'.format(debrid,
                                                                   i['status'].title(),
                                                                   i['progress'],
                                                                   i['release_title']))
                g.add_directory_item(title)

        g.close_directory(self.view_type)

    def assist_non_active_clear(self):
        self.torrent_assist.clear_non_active_assist()

    def list_premiumize_transfers(self):

        from resources.lib.debrid import premiumize
        transfer_list = premiumize.Premiumize().list_transfers()
        if len(transfer_list['transfers']) == 0 or 'transfers' not in transfer_list:
            g.close_directory(self.view_type)
            return
        for i in transfer_list['transfers']:
            title = '{} - {}% : {}' \
                .format(g.color_string(i['status'].title()), str(i['progress'] * 100), i['name'][:50] + "...")
            g.add_directory_item(title)
        g.close_directory(self.view_type)

    def list_rd_transfers(self):

        from resources.lib.debrid import real_debrid
        transfer_list = real_debrid.RealDebrid().list_torrents()
        if len(transfer_list) == 0:
            g.close_directory(self.view_type)
            return
        for i in transfer_list:
            title = '{} - {}% : {}' \
                .format(g.color_string(i['status'].title()), str(i['progress']), i['filename'][:50] + "...")
            g.add_directory_item(title)
        g.close_directory(self.view_type)
