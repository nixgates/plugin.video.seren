# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os

import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.globals import g


class SettingsHelper:
    def __init__(self):
        """SettingsHelper class."""
        self.valid_settings = {}
        self.current_user_settings = {}
        self.removed_settings = []
        self.added_settings = []
        self._load_default_settings()
        self._load_user_settings()

    def _load_default_settings(self):
        settings_config_file = os.path.join(
            g.ADDON_DATA_PATH, "resources", "settings.xml"
        )
        xml = tools.ElementTree.parse(settings_config_file)
        settings = xml.findall(".//setting")
        for node in settings:
            setting_id = node.get("id")
            if setting_id is None:
                continue
            setting_default = node.get("default")
            dict_item = {"id": setting_id}
            if setting_default is not None:
                dict_item["value"] = setting_default
            self.valid_settings.update({setting_id: dict_item})

    def _load_user_settings(self):
        current_settings_file = os.path.join(g.SETTINGS_PATH)
        if not xbmcvfs.exists(current_settings_file):
            self.create_and_clean_settings()
            self.save_settings()
        xml = tools.ElementTree.parse(current_settings_file)
        settings = xml.findall("./setting")
        for node in settings:
            setting_id = node.get("id")
            if g.KODI_VERSION >= 17:
                setting_value = node.text
            else:
                setting_value = node.get("value")
            item = {"id": setting_id}
            if setting_value:
                item["value"] = setting_value
            self.current_user_settings.update({setting_id: item})

    def create_and_clean_settings(self):
        self.removed_settings = {
            key: value
            for key, value in list(self.current_user_settings.items())
            if key not in self.valid_settings
        }
        self.added_settings = {
            key: value
            for key, value in list(self.valid_settings.items())
            if key not in self.current_user_settings
        }
        [self.current_user_settings.pop(key) for key in self.removed_settings]
        [
            self.current_user_settings.update({key: value})
            for key, value in list(self.added_settings.items())
        ]

    def save_settings(self):
        for key, value in list(self.valid_settings.items()):
            if "default" in value:
                self.current_user_settings[key]["default"] = value["default"]

        lines = self.construct_wrapper(
            [
                self.construct_line(self.current_user_settings[i])
                for i in sorted(self.current_user_settings.keys())
                if i is not None
            ]
        )
        current_settings_file = os.path.join(g.SETTINGS_PATH)
        if not xbmcvfs.exists(os.path.dirname(current_settings_file)):
            xbmcvfs.mkdirs(os.path.dirname(current_settings_file))
        new_settings_file = xbmcvfs.File(current_settings_file, "w")
        if not g.PYTHON3:
            new_settings_file.write(bytearray("\r".join(lines), encoding="utf-8"))
        else:
            new_settings_file.write(str("\r".join(lines)))
        new_settings_file.close()

    def construct_line(self, item):
        return "    <setting{}{}>{}</setting>".format(
            ' id="{}"'.format(item.get("id"))
            if item.get("id", None) is not None
            else "",
            ' default="true"' if self._is_default(item.get("value", "")) else "",
            item.get("value", item.get("default", "")),
        )

    @staticmethod
    def _is_default(value):
        if (
            not value
            or value == "0"
            or value == "false"
            or value == "None"
        ):
            return True

    def construct_wrapper(self, content):
        lines = ["<settings{}>".format(' version="2"' if g.KODI_VERSION > 17 else "")]
        lines.extend(content)
        lines.append("</settings>")
        return lines
