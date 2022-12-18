import xbmc
import xbmcgui

from resources.lib.common.thread_pool import ThreadPool
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.download_manager import Manager
from resources.lib.modules.globals import g


class DownloadManager(BaseWindow):
    def __init__(self, xml_file, location, item_information=None):
        super().__init__(xml_file, location, item_information=item_information)
        self.manager = Manager()
        self.list_control = None
        self.thread_pool = ThreadPool()
        self.exit_requested = False
        self.downloads = []

    def onInit(self):
        self.list_control = self.getControlList(1000)

        self._populate_menu_items()
        self.set_default_focus(self.list_control, 2999, control_list_reset=True)

        self._background_info_updater()
        super().onInit()

    def update_download_info(self):
        self.downloads = self.manager.get_all_tasks_info()

    @staticmethod
    def _set_menu_item_properties(menu_item, download_info):
        menu_item.setProperty('speed', download_info['speed'])
        menu_item.setProperty('progress', str(download_info['progress']))
        menu_item.setProperty('filename', download_info['filename'])
        menu_item.setProperty('eta', download_info['eta'])
        menu_item.setProperty('filesize', str(download_info['filesize']))
        menu_item.setProperty('downloaded', str(download_info['downloaded']))
        menu_item.setProperty('hash', str(download_info.get('hash', '')))

    def _populate_menu_items(self):
        def create_menu_item(download_item):
            new_item = xbmcgui.ListItem(label=f"{download_item['filename']}")
            self._set_menu_item_properties(new_item, download_item)
            return new_item

        self.update_download_info()

        if len(self.downloads) < self.list_control.size():
            while len(self.downloads) < self.list_control.size():
                self.list_control.removeItem(self.list_control.size() - 1)

        for idx, download in enumerate(self.downloads):
            if idx < self.list_control.size():
                menu_item = self.list_control.getListItem(idx)
                self._set_menu_item_properties(menu_item, download)
            else:
                menu_item = create_menu_item(download)
                self.list_control.addItem(menu_item)

    def _background_info_updater(self):
        self.update_download_info()
        while not self.exit_requested and not g.abort_requested():
            xbmc.sleep(1000)
            self.update_download_info()
            self._populate_menu_items()

    def _cancel_download(self, position):
        response = xbmcgui.Dialog().contextmenu([g.get_language_string(30070), g.get_language_string(30459)])
        if response == 0 and position > -1:
            self.manager.cancel_task(self.list_control.getListItem(position).getProperty('hash'))

    def close(self):
        self.exit_requested = True
        super().close()

    def handle_action(self, action_id, control_id=None):
        position = self.list_control.getSelectedPosition()
        # sourcery skip: merge-duplicate-blocks
        if action_id == 7:
            if control_id == 2001:
                self.manager.clear_complete()
            elif control_id == 2999:
                self.close()
            elif control_id == 2003:
                self._cancel_download(position)
        elif action_id == 117 and control_id == 2003:
            self._cancel_download(position)
