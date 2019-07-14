import threading
import ast
import copy

from datetime import datetime
from resources.lib.modules import trakt_sync
from resources.lib.indexers import trakt
from resources.lib.indexers import tvdb
from resources.lib.modules import database

class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):

    def mark_show_watched(self, show_id, watched):
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=? WHERE show_id=?', (watched, show_id,))
        cursor.connection.commit()
        cursor.close()
        from activities import TraktSyncDatabase as activities_database
        sync_thread = threading.Thread(target=activities_database()._sync_watched_episodes())
        sync_thread.run()

    def mark_season_watched(self, show_id, season, watched):
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=? WHERE show_id=? AND season=?', (watched, show_id, season))
        cursor.connection.commit()
        cursor.close()
        from activities import TraktSyncDatabase as activities_database
        sync_thread = threading.Thread(target=activities_database()._sync_watched_episodes())
        sync_thread.run()

    def mark_show_collected(self, show_id, collected):
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET collected=? WHERE show_id=?', (collected, show_id,))
        cursor.connection.commit()
        cursor.close()
        from activities import TraktSyncDatabase as activities_database
        sync_thread = threading.Thread(target=activities_database()._sync_collection_shows())
        sync_thread.run()

    def mark_season_collected(self, show_id, season, collected):
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET collected=? WHERE show_id=? AND season=?', (collected, show_id, season))
        cursor.connection.commit()
        cursor.close()
        from activities import TraktSyncDatabase as activities_database
        sync_thread = threading.Thread(target=activities_database()._sync_collection_shows())
        sync_thread.run()

    def mark_episode_watched(self, show_id, season, number):
        self._mark_episode_record('watched', 1, show_id, season, number)

    def mark_episode_watched_by_id(self, trakt_id):
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=1 WHERE trakt_id=?', (trakt_id,))
        cursor.connection.commit()
        cursor.close()

    def mark_episode_unwatched_by_id(self, trakt_id):
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET watched=0 WHERE trakt_id=?', (trakt_id,))
        cursor.connection.commit()
        cursor.close()

    def mark_episode_unwatched(self, show_id, season, number):
        self._mark_episode_record('watched', 0, show_id, season, number)

    def mark_episode_collected(self, show_id, season, number):
        self._mark_episode_record('collected', 1, show_id, season, number)

    def mark_episode_uncollected(self, show_id, season, number):
        self._mark_episode_record('collected', 0, show_id, season, number)

    def _mark_show_record(self, column, value, show_id):
        cursor = self._get_cursor()
        cursor.execute('UPDATE shows SET %s=? WHERE trakt_id=?' % column, (value, show_id))
        cursor.connection.commit()
        cursor.close()

    def _mark_episode_record(self, column, value, show_id, season, number):
        cursor = self._get_cursor()
        cursor.execute('UPDATE episodes SET %s=? WHERE show_id=? AND season=? AND number=?' % column, (value, show_id,
                                                                                                       season,
                                                                                                       number))
        cursor.connection.commit()
        cursor.close()

    def get_all_shows(self):
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM shows')
        shows = cursor.fetchall()
        cursor.close()
        shows = [i['trakt_id'] for i in shows]

        return shows

    def get_watched_shows(self):

        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM episodes WHERE watched = 1')
        watched_show_ids = list(set([episode['show_id'] for episode in cursor.fetchall()]))
        shows = []
        for i in watched_show_ids:
            show = cursor.execute('SELECT * FROM shows WHERE trakt_id=?', (i,)).fetchone()
            show['kodi_meta'] = ast.literal_eval(show['kodi_meta'])
            shows.append(show)

        return shows

    def get_watched_episodes(self):
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM episodes WHERE watched=1')
        episodes = cursor.fetchall()
        cursor.close()

        return episodes

    def get_collected_episodes(self):
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM episodes WHERE collected=1')
        episodes = cursor.fetchall()
        cursor.close()

        return episodes

    def get_season_list(self, show_id):
        self.threads = []
        show_meta = self.get_single_show(show_id)

        cursor = self._get_cursor()
        cursor.execute('SELECT* FROM seasons WHERE show_id = ?', (show_id,))
        seasons = cursor.fetchall()
        cursor.close()
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

        for season in range(int(show_meta['info']['season_count']) + 1):
            self.threads.append(threading.Thread(target=self.get_single_season, args=(show_meta['ids']['trakt'],
                                                                                      season, True)))

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
        self._start_queue_workers()

        for i in show_list:
            self.task_queue.put((self.get_single_show, (i, True, watch_info)), True)

        self._finish_queue_workers()

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

        show_list = list(set(show_list))

        self.item_list = []

        cursor = self._get_cursor()
        db_query = 'SELECT * FROM shows WHERE '
        for idx, i in enumerate(show_list):
            db_query += 'trakt_id = %s' % i
            if show_list[int(idx)] != show_list[-1]:
                db_query += ' OR '
        cursor.execute(db_query)
        show_db_list = cursor.fetchall()
        cursor.close()
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

        cursor = self._get_cursor()
        cursor.execute(db_query)
        show_db_list = cursor.fetchall()
        cursor.close()
        meta_list = [ast.literal_eval(i['kodi_meta']) for i in show_db_list if i['kodi_meta'] != '{}']
        meta_list = [self.get_show_watched_info(i) for i in meta_list]

        return meta_list

    def get_episode_list(self, episode_dicts):

        self.item_list = []

        cursor = self._get_cursor()
        db_query = 'SELECT * FROM episodes WHERE '
        for idx, i in enumerate(episode_dicts):
            db_query += '(show_id = %s AND season=%s AND number=%s)' % (i['show']['ids']['trakt'],
                                                                         i['episode']['season'],
                                                                         i['episode']['number'])
            if episode_dicts[int(idx)] != episode_dicts[-1]:
                db_query += ' OR '
        cursor.execute(db_query)
        episode_db_list = cursor.fetchall()
        cursor.close()
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

        cursor = self._get_cursor()
        cursor.execute(db_query)
        episode_db_list = cursor.fetchall()
        cursor.close()

        show_list = self.get_show_list([i['show_id'] for i in episode_db_list])

        return self.get_meta_episode_list(episode_db_list, show_list)

    def update_episode_list(self, episode_dicts):
        self.item_list = []
        self._start_queue_workers()
        for item in episode_dicts:
            self.task_queue.put((self.get_single_episode, (item['show']['ids']['trakt'], item['episode']['season'],
                                                           item['episode']['number'], True)), True)

        self._finish_queue_workers()

        return self.item_list

    def get_meta_episode_list(self, episode_list, show_list):
        meta_list = []

        for episode in episode_list:
            try:
                episode['kodi_meta'] = ast.literal_eval(episode['kodi_meta'])
                if 'info' not in episode['kodi_meta']: continue
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

        try:

            cursor = self._get_cursor()
            cursor.execute('SELECT * FROM shows WHERE trakt_id=?', (show_id,))
            show_object = cursor.fetchone()
            cursor.execute('SELECT * FROM seasons WHERE show_id=? AND season=?', (show_id, season))
            season_object = cursor.fetchone()
            cursor.execute('SELECT * FROM episodes WHERE show_id=? AND season=?', (show_id, season))
            season_episodes = cursor.fetchall()
            cursor.close()

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

            trakt_list = database.get(trakt.TraktAPI().json_response, 24, 'shows/%s/seasons/%s' % (show_id, season))

            self._start_queue_workers()

            for i in trakt_list:
                self.task_queue.put((self.get_single_episode, (show_id, season, i['number'], True)), True)

            self._finish_queue_workers()

            return self.item_list

    def _get_show_episodes(self, show_id, meta=False):
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM episodes WHERE show_id=?', (show_id,))
        episodes = cursor.fetchall()
        cursor.close()
        if meta:
            episodes = [episode['kodi_meta'] for episode in episodes]
        return episodes

    def get_single_show(self, show_id, list_mode=False, watch_info=True, get_meta=True):

        # Get show from Database if it exsits, else create new record
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM shows WHERE trakt_id=?', (int(show_id),))
        item = cursor.fetchone()
        cursor.close()

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
            show_meta['info']['UnWatchedEpisodes'] = int(show_meta['info']['episode_count']) - play_count
            if play_count < aired_episodes:
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

        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM seasons WHERE show_id=? AND season=?', (show_id, season))
        item = cursor.fetchone()
        cursor.close()

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
                cursor = self._get_cursor()
                cursor.execute('SELECT * FROM episodes WHERE watched=1 AND season=? AND show_id=?',
                               (season_no, show_id))
                episodes = cursor.fetchall()
                cursor.close()

                # \
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

        cursor = self._get_cursor()

        cursor.execute('SELECT * FROM episodes WHERE show_id=? AND season=? AND number=?',
                       (show_id, season, episode))
        item = cursor.fetchone()
        cursor.close()

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
        item['showInfo']['info'].pop('castandrole', '')
        item['showInfo'].pop('setCast', '')
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
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM shows WHERE trakt_id=?', (trakt_id,))
        old_entry = cursor.fetchone()
        cursor.close()

        if get_meta:
            kodi_meta = tvdb.TVDBAPI().seriesIDToListItem(show_item)
            if kodi_meta is None:
                return
            update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        else:
            if old_entry is None:
                kodi_meta = {}
                update_time = self.base_date
            else:
                update_time = old_entry['last_updated']
                kodi_meta = old_entry['kodi_meta']

        cursor = self._get_cursor()
        try:
            cursor.execute('PRAGMA foreign_keys=OFF')
            cursor.execute(
                "INSERT OR REPLACE INTO shows ("
                "trakt_id, kodi_meta, last_updated)"
                "VALUES "
                "(?, ?, ?)",
                (int(trakt_id), str(kodi_meta), update_time))
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.connection.commit()
            cursor.close()

            return {'trakt_id': trakt_id, 'kodi_meta': kodi_meta, 'last_updated': update_time}
        except:
            cursor.close()

            import traceback
            traceback.print_exc()
            pass

    def _update_season(self, show_meta, season_meta, get_meta=True):

        if get_meta:
            kodi_meta = tvdb.TVDBAPI().seasonIDToListItem(season_meta, show_meta)
        else:
            kodi_meta = {}

        season = season_meta['number']
        show_id = show_meta['ids']['trakt']
        cursor = self._get_cursor()

        try:
            update = cursor.execute(
                    "UPDATE seasons SET kodi_meta=? WHERE show_id=? AND season = ?",
                    (str(kodi_meta), show_id, season))

            if update.rowcount is 0:
                cursor.execute(
                    "INSERT INTO seasons ("
                    "show_id, season, kodi_meta)"
                    "VALUES "
                    "(?, ?, ?)",
                    (show_id, season, str(kodi_meta)))
            cursor.connection.commit()
            cursor.close()
            return {'show_id': show_meta['ids']['trakt'], 'season': season, 'kodi_meta': kodi_meta}

        except:
            cursor.close()
            import traceback
            traceback.print_exc()
            pass

    def _update_episode(self, show_id, episode_object, get_meta=True, watched=None, collected=None):

        show_meta = self.get_single_show(show_id, get_meta=get_meta)
        if show_meta is None:
            return

        episode_id = episode_object['ids']['trakt']
        season = episode_object['season']
        old_entry = None
        number = episode_object['number']
        cursor = self._get_cursor()

        try:
            cursor.execute("SELECT * FROM episodes WHERE trakt_id=?", (episode_id,))
            old_entry = cursor.fetchone()
            cursor.close()
        except:
            pass

        if show_meta == '{}' and get_meta:
            return

        show_meta = {'showInfo': show_meta}

        if (get_meta and old_entry is None) or (get_meta and old_entry['kodi_meta'] == '{}'):
            kodi_meta = tvdb.TVDBAPI().episodeIDToListItem(episode_object, copy.deepcopy(show_meta))
            if kodi_meta is None:
                return
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
            old_entry = {'collected': 0, 'watched': 0}

        if collected is None:
            collected = old_entry['collected']

        if watched is None:
            watched = old_entry['watched']

        cursor = self._get_cursor()

        try:
            cursor.execute(
                "INSERT OR REPLACE INTO episodes ("
                "show_id, season, trakt_id, kodi_meta, last_updated, watched, collected, number)"
                "VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)",
                (show_id, season, episode_id, str(kodi_meta), update_time, watched, collected, number))

            cursor.connection.commit()
            cursor.close()

            return {'show_id': show_id, 'season': season, 'episode_id': episode_id, 'kodi_meta': kodi_meta,
                    'update_time': update_time, 'watched': watched, 'collected': collected, 'number': number}
        except:
            cursor.close()

            import traceback
            traceback.print_exc()
            pass

    def _sync_insert_episode(self, show_id, episode_id, season, episode, watched=None, collected=None):

        cursor = self._get_cursor()

        cursor.execute('SELECT * FROM episodes WHERE show_id=? AND season=? AND number=?',
                       (show_id, season, episode))
        item = cursor.fetchone()
        cursor.close()

        if item is None:
            episode_object = {'ids': {'trakt': episode_id}, 'season': season, 'number': episode}
            self._update_episode(show_id, episode_object, False, watched, collected)
        else:
            if watched is not None:
                self.mark_episode_watched_by_id(episode_id)
            if collected is None:
                self.mark_episode_collected(show_id, season, episode)

