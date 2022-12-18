import xbmcgui

from resources.lib.database.providerCache import ProviderCache
from resources.lib.database.skinManager import SkinManager
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.gui.windows.configure_provider_package import PackageConfiguration
from resources.lib.modules.globals import g


class ProviderPackages(BaseWindow):
    def __init__(self, xml_file, xml_location):
        super().__init__(xml_file, xml_location)
        self.packages = self.provider_class.known_packages
        self.providers = self.provider_class.known_providers
        self.package_list = None
        self.providerCache = ProviderCache()

    def onInit(self):
        self.package_list = self.getControlList(1000)
        self.fill_packages()

        self.set_default_focus(self.package_list, 2999, control_list_reset=True)
        super().onInit()

    def refresh_data(self):
        self.provider_class.poll_database()
        self.packages = self.provider_class.known_packages

    def fill_packages(self):
        self.refresh_data()
        self.package_list.reset()
        for i in self.packages:
            item = xbmcgui.ListItem(label=i["pack_name"])
            provider_imports = (
                '.'.join(["providers", i["pack_name"], "", ""]),
                None,
                i["pack_name"],
            )
            package_icon = self.provider_class.get_icon(provider_imports)
            if package_icon is not None:
                item.setProperty(
                    "package.icon",
                    package_icon,
                )
            for info in i:
                item.setProperty(info, i[info])
            self.package_list.addItem(item)

    @staticmethod
    def _configure_package(package):
        try:
            window = PackageConfiguration(
                *SkinManager().confirm_skin_path('configure_provider_package.xml'), package_name=package
            )
            window.doModal()
        finally:
            del window

    def flip_mutliple_providers(self, status, package_name):

        g.show_busy_dialog()
        providers = [i for i in self.providers if i['package'] == package_name]

        for i in providers:
            self.provider_class.flip_provider_status(i['package'], i['provider_name'], status)

        self.providers = self.providerCache.get_providers()

        g.close_busy_dialog()

    def handle_action(self, action, control_id=None):
        selected_item = self.package_list.getSelectedItem()
        package_name = selected_item.getLabel() if selected_item is not None else ""
        if action == 117:
            enabled = any(p["status"] == "enabled" for p in [i for i in self.providers if i["package"] == package_name])

            response = xbmcgui.Dialog().contextmenu(
                [
                    g.get_language_string(30475),
                    g.get_language_string(30241) if enabled else g.get_language_string(30240),
                    g.get_language_string(30239),
                ]
            )
            if response == 0:
                self._configure_package(package_name)
            elif response == 1:
                self.flip_mutliple_providers('disabled' if enabled else 'enabled', selected_item.getLabel())
            elif response == 2:
                g.show_busy_dialog()
                try:
                    confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30267).format(package_name))
                    if not confirm:
                        g.close_busy_dialog()
                        return

                    self.provider_class.uninstall_package(package=package_name)
                    self.packages = self.providerCache.get_provider_packages()
                    self.fill_packages()
                    self.set_default_focus(self.package_list, 2999)
                finally:
                    g.close_busy_dialog()

        if action == 7:
            if control_id == 1000:
                self._configure_package(package_name)
            elif control_id == 2999:
                self.close()
            elif control_id == 2002:
                g.show_busy_dialog()
                try:
                    self.provider_class.install_package(None)
                    self.packages = self.providerCache.get_provider_packages()
                    self.fill_packages()
                    self.set_default_focus(self.package_list, 2000)
                finally:
                    g.close_busy_dialog()
