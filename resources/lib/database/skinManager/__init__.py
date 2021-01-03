# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import collections
import json
import os
import shutil
import threading

import requests
import xbmcgui
import xbmcvfs

from resources.lib.common import tools
from resources.lib.database import Database
from resources.lib.modules.exceptions import SkinNotFoundException
from resources.lib.modules.globals import g
from resources.lib.modules.zip_manager import ZipManager

migrate_db_lock = threading.Lock()

DEFAULT_SKIN_NAME = "Seren Default"

schema = {
    "skins": {
        "columns": collections.OrderedDict(
            [
                ("skin_name", ["TEXT", "NOT NULL", "PRIMARY KEY"]),
                ("version", ["TEXT", "NOT NULL"]),
                ("author", ["TEXT", "NOT NULL"]),
                ("active", ["TEXT", "NOT NULL"]),
                ("remote_meta", ["TEXT"]),
                ("update_directory", ["TEXT"]),
            ]
        ),
        "table_constraints": ["UNIQUE(skin_name)"],
        "default_seed": [[DEFAULT_SKIN_NAME, "1.0.1", "Nixgates", "1", None, None]],
    }
}


class SkinManager(Database, ZipManager):
    """
    Class for handling of installed custom themes for Seren
    """

    def __init__(self):
        super(SkinManager, self).__init__(g.SKINS_DB_PATH, schema, migrate_db_lock)
        ZipManager.__init__(self)
        # This is a list of default skins that may not be overwritten
        self.seren_skins = [DEFAULT_SKIN_NAME]
        self.installed_skins = self._get_all_installed()
        if "Seren Fox" in [i["skin_name"] for i in self.installed_skins]:
            self.execute_sql("DELETE FROM [skins] where [skin_name] = 'Seren Fox'")
            self._mark_skin_active(DEFAULT_SKIN_NAME)
            self.installed_skins = self._get_all_installed()
        self._active_skin_path = self._get_active_skin_path()
        self._progress_dialog = xbmcgui.DialogProgress()

    # region private methods

    def _get_active_skin_path(self):
        active_skin_name = self._get_active_skin()
        if active_skin_name in self.seren_skins:
            return g.ADDON_PATH
        else:
            return os.path.join(g.ADDON_USERDATA_PATH, "skins", active_skin_name)

    def _get_active_skin(self):
        active_skin = self.execute_sql(
            "SELECT * FROM skins WHERE active = 1"
        ).fetchone()
        if active_skin is None:
            g.log("Failed to identify active skin, resetting to Default", "error")
            self.execute_sql(
                "UPDATE skins SET active=1 WHERE skin_name == ?", (DEFAULT_SKIN_NAME,)
            )
            active_skin = self.execute_sql("SELECT * FROM skins WHERE active = 1")
        return active_skin["skin_name"]

    def _is_skin_active(self, skin_name):
        return (
            self.execute_sql(
                "SELECT * FROM skins WHERE skin_name=?", (skin_name,)
            ).fetchone()["active"]
            == "1"
        )

    def _select_installed_skin(self, hide_default=False):
        installed_skins = [
            ("{} - {}".format(i["skin_name"], i["version"]), i["skin_name"])
            for i in self.installed_skins
        ]
        if hide_default:
            installed_skins.remove(
                [i for i in installed_skins if i[1] == DEFAULT_SKIN_NAME][0]
            )

        selection = xbmcgui.Dialog().select(
            g.ADDON_NAME, [i[0] for i in installed_skins]
        )

        if selection == -1:
            return

        return installed_skins[selection][1]

    def _extract_zip(self, skin_meta):
        try:
            file_path = [i for i in self._file_list if i.endswith("resources/skins/")][
                0
            ]
            file_path = file_path.split("resources/")[0]
        except IndexError:
            file_path = ""

        if "{}resources/".format(file_path) not in self._file_list:
            g.log('Theme Folder Structure Invalid: Missing folder "Resources"')
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30231))
            raise Exception

        skin_path = os.path.join(g.SKINS_PATH, skin_meta["skin_name"])
        self._extract_zip_members(
            [i for i in self._file_list if i.startswith(file_path) and i != file_path],
            skin_path,
        )
        self._destroy_created_temp_items()

    def _get_skin_meta(self):
        return json.loads(
            self._get_file_member_contents(
                [i for i in self._file_list if i.endswith("meta.json")][0]
            )
        )

    def _get_all_installed(self):
        return self.execute_sql("SELECT * FROM skins").fetchall()

    def _mark_skin_active(self, skin_name):
        self.execute_sql("UPDATE skins SET active=? WHERE active=?", ("0", "1"))
        self.execute_sql(
            "UPDATE skins SET active=? WHERE skin_name=?", ("1", skin_name)
        )
        g.set_setting(
            "skin.active",
            "{skin_name} - {version}".format(
                **self.execute_sql(
                    "SELECT skin_name, version FROM skins WHERE skin_name=?",
                    (skin_name,),
                ).fetchone()
            ),
        )
        self._active_skin_path = self._get_active_skin_path()

    def _add_skin_to_database(self, skin_meta):
        if skin_meta["skin_name"] in self.seren_skins:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30337))
            return

        update = self.execute_sql(
            "UPDATE skins SET "
            "version=?, "
            "author=?, "
            "remote_meta=?, "
            "update_directory=? "
            "WHERE skin_name=?",
            (
                skin_meta["version"],
                skin_meta["author"],
                skin_meta.get("remote_meta", None),
                skin_meta.get("update_directory", None),
                skin_meta["skin_name"],
            ),
        )

        if update.rowcount == 0:
            self.execute_sql(
                "INSERT INTO skins VALUES (?,?,?,?,?,?)",
                (
                    skin_meta["skin_name"],
                    skin_meta["version"],
                    skin_meta["author"],
                    "0",
                    skin_meta.get("remote_meta", None),
                    skin_meta.get("update_directory", None),
                ),
            )

        self.installed_skins = self._get_all_installed()


    def _remove_skin_from_database(self, skin_name):
        self.execute_sql("DELETE FROM skins WHERE skin_name=?", (skin_name,))

    @staticmethod
    def _check_skin_for_update(skin_info):

        try:
            remote_meta = requests.get(skin_info["remote_meta"]).json()
            return tools.compare_version_numbers(
                skin_info["version"], remote_meta["version"]
            )
        except:
            g.log(
                "Failed to obtain remote meta information for skin: {}".format(
                    skin_info["skin_name"]
                )
            )
            return False

    @staticmethod
    def _skin_can_update(skin_info):
        keys = ["remote_meta", "update_directory"]

        for key in keys:
            if not skin_info.get(key):
                return False
            if not skin_info[key].startswith("http"):
                return False

        return True

    # endregion

    # region public methods
    def check_for_updates(self, skin_name=None, silent=False):
        """
        Performs update check for requested theme/s
        :param skin_name: Optional name of skin to update
        :type skin_name: str
        :param silent: Optional argument to disable user feedback
        :type silent: bool
        :return: None
        :rtype: None
        """
        skins = []

        if skin_name is None:
            skins = self.installed_skins

        else:
            try:
                skins.append(
                    [i for i in self.installed_skins if i["skin_name"] == skin_name][0]
                )
            except IndexError:
                raise SkinNotFoundException(skin_name)

        if not silent:
            self._progress_dialog.create(g.ADDON_NAME, g.get_language_string(30085))
            self._progress_dialog.update(-1)

        skins = [i for i in skins if self._skin_can_update(i)]
        skins = [i for i in skins if self._check_skin_for_update(i)]

        if len(skins) == 0:
            if not silent:
                self._progress_dialog.close()
                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30084))
            return

        if not silent:
            self._progress_dialog.close()
            while skins and len(skins) > 0:
                self._progress_dialog.create(g.ADDON_NAME, g.get_language_string(30336))
                self._progress_dialog.update(-1)

                selection = xbmcgui.Dialog().select(
                    g.ADDON_NAME,
                    ["{} - {}".format(i["skin_name"], i["version"]) for i in skins],
                )
                if selection == -1:
                    return

                skin_info = skins[selection]

                try:
                    self.install_skin(skin_info["update_directory"], True)
                    skins.remove(skin_info)
                    self._progress_dialog.close()
                    xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30078))
                except Exception as e:
                    g.log_stacktrace()
                    g.log("Failed to update skin: {}".format(selection))
                    g.notification(g.ADDON_NAME, g.get_language_string(30080))
                    raise e

            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30084))
            return

        else:
            for skin in skins:
                try:
                    self.install_skin(skin["update_directory"], True)
                except Exception as e:
                    g.log("Failed to update theme: {}".format(skin["skin_name"]))
                    raise e

        g.log("Skin updates completed")

    def confirm_skin_path(self, xml_file):
        """
        Confirms xml_file for window exists and retuns a tuple for path data, if xml file does not exist, reverts to
        base theme window xml
        :param xml_file: Name of window xml_file
        :type xml_file: str
        :return: Typle (xml file name, xml file path)
        :rtype: tuple
        """
        if self._active_skin_path == g.ADDON_PATH:
            return xml_file, self._active_skin_path

        skins_folder = os.path.join(
            self._active_skin_path, "resources", "skins", "Default"
        )

        tools.makedirs(skins_folder, exist_ok=True)

        for folder in [
            folder
            for folder in os.listdir(skins_folder)
            if folder and os.path.isdir(os.path.join(skins_folder, folder))
        ]:
            if folder == "media":
                continue
            if xml_file in os.listdir(os.path.join(skins_folder, folder)):
                return xml_file, self._active_skin_path

        return xml_file, g.ADDON_PATH

    def install_skin(self, zip_location=None, silent=False):
        """
        Method to install a new theme into Seren
        :param zip_location: Optional url to fetch zip file from
        :type zip_location: str
        :param silent: Optional argument to disable user feedback
        :type silent: bool
        :return: None
        :rtype: None
        """
        self._get_zip_file(url=zip_location)

        if self._zip_file is None:
            return

        skin_meta = self._get_skin_meta()

        if skin_meta is None:
            return

        if skin_meta["skin_name"] in self.seren_skins:
            xbmcgui.Dialog().ok(
                g.ADDON_NAME,
                g.get_language_string(30228).format(skin_meta["skin_name"]),
            )
            return

        self._extract_zip(skin_meta)
        self._add_skin_to_database(skin_meta)

        if not silent:
            switch_skin = xbmcgui.Dialog().yesno(
                g.ADDON_NAME,
                g.get_language_string(30218).format(
                    g.encode_py2(skin_meta["skin_name"]),
                    g.encode_py2(skin_meta["version"]),
                ),
            )
            if not switch_skin:
                return

            self.switch_skin(skin_meta["skin_name"])

    def switch_skin(self, skin_name=None):
        """
        Method to switch the active skin
        :param skin_name: Optional argument to provide name of theme to switch to
        :type skin_name: str
        :return: None
        :rtype: None
        """
        if skin_name is None:
            skin_name = self._select_installed_skin()
            if skin_name is None:
                return

        self._mark_skin_active(skin_name)

        xbmcgui.Dialog().ok(
            g.ADDON_NAME, g.get_language_string(30227).format(skin_name)
        )

    def uninstall_skin(self, skin_name=None):
        """
        Method to uninstall an installed theme
        :param skin_name: Optional param to specify which theme to uninstall
        :type skin_name: str
        :return: None
        :rtype: None
        """

        if skin_name is None:
            skin_name = self._select_installed_skin(hide_default=True)
            if skin_name is None:
                return

        confirmation = xbmcgui.Dialog().yesno(
            g.ADDON_NAME, g.get_language_string(30219).format(skin_name)
        )

        if not confirmation:
            return

        if self._is_skin_active(skin_name):
            confirmation = xbmcgui.Dialog().yesno(
                g.ADDON_NAME,
                g.get_language_string(30226),
                nolabel="Cancel",
                yeslabel="Ok",
            )
            if not confirmation:
                return
            self.switch_skin(DEFAULT_SKIN_NAME)

        skin_path = os.path.join(g.SKINS_PATH, skin_name)

        if xbmcvfs.exists(skin_path) and os.path.isdir(skin_path):
            shutil.rmtree(skin_path)

        self._remove_skin_from_database(skin_name)

        xbmcgui.Dialog().ok(
            g.ADDON_NAME, g.get_language_string(30220).format(skin_name)
        )

    # endregion
