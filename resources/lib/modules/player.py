# -*- coding: utf-8 -*-

import datetime
import json
import sys
import xmlrpclib

try:
    import AddonSignals
except:
    pass

from resources.lib.common import tools
from resources.lib.indexers import trakt
from resources.lib.modules import smartPlay

try:
    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
except:
    pass


class serenPlayer(tools.player):
    def __init__(self):
        tools.player.__init__(self)
        self.trakt_api = trakt.TraktAPI()
        self.pre_cache_initiated = False
        self.play_next_triggered = False
        self.trakt_id = None
        self.media_type = None
        self.offset = None
        self.media_length = 0
        self.current_time = 0
        self.args = {}
        self.playback_started = False
        self.scrobbled = False

    def play_source(self, stream_link, args):

        try:
            self.pre_cache_initiated = False
            if stream_link is None:
                tools.playList.clear()
                raise Exception
            self.args = args

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

            if tools.playList.getposition() == 0 and tools.getSetting('smartPlay.traktresume') == 'true' \
                    and tools.getSetting('trakt.auth') is not '':
                tools.log('Getting Trakt Resume Point', 'info')
                self.traktBookmark()

            tools.resolvedUrl(syshandle, True, item)

            self.keepAlive()

            try:
                tools.closeBusyDialog()
            except:
                pass

        except:
            import traceback
            traceback.print_exc()

    def onPlayBackSeek(self, time, seekOffset):

        seekOffset /= 1000
        self.traktStartWatching(offset=seekOffset)

    def onPlayBackSeekChapter(self, chapter):

        self.traktStartWatching()
        pass

    def onPlayBackStarted(self):
        self.start_playback()
        pass

    def onAVStarted(self):
        self.start_playback()
        pass

    def onPlayBackError(self):

        sys.exit(1)

    def start_playback(self):

        try:
            if self.playback_started:
                return
            self.playback_started = True
            tools.execute('Dialog.Close(all,true)')
            self.current_time = self.getTime()
            self.media_length = self.getTotalTime()

            if 'episodeInfo' in self.args and tools.getSetting('smartplay.upnext') == 'true':
                source_id = 'plugin.video.%s' % tools.addonName.lower()
                return_id = 'plugin.video.%s_play_action' % tools.addonName.lower()

                try:
                    next_info = self.next_info()
                    AddonSignals.sendSignal('upnext_data', next_info, source_id=source_id)
                    AddonSignals.registerSlot('upnextprovider', return_id, self.signals_callback)
                except:
                    import traceback
                    traceback.print_exc()
                    pass

            if tools.getSetting('general.smartplay') is not 'false' and self.media_type is 'episode':
                if int(tools.playList.getposition()) == (tools.playList.size() - 1):
                    self.next_season = smartPlay.SmartPlay(self.args).append_next_season()

            self.traktStartWatching()

        except:
            import traceback
            traceback.print_exc()
            pass

    def onPlayBackEnded(self):
        pass

    def onPlayBackStopped(self):
        self.traktStopWatching()
        self.scrobbled = True

        tools.playList.clear()

    def onPlayBackPaused(self):

        self.traktPause()

    def onPlayBackResumed(self):

        self.traktStartWatching()

    def getWatchedPercent(self, offset=None):

        try:
            position = self.getTime()
            if position is not 0:
                self.current_time = position
            total_length = self.getTotalTime()
            if total_length is not 0:
                self.media_length = total_length
        except:
            pass

        current_position = self.current_time
        total_length = self.media_length
        watched_percent = 0

        if int(total_length) == 0:
            try:
                total_length = self.getTotalTime()
            except:
                return

        if offset is not None:
            try:
                current_position += offset
            except:
                pass

        if int(total_length) is not 0:
            try:
                watched_percent = float(current_position) / float(total_length) * 100
                if watched_percent > 100:
                    watched_percent = 100
            except:
                import traceback
                traceback.print_exc()
                pass

        return watched_percent

    def traktStartWatching(self, offset=None):

        if not self.trakt_integration() or self.scrobbled:
            return

        post_data = self.buildTraktObject(offset=offset)

        self.trakt_api.post_request('scrobble/start', postData=post_data, limit=False)

    def traktStopWatching(self, override_progress=None):

        if not self.trakt_integration() or self.scrobbled:
            return

        post_data = self.buildTraktObject(override_progress=override_progress)

        self.trakt_api.post_request('scrobble/stop', postData=post_data, limit=False)

        try:
            if post_data['progress'] > 90:
                if self.media_type == 'episode':
                    from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
                    TraktSyncDatabase().mark_episode_watched(self.args['showInfo']['ids']['trakt'],
                                                             self.args['info']['season'], self.args['info']['episode'])
                if self.media_type == 'movie':
                    from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase
                    TraktSyncDatabase().mark_movie_watched(self.trakt_id)
        except:
            pass

    def traktPause(self):

        if not self.trakt_integration():
            return

        post_data = self.buildTraktObject()

        self.trakt_api.post_request('scrobble/pause', postData=post_data, limit=False)

    def buildTraktObject(self, offset=None, override_progress=None):

        try:
            if self.media_type == 'episode':
                post_data = {'episode': {'ids': {'trakt': self.trakt_id}}}
            else:
                post_data = {'movie': {'ids': {'trakt': self.trakt_id}}}

            progress = int(self.getWatchedPercent(offset))

            if override_progress is not None:
                progress = override_progress
            if progress > 0:
                post_data['progress'] = progress
            else:
                post_data['progress'] = 0

            return post_data
        except:
            import traceback
            traceback.print_exc()

    def keepAlive(self):

        for i in range(0, 240):
            if self.isPlayingVideo(): break
            tools.kodi.sleep(1000)

        while self.isPlaying():
            try:
                if not self.playback_started:
                    tools.kodi.sleep(5000)
                    continue
                if not self.playback_started:
                    self.start_playback()

                if self.offset is not None and int(self.offset) != 0:
                    tools.log("Seeking %s seconds" % self.offset, 'info')
                    self.seekTime(self.offset)
                    self.offset = None
                else:
                    tools.log("No seeking applied", 'info')
                try:
                    position = self.getTime()
                    self.current_time = position
                    total_length = self.getTotalTime()
                    self.media_length = total_length
                except:
                    pass
                if self.pre_cache_initiated is False:
                    try:
                        if self.getWatchedPercent() > 80 and tools.getSetting('smartPlay.preScrape') == 'true':
                            self.pre_cache_initiated = True
                            smartPlay.SmartPlay(self.args).pre_scrape()
                    except:
                        pass

                # We manually check an signal this as Kodi always calls the playbackEnded call after a new player
                # class is created, marking the wrong episode watched
                if self.getWatchedPercent() > 90 and not self.scrobbled:
                    self.traktStopWatching()
                    self.scrobbled = True

            except:
                import traceback
                traceback.print_exc()
                tools.kodi.sleep(1000)
                continue

            tools.kodi.sleep(1000)

        self.traktStopWatching()

    def traktBookmark(self):

        if not self.trakt_integration():
            return
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
                    prompt = tools.showDialog.yesno(tools.addonName + ': Resume', '%s %s' %
                                                    (tools.lang(32092),
                                                     datetime.timedelta(seconds=offset)),
                                                    nolabel="Resume", yeslabel="Restart")
                    if prompt == 0:
                        self.offset = offset
                    else:
                        return
            else:
                self.offset = offset
        except:
            import traceback
            traceback.print_exc()

    def signals_callback(self, data):

        if not self.play_next_triggered:
            if not self.scrobbled:
                try:
                    self.traktStopWatching()
                    self.scrobbled = True
                except:
                    pass
            self.play_next_triggered = True
            # Using a seek here as playnext causes Kodi gui to wig out. So we seek instead so it looks more graceful
            self.seekTime(self.media_length)

    def trakt_integration(self):

        if tools.getSetting('trakt.auth') == '':
            return False
        else:
            if tools.getSetting('trakt.scrobbling') == 'true':
                return True

    def next_info(self):

        current_info = self.args
        current_episode = {}
        current_episode["episodeid"] = current_info['episodeInfo']['ids']['trakt']
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
        next_episode["episodeid"] = next_info['episodeInfo']['ids']['trakt']
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
        play_info["item_id"] = current_info['episodeInfo']['ids']['trakt']

        next_info = {
            "current_episode": current_episode,
            "next_episode": next_episode,
            "play_info": play_info,
            "notification_time": int(tools.getSetting('smartplay.upnexttime'))
        }

        return next_info

