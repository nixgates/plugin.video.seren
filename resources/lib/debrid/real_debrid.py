# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import threading
import time

import requests
import xbmc
import xbmcgui
from requests.adapters import HTTPAdapter
from urllib3 import Retry

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database.cache import use_cache
from resources.lib.modules.exceptions import UnexpectedResponse
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g

RD_AUTH_KEY = "rd.auth"
RD_REFRESH_KEY = "rd.refresh"
RD_EXPIRY_KEY = "rd.expiry"
RD_SECRET_KEY = "rd.secret"
RD_CLIENT_ID_KEY = "rd.client_id"
RD_USERNAME_KEY = "rd.username"


class RealDebrid:
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    _threading_lock = threading.Lock()

    def __init__(self):
        self.client_id = g.get_setting("rd.client_id")
        if not self.client_id:
            self.client_id = "X245A4XAIBGVM"
        self.oauth_url = "https://api.real-debrid.com/oauth/v2/"
        self.device_code_url = "device/code?{}"
        self.device_credentials_url = "device/credentials?{}"
        self.token_url = "token"
        self.token = g.get_setting(RD_AUTH_KEY)
        self.session.headers.update({"Authorization": "Bearer {}".format(self.token)})
        self.refresh = g.get_setting(RD_REFRESH_KEY)
        self.expiry = g.get_float_setting(RD_EXPIRY_KEY)
        self.device_code = ""
        self.client_secret = g.get_setting(RD_SECRET_KEY)
        self.oauth_timeout = 0
        self.oauth_time_step = 0
        self.base_url = "https://api.real-debrid.com/rest/1.0/"
        self.cache_check_results = {}
        self.progress_dialog = xbmcgui.DialogProgress()

    def _auth_loop(self):
        url = "client_id={}&code={}".format(self.client_id, self.device_code)
        url = self.oauth_url + self.device_credentials_url.format(url)
        response = self.session.get(url).json()
        if "error" not in response:
            try:
                self.progress_dialog.close()
                g.set_setting(RD_CLIENT_ID_KEY, response["client_id"])
                g.set_setting(RD_SECRET_KEY, response["client_secret"])
                self.client_secret = response["client_secret"]
                self.client_id = response["client_id"]
                return True
            except:
                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30068))
                raise
        return False

    def auth(self):
        self.client_secret = ""
        self.client_id = "X245A4XAIBGVM"
        url = "client_id={}&new_credentials=yes".format(self.client_id)
        url = self.oauth_url + self.device_code_url.format(url)
        response = self.session.get(url).json()
        tools.copy2clip(response["user_code"])
        self.progress_dialog.create(
            g.ADDON_NAME + ": " + g.get_language_string(30018),
            tools.create_multiline_message(
                line1=g.get_language_string(30019).format(
                    g.color_string("https://real-debrid.com/device")
                ),
                line2=g.get_language_string(30020).format(
                    g.color_string(response["user_code"])
                ),
                line3=g.get_language_string(30048),
            ),
        )
        self.oauth_timeout = int(response["expires_in"])
        token_ttl = int(response["expires_in"])
        self.oauth_time_step = int(response["interval"])
        self.device_code = response["device_code"]
        success = False
        self.progress_dialog.update(100)
        while (
            not self.client_secret
            and not token_ttl <= 0
            and not self.progress_dialog.iscanceled()
        ):
            xbmc.sleep(1000)
            if token_ttl % self.oauth_time_step == 0:
                success = self._auth_loop()
            progress_percent = int(float((token_ttl * 100) / self.oauth_timeout))
            self.progress_dialog.update(progress_percent)
            token_ttl -= 1

        self.progress_dialog.close()

        if success:
            self.token_request()

            user_information = self.get_url("user")
            if user_information["type"] != "premium":
                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30216))

    def token_request(self):
        import time

        if not self.client_secret:
            return

        url = self.oauth_url + self.token_url
        response = self.session.post(
            url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": self.device_code,
                "grant_type": "http://oauth.net/grant_type/device/1.0",
            },
        ).json()
        g.set_setting(RD_AUTH_KEY, response["access_token"])
        g.set_setting(RD_REFRESH_KEY, response["refresh_token"])
        self.token = response["access_token"]
        self.session.headers.update({"Authorization": "Bearer {}".format(self.token)})
        self.refresh = response["refresh_token"]
        g.set_setting(RD_EXPIRY_KEY, str(time.time() + int(response["expires_in"])))
        username = self.get_url("user").get("username")
        g.set_setting(RD_USERNAME_KEY, username)
        xbmcgui.Dialog().ok(g.ADDON_NAME, "Real Debrid " + g.get_language_string(30021))
        g.log("Authorised Real Debrid successfully", "info")

    @staticmethod
    def _handle_error(response):
        g.log("Real Debrid API return a {} response".format(response.status_code))
        g.log(response.text)
        g.log(response.request.url)

    def _is_response_ok(self, response):
        try:
            if "error" in response.json():
                self._handle_error(response)
                return False
            return True
        except JSONDecodeError:
            return True

    def try_refresh_token(self):
        if not self.token or float(time.time()) < (self.expiry - (15 * 60)):
            return

        with GlobalLock(
            self.__class__.__name__, self._threading_lock, True, self.refresh
        ):
            url = self.oauth_url + "token"
            response = self.session.post(
                url,
                data={
                    "grant_type": "http://oauth.net/grant_type/device/1.0",
                    "code": self.refresh,
                    "client_secret": self.client_secret,
                    "client_id": self.client_id,
                },
            )
            if not self._is_response_ok(response):
                response = response.json()
                g.notification(
                    g.ADDON_NAME, "Failed to refresh RD token, please manually re-auth"
                )
                g.log("RD Refresh error: {}".format(response["error"]))
                g.log(
                    "Invalid response from Real Debrid - {}".format(response), "error"
                )
                return False
            response = response.json()
            if "access_token" in response:
                self.token = response["access_token"]
            if "refresh_token" in response:
                self.refresh = response["refresh_token"]
            g.set_setting(RD_AUTH_KEY, self.token)
            g.set_setting(RD_REFRESH_KEY, self.refresh)
            g.set_setting(RD_EXPIRY_KEY, str(time.time() + int(response["expires_in"])))
            g.log("Real Debrid Token Refreshed")
            return True
            ###############################################
            # To be FINISHED FINISH ME
            ###############################################

    def post_url(self, url, post_data, fail_check=False):
        original_url = url
        url = self.base_url + url
        if not self.token:
            return None

        response = self.session.post(url, data=post_data, timeout=5)
        if not self._is_response_ok(response) and not fail_check:
            self.try_refresh_token()
            response = self.post_url(original_url, post_data, fail_check=True)
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response

    def get_url(self, url, fail_check=False):
        original_url = url
        url = self.base_url + url
        if not self.token:
            g.log("No Real Debrid Token Found")
            return None

        response = self.session.get(url, timeout=5)

        if not self._is_response_ok(response) and not fail_check:
            self.try_refresh_token()
            response = self.get_url(original_url, fail_check=True)
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response

    def check_hash(self, hash_list):
        if isinstance(hash_list, list):
            hash_list = [hash_list[x : x + 100] for x in range(0, len(hash_list), 100)]
            thread = ThreadPool()
            for section in hash_list:
                thread.put(self._check_hash_thread, sorted(section))
            thread.wait_completion()
            return self.cache_check_results
        else:
            hash_string = "/" + hash_list
            return self.get_url("torrents/instantAvailability" + hash_string)

    def _check_hash_thread(self, hashes):
        hash_string = "/" + "/".join(hashes)
        response = self.get_url("torrents/instantAvailability" + hash_string)
        self.cache_check_results.update(response)

    def add_magnet(self, magnet):
        post_data = {"magnet": magnet}
        url = "torrents/addMagnet"
        response = self.post_url(url, post_data)
        return response

    def list_torrents(self):
        url = "torrents"
        response = self.get_url(url)
        return response

    def torrent_info(self, id):
        url = "torrents/info/{}".format(id)
        return self.get_url(url)

    def torrent_select(self, torrent_id, file_id):
        url = "torrents/selectFiles/{}".format(torrent_id)
        post_data = {"files": file_id}
        return self.post_url(url, post_data)

    def resolve_hoster(self, link):
        url = "unrestrict/link"
        post_data = {"link": link}
        response = self.post_url(url, post_data)
        try:
            return response["download"]
        except KeyError:
            raise UnexpectedResponse(response)

    def delete_torrent(self, id):
        if not self.token:
            return None
        self.session.delete(self.base_url + "torrents/delete/{}".format(id), timeout=5)

    @staticmethod
    def is_streamable_storage_type(storage_variant):
        """
        Confirms that all files within the storage variant are video files
        This ensure the pack from RD is instantly streamable and does not require a download
        :param storage_variant:
        :return: BOOL
        """
        return (
            False
            if len(
                [
                    i
                    for i in storage_variant.values()
                    if not source_utils.is_file_ext_valid(i["filename"])
                ]
            )
            > 0
            else True
        )

    @use_cache(1)
    def get_relevant_hosters(self):
        host_list = self.get_url("hosts/status")
        if "error" in host_list:
            return []
        valid_hosts = []
        for domain, status in host_list.items():
            if status["supported"] == 1 and status["status"] == "up":
                valid_hosts.append(domain)
        return valid_hosts

    def get_hosters(self, hosters):
        host_list = self.get_relevant_hosters()
        if host_list is None:
            host_list = self.get_relevant_hosters()
        if host_list is not None:
            hosters["premium"]["real_debrid"] = [
                (i, i.split(".")[0]) for i in host_list
            ]
        else:
            hosters["premium"]["real_debrid"] = []

    @staticmethod
    def is_service_enabled():
        return g.get_bool_setting("realdebrid.enabled") and g.get_setting(RD_AUTH_KEY)

    def is_account_premium(self):
        return self.get_url("user").get("type", "free") != "free"
