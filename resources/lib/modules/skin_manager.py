# -*- coding: utf-8 -*-

from resources.lib.common import tools
from resources.lib.modules import database

import zipfile

import xbmc
import os
import json
import shutil
import requests


class SkinNotFoundException(Exception):

    def __init__(self, skin_name):
        tools.log('Unable to find skin "{}", check it\'s installed?'.format(skin_name), 'error')


class SkinUpdateFailed(Exception):

    def __init__(self, msg):
        tools.log('Skin Update Failed: \n {}'.format(msg), 'error')


class SkinManager:

    def __init__(self):

        # This is a list of default skins that may not be overwritten
        self.seren_skins = ['Seren Fox', 'Default']

        if not os.path.exists(tools.SKINS_PATH):
            os.mkdir(tools.SKINS_PATH)

        self._check_database_for_updates()
        self._create_database()

        self.installed_skins = self._get_all_installed()
        self.active_skin_path = self.get_active_skin_path()

    def get_active_skin_path(self):
        active_skin_name = self.get_active_skin()

        if active_skin_name in self.seren_skins:
            return tools.ADDON_PATH
        else:
            return os.path.join(tools.dataPath, 'skins', active_skin_name)

    def get_active_skin(self):
        cursor = self._get_skin_cursor()

        cursor.execute('SELECT * FROM skins WHERE active = 1')
        active_skin = cursor.fetchone()
        if active_skin is None:
            tools.log('Failed to identify active skin, resetting to Default', 'error')
            cursor.execute('UPDATE skins SET active=1 WHERE skin_name == ?', ('Seren Fox',))
            cursor.connection.commit()
            cursor.execute('SELECT * FROM skins WHERE active = 1')
            active_skin = cursor.fetchone()
        cursor.close()

        return active_skin['skin_name']

    def install_skin(self, zip_location=None, silent=False):
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

        if not silent:
            switch_skin = tools.showDialog.yesno(tools.addonName, tools.lang(40158) %
                                                 (skin_meta['skin_name'].encode('utf-8'),
                                                  skin_meta['version'].encode('utf-8')))

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
        cursor = self._get_skin_cursor()

        cursor.execute('SELECT * FROM skins WHERE skin_name=?', (skin_name,))
        skin_info = cursor.fetchone()

        cursor.close()

        if skin_info['active'] == '1':
            return True
        else:
            return False

    def _select_installed_skin(self, hide_default=False):
        installed_skins = [('{} - {}'.format(i['skin_name'], i['version']), i['skin_name'])
                           for i in self.installed_skins]
        if hide_default:
            installed_skins.remove([i for i in installed_skins if i[1] == 'Seren Fox'][0])

        selection = tools.showDialog.select(tools.addonName, [i[0] for i in installed_skins])

        if selection == -1:
            return

        return installed_skins[selection][1]

    def _extract_zip(self, install_package, skin_meta):

        try:
            file_path = [i for i in install_package.namelist() if i.endswith('resources/skins/')][0]
            file_path = file_path.split('resources/')[0]
        except:
            file_path = ''

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
            zip_location = tools.fileBrowser(1, tools.lang(40304).format('Theme'), 'files', '.zip', True, False)
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

        cursor = self._get_skin_cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS skins ("
                       "skin_name TEXT, "
                       "version TEXT, "
                       "author TEXT, "
                       "active TEXT, "
                       "remote_meta TEXT, "
                       "update_directory TEXT, "
                       "UNIQUE(skin_name))")

        default_installed = cursor.execute('UPDATE skins SET '
                                           'skin_name=?, '
                                           'version=?,'
                                           ' author=?, '
                                           'update_directory=?, '
                                           'remote_meta=?'
                                           ' WHERE skin_name=?',
                                           ('Seren Fox',
                                            '1.0.1',
                                            'Nixgates',
                                            None,
                                            None,
                                            'Seren Fox'))
        if default_installed.rowcount == 0:
            cursor.execute('INSERT INTO skins VALUES (?,?,?,?,?,?)',
                           ('Seren Fox',
                            '1.0.1',
                            'Nixgates',
                            '1',
                            None,
                            None
                            ))

        cursor.connection.commit()
        cursor.close()

    def _get_all_installed(self):

        cursor = self._get_skin_cursor()

        cursor.execute("SELECT * FROM skins")
        installed_skins = cursor.fetchall()
        cursor.close()

        return installed_skins

    def _mark_skin_active(self, skin_name):

        cursor = self._get_skin_cursor()

        cursor.execute('UPDATE skins SET active=? WHERE active=?', ('0', '1'))

        cursor.execute('UPDATE skins SET active=? WHERE skin_name=?', ('1', skin_name))

        cursor.connection.commit()
        cursor.close()

        tools.setSetting('skin.active', skin_name)

    def _add_skin_to_database(self, skin_meta):

        if skin_meta['skin_name'] in self.seren_skins:
            tools.showDialog.ok(tools.addonName, tools.lang(40321))
            return

        cursor = self._get_skin_cursor()

        update = cursor.execute('UPDATE skins SET '
                                'version=?, '
                                'author=?, '
                                'remote_meta=?, '
                                'update_directory=? '
                                'WHERE skin_name=?', (skin_meta['version'],
                                                      skin_meta['author'],
                                                      skin_meta.get('remote_meta', None),
                                                      skin_meta.get('update_directory', None),
                                                      skin_meta['skin_name']))
        if update.rowcount == 0:
            cursor.execute('INSERT INTO skins VALUES (?,?,?,?,?,?)',
                           (skin_meta['skin_name'],
                            skin_meta['version'],
                            skin_meta['author'],
                            '0',
                            skin_meta.get('remote_meta', None),
                            skin_meta.get('update_directory', None)
                            ))

        cursor.connection.commit()
        cursor.close()

    def _remove_skin_from_database(self, skin_name):

        cursor = self._get_skin_cursor()
        cursor.execute('DELETE FROM skins WHERE skin_name=?', (skin_name,))
        cursor.connection.commit()
        cursor.close()

    def confirm_skin_path(self, xml_file):

        if self.active_skin_path == tools.ADDON_PATH:
            return xml_file, self.active_skin_path

        skins_folder = os.path.join(self.active_skin_path, 'resources', 'skins', 'Default')

        for folder in [folder for folder in
                       os.listdir(skins_folder)
                       if os.path.isdir(os.path.join(skins_folder, folder))]:

            if folder == 'media':
                continue

            if xml_file in os.listdir(os.path.join(skins_folder, folder)):
                return xml_file, self.active_skin_path

        return xml_file, tools.ADDON_PATH

    def _check_skin_for_update(self, skin_info):

        try:
            remote_meta = requests.get(skin_info['remote_meta']).json()
            return tools.check_version_numbers(skin_info['version'], remote_meta['version'])
        except:
            tools.log('Failed to obtain remote meta information for skin: {}'.format(skin_info['skin_name']))
            return False

    def _skin_can_update(self, skin_info):
        keys = ['remote_meta', 'update_directory']

        for key in keys:
            if skin_info[key] is None:
                return False
            if skin_info[key] is '':
                return False
            if not skin_info[key].startswith('http'):
                return False

        return True

    def check_for_updates(self, skin_name=None, silent=False):

        skins = []

        if skin_name is None:
            skins = self.installed_skins

        else:
            try:
                skins.append([i for i in self.installed_skins if i['skin_name'] == skin_name][0])
            except IndexError:
                raise SkinNotFoundException(skin_name)

        if not silent:
            tools.progressDialog.create(tools.addonName, tools.lang(33019))
            tools.progressDialog.update(-1)

        skins = [i for i in skins if self._skin_can_update(i)]
        skins = [i for i in skins if self._check_skin_for_update(i)]

        if len(skins) == 0:
            if not silent:
                tools.progressDialog.close()
                tools.showDialog.ok(tools.addonName, tools.lang(33018))
            return

        if not silent:
            tools.progressDialog.close()
            while skins and len(skins) > 0:
                tools.progressDialog.create(tools.addonName, tools.lang(40311))
                tools.progressDialog.update(-1)

                selection = tools.showDialog.select(tools.addonName, ['{} - {}'.format(i['skin_name'], i['version'])
                                                                      for i in skins])
                if selection == -1:
                    return

                skin_info = skins[selection]

                try:
                    self.install_skin(skin_info['update_directory'], True)
                    skins.remove(skin_info)
                    tools.progressDialog.close()
                    tools.showDialog.ok(tools.addonName, tools.lang(40318))
                except:
                    import traceback
                    traceback.print_exc()
                    tools.log('Failed to update skin: {}'.format(selection['skin_name']))
                    tools.showDialog.notification(tools.addonName, tools.lang(33013))

            tools.showDialog.ok(tools.addonName, tools.lang(33018))
            return

        for skin in skins:
            try:
                self.install_skin(skin['update_directory'], True)
            except:
                tools.log('Failed to update theme: {}'.format(skin['skin_name']))

        tools.log('Skin updates completed')

    def _get_skin_cursor(self):
        return database._get_connection_cursor(tools.SKINS_DB_PATH)

    def _check_database_for_updates(self):
        cursor = self._get_skin_cursor()
        try:
            cursor.execute("SELECT * FROM skins WHERE skin_name=?", ('Seren Fox',))
            base_skin = cursor.fetchone()
        except database.OperationalError:
            return
        finally:
            cursor.close()

        if 'update_directory' not in base_skin:
            self._update_db_skin_updates()

    def _update_db_skin_updates(self):
        cursor = self._get_skin_cursor()
        cursor.execute('ALTER TABLE skins ADD COLUMN update_directory TEXT')
        cursor.execute('ALTER TABLE skins ADD COLUMN remote_meta TEXT')
        cursor.close()
