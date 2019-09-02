
from resources.lib.common import tools
from resources.lib.gui.windows.base_window import BaseWindow

class PersistentBackground(BaseWindow):

    def __init__(self, xml_file, location, actionArgs=None):

        super(PersistentBackground, self).__init__(xml_file, location, actionArgs=actionArgs)

        if actionArgs is None:
            return

        tools.closeBusyDialog()

    def setText(self, text):
        self.setProperty('notification_text', str(text))