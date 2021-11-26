# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc
import xbmcgui

from resources.lib.common.thread_pool import ThreadPool
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.download_manager import Manager
from resources.lib.modules.globals import g


class DownloadManager(BaseWindow):

    def __init__(self, xml_file, location):
        super(DownloadManager, self).__init__(xml_file, location)
        self.manager = Manager()
        self.list_control = None
        self.thread_pool = ThreadPool()
        self.exit_requested = False
        self.downloads = {}

    def onInit(self):
        self.list_control = self.getControlList(1000)
        self.setFocus(self.getControl(2001))
        self._populate_menu_items()
        self._background_info_updater()

    def update_download_info(self):
        self.downloads = self.manager.get_all_tasks_info()

    @staticmethod
    def _set_menu_item_properties(menu_item, download_info):
        menu_item.setProperty('speed', download_info['speed'])
        menu_item.setProperty('progress', g.UNICODE(download_info['progress']))
        menu_item.setProperty('filename', download_info['filename'])
        menu_item.setProperty('eta', download_info['eta'])
        menu_item.setProperty('filesize', g.UNICODE(download_info['filesize']))
        menu_item.setProperty('downloaded', g.UNICODE(download_info['downloaded']))
        menu_item.setProperty('hash', g.UNICODE(download_info.get('hash', '')))

    def _populate_menu_items(self):

        def create_menu_item(download):
            new_item = xbmcgui.ListItem(label='{}'.format(download['filename']))
            self._set_menu_item_properties(new_item, download)
            return new_item

        self.update_download_info()

        if len(self.downloads) < self.list_control.size():
            while len(self.downloads) < self.list_control.size():
                self.list_control.removeItem(self.list_control.size() - 1)

        for idx, download in enumerate(self.downloads):
            try:
                menu_item = self.list_control.getListItem(idx)
                self._set_menu_item_properties(menu_item, download)
            except RuntimeError:
                menu_item = create_menu_item(download)
                self.list_control.addItem(menu_item)

    def _background_info_updater(self):
        self.update_download_info()
        self.list_control.reset()
        while not self.exit_requested and not g.abort_requested():
            xbmc.sleep(1000)
            self.update_download_info()
            self._populate_menu_items()

    def close(self):
        self.exit_requested = True
        super(DownloadManager, self).close()

    def onClick(self, control_id):
        self.handle_action(7, control_id)

    def onAction(self, action):
        action_id = action.getId()
        if action_id in [92, 10, 117]:
            self.handle_action(action_id)

    def handle_action(self, action_id, control_id=None):
        position = self.list_control.getSelectedPosition()

        if control_id is None:
            control_id = self.getFocusId()

        if action_id == 117 or (action_id == 7 and control_id == 2003):
            response = xbmcgui.Dialog().contextmenu([g.get_language_string(30072), g.get_language_string(30483)])
            if response == 0 and position > -1:
                self.manager.cancel_task(self.list_control.getListItem(position).getProperty('hash'))

        if control_id == 2002 and action_id == 7:
            self.close()

        if control_id == 2001 and action_id == 7:
            self.manager.clear_complete()

        if action_id == 92 or action_id == 10:
            self.close()
