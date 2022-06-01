# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.gui.windows.download_manager import DownloadManager
from resources.lib.gui.windows.get_sources_window import GetSourcesWindow
from resources.lib.gui.windows.resolver_window import ResolverWindow


class Resolver(ResolverWindow):
    def onInit(self, test=False):
        super(Resolver, self).onInit(True)

    def onAction(self, action):
        self.close()


class GetSources(GetSourcesWindow):
    class MockScraperClass(object):
        canceled = False

    def onInit(self):
        super(GetSources, self).onInit()
        self.set_scraper_class(self.MockScraperClass())

    def onAction(self, action):
        super(GetSources, self).onAction(action)
        self.close()


class KodiPlayer:
    def __init__(self):
        self.playing_file = "http://testurl.com/Barry.S02E01.1080p.TVShows.mkv"

    def isPlaying(self):
        return True

    def getPlayingFile(self):
        return self.playing_file

    def getTotalTime(self):
        return 2048

    def getTime(self):
        return 2045

    def pause(self):
        """
        Over write normal behaivour
        :return:
        """
        pass

    def seekTime(self, time):
        """
        Over write normal behaivour
        :return:
        """
        pass

    def stop(self):
        """
        Over write normal behaivour
        :return:
        """
        pass


class DownloadManagerWindow(DownloadManager):
    def __init__(self, xml_file, location, item_information=None, mock_downloads=None):
        super(DownloadManagerWindow, self).__init__(xml_file, location, item_information)
        self.downloads = mock_downloads if mock_downloads else []

    def update_download_info(self):
        pass
