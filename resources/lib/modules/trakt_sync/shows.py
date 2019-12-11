import ast
import copy
import threading
from datetime import datetime

from resources.lib.common import tools
from resources.lib.indexers import trakt, imdb, tmdb
from resources.lib.indexers import tvdb
from resources.lib.modules import database
from resources.lib.modules import trakt_sync


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):

    def mark_show_watched(self, show_id, watched):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=? WHERE show_id=?', (watched, show_id,))
        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        from activities import TraktSyncDatabase as activities_database
        sync_thread = threading.Thread(target=activities_database()._sync_watched_episodes())
        sync_thread.run()

    def mark_season_watched(self, show_id, season, watched):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=? WHERE show_id=? AND season=?', (watched, show_id, season))
        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        from activities import TraktSyncDatabase as activities_database
        sync_thread = threading.Thread(target=activities_database()._sync_watched_episodes())
        sync_thread.run()

    def mark_show_collected(self, show_id, collected):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET collected=? WHERE show_id=?', (collected, show_id,))
        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        from activities import TraktSyncDatabase as activities_database
        sync_thread = threading.Thread(target=activities_database()._sync_collection_shows())
        sync_thread.run()

    def mark_season_collected(self, show_id, season, collected):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET collected=? WHERE show_id=? AND season=?', (collected, show_id, season))
        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        from activities import TraktSyncDatabase as activities_database
        sync_thread = threading.Thread(target=activities_database()._sync_collection_shows())
        sync_thread.run()

    def mark_episode_watched(self, show_id, season, number):
        self._mark_episode_record('watched', 1, show_id, season, number)

    def mark_episode_watched_by_id(self, trakt_id):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=1 WHERE trakt_id=?', (trakt_id,))
        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

    def mark_episode_unwatched_by_id(self, trakt_id):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=0 WHERE trakt_id=?', (trakt_id,))
        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

    def mark_episode_unwatched(self, show_id, season, number):
        self._mark_episode_record('watched', 0, show_id, season, number)

    def mark_episode_collected(self, show_id, season, number):
        self._mark_episode_record('collected', 1, show_id, season, number)

    def mark_episode_uncollected(self, show_id, season, number):
        self._mark_episode_record('collected', 0, show_id, season, number)

    def _mark_show_record(self, column, value, show_id):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('UPDATE shows SET %s=? WHERE trakt_id=?' % column, (value, show_id))
        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

    def _mark_episode_record(self, column, value, show_id, season, number):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET %s=? WHERE show_id=? AND season=? AND number=?' % column, (value, show_id,
                                                                                                       season,
                                                                                                       number))
        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

    def get_all_shows(self):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM shows')
        shows = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        shows = [i['trakt_id'] for i in shows]

        return shows

    def get_watched_shows(self):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM shows s INNER JOIN (SELECT distinct show_id FROM episodes '
                       'WHERE watched = 1) e ON e.show_id == s.trakt_id')
        shows = []
        for show in cursor.fetchall():
            show['kodi_meta'] = ast.literal_eval(show['kodi_meta'])
            shows.append(show)

        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        return shows

    def get_watched_episodes(self):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM episodes WHERE watched=1')
        episodes = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

        return episodes

    def get_collected_episodes(self):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM episodes WHERE collected=1')
        episodes = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

        return episodes

    def get_season_list(self, show_id):
        self.threads = []
        show_meta = self.get_single_show(show_id)
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('SELECT* FROM seasons WHERE show_id = ?', (show_id,))
        seasons = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        season_count = int(show_meta['info']['season_count'])
        try:
            if len([i for i in seasons if i['kodi_meta'] == '{}']) > 0:
                raise Exception
            if len([i for i in seasons if int(i['season']) != 0]) == season_count:
                seasons = [i for i in seasons if i['kodi_meta'] != '{}']
                if len(seasons) == 0 or len(seasons) != season_count:
                    raise Exception
                seasons = [ast.literal_eval(season['kodi_meta']) for season in seasons]
                seasons = [self.get_season_watch_info(season) for season in seasons]
                return seasons
        except:
            # We likely haven't built the meta information yet
            pass

        seasons = trakt.TraktAPI().json_response('shows/%s/seasons' % show_meta['ids']['trakt'])

        # Maybe we can add here other providers to get some more information out
        # if seasons is None:
        #    return self.item_list

        for season in seasons:
            self.threads.append(threading.Thread(target=self.get_single_season, args=(show_meta['ids']['trakt'],
                                                                                      season['number'], True)))

        for i in self.threads:
            i.start()

        for i in self.threads:
            # What the actual fuck? There are a stack of threads being created somehow after the first start is called
            # If someone can spot the issue here, I'd love to know what the fuck I've done wrong lol
            try:
                i.join()
            except:
                break

        self.threads = []

        return self.item_list

    def update_show_list(self, show_list, watch_info=True):
        for i in show_list:
            self.task_queue.put(self.get_single_show, i, True, watch_info)

        self.task_queue.wait_completion()

        return self.item_list

    def get_show_list(self, show_list, watch_info=True):

        # Ease of use to get full list from DB
        # We first attempt to pull the entire list in one DB hit to minimise transactions
        # Failing ability to get all items, we send the required items to be updated and then return

        if type(show_list[0]) is dict:
            if 'show' in show_list[0]:
                show_list = [i['show'] for i in show_list]

            if 'ids' in show_list[0]:
                show_list = [i['ids']['trakt'] for i in show_list]

        show_list = set(show_list)

        self.item_list = []
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        db_query = 'SELECT * FROM shows WHERE trakt_id IN (%s)' % ','.join((str(i) for i in show_list))
        cursor.execute(db_query)
        show_db_list = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        requires_update = []

        for show_id in show_list:
            db_item = [i for i in show_db_list if i['trakt_id'] == show_id]
            if len(db_item) == 1:
                db_item = db_item[0]
                if db_item['kodi_meta'] == '{}':
                    requires_update.append(show_id)
            else:
                requires_update.append(show_id)

        if len(requires_update) == 0:
            meta_list = [ast.literal_eval(i['kodi_meta']) for i in show_db_list if i['kodi_meta'] != '{}']
            meta_list = [self.get_show_watched_info(i) for i in meta_list]
            return meta_list
        else:
            self.update_show_list(requires_update, watch_info)
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute(db_query)
        show_db_list = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        meta_list = [ast.literal_eval(i['kodi_meta']) for i in show_db_list if i['kodi_meta'] != '{}']
        meta_list = [self.get_show_watched_info(i) for i in meta_list]

        return meta_list

    def get_flat_episode_list(self, show_id):

        show_meta = self.get_single_show(show_id)
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()

        cursor.execute('SELECT * FROM episodes WHERE show_id=?', (show_id,))
        episodes = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        try:
            if len(episodes) != int(show_meta['info']['episode_count']):
                raise Exception

            if len([i for i in episodes if i['kodi_meta'] == '{}']) > 0:
                raise Exception

            return self.get_meta_episode_list(episodes, [show_meta])

        except:

            seasons = trakt.TraktAPI().json_response('shows/%s/seasons?extended=episodes' % show_id)
            episodes = [episode for season in seasons for episode in season['episodes']]

            for i in episodes:
                self.task_queue.put(self.get_single_episode, show_id, i['season'], i['number'], True)

            self.task_queue.wait_completion()

            return self.item_list

    def get_episode_list(self, episode_dicts):
        self.item_list = []
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        values = ('(show_id = %s AND season=%s AND number=%s)' % (i['show']['ids']['trakt'], i['episode']['season'],
                                                                  i['episode']['number']) for i in episode_dicts)
        db_query = 'SELECT * FROM episodes WHERE %s' % ' OR '.join(values)

        cursor.execute(db_query)
        episode_db_list = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        requires_update = []

        for episode_object in episode_dicts:
            db_item = [i for i in episode_db_list
                       if i['show_id'] == episode_object['show']['ids']['trakt']
                       and i['season'] == episode_object['episode']['season']
                       and i['number'] == episode_object['episode']['number']]
            if len(db_item) == 1:
                db_item = db_item[0]
                if db_item['kodi_meta'] == '{}':
                    requires_update.append(episode_object)
            else:
                requires_update.append(episode_object)

        if len(requires_update) == 0:
            show_list = self.get_show_list([i['show_id'] for i in episode_db_list])

            return self.get_meta_episode_list(episode_db_list, show_list)
        else:
            self.update_episode_list(requires_update)
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute(db_query)
        episode_db_list = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        show_list = self.get_show_list([i['show_id'] for i in episode_db_list])

        return self.get_meta_episode_list(episode_db_list, show_list)

    def update_episode_list(self, episode_dicts):
        self.item_list = []
        for item in episode_dicts:
            self.task_queue.put(self.get_single_episode, item['show']['ids']['trakt'], item['episode']['season'],
                                item['episode']['number'])
        self.task_queue.wait_completion()

        return self.item_list

    def get_meta_episode_list(self, episode_list, show_list):
        meta_list = []

        for episode in episode_list:
            try:
                episode['kodi_meta'] = ast.literal_eval(episode['kodi_meta'])
                if 'info' not in episode['kodi_meta']:
                    continue
                episode['kodi_meta'].update({'showInfo': [i for i in show_list
                                                          if i['ids']['trakt'] == episode['show_id']][0]})
                episode['kodi_meta'] = self.clean_episode_showinfo(episode['kodi_meta'])
                episode = self.update_episode_playcount(episode)
                meta_list.append(episode['kodi_meta'])
            except:
                import traceback
                traceback.print_exc()
                pass

        return meta_list

    def get_season_episodes(self, show_id, season):
        self.item_list = []
        try:
            tools.traktSyncDB_lock.acquire()
            cursor = self._get_cursor()
            cursor.execute('SELECT * FROM shows WHERE trakt_id=?', (show_id,))
            show_object = cursor.fetchone()
            cursor.execute('SELECT * FROM seasons WHERE show_id=? AND season=?', (show_id, season))
            season_object = cursor.fetchone()
            cursor.execute('SELECT * FROM episodes WHERE show_id=? AND season=?', (show_id, season))
            season_episodes = cursor.fetchall()
            cursor.close()
            tools.try_unlock(tools.traktSyncDB_lock)

            show_object = ast.literal_eval(show_object['kodi_meta'])
            season_meta = ast.literal_eval(season_object['kodi_meta'])
            season_episode_count = season_meta['info']['episode_count']
            season_aired_count = season_meta['info']['aired_episodes']

            if int(season_episode_count) == 0:
                raise Exception

            if int(season_episode_count) > int(season_aired_count):
                # Because of trakt caching, we can not trust the information gathered on the last call if the season
                # is not completely aired. We can limit the amount this slow down is occured by limiting it to
                # only unfinished seasons
                raise Exception

            if len(season_episodes) < int(season_aired_count):
                raise Exception

            if len([i for i in season_episodes if i['kodi_meta'] == '{}']) > 0:
                raise Exception

            for episode in season_episodes:
                episode['kodi_meta'] = ast.literal_eval(episode['kodi_meta'])

            for episode in season_episodes:
                episode = self.update_episode_playcount(episode)
                episode['kodi_meta'].update({'showInfo': show_object})

            return [episode['kodi_meta'] for episode in season_episodes]

        except:
            from resources.lib.common import tools

            trakt_list = database.get(trakt.TraktAPI().json_response, 24, 'shows/%s/seasons/%s' % (show_id, season))

            for i in trakt_list:
                self.task_queue.put(self.get_single_episode, show_id, season, i['number'], True)

            self.task_queue.wait_completion()

            return self.item_list

    def _get_show_episodes(self, show_id, meta=False):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM episodes WHERE show_id=?', (show_id,))
        episodes = cursor.fetchall()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        if meta:
            episodes = [episode['kodi_meta'] for episode in episodes]
        return episodes

    def get_single_show(self, show_id, list_mode=False, watch_info=True, get_meta=True):
        tools.traktSyncDB_lock.acquire()
        # Get show from Database if it exsits, else create new record
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM shows WHERE trakt_id=?', (int(show_id),))
        item = cursor.fetchone()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

        if item is None:
            if get_meta:
                show_item = database.get(trakt.TraktAPI().json_response, 24, '/shows/%s?extended=full' % show_id)
            else:
                show_item = None
            item = self._update_show(show_id, show_item, get_meta)

        else:
            if item['kodi_meta'] == '{}' and get_meta:
                show_item = database.get(trakt.TraktAPI().json_response, 24, '/shows/%s?extended=full' % show_id)
                item = self._update_show(show_id, show_item, get_meta)
            else:
                item['kodi_meta'] = ast.literal_eval(item['kodi_meta'])

        if item is None:
            return

        if watch_info and get_meta:
            item['kodi_meta'] = self.get_show_watched_info(item['kodi_meta'])

        if list_mode:
            self.item_list.append(copy.deepcopy(item['kodi_meta']))
        else:
            return item['kodi_meta']

    def get_show_watched_info(self, show_meta):

        try:
            episodes = self._get_show_episodes(show_meta['ids']['trakt'])
            aired_episodes = int(show_meta['info']['episode_count'])

            play_count = len([episode for episode in episodes if int(episode['season']) != 0
                              and episode['watched'] == 1])
            show_meta['info']['WatchedEpisodes'] = play_count
            show_meta['info']['UnWatchedEpisodes'] = aired_episodes - play_count if aired_episodes != 0 else 0
            if play_count < aired_episodes or aired_episodes == 0:
                play_count = 0
            else:
                play_count = 1

            show_meta['info']['playcount'] = play_count

            return show_meta
        except:
            import traceback
            traceback.print_exc()

            return show_meta

    def get_single_season(self, show_id, season, list_mode=False, get_meta=True):

        show_meta = self.get_single_show(show_id)

        if show_meta is None:
            return
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM seasons WHERE show_id=? AND season=?', (show_id, season))
        item = cursor.fetchone()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

        if item is None or (item['kodi_meta'] == '{}' and get_meta):
            try:
                season_meta = trakt.TraktAPI().json_response('shows/%s/seasons/?extended=full' % show_id)
                season_meta = [i for i in season_meta if i['number'] == int(season)][0]
                item = self._update_season(show_meta, season_meta, get_meta)
                if item is None:
                    return
            except:
                return None
        else:
            item['kodi_meta'] = ast.literal_eval(item['kodi_meta'])

        item['kodi_meta'] = self.get_season_watch_info(item['kodi_meta'])

        if list_mode:
            self.item_list.append(copy.deepcopy(item['kodi_meta']))
        else:
            return item['kodi_meta']

    def get_season_watch_info(self, season_meta):
        if season_meta is None:
            return None
        try:
            if int(season_meta['info']['aired_episodes']) != 0:
                play_count = 0
                if int(season_meta['info']['episode_count']) == 0:
                    season_meta['info']['playcount'] = play_count
                    season_meta['info']['WatchedEpisodes'] = 0
                    season_meta['info']['UnWatchedEpisodes'] = 0
                    return season_meta

                show_id = season_meta['showInfo']['ids']['trakt']
                season_no = season_meta['info']['season']
                tools.traktSyncDB_lock.acquire()
                cursor = self._get_cursor()
                cursor.execute('SELECT * FROM episodes WHERE watched=1 AND season=? AND show_id=?',
                               (season_no, show_id))
                episodes = cursor.fetchall()
                cursor.close()
                tools.try_release_lock(tools.traktSyncDB_lock)

                if len(episodes) < int(season_meta['info']['aired_episodes']):
                    play_count = 0
                else:
                    play_count = 1

                season_meta['info']['playcount'] = play_count
                season_meta['info']['WatchedEpisodes'] = len(episodes)
                season_meta['info']['UnWatchedEpisodes'] = int(season_meta['info']['aired_episodes']) - len(episodes)
            else:
                season_meta['info']['playcount'] = 0
                season_meta['info']['WatchedEpisodes'] = 0
                season_meta['info']['UnWatchedEpisodes'] = 0

            return season_meta
        except:
            if 'info' in season_meta:
                season_meta['info']['playcount'] = 0
                season_meta['info']['WatchedEpisodes'] = 0
                season_meta['info']['UnWatchedEpisodes'] = 0
            return season_meta

    def get_single_episode(self, show_id, season, episode, list_mode=False, get_meta=True,
                           watched=None, collected=None):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()

        cursor.execute('SELECT * FROM episodes WHERE show_id=? AND season=? AND number=?',
                       (show_id, season, episode))
        item = cursor.fetchone()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

        show_meta = self.get_single_show(show_id, get_meta=get_meta, watch_info=False)

        if show_meta is None:
            return

        if item is None:
            episode_object = database.get(trakt.TraktAPI().json_response, 24,
                                          '/shows/%s/seasons/%s/episodes/%s?extended=full' % (show_id, season, episode))
            if episode_object is None:
                return

            item = self._update_episode(show_id, episode_object, get_meta, watched, collected)
        else:
            if get_meta and item['kodi_meta'] == '{}':
                episode_object = database.get(trakt.TraktAPI().json_response, 24,
                                              '/shows/%s/seasons/%s/episodes/%s?extended=full' %
                                              (show_id, season, episode))
                if episode_object is None:
                    return

                item = self._update_episode(show_id, episode_object, get_meta, watched, collected)
            else:
                item['kodi_meta'] = ast.literal_eval(item['kodi_meta'])

        if item is None:
            return

        item['kodi_meta'].update({'showInfo': show_meta})

        if item['collected'] == 0 and collected == 1:
            self._mark_episode_record('collected', 1, item['show_id'], item['season'], item['number'])

        if item['watched'] == 0 and watched == 1:
            self._mark_episode_record('watched', 1, item['show_id'], item['season'], item['number'])

        try:
            if get_meta:
                item['kodi_meta'] = self.clean_episode_showinfo(item['kodi_meta'])
                item = self.update_episode_playcount(item)
        except:
            import traceback
            traceback.print_exc()
            pass

        if list_mode:
            try:
                self.item_list.append(copy.deepcopy(item['kodi_meta']))
            except:
                import traceback
                traceback.print_exc()
                pass
        else:
            return item['kodi_meta']

    def clean_episode_showinfo(self, item):
        item['showInfo']['info'].pop('plot', '')
        item['showInfo'].pop('cast', '')
        return item

    def update_episode_playcount(self, item):

        try:
            if item is None:
                return item
            if item['kodi_meta'] == {}:
                return item

            if item['watched'] == 1:
                item['kodi_meta']['info']['playcount'] = 1
            else:
                item['kodi_meta']['info']['playcount'] = 0
        except:
            import traceback
            traceback.print_exc()
            pass

        return item

    def _update_show(self, trakt_id, show_item, get_meta=True):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM shows WHERE trakt_id=?', (trakt_id,))
        old_entry = cursor.fetchone()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)

        if get_meta:
            try:
                kodi_meta = tvdb.TVDBAPI().seriesIDToListItem(show_item)
                if kodi_meta is None or kodi_meta == '{}':
                    kodi_meta = tmdb.TMDBAPI().showToListItem(show_item)
                if kodi_meta is None or kodi_meta == '{}':
                    kodi_meta = imdb.IMDBScraper().showToListItem(show_item)
                if kodi_meta is None or kodi_meta == '{}':
                    return
                update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
            except:
                return None
        else:
            if old_entry is None:
                kodi_meta = {}
                update_time = self.base_date
            else:
                update_time = old_entry['last_updated']
                kodi_meta = old_entry['kodi_meta']
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        try:
            cursor.execute('PRAGMA foreign_keys=OFF')
            cursor.execute(
                "REPLACE INTO shows ("
                "trakt_id, kodi_meta, last_updated, air_date)"
                "VALUES "
                "(?, ?, ?, ?)",
                (int(trakt_id), str(kodi_meta), update_time, kodi_meta['info']['premiered']))
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.connection.commit()
            cursor.close()

            return {'trakt_id': trakt_id, 'kodi_meta': kodi_meta, 'last_updated': update_time}
        except:
            cursor.close()

            import traceback
            traceback.print_exc()
            pass
        finally:
            tools.try_release_lock(tools.traktSyncDB_lock)

    def _update_season(self, show_meta, season_meta, get_meta=True):

        if get_meta:
            try:
                kodi_meta = tvdb.TVDBAPI().seasonIDToListItem(season_meta, show_meta)
                if kodi_meta is None or kodi_meta == '{}':
                    kodi_meta = tmdb.TMDBAPI().showSeasonToListItem(season_meta, show_meta)
                if kodi_meta is None or kodi_meta == '{}':
                    kodi_meta = imdb.IMDBScraper().showSeasonToListItem(season_meta, show_meta)
            except:
                return None
        else:
            kodi_meta = {}

        season = season_meta['number']
        show_id = show_meta['ids']['trakt']
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()

        try:
            cursor.execute(
                "REPLACE INTO seasons ("
                "show_id, season, kodi_meta, air_date)"
                "VALUES "
                "(?, ?, ?, ?)",
                (int(show_id), str(season), str(kodi_meta), kodi_meta['info']['aired']))
            cursor.connection.commit()
            cursor.close()
            return {'show_id': show_meta['ids']['trakt'], 'season': season, 'kodi_meta': kodi_meta}

        except:
            cursor.close()
            import traceback
            traceback.print_exc()
            pass
        finally:
            tools.try_release_lock(tools.traktSyncDB_lock)

    def _update_episode(self, show_id, episode_object, get_meta=True, watched=None, collected=None):
        episode_id = episode_object['ids']['trakt']
        season = episode_object['season']
        old_entry = None
        number = episode_object['number']

        show_meta = self.get_single_show(show_id, get_meta=get_meta)
        if show_meta is None:
            return

        season_meta = self.get_single_season(show_id, season, get_meta=get_meta)
        if season_meta is None:
            return

        try:
            tools.traktSyncDB_lock.acquire()
            cursor = self._get_cursor()
            cursor.execute("SELECT * FROM episodes WHERE trakt_id=?", (episode_id,))
            old_entry = cursor.fetchone()
            cursor.close()
            tools.try_release_lock(tools.traktSyncDB_lock)
        except:
            pass

        if show_meta == '{}' and get_meta:
            return

        show_meta = {'showInfo': show_meta, 'seasonInfo': season_meta}

        if (get_meta and old_entry is None) or (get_meta and old_entry['kodi_meta'] == '{}'):
            try:
                kodi_meta = tvdb.TVDBAPI().episodeIDToListItem(episode_object, copy.deepcopy(show_meta))
                if kodi_meta is None or kodi_meta == '{}':
                    kodi_meta = tmdb.TMDBAPI().episodeIDToListItem(episode_object, copy.deepcopy(show_meta))
                if kodi_meta is None or kodi_meta == '{}':
                    kodi_meta = imdb.IMDBScraper().episodeIDToListItem(episode_object, copy.deepcopy(show_meta))
                if kodi_meta is None or kodi_meta == '{}':
                    return
            except:
                return None
            kodi_meta.pop('showInfo')
            update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        else:
            if old_entry is None:
                update_time = self.base_date
                kodi_meta = {}
            else:
                update_time = old_entry['last_updated']
                kodi_meta = old_entry['kodi_meta']

        if old_entry is None:
            old_entry = {'collected': 0, 'watched': 0, 'air_date': ''}

        if collected is None:
            collected = old_entry['collected']

        if watched is None:
            watched = old_entry['watched']
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()

        try:
            cursor.execute(
                "REPLACE INTO episodes ("
                "show_id, season, trakt_id, kodi_meta, last_updated, watched, collected, number, air_date)"
                "VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (show_id, season, episode_id, str(kodi_meta), update_time, watched, collected, number,
                 kodi_meta['info']['premiered']))

            cursor.connection.commit()
            cursor.close()

            return {'show_id': show_id, 'season': season, 'episode_id': episode_id, 'kodi_meta': kodi_meta,
                    'update_time': update_time, 'watched': watched, 'collected': collected, 'number': number}
        except:
            cursor.close()

            import traceback
            traceback.print_exc()
            pass
        finally:
            tools.try_release_lock(tools.traktSyncDB_lock)

    def _sync_insert_episode(self, show_id, episode_id, season, episode, watched=None, collected=None):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()

        cursor.execute('SELECT * FROM episodes WHERE show_id=? AND season=? AND number=?',
                       (show_id, season, episode))
        item = cursor.fetchone()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        if item is None:
            episode_object = {'ids': {'trakt': episode_id}, 'season': season, 'number': episode}
            self._update_episode(show_id, episode_object, False, watched, collected)
        else:
            if watched is not None:
                self.mark_episode_watched_by_id(episode_id)
            if collected is None:
                self.mark_episode_collected(show_id, season, episode)

    def get_nextup_episodes(self):
        cursor = self._get_cursor()
        db_query = (
            "SELECT e.show_id AS show_id, MIN(e.season) AS season, "
            "e.number AS number FROM episodes AS e INNER JOIN ("
            "SELECT e.show_id, e.season AS season, e.number AS number FROM episodes e LEFT JOIN ("
            "SELECT mw_se.show_id, MAX(mw_se.season) AS max_watched_season, "
            "mw_ep.number AS max_watched_episode_number FROM episodes AS mw_se INNER JOIN ("
            "SELECT show_id, season, MAX(number) AS number FROM episodes WHERE "
            "watched = 1 AND season > 0 GROUP BY show_id, season) AS "
            "mw_ep ON mw_se.show_id = mw_ep.show_id AND mw_se.season = mw_ep.season GROUP BY mw_se.show_id) AS "
            "mw ON e.show_id = mw.show_id WHERE (("
            "e.season = mw.max_watched_season AND e.number = mw.max_watched_episode_number) OR ("
            "e.season = mw.max_watched_season AND e.number > mw.max_watched_episode_number) OR ("
            "e.season > mw.max_watched_season AND e.number = 1)) AND watched = 0) AS nw ON ("
            "e.show_id == nw.show_id AND e.season == nw.season AND e.number >= nw.number) WHERE "
            "e.season > 0 AND watched = 0 AND e.show_id NOT IN (SELECT trakt_id AS show_id FROM hidden WHERE "
            "section IN ('progress_watched', 'shows')) AND Datetime(air_date) < Datetime('now') GROUP BY e.show_id")

        try:
            cursor.execute(db_query)
            result = cursor.fetchall()
            return result
        except:
            import traceback
            traceback.print_exc()
            pass
        finally:
            cursor.close()
