# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmcgui

from resources.lib.debrid.premiumize import PremiumizeTransfers, Premiumize
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers.base_resolver import (
    TorrentResolverBase,
)


class PremiumizeResolver(TorrentResolverBase):
    """
    Resolver for Premiumize
    """
    def __init__(self):
        super(PremiumizeResolver, self).__init__()
        self.debrid_module = Premiumize()
        self.transfer_class = PremiumizeTransfers()

    def _fetch_source_files(self, torrent, item_information):
        return self.debrid_module.direct_download(torrent["magnet"])["content"]

    def resolve_stream_url(self, file_info):
        """
        Convert provided source file into a link playable through debrid service
        :param file_info: Normalised information on source file
        :return: streamable link
        """
        if file_info is None:
            raise TypeError("NoneType passed to _fetch_transcode_or_standard")
        if g.get_bool_setting("premiumize.transcoded") and file_info[
            "transcode_status"
        ] in ["finished", "good_as_is"]:
            return file_info["stream_link"]
        else:
            return file_info["link"]

    def _do_post_processing(self, item_information, torrent):
        if g.get_bool_setting("premiumize.addToCloud"):
            transfer = self.debrid_module.create_transfer(torrent["magnet"])
            if transfer.get("id"):
                self.transfer_class.add_premiumize_transfer(transfer["id"])
            else:
                xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30508))
                g.log(transfer, "error")
