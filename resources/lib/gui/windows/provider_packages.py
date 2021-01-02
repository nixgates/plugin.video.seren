import xbmcgui

from resources.lib.database.providerCache import ProviderCache
from resources.lib.database.skinManager import SkinManager
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.gui.windows.configure_provider_package import PackageConfiguration
from resources.lib.modules.globals import g
from resources.lib.modules.providers.install_manager import ProviderInstallManager


class ProviderPackages(BaseWindow):
    providers_class = ProviderInstallManager()

    def __init__(self, xml_file, xml_location):
        BaseWindow.__init__(self, xml_file, xml_location)
        self.packages = self.providers_class.known_packages
        self.providers = self.providers_class.known_providers
        self.package_list = None
        self.providerCache = ProviderCache()

    def onInit(self):
        g.close_busy_dialog()
        self.package_list = self.getControlList(1000)

        self.fill_packages()
        self.setFocus(self.package_list)

    def refresh_data(self):
        self.providers_class.poll_database()
        self.packages = self.providers_class.known_packages

    def fill_packages(self):
        self.refresh_data()
        self.package_list.reset()
        for i in self.packages:
            item = xbmcgui.ListItem(label=i['pack_name'])
            for info in i.keys():
                item.setProperty(info, i[info])
            self.package_list.addItem(item)

    def onClick(self, control_id):
        self.handle_action(7, control_id)

    def _configure_package(self, package):
        window = PackageConfiguration(*SkinManager().confirm_skin_path('configure_provider_package.xml'),
                             package_name=package)
        window.doModal()
        del window

    def flip_mutliple_providers(self, status, package_name, provider_type=None):

        g.show_busy_dialog()
        providers = [i for i in self.providers if i['package'] == package_name]

        for i in providers:
            self.providers_class.flip_provider_status(i['package'], i['provider_name'], status)

        self.providers = self.providerCache.get_providers()

        g.close_busy_dialog()

    def handle_action(self, action, control_id=None):
        if action == 7:
            if control_id == 2001:
                self.close()
            elif control_id == 3001:
                self._configure_package(self.package_list.getSelectedItem().getLabel())
            elif control_id == 3002:
                g.show_busy_dialog()
                try:
                    self.providers_class.install_package(None)
                    self.packages = self.providerCache.get_provider_packages()
                    self.fill_packages()
                    self.setFocus(self.package_list)
                finally:
                    g.close_busy_dialog()

            elif control_id == 1000:
                self._configure_package(self.package_list.getSelectedItem().getLabel())
            elif control_id == 3003:
                package = self.package_list.getSelectedItem().getLabel()
                g.show_busy_dialog()
                try:
                    confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30293).format(package))
                    if not confirm:
                        g.close_busy_dialog()
                        return

                    self.providers_class.uninstall_package(package=self.package_list.getSelectedItem().getLabel())
                    self.packages = self.providerCache.get_provider_packages()
                    self.fill_packages()
                    self.setFocus(self.package_list)
                finally:
                    g.close_busy_dialog()
                g.close_busy_dialog()
            elif control_id == 3004:
                self.flip_mutliple_providers('enabled', self.package_list.getSelectedItem().getLabel())
            elif control_id == 3005:
                self.flip_mutliple_providers('disabled', self.package_list.getSelectedItem().getLabel())
        else:
            super(ProviderPackages, self).handle_action(action, control_id)

    def doModal(self):
        BaseWindow.doModal(self)
        self.clearProperties()
