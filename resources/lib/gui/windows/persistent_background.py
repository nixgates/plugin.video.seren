import os

from resources.lib.common import tools
from resources.lib.gui.windows.base_window import BaseWindow

class PersistentBackground(BaseWindow):

    def __init__(self, xml_file, location, actionArgs=None):
        super(BaseWindow, self).__init__(xml_file, location)
        if actionArgs is None:
            return

        tools.closeBusyDialog()

        self.canceled = False
        self.item_information = tools.get_item_information(actionArgs)

        self.setProperty('texture.white', os.path.join(tools.IMAGES_PATH, 'white.png'))
        self.setProperty('seren.logo', tools.SEREN_LOGO_PATH)
        self.setProperty('settings.color', tools.get_user_text_color())
        self.setProperty('test_pattern', os.path.join(tools.IMAGES_PATH, 'test_pattern.png'))

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

    def setText(self, text):
        self.setProperty('notification_text', str(text))