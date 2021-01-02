# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.database.providerCache import ProviderCache
from resources.lib.modules.globals import g


class SettingsManager(ProviderCache):
    settings_template = {
        'string': {
            'default': '',
            'cast': str,
        },
        'int': {
            'default': 0,
            'cast': int
        }
    }

    def __init__(self):
        self._setting_store = {}
        super(SettingsManager, self).__init__()

    def create_settings(self, package_name, settings):
        self.execute_sql(self.package_setting_insert_query, [self._parse_new_setting(package_name, setting)
                                                             for setting in settings])

    def _parse_new_setting(self, package_name, setting):
        try:
            setting_id = setting['id']
            setting_type = setting['type']
        except KeyError as e:
            g.log('Failed to create provider setting - {}'.format(setting))
            raise e

        visible = 1 if setting.get('visible', False) else 0
        label = setting.get('label', '')
        value = setting.get('default', self.settings_template[setting_type]['default'])
        return package_name, setting_id, setting_type, visible, value, label, setting

    def remove_package_settings(self, package_name):
        self.execute_sql('DELETE FROM package_settings WHERE package=?', (package_name,))

    def _cast_setting(self, setting, forced_value=None):
        return self.settings_template[setting['type']]['cast'](setting['value'] if not forced_value else forced_value)

    def get_setting(self, package_name, setting_id):
        setting = self._get_package_setting(package_name, setting_id)
        return self._cast_setting(setting)

    def get_all_package_settings(self, package):
        return self.execute_sql("SELECT * FROM package_settings WHERE package=?", (package,)).fetchall()

    def get_all_visible_package_settings(self, package):
        return self.execute_sql("SELECT * FROM package_settings WHERE package=? AND visible=1", (package,)).fetchall()

    def set_setting(self, package_name, setting_id, value):
        setting = self._get_package_setting(package_name, setting_id)
        self._cast_setting(setting, forced_value=value)
        self._set_package_setting(package_name, setting_id, str(value))
