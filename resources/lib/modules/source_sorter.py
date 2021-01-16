# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import random
from copy import deepcopy

import xbmcgui

from resources.lib.common import tools
from resources.lib.common.source_utils import get_accepted_resolution_list
from resources.lib.debrid import get_debrid_priorities
from resources.lib.modules.globals import g


class SourceSorter:
    """
    Handles sorting of sources according to users preferences
    """

    def __init__(self, media_type, uncached=False):
        """
        Handles sorting of sources according to users preference
        :param media_type: Type of media to be sorted (movie/episode)
        :type media_type: str
        :param uncached: Whether to include uncached torrents or not
        :type uncached: bool
        """
        self.sort_method = g.get_int_setting("general.sortsources")
        self.resolution_list = reversed(get_accepted_resolution_list())
        self.media_type = media_type
        self.torrent_list = []
        self.hoster_list = []
        self.cloud_files = []
        self.source_types = ["torrent_list", "hoster_list", "cloud_files"]
        self.debrid_priorities = get_debrid_priorities()
        self._resolution_lambda = lambda i, j, k: i == k["quality"] and \
                                                  (j["slug"] == k.get("debrid_provider", "")
                                                   or (not k.get("debrid_provider", "") and uncached))
        self.group_style = [
            self._group_method_zero,
            self._group_method_one,
            self._group_method_two,
            lambda: self.torrent_list + self.hoster_list + self.cloud_files
            ]

    def _apply_sort_to_all_types(self, **kwargs):
        for i in self.source_types:
            setattr(self, i, sorted(getattr(self, i, []), **kwargs))

    def _filter_all_by_methods(self, lambda_methods):
        for idx, i in enumerate(self.source_types):
            lists = []
            for method in lambda_methods:
                lists.append(
                    self._filter_list_by_method(
                        getattr(self, self.source_types[idx], []), method
                        )
                    )

            setattr(self, i, [item for sublist in lists for item in sublist])

    @staticmethod
    def _filter_list_by_method(unfiltered_list, lambda_method):
        return [i for i in unfiltered_list if lambda_method(i)]

    def _stacked_for_loops_filter(self, stacked_lists, lambda_methods, *args):
        args = [i for i in args]
        if args:
            args = args.pop(0)
        if stacked_lists:
            results = []
            for i in stacked_lists[0]:
                results += self._stacked_for_loops_filter(
                    stacked_lists[1:], lambda_methods, args + [i]
                    )
            return results
        else:
            filtered = []
            for method in lambda_methods:
                if not method(*args):
                    return []
            filtered.append(args[-1])
            return filtered

    def _size_sort(self):
        if g.get_bool_setting("general.sizesort"):
            self._apply_sort_to_all_types(
                key=lambda k: int(k["size"]),
                reverse=not g.get_bool_setting("general.reversesizesort"),
                )
        else:
            random.shuffle(self.torrent_list)

    def _filter_3d(self):
        if g.get_bool_setting("general.disable3d"):
            self._filter_all_by_methods([lambda i: "3D" not in i["info"]])

    def _filter_cam_quality(self):
        if g.get_bool_setting("general.disablelowQuality"):
            self._filter_all_by_methods([lambda i: "CAM" not in i["info"]])

    def _apply_size_limits(self):
        if g.get_bool_setting("general.enablesizelimit"):
            if self.media_type == "episode":
                size_limit = g.get_int_setting("general.sizelimit.episode") * 1024
                size_minimum = int(g.get_float_setting("general.sizeminimum.episode") * 1024)
            else:
                size_limit = g.get_int_setting("general.sizelimit.movie") * 1024
                size_minimum = int(g.get_float_setting("general.sizeminimum.movie") * 1024)
            self._filter_all_by_methods(
                [lambda i: size_limit > int(i.get("size", 0)) > size_minimum]
                )

    def _apply_hevc_priority(self):
        if g.get_bool_setting("general.265sort"):
            self._filter_all_by_methods(
                [lambda i: "HEVC" in i["info"], lambda i: "HEVC" not in i["info"]]
                )

    def _low_cam_sort(self):
        if g.get_bool_setting("general.lowQualitysort"):
            self._filter_all_by_methods(
                [lambda i: "CAM" not in i["info"], lambda i: "CAM" in i["info"]]
                )

    def _filter_hevc(self):
        if g.get_bool_setting("general.disable265"):
            self._filter_all_by_methods([lambda i: "HEVC" not in i["info"]])

    def _filter_sd(self):
        if g.get_bool_setting("general.hidesd"):
            self._filter_all_by_methods([lambda i: i["quality"] != "SD"])

    def _filter_hdr(self):
        if g.get_bool_setting("general.disablehdrsources"):
            self._filter_all_by_methods([lambda i: "HDR" not in i["info"]])

    def _resolution_sort_helper(self, resolution, methods, list_to_filter):
        return self._stacked_for_loops_filter(
            [[resolution], self.debrid_priorities, list_to_filter], [methods]
            )

    def _group_method_zero(self):
        sorted_list = []

        for resolution in self.resolution_list:
            sorted_list += self._resolution_sort_helper(
                resolution, self._resolution_lambda,  tools.extend_array(self.torrent_list, self.cloud_files)
                )
            sorted_list += self._resolution_sort_helper(
                resolution, self._resolution_lambda, self.hoster_list
                )

            for file in self.hoster_list:
                if (
                        "debrid_provider" not in file
                        and file.get("direct")
                        and file.get("quality") == resolution
                ):
                    sorted_list.append(file)

        for resolution in self.resolution_list:
            sorted_list += self._resolution_sort_helper(
                resolution, self._resolution_lambda, self.hoster_list
                )

            for file in self.hoster_list:
                if (
                        "debrid_provider" not in file
                        and file.get("direct")
                        and file.get("quality") == resolution
                ):
                    sorted_list.append(file)

        return sorted_list

    def _group_method_one(self):
        sorted_list = []
        for resolution in self.resolution_list:
            sorted_list += self._resolution_sort_helper(
                resolution, self._resolution_lambda, self.hoster_list
                )

            for file in self.hoster_list:
                if "debrid_provider" not in file and file["quality"] == resolution and file.get("direct"):
                    sorted_list.append(file)

        sorted_list += self._stacked_for_loops_filter(
            [self.resolution_list, self.debrid_priorities, tools.extend_array(self.torrent_list, self.cloud_files)],
            [self._resolution_lambda],
            )

        return sorted_list

    def _group_method_two(self):
        sorted_list = []

        for resolution in self.resolution_list:
            sorted_list += self._resolution_sort_helper(
                resolution, self._resolution_lambda, tools.extend_array(self.torrent_list, self.cloud_files)
                )
            sorted_list += self._resolution_sort_helper(
                resolution, self._resolution_lambda, self.hoster_list
                )

            for file in self.hoster_list:
                if "debrid_provider" not in file and file["quality"] == resolution and file.get("direct"):
                    sorted_list.append(file)

        return sorted_list

    def _do_filters(self):
        self._filter_3d()
        self._filter_cam_quality()
        self._apply_size_limits()
        self._low_cam_sort()
        self._filter_sd()
        self._filter_hevc()
        self._filter_hdr()

    def _do_priorities(self):
        self._apply_hevc_priority()

    def _do_sorts(self):
        self._size_sort()
        self._do_priorities()
        sorted_list = self.group_style[self.sort_method]()
        return [i for i in sorted_list if i.get("type") == "cloud"] +\
               [i for i in sorted_list if i.get("type") != "cloud"]

    def sort_sources(self, torrents=None, hosters=None, cloud=None):
        """Takes in multiple optional lists of sources and sorts them according to Seren's sort settings

         :param torrents: list of torrent sources
         :type torrents: list
         :param hosters: list of hoster sources
         :type hosters: list
         :param cloud: list of cloud sources
         :type cloud: list
         :return: sorted list of sources
         :rtype: list
         """
        torrents = torrents if torrents else []
        hosters = hosters if hosters else []
        cloud = cloud if cloud else []

        self.torrent_list = deepcopy(torrents)
        self.hoster_list = deepcopy(hosters)
        self.cloud_files = deepcopy(cloud)

        self._do_filters()
        if (
                len(self.torrent_list + self.hoster_list + self.cloud_files) == 0
                and len(torrents + hosters + cloud) > 0
        ):
            response = xbmcgui.Dialog().yesno(
                g.ADDON_NAME, g.get_language_string(30510)
                )
            if response:
                self.torrent_list = deepcopy(torrents)
                self.hoster_list = deepcopy(hosters)
                self.cloud_files = deepcopy(cloud)
        return self._do_sorts()
