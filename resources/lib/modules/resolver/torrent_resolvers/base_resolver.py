# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import abc

import xbmcgui

from resources.lib.common import source_utils
from resources.lib.indexers.apibase import ApiBase
from resources.lib.modules.exceptions import FileIdentification
from resources.lib.modules.globals import g


class TorrentResolverBase(ApiBase):
    """
    Base Class to resolve torrent from debrid provider
    Extend appropriate debrid torrent resolver with this class
    """
    def __init__(self):
        super(TorrentResolverBase, self).__init__()
        self.pack_select = False
        self.debrid_module = None
        self._source_normalization = None
        self.media_type = None
        self.item_information = None

    def resolve_magnet(self, item_information, torrent, pack_select=False):
        """
        Resolves torrent information into a playable stream link
        :param item_information: Dictionary of show/movies meta
        :param torrent: torrent information identified
        :param pack_select: allows manual selection of file within torrent
        :return:
        """
        self.item_information = item_information
        self.pack_select = pack_select
        if "tvshowtitle" not in item_information["info"]:
            self.media_type = "movie"
            return self._movie_resolve(item_information, torrent)
        else:
            self.media_type = "episode"
            return self._multi_pack_resolve(item_information, torrent)

    @abc.abstractmethod
    def _fetch_source_files(self, torrent, item_information):
        """
        Fetches files from debrid service
        :param torrent: source dictionary
        :return: list - normalized list of files
        """

    def _normalize_item(self, item):
        if not self._source_normalization:
            return item
        else:
            return self._normalize_info(self._source_normalization, item)

    @abc.abstractmethod
    def resolve_stream_url(self, file_info):
        """
        Makes final connection to debrid provider for the streamable link
        :param file_info: dict - normalized information for file
        :return: string - Streamable URL
        """

    @abc.abstractmethod
    def _do_post_processing(self, item_information, torrent):
        """
        Perform any required processing post the resolving of the file
        :param torrent:
        :param item_information:
        :param identified_file:
        :return:
        """

    @staticmethod
    def _filter_non_playable_files(folder_details):
        return [i for i in folder_details if source_utils.is_file_ext_valid(i["path"])]

    def _user_selection(self, folder_details):
        folder_details = self._filter_non_playable_files(folder_details)
        folder_details = sorted(folder_details, key= lambda k: k['path'].split("/")[-1])
        selection = xbmcgui.Dialog().select(g.get_language_string(30523),
                                            [i['path'].split('/')[-1] for i in folder_details])
        return folder_details[selection] if selection >= 0 else None

    def _finalize_resolving(self, item_information, torrent, identified_file, folder_details):
        if identified_file is None:
            return None
        stream_link = self.resolve_stream_url(identified_file)
        self._do_post_processing(item_information, torrent)
        if not stream_link:
            raise FileIdentification([i["path"] for i in folder_details])
        return stream_link

    def _sort_and_filter_files(self, folder_details, item_information, sort = False):
        filtered_files = self._filter_non_playable_files(source_utils.filter_files_for_resolving(folder_details,
                                                                                                 item_information))

        if sort:
            filtered_files = sorted(
                filtered_files, key=lambda i: int(i["size"]), reverse=True
                )
        return filtered_files

    def _multi_pack_resolve(self, item_information, torrent):
        folder_details = self._normalize_item(self._fetch_source_files(torrent, item_information))
        if self.pack_select:
            return self._finalize_resolving(
                item_information,
                torrent,
                self._user_selection(folder_details),
                folder_details,
                )
        else:
            folder_details = self._sort_and_filter_files(
                folder_details, item_information
                )
            best_match = source_utils.get_best_episode_match(
                "path", folder_details, item_information
                )
            return self._finalize_resolving(
                item_information, torrent, best_match, folder_details
                )

    @staticmethod
    def _try_m2ts_resolving(folder_details):
        if any(i['path'].endswith(".m2ts") for i in folder_details):
            return sorted(folder_details, key=lambda s: s['size'], reverse=True)[0]

    def _movie_resolve(self, item_information, torrent):
        simple_info = {
            "year": item_information.get("info", {}).get("year"),
            "title": item_information.get("info").get("title"),
            }

        folder_details = self._sort_and_filter_files(
            self._normalize_item(self._fetch_source_files(torrent, item_information)), item_information, True
            )

        if self.pack_select:
            return self._finalize_resolving(
                item_information,
                torrent,
                self._user_selection(folder_details),
                folder_details,
                )

        m2ts_check = self._try_m2ts_resolving(folder_details)
        if m2ts_check:
            return self._finalize_resolving(
                item_information, torrent, folder_details[0], [m2ts_check]
                )

        if len(folder_details) == 1:
            return self._finalize_resolving(
                item_information, torrent, folder_details[0], folder_details
                )

        folder_details = source_utils.filter_files_for_resolving(
            folder_details, item_information
            )
        filter_list = [
            i
            for i in folder_details
            if source_utils.filter_movie_title(
                None,
                i["path"].split("/")[-1],
                item_information["info"]["originaltitle"],
                simple_info,
                )
            ]
        if len(filter_list) == 1:
            return self._finalize_resolving(
                item_information, torrent, filter_list[0], folder_details
                )

        raise FileIdentification([i["path"] for i in folder_details])
