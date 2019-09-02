# -*- coding: utf-8 -*-

from resources.lib.common import tools
from resources.lib.modules import database

if tools.kodiVersion > 17:
    from resources.lib.modules import zfile as zipfile
else:
    import zipfile

import xbmc
import requests
import os
import json
import shutil

class SkinManager:

    def __init__(self):

        # This is a list of default skins that may not be overwritten
        self.seren_skins = ['Seren Fox', 'Default']

        if not os.path.exists(tools.SKINS_PATH):
            os.mkdir(tools.SKINS_PATH)

        self._create_database()
        self.installed_skins = self._get_all_installed()

        self.seren_default_window_path = os.path.join(tools.addonDir, 'resources', 'skins', 'seren_backup_files')

        self.active_skin_path = self.get_active_skin_path()

    def get_active_skin_path(self):
        active_skin_name = self.get_active_skin()

        if active_skin_name in self.seren_skins:
            return tools.ADDON_PATH
        else:
            return os.path.join(tools.dataPath, 'skins', active_skin_name)

    def get_active_skin(self):
        cursor = database._get_connection_cursor(tools.SKINS_DB_PATH)

        cursor.execute('SELECT * FROM skins WHERE active = 1')
        active_skin = cursor.fetchone()
        cursor.close()

        return active_skin['skin_name']

    def install_skin(self, zip_location=None):
        if zip_location is None:
            zip_location = self._get_zip_location()

            if zip_location is None:
                return
        install_package = self._get_zip_file(zip_location)

        if install_package is None:
            return

        skin_meta = self._get_skin_meta(install_package)

        if skin_meta is None:
            return

        if skin_meta['skin_name'] in self.seren_skins:
            tools.showDialog.ok(tools.addonName, tools.lang(40168) % skin_meta['skin_name'])
            return

        self._extract_zip(install_package, skin_meta)
        self._add_skin_to_database(skin_meta)

        self._cleanup_temp_files(skin_meta)

        switch_skin = tools.showDialog.yesno(tools.addonName, tools.lang(40158).encode('utf-8') %
                                             (skin_meta['skin_name'], skin_meta['version']))

        if not switch_skin:
             return

        self.switch_skin(skin_meta['skin_name'])

    def uninstall_skin(self, skin_name=None):

        if skin_name is None:
            skin_name = self._select_installed_skin(hide_default=True)
            if skin_name is None:
                return

        confirmation = tools.showDialog.yesno(tools.addonName, tools.lang(40159) % skin_name)

        if not confirmation:
            return

        if self._is_skin_active(skin_name):
            confirmation = tools.showDialog.yesno(tools.addonName, tools.lang(40166), nolabel='Cancel', yeslabel="Ok")
            if not confirmation:
                return
            self.switch_skin('Seren Fox')

        skin_path = os.path.join(tools.SKINS_PATH, skin_name)

        if os.path.exists(skin_path) and os.path.isdir(skin_path):
            shutil.rmtree(skin_path)

        self._remove_skin_from_database(skin_name)

        tools.showDialog.ok(tools.addonName, tools.lang(40160) % skin_name)

    def switch_skin(self, skin_name=None):

        if skin_name == None:
            skin_name = self._select_installed_skin()
            if skin_name is None:
                return

        self._mark_skin_active(skin_name)

        tools.showDialog.ok(tools.addonName, tools.lang(40167) % skin_name)

    def _is_skin_active(self, skin_name):
        cursor = database._get_connection_cursor(tools.SKINS_DB_PATH)

        cursor.execute('SELECT * FROM skins WHERE skin_name=?', (skin_name,))
        skin_info = cursor.fetchone()

        cursor.close()

        if skin_info['active'] == '1':
            return True
        else:
            return False

    def _select_installed_skin(self, hide_default=False):
        installed_skins = [i['skin_name'] for i in self.installed_skins]
        if hide_default:
            installed_skins.remove('Seren Fox')

        selection = tools.showDialog.select(tools.addonName, installed_skins)

        if selection == -1:
            return

        return installed_skins[selection]

    def _extract_zip(self, install_package, skin_meta):

        try:
            file_path = [i for i in install_package.namelist() if i.endswith('resources/skins/')][0]
            file_path = file_path.split('resources/')[0]
        except:
            file_path = ''
        tools.log('%sresources/' % file_path)
        if '%sresources/' % file_path not in install_package.namelist():
            tools.log('Theme Folder Structure Invalid: Missing folder "Resources"')
            tools.showDialog.ok(tools.addonName, tools.lang(40171))
            raise Exception

        skin_path = os.path.join(tools.SKINS_PATH, skin_meta['skin_name'])

        if os.path.exists(skin_path):
            if os.path.exists(skin_path + '.temp'):
                shutil.rmtree(skin_path + '.temp')
            os.rename(skin_path, skin_path + '.temp')
            os.mkdir(skin_path)

        try:
            for i in [i for i in install_package.namelist() if i.startswith(file_path) and i != file_path]:
                install_package.extract(i, skin_path)
        except:
            import traceback
            traceback.print_exc()
            if os.path.exists(skin_path + '.temp'):
                shutil.rmtree(skin_path)
                os.rename(skin_path + '.temp', skin_path)
            raise Exception

        # Move Folders out of child folder if it exists
        tree_location = os.path.join(skin_path, file_path)
        if os.path.exists(tree_location):
            for i in os.listdir(tree_location):
                if os.path.isdir(os.path.join(tree_location, i)):
                    shutil.copytree(os.path.join(tree_location, i), os.path.join(skin_path, i))
                else:
                    shutil.copyfile(os.path.join(tree_location, i), os.path.join(skin_path, i))

            shutil.rmtree(tree_location)

    def _get_zip_file(self, zip_location, silent=False):
        # This function processes any requests for zip files

        if zip_location == '':
            return

        if zip_location.startswith('special://'):
            zip_location = xbmc.translatePath(zip_location)

        if zip_location.startswith('smb'):
            if not silent:
                tools.showDialog.ok(tools.addonName, tools.lang(33014))
            return

        if zip_location.startswith('http'):
            response = requests.get(zip_location, stream=True)
            if not response.ok and not silent:
                tools.showDialog.ok(tools.addonName, tools.lang(33015))
                return
            else:
                pass
            try:
                import StringIO
                install_package = zipfile.ZipFile(StringIO.StringIO(response.content))
            except:
                # Python 3 Support
                import io
                install_package = zipfile.ZipFile(io.BytesIO(response.content))
        else:
            install_package = zipfile.ZipFile(zip_location)

        return install_package

    def _get_skin_meta(self, zip_file):
        file_list = zip_file.namelist()

        meta_file = None
        zip_root_dir = ''

        for i in file_list:
            if i.endswith('meta.json'):
                meta_file = i

        if meta_file is None:
            tools.log('%s/meta.json' % file_list[0])
            if '%s/meta.json' % file_list[0] in file_list:
                zip_root_dir = file_list[0]
                meta_file = 'meta.json'

        if meta_file is None:
            raise Exception

        meta = zip_file.open(zip_root_dir + meta_file)
        meta = meta.readlines()
        meta = ''.join(meta)
        meta = meta.replace(' ', '').replace('\r', '').replace('\n', '')
        meta = json.loads(meta)

        return meta

    def _get_zip_location(self):
        zip_location = None

        install_type = tools.showDialog.select(tools.addonName, [tools.lang(40302), tools.lang(40303)])

        if install_type == -1:
            return None

        if install_type == 0:
            zip_location = tools.fileBrowser(1, tools.lang(40304), 'files', '.zip', True, False)
        elif install_type == 1:
            user_input = tools.showKeyboard('', '%s: %s' % (tools.addonName, tools.lang(40305)))
            user_input.doModal()
            if user_input.isConfirmed() and user_input.getText() != '':
                zip_location = user_input.getText()
            else:
                return

        return zip_location

    def _cleanup_temp_files(self, skin_meta):

        skin_path = os.path.join(tools.SKINS_PATH, skin_meta['skin_name'])

        if os.path.exists(skin_path + '.temp'):
            shutil.rmtree(skin_path + '.temp')

    def _create_database(self):

        cursor = database._get_connection_cursor(tools.SKINS_DB_PATH)

        cursor.execute("CREATE TABLE IF NOT EXISTS skins ("
                       "skin_name TEXT, "
                       "version TEXT, "
                       "author TEXT, "
                       "active TEXT, "
                       "UNIQUE(skin_name))")

        default_installed = cursor.execute('UPDATE skins SET '
                                           'skin_name=?, version=?, author=? WHERE skin_name=?',
                                           ('Seren Fox', '1.0.0', 'Nixgates', 'Seren Fox'))
        if default_installed.rowcount == 0:
            cursor.execute('INSERT INTO skins VALUES (?,?,?,?)', ('Seren Fox', '1.0.0', 'Nixgates', '1'))

        cursor.connection.commit()
        cursor.close()

    def _get_all_installed(self):

        cursor = database._get_connection_cursor(tools.SKINS_DB_PATH)

        cursor.execute("SELECT * FROM skins")
        installed_skins = cursor.fetchall()
        cursor.close()

        return installed_skins

    def _mark_skin_active(self, skin_name):

        cursor = database._get_connection_cursor(tools.SKINS_DB_PATH)

        cursor.execute('UPDATE skins SET active=? WHERE active=?', ('0', '1'))

        cursor.execute('UPDATE skins SET active=? WHERE skin_name=?', ('1', skin_name))

        cursor.connection.commit()
        cursor.close()

        tools.setSetting('skin.active', skin_name)

    def _add_skin_to_database(self, skin_meta):

        if skin_meta['skin_name'] in self.seren_skins:
            tools.showDialog.ok(tools.addonName, tools.lang(40321))
            return

        cursor = database._get_connection_cursor(tools.SKINS_DB_PATH)

        update = cursor.execute('UPDATE skins SET version=?, author=? WHERE skin_name=?', (skin_meta['version'],
                                                                                           skin_meta['author'],
                                                                                           skin_meta['skin_name']))
        if update.rowcount == 0:
            cursor.execute('INSERT INTO skins VALUES (?,?,?,?)', (skin_meta['skin_name'],
                                                                  skin_meta['version'],
                                                                  skin_meta['author'], '0'))

        cursor.connection.commit()
        cursor.close()

    def _remove_skin_from_database(self, skin_name):

        cursor = database._get_connection_cursor(tools.SKINS_DB_PATH)
        cursor.execute('DELETE FROM skins WHERE skin_name=?', (skin_name,))
        cursor.connection.commit()
        cursor.close()