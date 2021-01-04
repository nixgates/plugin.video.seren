# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import base64
import importlib
import json
import os
import sys
import threading

import xbmcvfs

from resources.lib.common import tools
from resources.lib.database.providerCache import ProviderCache
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g
from resources.lib.modules.providers.settings import SettingsManager

try:
    from importlib import reload as reload_module  # pylint: disable=no-name-in-module
except ImportError:
    # Invalid version of importlib
    from imp import reload as reload_module

# Below is the contents of the providers/__init__.py base64 encoded
# If you update this init file_path you will need to update this base64 as well to ensure it is deployed on the users machine
# If you change the init file_path without updating this it will be overwritten with the old one!!
INIT_BASE64 = "aW1wb3J0IG9zCmZyb20gcmVzb3VyY2VzLmxpYi5tb2R1bGVzLmdsb2JhbHMgaW1wb3J0IGcKZnJvbSByZXNvdXJjZXMubGliLmRhdGFiYXNlLnByb3ZpZGVyQ2FjaGUgaW1wb3J0IFByb3ZpZGVyQ2FjaGUKCgpkZWYgX2lzX3ZhbGlkX3Byb3ZpZGVyX2RpcihuYW1lKToKICAgIGRpcl9wYXRoID0gb3MucGF0aC5qb2luKGRhdGFfcGF0aCwgbmFtZSkKICAgIHRyeToKICAgICAgICBpZiBub3Qgb3MucGF0aC5pc2RpcihkaXJfcGF0aCk6CiAgICAgICAgICAgIHJldHVybiBGYWxzZQogICAgICAgIGlmIG5hbWUuc3RhcnRzd2l0aCgnX18nKToKICAgICAgICAgICAgcmV0dXJuIEZhbHNlCgogICAgICAgIHJldHVybiBUcnVlCgogICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICByZXR1cm4gRmFsc2UKCgpkYXRhX3BhdGggPSBvcy5wYXRoLmpvaW4oZy5BRERPTl9VU0VSREFUQV9QQVRILCAncHJvdmlkZXJzJykKcHJvdmlkZXJfcGFja2FnZXMgPSBbbmFtZSBmb3IgbmFtZSBpbiBvcy5saXN0ZGlyKGRhdGFfcGF0aCkgaWYgX2lzX3ZhbGlkX3Byb3ZpZGVyX2RpcihuYW1lKV0KcHJvdmlkZXJDYWNoZSA9IFByb3ZpZGVyQ2FjaGUoKQoKcHJvdmlkZXJfdHlwZXMgPSAoCiAgICAoJ2hvc3RlcnMnLCAnZ2V0X2hvc3RlcnMnKSwKICAgICgndG9ycmVudCcsICdnZXRfdG9ycmVudCcpLAogICAgKCdhZGFwdGl2ZScsICdnZXRfYWRhcHRpdmUnKQopCgoKZGVmIF9pc19wcm92aWRlcl9lbmFibGVkKHByb3ZpZGVyX25hbWUsIHBhY2thZ2UsIHN0YXR1c2VzKToKICAgIHJldHVybiBUcnVlIGlmIGxlbigKICAgICAgICBbaSBmb3IgaSBpbiBzdGF0dXNlcyBpZiBpWydwcm92aWRlcl9uYW1lJ10gPT0gcHJvdmlkZXJfbmFtZSBhbmQgaVsncGFja2FnZSddID09IHBhY2thZ2VdKSBlbHNlIEZhbHNlCgoKZGVmIF9nZXRfcHJvdmlkZXJzKGxhbmd1YWdlLCBzdGF0dXM9RmFsc2UpOgogICAgcHJvdmlkZXJfc3RvcmUgPSB7CiAgICAgICAgJ2hvc3RlcnMnOiBbXSwKICAgICAgICAndG9ycmVudCc6IFtdLAogICAgICAgICdhZGFwdGl2ZSc6IFtdLAogICAgfQogICAgZm9yIHBhY2thZ2UgaW4gcHJvdmlkZXJfcGFja2FnZXM6CiAgICAgICAgcHJvdmlkZXJzX3BhdGggPSAncHJvdmlkZXJzLiVzLiVzJyAlIChwYWNrYWdlLCBsYW5ndWFnZSkKICAgICAgICBwcm92aWRlcl9saXN0ID0gX19pbXBvcnRfXyhwcm92aWRlcnNfcGF0aCwgZnJvbWxpc3Q9WycnXSkKICAgICAgICBmb3IgcHJvdmlkZXJfdHlwZSBpbiBwcm92aWRlcl90eXBlczoKICAgICAgICAgICAgZm9yIGkgaW4gZ2V0YXR0cihwcm92aWRlcl9saXN0LCBwcm92aWRlcl90eXBlWzFdLCBsYW1iZGE6IFtdKSgpOgogICAgICAgICAgICAgICAgaWYgc3RhdHVzIGlzIG5vdCBGYWxzZSBhbmQgbm90IF9pc19wcm92aWRlcl9lbmFibGVkKGksIHBhY2thZ2UsIHN0YXR1cyk6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICAgICBwcm92aWRlcl9zdG9yZVtwcm92aWRlcl90eXBlWzBdXS5hcHBlbmQoKCd7fS57fScuZm9ybWF0KHByb3ZpZGVyc19wYXRoLCBwcm92aWRlcl90eXBlWzBdKSwgaSwgcGFja2FnZSkpCgogICAgcmV0dXJuIHByb3ZpZGVyX3N0b3JlCgoKZGVmIGdldF9yZWxldmFudChsYW5ndWFnZSk6CiAgICAjIEdldCBlbmFibGVkIHByb3ZpZGVycwogICAgcHJvdmlkZXJfc3RhdHVzID0gW2kgZm9yIGkgaW4gcHJvdmlkZXJDYWNoZS5nZXRfcHJvdmlkZXJzKCkgaWYgaVsnY291bnRyeSddID09IGxhbmd1YWdlXQogICAgcHJvdmlkZXJfc3RhdHVzID0gW2kgZm9yIGkgaW4gcHJvdmlkZXJfc3RhdHVzIGlmIGlbJ3N0YXR1cyddID09ICdlbmFibGVkJ10KCiAgICByZXR1cm4gX2dldF9wcm92aWRlcnMobGFuZ3VhZ2UsIHByb3ZpZGVyX3N0YXR1cykKCgpkZWYgZ2V0X2FsbChsYW5ndWFnZSk6CiAgICByZXR1cm4gX2dldF9wcm92aWRlcnMobGFuZ3VhZ2UpCg=="

