# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import time

import requests
import xbmc
import xbmcgui
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.database.premiumizeTransfers import PremiumizeTransfers
from resources.lib.modules.globals import g

PM_TOKEN_KEY = "premiumize.token"


class Premiumize:
    """
    Wrapper to handle calls to Premiumize API
    """
    client_id = "288300453"
    client_secret = "2jw9suzfdue2t7eq46"
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    def __init__(self):
        self.headers = {
            "Authorization": "Bearer {}".format(g.get_setting(PM_TOKEN_KEY))
        }
        self.premiumize_transfers = PremiumizeTransfers()
        self.progress_dialog = xbmcgui.DialogProgress()

    @staticmethod
    def _error_handler(request):
        if request.json().get("status") == "error":
            message = "Premiumize API error: {}".format(request.json().get("message"))
            g.notification(g.ADDON_NAME, message)
            g.log(message, "error")
            g.log(request.request.headers)
        return request

    def auth(self):
        """
        Initiates and performs OAuth process
        :return: None
        :rtype: None
        """
        data = {"client_id": self.client_id, "response_type": "device_code"}
        token = self.session.post("https://www.premiumize.me/token", data=data).json()
        expiry = int(token["expires_in"])
        token_ttl = int(token["expires_in"])
        interval = int(token["interval"])
        poll_again = True
        success = False
        tools.copy2clip(token["user_code"])
        self.progress_dialog.create(
            g.ADDON_NAME + ": " + g.get_language_string(30382),
            tools.create_multiline_message(
                line1=g.get_language_string(30019).format(
                    g.color_string(token["verification_uri"])
                ),
                line2=g.get_language_string(30020).format(
                    g.color_string(token["user_code"])
                ),
                line3=g.get_language_string(30048),
            ),
        )
        self.progress_dialog.update(100)

        while poll_again and not token_ttl <= 0 and not self.progress_dialog.iscanceled():
            xbmc.sleep(1000)
            if token_ttl % interval == 0:
                poll_again, success = self._poll_token(token["device_code"])
            progress_percent = int(float((token_ttl * 100) / expiry))
            self.progress_dialog.update(progress_percent)
            token_ttl -= 1

        self.progress_dialog.close()

        if success:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30021))

    def _poll_token(self, device_code):
        data = {
            "client_id": self.client_id,
            "code": device_code,
            "grant_type": "device_code",
        }
        token = self.session.post("https://www.premiumize.me/token", data=data).json()
        if "error" in token:
            if token["error"] == "access_denied":
                return False, False
            return True, False

        g.set_setting(PM_TOKEN_KEY, token["access_token"])
        self.headers["Authorization"] = "Bearer {}".format(token["access_token"])

        account_info = self.account_info()
        g.set_setting("premiumize.username", account_info["customer_id"])

        return False, True

    def get_url(self, url):
        """
        Perform a GET request to the Premiumize API
        :param url: URI to perform request again
        :type url: str
        :return: JSON response
        :rtype: dict
        """
        if self.headers["Authorization"] == "Bearer ":
            g.log("User is not authorised to make PM requests", "warning")
            return None
        url = "https://www.premiumize.me/api{}".format(url)
        req = self.session.get(url, timeout=10, headers=self.headers)
        req = self._error_handler(req)
        return req.json()

    def post_url(self, url, data):
        """
        Perform a POST request to the Premiumize API
        :param url: URI to perform request again
        :type url: str
        :param data: POST data to send with request
        :type data: dict
        :return: JSON response
        :rtype: dict
        """
        if self.headers["Authorization"] == "Bearer ":
            g.log("User is not authorised to make PM requests", "warning")
            return None
        url = "https://www.premiumize.me/api{}".format(url)
        req = self.session.post(url, headers=self.headers, data=data, timeout=10)
        req = self._error_handler(req)
        return req.json()

    def account_info(self):
        """
        Request account info from the api
        :return: JSON account info
        :rtype: dict
        """
        url = "/account/info"
        response = self.get_url(url)
        return response

    def list_folder(self, folder_id):
        """
        Fetches listing of folder from api
        :param folder_id: ID of the folder to list
        :type folder_id: str
        :return: Folder list
        :rtype: list
        """
        url = "/folder/list"
        post_data = {"id": folder_id}
        response = self.post_url(url, post_data)
        return response["content"]

    def list_folder_all(self):
        """
        List all files
        :return: List of files
        :rtype: list
        """
        url = "/item/listall"
        response = self.get_url(url)
        return response["files"]

    def hash_check(self, hash_list):
        """
        Checks hash list against Premiumize cache
        :param hash_list: List of hashes to check
        :type hash_list: list
        :return: List of responses
        :rtype: list
        """
        url = "/cache/check"
        post_data = {"items[]": hash_list}
        response = self.post_url(url, post_data)
        return response

    def item_details(self, item_id):
        """
        Fetches details on a item
        :param item_id: ID of the item
        :type item_id: str
        :return: Item Details
        :rtype: dict
        """
        url = "/item/details"
        post_data = {"id": item_id}
        return self.post_url(url, post_data)

    def create_transfer(self, src, folder_id="0"):
        """
        Initiates a transfer at remote host
        :param src: http(s) links to supported container files, links to any supported website and magnet links.
        :type src: str
        :param folder_id: ID of folder to store new item at, defaults to 0
        :type folder_id: str
        :return: Results of request
        :rtype: dict
        """
        post_data = {"src": src, "folder_id": folder_id}
        url = "/transfer/create"
        return self.post_url(url, post_data)

    def direct_download(self, src):
        """
        Fetches download information for requested source
        :param src: src can be: http(s) links to cached container files, magnets and links to any supported websites.
        :type src: str
        :return: Download details
        :rtype: dict
        """
        post_data = {"src": src}
        url = "/transfer/directdl"
        return self.post_url(url, post_data)

    def list_transfers(self):
        """
        Fetches a list of all current transfers on users account
        :return: List of all transfers
        :rtype: list
        """
        url = "/transfer/list"
        post_data = {}
        return self.post_url(url, post_data)

    def delete_transfer(self, id):
        """
        Deletes a transfer from the users transfer list
        :param id: ID of the transfer
        :type id: str
        :return: Results of operation
        :rtype: dict
        """
        url = "/transfer/delete"
        post_data = {"id": id}
        return self.post_url(url, post_data)

    def get_used_space(self):
        """
        Fetches the currently used space for the users account
        :return: Current space used in MB
        :rtype: int
        """
        info = self.account_info()
        if not info:
            g.log("Failed to get used space for Premiumize account", "error")
            return 0
        used_space = int(((info["space_used"] / 1024) / 1024) / 1024)
        return used_space

    def hoster_cache_check(self, source_list):
        """
        Checks to see if a URL is cached
        :param source_list: list of items to check against
        :type source_list: list
        :return: List of all results
        :rtype: list
        """
        post_data = {"items[]": source_list}
        return self.post_url("/cache/check", data=post_data)

    @use_cache(1)
    def update_relevant_hosters(self):
        """
        Cached request to fetch all relevant available hoster domains currently supported
        :return: Information on available services
        :rtype: dict
        """
        return self.post_url("/services/list", {})

    def resolve_hoster(self, source):
        """
        Resolves a hoster link into a streamable link through services servers
        :param source: URL to item to resolve
        :type source: str
        :return: Resolved url
        :rtype: str
        """
        direct_link = self.direct_download(source)
        if direct_link["status"] == "success":
            stream_link = direct_link["location"]
        else:
            stream_link = None

        return stream_link

    def folder_streams(self, folder_id):
        """
        Lists all available streams in a givn folder
        :param folder_id: ID of folder to list
        :type folder_id: str
        :return: List of a file items
        :rtype: list
        """
        files = self.list_folder(folder_id)
        return_files = []
        files = [i for i in files if i["type"] == "file_path"]
        for i in files:
            if i["transcode_status"] == "finished":
                return_files.append(
                    {"name": i["name"], "link": i["stream_link"], "type": "file_path"}
                )
            else:
                for extension in g.common_video_extensions:
                    if i["link"].endswith(extension):
                        return_files.append(
                            {"name": i["name"], "link": i["link"], "type": "file_path"}
                        )
                        break
        return return_files

    def internal_folders(self, folder_id):
        """
        Lists all internal folders in a given folder
        :param folder_id: ID of folder to list
        :type folder_id: str
        :return: List of internal folders
        :rtype: list
        """
        folders = self.list_folder(folder_id)
        return_folders = []
        for i in folders:
            if i["type"] == "folder":
                return_folders.append(
                    {"name": i["name"], "id": i["id"], "type": "folder"}
                )
        return return_folders

    def get_hosters(self, hosters):
        """
        Accepts a specificly formatted dict and updates it with available premium hosters
        :param hosters: Formatted hoster dict
        :type hosters: dict
        :return: Updated Dict
        :rtype: dict
        """
        host_list = self.update_relevant_hosters()
        if host_list is not None:
            hosters["premium"]["premiumize"] = [
                (i, i.split(".")[0]) for i in host_list.get("directdl", [])
            ]
        else:
            hosters["premium"]["premiumize"] = []

    def is_service_enabled(self):
        """
        Check to confirm api is enabled in Seren
        :return:
        :rtype:
        """
        return (
            g.get_bool_setting("premiumize.enabled")
            and g.get_setting(PM_TOKEN_KEY, None) is not None
        )

    def is_account_premium(self):
        """
        Confirm accounts Premium status
        :return: True if premium else false
        :rtype: bool
        """
        return self.account_info()["premium_until"] > time.time()
