# -*- coding: utf-8 -*-

import json
import sys
import traceback

from resources.lib.common import tools
from resources.lib.indexers import trakt
from resources.lib.modules import smartPlay
from resources.lib.modules.trakt_sync import bookmark
from resources.lib.modules import database
from resources.lib.modules.playback_points import IdentifyCreditsIntro

try:
    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
except:
    pass

bookmark_sync = bookmark.TraktSyncDatabase()


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
        self.playing_file = None
        self.AVStarted = False
        self.scrobbling_enabled = tools.getSetting('trakt.scrobbling') == 'true'
        self.scrobbled = False
        self.original_action_args = ''
        self.smart_playlists = tools.getSetting('smartplay.playlistcreate')
        self.smart_module = None
        self.ignoreSecondsAtStart = int(tools.get_advanced_setting('video', 'ignoresecondsatstart'))
        self.ignorePercentAtEnd = int(tools.get_advanced_setting('video', 'ignorepercentatend'))
        self.playCountMinimumPercent = int(tools.get_advanced_setting('video', 'playcountminimumpercent'))

        self.min_time_before_scrape = int(tools.getSetting('playingnext.time')) + \
                                      int(int(tools.getSetting('general.timeout'))) + 20
        self.marked_watched = False
        tools.player.__init__(self)

    def play_source(self, stream_link, args, resume_time=None, params=None):
        try:
            self.pre_cache_initiated = False
            if resume_time is not None:
                self.offset = float(resume_time)

            self.params = params

            if stream_link is None:
                tools.cancelPlayback()
                raise Exception

            self.playing_file = stream_link
            self.original_action_args = args
            self.smart_module = smartPlay.SmartPlay(self.original_action_args)

            args = tools.get_item_information(args)
            self.args = args

            if 'showInfo' in args:
                self.media_type = 'episode'
                # Workaround for estuary skin to allow episode information to be displayed in Video Top Info
                args['art']['tvshow.clearlogo'] = args['art'].get('clearlogo', '')
            else:
                self.media_type = 'movie'

            self.trakt_id = args['ids']['trakt']

            orginalArgs = json.loads(tools.unquote(self.original_action_args))

            if 'resume' in orginalArgs:
                if orginalArgs['resume'] == 'true':
                    self.tryGetBookmark()

            self.handleBookmark()

            item = tools.menuItem(path=stream_link)
            args['info']['FileNameAndPath'] = tools.unquote(stream_link)
            item.setInfo(type='video', infoLabels=args['info'])
            item.setArt(args['art'])
            item.setCast(args['cast'])
            item.setUniqueIDs(args['ids'])

            tools.closeBusyDialog()
            tools.closeAllDialogs()

            tools.resolvedUrl(syshandle, True, item)

            self.keepAlive()

        except:
            traceback.print_exc()
            pass

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
        self.AVStarted = True
        self.start_playback()

    def onAVChange(self):
        self.AVStarted = True
        self.start_playback()

    def onPlayBackError(self):
        self.handleBookmark()
        tools.playList.clear()
        sys.exit(1)

    def start_playback(self):
        try:

            if self.playback_started:
                return

            # tools.closeAllDialogs()

            self.playback_started = True
            self.scrobbled = False

            self.traktStartWatching()

            self.media_length = self.getTotalTime()

            if tools.playList.size() == 1 and self.smart_playlists == 'true' and self.media_type == 'episode':
                self.smart_module.build_playlist(params=self.params)

            if tools.playList.size() == tools.playList.getposition() + 1 \
                    and self.media_type == 'episode' \
                    and self.smart_playlists == 'true':
                smartPlay.SmartPlay(self.original_action_args).append_next_season()

        except:
            import traceback
            traceback.print_exc()
            pass

    def onPlayBackEnded(self):
        self.commonEndPlayBack()

    def onPlayBackStopped(self):
        tools.playList.clear()
        self.commonEndPlayBack()

    def commonEndPlayBack(self):
        self.handleBookmark()
        self.traktStopWatching()
        tools.container_refresh()
        tools.trigger_widget_refresh()

    def onPlayBackPaused(self):
        self.traktPause()

    def onPlayBackResumed(self):
        self.traktStartWatching()

    def getWatchedPercent(self, offset=None):

        try:
            current_position = self.getTime()
        except:
            current_position = self.current_time

        total_length = self.media_length
        watched_percent = 0

        if int(total_length) == 0:
            try:
                total_length = self.getTotalTime()
            except:
                import traceback
                traceback.print_exc()
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
        if not self.trakt_integration() or not self.scrobbling_enabled or self.scrobbled:
            return

        post_data = self.buildTraktObject(offset=offset)

        self.trakt_api.post_request('scrobble/start', postData=post_data, limit=False)

    def traktStopWatching(self, override_progress=None):
        if not self.trakt_integration():
            return

        self.handleBookmark()

        if self.scrobbling_enabled and not self.scrobbled:
            post_data = self.buildTraktObject(override_progress=override_progress)
            try:
                scrobble_response = self.trakt_api.json_response('scrobble/stop', postData=post_data, limit=False)

                # Consider the scrobble attempt a failure if the attempt returns a None value
                if scrobble_response is not None:
                    self.scrobbled = True
            except:
                pass

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

        elif not self.scrobbling_enabled and not self.marked_watched:
            if int(self.getWatchedPercent()) >= int(tools.get_advanced_setting('video', 'playcountminimumpercent')):
                if self.media_type == 'episode':
                    from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
                    TraktSyncDatabase().mark_episode_watched_by_id(self.trakt_id)
                else:
                    from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase
                    TraktSyncDatabase().mark_movie_watched(self.trakt_id)

    def traktPause(self):

        if not self.trakt_integration() or not self.scrobbling_enabled or self.scrobbled:
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

        for i in range(0, 480):
            tools.kodi.sleep(250)
            if self.isPlayingVideo():
                break

        for i in range(0, 480):
            if self.AVStarted:
                break

        tools.closeAllDialogs()

        self.media_length = self.getTotalTime()

        if self.offset is not None and self.offset != 0:
            tools.log("Seeking {} seconds".format(self.offset))
            self.seekTime(self.offset)
            self.offset = None

        while self.isPlayingVideo() and not self.scrobbled:
            try:
                watched_percentage = self.getWatchedPercent()
                time_left = int(self.getTotalTime()) - int(self.getTime())

                try:
                    self.current_time = self.getTime()

                except:
                    import traceback
                    traceback.print_exc()
                    pass

                if not self.playback_started:
                    tools.kodi.sleep(1000)
                    continue

                if watched_percentage > 80 or time_left <= self.min_time_before_scrape:

                    if self.pre_cache_initiated is False:

                        try:
                            if tools.getSetting('smartPlay.preScrape') == 'true':
                                self.pre_cache_initiated = True
                                smartPlay.SmartPlay(self.original_action_args).pre_scrape()
                        except:
                            import traceback
                            traceback.print_exc()
                            pass

                if watched_percentage > 80:
                    self.traktStopWatching()
                    self.handleBookmark()
                    break

            except:
                import traceback
                traceback.print_exc()
                tools.kodi.sleep(1000)
                continue

            tools.kodi.sleep(1000)

        else:
            self.traktStopWatching()
            return

        if tools.getSetting('smartplay.playingnextdialog') == 'true' or \
                tools.getSetting('smartplay.stillwatching') == 'true':
            endpoint = int(tools.getSetting('playingnext.time'))
        else:
            endpoint = False

        if endpoint:
            while self.isPlayingVideo():
                if int(self.getTotalTime()) - int(self.getTime()) <= endpoint:
                    tools.execute('RunPlugin("plugin://plugin.video.seren/?action=runPlayerDialogs")')
                    break
                else:
                    tools.kodi.sleep(1000)

        self.traktStopWatching()

    def tryGetBookmark(self):
        bookmark = bookmark_sync.get_bookmark(self.trakt_id)
        self.offset = bookmark['timeInSeconds'] if bookmark is not None else None

    def handleBookmark(self):
        if self.media_length == 0 or self.current_time == 0:
            bookmark_sync.remove_bookmark(self.trakt_id)
            return

        if self.getWatchedPercent() < 80 and self.current_time >= 60:
            bookmark_sync.set_bookmark(self.trakt_id, self.current_time)
        else:
            bookmark_sync.remove_bookmark(self.trakt_id)

        try:
            database.clear_local_bookmarks()
        except:
            pass

    @staticmethod
    def trakt_integration():
        if tools.getSetting('trakt.auth') == '':
            return False
        else:
            return True


