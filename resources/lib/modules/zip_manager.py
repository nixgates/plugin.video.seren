# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import shutil
import zipfile

import requests
import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.exceptions import UnsafeZipStructure
from resources.lib.modules.globals import g

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

try:
    from StringIO import StringIO as BytesIO
except ImportError:
    # Python 3 Support
    from io import BytesIO as BytesIO

TEMP_FORMAT = "{}.temp"


class ZipManager:
    """
    Module to handle the unpacking of zip files
    Extend your class with this class
    """

    def __init__(self):
        self._zip_file = None
        self._file_list = []
        self._root_directory = ''
        self._temporary_items = []
        self._extracted_members = []

    def _revert_all_changes(self):
        for i in self._extracted_members:
            self._destroy_file_if_exists(i)
            self._destroy_folder_if_exists(i)
        for temp in self._temporary_items:
            self._restore_temp_item(temp[1])

    @staticmethod
    def _get_zip_location_type():
        return xbmcgui.Dialog().select(
            g.ADDON_NAME, [g.get_language_string(30331), g.get_language_string(30332)]
        )

    def _get_new_package_location(self, install_style):
        install_style = (
            self._get_zip_location_type()
            if install_style is None
            else int(install_style)
        )

        if install_style == 0:
            zip_location = xbmcgui.Dialog().browse(
                1,
                g.get_language_string(30333).format("Provider"),
                "",
                ".zip",
                True,
                False,
            )
        elif install_style == 1:
            zip_location = xbmc.Keyboard(
                "", "{}: {}".format(g.ADDON_NAME, g.get_language_string(30334))
            )
            zip_location.doModal()
            if zip_location.isConfirmed() and zip_location.getText():
                zip_location = zip_location.getText()
            else:
                return
        else:
            return

        return zip_location

    def _get_zip_file(self, install_style=None, silent=False, url=None):
        # This function processes any requests for zip files

        if url is None:
            zip_location = self._get_new_package_location(install_style)
        else:
            zip_location = url

        if not zip_location:
            return

        if zip_location.startswith("http"):
            response = requests.get(zip_location, stream=True)
            if not response.ok and not silent:
                raise requests.exceptions.ConnectionError
            content = response.content
        else:
            f = xbmcvfs.File(zip_location)
            content = f.readBytes()
            f.close()

        self._zip_file = zipfile.ZipFile(BytesIO(content))
        self._file_list = self._zip_file.namelist()
        self._confirm_safe_zip()
        self._root_directory = self._get_zip_root_directory()

    def _confirm_safe_zip(self):
        for i in self._file_list:
            if i.startswith("/") or ".." in i:
                raise UnsafeZipStructure("Zip contains invalid or dirty paths")

    def _get_zip_root_directory(self):
        if self._file_list[0].endswith("/"):
            return self._file_list[0]
        else:
            return ""

    def _create_temp_item(self, file_path):
        if os.path.exists(file_path):
            if os.path.isfile(file_path):
                self._destroy_file_if_exists(TEMP_FORMAT.format(file_path))
                xbmcvfs.rename(file_path, TEMP_FORMAT.format(file_path))
            else:
                if xbmcvfs.exists(tools.ensure_path_is_dir(TEMP_FORMAT.format(file_path))):
                    shutil.rmtree(TEMP_FORMAT.format(file_path))
                os.rename(tools.ensure_path_is_dir(file_path), tools.ensure_path_is_dir(TEMP_FORMAT.format(file_path)))

            self._temporary_items.append(file_path)

    @staticmethod
    def _destroy_folder_if_exists(output_path):
        if os.path.exists(output_path) and os.path.isdir(output_path):
            shutil.rmtree(output_path)

    @staticmethod
    def _destroy_file_if_exists(output_path):
        if os.path.exists(output_path) and not os.path.isdir(output_path):
            os.remove(output_path)

    def _restore_temp_item(self, output_path):
        if os.path.exists(TEMP_FORMAT.format(output_path)):
            self._destroy_file_if_exists(output_path)
            self._destroy_folder_if_exists(output_path)
            xbmcvfs.rename(TEMP_FORMAT.format(output_path), output_path)

    def _destroy_created_temp_items(self):
        for i in self._temporary_items:
            self._destroy_folder_if_exists(TEMP_FORMAT.format(i))
            self._destroy_file_if_exists(TEMP_FORMAT.format(i))

    def _extract_zip_members(self, members, output_path, backup_paths=None):
        self._create_temp_item(output_path if not backup_paths else backup_paths)
        try:
            for i in members:
                self._extract_zip_member(i, output_path)
        except Exception as e:
            self._revert_all_changes()
            raise e

    def _get_file_member_contents(self, member_path):
        if member_path.endswith("/"):
            raise FileNotFoundError(member_path)
        contents = self._zip_file.open(member_path)
        contents = contents.readlines()
        contents = "".join(
            [
                value if not isinstance(value, bytes) else value.decode('utf-8')
                for value in contents
            ]
        )
        return contents.replace(" ", "").replace("\r", "").replace("\n", "")

    def _extract_zip_member(self, member, output_path):
        target_path = os.path.join(output_path, member.replace(self._root_directory, ""))
        upper_dirs = os.path.dirname(target_path)

        if upper_dirs and not xbmcvfs.exists(upper_dirs):
            xbmcvfs.mkdirs(upper_dirs)

        if member[-1] == "/":
            self._create_folder_member(target_path)
        else:
            self._create_file_member(member, target_path)

    def _create_file_member(self, member, target_path):
        with self._zip_file.open(member) as source, open(target_path, 'wb') as target:
            contents = source.read()
            contents = contents.decode('utf-8') if not isinstance(contents, bytes) else contents
            target.write(contents)
            target.close()
            self._extracted_members.append(target_path)

    def _create_folder_member(self, target_path):
        if not os.path.isdir(target_path):
            xbmcvfs.mkdir(tools.ensure_path_is_dir(target_path))
            self._extracted_members.append(target_path)
