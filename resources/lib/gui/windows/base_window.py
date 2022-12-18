import abc
from copy import deepcopy

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.database.skinManager import SkinManager
from resources.lib.modules.globals import g
from resources.lib.modules.providers.install_manager import ProviderInstallManager

ACTION_PREVIOUS_MENU = 10
ACTION_PLAYER_STOP = 13
ACTION_NAV_BACK = 92


class BaseWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, xml_file, location, item_information=None):
        super().__init__(xml_file, location)
        self.item_information = {}
        self.action_exitkeys_id = {
            ACTION_PREVIOUS_MENU,
            ACTION_PLAYER_STOP,
            ACTION_NAV_BACK,
        }
        self.canceled = False
        self.provider_class = ProviderInstallManager()

        self.setProperty('texture.white', f"{g.IMAGES_PATH}white.png")
        self.setProperty('seren.logo', g.DEFAULT_LOGO)
        self.setProperty('seren.fanart', g.DEFAULT_FANART)
        self.setProperty('settings.color', g.get_user_text_color())
        self.setProperty('test.pattern', f"{g.IMAGES_PATH}test_pattern.png")
        self.setProperty('skin.dir', SkinManager().confirm_skin_path(xml_file)[1])

        if item_information is None:
            return

        self.add_item_information_to_window(item_information)

    def onInit(self):
        g.close_busy_dialog()

    def set_default_focus(self, control_list=None, control_id=None, control_list_reset=False):
        """
        Set the focus on a control
        :param control_list: A control list object
        :type control_list: xbmcgui.ControlList
        :param control_id: A control ID to set focus on if the control list is None or has a 0 length.
                           Can be used as a fallback for empty control lists.
        :type control_id: int
        :param control_list_reset: True if the control list object should be reset to item 0. Default: False
        :return:
        """
        control_to_focus = None

        if control_list is not None and control_list.size() > 0:
            control_to_focus = control_list
        elif control_id is not None:
            try:
                control_to_focus = self.getControl(control_id)
            except RuntimeError:
                pass  # Not all controls have a python API type.

        if isinstance(control_to_focus, xbmcgui.ControlList) and control_list_reset and control_list.size() > 0:
            control_to_focus.selectItem(0)

        if control_to_focus is not None:
            self.setFocus(control_to_focus)
        elif control_id is not None:
            self.setFocusId(control_id)
        else:
            g.log("Could not identify a control to focus", "debug")

    @staticmethod
    def get_list_item_with_properties(item_information, label=''):
        item_information = deepcopy(item_information)
        return g.add_directory_item(label, menu_item=item_information, bulk_add=True)[1]

    def getControlList(self, control_id):
        """Get and check the control for the ControlList type.

        :param control_id: Control id to get nd check for ControlList
        :type control_id: int
        :return: The checked control
        :rtype: xbmcgui.ControlList
        """
        try:
            control = self.getControl(control_id)
        except RuntimeError as e:
            g.log(f'Control does not exist {control_id}', 'error')
            g.log(e)
        if not isinstance(control, xbmcgui.ControlList):
            raise AttributeError(f"Control with Id {control_id} should be of type ControlList")

        return control

    def getControlProgress(self, control_id):
        """Get and check the control for the ControlProgress type.

        :param control_id: Control id to get nd check for ControlProgress
        :type control_id: int
        :return: The checked control
        :rtype: xbmcgui.ControlProgress
        """
        control = self.getControl(control_id)
        if not isinstance(control, xbmcgui.ControlProgress):
            raise AttributeError(f"Control with Id {control_id} should be of type ControlProgress")

        return control

    def add_id_properties(self):
        id_dict = {k: self.item_information["info"][k] for k in self.item_information["info"] if k.endswith("_id")}

        for key, value in id_dict.items():
            self.setProperty(f"item.ids.{key}", str(value))

    def add_art_properties(self):
        for i in self.item_information['art']:
            self.setProperty(f'item.art.{i}', str(self.item_information['art'][i]))

    def add_date_properties(self):
        info = deepcopy(self.item_information['info'])
        media_type = info.get("mediatype", None)
        if media_type in [g.MEDIA_SHOW, g.MEDIA_SEASON, g.MEDIA_EPISODE]:
            # Convert dates to localtime for display
            g.convert_info_dates(info)
        try:
            year, month, day = self.item_information['info'].get('aired', '0000-00-00').split('-')

            self.setProperty('item.info.aired.year', year)
            self.setProperty('item.info.aired.month', month)
            self.setProperty('item.info.aired.day', day)
        except ValueError:
            pass

        if 'aired' in info:
            aired_date = info['aired']
            aired_date = tools.parse_datetime(aired_date)
            aired_date = aired_date.strftime(xbmc.getRegion('dateshort'))
            try:
                aired_date = aired_date[:10]
            except IndexError:
                aired_date = "TBA"
            self.setProperty('item.info.aired', aired_date)

        if 'premiered' in info:
            premiered = info['premiered']
            premiered = tools.parse_datetime(premiered)
            premiered = premiered.strftime(xbmc.getRegion('dateshort'))
            try:
                premiered = premiered[:10]
            except IndexError:
                premiered = "TBA"
            self.setProperty('item.info.premiered', premiered)

    def add_info_properties(self):
        for i in self.item_information['info']:
            value = self.item_information['info'][i]
            if i in ['aired', 'premiered']:
                continue
            if i == 'duration':
                hours, minutes = divmod(value, 60 * 60)
                self.setProperty(f'item.info.{i}.minutes', str(minutes // 60))
                self.setProperty(f'item.info.{i}.hours', str(hours))
            try:
                self.setProperty(f'item.info.{i}', str(value))
            except UnicodeEncodeError:
                self.setProperty(f'item.info.{i}', value)

    def add_item_information_to_window(self, item_information):
        self.item_information = deepcopy(item_information)
        self.add_id_properties()
        self.add_art_properties()
        self.add_date_properties()
        self.add_info_properties()

    def onClick(self, control_id):
        """
        Callback from kodi when a click event occurs in dialog
        :param control_id: control the click was perfomed on
        :type control_id: int
        :return: None
        :rtype: none
        """
        self.handle_action(7, control_id)

    def onAction(self, action):
        action_id = action.getId()
        if action_id in self.action_exitkeys_id:
            self.close()
            return
        if action_id != 7:  # Enter(7) also fires an onClick event
            self.handle_action(action_id, self.getFocusId())

    @abc.abstractmethod
    def handle_action(self, action_id, control_id=None):
        """
        Handles interactions on window
        :param action_id: int - ID of action taken
        :param control_id: int - ID of control action performed on
        :return:
        """
