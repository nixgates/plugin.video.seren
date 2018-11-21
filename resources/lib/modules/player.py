import sys, datetime, json
from resources.lib.common import tools
from resources.lib.indexers import trakt
from resources.lib.modules import smartPlay
import AddonSignals

sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])

class serenPlayer(tools.player):

    def __init__(self):
        tools.player.__init__(self)
        self.trakt_api = trakt.TraktAPI()
        self.pre_cache_initiated = False
        self.play_next_triggered = False

    def play_source(self, stream_link, args):
        try:
            self.pre_cache_initiated = False
            if stream_link is None:
                tools.playList.clear()
                raise Exception
            self.args = args
            self.offset = None
            self.media_length = 0
            self.current_time = 0
            self.stopped = False

            if tools.checkOmniConnect():
                port = tools.getSetting('omni.port')
                stream_link = 'http://localhost:%s?BLASTURL=%s' % (port, stream_link)

            item = tools.menuItem(path=stream_link)

            if 'episodeInfo' in args:
                self.media_type = 'episode'
                self.trakt_id = args['episodeInfo']['ids']['trakt']
                item.setArt(args['episodeInfo']['art'])
                item.setInfo(type='video', infoLabels=args['episodeInfo']['info'])
            else:
                self.media_type = 'movie'
                self.trakt_id = args['ids']['trakt']
                item.setArt(args['art'])
                item.setInfo(type='video', infoLabels=args['info'])

            if tools.playList.getposition() == 0 and tools.getSetting('smartPlay.traktresume') == 'true':
                tools.log('Getting Trakt Resume Point', 'info')
                self.traktBookmark()

            tools.log('Self Offset is equal to %s' % self.offset, 'info')


            tools.resolvedUrl(syshandle, True, item)

            try:tools.busyDialog.close()
            except:pass

            self.keepAlive()
        except:
            import traceback
            traceback.print_exc()

    def onPlayBackSeek(self, time, seekOffset):
        self.traktStartWatching()
        pass

    def onPlayBackStarted(self):
        try:
            tools.execute('Dialog.Close(all,true)')
            self.current_time = self.getTime()
            self.media_length = self.getTotalTime()

            if self.offset is not None and int(self.offset) != 0:
                tools.log("Seeking %s seconds" % self.offset, 'info')
                self.seekTime(self.offset)
                self.offset = None
            else:
                tools.log("No seeking applied")

            self.traktStartWatching()
            if 'episodeInfo' in self.args and tools.getSetting('smartplay.upnext') == 'true':
                try:
                    next_info = self.next_info()
                    AddonSignals.sendSignal('upnext_data', next_info, source_id='plugin.video.%s' % tools.addonName)
                    AddonSignals.registerSlot('upnextprovider', 'plugin.video.%s_play_action' %
                                              tools.addonName, self.signals_callback)
                except:
                    import traceback
                    traceback.print_exc()
                    pass
        except:
            pass


    def onPlayBackEnded(self):
        self.close_omni()
        self.traktStopWatching(finished=True)
        if tools.getSetting('general.smartplay') is not 'false' and self.media_type is 'episode':
            if int(tools.playList.getposition()) == -1:
                self.next_season = smartPlay.SmartPlay(self.args).return_next_season()
        self.stopped = True

    def onPlayBackStopped(self):
        self.close_omni()
        watched_percent = self.getWatchedPercent()
        if watched_percent < 90.00:
            self.traktPause()
        else:
            self.traktStopWatching()

        tools.playList.clear()

        self.stopped = True

    def onPlayBackPaused(self):
        self.traktPause()

    def onPlayBackResumed(self):
        self.traktStartWatching()

    def getWatchedPercent(self):
        if self.media_length is not 0:
            try:
                return float(self.current_time) / float(self.media_length) * 100
            except ZeroDivisionError:
                return 0

    def traktStartWatching(self):

        post_data = self.buildTraktObject()
        self.trakt_api.post_request('scrobble/start', postData=post_data, limit=False)

    def traktStopWatching(self, finished=False):

        post_data = self.buildTraktObject(finished=finished)
        self.trakt_api.post_request('scrobble/stop', postData=post_data, limit=False)

    def traktPause(self):
        post_data = self.buildTraktObject()
        self.trakt_api.post_request('scrobble/pause', postData=post_data, limit=False)

    def buildTraktObject(self, finished=False):
        try:

            if self.media_type == 'episode':
                post_data = {'episode': {'ids': {'trakt': self.trakt_id}}}
            else:
                post_data = {'movies': {'ids': {'trakt': self.trakt_id}}}
            if finished == True:
                post_data['progress'] = 100
            else:
                progress = int(self.getWatchedPercent())
                if progress > 0:
                    post_data['progress'] = progress
                else:
                    post_data['progress'] = 0

            return post_data
        except:
            import traceback
            traceback.print_exc()

    def keepAlive(self):
        while not self.stopped:
            if self.isPlaying():
                try:
                    self.current_time = self.getTime()
                    if self.pre_cache_initiated is False:
                        if self.getWatchedPercent() > 80 and tools.getSetting('smartPlay.preScrape') == 'true':
                            self.pre_cache_initiated = True
                            smartPlay.SmartPlay(self.args).pre_scrape()
                except:
                    pass
            tools.kodi.sleep(1000)
        pass

    def traktBookmark(self):
        try:
            offset = None
            if self.media_type == 'episode':
                progress = self.trakt_api.json_response('sync/playback/episodes?extended=full')
                for i in progress:
                    if self.trakt_id == i['episode']['ids']['trakt']:
                        # Calculating Offset to seconds
                        offset = int((float(i['progress'] / 100) * int(i['episode']['runtime']) * 60))
            else:
                progress = self.trakt_api.json_response('sync/playback/movies?extended=full')
                for i in progress:
                    if self.trakt_id == i['movie']['ids']['trakt']:
                        # Calculating Offset to seconds
                        offset = int((float(i['progress'] / 100) * int(i['movie']['runtime']) * 60))


            if tools.getSetting('smartPlay.bookmarkprompt') == 'true':
                if offset is not None and offset is not 0:
                    prompt = tools.showDialog.yesno(tools.addonName + ': Resume', 'Resume from %s' %
                                                    datetime.timedelta(seconds=offset),
                                                    nolabel="Resume", yeslabel="Restart")
                    if prompt == 0:
                        tools.log('Found progress, resuming from %s ' % str(offset * 60), 'error')
                        self.offset = offset
                    else:
                        return
            else:
                self.offset = offset
        except:
            import traceback
            traceback.print_exc()

    def close_omni(self):
        if tools.checkOmniConnect():
            import requests
            port = tools.getSetting('omni.port')
            stream_link = 'http://localhost:%s?BLASTURL=%s' % (port, 'close')
            requests.get(stream_link)

    def signals_callback(self, data):
        if not self.play_next_triggered:
            self.pause()
            self.playnext()
            self.play_next_triggered = True

    def next_info(self):
        current_info = self.args
        current_episode = {}
        current_episode["episodeid"] = current_info['episodeInfo']['info']['imdbnumber']
        current_episode["tvshowid"] = current_info['showInfo']['info']['imdbnumber']
        current_episode["title"] = current_info['episodeInfo']['info']['title']
        current_episode["art"] = {}
        current_episode["art"]["tvshow.poster"] = current_info['episodeInfo']['art']['poster']
        current_episode["art"]["thumb"] = current_info['episodeInfo']['art']['thumb']
        current_episode["art"]["tvshow.fanart"] = current_info['episodeInfo']['art']['fanart']
        current_episode["art"]["tvshow.landscape"] = current_info['episodeInfo']['art']['fanart']
        current_episode["art"]["tvshow.clearart"] = ''
        current_episode["art"]["tvshow.clearlogo"] = ''
        current_episode["plot"] = current_info['episodeInfo']['info']['plot']
        current_episode["showtitle"] = current_info['showInfo']['info']['tvshowtitle']
        current_episode["playcount"] = 0
        current_episode["season"] = current_info['episodeInfo']['info']['season']
        current_episode["episode"] = current_info['episodeInfo']['info']['episode']
        current_episode["rating"] = current_info['episodeInfo']['info']['rating']
        current_episode["firstaired"] = current_info['episodeInfo']['info']['premiered']

        current_position = tools.playList.getposition()
        url = tools.playList[current_position + 1].getPath()
        params = dict(tools.parse_qsl(url.replace('?', '')))
        next_info = json.loads(params.get('actionArgs'))


        next_episode = {}
        next_episode["episodeid"] = next_info['episodeInfo']['info']['imdbnumber']
        next_episode["tvshowid"] = next_info['showInfo']['info']['imdbnumber']
        next_episode["title"] = next_info['episodeInfo']['info']['title']
        next_episode["art"] = {}
        next_episode["art"]["tvshow.poster"] = next_info['episodeInfo']['art']['poster']
        next_episode["art"]["thumb"] = next_info['episodeInfo']['art']['thumb']
        next_episode["art"]["tvshow.fanart"] = next_info['episodeInfo']['art']['fanart']
        next_episode["art"]["tvshow.landscape"] = next_info['episodeInfo']['art']['fanart']
        next_episode["art"]["tvshow.clearart"] = ''
        next_episode["art"]["tvshow.clearlogo"] = ''
        next_episode["plot"] = next_info['episodeInfo']['info']['plot']
        next_episode["showtitle"] = next_info['showInfo']['info']['tvshowtitle']
        next_episode["playcount"] = 0
        next_episode["season"] = next_info['episodeInfo']['info']['season']
        next_episode["episode"] = next_info['episodeInfo']['info']['episode']
        next_episode["rating"] = next_info['episodeInfo']['info']['rating']
        next_episode["firstaired"] = next_info['episodeInfo']['info']['premiered']

        play_info = {}
        play_info["item_id"] = current_info['episodeInfo']['info']['imdbnumber']

        next_info = {
            "current_episode": current_episode,
            "next_episode": next_episode,
            "play_info": play_info,
            "notification_time": int(tools.getSetting('smartplay.upnexttime'))
        }
        return next_info

