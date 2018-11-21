import os, sys
from resources.lib.common import tools
from resources.lib.modules import database

class providers:

    def __init__(self):
        # self.language = tools.getSetting('general.language')
        self.language = 'en'
        tools.progressDialog.create(tools.addonName, 'Please Wait, Building Provider List')
        self.known_providers = database.get_providers()
        tools.progressDialog.close()
        self.update_known_providers()
        self.providers_path = os.path.join(tools.dataPath, 'providers')
        self.modules_path = os.path.join(tools.dataPath, 'providerModules')


    def update_known_providers(self):
        sys.path.append(tools.dataPath)
        import providers
        providers = providers.get_all(self.language)

        if self.known_providers is None or len(self.known_providers) == 0:
            for provider in providers[0]:
                database.add_provider(provider[1], provider[2], 'enabled', self.language, 'torrent')
            for provider in providers[1]:
                database.add_provider(provider[1], provider[2], 'enabled', self.language, 'hoster')
            return

        for provider in providers[0]:
            check = False
            for kp in self.known_providers:
                if kp['country'] != self.language:
                    continue
                if kp['provider_type'] != 'torrent':
                    continue
                if provider[2] == kp['package'] and provider[1] == kp['provider_name']:
                    check = True
                    pass
            if check is False:
                tools.log('Adding Provider %s' % provider[1])
                database.add_provider(provider[1], provider[2], 'enabled', self.language, 'torrent')
                check = False

        for provider in providers[1]:
            check = False
            for kp in self.known_providers:
                if kp['country'] != self.language:
                    continue
                if kp['provider_type'] != 'hoster':
                    continue
                if provider[2] == kp['package'] and provider[1] == kp['provider_name']:
                    check = True
            if check is False:
                tools.log('Adding Provider %s' % provider[1])
                database.add_provider(provider[1], provider[2], 'enabled', self.language, 'hoster')
                check = False

        self.known_providers = database.get_providers()

    def adjust_providers(self, status):
        if status == 'disabled':
            action = 'enabled'
        if status == 'enabled':
            action = 'disabled'
        if len(self.known_providers) == 0:
            self.known_providers = database.get_providers()
        packages = list(set([provider['package'] for provider in self.known_providers]))
        selection = tools.showDialog.select("%s: %s Providers" %
                                            (tools.addonName, action[:-1].title()), packages)

        if selection == -1:
            return

        providers = [i for i in self.known_providers if i['package'] == packages[selection] and i['status'] == status]

        display_list = ["%s - %s" % (tools.colorString(i['provider_name'].upper()), i['provider_type'].title())
                        for i in providers if i['status'] == status]

        selection = tools.showDialog.multiselect("%s: %s Providers" %
                                                 (tools.addonName, action[:-1].title()), display_list)

        if selection is None:
            return

        for i in selection:
            provider = providers[i]
            database.add_provider(provider['provider_name'], provider['package'], action, self.language,
                               provider['provider_type'])

    def uninstall_package(self):
        import shutil
        packages = list(set([provider['package'] for provider in self.known_providers]))
        if len(packages) == 0:
            tools.showDialog.ok(tools.addonName, 'There are currently no packages installed')
            return
        selection = tools.showDialog.select("%s: %s Providers" %
                                            (tools.addonName, 'Uninstall'), packages)
        if selection == -1:
            return
        package_name = packages[selection]
        confirm = tools.showDialog.yesno(tools.addonName, "Are you sure you wish to remove %s" % package_name)
        if confirm == 0:
            return

        provider_path = os.path.join(self.providers_path, package_name)
        modules_path = os.path.join(self.modules_path, package_name)
        if os.path.exists(provider_path):
            shutil.rmtree(provider_path)
        if os.path.exists(modules_path):
            shutil.rmtree(modules_path)
        database.uninstall_provider_package(package_name)
        tools.showDialog.ok(tools.addonName, '%s successfully uninstalled' % package_name)