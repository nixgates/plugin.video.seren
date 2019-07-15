# -*- coding: utf-8 -*-

import os
import threading
from resources.lib.common import tools
from resources.lib.gui.windows.base_window import BaseWindow
import copy

class GetSources(BaseWindow):

    def __init__(self, xml_file, xml_location, actionArgs=None):
        super(GetSources, self).__init__(xml_file, xml_location, actionArgs=actionArgs)
        self.setProperty('process_started', 'false')
        self.position = -1
        self.canceled = False
        self.display_list = None
        self.return_data = None
        self.args = actionArgs
        self.progress = 0
        self.background_dialog = None
        self.setProperty('progress', '0')
        self.setProperty('loading.ico', os.path.join(tools.IMAGES_PATH, 'loading2.gif'))
        self.setProperty('ico.trans.upper', os.path.join(tools.IMAGES_PATH, 'trans-fox-upper.png'))
        self.setProperty('ico.trans.lower', os.path.join(tools.IMAGES_PATH, 'trans-fox-lower.png'))
        tools.closeBusyDialog()

    def onInit(self):
        threading.Thread(target=self.getSources, args=(self.args,)).start()

        pass

    def doModal(self):
        try:
            if tools.getSetting('general.tempSilent') == 'true':
                self.silent = True
            try:
                self.display_style = int(tools.getSetting('general.scrapedisplay'))
            except:
                pass

            if not self.silent and self.display_style == 1:
                self.background_dialog = tools.bgProgressDialog()
                self.getSources(self.args)

            elif not self.silent and self.display_style == 0:
                super(GetSources, self).doModal()
            else:
                self.getSources(self.args)

            return self.return_data
        except:
            import traceback
            traceback.print_exc()
            self.close()

    def getSources(self, args):
        """
        Entry Point for initiating scraping
        :param args:
        :return:
        """

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
            if self.display_style == 0:
                self.background.setImage(url)
        pass

    def close(self):
        if not self.silent:
            if self.display_style == 0:
                tools.dialogWindow.close(self)
            elif self.display_style == 1:
                self.background_dialog.close()

    def setText(self, text=None):
        if self.silent:
            return
        if self.display_style == 0:
            if text is not None:
                self.setProperty('notification_text', str(text))
            self.update_properties()
        elif self.display_style == 1:
            self.background_dialog.update(self.progress, message=text)

    def update_properties(self):

        # Set Resolution count properties
        self.setProperty('4k_sources', str(self.torrents_qual_len[0] + self.hosters_qual_len[0]))
        self.setProperty('1080p_sources', str(self.torrents_qual_len[1] + self.hosters_qual_len[1]))
        self.setProperty('720p_sources', str(self.torrents_qual_len[2] + self.hosters_qual_len[2]))
        self.setProperty('SD_sources', str(self.torrents_qual_len[3] + self.hosters_qual_len[3]))

        # Set total source type counts
        # self.setProperty('total_torrents', str(len([i for i in self.allTorrents])))

        self.setProperty('total_torrents', str(len([i for i in self.allTorrents])))
        self.setProperty('cached_torrents', str(len([i for i in self.torrentCacheSources])))
        self.setProperty('hosters_sources', str(len([i for i in self.hosterSources])))
        self.setProperty('cloud_sources', str(len([i for i in self.cloud_files])))

        # Set remaining providers string
        self.setProperty("remaining_providers_count", str((len(self.remainingProviders))))
        self.setProperty("remaining_providers_list", ' | '.join([tools.colorString(i.upper())
                                                                for i in self.remainingProviders]))

    def setProgress(self):
        if not self.silent:
            if self.display_style == 0:
                self.setProperty('progress', str(self.progress))
            elif self.display_style == 1:
                self.background_dialog.update(self.progress)

    def clearText(self):
        if self.silent:
            return
        self.text_label3.setLabel('')
        self.text_label2.setLabel('')
        self.text_label.setLabel('')
