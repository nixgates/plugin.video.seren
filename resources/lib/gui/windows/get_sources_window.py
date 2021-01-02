# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import threading

from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g


class GetSourcesWindow(BaseWindow):
    def __init__(self, xml, location, item_information=None):
        super(GetSourcesWindow, self).__init__(xml, location,
                                               item_information=item_information)
        self.scraper_class = None

    def onInit(self):
        super(GetSourcesWindow, self).onInit()

    def update_properties(self, sources_information):
        # Set Resolution count properties
        self.setProperty('4k_sources', str(sources_information["torrents_quality"][0] +
                                           sources_information["hosters_quality"][0]))
        self.setProperty('1080p_sources', str(sources_information["torrents_quality"][1] +
                                              sources_information["hosters_quality"][1]))
        self.setProperty('720p_sources', str(sources_information["torrents_quality"][2] +
                                             sources_information["hosters_quality"][2]))
        self.setProperty('SD_sources', str(sources_information["torrents_quality"][3] +
                                           sources_information["hosters_quality"][3]))

        # Set total source type counts
        self.setProperty('total_torrents', str(len(sources_information["allTorrents"])))
        self.setProperty('cached_torrents', str(len(sources_information["torrentCacheSources"])))
        self.setProperty('hosters_sources', str(len(sources_information["hosterSources"])))
        self.setProperty('cloud_sources', str(len(sources_information["cloudFiles"])))
        self.setProperty('adaptive_sources', str(len(sources_information["adaptiveSources"])))

        # Set remaining providers string
        self.setProperty("remaining_providers_count", str((len(sources_information["remainingProviders"]))))

        self.setProperty("remaining_providers_list", g.color_string(' | ')
                         .join([i.upper() for i in sources_information["remainingProviders"]]))

        try:
            remaining_providers_list = self.getControlList(2000)
            remaining_providers_list.reset()
            remaining_providers_list.addItems(sources_information["remainingProviders"])
        except:
            pass

    def set_property(self, key, value):
        self.setProperty(key, value)

    def setProgress(self, progress):
        self.setProperty('progress', str(progress))

    def __del__(self):
        self.close()

    def show(self):
        threading.Thread(target=self.doModal).start()
        self.set_property('process_started', 'false')
        self.set_property('progress', '0')

    def set_scraper_class(self, scraper_class):
        self.scraper_class = scraper_class

    def onAction(self, action):
        if action.getId() in self.action_exitkeys_id:
            self.scraper_class.canceled = True
