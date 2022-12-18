import base64
import importlib
import json
import os
import sys
from importlib import reload as reload_module

import xbmcvfs

from resources.lib.common import tools
from resources.lib.database.providerCache import ProviderCache
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g
from resources.lib.modules.providers.settings import SettingsManager

# Below is the contents of the providers/__init__.py base64 encoded
# If you update this init file_path you will need to update this base64 as well to ensure it is deployed on the users machine
# If you change the init file_path without updating this it will be overwritten with the old one!!
INIT_BASE64 = "aW1wb3J0IG9zCmZyb20gcmVzb3VyY2VzLmxpYi5tb2R1bGVzLmdsb2JhbHMgaW1wb3J0IGcKZnJvbSByZXNvdXJjZXMubGliLmRhdGFiYXNlLnByb3ZpZGVyQ2FjaGUgaW1wb3J0IFByb3ZpZGVyQ2FjaGUKCgpkZWYgX2lzX3ZhbGlkX3Byb3ZpZGVyX2RpcihuYW1lKToKICAgIGRpcl9wYXRoID0gb3MucGF0aC5qb2luKGRhdGFfcGF0aCwgbmFtZSkKICAgIHRyeToKICAgICAgICBpZiBub3Qgb3MucGF0aC5pc2RpcihkaXJfcGF0aCk6CiAgICAgICAgICAgIHJldHVybiBGYWxzZQogICAgICAgIGlmIG5hbWUuc3RhcnRzd2l0aCgnX18nKToKICAgICAgICAgICAgcmV0dXJuIEZhbHNlCgogICAgICAgIHJldHVybiBUcnVlCgogICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICByZXR1cm4gRmFsc2UKCgpkYXRhX3BhdGggPSBvcy5wYXRoLmpvaW4oZy5BRERPTl9VU0VSREFUQV9QQVRILCAncHJvdmlkZXJzJykKcHJvdmlkZXJfcGFja2FnZXMgPSBbbmFtZSBmb3IgbmFtZSBpbiBvcy5saXN0ZGlyKGRhdGFfcGF0aCkgaWYgX2lzX3ZhbGlkX3Byb3ZpZGVyX2RpcihuYW1lKV0KcHJvdmlkZXJDYWNoZSA9IFByb3ZpZGVyQ2FjaGUoKQoKcHJvdmlkZXJfdHlwZXMgPSAoCiAgICAoJ2hvc3RlcnMnLCAnZ2V0X2hvc3RlcnMnKSwKICAgICgndG9ycmVudCcsICdnZXRfdG9ycmVudCcpLAogICAgKCdhZGFwdGl2ZScsICdnZXRfYWRhcHRpdmUnKSwKICAgICgnZGlyZWN0JywgJ2dldF9kaXJlY3QnKSwKKQoKCmRlZiBfaXNfcHJvdmlkZXJfZW5hYmxlZChwcm92aWRlcl9uYW1lLCBwYWNrYWdlLCBzdGF0dXNlcyk6CiAgICByZXR1cm4gVHJ1ZSBpZiBsZW4oCiAgICAgICAgW2kgZm9yIGkgaW4gc3RhdHVzZXMgaWYgaVsncHJvdmlkZXJfbmFtZSddID09IHByb3ZpZGVyX25hbWUgYW5kIGlbJ3BhY2thZ2UnXSA9PSBwYWNrYWdlXSkgZWxzZSBGYWxzZQoKCmRlZiBfZ2V0X3Byb3ZpZGVycyhsYW5ndWFnZSwgc3RhdHVzPUZhbHNlKToKICAgIHByb3ZpZGVyX3N0b3JlID0gewogICAgICAgICdob3N0ZXJzJzogW10sCiAgICAgICAgJ3RvcnJlbnQnOiBbXSwKICAgICAgICAnYWRhcHRpdmUnOiBbXSwKICAgICAgICAnZGlyZWN0JzogW10sCiAgICB9CiAgICBmb3IgcGFja2FnZSBpbiBwcm92aWRlcl9wYWNrYWdlczoKICAgICAgICBwcm92aWRlcnNfcGF0aCA9ICdwcm92aWRlcnMuJXMuJXMnICUgKHBhY2thZ2UsIGxhbmd1YWdlKQogICAgICAgIHByb3ZpZGVyX2xpc3QgPSBfX2ltcG9ydF9fKHByb3ZpZGVyc19wYXRoLCBmcm9tbGlzdD1bJyddKQogICAgICAgIGZvciBwcm92aWRlcl90eXBlIGluIHByb3ZpZGVyX3R5cGVzOgogICAgICAgICAgICBmb3IgaSBpbiBnZXRhdHRyKHByb3ZpZGVyX2xpc3QsIHByb3ZpZGVyX3R5cGVbMV0sIGxhbWJkYTogW10pKCk6CiAgICAgICAgICAgICAgICBpZiBzdGF0dXMgaXMgbm90IEZhbHNlIGFuZCBub3QgX2lzX3Byb3ZpZGVyX2VuYWJsZWQoaSwgcGFja2FnZSwgc3RhdHVzKToKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgICAgIHByb3ZpZGVyX3N0b3JlW3Byb3ZpZGVyX3R5cGVbMF1dLmFwcGVuZCgoJ3t9Lnt9Jy5mb3JtYXQocHJvdmlkZXJzX3BhdGgsIHByb3ZpZGVyX3R5cGVbMF0pLCBpLCBwYWNrYWdlKSkKCiAgICByZXR1cm4gcHJvdmlkZXJfc3RvcmUKCgpkZWYgZ2V0X3JlbGV2YW50KGxhbmd1YWdlKToKICAgICMgR2V0IGVuYWJsZWQgcHJvdmlkZXJzCiAgICBwcm92aWRlcl9zdGF0dXMgPSBbaSBmb3IgaSBpbiBwcm92aWRlckNhY2hlLmdldF9wcm92aWRlcnMoKSBpZiBpWydjb3VudHJ5J10gPT0gbGFuZ3VhZ2VdCiAgICBwcm92aWRlcl9zdGF0dXMgPSBbaSBmb3IgaSBpbiBwcm92aWRlcl9zdGF0dXMgaWYgaVsnc3RhdHVzJ10gPT0gJ2VuYWJsZWQnXQoKICAgIHJldHVybiBfZ2V0X3Byb3ZpZGVycyhsYW5ndWFnZSwgcHJvdmlkZXJfc3RhdHVzKQoKCmRlZiBnZXRfYWxsKGxhbmd1YWdlKToKICAgIHJldHVybiBfZ2V0X3Byb3ZpZGVycyhsYW5ndWFnZSkK"


