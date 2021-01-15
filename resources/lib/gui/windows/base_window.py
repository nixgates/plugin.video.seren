# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import abc
import os
from copy import deepcopy

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.database.skinManager import SkinManager
from resources.lib.modules.globals import g

ACTION_PREVIOUS_MENU = 10
ACTION_PLAYER_STOP = 13
ACTION_NAV_BACK = 92


class BaseWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, xml_file, location, item_information=None):
        xbmcgui.WindowXMLDialog.__init__(self, xml_file, location)
        self.item_information = {}
        self.action_exitkeys_id = [ACTION_PREVIOUS_MENU,
                                   ACTION_PLAYER_STOP,
                                   ACTION_NAV_BACK]
        self.canceled = False

        self.setProperty('texture.white', os.path.join(g.IMAGES_PATH, 'white.png'))
        self.setProperty('seren.logo', os.path.join(g.IMAGES_PATH, 'logo-seren-2.png'))
        self.setProperty('seren.fanart', g.DEFAULT_FANART)
        self.setProperty('settings.color', g.get_user_text_color())
        self.setProperty('test.pattern', os.path.join(g.IMAGES_PATH, 'test_pattern.png'))
        self.setProperty('skin.dir', SkinManager().confirm_skin_path(xml_file)[1])

        if item_information is None:
            return

        self.add_item_information_to_window(item_information)

    def onInit(self):
        persistent_list = xbmcgui.ControlList(-100, -100, 0, 0)
        self.addControl(persistent_list)
        persistent_list.addItem(self.get_list_item_with_properties(self.item_information))
        self.setFocusId(persistent_list.getId())

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
            g.log('Control does not exist {}'.format(control_id), 'error')
            g.log(e)
        if not isinstance(control, xbmcgui.ControlList):
            raise AttributeError("Control with Id {} should be of type ControlList".format(control_id))

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
            raise AttributeError("Control with Id {} should be of type ControlProgress".format(control_id))

        return control

    def add_id_properties(self):
        id_dict = {}
        [id_dict.update({i.split('_')[0]: self.item_information['info'][i]})
         for i in self.item_information['info'].keys() if i.endswith('id')]
        for id, value in id_dict.items():
            self.setProperty('item.ids.{}_id'.format(id), str(value))

    def add_art_properties(self):
        for i in self.item_information['art'].keys():
            self.setProperty('item.art.{}'.format(i), str(self.item_information['art'][i]))

    def add_date_properties(self):
        try:
            try:
                year, month, day = self.item_information['info'].get('aired', '0000-00-00').split('-')
            except ValueError:
                year, month, day = self.item_information['info'].get('aired', '00/00/0000').split('/')

            self.setProperty('item.info.aired.year', year)
            self.setProperty('item.info.aired.month', month)
            self.setProperty('item.info.aired.day', day)
        except ValueError:
            pass

        if 'aired' in self.item_information['info']:
            aired_date = self.item_information['info']['aired']
            aired_date = tools.parse_datetime(aired_date, tools.DATE_FORMAT)
            aired_date = aired_date.strftime(xbmc.getRegion('dateshort'))
            try:
                aired_date = aired_date[:10]
            except IndexError:
                aired_date = "TBA"
            self.setProperty('item.info.premiered', str(aired_date))

        if 'premiered' in self.item_information['info']:
            premiered = self.item_information['info']['premiered']
            premiered = tools.parse_datetime(premiered, tools.DATE_FORMAT)
            premiered = premiered.strftime(xbmc.getRegion('dateshort'))
            try:
                premiered = premiered[:10]
            except IndexError:
                premiered = "TBA"
            self.setProperty('item.info.premiered', str(premiered))

    def add_info_properties(self):
        for i in self.item_information['info'].keys():
            value = self.item_information['info'][i]
            if i == 'aired' or i == 'premiered':
                continue
            if i == 'duration':
                hours, minutes = divmod(value, 60 * 60)
                self.setProperty('item.info.{}.minutes'.format(i), str(minutes // 60))
                self.setProperty('item.info.{}.hours'.format(i), str(hours))
            try:
                self.setProperty('item.info.{}'.format(i), str(value))
            except UnicodeEncodeError:
                self.setProperty('item.info.{}'.format(i), value)

    def add_item_information_to_window(self, item_information):
        self.item_information = deepcopy(item_information)
        self.add_id_properties()
        self.add_art_properties()
        self.add_date_properties()
        self.add_info_properties()

    def onAction(self, action):
        action_id = action.getId()
        if action_id in self.action_exitkeys_id:
            self.close()
            return
        elif action != 7:
            self.handle_action(action_id)

    @abc.abstractmethod
    def handle_action(self, action_id, control_id=None):
        """
        Handles interactions on window
        :param action_id: int - ID of action taken
        :param control_id: int - ID of control action performed on
        :return:
        """
