import os, time, threading, json
from resources.lib.common import tools

# WINDOWS

def test_method(window, text):
    window.setText(text)

class persistant_background(tools.dialogWindow):

    def __init__(self):
        texture_path = os.path.join(tools.IMAGES_PATH, 'texture.png')
        self.texture = tools.imageControl(0, 0, 1280, 720, texture_path)
        self.addControl(self.texture)
        self.background = tools.imageControl(0, 0, 1280, 720, '')
        background_diffuse = '0x1FFFFFFF'
        self.background.setColorDiffuse(background_diffuse)
        self.addControl(self.background)
        self.panda_logo = tools.imageControl(605, 330, 70, 60, tools.PANDA_LOGO_PATH)
        self.addControl(self.panda_logo)
        self.text_label = tools.labelControl(0, 400, 1280, 50, '', font='font13', alignment=tools.XBFONT_CENTER_X)
        self.addControl(self.text_label)

    def setBackground(self, info):
        info = json.loads(tools.unquote(info))
        if 'showInfo' in info:
            background = info['showInfo']['art']['fanart']
        elif 'fanart' in info:
            background = info['fanart']
        else:
            background = info['art']['fanart']

        self.background.setImage(background)

    def setText(self, text):
        self.text_label.setLabel(str(text))


class smart_play_background(tools.dialogWindow):

    def __init__(self):
        self.return_data = 'Nothing'

        tools.closeBusyDialog()
        self.canceled = False
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

    def doModal(self, function, *args):

        if tools.getSetting('general.tempSilent') == 'false':
            window = self
        else:
            window = None

        args = (window,) + args
        thread = threading.Thread(target=function, args=args)
        thread.start()
        if window is not None:
            tools.kodiGui.WindowDialog.doModal(self)
        else:
            thread.join()

        return self.return_data

    def onAction(self, action):

        id = action.getId()
        if id == 92:
            self.canceled = True
        if id == 7:
            self.canceled = True

    def setBackground(self, url):
        self.background.setImage(url)
        pass

    def setText(self, text):
        self.text_label.setLabel(str(text))

    def setText2(self, text):
        self.text_label2.setLabel(str(text))

    def setText3(self, text):
        self.text_label3.setLabel(str(text))

    def setProgress(self, progress=0):
        progress = int(progress)
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

    def isCanceled(self):
        return self.canceled

    def runFunction(self):
        for i in range(0,5):
            self.setText(i)
            time.sleep(1)
        self.close()

    def clearText(self):
        self.text_label3.setLabel('')
        self.text_label2.setLabel('')
        self.text_label.setLabel('')