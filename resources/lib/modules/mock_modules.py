from resources.lib.modules.resolver import Resolver as _Resolver


class Resolver(_Resolver):

    def onInit(self):
        pass

    def onAction(self, action):
        self.close()


class KodiPlayer:

    def __init__(self):
        self.playing_file = 'http://testurl.com/Barry.S02E01.1080p.TVShows.mkv'

    def getPlayingFile(self):
        return self.playing_file

    def getTotalTime(self):
        return 2048

    def getTime(self):
        return 2045

    def pause(self):
        pass

    def seekTime(self, time):
        pass

    def stop(self):
        pass
