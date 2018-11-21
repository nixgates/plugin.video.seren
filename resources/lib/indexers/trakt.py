import requests, json, threading
from time import sleep
from resources.lib.common import tools

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
                        'trakt-api-key': self.ClientID}

        if not self.AccessToken is '':
            self.headers['Authorization'] = 'Bearer %s' % self.AccessToken

    def revokeAuth(self):
        url = "oauth/revoke"
        postData={"token": tools.getSetting('trakt.auth')}
        response = self.post_request(url, postData, limit=False)
        tools.setSetting('trakt.auth', '')
        tools.setSetting('trakt.refresh', '')
        tools.setSetting('trakt.username', '')
        tools.showDialog.ok(tools.addonName, tools.lang(32030))

    def auth(self):


        url = 'https://api.trakt.tv/oauth/device/code'
        postData = {'client_id': self.ClientID}
        response = requests.post(url, data=postData)
        response = json.loads(response.text)
        try:
            user_code = response['user_code']
            device = response['device_code']
            interval = int(response['interval'])
            expiry = int(response['expires_in'])
        except:
            pass

        currentTime = 0
        tools.copy2clip(user_code)
        tools.progressDialog.create(tools.addonName + ': ' + tools.lang(32031), tools.lang(32024) +
                                    tools.colorString('https://trakt.tv/activate \n') +
                                    tools.lang(32025) + tools.colorString(user_code) + "\n" +
                                    "This code has been copied to your clipboard"


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
                self.headers['Authorization'] = 'Bearer %s' % response['access_token']
                tools.setSetting('trakt.username', self.get_username())
                tools.progressDialog.close()
                tools.showDialog.ok(tools.addonName, 'Sucessfully authenticated with Trakt')
                break
            if '400' in str(response):
                pass
            else:
                tools.showDialog.ok(tools.addonName, tools.lang(32032))
                tools.progressDialog.close()
                tools.showDialog.ok(tools.addonName, tools.lang(32033))

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

    def get_request(self, url, limit=True, limitOverride=0, refreshCheck=False):

        if refreshCheck == False:
            url = self.ApiUrl + url
            if limit == True:
                if limitOverride == 0:
                    limitAmount = int(tools.getSetting('item.limit'))
                else:
                    limitAmount = limitOverride
                if not '?' in url:
                    url += '?limit=%s' % limitAmount
                url += '&limit=%s' % limitAmount

        try:

            response = requests.get(url, headers=self.headers)

            if response.status_code == 401:
                tools.log('Trakt OAuth Failure, %s %s' % (str(response.text), response.request.headers), 'info')
                if refreshCheck == False:
                    self.refreshToken()
                    self.get_request(url, refreshCheck=True)
                else:
                    tools.log('Failed to perform request even after token refresh', 'error')
            if response.status_code > 499:
                return None
            if response.status_code == 404:
                return '[]'
            if response.status_code == 502:
                tools.log('Trakt is currently experiencing Gateway Issues')
        except requests.exceptions.ConnectionError:
            tools.showDialog.ok(tools.addonName, tools.lang(32034))
            return
        except not requests.exceptions.ConnectionError:
            tools.showDialog.ok(tools.addonName, tools.lang(32035))
            return
        return response.text

    def post_request(self, url, postData, limit=True, refreshCheck=False):
        if refreshCheck == False:
            url = self.ApiUrl + url
            if limit == True:
                limitAmount = tools.getSetting('item.limit')
                if not '?' in url:
                    url += '?limit=%s' % limitAmount
                url += '&limit=%s' % limitAmount
        try:
            response = requests.post(url, json=postData, headers=self.headers)
            if response.status_code == 401:
                if refreshCheck == False:
                    self.refreshToken()
                    self.post_request(url, postData, limit=limit, refreshCheck=True)
                else:
                    tools.log('Failed to perform trakt request even after token refresh', 'error')

            if response.status_code > 499:
                return None

        except requests.exceptions.ConnectionError:
            tools.showDialog.ok(tools.addonName, tools.lang(32034))
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
        try: response = json.loads(response)
        except: return None
        return response

    def traktManager(self, trakt_object):
        trakt_object = json.loads(tools.unquote(trakt_object))
        if trakt_object == None:
            tools.showDialog.notification(tools.addonName, 'There may be an issue with the Trakt service, please clear cache and wait')

        dialog_list = ['Add to Collection', 'Remove from Collection', 'Add to Watchlist', 'Remove from Watchlist',
                       'Mark as Watched', 'Mark as Unwatched', 'Add to List', 'Remove From List']

        selection = tools.showDialog.select(tools.addonName + ': Trakt Manager', dialog_list)
        thread = None

        if selection == 0:
            thread = threading.Thread(target=self.addToCollection, args=(trakt_object,))
        elif selection == 1:
            thread = threading.Thread(target=self.removeFromCollection, args=(trakt_object,))
        elif selection == 2:
            thread = threading.Thread(target=self.addToWatchList, args=(trakt_object,))
        elif selection == 3:
            thread = threading.Thread(target=self.removeFromWatchlist, args=(trakt_object,))
        elif selection == 4:
            thread = threading.Thread(target=self.markWatched, args=(trakt_object,))
        elif selection == 5:
            thread = threading.Thread(target=self.markUnwatched, args=(trakt_object,))
        elif selection == 6:
            self.addToList(trakt_object)
        elif selection == 7:
            self.removeFromList(trakt_object)
        else:
            return

        if thread is not None:
            thread.start()

        return

    def markWatched(self, trakt_object):
        self.post_request('sync/history', postData=trakt_object)
        tools.showDialog.notification(tools.addonName + ': Trakt Manager', 'Item marked as watched')

    def markUnwatched(self, trakt_object):
        self.post_request('sync/history/remove', postData=trakt_object)
        tools.showDialog.notification(tools.addonName + ': Trakt Manager', 'Item marked as unwatched')

    def addToCollection(self, trakt_object):
        self.post_request('sync/collection', postData=trakt_object)
        tools.showDialog.notification(tools.addonName + ': Trakt Manager', 'Item added to Collection')

    def removeFromCollection(self, trakt_object):

        self.post_request('sync/collection/remove', postData=trakt_object)
        tools.showDialog.notification(tools.addonName + ': Trakt Manager', 'Item removed from Collection')

    def addToWatchList(self, trakt_object):
        self.post_request('sync/watchlist', postData=trakt_object)
        tools.showDialog.notification(tools.addonName + ': Trakt Manager', 'Item added to Watchlist')

    def removeFromWatchlist(self, trakt_object):
        self.post_request('sync/watchlist/remove', postData=trakt_object)
        tools.showDialog.notification(tools.addonName + ': Trakt Manager', 'Item removed from Watchlist')

    def addToList(self, trakt_object):
        lists = self.getLists()
        selection = tools.showDialog.select(tools.addonName + ": Select a list", [i['name'] for i in lists])
        selection = lists[selection]
        self.json_response('users/me/lists/%s/items' % selection['ids']['trakt'], postData=trakt_object)
        tools.showDialog.notification(tools.addonName + ': Trakt Manager', 'Item added to %s' % selection['name'])

    def removeFromList(self, trakt_object):
        lists = self.getLists()
        selection = tools.showDialog.select(tools.addonName + ": Select a list", [i['name'] for i in lists])
        selection = lists[selection]
        self.json_response('users/me/lists/%s/items/remove' % selection['ids']['trakt'], postData=trakt_object)
        tools.showDialog.notification(tools.addonName + ': Trakt Manager', 'Item removed from %s' % selection['name'])

    def get_username(self):
        settings = json.loads(self.get_request('users/settings'))
        return settings['user']['username']

    def getLists(self, username='me'):
        lists = self.json_response('users/%s/lists' % username)
        return lists

    def myTraktLists(self, media_type):

        lists = self.getLists()
        lists += [i['list'] for i in self.json_response('users/likes/lists', limit=False)]
        for user_list in lists:
            arguments = {'trakt_id': user_list['ids']['trakt'],
                         'username': user_list['user']['username'],
                         'type': media_type,
                         'sort_how': user_list['sort_how'],
                         'sort_by': user_list['sort_by']
                         }
            tools.addDirectoryItem(user_list['name'], 'traktList&page=1&actionArgs=%s' % tools.quote(json.dumps(arguments))
                                   , None, None)

        tools.closeDirectory('addons')
        return

    def getListItems(self, arguments, page):

        arguments = json.loads(tools.unquote(arguments))
        media_type = arguments['type']

        list_items = self.json_response('users/%s/lists/%s/items/%s?extended=full'
                                        % (arguments['username'],
                                           arguments['trakt_id'],
                                           media_type), limit=False)

        sort_by = arguments['sort_by']

        supported_sorts = ['added', 'rank', 'title', 'released', 'runtime', 'popularity', 'votes', 'random']

        if media_type == 'movies':
            media_type = 'movie'

        if media_type == 'shows':
            media_type = 'show'

        if sort_by == 'added':
            list_items = sorted(list_items, key=lambda x: x['listed_at'])
        if sort_by == 'rank':
            list_items = sorted(list_items, key=lambda x: x['rank'])
        if sort_by == 'title':
            list_items = sorted(list_items, key=lambda x: x[media_type]['title'])
        if sort_by == 'released':
            list_items = sorted(list_items, key=lambda x: x[media_type]['released'])
        if sort_by =='runtime':
            list_items = sorted(list_items, key=lambda x: x[media_type]['runtime'])
        if sort_by == 'popularity':
            list_items = sorted(list_items, key=lambda x: x[media_type]['rating'])
        if sort_by == 'votes':
            list_items = sorted(list_items, key=lambda x: x[media_type]['votes'])
        if sort_by == 'random':
            import random
            list_items = random.shuffle(list_items)

        if sort_by not in supported_sorts:
            list_items = sorted(list_items, key=lambda x: x['listed_at'])

        if arguments['sort_how'] == 'desc':
            list_items.reverse()

        limitAmount = int(tools.getSetting('item.limit'))
        split = (int(page) - 1) * limitAmount
        list_items = list_items[split:]
        list_items = list_items[:limitAmount]

        if media_type == 'show':
            list_items = [i['show'] for i in list_items if i['type'] == 'show']
            from resources.lib.gui import tvshowMenus
            tvshowMenus.Menus().showListBuilder(list_items)

        if media_type == 'movie':
            list_items = [i['movie'] for i in list_items if i['type'] == 'movie']
            from resources.lib.gui import movieMenus
            movieMenus.Menus().commonListBuilder(list_items)

        content_type = 'tvshows'

        if arguments['type'] == 'movie':
            content_type = 'movies'

        if len(list_items) == int(tools.getSetting('item.limit')):
            page = int(page) + 1
            tools.addDirectoryItem('Next', 'traktList&page=%s&actionArgs=%s' %
                                   (str(page), tools.quote(json.dumps(arguments))), '', '')
        tools.closeDirectory(content_type)
        return





