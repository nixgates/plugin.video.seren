import time, threading, json, xbmc
from resources.lib.debrid import premiumize
from resources.lib.debrid import real_debrid
from resources.lib.common import tools
from resources.lib.modules import database

monitor = xbmc.Monitor()

class CacheAssit:

    def __init__(self, url):
        url = json.loads(tools.unquote(url))
        args = url['args']
        torrent_list = url['torrent_list']

        # HARDCODED FOR NOW
        if 'showInfo' in args:
            self.title = args['showInfo']['info']['originaltitle']
        else:
            self.title = args['title']

        cache_location = int(tools.getSetting('general.cachelocation'))

        threads = []
        self.notified = False

        if cache_location == 0 and tools.getSetting('premiumize.enabled') == 'true':
            threads.append(threading.Thread(target=self.premiumize_downloader, args=(torrent_list[0],)))

        if cache_location == 1 and tools.getSetting('realdebrid.enabled') == 'true':
            threads.append(threading.Thread(target=self.real_debrid_downloader(torrent_list[0], args)))
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
            tools.showDialog.notification(tools.addonName, 'Cache Assist is attempting to build a torrent source')
            database.add_assist_torrent(transfer_id, 'premiumize', 'queued',
                                        torrent_object['release_title'], str(current_percent))
        except:
            tools.log('Failed to start premiumize debrid transfer', 'error')
            return
        tools.log('TRANSFER PREMIUMIZE')
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
                    break
                if current_percent == transfer_status['progress']:
                    if (timestamp + 1800) < time.time():
                        database.add_assist_torrent(transfer_id, 'premiumize', 'failed',
                                                    torrent_object['release_title'],
                                                 str(current_percent))
                        # End the transfer if progress has stalled for over 30 minutes
                        debrid.delete_transfer(transfer_id)
                        tools.log('Could not create cache for magnet- %s' % torrent_object['magnet'], 'info')
                        break
                else:
                    timestamp = time.time()
                    database.add_assist_torrent(transfer_id, 'premiumize', transfer_status['status'],
                                                torrent_object['release_title'],
                                             str(current_percent))

            except:
                database.add_assist_torrent(transfer_id, 'premiumize', 'failed', torrent_object['release_title'],
                                         str(current_percent))
                debrid.delete_transfer(transfer_id)

                break

        return

    def real_debrid_downloader(self, torrent_object, args):
        from resources.lib.common import source_utils
        tools.log('REAL DEBRID CACHE ASSIST STARTING')
        tools.showDialog.notification(tools.addonName, 'Cache Assist is attempting to build a torrent source')
        current_percent = 0
        episodeStrings, seasonStrings = source_utils.torrentCacheStrings(args)
        debrid = real_debrid.RealDebrid()
        magnet = debrid.addMagnet(torrent_object['magnet'])
        info = debrid.torrentInfo(magnet['id'])
        torrent_id = info['id']
        file_key = None
        database.add_assist_torrent(torrent_id, 'real_debrid', 'queued', torrent_object['release_title'],
                                    str(current_percent))
        for file in info['files']:
            filename = file['path']
            key = file['id']
            if any(source_utils.cleanTitle(episodeString) in source_utils.cleanTitle(filename) for episodeString in
                   episodeStrings):
                if any(filename.lower().endswith(extension) for extension in
                       source_utils.COMMON_VIDEO_EXTENSIONS):
                    file_key = key
                    break


        debrid.torrentSelect(torrent_id, file_key)
        downloading_status = ['queued', 'downloading']

        while not monitor.abortRequested():
            if monitor.waitForAbort(120):
                break
            try:
                info = debrid.torrentInfo(torrent_id)
                current_percent = info['progress']
                if info['status'] == 'downloaded':
                    tools.showDialog.notification(tools.addonName + ': %s' % self.title,
                                                  'New cached sources have been created for %s' % self.title,
                                                  time=5000)
                    database.add_assist_torrent(torrent_id, 'real_debrid', 'finished', torrent_object['release_title'],
                                                str(current_percent))
                    debrid.deleteTorrent(torrent_id)
                    break
                if info['status'] in downloading_status:
                    database.add_assist_torrent(torrent_id, 'real_debrid', 'downloading',
                                                torrent_object['release_title'],
                                                str(current_percent))
                    continue
                else:
                    database.add_assist_torrent(torrent_id, 'real_debrid', 'failed', torrent_object['release_title'],
                                                str(current_percent))
                    debrid.deleteTorrent(torrent_id)
                    tools.log('Could not create cache for magnet- %s' % torrent_object['magnet'], 'info')
                    break
            except:
                debrid.deleteTorrent(torrent_id)
