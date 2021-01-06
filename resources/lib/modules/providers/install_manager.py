# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import json
import os
import shutil
import sys

import requests
import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.exceptions import (
    FileIOError,
    InvalidMetaFormat,
    UnsafeZipStructure,
)
from resources.lib.modules.globals import g
from resources.lib.modules.providers import CustomProviders
from resources.lib.modules.providers.service_manager import ProvidersServiceManager
from resources.lib.modules.providers.settings import SettingsManager
from resources.lib.modules.zip_manager import ZipManager

try:
    from importlib import reload as reload_module  # pylint: disable=no-name-in-module
except ImportError:
    # Invalid version of importlib
    from imp import reload as reload_module


TEMP_FORMAT = "{}.temp"


class ProviderInstallManager(CustomProviders, ZipManager):
    """
    Class for handling provider package installations
    """
    def __init__(self, silent=False):
        super(ProviderInstallManager, self).__init__()
        ZipManager.__init__(self)
        self.silent = silent
        self.output_folders = ["providerModules/", "providers/"]

    def _get_package_selection(self):
        packages = [i["pack_name"] for i in self.known_packages]
        if len(packages) == 0:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30049))
            return
        selection = xbmcgui.Dialog().select(
            "{}: {} {}".format(
                g.ADDON_NAME,
                g.get_language_string(30050),
                g.get_language_string(30147),
            ),
            packages,
        )
        if selection == -1:
            return
        return packages[selection]

    def uninstall_package(self, package=None, silent=False):
        """
        Initiate uninstallation of a package, optionally supply package name to automate process
        :param package: (Optional) name of package to uninstall
        :type package: basestring
        :param silent: Opiton to disable user feedback
        :type silent: bool
        :return: None
        :rtype: None
        """
        self.silent = silent

        package_name = self._get_package_selection() if package is None else package
        if package_name is None:
            return

        confirm = xbmcgui.Dialog().yesno(
            g.ADDON_NAME, g.get_language_string(30051) + " {}".format(package_name)
        )
        if confirm == 0:
            return

        try:
            self._remove_package_directories(package_name)
            self.remove_provider_package(package_name)
            self.provider_settings.remove_package_settings(package_name)

            if not silent:
                xbmcgui.Dialog().ok(
                    g.ADDON_NAME,
                    "{} {}".format(package_name, g.get_language_string(30052)),
                )
        except Exception as e:
            self._handle_uninstall_failure(package_name)
            raise e

        ProvidersServiceManager().stop_package_services(package_name)

    @staticmethod
    def _handle_uninstall_failure(package_name):
        xbmcgui.Dialog().ok(
            g.ADDON_NAME,
            g.get_language_string(30183).format(g.ADDON_NAME, package_name),
        )
        g.log_stacktrace()

    def _remove_package_directories(self, package_name):
        self._destroy_folder_if_exists(os.path.join(self.providers_path, package_name))
        self._destroy_folder_if_exists(os.path.join(self.modules_path, package_name))
        self._destroy_folder_if_exists(os.path.join(self.meta_path, package_name))

    @staticmethod
    def _handle_install_failure(exception):
        g.log(exception, "error")
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30514))
        return

    def install_package(self, install_style, url=None):
        """
        Initiates the installation of a provider package
        :param install_style: Method of obtaining the zip file to be installed
        :type install_style: [int,None]
        :param url: Optionally supply the url to use
        :type url: basestring
        :return: No return
        :rtype: None
        """
        self.deploy_init()

        self._get_zip_file(install_style=install_style, url=url)

        try:
            self._install_zip()
        except (UnsafeZipStructure, InvalidMetaFormat):
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30075))
        except FileIOError as e:
            g.log(e, "error")
            self._failed_prompt()

        self._init_providers()
        self.poll_database()

    def _confirm_meta_file_contents(self, meta):
        requirements = ["author", "name", "version"]
        for req in requirements:
            if req not in meta:
                self._failed_prompt()
                raise InvalidMetaFormat(
                    "Source pack is malformed, please check and correct issue in the meta "
                    "file_path"
                )
        return meta

    def _handle_no_updates_prompt(self, remote_meta):
        if not remote_meta and not self.silent:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30082))

    def _install_confirmation(self, pack_name, author, version):
        if not self.silent:
            accept = xbmcgui.Dialog().yesno(
                g.ADDON_NAME + " - {}".format(g.get_language_string(30072)),
                "{}\n{}\n{}".format(g.color_string(g.get_language_string(30069)) +
                                    " {} - v{}".format(pack_name, version),
                                    g.color_string(g.get_language_string(30070)) + "{}".format(author),
                                    g.get_language_string(30071)),
                nolabel=g.get_language_string(30073),
                yeslabel=g.get_language_string(30074),
            )
            if accept == 0:
                return False
        return True

    def _get_meta_json(self):
        return json.loads(self._get_file_member_contents("{}{}".format(self._root_directory, "meta.json")))

    def _output_meta_file(self, meta_output_location):
        self._extract_zip_members([i for i in self._file_list if i.endswith('meta.json')], meta_output_location)

    def _extract_package_folders(self, pack_name):
        for folder in self.output_folders:
            try:
                folder_path = os.path.join(folder.strip("/"), pack_name)
                file_list = [i for i in self._file_list if i != "providers/__init__.py"
                             and i.startswith(os.path.join(self._root_directory, folder))]
                self._extract_zip_members(file_list, g.ADDON_USERDATA_PATH,
                                          os.path.join(g.ADDON_USERDATA_PATH, folder_path))

            except Exception as e:
                raise FileIOError("{} Failed to extract to folder - {}".format(e, folder))

    def _install_zip(self):
        install_progress = None
        # self._remove_root_directory_from_file_paths()
        meta = self._get_meta_json()
        meta = self._confirm_meta_file_contents(meta)

        author = meta["author"]
        version = meta["version"]
        pack_name = meta["name"]
        remote_meta = meta.get("remote_meta", "")
        services = "|".join(meta.get("services", []))

        if not self._install_confirmation(pack_name, author, version):
            return

        self.pre_update_collection = [
            i for i in self.get_providers() if i["package"] == pack_name
        ]
        meta_output_location = os.path.join(g.ADDON_USERDATA_PATH, "providerMeta", pack_name)

        self._output_meta_file(meta_output_location)

        if not self.silent:
            install_progress = xbmcgui.DialogProgress()
            install_progress.create(
                g.ADDON_NAME,
                tools.create_multiline_message(
                    line1="{} - {}".format(pack_name, g.get_language_string(30076)),
                    line2=g.get_language_string(30077),
                ),
            )
            install_progress.update(-1)

        self._extract_package_folders(pack_name)
        self._destroy_created_temp_items()

        if install_progress:
            install_progress.close()

        SettingsManager().create_settings(meta["name"], meta.get("settings", []))
        g.log("Refreshing provider database ")
        self.add_provider_package(pack_name, author, remote_meta, version, services)
        self._do_package_pre_config(meta["name"], meta.get("setup_extension"))

        if not self.silent:
            xbmcgui.Dialog().ok(
                g.ADDON_NAME, "{} - {}".format(g.get_language_string(30078), pack_name)
            )
        xbmc.executebuiltin(
            'RunPlugin("plugin://plugin.video.{}/?action=refreshProviders")'.format(
                g.ADDON_NAME.lower()
            )
        )

        ProvidersServiceManager().start_package_services(pack_name)
        return True

    def _remove_root_directory_from_file_paths(self):
        if not self._root_directory:
            return
        for i, v in enumerate(self._file_list):
            self._file_list[i] = self._file_list[i].replace(self._root_directory, "")
        return self._file_list[1:]

    def update(self, meta_file, silent=False):
        """
        Request the upate of a installed package
        :param meta_file: Contents of provider packages meta file
        :type meta_file: dict
        :param silent: optional disabling of user feedback
        :type silent: bool
        :return: None
        :rtype: None
        """
        self.silent = silent
        update_directory = meta_file["update_directory"]
        package_name = meta_file["name"]
        version = meta_file["version"]
        zip_file = "{}{}-{}.zip".format(update_directory, package_name, version)
        try:
            self._get_zip_file(url=zip_file, silent=True)
        except requests.exceptions.ConnectionError:
            g.close_busy_dialog()
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30081))
            return

        result = self._install_zip()
        if result is not None:
            g.notification(
                g.ADDON_NAME, g.get_language_string(30083).format(package_name)
            )

    def manual_update(self):
        """
        Manual run of checking for updates
        :return: None
        :rtype: None
        """
        update = self.check_for_updates()

        # If there are no available updates return
        if not update:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30084))
            return

        # Display available packages to update
        display_list = ["{} - {}".format(i["name"], i["version"]) for i in update]
        selection = xbmcgui.Dialog().select(g.ADDON_NAME, display_list)

        if selection == -1:
            return

        selection = update[selection]
        self.update(selection)

    @staticmethod
    def _failed_prompt():
        xbmcgui.Dialog().ok(
            g.ADDON_NAME,
            tools.create_multiline_message(
                line1=g.get_language_string(30080), line2=g.get_language_string(30079)
            ),
        )

    @staticmethod
    def _failure_cleanup(meta_location, package_name, folders):
        # In the event of a failure to install package this function will revert changes made

        g.log("Reverting changes")
        try:
            if xbmcvfs.exists("{}.temp".format(meta_location)):
                os.remove(meta_location)
                os.rename("{}.temp".format(meta_location), meta_location)
        except:
            pass

        for folder in folders:
            folder_path = os.path.join(
                g.ADDON_USERDATA_PATH, folder.strip("/"), package_name
            )
            if xbmcvfs.exists("{}.temp".format(folder_path)):
                try:
                    shutil.rmtree(folder_path)
                except:
                    pass
                os.rename("{}.temp".format(folder_path), folder_path)

    @staticmethod
    def _do_package_pre_config(package_name, config_file):
        if not config_file:
            return
        reload = False
        config_path = "providers.{}.{}".format(package_name, config_file.strip(".py"))
        if config_path in sys.modules:
            reload = True
        module = __import__(config_path, fromlist=[""])
        if reload:
            reload_module(module)

    def check_for_updates(self, silent=False, automatic=False):
        """
        Check all packages for updates
        :param silent: Optional setting to disable user feedback
        :type silent: bool
        :param automatic: Optional argument to automatically process updates if available
        :type automatic: bool
        :return: None if automatic set to True else returns a list of available updates if set to False
        :rtype: [None,list]
        """
        # Automatic "True" will update all packages with available updates
        # Silent "True" will prevent kodi from creating any dialogs except for a single notification

        if not silent:
            update_dialog = xbmcgui.DialogProgress()
            update_dialog.create(g.ADDON_NAME, g.get_language_string(30085))
            update_dialog.update(-1)

        updates = []
        update_dialog = None

        packages = self.known_packages

        if len(packages) == 0:
            return []

        for package in packages:
            if not package["remote_meta"]:
                continue

            meta_file = requests.get(package["remote_meta"])
            if meta_file.status_code != 200:
                continue

            meta_file = json.loads(meta_file.text)

            if not meta_file["name"] == package["pack_name"]:
                g.log(
                    "Pack name check failure - {} : {}".format(
                        meta_file["name"], package["pack_name"]
                    )
                )
                continue
            if not tools.compare_version_numbers(package["version"], meta_file["version"]):
                continue
            if not automatic:
                updates.append(meta_file)
            else:
                ProviderInstallManager().update(meta_file, silent)

        if not silent and update_dialog:
            update_dialog.close()

        if not automatic:
            return updates