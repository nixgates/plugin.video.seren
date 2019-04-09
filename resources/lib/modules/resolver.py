# -*- coding: utf-8 -*-

import os
import requests
import sys
import threading

from resources.lib.common import tools
from resources.lib.debrid import premiumize as Premiumize
from resources.lib.debrid import real_debrid

try:
    sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
except:
    #Running outside Kodi Call
    pass

sys.path.append(tools.dataPath)

class Resolver(tools.dialogWindow):

    def __init__(self):
        self.return_data = None
        self.canceled = False
        self.progress = 1
        self.silent = False
        self.line1 = ''
        self.line2 = ''
        self.line3 = ''

        text = ''

        background_image = ''

        background_image = os.path.join(tools.IMAGES_PATH, 'background.png')

        texture_path = os.path.join(tools.IMAGES_PATH, 'texture.png')
        background_diffuse = '0x1FFFFFFF'
        self.perc_on_path = os.path.join(tools.IMAGES_PATH, 'on.png')
        self.perc_off_path = os.path.join(tools.IMAGES_PATH, 'off.png')
        self.texture = tools.imageControl(0, 0, 1280, 720, texture_path)
        self.addControl(self.texture)
        self.background = tools.imageControl(0, 0, 1280, 720, background_image)
        self.background.setColorDiffuse(background_diffuse)

        self.addControl(self.background)

        self.panda_logo = tools.imageControl(605, 330, 70, 60, tools.PANDA_LOGO_PATH)
        self.addControl(self.panda_logo)

        lpx = 570
        lpy = 410

        self.perc10 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc20 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc30 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc40 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc50 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc60 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc70 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc80 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc90 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)
        lpx += 15
        self.perc100 = tools.imageControl(lpx, lpy, 10, 10, self.perc_off_path)

        self.addControl(self.perc10)
        self.addControl(self.perc20)
        self.addControl(self.perc30)
        self.addControl(self.perc40)
        self.addControl(self.perc50)
        self.addControl(self.perc60)
        self.addControl(self.perc70)
        self.addControl(self.perc80)
        self.addControl(self.perc90)
        self.addControl(self.perc100)

        self.text_label = tools.labelControl(0, 430, 1280, 50, str(text), font='font13', alignment=tools.XBFONT_CENTER_X)
        self.text_label2 = tools.labelControl(0, 470, 1280, 50, "", font='font13', alignment=tools.XBFONT_CENTER_X)
        self.text_label3 = tools.labelControl(0, 510, 1280, 50, "", font='font13', alignment=tools.XBFONT_CENTER_X)

        self.addControl(self.text_label)
        self.addControl(self.text_label2)
        self.addControl(self.text_label3)
        self.pack_select = None

    def resolve(self, sources, args, pack_select=False):
        try:
            if 'showInfo' in args:
                background = args['showInfo']['art']['fanart']
            else:
                background = args['fanart']

            self.setText(tools.lang(33000))
            self.setBackground(background)
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
                    loop_count_string = "(" + str(loop_count) + " of " + str(len(sources)) + ")"
                    line1 = "%s %s - %s" % (tools.lang(32036),
                                            tools.colorString(tools.display_string(i['release_title'])),
                                            loop_count_string)
                    line2 = "%s %s | Source: %s" % (tools.lang(32037),
                                                    tools.colorString(debrid_provider.upper()),
                                                    tools.colorString(i['source']))
                    line3 = '%s %s | Info: %s' % (tools.lang(32038),
                                                  tools.colorString(i['quality']),
                                                  tools.colorString(" ".join(i['info'])))

                    self.setText(line1)
                    self.setText2(line2)
                    self.setText3(line3)

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


                    elif i['type'] == 'hoster':
                        # Quick fallback to speed up resolving while direct and free hosters are not supported

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
                            if i['debrid_provider'] == 'premiumize' and tools.getSetting('premiumize.enabled') == 'true':
                                stream_link = self.premiumizeResolve(i, args)
                                if stream_link is None:
                                    continue

                            if i['debrid_provider'] == 'real_debrid':
                                stream_link = self.realdebridResolve(i, args)
                                if stream_link is None:
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
            if tools.getSetting('premiumize.enabled') == 'true':
                tools.execute('RunPlugin("plugin://plugin.video.%s/?action=premiumizeCleanup")' % tools.addonName.lower())
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
        except:
            pass
        return stream_link

    def realdebridResolve(self, i, args):

        stream_link = None
        rd = real_debrid.RealDebrid()

        try:
            if i['type'] == 'torrent':
                stream_link = rd.magnetToLink(i, args)

            elif i['type'] == 'hoster':
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
            pass

    def setText(self, text):
        self.text_label.setLabel(str(text))

    def setText2(self, text):
        self.text_label2.setLabel(str(text))

    def setText3(self, text):
        self.text_label3.setLabel(str(text))

    def setProgress(self):
        if not self.silent:
            progress = int(self.progress)
            if progress > 10:
                self.perc10.setImage(self.perc_on_path)
            if progress > 20:
                self.perc20.setImage(self.perc_on_path)
            if progress > 30:
                self.perc30.setImage(self.perc_on_path)
            if progress > 40:
                self.perc40.setImage(self.perc_on_path)
            if progress > 50:
                self.perc50.setImage(self.perc_on_path)
            if progress > 60:
                self.perc60.setImage(self.perc_on_path)
            if progress > 70:
                self.perc70.setImage(self.perc_on_path)
            if progress > 80:
                self.perc80.setImage(self.perc_on_path)
            if progress > 90:
                self.perc90.setImage(self.perc_on_path)
            if progress == 100:
                self.perc100.setImage(self.perc_on_path)

    def clearText(self):
        self.text_label3.setLabel('')
        self.text_label2.setLabel('')
        self.text_label.setLabel('')
