# -*- coding: utf-8 -*-

import json
import threading
import time
import xbmc

from resources.lib.common import tools
from resources.lib.debrid import premiumize
from resources.lib.debrid import real_debrid
from resources.lib.modules import database

monitor = xbmc.Monitor()


class CacheAssit:
    def __init__(self, url):
        url = json.loads(tools.unquote(url))
        args = url['args']
        torrent_list = url['torrent_list']

        if 'showInfo' in args:
            self.title = args['showInfo']['info']['originaltitle']
        else:
            self.title = args['title']

        cache_location = int(tools.getSetting('general.cachelocation'))

        threads = []
        self.notified = False

        if cache_location == 0 and tools.getSetting('premiumize.enabled') == 'true':
            threads.append(threading.Thread(target=self.premiumize_downloader, args=(torrent_list[0],)))

        elif cache_location == 1 and tools.getSetting('realdebrid.enabled') == 'true':
            threads.append(threading.Thread(target=self.real_debrid_downloader(torrent_list[0])))
            pass

        for i in threads:
            i.start()
        for i in threads:
            i.join()

    def premiumize_downloader(self, torrent_object):
        current_percent = 0
        debrid = premiumize.PremiumizeFunctions()

        try:
            transfer_id = debrid.create_transfer(torrent_object['magnet'])['id']
            tools.showDialog.notification(tools.addonName, tools.lang(32072))
            database.add_assist_torrent(transfer_id, 'premiumize', 'queued',
                                        torrent_object['release_title'], str(current_percent))
        except:
            import traceback
            traceback.print_exc()
            tools.log('Failed to start premiumize debrid transfer', 'error')
            return

        timestamp = time.time()
        while not monitor.abortRequested():
            try:
                if monitor.waitForAbort(120):
                    break
                transfer_status = [i for i in debrid.list_transfers()['transfers'] if i['id'] == transfer_id][0]
                current_percent = transfer_status['progress']
                if transfer_status['status'] == 'finished':
                    database.add_assist_torrent(transfer_id, 'premiumize', transfer_status['status'],
                                                torrent_object['release_title'], str(current_percent))
                    if self.notified == False:
                        tools.showDialog.notification(tools.addonName + ': %s' % self.title,
                                                      'New cached sources have been created for %s' % self.title,
                                                      time=5000)
                        debrid.delete_transfer(transfer_id)
                        database.add_premiumize_transfer(transfer_id)
                        from resources.lib.common import maintenance
                        maintenance.premiumize_transfer_cleanup()
                    break
                if current_percent == transfer_status['progress']:
                    if timestamp == (time.time() + 10800):
                        database.add_assist_torrent(transfer_id, 'premiumize', 'failed',
                                                    torrent_object['release_title'],
                                                    str(current_percent))
                        debrid.delete_transfer(transfer_id)
                        tools.showDialog.notification(tools.addonName,
                                                      'Cache assist for %s has failed due to no progress'
                                                      % self.title)
                        break
                    continue
                else:
                    database.add_assist_torrent(transfer_id, 'premiumize', transfer_status['status'],
                                                torrent_object['release_title'],
                                                str(current_percent))

            except:
                database.add_assist_torrent(transfer_id, 'premiumize', 'failed', torrent_object['release_title'],
                                            str(current_percent))
                debrid.delete_transfer(transfer_id)

                break

        return

    def real_debrid_downloader(self, torrent_object):
        from resources.lib.common import source_utils

        tools.showDialog.notification(tools.addonName, tools.lang(32072))
        current_percent = 0
        debrid = real_debrid.RealDebrid()
        magnet = debrid.addMagnet(torrent_object['magnet'])
        info = debrid.torrentInfo(magnet['id'])
        torrent_id = info['id']
        database.add_assist_torrent(torrent_id, 'real_debrid', 'queued', torrent_object['release_title'],
                                    str(current_percent))

        key_list = []

        for file in info['files']:
            filename = file['path']
            key = file['id']
            if any(filename.lower().endswith(extension) for extension in
                   source_utils.COMMON_VIDEO_EXTENSIONS):
                key_list.append(str(key))
                break

        debrid.torrentSelect(torrent_id, ','.join(key_list))
        downloading_status = ['queued', 'downloading']
        current_percent = 0
        timestamp = time.time()

        while not monitor.abortRequested():
            if monitor.waitForAbort(120):
                break
            try:

                info = debrid.torrentInfo(torrent_id)

                if info['status'] == 'downloaded':
                    tools.showDialog.notification(tools.addonName + ': %s' % self.title,
                                                  tools.lang(32072) + ' %s' % self.title,
                                                  time=5000)
                    database.add_assist_torrent(torrent_id, 'real_debrid', 'finished', torrent_object['release_title'],
                                                str(current_percent))
                    debrid.deleteTorrent(torrent_id)
                    break

                if info['status'] in downloading_status:
                    if info['progress'] == current_percent:
                        if timestamp == (time.time() + 10800):
                            database.add_assist_torrent(torrent_id, 'real_debrid', 'failed',
                                                        torrent_object['release_title'],
                                                        str(current_percent))
                            debrid.deleteTorrent(torrent_id)
                            tools.showDialog.notification(tools.addonName,
                                                          'Cache assist for %s has failed due to no progress'
                                                          % self.title)
                            break
                        continue

                    else:
                        database.add_assist_torrent(torrent_id, 'real_debrid', 'downloading',
                                                    torrent_object['release_title'],
                                                    str(current_percent))
                        current_percent = info['progress']
                    continue
                else:
                    database.add_assist_torrent(torrent_id, 'real_debrid', 'failed', torrent_object['release_title'],
                                                str(current_percent))
                    debrid.deleteTorrent(torrent_id)
                    tools.log('Could not create cache for magnet- %s' % torrent_object['magnet'], 'info')
                    tools.showDialog.notification(tools.addonName,
                                                  'Cache assist for %s has failed according to Real Debrid'
                                                  % self.title)
                    break
            except:
                debrid.deleteTorrent(torrent_id)