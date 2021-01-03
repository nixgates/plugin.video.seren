# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.debrid.all_debrid import AllDebrid
from resources.lib.modules.exceptions import UnexpectedResponse
from resources.lib.modules.resolver.torrent_resolvers.base_resolver import (
    TorrentResolverBase,
)


class AllDebridResolver(TorrentResolverBase):
    """
    Resolver for All Debrid
    """
    def __init__(self):
        super(AllDebridResolver, self).__init__()
        self.debrid_module = AllDebrid()
        self._source_normalization = (
            ("size", "size", lambda k: (k / 1024) / 1024),
            ("filename", ["release_title", "path"], None),
            ("id", "id", None),
            ("link", "link", None),
        )
        self.magnet_id = None

    def _fetch_source_files(self, torrent, item_information):
        self.magnet_id = self.debrid_module.upload_magnet(torrent['hash'])["magnets"][0]["id"]
        status = self.debrid_module.magnet_status(self.magnet_id)["magnets"]
        if status["status"] != "Ready":
            raise UnexpectedResponse(status)
        return status['links']

    def resolve_stream_url(self, file_info):
        """
        Convert provided source file into a link playable through debrid service
        :param file_info: Normalised information on source file
        :return: streamable link
        """
        return self.debrid_module.resolve_hoster(file_info["link"])

    def _do_post_processing(self, item_information, torrent):
        pass