class CustomProviders(ProviderCache):
    def __init__(self):
        super().__init__()
        self.deploy_init()
        self.providers_module = self._try_add_providers_path()
        self.pre_update_collection = []
        self.language = "en"
        self.known_packages = None
        self.known_providers = None

        self.providers_path = os.path.join(g.ADDON_USERDATA_PATH, "providers")
        self.modules_path = os.path.join(g.ADDON_USERDATA_PATH, "providerModules")
        self.meta_path = os.path.join(g.ADDON_USERDATA_PATH, "providerMeta")
        self.media_path = os.path.join(g.ADDON_USERDATA_PATH, "providerMedia")
        self.provider_types = ["torrent", "hosters", "adaptive", "direct"]

        try:
            with GlobalLock(self.__class__.__name__, True):
                self._init_providers()
        except RanOnceAlready:
            pass
        self.poll_database()
        self.provider_settings = SettingsManager()

    def _init_providers(self):
        g.log("Init provider packages")
        self.update_known_packages()
        self.update_known_providers()

    def _try_add_providers_path(self):
        try:
            if g.ADDON_USERDATA_PATH in sys.path:
                return reload_module(importlib.import_module("providers"))

            sys.path.append(g.ADDON_USERDATA_PATH)
            return importlib.import_module("providers")
        except ImportError:
            g.log("Providers folder appears to be missing")

    def poll_database(self):
        self.known_providers = self.get_providers()
        self.known_packages = self.get_provider_packages()

    def update_known_packages(self):
        packages = []
        for root, _, files in os.walk(self.meta_path):
            for filename in files:
                if filename.endswith(".json"):
                    with open(os.path.join(root, filename)) as f:
                        meta = json.load(f)
                        try:
                            packages.append(
                                (
                                    meta["name"],
                                    meta["author"],
                                    meta["remote_meta"],
                                    meta["version"],
                                    "|".join(meta.get("services", [])),
                                )
                            )
                        except KeyError:
                            continue

        predicate = "','".join(p[0] for p in packages)
        self.execute_sql(self.package_insert_query, packages)
        self.execute_sql(f"DELETE FROM providers where package not in ('{predicate}')")
        self.known_packages = self.get_provider_packages()

    def update_known_providers(self):
        providers = self._try_add_providers_path()
        all_providers = providers.get_all(self.language)
        providers = [
            (provider[1], provider[2], "enabled", self.language, provider_type)
            for provider_type in self.provider_types
            for provider in all_providers.get(provider_type, [])
            if any(provider[2] == package['pack_name'] for package in self.known_packages)
        ]

        self.execute_sql(self.provider_insert_query, providers)
        providers = {
            provider[1] for provider_type in self.provider_types for provider in all_providers.get(provider_type, [])
        }
        packages = {
            provider[2] for provider_type in self.provider_types for provider in all_providers.get(provider_type, [])
        }
        self.execute_sql(
            f"""
            DELETE FROM providers
            WHERE (NOT package IN ('{"','".join(packages)}') OR NOT provider_name IN ('{"','".join(providers)}'))
            """
        )

    def flip_provider_status(self, package_name, provider_name, status_override=None):
        current_status = self.get_single_provider(provider_name, package_name)["status"]

        if status_override:
            new_status = status_override
        else:
            new_status = "disabled" if current_status == "enabled" else "enabled"
        self.adjust_provider_status(provider_name, package_name, new_status)
        return new_status

    def get_icon(self, provider_imports):
        if not provider_imports or len(provider_imports) != 3:
            return None

        # provider_imports = ("providers.PACKAGE_NAME.LANGUAGE.PROVIDER_TYPE",
        #                     "PROVIDER_NAME",
        #                     "PACKAGE_NAME")
        package_name = provider_imports[2]
        package_split = provider_imports[0].split(".")
        language = package_split[2] if len(package_split) >= 3 else None
        provider_type = package_split[3] if len(package_split) >= 4 else None
        provider_name = provider_imports[1]

        package_path = None
        provider_path = None

        if None in [language, provider_type, provider_name]:
            package_path = os.path.join(
                g.ADDON_USERDATA_PATH,
                "providerMedia",
                package_name,
                f"{package_name}.png",
            )
        elif provider_type == "cloud":
            provider_path = os.path.join(
                g.IMAGES_PATH,
                "providerMedia",
                f"{provider_name}.png",
            )
        else:
            provider_path = os.path.join(
                g.ADDON_USERDATA_PATH,
                "providerMedia",
                package_name,
                language,
                provider_type,
                f"{provider_name}.png",
            )

        if provider_path is not None and xbmcvfs.exists(provider_path):
            return provider_path
        elif package_path is not None and xbmcvfs.exists(package_path):
            return package_path
        else:
            return None

    @staticmethod
    def deploy_init():
        folders = ["providerModules/", "providers/", "providerMedia/"]
        root_init_path = os.path.join(g.ADDON_USERDATA_PATH, "__init__.py")

        if not xbmcvfs.exists(g.ADDON_USERDATA_PATH):
            tools.makedirs(g.ADDON_USERDATA_PATH, exist_ok=True)
        if not xbmcvfs.exists(root_init_path):
            xbmcvfs.File(root_init_path, "a").close()
        for i in folders:
            folder_path = os.path.join(g.ADDON_USERDATA_PATH, i)
            tools.makedirs(folder_path, exist_ok=True)
            xbmcvfs.File(os.path.join(folder_path, "__init__.py"), "a").close()
        provider_init = xbmcvfs.File(os.path.join(g.ADDON_USERDATA_PATH, "providers", "__init__.py"), "w+")
        provider_init.write(str(base64.b64decode(INIT_BASE64).decode("utf-8")))
        provider_init.close()
