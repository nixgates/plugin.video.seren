from functools import cached_property

from resources.lib.common import tools
from resources.lib.modules.globals import g


class Menus:
    def __init__(self):
        self.view_type = g.CONTENT_MENU

    @cached_property
    def torrent_assist(self):
        from resources.lib.database.torrentAssist import TorrentAssist

        return TorrentAssist()

    def home(self):
        g.add_directory_item(
            g.get_language_string(30219),
            action='cacheAssistStatus',
            menu_item=g.create_icon_dict("cloud_files", g.ICONS_PATH),
        )
        if g.get_bool_setting('premiumize.enabled'):
            g.add_directory_item(
                g.get_language_string(30220),
                action='premiumize_transfers',
                menu_item=g.create_icon_dict("premiumize", g.ICONS_PATH),
            )
        if g.get_bool_setting('realdebrid.enabled'):
            g.add_directory_item(
                g.get_language_string(30221),
                action='realdebridTransfers',
                menu_item=g.create_icon_dict("real_debrid", g.ICONS_PATH),
            )
        g.close_directory(self.view_type)

    def get_assist_torrents(self):
        g.add_directory_item(g.get_language_string(30222), action='nonActiveAssistClear')
        torrent_list = self.torrent_assist.get_assist_torrents()
        if torrent_list is not None:

            for i in torrent_list:
                debrid = tools.shortened_debrid(i['provider'])
                title = g.color_string(f"{debrid} - {i['status'].title()} - {i['progress']}% : {i['release_title']}")
                g.add_directory_item(title, is_playable=False, is_folder=False)

        g.close_directory(self.view_type)

    def assist_non_active_clear(self):
        self.torrent_assist.clear_non_active_assist()

    def list_premiumize_transfers(self):
        from resources.lib.debrid import premiumize

        transfer_list = premiumize.Premiumize().list_transfers()
        if len(transfer_list['transfers']) == 0 or "transfers" not in transfer_list:
            g.close_directory(self.view_type)
            return
        for i in transfer_list['transfers']:
            title = "{} - {}% : {}".format(  # sourcery skip: use-fstring-for-formatting
                g.color_string(i['status'].title().title()),
                str(i['progress'] * 100),
                f"{i['name'][:50]}..." if len(i['name']) > 50 else i['name'],
            )
            g.add_directory_item(
                title, is_playable=False, is_folder=False, menu_item=g.create_icon_dict("premiumize", g.ICONS_PATH)
            )
        g.close_directory(self.view_type)

    def list_rd_transfers(self):
        from resources.lib.debrid import real_debrid

        transfer_list = real_debrid.RealDebrid().list_torrents()
        if len(transfer_list) == 0:
            g.close_directory(self.view_type)
            return
        for i in transfer_list:
            title = "{} - {}% : {}".format(  # sourcery skip: use-fstring-for-formatting
                g.color_string(i['status'].title()),
                str(i['progress']),
                f"{i['filename'][:50]}..." if len(i['filename']) > 50 else i['filename'],
            )
            g.add_directory_item(
                title, is_playable=False, is_folder=False, menu_item=g.create_icon_dict("real_debrid", g.ICONS_PATH)
            )
        g.close_directory(self.view_type)
