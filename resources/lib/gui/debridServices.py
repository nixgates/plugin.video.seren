from resources.lib.modules import database
from resources.lib.common import tools


class Menus:

    def __init__(self):
        self.view_type = 'addons'

    def home(self):
        tools.addDirectoryItem('Cache Assist History', 'cacheAssistStatus', None, None)
        if tools.getSetting('premiumize.enabled') == 'true':
            tools.addDirectoryItem('Current Premiumize Transfers', 'premiumizeTransfers', None, None)
        if tools.getSetting('realdebrid.enabled') == 'true':
            tools.addDirectoryItem('Current Real Debrid Transfers', 'realdebridTransfers', None, None)
        tools.closeDirectory(self.view_type)

    def get_assist_torrents(self):
        tools.addDirectoryItem('Clear Non Active...', 'nonActiveAssistClear', None, None)
        torrent_list = database.get_assist_torrents()
        if torrent_list is not None:

            for i in torrent_list:
                debrid = tools.shortened_debrid(i['provider'])
                title = tools.colorString('%s - %s - %s%% : %s' % (debrid, i['status'].title(),
                                                                 i['progress'], i['release_title']))
                tools.addDirectoryItem(title, '', None, None)

        tools.closeDirectory('addons')

    def assist_non_active_clear(self):
        database.clear_non_active_assist()

    def list_premiumize_transfers(self):

        from resources.lib.debrid import premiumize
        transfer_list = premiumize.PremiumizeFunctions().list_transfers()
        if len(transfer_list['transfers']) == 0 or 'transfers' not in transfer_list:
            tools.closeDirectory(self.view_type)
            return
        for i in transfer_list['transfers']:
            title = '%s - %s%% : %s' % \
                    (tools.colorString(i['status'].title()), str(i['progress'] * 100), i['name'][:50] + "...")
            tools.addDirectoryItem(title, '', None, None, isPlayable=False, isFolder=False, isAction=True)
        tools.closeDirectory(self.view_type)

    def list_RD_transfers(self):

        from resources.lib.debrid import real_debrid
        transfer_list = real_debrid.RealDebrid().list_torrents()
        if len(transfer_list) == 0:
            tools.closeDirectory(self.view_type)
            return
        for i in transfer_list:
            title = '%s - %s%% : %s' % \
                    (tools.colorString(i['status'].title()), str(i['progress']), i['filename'][:50] + "...")
            tools.addDirectoryItem(title, '', None, None, isPlayable=False, isFolder=False, isAction=True)
        tools.closeDirectory(self.view_type)