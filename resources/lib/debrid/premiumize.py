try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

import time
from functools import cached_property

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.database.premiumizeTransfers import PremiumizeTransfers
from resources.lib.modules.globals import g

PM_TOKEN_KEY = "premiumize.token"


class Premiumize:
    """
    Wrapper to handle calls to Premiumize API
    """

    client_id = "662875953"
    client_secret = "xmg33m74n6t6x8phun"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {g.get_setting(PM_TOKEN_KEY)}",
        }
        self.premiumize_transfers = PremiumizeTransfers()

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    @staticmethod
    def _error_handler(request):
        message = None
        try:
            request_json = request.json()
            message = request_json.get("message") if request_json.get("status") == "error" else None
        except JSONDecodeError as jde:
            message = jde

        if message is not None:
            g.notification(g.ADDON_NAME, f"Premiumize API error: {message}")
            g.log(f"Premiumize API error: {message}", "error")

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
        try:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(
                f"{g.ADDON_NAME}: {g.get_language_string(30349)}",
                tools.create_multiline_message(
                    line1=g.get_language_string(30018).format(g.color_string(token["verification_uri"])),
                    line2=g.get_language_string(30019).format(g.color_string(token["user_code"])),
                    line3=g.get_language_string(30047),
                ),
            )
            progress_dialog.update(100)

            while poll_again and token_ttl > 0 and not progress_dialog.iscanceled():
                xbmc.sleep(1000)
                if token_ttl % interval == 0:
                    poll_again, success = self._poll_token(token["device_code"])
                progress_percent = int(float((token_ttl * 100) / expiry))
                progress_dialog.update(progress_percent)
                token_ttl -= 1

            progress_dialog.close()
        finally:
            del progress_dialog

        if success:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30020))

    def _poll_token(self, device_code):
        data = {
            "client_id": self.client_id,
            "code": device_code,
            "grant_type": "device_code",
        }
        token = self.session.post("https://www.premiumize.me/token", data=data).json()
        if "error" in token:
            return (False, False) if token["error"] == "access_denied" else (True, False)
        g.set_setting(PM_TOKEN_KEY, token["access_token"])
        self.headers["Authorization"] = f"Bearer {token['access_token']}"

        account_info = self.account_info()
        g.set_setting("premiumize.username", account_info["customer_id"])
        g.set_setting("premiumize.premiumstatus", self.get_account_status().title())

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
        url = f"https://www.premiumize.me/api{url}"
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
        url = f"https://www.premiumize.me/api{url}"
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
        return self.get_url(url)

    def list_folder(self, folder_id):
        """
        Fetches listing of folder from api
        :param folder_id: ID of the folder to list
        :type folder_id: str
        :return: Folder list
        :rtype: list
        """
        url = "/folder/list"
        post_data = {"id": folder_id} if folder_id else None
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
        files = response.get("files")
        return files if isinstance(files, list) else []

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
        return self.post_url(url, post_data)

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
        response = self.post_url(url, post_data)
        for transfer in response.get("transfers", []):
            if transfer.get("progress") is None:
                transfer["progress"] = 1.0 if transfer.get("status") == "finished" else 0.0

        return response

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
        :return: Current space used in GB
        :rtype: float
        """
        info = self.account_info()
        if not info:
            g.log("Failed to get used space for Premiumize account", "error")
            return 0.0
        return info["space_used"] * 1000.0

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
        return direct_link["location"] if direct_link["status"] == "success" else None

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
                return_files.append({"name": i["name"], "link": i["stream_link"], "type": "file_path"})
            elif i["link"].endswith(g.common_video_extensions):
                return_files.append({"name": i["name"], "link": i["link"], "type": "file_path"})
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
        return [{"name": i["name"], "id": i["id"], "type": "folder"} for i in folders if i["type"] == "folder"]

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
            hosters["premium"]["premiumize"] = [(i, i.split(".")[0]) for i in host_list.get("directdl", [])]
        else:
            hosters["premium"]["premiumize"] = []

    @staticmethod
    def is_service_enabled():
        """
        Check to confirm api is enabled in Seren
        :return:
        :rtype:
        """
        return g.get_bool_setting("premiumize.enabled") and g.get_setting(PM_TOKEN_KEY) is not None

    def get_account_status(self):
        """
        Confirm accounts Premium status
        :return: 'premium' if premium else 'expired'
        :rtype: bool
        """
        account_info = self.account_info()
        if isinstance(account_info, dict):
            premium_until = account_info.get("premium_until")
        if not premium_until or not isinstance(premium_until, (float, int)):
            return "unknown"
        return "premium" if premium_until > time.time() else "expired"
