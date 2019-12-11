# -*- coding: utf-8 -*-

from resources.lib.common import tools
from resources.lib.common import source_utils
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.resolver import Resolver
from resources.lib.modules import database
from resources.lib.modules.skin_manager import SkinManager

class SourceSelect(BaseWindow):

    def __init__(self, xml_file, location, actionArgs=None, sources=None, **kwargs):
        super(SourceSelect, self).__init__(xml_file, location, actionArgs=actionArgs)
        self.actionArgs = actionArgs
        self.sources = sources
        self.position = -1
        self.canceled = False
        self.display_list = None
        tools.closeBusyDialog()
        self.stream_link = None

    def onInit(self):
        self.display_list = self.getControl(1000)
        menu_items = []

        for idx, i in enumerate(self.sources):
            menu_item = tools.menuItem(label=('%s) %s' % (idx + 1, i['release_title'])))
            for info in i.keys():
                try:
                    value = i[info]
                    if type(value) == list:
                        value = [str(k) for k in value]
                        value = ' '.join(sorted(value))
                    if info == 'size':
                        value = tools.source_size_display(value)
                    menu_item.setProperty(info, str(value).replace('_', ' '))
                except UnicodeEncodeError:
                    menu_item.setProperty(info, i[info])

            struct_info = source_utils.info_list_to_sorted_dict(i.get('info', []))
            for property in struct_info.keys():
                menu_item.setProperty('info.{}'.format(property), struct_info[property])

            menu_items.append(menu_item)
            self.display_list.addItem(menu_item)

        self.setFocusId(1000)

    def doModal(self):
        super(SourceSelect, self).doModal()
        return self.stream_link

    def onClick(self, controlId):

        if controlId == 1000:
            self.position = self.display_list.getSelectedPosition()
            self.resolve_item()

    def onAction(self, action):
        id = action.getId()
        if id == 92 or id == 10:
            self.stream_link = False
            self.close()

        if id == 7:
            self.position = self.display_list.getSelectedPosition()
            self.resolve_item()

        if id == 0:
            pass

    def resolve_item(self):
        if tools.getSetting('general.autotrynext') == 'true':
            sources = self.sources[self.position:]
        else:
            sources = [self.sources[self.position]]

        resolver = Resolver(*SkinManager().confirm_skin_path('resolver.xml'), actionArgs=self.actionArgs)

        self.stream_link = database.get(resolver.doModal, 1, sources,
                                        tools.get_item_information(self.actionArgs), False)

        if self.stream_link is None:
            tools.showDialog.notification(tools.addonName, tools.lang(32047), time=2000)
            return
        else:
            self.close()
