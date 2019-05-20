# -*- coding: utf-8 -*-

import json

from resources.lib.common import tools
from resources.lib.gui import tvshowMenus
from resources.lib.gui import windows
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.modules import database

class SmartPlay:
    def __init__(self, info_dictionary):
        try:
            self.info_dictionary = json.loads(tools.unquote(info_dictionary))
        except:
            self.info_dictionary = info_dictionary

        if type(self.info_dictionary) is not dict:
            raise Exception

        try:
            self.poster = self.info_dictionary['showInfo']['art'].get('fanart', '')
            self.show_trakt_id = self.info_dictionary['showInfo']['ids']['trakt']
        except:
            self.poster = self.info_dictionary['art'].get('fanart', '')
            self.show_trakt_id = self.info_dictionary['ids']['trakt']

        self.window = None

    def get_season_info(self):
        return database.get(TraktAPI().json_response, 12, 'shows/%s/seasons' % self.show_trakt_id)

    def smart_play_show(self, append_playlist=False):

        self.window = windows.smart_play_background()
        self.window.setBackground(self.poster)
        self.window.setText(tools.lang(32094))

        if not append_playlist:
            self.window.show()

        self.window.setProgress(0)
        self.window.setProgress(40)
        self.window.setText(tools.lang(32095))

        if not append_playlist:
            tools.playList.clear()

        if 'episodeInfo' not in self.info_dictionary:
            if tools.getSetting('trakt.auth') == '':
                tools.showDialog.ok(tools.addonName, tools.lang(32093))
                return
            else:
                self.user_history = TraktAPI().json_response('sync/history/shows/%s' % self.show_trakt_id)

            season, episode = self.get_resume_episode()

            if self.final_episode_check(season, episode) is True:
                season = 1
                episode = 1

        else:
            season = self.info_dictionary['episodeInfo']['info']['season']
            episode = self.info_dictionary['episodeInfo']['info']['episode']

        self.window.setText(tools.lang(32096))
        self.window.setProgress(60)

        if append_playlist:
            # Add next seasons episodes to the currently playing playlist and then finish up

            playlist = tvshowMenus.Menus().episodeListBuilder(self.show_trakt_id, season,
                                                              hide_unaired=True, smartPlay=True)
            for i in playlist:
                # Confirm that the episode meta we have received from TVDB are for the correct episodes
                # If trakt provides the incorrect TVDB ID it's possible to begin play from the incorrect episode
                params = dict(tools.parse_qsl(i[0].replace('?', '')))
                actionArgs = json.loads(params.get('actionArgs'))
                if actionArgs['episodeInfo']['info']['episode'] < episode:
                    continue

                # If the episode is confirmed ok, add it to our playlist.
                if tvshowMenus.Menus().is_aired(actionArgs['episodeInfo']['info']):
                    tools.playList.add(url=i[0], listitem=i[1])
            return

        season_episodes = tvshowMenus.Menus().episodeListBuilder(self.show_trakt_id, season, smartPlay=True)

        self.window.setText(tools.lang(32097))
        self.window.setProgress(80)

        playlist = []

        for ep in season_episodes:
            path_arguments = dict(tools.parse_qsl(ep[0].replace('?', '')))
            episode_args = json.loads(tools.unquote(path_arguments['actionArgs']))
            ep_no = int(episode_args['episodeInfo']['info']['episode'])

            if ep_no >= episode and tvshowMenus.Menus().is_aired(episode_args['episodeInfo']['info']):
                playlist.append(ep)

        self.window.setText('Starting Playback')
        self.window.setProgress(100)

        for i in playlist:
            tools.playList.add(url=i[0], listitem=i[1])

        tools.log('Begining play from Season %s Episode %s' % (season, episode), 'info')

        self.window.close()

        tools.player().play(tools.playList)

    def get_resume_episode(self):

        try:
            episode_info = self.user_history[0]
            season_number = episode_info['episode']['season']
            episode_number = episode_info['episode']['number']
            if episode_info['action'] == 'watch':
                return season_number, episode_number
            else:
                episode_number += 1
            relevant_season_info = [i for i in self.get_season_info() if i['number'] == season_number][0]
            if episode_number >= relevant_season_info['episode_count']:
                season_number += 1
                episode_number = 1
            return season_number, episode_number
        except:
            return 1, 1

    def final_episode_check(self, season, episode):

        last_aired = TraktAPI().json_response('shows/%s/last_episode' % self.show_trakt_id)
        if str(season) == str(last_aired['season']):
            if str(episode) == str(last_aired['number']):
                return True
        return False

    def append_next_season(self):
        season = self.info_dictionary['episodeInfo']['info']['season']
        episode = self.info_dictionary['episodeInfo']['info']['episode']
        season_info = self.get_season_info()
        current_season_info = [i for i in season_info if season == i['number']][0]
        if episode == current_season_info['episode_count']:
            if len([i for i in season_info if i['number'] == season + 1]) == 0:
                return False
            self.info_dictionary['episodeInfo']['info']['episode'] = 1
            self.info_dictionary['episodeInfo']['info']['season'] += 1
            self.smart_play_show(append_playlist=True)
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
        episode = info['episodeInfo']['info']['episode']
        season = info['episodeInfo']['info']['season']
        show_id = info['showInfo']['ids']['trakt']

        list_item = tvshowMenus.Menus().episodeListBuilder(show_id, season, hide_unaired=True, smartPlay=True)
        url = list_item[0] + "&packSelect=true"
        tools.playList.add(url=url, listitem=list_item[1])
        tools.player().play(tools.playList)

    def shufflePlay(self):
        import random
        self.window = windows.smart_play_background()
        self.window.setBackground(self.poster)
        self.window.setProgress(0)
        self.window.show()
        self.window.setText(tools.lang(32096))
        tools.playList.clear()

        season_list = TraktAPI().json_response('shows/%s/seasons?extended=episodes' % self.show_trakt_id)
        if season_list[0]['number'] == 0:
            season_list.pop(0)
        self.window.setProgress(50)
        self.window.setText(tools.lang(32097))
        episode_list = [episode for season in season_list for episode in season['episodes']]
        random.shuffle(episode_list)
        episode_list = episode_list[:40]
        shuffle_list = []
        for episode in episode_list:
            shuffle_list.append({'episode': episode, 'show': {'ids': {'trakt': self.show_trakt_id}}})

        # mill the episodes
        playlist = tvshowMenus.Menus().mixedEpisodeBuilder(shuffle_list, sort=False, smartPlay=True)
        self.window.setProgress(100)
        self.window.setText(tools.lang(32098))
        for episode in playlist:
            if episode is not None:
                tools.playList.add(url=episode[0], listitem=episode[1])
        self.window.setProgress(100)
        self.window.close()
        tools.playList.shuffle()
        tools.player().play(tools.playList)

    def play_from_random_point(self):

        import random
        random_season = random.randint(1, int(self.info_dictionary['showInfo']['info']['season_count']))

        playlist = tvshowMenus.Menus().episodeListBuilder(self.show_trakt_id, random_season, smartPlay=True,
                                                          hide_unaired=True)

        random_episode = random.randint(1, int(len(playlist)))

        playlist = playlist[random_episode:]

        self.window.setProgress(100)
        self.window.setText(tools.lang(32098))
        for episode in playlist:
            if episode is not None:
                tools.playList.add(url=episode[0], listitem=episode[1])
        self.window.setProgress(100)
        self.window.close()
        tools.player().play(tools.playList)

    def workaround(self):
        actionArgs = tools.quote(json.dumps(self.info_dictionary, sort_keys=True))
        tools.execute('RunPlugin(plugin://plugin.video.%s?action=buildPlaylistWorkaround&actionArgs=%s)' %
                      (tools.addonName.lower(), actionArgs))
