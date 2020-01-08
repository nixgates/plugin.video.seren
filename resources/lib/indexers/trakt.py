# -*- coding: utf-8 -*-
import ast
import json
import threading
from time import sleep

import requests

from resources.lib.common import tools
from resources.lib.modules.trakt_sync import lists


class TraktAPI:
    def __init__(self):

        self.ApiUrl = 'https://api.trakt.tv/'
        self.BaseUrl = 'https://trakt.tv'

        self.ClientID = ''
        self.ClientID = tools.getSetting('trakt.clientid')
        if self.ClientID == '':
            self.ClientID = '4dd60d1ccb4b5c79aba64313467f6fefbda570605a927639549e8668558ce37e'

        self.ClientSecret = ''
        self.ClientSecret = tools.getSetting('trakt.secret')
        if self.ClientSecret == '':
            self.ClientSecret = 'd4dd35c0c1b0ec21b7b0cc7085011833c32bc28a0a62b454f4777d745aea07aa'

        self.RedirectUri = 'urn:ietf:wg:oauth:2.0:oob'
        self.AccessToken = tools.getSetting('trakt.auth')
        self.RefreshToken = tools.getSetting('trakt.refresh')

        self.headers = {'trakt-api-version': '2',
                        'trakt-api-key': self.ClientID,
                        'content-type': 'application/json'}

        if not self.AccessToken is '':
            self.headers['Authorization'] = 'Bearer %s' % self.AccessToken

        self.response_headers = {}
        self.response_code = 0

    def revokeAuth(self):
        url = "oauth/revoke"
        postData = {"token": tools.getSetting('trakt.auth')}
        self.post_request(url, postData, limit=False)
        tools.setSetting('trakt.auth', '')
        tools.setSetting('trakt.refresh', '')
        tools.setSetting('trakt.username', '')
        from resources.lib.modules.trakt_sync import activities
        database = activities.TraktSyncDatabase()
        database.clear_user_information()
        tools.showDialog.ok(tools.addonName, tools.lang(32030))

    def auth(self):

        url = 'https://api.trakt.tv/oauth/device/code'
        postData = {'client_id': self.ClientID}
        response = requests.post(url, data=postData)
        if not response.ok:
            tools.showDialog.ok(tools.addonName, tools.lang(40113))
            return
        response = json.loads(response.text)
        try:
            user_code = response['user_code']
            device = response['device_code']
            interval = int(response['interval'])
            expiry = int(response['expires_in'])
        except:
            tools.showDialog.ok(tools.addonName, tools.lang(32032))
            return
        currentTime = 0
        tools.copy2clip(user_code)
        tools.progressDialog.create(tools.addonName + ': ' + tools.lang(32031),
                                    tools.lang(32024).format(tools.colorString('https://trakt.tv/activate \n')) +
                                    tools.lang(32025).format(tools.colorString(user_code) + "\n" +
                                    tools.lang(32071))
                                    )
        tools.progressDialog.update(100)
        while currentTime < (expiry - interval):
            if tools.progressDialog.iscanceled():
                tools.progressDialog.close()
                return
            progressPercent = int(100 - ((float(currentTime) / expiry) * 100))
            tools.progressDialog.update(progressPercent)
            sleep(interval)
            postData = {'code': device, 'client_id': self.ClientID, 'client_secret': self.ClientSecret}
            url = 'https://api.trakt.tv/oauth/device/token'
            response = requests.post(url, data=postData)

            if '200' in str(response):
                response = json.loads(response.text)
                tools.setSetting('trakt.auth', response['access_token'])
                tools.setSetting('trakt.refresh', response['refresh_token'])
                self.AccessToken = response['access_token']
                self.headers = {'trakt-api-version': '2',
                                'trakt-api-key': self.ClientID,
                                'content-type': 'application/json'}

                if not self.AccessToken is '':
                    self.headers['Authorization'] = 'Bearer %s' % self.AccessToken
                username = self.get_username()
                tools.setSetting('trakt.username', username)
                tools.progressDialog.close()
                tools.showDialog.ok(tools.addonName, tools.lang(40263))

                # Synchronise Trakt Database with new user
                from resources.lib.modules.trakt_sync import activities
                database = activities.TraktSyncDatabase()
                if database.activites['trakt_username'] != username:
                    database.clear_user_information()
                    database.flush_activities(False)
                    database._build_sync_activities()
                    database.set_trakt_user(username)
                    tools.execute('RunPlugin("plugin://plugin.video.%s/?action=syncTraktActivities")' %
                                  tools.addonName.lower())
                break
            if '400' in str(response):
                pass
            else:
                tools.progressDialog.close()
                tools.showDialog.ok(tools.addonName, tools.lang(32032))
                break

    def refreshToken(self):
        url = self.ApiUrl + "/oauth/token"
        postData = {
            'refresh_token': self.RefreshToken,
            'client_id': self.ClientID,
            'client_secret': self.ClientSecret,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'refresh_token'
        }
        response = requests.post(url, data=postData)
        try:
            response = json.loads(response.text)
            tools.setSetting('trakt.auth', response['access_token'])
            tools.setSetting('trakt.refresh', response['refresh_token'])
            self.AccessToken = response['access_token']
            self.RefreshToken = response['refresh_token']
            tools.log('Refreshed Trakt Token')
            if not self.AccessToken is '':
                self.headers['Authorization'] = self.AccessToken
            return
        except:
            import traceback
            traceback.print_exc()
            tools.log('Failed to refresh Trakt Access Token', 'error')
            return

    def _handle_re_auth(self, response):

        tools.log('Trakt OAuth Failure, %s %s' % (str(response.text), response.request.headers), 'info')

        self.refreshToken()

    def _append_limit(self, url, limit_override):
        if limit_override == 0:
            limit_amount = int(tools.getSetting('item.limit'))
        else:
            limit_amount = limit_override
        if not '?' in url:
            url += '?limit=%s' % limit_amount
        else:
            url += '&limit=%s' % limit_amount

        return url

    def get_request(self, url, limit=True, limitOverride=0, refreshCheck=False, attempts=0):

        if not refreshCheck:
            if limit:
                url = self._append_limit(url, limitOverride)

        try:
            response = requests.get(self.ApiUrl + url, headers=self.headers)
            self.response_headers = response.headers

            if response.status_code == 403:
                if refreshCheck == False:
                    self._handle_re_auth(response)
                    return self.get_request(url, refreshCheck=True)
                else:
                    tools.log('Failed to perform request even after token refresh', 'error')

            if response.status_code > 499:
                if attempts < 5:
                    attempts += 1
                    tools.log('Failed to perform Trakt Get request, re-trying. Attempts: {}'.format(attempts), 'error')
                    return self.get_request(url, limit, limitOverride, True, attempts)
                else:
                    tools.log('Trakt failed to reply on multiple attempts, URL: {}'.format(url), 'error')
                    return None

            if response.status_code == 404:
                tools.log('Trakt returned a 404: {}'.format(url), 'error')
                return None

            if response.status_code == 502:
                tools.log('Trakt is currently experiencing Gateway Issues', 'error')

        except requests.exceptions.ConnectionError:
            return
        except not requests.exceptions.ConnectionError:
            tools.showDialog.ok(tools.addonName, tools.lang(32035))
            return

        return response.text

    def post_request(self, url, postData, limit=True, refreshCheck=False, attempts=0):
        if not refreshCheck:
            if limit:
                url = self._append_limit(url, 0)
        try:
            response = requests.post(self.ApiUrl + url, json=postData, headers=self.headers)
            self.response_headers = response.headers

            if response.status_code == 403:
                if not refreshCheck:
                    self._handle_re_auth(response)
                    self.post_request(url, postData, limit=limit, refreshCheck=True)
                else:
                    tools.log('Failed to perform trakt request even after token refresh', 'error')

            if response.status_code > 499:
                if attempts < 5:
                    attempts += 1
                    tools.log('Failed to perform Trakt POST request, re-trying. Attempts: {}'.format(attempts), 'error')
                    return self.post_request(url, postData, limit, True, attempts)
                else:
                    tools.log('Trakt failed to reply on multiple attempts, URL: {}'.format(url), 'error')
                    return None

        except requests.exceptions.ConnectionError:
            return
        except not requests.exceptions.ConnectionError:
            tools.showDialog.ok(tools.addonName, tools.lang(32035))
            return

        return response.text

    def delete_request(self, url, refreshCheck=False):
        if not refreshCheck:
            url = self.ApiUrl + url

        try:
            response = requests.delete(url, headers=self.headers)
            if response.status_code == 401:
                if not refreshCheck:
                    self.refreshToken()
                    self.delete_request(url, refreshCheck=True)
                else:
                    tools.log('Failed to perform trakt request even after token refresh', 'error')

            if response.status_code > 499:
                return None

        except requests.exceptions.ConnectionError:
            return
        except not requests.exceptions.ConnectionError:
            tools.showDialog.ok(tools.addonName, tools.lang(32035))
            return

        return response.text

    def json_response(self, url, postData=None, limit=True, limitOverride=0):
        if postData is None:
            response = self.get_request(url, limit=limit, limitOverride=limitOverride)
        else:
            response = self.post_request(url, postData, limit=limit)
        try:
            response = json.loads(response)
        except:
            return None
        return response

    @staticmethod
    def _get_display_name(type):
        if type == 'movie':
            return tools.lang(40279)
        else:
            return tools.lang(40276)

    def traktManager(self, actionArgs):

        item_information = tools.get_item_information(actionArgs)

        trakt_object = item_information['trakt_object']

        trakt_id = item_information['ids']['trakt']

        actionArgs = json.loads(tools.unquote(actionArgs))

        type = actionArgs['item_type'].lower()

        display_type = self._get_display_name(type)

        if trakt_object is None:
            tools.showDialog.notification(tools.addonName, tools.lang(40264))

        dialog_list = []

        if item_information['info']['playcount'] > 0:
            dialog_list.append(tools.lang(40270))
        else:
            dialog_list.append(tools.lang(40269))

        if 'movies' in trakt_object:
            from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase
            collection = [i['trakt_id'] for i in TraktSyncDatabase().get_collected_movies()]
            if trakt_id in collection:
                dialog_list.append(tools.lang(40266) % display_type)
            else:
                dialog_list.append(tools.lang(40265) % display_type)
        else:
            from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
            collection = TraktSyncDatabase().get_collected_episodes()
            collection = [i for i in collection if i is not None]
            collection = list(set([i['show_id'] for i in collection]))
            trakt_id = trakt_object['show_id'] = actionArgs['trakt_id']
            if trakt_id in collection:
                dialog_list.append(tools.lang(40266) % display_type)
            else:
                dialog_list.append(tools.lang(40265) % display_type)
            pass

        standard_list = [tools.lang(40267), tools.lang(40268),
                         tools.lang(40271), tools.lang(40272), tools.lang(40273) % display_type, tools.lang(40274)]

        for i in standard_list:
            dialog_list.append(i)

        if not type in ['show', 'season']:
            dialog_list.append(tools.lang(40275))

        selection = tools.showDialog.select('{}: {}'.format(tools.addonName, tools.lang(40280)), dialog_list)

        if selection == -1:
            return

        thread = None

        if dialog_list[selection] == tools.lang(40265) % display_type:
            thread = threading.Thread(target=self.addToCollection, args=(trakt_object,))
        elif dialog_list[selection] == tools.lang(40266) % display_type:
            thread = threading.Thread(target=self.removeFromCollection, args=(trakt_object,))
        elif dialog_list[selection] == tools.lang(40267):
            thread = threading.Thread(target=self.addToWatchList, args=(trakt_object,))
        elif dialog_list[selection] == tools.lang(40268):
            thread = threading.Thread(target=self.removeFromWatchlist, args=(trakt_object,))
        elif dialog_list[selection] == tools.lang(40269):
            thread = threading.Thread(target=self.markWatched, args=(trakt_object, actionArgs))
        elif dialog_list[selection] == tools.lang(40270):
            thread = threading.Thread(target=self.markUnwatched, args=(trakt_object, actionArgs))
        elif dialog_list[selection] == tools.lang(40271):
            self.addToList(trakt_object)
        elif dialog_list[selection] == tools.lang(40272):
            self.removeFromList(trakt_object)
        elif dialog_list[selection] == tools.lang(40273) % display_type:
            self.hideItem(actionArgs)
        elif dialog_list[selection] == tools.lang(40274):
            self.refresh_meta_information(trakt_object)
        elif dialog_list[selection] == tools.lang(40275):
            self.removePlaybackHistory(trakt_object)
        else:
            return

        if thread is not None:
            thread.start()

        return

    def refresh_meta_information(self, trakt_object):
        from resources.lib.modules import trakt_sync
        trakt_sync.TraktSyncDatabase().clear_specific_meta(trakt_object)
        tools.container_refresh()
        tools.trigger_widget_refresh()

    def confirm_marked_watched(self, response, type):
        try:
            if response['added'][type] > 0:
                return True

            raise Exception

        except Exception as e:
            tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)), tools.lang(40281))
            tools.log('Failed to mark item as watched, error: %s \n Trakt Response: %s' % (e, response))

            return False

    def confirm_marked_unwatched(self, response, type):
        try:
            if response['deleted'][type] > 0:
                return True

            raise Exception

        except Exception as e:
            tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)), tools.lang(40281))
            tools.log('Failed to mark item as unwatched, error: %s \n Trakt Response: %s' % (e, response))

            return False

    def markWatched(self, trakt_object, actionArgs, silent=False):
        response = self.json_response('sync/history', postData=trakt_object)

        if 'episodes' in trakt_object:
            if not silent:
                if not self.confirm_marked_watched(response, 'episodes'):
                    return
            from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
            trakt_object = trakt_object['episodes'][0]
            TraktSyncDatabase().mark_episode_watched_by_id(trakt_object['ids']['trakt'])
            from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase
            TraktSyncDatabase().remove_bookmark(trakt_object['ids']['trakt'])

        elif 'seasons' in trakt_object:
            if not silent:
                if not self.confirm_marked_watched(response, 'episodes'):
                    return
            from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
            show_id = actionArgs['trakt_id']
            season_no = trakt_object['seasons'][0]['number']
            TraktSyncDatabase().mark_season_watched(show_id, season_no, 1)

        elif 'shows' in trakt_object:
            if not silent:
                if not self.confirm_marked_watched(response, 'episodes'):
                    return
            from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
            trakt_object = trakt_object['shows'][0]
            TraktSyncDatabase().mark_show_watched(trakt_object['ids']['trakt'], 1)

        elif 'movies' in trakt_object:
            if not silent:
                if not self.confirm_marked_watched(response, 'movies'):
                    return
            from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase
            trakt_object = trakt_object['movies'][0]
            TraktSyncDatabase().mark_movie_watched(trakt_object['ids']['trakt'])
            from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase
            TraktSyncDatabase().remove_bookmark(trakt_object['ids']['trakt'])

        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)), tools.lang(40282))
        if not silent:
            tools.container_refresh()
            tools.trigger_widget_refresh()

    def markUnwatched(self, trakt_object, actionArgs):
        response = self.json_response('sync/history/remove', postData=trakt_object)

        if 'episodes' in trakt_object:
            if not self.confirm_marked_unwatched(response, 'episodes'):
                return
            from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
            trakt_object = trakt_object['episodes'][0]
            TraktSyncDatabase().mark_episode_unwatched_by_id(trakt_object['ids']['trakt'])
            from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase
            TraktSyncDatabase().remove_bookmark(trakt_object['ids']['trakt'])

        elif 'seasons' in trakt_object:
            from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
            if not self.confirm_marked_unwatched(response, 'episodes'):
                return
            show_id = actionArgs['trakt_id']
            season_no = trakt_object['seasons'][0]['number']
            TraktSyncDatabase().mark_season_watched(show_id, season_no, 0)

        elif 'shows' in trakt_object:
            from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
            if not self.confirm_marked_unwatched(response, 'episodes'):
                return
            trakt_object = trakt_object['shows'][0]
            TraktSyncDatabase().mark_show_watched(trakt_object['ids']['trakt'], 0)

        elif 'movies' in trakt_object:
            from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase
            if not self.confirm_marked_unwatched(response, 'movies'):
                return
            trakt_object = trakt_object['movies'][0]
            TraktSyncDatabase().mark_movie_unwatched(trakt_object['ids']['trakt'])
            from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase
            TraktSyncDatabase().remove_bookmark(trakt_object['ids']['trakt'])

        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)), tools.lang(40283))
        tools.container_refresh()
        tools.trigger_widget_refresh()

    def addToCollection(self, trakt_object):
        if 'movies' in trakt_object:
            self.post_request('sync/collection', postData=trakt_object)
            from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase
            trakt_object = trakt_object['movies'][0]
            TraktSyncDatabase().mark_movie_collected(trakt_object['ids']['trakt'])
        else:
            trakt_object = {'shows': [{'ids': {'trakt': trakt_object['show_id']}}]}
            self.post_request('sync/collection', postData=trakt_object)
            from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase
            TraktSyncDatabase()._sync_collection_shows()

        tools.container_refresh()
        tools.trigger_widget_refresh()
        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)), tools.lang(40284))

    def removeFromCollection(self, trakt_object):
        if 'movies' in trakt_object:
            self.post_request('sync/collection/remove', postData=trakt_object)
            from resources.lib.modules.trakt_sync.movies import TraktSyncDatabase
            trakt_object = trakt_object['movies'][0]
            TraktSyncDatabase().mark_movie_uncollected(trakt_object['ids']['trakt'])
        else:
            show_id = trakt_object['show_id']
            trakt_object = {'shows': [{'ids': {'trakt': show_id}}]}

            self.post_request('sync/collection/remove', postData=trakt_object)
            from resources.lib.modules.trakt_sync.shows import TraktSyncDatabase
            TraktSyncDatabase().mark_show_collected(show_id, 0)

        tools.container_refresh()
        tools.trigger_widget_refresh()
        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)), tools.lang(40285))

    def addToWatchList(self, trakt_object):
        self.post_request('sync/watchlist', postData=trakt_object)
        tools.container_refresh()
        tools.trigger_widget_refresh()
        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)), tools.lang(40286))

    def removeFromWatchlist(self, trakt_object):
        self.post_request('sync/watchlist/remove', postData=trakt_object)
        tools.container_refresh()
        tools.trigger_widget_refresh()
        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)), tools.lang(40287))

    def addToList(self, trakt_object):
        lists = self.getLists()
        selection = tools.showDialog.select('{}: {}'.format(tools.addonName, tools.lang(40290)),
                                            [i['name'] for i in lists])
        selection = lists[selection]
        self.json_response('users/me/lists/%s/items' % selection['ids']['trakt'], postData=trakt_object)
        tools.container_refresh()
        tools.trigger_widget_refresh()
        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)),
                                      tools.lang(40288) % selection['name'])

    def removeFromList(self, trakt_object):
        lists = self.getLists()
        selection = tools.showDialog.select('{}: {}'.format(tools.addonName, tools.lang(40290)),
                                            [i['name'] for i in lists])
        selection = lists[selection]
        self.json_response('users/me/lists/%s/items/remove' % selection['ids']['trakt'], postData=trakt_object)
        tools.container_refresh()
        tools.trigger_widget_refresh()
        tools.showDialog.notification('{}: {}'.format(tools.addonName, tools.lang(40280)),
                                      tools.lang(40289) % selection['name'])

    def hideItem(self, trakt_object):
        from resources.lib.modules.trakt_sync.hidden import TraktSyncDatabase

        sections = ['progress_watched', 'calendar']
        sections_display = [tools.lang(40291), tools.lang(40292)]
        selection = tools.showDialog.select('{}: {}'.format(tools.addonName, tools.lang(40293)), sections_display)
        if selection == -1:
            return
        section = sections[selection]

        if trakt_object['item_type'] in ['season', 'show', 'episode']:
            trakt_object = {'shows': [{'ids': {'trakt': trakt_object['trakt_id']}}]}
        elif trakt_object['item_type'] == 'movie':
            trakt_object = {'movies': [{'ids': {'trakt': trakt_object['trakt_id']}}]}

        self.json_response('users/hidden/%s' % section, postData=trakt_object)

        if 'movies' in trakt_object:
            trakt_object = trakt_object['movies'][0]
            TraktSyncDatabase().add_hidden_item(trakt_object['ids']['trakt'], 'movie', section)
        if 'shows' in trakt_object:
            trakt_object = trakt_object['shows'][0]
            TraktSyncDatabase().add_hidden_item(trakt_object['ids']['trakt'], 'show', section)

        tools.container_refresh()
        tools.trigger_widget_refresh()
        tools.showDialog.notification(tools.addonName, tools.lang(40294) % sections_display[selection])

    def removePlaybackHistory(self, trakt_object):
        type = 'movie'
        multi_type = 'movies'

        if 'episodes' in trakt_object:
            type = 'episode'
            multi_type = 'episodes'

        progress = self.json_response('sync/playback/%s' % multi_type, limit=False)
        progress = [i for i in progress if i['type'] == type]
        progress = [i for i in progress
                    if i[type]['ids']['trakt'] == trakt_object[multi_type][0]['ids']['trakt']]

        for i in progress:
            self.delete_request('sync/playback/%s' % i['id'])

        from resources.lib.modules.trakt_sync.activities import TraktSyncDatabase
        TraktSyncDatabase().remove_bookmark(trakt_object[multi_type][0]['ids']['trakt'])

        tools.container_refresh()
        tools.trigger_widget_refresh()
        tools.showDialog.notification(tools.addonName, tools.lang(40295))

    def get_username(self):
        user_details = json.loads(self.get_request('users/me'))
        return user_details['username']

    def getLists(self, username='me'):
        lists = self.json_response('users/%s/lists' % username, limit=True, limitOverride=500)
        return lists

    def myTraktLists(self, media_type):
        lists_database = lists.TraktSyncDatabase()
        for user_list in lists_database.get_lists(self._remove_pluralization(media_type), 'myLists'):
            arguments = {'trakt_id': user_list['trakt_id'],
                         'username': user_list['username'],
                         'type': user_list['media_type'],
                         'sort_how': user_list['sort_how'],
                         'sort_by': user_list['sort_by']}

            tools.addDirectoryItem('{} - [COLOR {}]{}[/COLOR]'.format(user_list['name'].encode('utf-8'),
                                                                      tools.get_user_text_color(),
                                                                      user_list['username'].encode('utf-8')),
                                   'traktList&page=1&actionArgs=%s' % tools.quote(json.dumps(arguments)))

        tools.closeDirectory('addons')

    @staticmethod
    def _remove_pluralization(media_type):
        if media_type == 'shows':
            return 'show'
        if media_type == 'movies':
            return 'movie'

    def sort_list(self, sort_by, sort_how, list_items, media_type):
        supported_sorts = ['added', 'rank', 'title', 'released', 'runtime', 'popularity', 'votes', 'random']

        if sort_by == 'added':
            list_items = sorted(list_items, key=lambda x: x['listed_at'])
        if sort_by == 'rank':
            list_items = sorted(list_items, key=lambda x: x['rank'])
        if sort_by == 'title':
            list_items = sorted(list_items, key=lambda x: x[media_type]['title'].lower().replace('the ', ''))
        if sort_by == 'released':
            try:
                list_items = sorted(list_items, key=lambda x: x[media_type]['released'])
            except:
                list_items = sorted(list_items, key=lambda x: x[media_type]['first_aired'])
        if sort_by == 'runtime':
            if 'aired_episodes' in list_items[0][media_type]:
                list_items = sorted(list_items, key=lambda x:
                (x[media_type]['runtime'] * x[media_type]['aired_episodes']))
            else:
                list_items = sorted(list_items, key=lambda x: x[media_type]['runtime'])
        if sort_by == 'popularity':
            list_items = sorted(list_items, key=lambda x: x[media_type]['rating'])
        if sort_by == 'votes':
            list_items = sorted(list_items, key=lambda x: x[media_type]['votes'])
        if sort_by == 'random':
            import random
            list_items = random.shuffle(list_items)

        if sort_by not in supported_sorts:
            return list_items

        if sort_how == 'desc':
            list_items.reverse()

        return list_items

    def getListItems(self, arguments, page):
        lists_database = lists.TraktSyncDatabase()
        paginate_lists = (tools.getSetting('general.paginatetraktlists') == 'true')
        arguments = json.loads(tools.unquote(arguments))
        media_type = arguments['type']
        list_items = ast.literal_eval(lists_database.get_list(arguments['trakt_id'], media_type, arguments['username'])['kodi_meta'])
        max_items = len(list_items)

        if paginate_lists:
            list_items = tools.paginate_list(list_items, int(page), int(tools.getSetting('item.limit')))

        if media_type in ['show', 'shows']:
            from resources.lib.gui import tvshowMenus
            tvshowMenus.Menus().showListBuilder(list_items)

        if media_type in ['movie', 'movies']:
            from resources.lib.gui import movieMenus
            movieMenus.Menus().commonListBuilder(list_items)

        content_type = 'tvshows'
        if media_type in ['movie', 'movies']:
            content_type = 'movies'

        if paginate_lists:
            limit = int(tools.getSetting('item.limit'))
            if int(page) * limit < max_items:
                tools.addDirectoryItem(tools.lang(32019), 'traktList&page=%s&actionArgs=%s' %
                                       (int(page) + 1, tools.quote(json.dumps(arguments))))
        tools.closeDirectory(content_type)
        return
