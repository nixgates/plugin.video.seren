from resources.lib.common import tools
import os

def build_display_title(source):
    debrid_provider = tools.colorString(tools.shortened_debrid(source.get('debrid_provider', '')))
    quality = tools.color_quality(source['quality'])
    release_title = tools.colorString(source['release_title'])
    info = str(source['info']).replace('[','').replace(']','').replace('\'','')[1:]
    if info == '':
        pass
    else:
        info = '- %s' % info

    if source['type'] == 'torrent':
        size = tools.colorString(tools.source_size_display(source['size']))
        title = "%s - %s | %s - %s -%s" % (debrid_provider,
                                           quality,
                                           size,
                                           source['source'].upper(),
                                           release_title
                                           )
    if source['type'] == 'hoster':
        title = "%s - %s - %s | %s - %s %s" % (debrid_provider,
                                               quality,
                                               source['provider'].upper(),
                                               source['source'],
                                               release_title,
                                               info)

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
            selection = tools.showDialog.select(tools.addonName + ': Source Selection', display_list)

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
        #self.dispaly_title = tools.labelControl(310, 100, 1000, 100,'', font='font24', textColor='0xFFFFFFFF')
        #if 'showInfo' in info:
        #     label_text = '[B]%s S%sE%s[/B]' % (info['showInfo']['info']['tvshowtitle'],
        #                                 str(info['episodeInfo']['info']['season']).zfill(2),
        #                                 str(info['episodeInfo']['info']['episode']).zfill(2))
        # else:
        #     label_text = '[B]%s (%s)[/B]' % (info['title'], info['year'])
        #self.dispaly_title.setLabel(label_text)
        #self.addControl(self.dispaly_title)
        self.list = tools.listControl(60, 200, 1160, 490, buttonFocusTexture=os.path.join(tools.IMAGES_PATH, 'highlight11.png'))
        #self.list = tools.listControl(60, 280, 1160, 490, buttonFocusTexture=os.path.join(tools.IMAGES_PATH, 'highlight11.png'))
        self.addControl(self.list)
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
        if id == 92:
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
        tools.log('Selected Position - %s' % self.list.getSelectedPosition())
        self.clearProperties()
        return self.position
