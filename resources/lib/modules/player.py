# -*- coding: utf-8 -*-

import datetime
import sys

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
        self.playback_resumed = False
        self.original_action_args = ''
        tools.player.__init__(self)


    def play_source(self, stream_link, args):

        try:
            self.pre_cache_initiated = False
            if stream_link is None:
                tools.cancelPlayback()
                raise Exception
            self.original_action_args = args

            args = tools.get_item_information(args)

            self.args = args

            item = tools.menuItem(path=stream_link)

            if 'showInfo' in args:
                self.media_type = 'episode'
                self.trakt_id = args['ids']['trakt']
                item.setArt(args['art'])
                item.setUniqueIDs(args['ids'])
                item.setInfo(type='video', infoLabels=args['info'])
            else:
                self.media_type = 'movie'
                self.trakt_id = args['ids']['trakt']
                item.setUniqueIDs(args['ids'])
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

            self.traktStartWatching()

            tools.execute('Dialog.Close(all,true)')

            self.current_time = self.getTime()
            self.media_length = self.getTotalTime()

            if tools.playList.size() == tools.playList.getposition() + 1 and self.media_type == 'episode':
                smartPlay.SmartPlay(self.original_action_args).append_next_season()

            if self.media_type == 'episode' and tools.getSetting('smartplay.upnext') == 'true':
                self.registerUpNext()

        except:
            import traceback
            traceback.print_exc()
            pass

    def registerUpNext(self):
        source_id = 'plugin.video.%s' % tools.addonName.lower()
        return_id = 'plugin.video.%s_play_action' % tools.addonName.lower()

        try:
            next_info = self.next_info()
            AddonSignals.registerSlot('upnextprovider', return_id, self.signals_callback)
            AddonSignals.sendSignal('upnext_data', next_info, source_id=source_id)

        except RuntimeError:
            pass

        except:
            import traceback
            traceback.print_exc()
            pass

    def onPlayBackEnded(self):
        if not self.scrobbled:
            self.traktStopWatching()
            tools.trigger_widget_refresh()
        pass

    def onPlayBackStopped(self):
        self.traktStopWatching()

        tools.playList.clear()

    def onPlayBackPaused(self):

        self.traktPause()

    def onPlayBackResumed(self):

        self.traktStartWatching()

    def getWatchedPercent(self, offset=None):

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

        scrobble_response = self.trakt_api.json_response('scrobble/stop', postData=post_data, limit=False)

        # Consider the scrobble attempt a failure if the attempt returns a None value
        if scrobble_response is None:
            return

        self.scrobbled = True

        try:
            if post_data['progress'] >= 80:
                if self.media_type == 'episode':
                    from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
                    TraktSyncDatabase().mark_episode_watched_by_id(self.trakt_id)
                    
                if self.media_type == 'movie':
                    from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase
                    TraktSyncDatabase().mark_movie_watched(self.trakt_id)

        except:
            import traceback
            traceback.print_exc()
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
        tools.kodi.sleep(5000)
        for i in range(0, 240):
            if self.isPlayingVideo(): break
            tools.kodi.sleep(1000)

        while self.isPlayingVideo():
            try:
                if not self.playback_started:
                    tools.kodi.sleep(1000)
                    continue

                if not self.playback_started:
                    self.start_playback()

                if self.offset is not None and int(self.offset) != 0 and self.playback_resumed is False:
                    tools.log("Seeking %s seconds" % self.offset, 'info')
                    self.seekTime(self.offset)
                    self.offset = None
                    self.playback_resumed = True
                else:
                    self.playback_resumed = True

                try:
                    self.current_time = self.getTime()
                    self.media_length = self.getTotalTime()
                except:
                    pass

                if self.pre_cache_initiated is False:
                    tools.log(self.pre_cache_initiated)
                    try:
                        if self.getWatchedPercent() > 80 and tools.getSetting('smartPlay.preScrape') == 'true':
                            tools.log(self.getWatchedPercent())
                            self.pre_cache_initiated = True
                            smartPlay.SmartPlay(self.original_action_args).pre_scrape()
                    except:
                        pass

                if self.getWatchedPercent() > 80 and not self.scrobbled:
                    self.traktStopWatching()
                    tools.trigger_widget_refresh()

            except:
                import traceback
                traceback.print_exc()
                tools.kodi.sleep(1000)
                continue

            tools.kodi.sleep(3000)

        self.traktStopWatching()

    def traktBookmark(self):

        if not self.trakt_integration():
            return
        try:

            offset = None
            if self.media_type == 'episode':
                progress = self.trakt_api.json_response('sync/playback/episodes?extended=full')
                for i in progress:
                    if int(self.trakt_id) == int(i['episode']['ids']['trakt']):
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
                tools.log('Offset is equal to : %s seconds' % offset)
        except:
            import traceback
            traceback.print_exc()

    def signals_callback(self, data):

        if not self.play_next_triggered:
            if not self.scrobbled:
                try:
                    self.traktStopWatching()
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
        current_episode["episodeid"] = current_info['ids']['trakt']
        current_episode["tvshowid"] = current_info['showInfo']['info']['imdbnumber']
        current_episode["title"] = current_info['info']['title']
        current_episode["art"] = {}
        current_episode["art"]["tvshow.poster"] = current_info['art']['poster']
        current_episode["art"]["thumb"] = current_info['art']['thumb']
        current_episode["art"]["tvshow.fanart"] = current_info['art']['fanart']
        current_episode["art"]["tvshow.landscape"] = current_info['art']['fanart']
        current_episode["art"]["tvshow.clearart"] = current_info['art'].get('clearart', '')
        current_episode["art"]["tvshow.clearlogo"] = current_info['art'].get('clearlogo', '')
        current_episode["plot"] = current_info['info']['plot']
        current_episode["showtitle"] = current_info['showInfo']['info']['tvshowtitle']
        current_episode["playcount"] = current_info['info'].get('playcount', 0)
        current_episode["season"] = current_info['info']['season']
        current_episode["episode"] = current_info['info']['episode']
        current_episode["rating"] = current_info['info']['rating']
        current_episode["firstaired"] = current_info['info']['premiered'][:10]

        current_position = tools.playList.getposition()
        url = tools.playList[current_position + 1].getPath()
        params = dict(tools.parse_qsl(url.replace('?', '')))
        next_info = tools.get_item_information(params.get('actionArgs'))

        next_episode = {}
        next_episode["episodeid"] = next_info['ids']['trakt']
        next_episode["tvshowid"] = next_info['showInfo']['info']['imdbnumber']
        next_episode["title"] = next_info['info']['title']
        next_episode["art"] = {}
        next_episode["art"]["tvshow.poster"] = next_info['art']['poster']
        next_episode["art"]["thumb"] = next_info['art']['thumb']
        next_episode["art"]["tvshow.fanart"] = next_info['art']['fanart']
        next_episode["art"]["tvshow.landscape"] = next_info['art']['fanart']
        next_episode["art"]["tvshow.clearart"] = next_info['art'].get('clearart', '')
        next_episode["art"]["tvshow.clearlogo"] = next_info['art'].get('clearlogo', '')
        next_episode["plot"] = next_info['info']['plot']
        next_episode["showtitle"] = next_info['showInfo']['info']['tvshowtitle']
        next_episode["playcount"] = next_info['info'].get('playcount', 0)
        next_episode["season"] = next_info['info']['season']
        next_episode["episode"] = next_info['info']['episode']
        next_episode["rating"] = next_info['info']['rating']
        next_episode["firstaired"] = next_info['info']['premiered'][:10]

        play_info = {}
        play_info["item_id"] = current_info['ids']['trakt']

        next_info = {
            "current_episode": current_episode,
            "next_episode": next_episode,
            "play_info": play_info,
            "notification_time": int(tools.getSetting('smartplay.upnexttime'))
        }

        return next_info

