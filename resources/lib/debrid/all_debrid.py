import time
from functools import cached_property
from functools import wraps
from urllib import parse

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.modules.globals import g

AD_AUTH_KEY = "alldebrid.apikey"
AD_ENABLED_KEY = "alldebrid.enabled"


def alldebrid_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        import requests

        try:
            response = func(*args, **kwarg)
            if response.status_code in [200, 201]:
                return response

            if response.status_code == 429:
                g.log('Alldebrid Throttling Applied, Sleeping for 1 seconds')
                xbmc.sleep(1 * 1000)
                response = func(*args, **kwarg)

            g.log(
                f"AllDebrid returned a {response.status_code} ({AllDebrid.http_codes[response.status_code]}): "
                f"while requesting {response.url}",
                "warning",
            )
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30024).format("AllDebrid"))
            raise

    return wrapper


class AllDebrid:
    base_url = "https://api.alldebrid.com/v4/"

    http_codes = {
        200: "Success",
        400: "Bad Request, The request was unacceptable, often due to missing a required parameter",
        401: "Unauthorized",
        404: "Not Found, Api endpoint doesn't exist",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        524: "Internal Server Error",
    }

    def __init__(self):
        self.agent_identifier = g.ADDON_NAME
        self.apikey = g.get_setting(AD_AUTH_KEY)

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    @alldebrid_guard_response
    def get(self, url, **params):
        if not g.get_bool_setting(AD_ENABLED_KEY):
            return

        params.update({"agent": self.agent_identifier, "apikey": None if params.pop("reauth", None) else self.apikey})

        return self.session.get(parse.urljoin(self.base_url, url), params=params)

    def get_json(self, url, **params):
        return self._extract_data(self.get(url, **params).json())

    @alldebrid_guard_response
    def post(self, url, post_data=None, **params):
        if not g.get_bool_setting(AD_ENABLED_KEY) or not self.apikey:
            return
        params.update({"agent": self.agent_identifier, "apikey": self.apikey})
        return self.session.post(parse.urljoin(self.base_url, url), data=post_data, params=params)

    def post_json(self, url, post_data=None, **params):
        return self._extract_data(self.post(url, post_data, **params).json())

    def _extract_data(self, response):
        return response["data"] if "data" in response else response

    def auth(self):
        resp = self.get_json("pin/get", reauth=True)
        expiry = pin_ttl = int(resp["expires_in"])
        auth_complete = False
        auth_check = None
        tools.copy2clip(resp["pin"])
        try:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(
                f"{g.ADDON_NAME}: {g.get_language_string(30334)}",
                tools.create_multiline_message(
                    line1=g.get_language_string(30018).format(g.color_string(resp["base_url"])),
                    line2=g.get_language_string(30019).format(g.color_string(resp["pin"])),
                    line3=g.get_language_string(30047),
                ),
            )

            # Seems the All Debrid servers need some time do something with the pin before polling
            # Polling to early will cause an invalid pin error
            xbmc.sleep(5 * 1000)
            progress_dialog.update(100)

            while not auth_complete and expiry > 0 and not progress_dialog.iscanceled():
                auth_check = self.get_json("pin/check", check=resp["check"], pin=resp["pin"])
                if auth_check["activated"]:
                    auth_complete = True
                    break
                else:
                    expiry = int(auth_check["expires_in"])
                    progress_percent = 100 - int((float(pin_ttl - expiry) / pin_ttl) * 100)
                    progress_dialog.update(progress_percent)
                    xbmc.sleep(1 * 1000)

            progress_dialog.close()

            if auth_complete and not progress_dialog.iscanceled() and auth_check is not None:
                g.set_setting(AD_AUTH_KEY, auth_check["apikey"])
                self.apikey = auth_check["apikey"]
                self.store_user_info()
        finally:
            del progress_dialog

        if auth_complete:
            xbmcgui.Dialog().ok(g.ADDON_NAME, f"AllDebrid {g.get_language_string(30020)}")
        else:
            return

    def get_user_info(self):
        return self._extract_data(self.get_json("user")).get("user", {})

    def store_user_info(self):
        user_information = self.get_user_info()
        if user_information is not None:
            g.set_setting("alldebrid.username", user_information["username"])
            g.set_setting("alldebrid.premiumstatus", self.get_account_status().title())

    def upload_magnet(self, magnet_hash):
        return self.get_json("magnet/upload", magnet=magnet_hash)

    @use_cache(1)
    def update_relevant_hosters(self):
        return self.get_json("hosts")

    def get_hosters(self, hosters):
        host_list = self.update_relevant_hosters()
        if host_list is not None:
            hosters["premium"]["all_debrid"] = [
                (d, d.split(".")[0])
                for l in host_list["hosts"].values()
                if "status" in l and l["status"]
                for d in l["domains"]
            ]
        else:
            g.log_stacktrace()
            hosters["premium"]["all_debrid"] = []

    def resolve_hoster(self, url):
        resolve = self.get_json("link/unlock", link=url)
        return resolve["link"]

    def magnet_status(self, magnet_id):
        return self.get_json("magnet/status", id=magnet_id) if magnet_id else self.get_json("magnet/status")

    def saved_magnets(self):
        return self.get_json("magnet/status")['magnets']

    def delete_magnet(self, magnet_id):
        return self.get_json("magnet/delete", id=magnet_id)

    def saved_links(self):
        return self.get_json("user/links")

    @staticmethod
    def is_service_enabled():
        return g.get_bool_setting(AD_ENABLED_KEY) and g.get_setting(AD_AUTH_KEY) is not None

    def get_account_status(self):
        user_info = self.get_user_info()
        if not isinstance(user_info, dict):
            return "unknown"

        premium = user_info.get("isPremium")
        premium_until = user_info.get("premiumUntil", 0)
        subscribed = user_info.get("isSubscribed")
        trial = user_info.get("isTrial")

        if premium and premium_until > time.time():
            return "premium"
        elif subscribed:
            return "subscribed"
        elif trial:
            return "trial"
        else:
            return "unknown"