class PlayerDialogs(tools.player):

    def __init__(self):
        super(PlayerDialogs, self).__init__()
        self._min_time = int(tools.getSetting('playingnext.time'))
        self.playing_file = self.getPlayingFile()

    def display_dialog(self):

        if tools.playList.size() > 0 and tools.playList.getposition() != (tools.playList.size() - 1):
            if tools.getSetting('smartplay.stillwatching') == 'true' and self._still_watching_calc():

                target = self._show_still_watching

            elif tools.getSetting('smartplay.playingnextdialog') == 'true':

                target = self._show_playing_next

            else:
                return

            if self.playing_file != self.getPlayingFile():
                return

            if not self.isPlayingVideo():
                return

            if not self._is_video_window_open():
                return

            target()

    @staticmethod
    def _still_watching_calc():
        calculation = float(tools.playList.getposition() + 1) / \
                      float(tools.getSetting('stillwatching.numepisodes'))

        if calculation == 0:
            return False

        return calculation.is_integer()

    def _show_playing_next(self):

        from resources.lib.gui.windows.playing_next import PlayingNext
        from resources.lib.modules.skin_manager import SkinManager

        PlayingNext(*SkinManager().confirm_skin_path('playing_next.xml'),
                    actionArgs=self._get_next_item_args()).doModal()

    def _show_still_watching(self):

        from resources.lib.gui.windows.still_watching import StillWatching
        from resources.lib.modules.skin_manager import SkinManager

        StillWatching(*SkinManager().confirm_skin_path('still_watching.xml'),
                      actionArgs=self._get_next_item_args()).doModal()

    @staticmethod
    def _get_next_item_args():
        current_position = tools.playList.getposition()
        url = tools.playList[current_position + 1].getPath()
        params = dict(tools.parse_qsl(url.replace('?', '')))
        next_info = params.get('actionArgs')
        return next_info

    @staticmethod
    def _is_video_window_open():

        if tools.kodiGui.getCurrentWindowId() != 12005:
            return False
        return True

