import xbmc
import xbmcgui

from resources.lib.database.providerCache import ProviderCache
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g
from resources.lib.modules.providers.install_manager import ProviderInstallManager
from resources.lib.modules.providers.settings import SettingsManager


class PackageConfiguration(BaseWindow):
    providers_class = ProviderInstallManager()

    def __init__(self, xml_file, xml_location, package_name):
        super(PackageConfiguration, self).__init__(xml_file, xml_location)
        self.providers = self.providers_class.known_providers

        self.manager = SettingsManager()
        self.providerCache = ProviderCache()

        self.package_name = package_name
        self.settings = []
        self.provider_list = None
        self.settings_list = None

    def onInit(self):
        self.settings_list = self.getControlList(1000)
        self.provider_list = self.getControlList(2000)

        self.update_settings()
        self.fill_providers()
        self.setProperty("package.name", self.package_name)
        self.setProperty(
            "hassettings", "true" if self.settings_list.size() > 0 else "false"
        )

        self.set_default_focus(self.provider_list, 2999, control_list_reset=True)
        super(PackageConfiguration, self).onInit()

    def refresh_data(self):
        self.providers_class.poll_database()
        self.providers = self.providers_class.known_providers
        self.update_settings()

    @staticmethod
    def _set_setting_item_properties(menu_item, setting):
        value = g.UNICODE(setting["value"])
        if setting["definition"].get("sensitive"):
            value = "*******"
        menu_item.setProperty("Label", setting["label"])
        menu_item.setProperty("value", value)

    def _populate_settings(self):
        def create_menu_item(setting):
            new_item = xbmcgui.ListItem(label="{}".format(setting["label"]))
            self._set_setting_item_properties(new_item, value)
            return new_item

        if len(self.settings) < self.settings_list.size():
            while len(self.settings) < self.settings_list.size():
                self.settings_list.removeItem(self.settings_list.size() - 1)

        for idx, value in enumerate(self.settings):
            try:
                menu_item = self.settings_list.getListItem(idx)
                self._set_setting_item_properties(menu_item, value)
            except RuntimeError:
                menu_item = create_menu_item(value)
                self.settings_list.addItem(menu_item)

    def fill_providers(self):
        self.refresh_data()
        self.provider_list.reset()

        provider_types = self.providers_class.provider_types
        for provider_type in provider_types:
            for i in [
                provider
                for provider in self.providers
                if provider["package"] == self.package_name
                and provider["provider_type"] == provider_type
            ]:
                item = xbmcgui.ListItem(label=i["provider_name"])
                for info in i:
                    item.setProperty(info, i[info])

                self.provider_list.addItem(item)

    def update_settings(self):
        self.settings = [
            i
            for i in reversed(
                self.manager.get_all_visible_package_settings(self.package_name)
            )
        ]
        self._populate_settings()

    def flip_provider_status(self):
        provider_item = self.provider_list.getSelectedItem()
        new_status = self.providers_class.flip_provider_status(
            provider_item.getProperty("package"), provider_item.getLabel()
        )

        provider_item.setProperty("status", new_status)
        self.providers = self.providerCache.get_providers()

    def flip_mutliple_providers(self, status, provider_type=None):
        g.show_busy_dialog()
        providers = [i for i in self.providers if i["package"] == self.package_name]

        if provider_type:
            providers = [i for i in providers if i["provider_type"] == provider_type]

        for i in providers:
            self.providers_class.flip_provider_status(
                i["package"], i["provider_name"], status
            )

        self.providers = self.providerCache.get_providers()
        self.fill_providers()

        self.set_default_focus(self.provider_list, 3000)
        g.close_busy_dialog()

    def handle_action(self, action, control_id=None):
        if action == 7:
            if control_id == 1000:
                position = self.settings_list.getSelectedPosition()
                self._edit_setting(self.settings[position])
            elif control_id == 2000:
                self.flip_provider_status()
            elif control_id == 2999:
                self.close()
            elif control_id in {3001, 3002, 3003, 3004, 3005, 3006}:
                options = {
                    3001: ("enabled", "hosters"),
                    3002: ("enabled", "torrent"),
                    3003: ("disabled", "hosters"),
                    3004: ("disabled", "torrent"),
                    3005: ("enabled", None),
                    3006: ("disabled", None),
                }

                option = options.get(control_id)
                self.flip_mutliple_providers(option[0], provider_type=option[1])

    def _edit_setting(self, setting):
        keyboard = xbmc.Keyboard("", setting.get("label"))
        keyboard.doModal()
        if keyboard.isConfirmed():
            try:
                self.manager.set_setting(
                    self.package_name,
                    setting["id"],
                    self.manager.settings_template[setting["type"]]["cast"](
                        keyboard.getText()
                    ),
                )
                self.update_settings()
            except TypeError:
                xbmcgui.Dialog().ok(g.ADDON_NAME, "The setting value was invalid")
