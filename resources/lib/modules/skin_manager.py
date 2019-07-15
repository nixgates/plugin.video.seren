# -*- coding: utf-8 -*-

from resources.lib.common import tools

import os

class SkinManager:

    def __init__(self):

        if not os.path.exists(tools.SKINS_PATH):
            os.mkdir(tools.SKINS_PATH)

        self.installed_skins = [i for i in os.listdir(tools.SKINS_PATH) if
                                os.path.isdir(os.path.join(tools.SKINS_PATH, i))]


    def install_skin(self):
        pass

    def _get_install(self):
        install_type = tools.showDialog.select(tools.addonName, ['Browse', 'Web Location'])


