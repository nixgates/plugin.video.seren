# -*- coding: utf-8 -*-

import requests
import sys
from resources.lib.common.worker import ThreadPool

from resources.lib.common import tools
from resources.lib.debrid import premiumize as Premiumize
from resources.lib.debrid import real_debrid
from resources.lib.debrid import all_debrid
from resources.lib.gui.windows.base_window import BaseWindow

try:
    sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
except:
    #Running outside Kodi Call
    pass

sys.path.append(tools.dataPath)

class Resolver(BaseWindow):

    def __init__(self, xml_file, location=None, actionArgs=None):
        try:
            super(Resolver, self).__init__(xml_file, location, actionArgs=actionArgs)
        except:
            pass
        self.return_data = None
        self.canceled = False
        self.progress = 1
        self.silent = False

        self.pack_select = None
        self.resolvers = {'all_debrid': all_debrid.AllDebrid,
                          'premiumize': Premiumize.Premiumize,
                          'real_debrid': real_debrid.RealDebrid}

    def onInit(self):
        self.resolve(self.sources, self.args, self.pack_select)

    def resolve(self, sources, args, pack_select=False):

        try:

            stream_link = None
            loop_count = 0
            # Begin resolving links

            for i in sources:
                debrid_provider = i.get('debrid_provider', 'None').replace('_', ' ')
                loop_count += 1
                try:
                    if self.is_canceled():
                        self.close()
                        return

                    if 'size' in i:
                        i['info'].append(tools.source_size_display(i['size']))

                    self.setProperty('release_title', tools.display_string(i['release_title']))
                    self.setProperty('debrid_provider', debrid_provider)
                    self.setProperty('source_provider', i['provider'])
                    self.setProperty('source_resolution', i['quality'])
                    self.setProperty('source_info', " ".join(i['info']))

                    if i['type'] == 'torrent':
                        stream_link = self.resolve_source(self.resolvers[i['debrid_provider']], i, args, pack_select)
                        if stream_link is None:
                            tools.log('Failed to resolve for torrent %s' % i['release_title'])
                            continue
                        else:
                            self.return_data = stream_link
                            self.close()
                            return

                    elif i['type'] == 'hoster' or i['type'] == 'cloud':

                        if i['url'] is None:
                            continue

                        if i['type'] == 'cloud' and i['debrid_provider'] == 'premiumize':
                            selected_file = Premiumize.Premiumize().item_details(i['url'])
                            if tools.getSetting('premiumize.transcoded') == 'true':
                                url = selected_file['stream_link']
                            else:
                                url = selected_file['link']
                            self.return_data = url
                            self.close()
                            return

                        if 'provider_imports' in i:
                            provider = i['provider_imports']
                            providerModule = __import__('%s.%s' % (provider[0], provider[1]), fromlist=[''])
                            providerModule = providerModule.source()

                            try:
                                i['url'] = providerModule.resolve(i['url'])
                            except:
                                import traceback
                                traceback.print_exc()
                                pass

                        if 'debrid_provider' in i:
                            stream_link = self.resolve_source(self.resolvers[i['debrid_provider']], i, args,
                                                              pack_select)
                            if stream_link is None:
                                continue
                            else:
                                try:
                                    requests.head(stream_link, timeout=1)
                                except requests.exceptions.RequestException:
                                    tools.log('Head Request failed link likely dead, skipping')
                                    continue

                        elif i['url'].startswith('http'):
                            try:
                                ext = i['url'].split('?')[0]
                                ext = ext.split('&')[0]
                                ext = ext.split('|')[0]
                                ext = ext.rsplit('.')[-1]
                                ext = ext.replace('/', '').lower()
                                if ext == 'rar': raise Exception()

                                try:
                                    headers = i['url'].rsplit('|', 1)[1]
                                except:
                                    headers = ''

                                headers = tools.quote_plus(headers).replace('%3D', '=') if ' ' in headers else headers
                                headers = dict(tools.parse_qsl(headers))

                                live_check = requests.head(i['url'], headers=headers, timeout=10)

                                if not live_check.status_code == 200:
                                    tools.log('Head Request failed link likely dead, skipping')
                                    continue

                                stream_link = i['url']
                            except:
                                import traceback
                                traceback.print_exc()
                                stream_link = None

                        elif tools.file_exists(i['url']):
                            stream_link = i['url']

                        if stream_link is None:
                            continue
                        else:
                            if stream_link.endswith('.rar'):
                                continue
                            self.return_data = stream_link
                            self.close()
                            return
                    continue

                except:
                    import traceback
                    traceback.print_exc()
                    continue

            self.close()
            return
        except:
            import traceback
            traceback.print_exc()
            self.close()
            return

    def resolve_source(self, api, source, args, pack_select=False):
        stream_link = None
        api = api()
        try:

            if source['type'] == 'torrent':
                stream_link = api.resolve_magnet(source['magnet'], args, source, pack_select)
            elif source['type'] == 'hoster':
                stream_link = api.resolve_hoster(source['url'])
        except:
            import traceback
            traceback.print_exc()
            pass
        return stream_link

    def getHosterList(self):
        thread_pool = ThreadPool()
        try:
            hosters = {'premium': {}, 'free': []}
            try:
                if tools.getSetting('premiumize.enabled') == 'true' and tools.getSetting(
                        'premiumize.hosters') == 'true':
                   thread_pool.put(Premiumize.Premiumize().get_hosters, hosters)
            except:
                pass

            try:
                if tools.getSetting('realdebrid.enabled') == 'true' and tools.getSetting('rd.hosters') == 'true':
                    thread_pool.put(real_debrid.RealDebrid().get_hosters, hosters)
            except:
                pass

            try:
                if tools.getSetting('alldebrid.enabled') == 'true' and tools.getSetting('alldebrid.hosters') == 'true':
                    thread_pool.put(all_debrid.AllDebrid().get_hosters, hosters)
            except:
                pass

            thread_pool.wait_completion()

            return hosters

        except:
            import traceback
            traceback.print_exc()

    def doModal(self, sources, args, pack_select):

        if tools.getSetting('general.tempSilent') == 'true':
            self.silent = True

        self.sources = sources
        self.args = args
        self.pack_select = pack_select
        self.setProperty('release_title', tools.display_string(self.sources[0]['release_title']))
        self.setProperty('debrid_provider', self.sources[0].get('debrid_provider', 'None').replace('_', ' '))
        self.setProperty('source_provider', self.sources[0]['provider'])
        self.setProperty('source_resolution', self.sources[0]['quality'])
        self.setProperty('source_info', " ".join(self.sources[0]['info']))
        if not self.silent:
            super(Resolver, self).doModal()
        else:
            self.resolve(sources, args, pack_select)

        return self.return_data

    def is_canceled(self):
        if not self.silent:
            if self.canceled:
                return True

    def onAction(self, action):

        id = action.getId()
        if id == 92 or id == 10:
            self.canceled = True
            self.close()

    def setBackground(self, url):
        if not self.silent:
            self.background.setImage(url)
        pass

    def close(self):
        if not self.silent:
            tools.dialogWindow.close(self)