provider_lock = threading.Lock()


class CustomProviders(ProviderCache):
    def __init__(self):
        super(CustomProviders, self).__init__()
        self.deploy_init()
        self.providers_module = self._try_add_providers_path()
        self.pre_update_collection = []
        self.language = "en"
        self.known_packages = None
        self.known_providers = None

        self.providers_path = os.path.join(g.ADDON_USERDATA_PATH, "providers")
        self.modules_path = os.path.join(g.ADDON_USERDATA_PATH, "providerModules")
        self.meta_path = os.path.join(g.ADDON_USERDATA_PATH, "providerMeta")
        self.provider_types = ["torrent", "hosters", "adaptive"]
        with GlobalLock(self.__class__.__name__, provider_lock, True) as lock:
            if not lock.runned_once():
                self._init_providers()
        self.poll_database()
        self.provider_settings = SettingsManager()

    def _init_providers(self):
        g.log("Init provider packages")
        self.update_known_packages()
        self.update_known_providers()

    def _try_add_providers_path(self):
        try:
            if g.ADDON_USERDATA_PATH not in sys.path:
                sys.path.append(g.ADDON_USERDATA_PATH)
                return importlib.import_module("providers")
            else:
                return reload_module(importlib.import_module("providers"))

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
                    with open(os.path.join(root, filename), "r") as f:
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
        self.execute_sql(
            "DELETE FROM providers where package not in ('{}')".format(predicate)
        )
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
        providers = set(
            [
                provider[1]
                for provider_type in self.provider_types
                for provider in all_providers.get(provider_type, [])
            ]
        )
        packages = set(
            [
                provider[2]
                for provider_type in self.provider_types
                for provider in all_providers.get(provider_type, [])
            ]
        )
        self.execute_sql(
            "DELETE FROM providers WHERE (NOT package in ('{}') OR NOT provider_name in ('{}'))"
            "".format("','".join(packages), "','".join(providers))
        )

    def flip_provider_status(self, package_name, provider_name, status_override=None):
        current_status = self.get_single_provider(provider_name, package_name)["status"]

        if status_override:
            new_status = status_override
        else:
            new_status = "disabled" if current_status == "enabled" else "enabled"
        self.adjust_provider_status(provider_name, package_name, new_status)
        return new_status

    @staticmethod
    def deploy_init():
        folders = ["providerModules/", "providers/"]
        root_init_path = os.path.join(g.ADDON_USERDATA_PATH, "__init__ .py")

        if not xbmcvfs.exists(g.ADDON_USERDATA_PATH):
            tools.makedirs(g.ADDON_USERDATA_PATH, exist_ok=True)
        if not xbmcvfs.exists(root_init_path):
            xbmcvfs.File(root_init_path, "a").close()
        for i in folders:
            folder_path = os.path.join(g.ADDON_USERDATA_PATH, i)
            tools.makedirs(folder_path, exist_ok=True)
            xbmcvfs.File(os.path.join(folder_path, "__init__.py"), "a").close()
        provider_init = xbmcvfs.File(
            os.path.join(g.ADDON_USERDATA_PATH, "providers", "__init__.py"), "w+"
        )
        provider_init.write(
            str(base64.b64decode(g.decode_py2(INIT_BASE64)).decode("utf-8"))
        )
        provider_init.close()
