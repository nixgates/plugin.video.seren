from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.common import tools

class PlayingNext(BaseWindow):

    def __init__(self, xml_file, xml_location, actionArgs=None):

        try:
            super(PlayingNext, self).__init__(xml_file, xml_location, actionArgs=actionArgs)
            self.player = tools.player()
            self.playing_file = self.player.getPlayingFile()
            self.duration = int(tools.getSetting('playingnext.time'))
            self.closed = False
            self.actioned = None
        except:
            import traceback
            traceback.print_exc()

    def onInit(self):
        self.background_tasks()

    def calculate_percent(self):
        return ((int(self.player.getTotalTime()) - int(self.player.getTime())) / float(self.duration)) * 100

    def background_tasks(self):
        try:
            try:
                progress_bar = self.getControl(3014)
            except:
                progress_bar = None

            while 120 > (int(self.player.getTotalTime()) - int(self.player.getTime())) > 1 and not self.closed:
                tools.kodi.sleep(500)
                if progress_bar is not None:
                    progress_bar.setPercent(self.calculate_percent())

            if tools.getSetting('playingnext.defaultaction') == '1' and\
                    self.playing_file == self.player.getPlayingFile() and\
                    not self.actioned:
                self.player.pause()
        except:
            import traceback
            traceback.print_exc()
            pass

        self.close()

    def doModal(self):
        try:
            super(PlayingNext, self).doModal()
        except:
            import traceback
            traceback.print_exc()

    def close(self):
        self.closed = True
        super(PlayingNext, self).close()

    def onClick(self, control_id):
        self.handle_action(7, control_id)

    def handle_action(self, action, control_id=None):
        if control_id is None:
            control_id = self.getFocusId()

        if control_id == 3001:
            self.actioned = True
            self.player.seekTime(self.player.getTotalTime())
            self.close()
        if control_id == 3002:
            self.actioned = True
            self.close()

    def onAction(self, action):

        action = action.getId()

        if action == 92 or action == 10:
            # BACKSPACE / ESCAPE
            self.close()

        if action == 7:
            self.handle_action(action)
            return

