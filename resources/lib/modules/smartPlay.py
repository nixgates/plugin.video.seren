# -*- coding: utf-8 -*-

import json

from resources.lib.common import tools
from resources.lib.gui import tvshowMenus
from resources.lib.gui.windows.persistent_background import PersistentBackground
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.modules import database
from resources.lib.modules.skin_manager import SkinManager


class SmartPlay:
    def __init__(self, actionArgs):
        self.actionArgs = actionArgs
        self.info_dictionary = tools.get_item_information(actionArgs)

        if type(self.info_dictionary) is not dict:
            raise Exception

        try:
            self.show_trakt_id = self.info_dictionary['showInfo']['ids']['trakt']
        except:
            self.show_trakt_id = self.info_dictionary['ids']['trakt']
        self.display_style = tools.getSetting('smartplay.displaystyle')
        self.window = BackgroundWindowAdapter()

    def get_season_info(self):
        return database.get(TraktAPI().json_response, 12, 'shows/%s/seasons?extended=full' % self.show_trakt_id)

    def fill_playlist(self, params=None):
        try:
            tools.cancelPlayback()
        except:
            import traceback
            traceback.print_exc()
            pass
        tools.closeAllDialogs()

        if self.display_style == '0':
            self.window = PersistentBackground(*SkinManager().confirm_skin_path('persistent_background.xml'),
                                               actionArgs=self.actionArgs)

        self.window.setText(tools.lang(32094))
        self.window.show()

        self.window.setText(tools.lang(32095))

        tools.playList.clear()

        season = self.info_dictionary['info']['season']
        episode = self.info_dictionary['info']['episode']

        self.window.setText(tools.lang(32096))

        self.window.setText(tools.lang(32097))

        self.build_playlist(season, episode, params=params)

        self.window.setText(tools.lang(40322))

        tools.log('Begining play from Season %s Episode %s' % (season, episode), 'info')

        self.window.close()

        tools.player().play(tools.playList)

    def resume_playback(self):

        tools.playList.clear()

        if self.display_style == '0':
            self.window = PersistentBackground(*SkinManager().confirm_skin_path('persistent_background.xml'),
                                               actionArgs=self.actionArgs)
        self.window.show()
        self.window.setText(tools.lang(32095).encode('utf-8'))

        if tools.getSetting('trakt.auth') == '':
            tools.showDialog.ok(tools.addonName, tools.lang(32093).encode('utf-8'))
            self.window.close()
            return

        playback_history = TraktAPI().json_response('sync/history/shows/%s' % self.show_trakt_id)

        self.window.setText(tools.lang(32096).encode('utf-8'))

        season, episode = self.get_resume_episode(playback_history)

        self.build_playlist(season, episode)

        self.window.close()

        tools.player().play(tools.playList)

    @staticmethod
    def clean_playback_params(params):
        if params is not None:

            # Do not apply the resume function to all items in the list
            if 'resume' in params:
                params.pop('resume')

            params.pop('actionArgs')
            params.pop('action')

            return tools.urlencode(params)

    def build_playlist(self, season=None, minimum_episode=None, params=None):

        if season is None:
            season = self.info_dictionary['info']['season']

        if minimum_episode is None:
            minimum_episode = int(self.info_dictionary['info']['episode']) + 1

        url_params = self.clean_playback_params(params)

        playlist = tvshowMenus.Menus().episodeListBuilder(self.show_trakt_id, season, smartPlay=True)

        for i in playlist:
            params = dict(tools.parse_qsl(i[0].replace('?', '')))
            actionArgs = params.get('actionArgs')

            if not tvshowMenus.Menus().is_aired(tools.get_item_information(actionArgs)['info']):
                tools.log('Episode not Aired, skipping')
                continue

            actionArgs = json.loads(actionArgs)

            if actionArgs['episode'] < minimum_episode:
                continue

            url = i[0]

            if actionArgs['episode'] == minimum_episode:
                request_args = json.loads(tools.unquote(self.actionArgs))
                # actionArgs['resume'] = request_args['resume'] if 'resume' in request_args else 'false'
                url = '&actionArgs='.join([url.split('&actionArgs=')[0],
                                           tools.quote(json.dumps(actionArgs, sort_keys=True))])

            if url_params is not None:
                url += '&{}'.format(url_params)

            tools.playList.add(url=url, listitem=i[1])

    def get_resume_episode(self, playback_history):

        try:

            episode_info = playback_history[0]
            season = episode_info['episode']['season']
            episode = episode_info['episode']['number']

            # Continue watching from last unfinished episode
            if episode_info['action'] == 'watch':
                return season, episode
            else:
                # Move on to next episode
                episode += 1

            # Get information for new season and check whether we are finished the season
            relevant_season_info = [i for i in self.get_season_info() if i['number'] == season][0]

            if episode >= relevant_season_info['episode_count']:
                season += 1
                episode = 1

            if self.final_episode_check(season, episode):
                season = 1
                episode = 1

            return season, episode
        except:
            return 1, 1

    def final_episode_check(self, season, episode):

        season = int(season)
        episode = int(episode)

        last_aired = TraktAPI().json_response('shows/%s/last_episode' % self.show_trakt_id)

        if season > last_aired['season']:
            return True

        if season == last_aired['season']:
            if episode == last_aired['number']:
                return True

        return False

    def append_next_season(self, params=None):

        season = self.info_dictionary['info']['season']
        episode = self.info_dictionary['info']['episode']

        season_info = self.get_season_info()

        current_season_info = [i for i in season_info if season == i['number']][0]

        if episode == current_season_info['episode_count']:

            if len([i for i in season_info if i['number'] == season + 1]) == 0:
                return False

            episode = 1
            season += 1

            self.build_playlist(season, episode, params=params)

        else:
            return False

    def pre_scrape(self):

        try:
            current_position = tools.playList.getposition()
            url = tools.playList[current_position + 1].getPath()
        except:
            url = None

        if url is None: return

        url = url.replace('getSources', 'preScrape')

        tools.setSetting(id='general.tempSilent', value='true')
        tools.execute('RunPlugin("%s")' % url)

    def torrent_file_picker(self):
        tools.playList.clear()
        info = self.info_dictionary
        episode = info['info']['episode']
        season = info['info']['season']
        show_id = info['showInfo']['ids']['trakt']

        list_item = tvshowMenus.Menus().episodeListBuilder(show_id, season, hide_unaired=True, smartPlay=True)
        url = list_item[0] + "&packSelect=true"
        tools.playList.add(url=url, listitem=list_item[1])
        tools.player().play(tools.playList)

    def shufflePlay(self):

        import random

        if self.display_style == '0':
            self.window = PersistentBackground(*SkinManager().confirm_skin_path('persistent_background.xml'),
                                               actionArgs=self.actionArgs)
        self.window.show()
        self.window.setText(tools.lang(32096))

        tools.playList.clear()

        season_list = TraktAPI().json_response('shows/%s/seasons?extended=episodes' % self.show_trakt_id)
        if season_list[0]['number'] == 0:
            season_list.pop(0)

        self.window.setText(tools.lang(32097))

        episode_list = [episode for season in season_list for episode in season['episodes']]
        random.shuffle(episode_list)
        episode_list = episode_list[:40]
        shuffle_list = []

        for episode in episode_list:
            shuffle_list.append({'episode': episode, 'show': {'ids': {'trakt': self.show_trakt_id}}})

        # mill the episodes
        playlist = tvshowMenus.Menus().mixedEpisodeBuilder(shuffle_list, sort=False, smartPlay=True)

        self.window.setText(tools.lang(32098))

        for episode in playlist:
            if episode is not None:
                tools.playList.add(url=episode[0], listitem=episode[1])

        self.window.close()

        tools.playList.shuffle()
        tools.player().play(tools.playList)

    def play_from_random_point(self):

        import random

        tools.playList.clear()

        random_season = random.randint(1, int(self.info_dictionary['info']['season_count']))

        playlist = tvshowMenus.Menus().episodeListBuilder(self.show_trakt_id, random_season, smartPlay=True,
                                                          hide_unaired=True)
        random_episode = random.randint(0, len(playlist) - 1)

        playlist = playlist[random_episode]

        tools.playList.add(url=playlist[0], listitem=playlist[1])

        tools.player().play(tools.playList)

    def getSourcesWorkaround(self, actionArgs):

        tools.execute('RunPlugin(plugin://plugin.video.%s?action=getSourcesWorkaround2&actionArgs=%s)' %
                      (tools.addonName.lower(), tools.quote(actionArgs)))

    def getSourcesWorkaround2(self, actionArgs):

        item_information = tools.get_item_information(actionArgs)
        item = tools.menuItem(label=item_information['info']['title'])
        item.setArt(item_information['art'])
        item.setUniqueIDs(item_information['ids'])
        item.setInfo(type='video', infoLabels=tools.clean_info_keys(item_information['info']))
        tools.playList.add(url='plugin://plugin.video.%s?action=getSources&actionArgs=%s' % (tools.addonName.lower(),
                                                                                             tools.quote(actionArgs)),
                           listitem=item)
        tools.player().play(tools.playList)

    def workaround(self):
        tools.execute('RunPlugin(plugin://plugin.video.%s?action=buildPlaylistWorkaround&actionArgs=%s)' %
                      (tools.addonName.lower(), tools.quote(self.actionArgs)))


class BackgroundWindowAdapter(tools.bgProgressDialog):

    def __init__(self):
        super(BackgroundWindowAdapter, self).__init__()
        self.text = ''
        self.created = False

    def show(self):
        self.create(tools.addonName, self.text)

    def setText(self, text):
        self.text = text
        if self.created:
            self.update()

    def update(self):
        super(BackgroundWindowAdapter, self).update(0, message=self.text)
