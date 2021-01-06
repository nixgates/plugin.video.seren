# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmcgui

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.database.skinManager import SkinManager
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.gui.windows.manual_caching import ManualCacheWindow
from resources.lib.modules.download_manager import create_task as download_file
from resources.lib.modules.globals import g
from resources.lib.modules.helpers import Resolverhelper


class SourceSelect(BaseWindow):
    """
    Window for source select
    """
    def __init__(self, xml_file, location, item_information = None, sources = None, uncached = None):
        super(SourceSelect, self).__init__(xml_file, location, item_information=item_information)
        self.uncached_sources = uncached
        self.sources = sources
        self.position = -1
        self.canceled = False
        self.display_list = None
        g.close_busy_dialog()
        self.stream_link = None

    def onInit(self):
        """
        Callback method for Kodi
        :return: None
        """
        self.display_list = self.getControlList(1000)
        self.display_list.reset()
        for idx, i in enumerate(self.sources):
            menu_item = self.get_list_item_with_properties(self.item_information, i['release_title'])
            for info in i.keys():
                try:
                    value = i[info]
                    if isinstance(value, list):
                        value = [str(k) for k in value]
                        value = ' '.join(sorted(value))
                    if info == 'size' and value != 'Variable':
                        value = tools.source_size_display(value)
                    menu_item.setProperty(info, str(value).replace('_', ' '))
                except UnicodeEncodeError:
                    menu_item.setProperty(info, i[info])

            struct_info = source_utils.info_list_to_dict(i.get('info', []))
            for prop in struct_info.keys():
                menu_item.setProperty('info.{}'.format(prop), struct_info[prop])

            self.display_list.addItem(menu_item)

        self.setFocusId(1000)

    def doModal(self):
        """
        Opens window in an intractable mode and runs background scripts
        :return:
        """
        super(SourceSelect, self).doModal()
        return self.stream_link

    def onClick(self, control_id):
        """
        Callback method from Kodi
        :param control_id: in
        :return: None
        """
        self._handle_action(7)

    def _handle_action(self, action_id, control_id = None):
        self.position = self.display_list.getSelectedPosition()

        if action_id == 117:
            response = xbmcgui.Dialog().contextmenu([g.get_language_string(30335),
                                                     g.get_language_string(30350),
                                                     g.get_language_string(30509),
                                                     g.get_language_string(30523)])
            if response == 0:
                self._open_manual_cache_assist()
            elif response == 1:
                action_id = 7
            elif response == 2:
                download_file(self.sources[self.display_list.getSelectedPosition()])
                xbmcgui.Dialog().ok(g.ADDON_NAME, 'Download task started')
            elif response == 3:
                self._resolve_item(True)

        if action_id == 7:
            focus_id = self.getFocusId()

            if focus_id == 1000 or focus_id == 2003:
                self._resolve_item(False)
            elif focus_id == 2001:
                self._open_manual_cache_assist()
            elif focus_id == 2002:
                download_file(self.sources[self.position])
                xbmcgui.Dialog().ok(g.ADDON_NAME, 'Download task started')

        if action_id == 92 or action_id == 10:
            self.stream_link = False
            self.close()

    def onAction(self, action):
        """
        Callback method from Kodi on keyboard input
        :param action:
        :return:
        """
        action_id = action.getId()
        if action_id in [92, 10, 117]:
            self._handle_action(action_id)
            return
        super(SourceSelect, self).onAction(action)

    def _resolve_item(self, pack_select):
        if g.get_bool_setting('general.autotrynext') and not pack_select:
            sources = self.sources[self.position:]
        else:
            sources = [self.sources[self.position]]

        self.stream_link = Resolverhelper().resolve_silent_or_visible(sources, self.item_information, pack_select,
                                                                      overwrite_cache=pack_select)

        if self.stream_link is None:
            g.notification(g.ADDON_NAME, g.get_language_string(30033), time=2000)
        else:
            self.close()

    def _open_manual_cache_assist(self):
        window = ManualCacheWindow(*SkinManager().confirm_skin_path('manual_caching.xml'),
                                   item_information=self.item_information, sources=self.uncached_sources)
        newly_cached_source = window.doModal()
        del window
        if newly_cached_source is None:
            return

        self.sources = [newly_cached_source] + self.sources
        self.onInit()
