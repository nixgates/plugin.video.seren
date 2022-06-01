# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmcgui

from resources.lib.common.source_utils import INFO_STRUCT
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g


class FilterSelect(BaseWindow):
    """
    Dialog to provide filter settings
    """

    def __init__(self, xml_file, xml_location):
        super(FilterSelect, self).__init__(xml_file, xml_location)

        self.videocodec_list = None
        self.hdrcodec_list = None
        self.audiocodec_list = None
        self.audiochannels_list = None
        self.misc_list = None

        filter_string = g.get_setting("general.filters")
        self.current_filters = (
            set() if filter_string is None else set(filter_string.split(","))
        )

    def onInit(self):
        self.videocodec_list = self.getControlList(1000)
        self.hdrcodec_list = self.getControlList(2000)
        self.audiocodec_list = self.getControlList(3000)
        self.audiochannels_list = self.getControlList(4000)
        self.misc_list = self.getControlList(5000)

        self._populate_list(self.videocodec_list, "videocodec")
        self._populate_list(self.hdrcodec_list, "hdrcodec")
        self._populate_list(self.audiocodec_list, "audiocodec")
        self._populate_list(self.audiochannels_list, "audiochannels")
        self._populate_list(self.misc_list, "misc")

        super(FilterSelect, self).onInit()

    @staticmethod
    def _set_setting_item_properties(menu_item, setting):
        value = g.UNICODE(setting["value"])
        menu_item.setProperty("label", setting["label"])
        menu_item.setProperty("value", value)

    def _populate_list(self, codec_list, key):
        def _create_menu_item(setting):
            new_item = xbmcgui.ListItem(label="{}".format(setting["label"]))
            self._set_setting_item_properties(new_item, setting)
            return new_item

        for idx, codec in enumerate(
            sorted([i for i in INFO_STRUCT[key] if i not in {"SDR", }])
        ):
            info_item = {
                "label": codec,
                "value": True if codec in self.current_filters else False,
            }
            if idx < codec_list.size():
                menu_item = codec_list.getListItem(idx)
                self._set_setting_item_properties(
                    menu_item,
                    info_item,
                )
            else:
                menu_item = _create_menu_item(info_item)
                codec_list.addItem(menu_item)

    def _flip_info(self, list_item):
        label = list_item.getLabel()
        if label in self.current_filters:
            self.current_filters.remove(label)
            list_item.setProperty("value", g.UNICODE(False))
        else:
            self.current_filters.add(label)
            list_item.setProperty("value", g.UNICODE(True))

    def handle_action(self, action, control_id=None):
        if action == 7:
            if control_id in [1000, 2000, 3000, 4000, 5000]:
                lists = {
                    1000: self.videocodec_list,
                    2000: self.hdrcodec_list,
                    3000: self.audiocodec_list,
                    4000: self.audiochannels_list,
                    5000: self.misc_list,
                }

                li = lists.get(control_id).getSelectedItem()

                self._flip_info(li)
            if control_id == 6001:
                self.close()

    def close(self):
        g.set_setting("general.filters", ",".join(self.current_filters))
        super(FilterSelect, self).close()
        g.open_addon_settings(6, 1)  # Open settings back where we were launched from
