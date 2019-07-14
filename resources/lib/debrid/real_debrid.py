# -*- coding: utf-8 -*-

import json
import re
import requests
import time
import threading

from resources.lib.common import source_utils
from resources.lib.common import tools


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
                user_information = self.get_url('user')
                tools.log(user_information)
                if user_information['type'] != 'premium':
                    tools.showDialog.ok(tools.addonName, tools.lang(40156))
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
        tools.progressDialog.update(-1, tools.lang(32024) + ' %s' % tools.colorString(
            'https://real-debrid.com/device'),
                                    tools.lang(32025) + ' %s' % tools.colorString(
                                        response['user_code']),
                                    'This code has been copied to your clipboard')
        self.OauthTimeout = int(response['expires_in'])
        self.OauthTimeStep = int(response['interval'])
        self.DeviceCode = response['device_code']
        while self.ClientSecret == '':
            self.auth_loop()
        self.token_request()

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

        response = requests.post(url, data=postData, timeout=10).text
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

        response = requests.get(url, timeout=10).text

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

    def unrestrict_link(self, link):
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
        response = requests.delete(self.BaseUrl + url)

    def singleMagnetToLink(self, magnet):
        try:
            hash = str(re.findall(r'btih:(.*?)&', magnet)[0].lower())
            hashCheck = self.checkHash(hash)
            fileIDString = ''
            if hash in hashCheck:
                if 'rd' in hashCheck[hash]:
                    for key in hashCheck[hash]['rd'][0]:
                        fileIDString += ',' + key

            torrent = self.addMagnet(magnet)
            try:
                self.torrentSelect(torrent['id'], fileIDString[1:])
                link = self.torrentInfo(torrent['id'])
                selected_files = [i for i in link['files'] if i['selected'] == 1]
                if len(selected_files) == 1:
                    link_index = 0
                else:
                    link_index = 0
                    index_bytes = 0
                    for idx, file in enumerate(selected_files):
                        if file['bytes'] > index_bytes:
                            link_index = idx
                link = self.unrestrict_link(link['links'][link_index])
                if tools.getSetting('rd.autodelete') == 'true':
                    self.deleteTorrent(torrent['id'])
            except:
                import traceback
                traceback.print_exc()
                self.deleteTorrent(torrent['id'])
                return None

            return link
        except:
            import traceback
            traceback.print_exc()
            return None

    def magnetToLink(self, torrent, args):
        try:
            if torrent['package'] == 'single' or 'showInfo' not in args:
                return self.singleMagnetToLink(torrent['magnet'])

            hash = str(re.findall(r'btih:(.*?)&', torrent['magnet'])[0].lower())
            hashCheck = self.checkHash(hash)
            torrent = self.addMagnet(torrent['magnet'])
            episodeStrings, seasonStrings = source_utils.torrentCacheStrings(args)
            key_list = []

            for storage_variant in hashCheck[hash]['rd']:
                file_inside = False
                key_list = []
                bad_storage = False

                for key, value in storage_variant.items():
                    filename = storage_variant[key]['filename']
                    if not any(filename.endswith(extension) for extension in
                               source_utils.COMMON_VIDEO_EXTENSIONS):
                        bad_storage = True
                        break
                    else:
                        key_list.append(key)
                        if any(episodeString in source_utils.cleanTitle(filename) for
                               episodeString in episodeStrings):
                            file_inside = True

                if not file_inside or bad_storage:
                    continue
                else:
                    break

            if len(key_list) == 0:
                self.deleteTorrent(torrent['id'])
                return None

            key_list = ','.join(key_list)

            self.torrentSelect(torrent['id'], key_list)

            link = self.torrentInfo(torrent['id'])

            file_index = None


            for idx, i in enumerate([i for i in link['files'] if i['selected'] == 1]):
                if any(source_utils.cleanTitle(episodeString) in source_utils.cleanTitle(i['path'].split('/')[-1]) for
                       episodeString in episodeStrings):
                        file_index = idx
                        break

            if file_index is None:
                self.deleteTorrent(torrent['id'])
                return None

            link = link['links'][file_index]
            link = self.unrestrict_link(link)

            if link.endswith('rar'):
                link = None

            if tools.getSetting('rd.autodelete') == 'true':
                self.deleteTorrent(torrent['id'])
            return link
        except:
            import traceback
            traceback.print_exc()
            self.deleteTorrent(torrent['id'])
            return None

    def getRelevantHosters(self):
        try:
            host_list = self.get_url('hosts/status')
            valid_hosts = []
            try:
                for domain, status in host_list.iteritems():
                    if status['supported'] == 1 and status['status'] == 'up':
                        valid_hosts.append(domain)
            except:
                # Python 3 support
                for domain, status in host_list.items():
                    if status['supported'] == 1 and status['status'] == 'up':
                        valid_hosts.append(domain)
            return valid_hosts
        except:
            import traceback
            traceback.print_exc()