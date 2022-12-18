from resources.lib.database.providerCache import ProviderCache
from resources.lib.modules.globals import g


class SettingsManager(ProviderCache):
    settings_template = {
        "str": {
            "default": "",
            "cast": str,
        },
        "int": {"default": 0, "cast": int},
        "bool": {"default": False, "cast": bool},
    }

    def __init__(self):
        self._setting_store = {}
        super().__init__()

    def create_settings(self, package_name, settings):
        self.execute_sql(
            self.package_setting_insert_query, [self._parse_new_setting(package_name, setting) for setting in settings]
        )

    def _parse_new_setting(self, package_name, setting):
        try:
            setting_id = setting['id']
            setting_type = setting['type']
        except KeyError as e:
            g.log(f'Failed to create provider setting - {setting}')
            raise e

        visible = 1 if setting.get('visible', False) else 0
        label = setting.get('label', '')
        value = setting.get('default', self.settings_template[setting_type]['default'])
        return package_name, setting_id, setting_type, visible, value, label, setting

    def remove_package_settings(self, package_name):
        self.execute_sql('DELETE FROM package_settings WHERE package=?', (package_name,))

    def _cast_setting(self, setting, forced_value=None):
        if setting["type"] == "bool":
            setting["value"] = setting["value"] == "True"

        return self.settings_template[setting["type"]]["cast"](
            forced_value if forced_value is not None else setting["value"]
        )

    def get_setting(self, package_name, setting_id):
        setting = self._get_package_setting(package_name, setting_id)
        return self._cast_setting(setting)

    def get_all_package_settings(self, package):
        return self.fetchall("SELECT * FROM package_settings WHERE package=?", (package,))

    def get_all_visible_package_settings(self, package):
        return self.fetchall("SELECT * FROM package_settings WHERE package=? AND visible=1", (package,))

    def set_setting(self, package_name, setting_id, value):
        setting = self._get_package_setting(package_name, setting_id)
        value = self._cast_setting(setting, forced_value=value)
        self._set_package_setting(package_name, setting_id, str(value))
