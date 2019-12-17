from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.common import tools

class StillWatching(BaseWindow):

    def __init__(self, xml_file, xml_location, actionArgs=None):

        try:
            self.player = tools.player()
            self.playing_file = self.player.getPlayingFile()
            self.closed = False
            self.duration = int(tools.getSetting('playingnext.time'))
            super(StillWatching, self).__init__(xml_file, xml_location, actionArgs=actionArgs)

        except:
            import traceback
            traceback.print_exc()

    def onInit(self):
        self.wait_for_timeout()

    def calculate_percent(self):
        return ((int(self.player.getTotalTime()) - int(self.player.getTime())) / float(self.duration)) * 100

    def wait_for_timeout(self):

        try:
            try:
                progress_bar = self.getControl(3014)
            except:
                progress_bar = None

            while (int(self.player.getTotalTime()) - int(self.player.getTime())) > 1 and not self.closed and \
                    self.playing_file == self.player.getPlayingFile():
                tools.kodi.sleep(500)
                if progress_bar is not None:
                    progress_bar.setPercent(self.calculate_percent())

            if not self.closed:
                self.player.pause()
        except:
            import traceback
            traceback.print_exc()

        self.close()

    def doModal(self):
        try:
            super(StillWatching, self).doModal()
        except:
            import traceback
            traceback.print_exc()

    def close(self):
        self.closed = True
        super(StillWatching, self).close()

    def onClick(self, control_id):
        self.handle_action(7, control_id)

    def handle_action(self, action, control_id=None):
        if control_id is None:
            control_id = self.getFocusId()

        if control_id == 3001:
            self.close()
        if control_id == 3002:
            self.stop()
            self.close()

    def onAction(self, action):

        action = action.getId()

        if action == 92 or action == 10:
            # BACKSPACE / ESCAPE
            self.close()

        if action == 7:
            self.handle_action(action)
            return

