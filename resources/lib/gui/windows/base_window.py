__metaclass__ = type

import os

from resources.lib.common import tools
from resources.lib.modules.skin_manager import SkinManager

class BaseWindow(tools.xmlWindow):

    def __init__(self, xml_file, location, actionArgs=None):

        try:
            super(BaseWindow, self).__init__(xml_file, location)
        except:
            tools.xmlWindow().__init__()

        tools.closeBusyDialog()
        self.canceled = False

        self.setProperty('texture.white', os.path.join(tools.IMAGES_PATH, 'white.png'))
        self.setProperty('seren.logo', tools.SEREN_LOGO_PATH)
        self.setProperty('seren.fanart', tools.SEREN_FANART_PATH)
        self.setProperty('settings.color', tools.get_user_text_color())
        self.setProperty('test_pattern', os.path.join(tools.IMAGES_PATH, 'test_pattern.png'))
        self.setProperty('skin.dir', os.path.join(SkinManager().active_skin_path))

        if actionArgs is None:
            return

        self.item_information = tools.get_item_information(actionArgs)

        for i in self.item_information['art'].keys():
            self.setProperty('item.art.%s' % i, str(self.item_information['art'][i]))

        for i in self.item_information['info'].keys():
            value = self.item_information['info'][i]
            if i == 'aired' or i == 'premiered':
                value = value[:10]
            try:
                self.setProperty('item.info.%s' % i, str(value))
            except UnicodeEncodeError:
                self.setProperty('item.info.%s' % i, value)
