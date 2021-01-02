# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmcgui

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.cacheAssist import CacheAssistHelper
from resources.lib.modules.exceptions import GeneralCachingFailure, FailureAtRemoteParty
from resources.lib.modules.globals import g
from resources.lib.modules.source_sorter import SourceSorter


class ManualCacheWindow(BaseWindow):
    def __init__(self, xml_file, location, item_information=None, sources=None):
        super(ManualCacheWindow, self).__init__(xml_file, location, item_information=item_information)
        self.sources = SourceSorter(item_information['info']['mediatype'], uncached=True).sort_sources(sources)
        self.canceled = False
        self.display_list = None
        self.cached_source = None
        self.cache_assist_helper = CacheAssistHelper()
        g.close_busy_dialog()

    def onInit(self):
        super(ManualCacheWindow, self).onInit()
        self.display_list = self.getControlList(1000)
        self.display_list.reset()
        # self.sources = sorted(self.sources, key=lambda x: int(x['seeds']), reverse=True)
        for idx, i in enumerate(self.sources):
            menu_item = xbmcgui.ListItem(label='{}'.format(i['release_title']))
            for info in i.keys():
                try:
                    value = i[info]
                    if isinstance(value, list):
                        value = ' '.join(sorted([str(k) for k in value]))
                    if info == 'size':
                        value = tools.source_size_display(value)
                    menu_item.setProperty(info, str(value).replace('_', ' '))
                except UnicodeEncodeError:
                    menu_item.setProperty(info, i[info])

            struct_info = source_utils.info_list_to_dict(i.get('info', []))
            for property in struct_info.keys():
                menu_item.setProperty('info.{}'.format(property), struct_info[property])

            self.display_list.addItem(menu_item)

        self.setFocusId(1000)

    def onClick(self, control_id):
        self._handle_action(7, control_id)

    def _handle_action(self, action_id, control_id=None):
        if action_id == 7:
            focus_id = self.getFocusId()
            if focus_id == 1000:
                try:
                    self._cache_item()
                except (GeneralCachingFailure, FailureAtRemoteParty) as e:
                    g.log(e, 'error')
            elif focus_id == 2001:
                self.close()

        else:
            super(ManualCacheWindow, self).handle_action(action_id, control_id)

    def doModal(self):
        super(ManualCacheWindow, self).doModal()
        return self.cached_source

    def _cache_item(self):
        uncached_source = self.sources[self.display_list.getSelectedPosition()]
        cache_assist_module = self.cache_assist_helper.manual_cache(uncached_source)

        cache_status = cache_assist_module.do_cache()

        if cache_status['result'] == 'success':
            return cache_status['source']
        else:
            return None
