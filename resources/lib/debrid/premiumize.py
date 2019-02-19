# -*- coding: utf-8 -*-

import json

import requests

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.modules import database

##################################################
# ACCOUNT VARIABLES
##################################################

CustomerPin = tools.getSetting('premiumize.pin')

##################################################
# URL VARIABLES
##################################################

BaseUrl = "https://www.premiumize.me/api"
DirectDownload = '/transfer/directdl'
AccountURL = "/account/info"
ListFolder = "/folder/list"
ItemDetails = "/item/details"
TransferList = "/transfer/list"
TransferCreate = "/transfer/create"
TransferDelete = "/transfer/delete"
CacheCheck = '/cache/check'

##################################################
# REQUESTS WRAPPERS
# Returns JSON on all calls
##################################################
import inspect

def get_url(url):
    if CustomerPin == '':
        return
    url = BaseUrl + "apikey=" + CustomerPin + url
    req = requests.get(url).text
    return json.loads(req)


def post_url(url, data):
    if CustomerPin == '':
        return
    url = BaseUrl + url
    data['apikey'] = CustomerPin
    req = requests.post(url, data=data).text
    return json.loads(req)


class PremiumizeBase():
    ##################################################
    # ACCOUNT FUNCTIONS
    ##################################################

    def account_info(self):
        url = AccountURL
        postData = {}
        response = post_url(url, postData)
        return response

    def list_folder(self, folderID):
        url = ListFolder
        postData = {'id': folderID}
        response = post_url(url, postData)
        return response['content']

    ##################################################
    # CACHE FUNCTIONS
    ##################################################

    def hash_check(self, hashList):
        url = CacheCheck
        postData = {'items[]': hashList}
        response = post_url(url, postData)
        return response

    ##################################################
    # ITEM FUNCTIONS
    ##################################################

    def item_details(self, itemID):
        url = ItemDetails
        postData = {'id': itemID}
        return post_url(url, postData)

    ##################################################
    # TRANSFER FUNCTIONS
    ##################################################

    def create_transfer(self, src, folderID=0):
        postData = {'src': src, 'folder_id': folderID}
        url = TransferCreate
        return post_url(url, postData)

    def direct_download(self, src):
        postData = {'src': src}
        url = DirectDownload
        return post_url(url, postData)

    def list_transfers(self):
        url = TransferList
        postData = {}
        return post_url(url, postData)

    def delete_transfer(self, id):
        url = TransferDelete
        postData = {'id': id}
        return post_url(url, postData)


class PremiumizeFunctions(PremiumizeBase):
    def __init__(self):
        pass

    def hosterCacheCheck(self, source_list):
        post_data = {'items[]': source_list}
        return post_url(CacheCheck, data=post_data)

    def updateRelevantHosters(self):
        hoster_list = database.get(post_url, 1, '/services/list', {})
        return hoster_list

    def resolveHoster(self, source):

        directLink = self.direct_download(source)
        if directLink['status'] == 'success':
            stream_link = directLink['location']
        else:
            stream_link = None

        return stream_link

    def folder_streams(self, folderID):

        files = self.list_folder(folderID)
        returnFiles = []
        for i in files:
            if i['type'] == 'file':
                if i['transcode_status'] == 'finished':
                    returnFiles.append({'name': i['name'], 'link': i['stream_link'], 'type': 'file'})
                else:
                    for extension in source_utils.COMMON_VIDEO_EXTENSIONS:
                        if i['link'].endswith(extension):
                            returnFiles.append({'name': i['name'], 'link': i['link'], 'type': 'file'})
                            break
        return returnFiles

    def internal_folders(self, folderID):
        folders = self.list_folder(folderID)
        returnFolders = []
        for i in folders:
            if i['type'] == 'folder':
                returnFolders.append({'name': i['name'], 'id': i['id'], 'type': 'folder'})
        return returnFolders

    def movieMagnetToStream(self, magnet, args):
        transfer = self.create_transfer(magnet)

        id = transfer['id']

        folder_details = self.direct_download(magnet)['content']
        folder_details = sorted(folder_details, key=lambda i: int(i['size']), reverse=True)
        for file in folder_details:
            if source_utils.filterMovieTitle(file['path'], args['title'], args['year']):
                if any(file['link'].endswith(ext) for ext in source_utils.COMMON_VIDEO_EXTENSIONS):
                    selectedFile = file
                    break

        if tools.getSetting('premiumize.transcoded') == 'true':
            if selectedFile['transcode_status'] == 'finished':
                return selectedFile['stream_link']
            else:
                pass

        return selectedFile['link']

    def magnetToStream(self, magnet, args, pack_select):

        if 'episodeInfo' not in args:
            return self.movieMagnetToStream(magnet, args)

        episodeStrings, seasonStrings = source_utils.torrentCacheStrings(args)
        showInfo = args['showInfo']['info']

        try:

            folder_details = self.direct_download(magnet)['content']

            if pack_select is not False and pack_select is not None:
                streamLink = self.user_select(folder_details)
                return streamLink

            streamLink = self.check_episode_string(folder_details, episodeStrings)

        except:
            import traceback
            traceback.print_exc()
            return

        return streamLink

    def check_episode_string(self, folder_details, episodeStrings):
        for i in folder_details:
            for epstring in episodeStrings:
                if source_utils.cleanTitle(epstring) in \
                        source_utils.cleanTitle(i['path'].replace('&', ' ')):
                    if any(i['link'].endswith(ext) for ext in source_utils.COMMON_VIDEO_EXTENSIONS):
                        if tools.getSetting('premiumize.transcoded') == 'true':
                            if i['transcode_status'] == 'finished':
                                return i['stream_link']
                            else:
                                pass

                        return i['link']
        return None

    def user_select(self, content):
        display_list = []
        for i in content:
            if any(i['path'].endswith(ext) for ext in source_utils.COMMON_VIDEO_EXTENSIONS):
                display_list.append(i)

        selection = tools.showDialog.select(tools.addonName + ": Torrent File Picker",
                                            [i['path'] for i in display_list])
        if selection == -1:
            return None

        selection = content[selection]

        if tools.getSetting('premiumize.transcoded') == 'true':
            if selection['transcode_status'] == 'finished':
                return selection['stream_link']
            else:
                pass

        return selection['link']

