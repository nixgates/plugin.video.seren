# -*- coding: utf-8 -*-

import json
import re
import requests
import time
import threading

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.modules import database


class RealDebrid:
    def __init__(self):
        self.ClientID = tools.getSetting('rd.client_id')
        if self.ClientID == '':
            self.ClientID = 'X245A4XAIBGVM'
        self.OauthUrl = 'https://api.real-debrid.com/oauth/v2/'
        self.DeviceCodeUrl = "device/code?%s"
        self.DeviceCredUrl = "device/credentials?%s"
        self.TokenUrl = "token"
        self.token = tools.getSetting('rd.auth')
        self.refresh = tools.getSetting('rd.refresh')
        self.DeviceCode = ''
        self.ClientSecret = tools.getSetting('rd.secret')
        self.OauthTimeout = 0
        self.OauthTimeStep = 0
        self.BaseUrl = "https://api.real-debrid.com/rest/1.0/"
        self.cache_check_results = {}

    def auth_loop(self):
        if tools.progressDialog.iscanceled():
            tools.progressDialog.close()
            return
        time.sleep(self.OauthTimeStep)
        url = "client_id=%s&code=%s" % (self.ClientID, self.DeviceCode)
        url = self.OauthUrl + self.DeviceCredUrl % url
        response = json.loads(requests.get(url).text)
        if 'error' in response:
            return
        else:
            try:
                tools.progressDialog.close()
                tools.setSetting('rd.client_id', response['client_id'])
                tools.setSetting('rd.secret', response['client_secret'])
                self.ClientSecret = response['client_secret']
                self.ClientID = response['client_id']
            except:
                tools.showDialog.ok(tools.addonName, tools.lang(32100))
            return

    def auth(self):
        self.ClientSecret = ''
        self.ClientID = 'X245A4XAIBGVM'
        url = ("client_id=%s&new_credentials=yes" % self.ClientID)
        url = self.OauthUrl + self.DeviceCodeUrl % url
        response = json.loads(requests.get(url).text)
        tools.copy2clip(response['user_code'])
        tools.progressDialog.create(tools.lang(32023))
        tools.progressDialog.update(-1, tools.lang(32024).format(tools.colorString(
            'https://real-debrid.com/device')),
                                    tools.lang(32025).format(tools.colorString(
                                        response['user_code'])),
                                    'This code has been copied to your clipboard')
        self.OauthTimeout = int(response['expires_in'])
        self.OauthTimeStep = int(response['interval'])
        self.DeviceCode = response['device_code']

        while self.ClientSecret == '':
            self.auth_loop()

        self.token_request()

        user_information = self.get_url('user')
        if user_information['type'] != 'premium':
            tools.showDialog.ok(tools.addonName, tools.lang(40156))

    def token_request(self):
        import time
        if self.ClientSecret is '':
            return

        postData = {'client_id': self.ClientID,
                    'client_secret': self.ClientSecret,
                    'code': self.DeviceCode,
                    'grant_type': 'http://oauth.net/grant_type/device/1.0'}

        url = self.OauthUrl + self.TokenUrl
        response = requests.post(url, data=postData).text
        response = json.loads(response)
        tools.setSetting('rd.auth', response['access_token'])
        tools.setSetting('rd.refresh', response['refresh_token'])
        self.token = response['access_token']
        self.refresh = response['refresh_token']
        tools.setSetting('rd.expiry', str(time.time() + int(response['expires_in'])))
        username = self.get_url('user')['username']
        tools.setSetting('rd.username', username)
        tools.showDialog.ok(tools.addonName, 'Real Debrid ' + tools.lang(32026))
        tools.log('Authorised Real Debrid successfully', 'info')

    def refreshToken(self):
        import time
        postData = {'grant_type': 'http://oauth.net/grant_type/device/1.0',
                    'code': self.refresh,
                    'client_secret': self.ClientSecret,
                    'client_id': self.ClientID
                    }
        url = self.OauthUrl + 'token'
        response = requests.post(url, data=postData)
        response = json.loads(response.text)
        if 'access_token' in response:
            self.token = response['access_token']
        else:
            pass
        if 'refresh_token' in response:
            self.refresh = response['refresh_token']
        tools.setSetting('rd.auth', self.token)
        tools.setSetting('rd.refresh', self.refresh)
        tools.setSetting('rd.expiry', str(time.time() + int(response['expires_in'])))
        tools.log('Real Debrid Token Refreshed')
        ###############################################
        # To be FINISHED FINISH ME
        ###############################################

    def post_url(self, url, postData, fail_check=False):
        original_url = url
        url = self.BaseUrl + url
        if self.token == '':
            return None
        if not fail_check:
            if '?' not in url:
                url += "?auth_token=%s" % self.token
            else:
                url += "&auth_token=%s" % self.token

        response = requests.post(url, data=postData, timeout=5).text
        if 'bad_token' in response or 'Bad Request' in response:
            if not fail_check:
                self.refreshToken()
                response = self.post_url(original_url, postData, fail_check=True)
        try:
            return json.loads(response)
        except:
            return response

    def get_url(self, url, fail_check=False):
        original_url = url
        url = self.BaseUrl + url
        if self.token == '':
            tools.log('No Real Debrid Token Found')
            return None
        if not fail_check:
            if '?' not in url:
                url += "?auth_token=%s" % self.token
            else:
                url += "&auth_token=%s" % self.token

        response = requests.get(url, timeout=5).text

        if 'bad_token' in response or 'Bad Request' in response:
            tools.log('Refreshing RD Token')
            if not fail_check:
                self.refreshToken()
                response = self.get_url(original_url, fail_check=True)
        try:
            return json.loads(response)
        except:
            return response

    def checkHash(self, hashList):

        if isinstance(hashList, list):
            cache_result = {}
            hashList = [hashList[x:x+100] for x in range(0, len(hashList), 100)]
            threads = []
            for section in hashList:
                threads.append(threading.Thread(target=self._check_hash_thread, args=(section,)))
            for i in threads:
                i.start()
            for i in threads:
                i.join()
            return self.cache_check_results
        else:
            hashString = "/" + hashList
            return self.get_url("torrents/instantAvailability" + hashString)

    def _check_hash_thread(self, hashes):
        hashString = '/' + '/'.join(hashes)
        response = self.get_url("torrents/instantAvailability" + hashString)
        self.cache_check_results.update(response)

    def addMagnet(self, magnet):
        postData = {'magnet': magnet}
        url = 'torrents/addMagnet'
        response = self.post_url(url, postData)
        return response

    def list_torrents(self):
        url = "torrents"
        response = self.get_url(url)
        return response

    def torrentInfo(self, id):
        url = "torrents/info/%s" % id
        return self.get_url(url)

    def torrentSelect(self, torrentID, fileID):
        url = "torrents/selectFiles/%s" % torrentID
        postData = {'files': fileID}
        return self.post_url(url, postData)

    def resolve_hoster(self, link):
        url = 'unrestrict/link'
        postData = {'link': link}
        response = self.post_url(url, postData)
        try:
            return response['download']
        except:
            return None

    def deleteTorrent(self, id):
        if self.token == '':
            return None
        url = "torrents/delete/%s&auth_token=%s" % (id, self.token)
        requests.delete(self.BaseUrl + url, timeout=5)

    def _single_magnet_resolve(self, torrent):
        try:
            magnet = torrent['magnet']

            hash = torrent['hash']

            hash_check = self.checkHash(hash)
           
            for storage_variant in hash_check[hash]['rd']:
                
                if not self.is_streamable_storage_type(storage_variant):
                    continue
                
                key_list = ','.join(storage_variant.keys())
                
                torrent = self.addMagnet(magnet)
                
                self.torrentSelect(torrent['id'], key_list)
                
                files = self.torrentInfo(torrent['id'])
                selected_files = [i for i in files['files'] if i['selected'] == 1]
                
                if len(selected_files) == 1:
                    stream_link = self.resolve_hoster(files['links'][0])
                else:
                    selected_files = [(idx, i) for idx, i in enumerate(selected_files)]
                    selected_files = sorted(selected_files, key=lambda x: x[1]['bytes'], reverse=True)
                    stream_link = self.resolve_hoster(files['links'][selected_files[0][0]])
                    
                if tools.getSetting('rd.autodelete') == 'true':
                    self.deleteTorrent(torrent['id'])
                
                return stream_link
        except:
            import traceback
            traceback.print_exc()
            return None

    def resolve_magnet(self, magnet, args, torrent, pack_select=False):
        try:
            if torrent['package'] == 'single' or 'showInfo' not in args:
                return self._single_magnet_resolve(torrent)

            hash = torrent['hash']

            hashCheck = self.checkHash(hash)
            cached_torrent = self.addMagnet(torrent['magnet'])

            for storage_variant in hashCheck[hash]['rd']:

                valid_storage = self.is_streamable_storage_type(storage_variant)

                if not valid_storage:
                    continue

                file_check = source_utils.get_best_match('filename', storage_variant.values(), args)

                if not file_check:
                    continue

                key_list = storage_variant.keys()

                if len(key_list) == 0:
                    self.deleteTorrent(cached_torrent['id'])
                    return None

                key_list = ','.join(key_list)

                self.torrentSelect(cached_torrent['id'], key_list)

                link = self.torrentInfo(cached_torrent['id'])

                selected_files = [(idx, i) for idx, i in enumerate([i for i in link['files'] if i['selected'] == 1])]

                best_match = source_utils.get_best_match('path', [i[1] for i in selected_files], args)

                if not best_match:
                    continue

                file_index = [i[0] for i in selected_files if i[1]['path'] == best_match['path']][0]

                link = link['links'][file_index]
                link = self.resolve_hoster(link)

                if link.endswith('rar'):
                    link = None

                if tools.getSetting('rd.autodelete') == 'true':
                    self.deleteTorrent(cached_torrent['id'])

                return link
        except:
            import traceback
            traceback.print_exc()
            self.deleteTorrent(cached_torrent['id'])
            return None

    def is_streamable_storage_type(self, storage_variant):
        """
        Confirms that all files within the storage variant are video files
        This ensure the pack from RD is instantly streamable and does not require a download
        :param storage_variant:
        :return: BOOL
        """
        return False if len([i for i in storage_variant.values()
                            if not source_utils.is_file_ext_valid(i['filename'])]) > 0 else True

    def getRelevantHosters(self):
        try:
            host_list = self.get_url('hosts/status')
            valid_hosts = []

            for domain, status in host_list.items():
                if status['supported'] == 1 and status['status'] == 'up':
                    valid_hosts.append(domain)
            return valid_hosts
        except:
            import traceback
            traceback.print_exc()

    def get_hosters(self, hosters):
        host_list = database.get(self.getRelevantHosters, 1)
        if host_list is None:
            host_list = self.getRelevantHosters()
        if host_list is not None:
            hosters['premium']['real_debrid'] = [(i, i.split('.')[0]) for i in host_list]
        else:
            hosters['premium']['real_debrid'] = []