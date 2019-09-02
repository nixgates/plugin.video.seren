from resources.lib.common import tools
from resources.lib.modules import customProviders
from resources.lib.modules import database
from resources.lib.gui.windows.base_window import BaseWindow


class CustomProviders(BaseWindow):
    providers_class = customProviders.providers()

    def __init__(self, xml_file, xml_location):
        super(CustomProviders, self).__init__(xml_file, xml_location)
        self.packages = self.providers_class.known_packages
        self.providers = self.providers_class.known_providers
        self.package_list = None
        self.provider_list = None
        pass

    def onInit(self):
        tools.closeBusyDialog()
        self.provider_list = self.getControl(2001)
        self.package_list = self.getControl(2000)

        self.fill_packages()
        self.fill_providers(self.package_list.getSelectedItem().getLabel())
        self.setFocus(self.package_list)

    def refresh_data(self):
        self.providers_class.poll_database()
        self.providers = self.providers_class.known_providers
        self.packages = self.providers_class.known_packages

    def fill_packages(self):
        self.refresh_data()
        self.package_list.reset()
        for i in self.packages:
            item = tools.menuItem(label=i['pack_name'])
            for info in i.keys():
                item.setProperty(info, i[info])
            self.package_list.addItem(item)

    def fill_providers(self, package_name=None):
        self.refresh_data()
        self.provider_list.reset()
        if package_name is None:
            self.provider_list.reset()
        provider_types = ['torrent', 'hosters']

        for provider_type in provider_types:

            for i in [provider for provider in self.providers
                      if provider['package'] == package_name
                      and provider['provider_type'] == provider_type]:

                item = tools.menuItem(label=i['provider_name'])
                for info in i.keys():
                    item.setProperty(info, i[info])

                self.provider_list.addItem(item)

    def flip_provider_status(self):
        provider_item = self.provider_list.getSelectedItem()
        new_status = self.providers_class.flip_provider_status(provider_item.getProperty('package'),
                                                               provider_item.getLabel())

        provider_item.setProperty('status', new_status)
        self.providers = database.get_providers()

    def flip_mutliple_providers(self, status, provider_type=None, package_name=None):

        tools.showBusyDialog()
        providers = self.providers

        if package_name:
            providers = [i for i in providers if i['package'] == package_name]

        if provider_type:
            providers = [i for i in providers if i['provider_type'] == provider_type]

        for i in providers:
            self.providers_class.flip_provider_status(i['package'], i['provider_name'], status)

        self.providers = database.get_providers()
        self.fill_providers(self.package_list.getSelectedItem().getLabel())

        tools.closeBusyDialog()

    def onClick(self, control_id):

        self.handle_action(7)

    def handle_action(self, action):

        focus_id = self.getFocusId()

        if (action == 4 or action == 3 or action == 7) and focus_id == 2000:
            # UP/ DOWN
            self.fill_providers(self.package_list.getSelectedItem().getLabel())

        if action == 92 or action == 10:
            # BACKSPACE / ESCAPE
            self.close()

        if action == 7:
            if focus_id == 2001:
                self.flip_provider_status()
            if focus_id == 3001:
                self.flip_mutliple_providers('enabled', provider_type='hosters')
            if focus_id == 3002:
                self.flip_mutliple_providers('enabled', provider_type='torrent')
            if focus_id == 3003:
                self.flip_mutliple_providers('disabled', provider_type='hosters')
            if focus_id == 3004:
                self.flip_mutliple_providers('disabled', provider_type='torrent')
            if focus_id == 3005:
                self.flip_mutliple_providers('enabled')
            if focus_id == 3006:
                self.flip_mutliple_providers('disabled')
            if focus_id == 3007:
                self.flip_mutliple_providers('enabled', package_name=self.package_list.getSelectedItem().getLabel())
            if focus_id == 3008:
                self.flip_mutliple_providers('disabled', package_name=self.package_list.getSelectedItem().getLabel())
            if focus_id == 3009:
                tools.showBusyDialog()

                self.providers_class.install_package(None)
                self.packages = database.get_provider_packages()
                self.fill_packages()
                try:
                    current_package = self.package_list.getSelectedItem().getLabel()
                    self.fill_providers(current_package)
                except:
                    self.provider_list.reset()
                    pass
                tools.closeBusyDialog()
                self.setFocus(self.package_list)
            if focus_id == 3010:
                try: package = self.package_list.getSelectedItem().getLabel()
                except:
                    return
                tools.showBusyDialog()
                confirm = tools.showDialog.yesno(tools.addonName, tools.lang(40255) % package)
                if not confirm:
                    tools.closeBusyDialog()
                    return

                self.providers_class.uninstall_package(package=self.package_list.getSelectedItem().getLabel(),
                                                       silent=True)
                self.packages = database.get_provider_packages()
                self.fill_packages()
                self.fill_providers()
                tools.closeBusyDialog()
                self.setFocus(self.package_list)
            pass

        if action == 0:
            pass

    def onAction(self, action):

        action = action.getId()

        if action == 2 and self.getFocusId() == 2000:
            self.fill_providers(self.package_list.getSelectedItem().getLabel())
            return

        if action == 7:
            return
        self.handle_action(action)

    def doModal(self):
        super(CustomProviders, self).doModal()
        self.clearProperties()
        return

    def onControl(self, control):
        if self.source_list.getId() == control.getId():
            self.close()

    def disable_provider(self):
        pass

    def enable_provider(self):
        pass
