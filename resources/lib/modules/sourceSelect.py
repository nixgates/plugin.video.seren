# -*- coding: utf-8 -*-

import os

from resources.lib.common import tools


def build_display_title(source):
    if 'debrid_provider' in source:
        debrid_provider = tools.colorString(tools.shortened_debrid(source.get('debrid_provider', '')))
        if debrid_provider != '':
            debrid_provider = " " + debrid_provider + " |"
        else:
            tools.log('No Debrid Provider')
    else:
        debrid_provider = ''
    quality = tools.color_quality(source['quality'])
    release_title = tools.colorString(source['release_title'])
    info = source['info']
    if len(info) > 0:
        info = ' '.join(info)
        info = '| ' + info
    else:
        info = ''

    title = ''

    if source['type'] == 'torrent':
        size = tools.colorString(tools.source_size_display(source['size']))
        title = "%s |%s %s | %s %s\n%s" % (
            quality,
            debrid_provider,
            source['source'].upper(),
            size,
            info,
            tools.deaccentString(release_title).encode('utf-8')
        )
    if source['type'] == 'hoster':
        title = "%s |%s %s | %s %s\n%s" % (
            quality,
            debrid_provider,
            source['provider'].upper(),
            source['source'],
            info,
            tools.deaccentString(release_title).encode('utf-8'),
        )

    if tools.getSetting('general.sourceselectlines') == 'false':
        title = title.replace('\n', ' | ')

    return title


def sourceSelect(source_list, info):
    try:
        if len(source_list) == 0:
            return None
        display_list = []

        for source in source_list:
            display_list.append(build_display_title(source))

        if tools.getSetting('general.sourceselect') == '1':
            window = source_select_list(display_list, info)
            selection = window.doModal()
            del window

        elif tools.getSetting('general.sourceselect') == '0':
            selection = tools.showDialog.select(tools.addonName + ': %s' % tools.lang(32099).encode('utf-8'),
                                                display_list)

    except:
        import traceback
        traceback.print_exc()
        selection = -1

    if selection == -1:
        try:
            tools.playList.clear()
        except:
            pass
        tools.log('Source Selection was cancelled', 'info')
        return []

    return source_list[selection:]


class source_select_list(tools.dialogWindow):
    def __init__(self, display_list, info):
        self.position = -1
        texture_path = os.path.join(tools.IMAGES_PATH, 'texture.png')
        self.texture = tools.imageControl(0, 0, 1280, 720, texture_path)
        self.addControl(self.texture)
        self.background = tools.imageControl(0, 0, 1280, 720, '')
        background_diffuse = '0x1FFFFFFF'
        self.background.setColorDiffuse(background_diffuse)
        self.boxImage = tools.imageControl(40, 180, 1200, 500, os.path.join(tools.IMAGES_PATH, 'box2.jpg'))
        self.boxImage.setColorDiffuse('0x1FFFFFFF')
        self.addControl(self.background)
        self.addControl(self.boxImage)
        if 'showInfo' in info:
            self.background.setImage(info['showInfo']['art']['fanart'])
        else:
            self.background.setImage(info['fanart'])
        self.panda_logo = tools.imageControl(605, 20, 70, 60, tools.PANDA_LOGO_PATH)
        self.addControl(self.panda_logo)
        #
        # When the "display_title" label is set for some reason it ends up setting the text for every other label
        # in any window while in the addon from then on, mind boggling, need to figure out why
        #
        # self.dispaly_title = tools.labelControl(310, 100, 1000, 100,'', font='font24', textColor='0xFFFFFFFF')
        # if 'showInfo' in info:
        #     label_text = '[B]%s S%sE%s[/B]' % (info['showInfo']['info']['tvshowtitle'],
        #                                 str(info['episodeInfo']['info']['season']).zfill(2),
        #                                 str(info['episodeInfo']['info']['episode']).zfill(2))
        # else:
        #     label_text = '[B]%s (%s)[/B]' % (info['title'], info['year'])
        # self.dispaly_title.setLabel(label_text)
        # self.addControl(self.dispaly_title)

        # This looks ridiculous below but it's needed as the Kodi Gui modules won't accept itemHeight as a Keyword

        item_height = 55

        if tools.getSetting('general.sourceselectlines') == 'false':
            item_height = 30

        self.list = tools.listControl(60, 200, 1160, 490, 'font13', '0xFFFFFFFF', '',
                                      os.path.join(tools.IMAGES_PATH, 'highlight11.png'),
                                      '', 0, 0, 0, 0, item_height
                                      )
        # self.list = tools.listControl(60, 280, 1160, 490, buttonFocusTexture=os.path.join(tools.IMAGES_PATH, 'highlight11.png'))
        self.addControl(self.list)
        self.list.setSpace(100)
        self.list.addItems(display_list)
        # self.thumbnail = tools.imageControl(40, 100, 100, 150, '')
        # if 'showInfo' in info:
        #     self.thumbnail.setImage(info['episodeInfo']['art']['poster'])
        # else:
        #     self.thumbnail.setImage(info['art']['poster'])
        # self.addControl(self.thumbnail)
        self.setFocus(self.list)
        self.canceled = False

    def onAction(self, action):

        print('Action = %s' % action.getId())
        id = action.getId()
        if id == 92 or id == 10:
            self.close()
            self.position = -1
            self.close()

        if id == 7:
            self.position = self.list.getSelectedPosition()
            self.close()

        if id == 0:
            pass

    def doModal(self):
        tools.kodiGui.WindowDialog.doModal(self)
        self.clearProperties()
        return self.position

    def onControl(self, control):
        if self.list.getId() == control.getId():
            self.position = self.list.getSelectedPosition()
            self.close()
