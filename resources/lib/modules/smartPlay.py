from resources.lib.indexers.trakt import TraktAPI
from resources.lib.common import tools
from resources.lib.gui import tvshowMenus
from resources.lib.modules import database
from resources.lib.gui import windows

import json

class SmartPlay:

    def __init__(self, info_dictionary):
        try:
            self.info_dictionary = json.loads(tools.unquote(info_dictionary))
        except:
            self.info_dictionary = info_dictionary

        if 'episodeInfo' not in info_dictionary:
            self.show_trakt_id = self.info_dictionary['ids']['trakt']
            self.user_history = TraktAPI().json_response('sync/history/shows/%s' % self.show_trakt_id)
            self.poster = self.info_dictionary['art']['fanart']
        else:
            self.poster = self.info_dictionary['showInfo']['art']['fanart']
            self.show_trakt_id = self.info_dictionary['showInfo']['ids']['trakt']

        self.show_season_info = database.get(TraktAPI().json_response, 12,
                                          'shows/%s/seasons?extended=full' % self.show_trakt_id)
        self.window = None

    def smart_play_show(self):


        self.window = windows.smart_play_background()

        self.window.setBackground(self.poster)

        self.window.setText("Begining SmartPlay")
        self.window.show()
        self.window.setProgress(0)
        self.window.setProgress(40)
        self.window.setText('Identifying Resume Point')

        tools.playList.clear()

        if 'episodeInfo' not in self.info_dictionary:
            if tools.getSetting('trakt.auth') == '':
                tools.showDialog.ok(tools.addonName, 'Error: Trakt is not authorized \n\nPlease disable the Smart '
                                                     'Episode Resume feature or alternatively '
                                                     'authorise Trakt in the settings menu')
                return
            season, episode = self.get_resume_episode()

            if self.final_episode_check(season, episode) is True:
                season = 1
                episode = 1
            season_object = TraktAPI().json_response('shows/%s/seasons?extended=full' % self.info_dictionary['ids']['trakt'])
            season_object = [x for x in season_object if x['number'] == season]
            self.info_dictionary = tvshowMenus.Menus().seasonListBuilder(season_object,
                                                                         self.info_dictionary,
                                                                         smartPlay=True)
            self.info_dictionary = json.loads(tools.unquote(self.info_dictionary))
        else:
            season = self.info_dictionary['episodeInfo']['info']['season']
            episode = self.info_dictionary['episodeInfo']['info']['episode']

        self.window.setText('Building PlayList')
        self.window.setProgress(60)

        episode_list = database.get(TraktAPI().json_response, 12, 'shows/%s/seasons/%s?extended=full' % (self.show_trakt_id, str(season)))

        playlist = []

        for i in episode_list:
            if i['number'] < episode:
                continue
            playlist.append(i)

        self.window.setText('Building List Items')
        self.window.setProgress(80)

        playlist = tvshowMenus.Menus().episodeListBuilder(playlist, self.info_dictionary, smartPlay=True)
        playlist = playlist[:40]
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
           relevant_season_info = [i for i in self.show_season_info if i['number'] == season_number][0]
           if episode_number >= relevant_season_info['episode_count']:
               season_number += 1
               episode_number = 1
           return season_number, episode_number
       except:
           return 1,1

    def final_episode_check(self, season, episode):

        last_aired = TraktAPI().json_response('shows/%s/last_episode?extended=full' % self.show_trakt_id)
        if str(season) == str(last_aired['season']):
            if str(episode) == str(last_aired['number']):
                return True
        return False

    def return_next_season(self):
        season = self.info_dictionary['episodeInfo']['info']['season']
        episode = self.info_dictionary['episodeInfo']['info']['episode']

        current_season_info = [i for i in self.show_season_info if season == i['number']][0]
        if episode == current_season_info['episode_count']:
            if len([i for i in self.show_season_info if i['number'] == season + 1]) == 0:
                return False
            self.info_dictionary['episodeInfo']['info']['episode'] = 1
            self.info_dictionary['episodeInfo']['info']['season'] += 1
            self.smart_play_show()
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
        trakt_object = TraktAPI().json_response('shows/%s/seasons/%s/episodes/%s?extended=full' % (show_id, season, episode))

        list_item = tvshowMenus.Menus().episodeListBuilder([trakt_object], info, smartPlay=True)[0]
        url = list_item[0] + "&packSelect=true"
        tools.playList.add(url=url, listitem=list_item[1])
        tools.player().play(tools.playList)

    def shufflePlay(self):
        import random
        self.window = windows.smart_play_background()
        self.window.setBackground(self.poster)
        self.window.setProgress(0)
        self.window.show()
        self.window.setText('Building Playlist')
        tools.playList.clear()
        showInfo = {}
        showInfo['showInfo'] = self.info_dictionary
        season_list = TraktAPI().json_response('shows/%s/seasons?extended=episodes' % self.show_trakt_id)
        if season_list[0]['number'] == 0:
            season_list.pop(0)
        self.window.setProgress(50)
        self.window.setText('Building List Items')
        episode_list = [episode for season in season_list for episode in season['episodes']]
        random.shuffle(episode_list)
        episode_list = episode_list[:40]

        #mill the episodes
        playlist = tvshowMenus.Menus().episodeListBuilder(episode_list, showInfo, smartPlay=True)
        self.window.setProgress(100)
        self.window.setText('Starting Scraping')
        for episode in playlist:
            if episode is not None:
                tools.playList.add(url=episode[0], listitem=episode[1])
        self.window.setProgress(100)
        self.window.close()
        tools.playList.shuffle()
        tools.player().play(tools.playList)












