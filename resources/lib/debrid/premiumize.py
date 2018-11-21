import requests, json
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

def get_url(url):
    url = BaseUrl + "apikey=" + CustomerPin + url
    req = requests.get(url).text
    return json.loads(req)

def post_url(url, data):
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
        database.add_premiumize_transfer(id)
        transfers = self.list_transfers()
        folder_id = None
        try:
            for i in transfers['transfers']:
                if i['id'] == id:
                    folder_id = i['folder_id']

            if folder_id is None: raise Exception

            folder_details = self.list_folder(folder_id)
            selectedFile = folder_details[0]

            for file in folder_details:
                if file['type'] == 'file':
                    if source_utils.filterMovieTitle(file['name'], args['title'], args['year']):
                        if any(file['link'].endswith(ext) for ext in source_utils.COMMON_VIDEO_EXTENSIONS):
                            selectedFile = file

        except:
            self.delete_transfer(id)
            return
        return selectedFile['link']

    def magnetToStream(self, magnet, args, pack_select):

        if 'episodeInfo' not in args:
            return self.movieMagnetToStream(magnet, args)

        episodeStrings, seasonStrings = source_utils.torrentCacheStrings(args)
        showInfo = args['showInfo']['info']
        showTitle = showInfo['tvshowtitle']

        transfer = self.create_transfer(magnet)
        transfer_id = transfer['id']
        database.add_premiumize_transfer(transfer_id)
        transfers = self.list_transfers()
        folder_id = None
        sub_folder_id = None
        try:
            for i in transfers['transfers']:
                if i['id'] == transfer_id:
                    folder_id = i['folder_id']
            if folder_id is None: raise Exception

            folder_details = self.list_folder(folder_id)

            if pack_select is not False and pack_select is not None:
                streamLink = self.user_select(folder_details, transfer_id)
                return streamLink

            streamLink = self.check_episode_string(folder_details, episodeStrings)

            if streamLink is None:

                for item in folder_details:
                    # Check for old Usenet standards
                    if source_utils.cleanTitle(item['name']) == source_utils.cleanTitle(showTitle):
                        folder_details = self.list_folder(item['id'])

                for item in folder_details:
                    if item['type'] != 'folder':
                        continue

                    for seasonStr in seasonStrings:
                        if seasonStr in source_utils.cleanTitle(item['name'].lower().replace('&', ' ')):
                            sub_folder_id = item['id']

                if sub_folder_id is not None:
                    folder_details = self.list_folder(sub_folder_id)
                    if not pack_select == "True":
                        streamLink = self.check_episode_string(folder_details, episodeStrings)
                    else:
                        name_list = [file['name'] for file in folder_details]
                        selection = tools.showDialog.select(tools.addonName + ": Select Episode", name_list)
                        streamLink = folder_details[selection]['link']
                else:
                    pass

        except:
            import traceback
            traceback.print_exc()
            self.delete_transfer(transfer_id)
            database.remove_premiumize_transfer(transfer_id)
            return

        return streamLink

    def check_episode_string(self, folder_details, episodeStrings):
        for i in folder_details:
            for epstring in episodeStrings:
                if epstring in source_utils.cleanTitle(i['name'].lower().replace('&', ' ')):
                    if any(i['link'].endswith(ext) for ext in source_utils.COMMON_VIDEO_EXTENSIONS):
                        return i['link']
        return None

    def user_select(self, folder_details, transfer_id):
        display_list = [tools.colorString(i['name']) for i in folder_details]
        selection = tools.showDialog.select(tools.addonName + ": Torrent File Picker", display_list)
        if selection == -1:
            return None
        selection = folder_details[selection]
        if selection['type'] != 'folder':
            streamlink = selection['link']
        else:
            folder_details = self.list_folder(selection['id'])
            streamlink = self.user_select(folder_details, transfer_id)

        return streamlink
