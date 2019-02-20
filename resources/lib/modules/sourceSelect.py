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
        self.addControl(self.background)

        if tools.getSetting('general.sourceselectlines') == 'false':
            item_height = 30
        else:
            item_height = 55

        self.source_list = tools.listControl(20, 130, 760, 640, 'font12', '0xFFFFFFFF', '',
                                             os.path.join(tools.IMAGES_PATH, 'highlight11.png'),
                                             '', 0, 0, 0, 0, item_height)
        self.addControl(self.source_list)
        self.source_list.addItems(display_list)

        self.boxImage = tools.imageControl(20, 100, 760, 680, os.path.join(tools.IMAGES_PATH, 'box2.jpg'))
        self.boxImage.setColorDiffuse('0x1FFFFFFF')
        self.addControl(self.boxImage)

        self.poster = tools.imageControl(890, 140, 280, 400, '')
        self.addControl(self.poster)

        info_label = tools.labelControl(800, 555, 460, 180, "", font="font10", alignment=tools.XBFONT_CENTER_X)
        self.addControl(info_label)
        info_label_string = '%s: %s | %s: %s | %s: %s mins'

        if 'showInfo' in info:
            self.background.setImage(info['showInfo']['art'].get('fanart', ''))
            self.poster.setImage(info['showInfo']['art'].get('poster', ''))

            info_label_string %= (tools.colorString('RATING'),
                                  info['episodeInfo']['info']['rating'],
                                  tools.colorString('DATE'),
                                  info['episodeInfo']['info']['premiered'],
                                  tools.colorString('DURATION'),
                                  str(int(info['episodeInfo']['info']['duration']) / 60))

            season_string = tools.labelControl(810, 100, 430, 50, "", font='font27_narrow', alignment=tools.XBFONT_CENTER_X)
            self.addControl(season_string)
            season_string.setLabel('%s - %s' % ('Season %s' %
                                                (tools.colorString(info['episodeInfo']['info']['season'])),
                                                'Episode %s' %
                                                (tools.colorString(info['episodeInfo']['info']['episode']))))

            plot_outline = tools.multi_text(830, 580, 430, 100, font='font12')
            self.addControl(plot_outline)
            plot_outline.setText(info['episodeInfo']['info']['plot'])

        else:

            info_label_string %= (tools.colorString('RATING'),
                                  info['rating'],
                                  tools.colorString('YEAR'),
                                  info['year'],
                                  tools.colorString('DURATION'),
                                  str(int(info['duration']) / 60))

            self.background.setImage(info['art'].get('fanart', ''))
            self.poster.setImage(info['art'].get('poster', ''))

            plot_outline = tools.multi_text(830, 580, 430, 100, font='font12')
            self.addControl(plot_outline)
            plot_outline.setText(info['plot'])

        info_label.setLabel('[B]%s[/B]' % info_label_string)

        self.panda_logo = tools.imageControl(605, 20, 70, 60, tools.PANDA_LOGO_PATH)
        self.addControl(self.panda_logo)

        self.setFocus(self.source_list)
        self.canceled = False

    def onAction(self, action):

        id = action.getId()
        if id == 92 or id == 10:
            self.close()
            self.position = -1
            self.close()

        if id == 7:
            self.position = self.source_list.getSelectedPosition()
            self.close()

        if id == 0:
            pass

    def doModal(self):
        tools.kodiGui.WindowDialog.doModal(self)
        self.clearProperties()
        return self.position

    def onControl(self, control):
        if self.source_list.getId() == control.getId():
            self.position = self.source_list.getSelectedPosition()
            self.close()
