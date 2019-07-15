from resources.lib.common import tools
from resources.lib.modules import customProviders
from resources.lib.modules import database

import os

class CustomProviders(tools.dialogWindow):

    installed_providers = database.get_providers()
    installed_packages = database.get_provider_packages()
    provider_packages = list(set(['%s' % pack['pack_name'] for pack in installed_packages]))
    package_display_strings = list(set(['%s - %s' % (pack['pack_name'], pack['version'])
                                        for pack in installed_packages]))


    def __init__(self):

        # Window Base
        texture_path = os.path.join(tools.IMAGES_PATH, 'texture.png')
        self.texture = tools.imageControl(0, 0, 1280, 720, texture_path)
        self.addControl(self.texture)

        self.background = tools.imageControl(0, 0, 1280, 720, '')
        background_diffuse = '0x1FFFFFFF'
        self.background.setColorDiffuse(background_diffuse)
        self.addControl(self.background)

        #################
        # Window Items  #
        #################

        # Package Display
        self.package_list_control = tools.listControl(20, 130, 480, 640, 'font12', '0xFFFFFFFF', '',
                                                      os.path.join(tools.IMAGES_PATH, 'highlight11.png'),
                                                      '', 0, 0, 0, 0, 30)
        self.addControl(self.package_list_control)
        self.package_list_control.addItems(self.package_display_strings)

        # Package Providers Display
        self.provider_list_control = tools.listControl(20, 130, 480, 640, 'font12', '0xFFFFFFFF', '',
                                                      os.path.join(tools.IMAGES_PATH, 'highlight11.png'),
                                                      '', 0, 0, 0, 0, 30)
        self.addControl(self.provider_list_control)
        self.providers_display = []
        self.package_title = ''
        self.providers_title = ''
        self.setFocus(self.package_list_control)
        pass

    def onAction(self, action):

        id = action.getId()
        if id == 92 or id == 10:
            self.close()
            self.close()

        if id == 7:
            self.close()

        if id == 0:
            pass

    def doModal(self):
        tools.kodiGui.WindowDialog.doModal(self)
        self.clearProperties()
        return

    def onControl(self, control):
        if self.source_list.getId() == control.getId():
            self.close()

    def disable_provider(self):
        pass

    def enable_provider(self):
        pass

