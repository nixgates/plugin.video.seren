# -*- coding: utf-8 -*-

import requests
import sys
import threading

from resources.lib.common import tools
from resources.lib.debrid import premiumize as Premiumize
from resources.lib.debrid import real_debrid
from resources.lib.gui.windows.base_window import BaseWindow

try:
    sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
except:
    #Running outside Kodi Call
    pass

sys.path.append(tools.dataPath)

class Resolver(BaseWindow):

    def __init__(self, xml_file, location, actionArgs=None):
        super(Resolver, self).__init__(xml_file, location, actionArgs=actionArgs)
        self.return_data = None
        self.canceled = False
        self.progress = 1
        self.silent = False

        self.pack_select = None

    def resolve(self, sources, args, pack_select=False):
        try:
            if 'showInfo' in args:
                background = args['showInfo']['art']['fanart']
            else:
                background = args['art']['fanart']

            stream_link = None
            loop_count = 0
            # Begin resolving links
            tools.log('Attempting to Resolve file link', 'info')
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
                    self.setProperty('source_provider', i['source'])
                    self.setProperty('source_resolution', i['quality'])
                    self.setProperty('source_info', " ".join(i['info']))

                    if i['type'] == 'torrent':
                        if i['debrid_provider'] == 'premiumize':
                            stream_link = self.premiumizeResolve(i, args, pack_select)
                        elif i['debrid_provider'] == 'real_debrid':
                            stream_link = self.realdebridResolve(i, args)

                        if stream_link is None:
                            tools.log('Failed to resolve for torrent %s' % i['release_title'])
                            continue
                        else:
                            self.return_data = stream_link
                            self.close()
                            return


                    elif i['type'] == 'hoster' or i['type'] == 'cloud':
                        # Quick fallback to speed up resolving while direct and free hosters are not supported

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

                        if i['url'] is None:
                            continue

                        if 'debrid_provider' in i:
                            if i['debrid_provider'] == 'premiumize' and tools.premiumize_enabled():
                                stream_link = self.premiumizeResolve(i, args)
                                if stream_link is None:
                                    continue
                                else:
                                    try:
                                        requests.head(stream_link, timeout=1)
                                    except:
                                        tools.log('Head Request failed link might be dead, skipping')
                                        continue

                            if i['debrid_provider'] == 'real_debrid' and tools.real_debrid_enabled():
                                stream_link = self.realdebridResolve(i, args)
                                if stream_link is None:
                                    continue
                                try:
                                    requests.head(stream_link, timeout=1)
                                except:
                                    tools.log('Head Request failed link might be dead, skipping')
                                    continue
                        else:
                            # Currently not supporting free hosters at this point in time
                            # ResolveURL and Direct link testing needs to be tested first
                            try:
                                ext = i['url'].split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/',
                                                                                                            '').lower()
                                if ext == 'rar': raise Exception()
                                try:
                                    headers = i['url'].rsplit('|', 1)[1]
                                except:
                                    headers = ''

                                try:
                                    headers = i['url'].rsplit('|', 1)[1]
                                except:
                                    headers = ''
                                headers = tools.quote_plus(headers).replace('%3D', '=') if ' ' in headers else headers
                                headers = dict(tools.parse_qsl(headers))

                                live_check = requests.head(i['url'], headers=headers, timeout=10)

                                if not live_check.status_code == 200:
                                    continue

                                stream_link = i['url']
                            except:
                                stream_link = None

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

    def premiumizeResolve(self, source, args, pack_select=False):

        stream_link = None
        try:

            premiumize = Premiumize.PremiumizeFunctions()

            if source['type'] == 'torrent':
                stream_link = premiumize.magnetToStream(source['magnet'], args, pack_select)
            elif source['type'] == 'hoster':
                stream_link = premiumize.resolveHoster(source['url'])
            elif source['type'] == 'cloud':
                stream_link = source['url']
        except:
            import traceback
            traceback.print_exc()
            pass
        return stream_link

    def realdebridResolve(self, i, args):

        stream_link = None
        rd = real_debrid.RealDebrid()

        try:
            if i['type'] == 'torrent':
                stream_link = rd.magnetToLink(i, args)

            elif i['type'] == 'hoster' or i['type'] == 'cloud':
                stream_link = rd.unrestrict_link(i['url'])
        except:
            import traceback
            traceback.print_exc()

        return stream_link

    def getHosterList(self):
        from resources.lib.modules import database
        try:
            hosters = {'premium': {}, 'free': []}
            try:
                if tools.getSetting('premiumize.enabled') == 'true' and tools.getSetting(
                        'premiumize.hosters') == 'true':
                    host_list = database.get(Premiumize.PremiumizeFunctions().updateRelevantHosters, 1)
                    if host_list is None:
                        host_list = Premiumize.PremiumizeFunctions().updateRelevantHosters()
                    if host_list is not None:
                        hosters['premium']['premiumize'] = [(i, i.split('.')[0]) for i in host_list['directdl']]
                    else:
                        hosters['premium']['premiumize'] = []
            except:
                pass

            try:
                if tools.getSetting('realdebrid.enabled') == 'true' and tools.getSetting('rd.hosters') == 'true':
                    host_list = database.get(real_debrid.RealDebrid().getRelevantHosters, 1)
                    if host_list is None:
                        host_list = real_debrid.RealDebrid().getRelevantHosters()
                    if host_list is not None:
                        hosters['premium']['real_debrid'] = [(i, i.split('.')[0]) for i in host_list]
                    else:
                        hosters['premium']['real_debrid'] = []
            except:
                pass

            return hosters

        except:
            import traceback
            traceback.print_exc()

    def doModal(self, sources, args, pack_select):

        if tools.getSetting('general.tempSilent') == 'true':
            self.silent = True

        thread = threading.Thread(target=self.resolve, args=(sources, args, pack_select))
        thread.start()
        if not self.silent:
            tools.dialogWindow.doModal(self)
        else:
            thread.join()

        return self.return_data

    def is_canceled(self):
        if not self.silent:
            if self.canceled:
                return True

    def onAction(self, action):

        id = action.getId()
        if id == 92 or id == 10:
            self.canceled = True

    def setBackground(self, url):
        if not self.silent:
            self.background.setImage(url)
        pass

    def close(self):
        if not self.silent:
            tools.dialogWindow.close(self)

