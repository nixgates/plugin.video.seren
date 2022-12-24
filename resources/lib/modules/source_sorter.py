from difflib import SequenceMatcher

import xbmcgui

from resources.lib.common.source_utils import get_accepted_resolution_set
from resources.lib.common.tools import FixedSortPositionObject
from resources.lib.modules.globals import g


class SourceSorter:
    """
    Handles sorting of sources according to users preferences
    """

    FIXED_SORT_POSITION_OBJECT = FixedSortPositionObject()

    def __init__(self, item_information):
        """
        Handles sorting of sources according to users preference
        """
        self.item_information = item_information
        self.mediatype = self.item_information['info']['mediatype']

        # Filter settings
        self.resolution_set = get_accepted_resolution_set()
        self.disable_dv = False
        self.disable_hdr = False
        self.filter_set = self._get_filters()

        # Size filter settings
        self.enable_size_limit = g.get_bool_setting("general.enablesizelimit")
        setting_mediatype = g.MEDIA_EPISODE if self.mediatype == g.MEDIA_EPISODE else g.MEDIA_MOVIE
        self.size_limit = g.get_int_setting(f"general.sizelimit.{setting_mediatype}") * 1024
        self.size_minimum = int(g.get_float_setting(f"general.sizeminimum.{setting_mediatype}") * 1024)

        # Sort Settings
        self.quality_priorities = {"4K": 3, "1080p": 2, "720p": 1, "SD": 0}

        # Sort Methods
        self._get_sort_methods()

    def _get_filters(self):
        filter_string = g.get_setting("general.filters")
        current_filters = set() if filter_string is None else set(filter_string.split(","))

        # Set HR filters and remove from set before returning due to HYBRID
        self.disable_dv = "DV" in current_filters
        self.disable_hdr = "HDR" in current_filters

        return current_filters.difference({"HDR", "DV"})

    def filter_sources(self, source_list):
        # Iterate sources, yielding only those that are not filtered
        for source in source_list:
            # Quality filter
            if (
                source['quality'] not in self.resolution_set
                and all(quality not in self.resolution_set for quality in source['quality'].split('/'))
                and source['quality'] != "Unknown"
            ):
                continue
            # Info Filter
            if self.filter_set & source['info']:
                continue
            # DV filter
            if self.disable_dv and "DV" in source['info'] and "HYBRID" not in source['info']:
                continue
            # HDR Filter
            if self.disable_hdr and "HDR" in source['info'] and "HYBRID" not in source['info']:
                continue
            # Hybrid Filter
            if self.disable_dv and self.disable_hdr and "HYBRID" in source['info']:
                continue
            if self.enable_size_limit:
                if (
                    (
                        isinstance(size := source.get("size", 0), (int, float))
                        and not (self.size_minimum <= int(size) <= self.size_limit)
                    )
                    or isinstance(size, str)
                    and size != "Variable"
                ):
                    continue

            # If not filtered, yield source
            yield source

    def sort_sources(self, sources_list):
        """Takes in a list of sources and filters and sorts them according to Seren's sort settings

        :param sources_list: list of sources
        :type sources_list: list
        :return: sorted list of sources
        :rtype: list
        """
        if not sources_list:
            return []

        filtered_sources = list(self.filter_sources(sources_list))
        if not filtered_sources:
            response = (
                None
                if g.get_bool_runtime_setting('tempSilent')
                else xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30474))
            )

            if response or g.get_bool_runtime_setting('tempSilent'):
                return self._sort_sources(sources_list)
            else:
                return []
        return self._sort_sources(filtered_sources)

    def _get_sort_methods(self):
        """
        Get Seren settings for sort methods
        """
        sort_methods = []
        sort_method_settings = {
            0: None,
            1: self._get_quality_sort_key,
            2: self._get_type_sort_key,
            3: self._get_debrid_priority_key,
            4: self._get_size_sort_key,
            5: self._get_low_cam_sort_key,
            6: self._get_hevc_sort_key,
            7: self._get_hdr_sort_key,
            8: self._get_audio_channels_sort_key,
        }

        if self.mediatype == g.MEDIA_EPISODE and g.get_bool_setting("general.lastreleasenamepriority"):
            self.last_release_name = g.get_runtime_setting(
                f"last_resolved_release_title.{self.item_information['info']['trakt_show_id']}"
            )
            if self.last_release_name:
                sort_methods.append((self._get_last_release_name_sort_key, False))

        for i in range(1, 9):
            sm = g.get_int_setting(f"general.sortmethod.{i}")
            reverse = g.get_bool_setting(f"general.sortmethod.{i}.reverse")

            if sort_method_settings[sm] is None:
                break

            if sort_method_settings[sm] == self._get_type_sort_key:
                self._get_type_sort_order()
            if sort_method_settings[sm] == self._get_debrid_priority_key:
                self._get_debrid_sort_order()
                reverse = False
            if sort_method_settings[sm] == self._get_hdr_sort_key:
                self._get_hdr_sort_order()

            sort_methods.append((sort_method_settings[sm], reverse))

        self.sort_methods = sort_methods

    def _get_type_sort_order(self):
        """
        Get seren settings for type sort priority
        """
        type_priorities = {}
        type_priority_settings = {
            0: None,
            1: "cloud",
            2: "adaptive",
            3: "torrent",
            4: "hoster",
            5: "direct",
        }

        for i in range(1, 6):
            tp = type_priority_settings.get(g.get_int_setting(f"general.sourcetypesort.{i}"))
            if tp is None:
                break
            type_priorities[tp] = -i
        self.type_priorities = type_priorities

    def _get_hdr_sort_order(self):
        """
        Get seren settings for type sort priority
        """
        hdr_priorities = {}
        hdr_priority_settings = {
            0: None,
            1: "DV",
            2: "HDR",
        }

        for i in range(1, 3):
            hdrp = hdr_priority_settings.get(g.get_int_setting(f"general.hdrsort.{i}"))
            if hdrp is None:
                break
            hdr_priorities[hdrp] = -i
        self.hdr_priorities = hdr_priorities

    def _get_debrid_sort_order(self):
        """
        Get seren settings for debrid sort priority
        """
        debrid_priorities = {}
        debrid_priority_settings = {
            0: None,
            1: "premiumize",
            2: "real_debrid",
            3: "all_debrid",
        }

        for i in range(1, 4):
            debridp = debrid_priority_settings.get(g.get_int_setting(f"general.debridsort.{i}"))
            if debridp is None:
                break
            debrid_priorities[debridp] = -i
        self.debrid_priorities = debrid_priorities

    def _sort_sources(self, sources_list):
        """
        Sort a source list based on sort_methods defined by settings
        All sort method key methods should return key values for *descending* sort.  If a reversed sort is required,
        reverse is specified as a boolean for the second item of each tuple in sort_methods
        :param sources_list: The list of sources to sort
        :return: The list of sorted sources
        :rtype: list
        """
        sources_list = sorted(sources_list, key=lambda s: s['release_title'])
        return sorted(sources_list, key=self._get_sort_key_tuple, reverse=True)

    def _get_sort_key_tuple(self, source):
        return tuple(-sm(source) if reverse else sm(source) for (sm, reverse) in self.sort_methods if sm)

    def _get_type_sort_key(self, source):
        return self.type_priorities.get(source.get("type"), -99)

    def _get_quality_sort_key(self, source):
        quality = source.get("quality")
        if quality is not None and '/' in quality:
            quality = quality.split('/')[0]
        return self.quality_priorities.get(quality, -99)

    def _get_debrid_priority_key(self, source):
        return self.debrid_priorities.get(source.get("debrid_provider"), self.FIXED_SORT_POSITION_OBJECT)

    def _get_size_sort_key(self, source):
        size = source.get("size", None)
        if size is None or not isinstance(size, (int, float)) or size < 0:
            size = 0
        return size

    @staticmethod
    def _get_low_cam_sort_key(source):
        return "CAM" not in source.get("info", {})

    @staticmethod
    def _get_hevc_sort_key(source):
        return "HEVC" in source.get("info", {})

    def _get_hdr_sort_key(self, source):
        hdrp = -99
        dvp = -99

        if "HDR" in source.get("info", {}):
            hdrp = self.hdr_priorities.get("HDR", -99)
        if "DV" in source.get("info", {}):
            dvp = self.hdr_priorities.get("DV", -99)

        return max(hdrp, dvp)

    def _get_last_release_name_sort_key(self, source):
        sm = SequenceMatcher(None, self.last_release_name, source['release_title'], autojunk=False)
        if sm.real_quick_ratio() < 1:
            return 0
        ratio = sm.ratio()
        return 0 if ratio < 0.85 else ratio

    @staticmethod
    def _get_audio_channels_sort_key(source):
        audio_channels = None
        if info := source['info']:
            audio_channels = {"2.0", "5.1", "7.1"} & info
        return float(max(audio_channels)) if audio_channels else 0
