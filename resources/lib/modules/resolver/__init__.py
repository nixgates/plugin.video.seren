# -*- coding: utf-8 -*-
"""
Resolver Module for resolving supplied source information into an object that can be played through Player module
"""
from __future__ import absolute_import, division, unicode_literals

import sys

import requests
import xbmcgui
import xbmcvfs

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.debrid.all_debrid import AllDebrid
from resources.lib.debrid.premiumize import Premiumize
from resources.lib.debrid.real_debrid import RealDebrid
from resources.lib.modules.exceptions import (
    UnexpectedResponse,
    FileIdentification,
    ResolverFailure,
)
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers import PremiumizeResolver, RealDebridResolver, AllDebridResolver


class Resolver:
    """
    Handles resolving of identified sources to a playable format to supply to Player module
    """
    torrent_resolve_failure_style = g.get_int_setting('general.resolvefailurehandling')

    def __init__(self):
        sys.path.append(g.ADDON_USERDATA_PATH)
        self.return_data = None
        self.resolvers = {
            "all_debrid": AllDebridResolver,
            "premiumize": PremiumizeResolver,
            "real_debrid": RealDebridResolver,
            }

    def resolve_multiple_until_valid_link(self, sources, item_information, pack_select=False, silent=False):
        """
        Resolves all supplied sources until an identified link is found
        :param sources: List of sources to resolve
        :param item_information: Metadata on item intended to be played
        :param pack_select: Set to True to force manual file selection
        :return: streamable URL or dictionary of adaptive source information
        """
        stream_link = None

        for source in sources:
            stream_link = self.resolve_single_source(source, item_information, pack_select, silent)
            if stream_link:
                break

        return stream_link

    def resolve_single_source(self, source, item_information, pack_select=False, silent=False):
        """
        Resolves source to a streamable object
        :param source: Item to attempt to resolve
        :param item_information: Metadata on item intended to be played
        :param pack_select: Set to True to force manual file selection
        :return: streamable URL or dictionary of adaptive source information
        """

        stream_link = None

        try:
            if source["type"] == "Adaptive":
                stream_link = source

            elif source["type"] == "torrent":
                stream_link = self._resolve_debrid_source(
                    self.resolvers[source["debrid_provider"]],
                    source,
                    item_information,
                    pack_select,
                    )

                if not stream_link and self.torrent_resolve_failure_style == 1 and not pack_select and not silent:
                    if xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30531)):
                        stream_link = self._resolve_debrid_source(
                            self.resolvers[source["debrid_provider"]],
                            source,
                            item_information,
                            True,
                            )

            elif source["type"] == "hoster" or source["type"] == "cloud":
                stream_link = self._resolve_hoster_or_cloud(source, item_information)

            if stream_link:
                return stream_link
            else:
                g.log("Failed to resolve source: {}".format(source), "error")
        except ResolverFailure as e:
            g.log('Failed to resolve source: {}'.format(e))

    @staticmethod
    def _handle_provider_imports_resolving(source):
        provider = source["provider_imports"]
        provider_module = __import__(
            "{}.{}".format(provider[0], provider[1]), fromlist=[str("")]
            )
        if hasattr(provider_module, "source"):
            provider_module = provider_module.source()

        source["url"] = provider_module.resolve(source["url"])
        return source

    def _handle_debrid_hoster_resolving(self, source, item_information):
        stream_link = self._resolve_debrid_source(
            self.resolvers[source["debrid_provider"]], source, item_information, False
            )

        if not stream_link:
            return
        try:
            requests.head(stream_link, timeout=3)
            return stream_link
        except requests.exceptions.RequestException as e:
            g.log(e, 'error')
            g.log("Head Request failed link likely dead, skipping", 'error')
            return

    def _resolve_hoster_or_cloud(self, source, item_information):
        stream_link = None

        if not source.get("url", False):
            return

        if source["type"] == "cloud" and source["debrid_provider"] == "premiumize":
            selected_file = Premiumize().item_details(source["url"])
            if g.get_bool_setting("premiumize.transcoded"):
                stream_link = selected_file["stream_link"]
            else:
                stream_link = selected_file["link"]
            return stream_link

        if "provider_imports" in source:
            source = self._handle_provider_imports_resolving(source)

        if "debrid_provider" in source:
            stream_link = self._handle_debrid_hoster_resolving(source, item_information)
        elif source["url"].startswith("http"):
            stream_link = self._test_direct_url(source)
        elif xbmcvfs.exists(source["url"]):
            stream_link = source["url"]

        if stream_link is None:
            return
        if stream_link.endswith(".rar"):
            return

        return stream_link

    @staticmethod
    def _test_direct_url(source):
        try:
            ext = source["url"].split("?")[0]
            ext = ext.split("&")[0]
            ext = ext.split("|")[0]
            ext = ext.rsplit(".")[-1]
            ext = ext.replace("/", "").lower()
            if ext == "rar":
                raise TypeError("Incorrect file format - rar file provided")

            try:
                headers = source["url"].rsplit("|", 1)[1]
            except IndexError:
                headers = ""

            headers = tools.quote_plus(headers).replace("%3D", "=") if " " in headers else headers
            headers = dict(tools.parse_qsl(headers))

            live_check = requests.head(source["url"], headers=headers, timeout=10)

            if not live_check.status_code == 200:
                g.log("Head Request failed link likely dead, skipping")
                return

            stream_link = source["url"]
        except IndexError:
            stream_link = None
        except KeyError:
            stream_link = None

        return stream_link

    @staticmethod
    def _resolve_debrid_source(api, source, item_information, pack_select = False):
        stream_link = None
        api = api()

        if source["type"] == "torrent":
            try:
                stream_link = api.resolve_magnet(item_information, source, pack_select)
            except (UnexpectedResponse, FileIdentification) as e:
                g.log(e, "error")
                return None
            except Exception:
                g.log("Failing Magnet: {}".format(source["magnet"]))
                raise ResolverFailure(source)
        elif source["type"] in ["hoster", "cloud"]:
            try:
                stream_link = api.resolve_stream_url({"link": source["url"]})
            except (UnexpectedResponse, FileIdentification) as e:
                g.log(e, "error")
                raise ResolverFailure(source)

        return stream_link

    @staticmethod
    def get_hoster_list():
        """
        Fetche
        :return:
        """
        thread_pool = ThreadPool()

        hosters = {"premium": {}, "free": []}

        try:
            if g.get_bool_setting("premiumize.enabled") and g.get_bool_setting("premiumize.hosters"):
                thread_pool.put(Premiumize().get_hosters, hosters)

            if g.get_bool_setting("realdebrid.enabled") and g.get_bool_setting("rd.hosters"):
                thread_pool.put(RealDebrid().get_hosters, hosters)

            if g.get_bool_setting("alldebrid.enabled") and g.get_bool_setting("alldebrid.hosters"):
                thread_pool.put(AllDebrid().get_hosters, hosters)
            thread_pool.wait_completion()
        except ValueError:
            g.log_stacktrace()
            xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30525))
            return hosters
        return hosters
