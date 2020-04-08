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
        self.setProperty('test.pattern', os.path.join(tools.IMAGES_PATH, 'test_pattern.png'))
        self.setProperty('skin.dir', SkinManager().confirm_skin_path(xml_file)[1])

        if actionArgs is None:
            return

        self.item_information = tools.get_item_information(actionArgs)

        for id, value in self.item_information['ids'].items():
            self.setProperty('item.ids.%s_id' % id, str(value))

        for i in self.item_information['art'].keys():
            self.setProperty('item.art.%s' % i, str(self.item_information['art'][i]))

        self.item_information['info'] = tools.clean_air_dates(self.item_information['info'])

        year, month, day = self.item_information['info'].get('aired', '0000-00-00').split('-')

        self.setProperty('item.info.aired.year', year)
        self.setProperty('item.info.aired.month', month)
        self.setProperty('item.info.aired.day', day)

        try:
            if 'aired' in self.item_information['info']:
                aired_date = self.item_information['info']['aired']
                aired_date = tools.datetime_workaround(aired_date)
                aired_date = aired_date.strftime(tools.get_region('dateshort'))
                self.item_information['info']['aired'] = aired_date
                
            if 'premiered' in self.item_information['info']:
                premiered = self.item_information['info']['premiered']
                premiered = tools.datetime_workaround(premiered)
                premiered = premiered.strftime(tools.get_region('dateshort'))
                self.item_information['info']['premiered'] = premiered
        except:
            pass

        for i in self.item_information['info'].keys():
            value = self.item_information['info'][i]
            if i == 'aired' or i == 'premiered':
                try:
                    value = value[:10]
                except:
                    value = 'TBA'
            if i == 'duration':
                try:
                    hours, minutes = divmod(value, 60 * 60)
                    self.setProperty('item.info.%s.minutes' % i, str(minutes // 60))
                    self.setProperty('item.info.%s.hours' % i, str(hours))
                except:
                    pass
            try:
                self.setProperty('item.info.%s' % i, str(value))
            except UnicodeEncodeError:
                self.setProperty('item.info.%s' % i, value)
