from datetime import datetime, timedelta

from resources.lib.common import tools
from resources.lib.indexers import trakt as Trakt
from resources.lib.modules import database
from resources.lib.modules import trakt_sync
from resources.lib.modules.trakt_sync import hidden
from resources.lib.modules.trakt_sync import movies
from resources.lib.modules.trakt_sync import shows
from resources.lib.modules.trakt_sync import lists

class TraktSyncDatabase(trakt_sync.TraktSyncDatabase, object):
    progress_dialog = None
    silent = True
    results_mill = {}

    def sync_activities(self, silent=False):
        sync_errors = False

        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))

        tools.log('STARTING SYNC')

        self._refresh_activites()

        if not silent and \
                str(self.activites['all_activities']) == self.base_date and \
                tools.getSetting('trakt.auth') != '':
            tools.showDialog.notification(tools.addonName, tools.lang(40133))

            # Give the people time to read the damn notification
            tools.kodi.sleep(500)
        try:

            if str(self.activites['all_activities']) == self.base_date:
                self.silent = False

            if not self.silent:
                self.progress_dialog = tools.bgProgressDialog()
                self.progress_dialog.create(tools.addonName + 'Sync', 'Seren: Trakt Sync')

            ############################################################################################################
            # CHECK FOR META REFRESH
            ############################################################################################################

            # Meta removal should only run every 12 hours, otherwise we repeatedly dump information every run

            try:
                if self.activites['shows_meta_update'] == self.base_date:
                    self._update_activity_record('shows_meta_update', update_time)
                else:
                    local_date = trakt_sync._parse_local_date_format(self.activites['shows_meta_update'])
                    local_date = local_date + timedelta(hours=2)
                    now = trakt_sync._utc_now_as_trakt_string()
                    local_date = trakt_sync._strf_local_date(local_date)
                    if trakt_sync._requires_update(now, local_date):
                        success = self._remove_old_meta_items('shows')
                        if success:
                            self._update_activity_record('shows_meta_update', update_time)
            except:
                sync_errors = True
                import traceback
                traceback.print_exc()
                pass

            try:
                if self.activites['movies_meta_update'] == self.base_date:
                    self._update_activity_record('movies_meta_update', update_time)
                else:
                    local_date = trakt_sync._parse_local_date_format(self.activites['movies_meta_update'])
                    local_date = local_date + timedelta(hours=2)
                    now = trakt_sync._utc_now_as_trakt_string()
                    local_date = trakt_sync._strf_local_date(local_date)
                    if trakt_sync._requires_update(now, local_date):
                        success = self._remove_old_meta_items('movies')
                        if success:
                            self._update_activity_record('movies_meta_update', update_time)
            except:
                sync_errors = True
                import traceback
                traceback.print_exc()
                pass

            if tools.getSetting('trakt.auth') == '':
                if self.progress_dialog is not None:
                    self.progress_dialog.close()
                    self.progress_dialog = None
                self._update_activity_record('all_activities', update_time)
                return

            ########################################################################################################
            # SYNC LISTS
            ########################################################################################################

            lists_to_update = []

            try:
                lists_db = lists.TraktSyncDatabase()
                trakt_api = Trakt.TraktAPI()
                my_lists = trakt_api.json_response('users/me/lists', limit=True, limitOverride=500)
                my_lists.extend([i['list'] for i in trakt_api.json_response('users/likes/lists', limit=True,
                                                                         limitOverride=500)])
                for item in my_lists:
                    sync_dates = [lists_db.get_list(item['ids']['trakt'], 'movie', item['user']['ids']['slug']),
                                  lists_db.get_list(item['ids']['trakt'], 'show', item['user']['ids']['slug'])]
                    sync_dates = [i for i in sync_dates if i]
                    sync_dates = [i['updated_at'][:19] for i in sync_dates]
                    if len(sync_dates) == 0:
                        lists_to_update.append(item)
                        continue
                    for date in sync_dates:
                        if trakt_sync._requires_update(item['updated_at'], date):
                            lists_to_update.append(item)
                            break

                self._sync_lists(lists_to_update)
            except:
                sync_errors = True
                import traceback
                traceback.print_exc()
                pass

            trakt_activities = Trakt.TraktAPI().json_response('sync/last_activities')

            if trakt_activities is None:
                tools.log('Unable to connect to Trakt', 'error')
                if self.progress_dialog is not None:
                    self.progress_dialog.close()
                    self.progress_dialog = None
                return True

            if trakt_sync._requires_update(trakt_activities['all'], self.activites['all_activities']):

                ########################################################################################################
                # SYNC HIDDEN ITEMS
                ########################################################################################################
                try:
                    if not self.silent:
                        self.progress_dialog.update(0, 'Syncing Hidden Items')
                    if trakt_sync._requires_update(trakt_activities['movies']['hidden_at'],
                                                   self.activites['hidden_sync']) and \
                            trakt_sync._requires_update(trakt_activities['shows']['hidden_at'],
                                                        self.activites['hidden_sync']):
                        self._sync_hidden()

                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass
                ########################################################################################################
                # SYNC WATCHED ITEMS
                ########################################################################################################
                sync_triggered = False

                try:
                    if trakt_sync._requires_update(trakt_activities['episodes']['watched_at'],
                                                   self.activites['shows_watched']):
                        sync_triggered = True
                        self._sync_watched_episodes()
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass
                try:
                    if trakt_sync._requires_update(trakt_activities['movies']['watched_at'],
                                                   self.activites['movies_watched']):
                        sync_triggered = True
                        self._sync_watched_movies()
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass
                try:
                    if sync_triggered:
                        if not self.silent:
                            self.progress_dialog.update(0, 'Syncing Unwatched items')
                        self._sync_unwatched()
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass

                ########################################################################################################
                # SYNC COLLECTION
                ########################################################################################################

                sync_triggered = False

                try:
                    if trakt_sync._requires_update(trakt_activities['episodes']['collected_at'],
                                                   self.activites['shows_collected']):
                        self._sync_collection_shows()
                        sync_triggered = True
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass

                try:
                    if trakt_sync._requires_update(trakt_activities['movies']['collected_at'],
                                                   self.activites['movies_collected']):
                        self._sync_collection_movies()
                        sync_triggered = True
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass

                try:
                    if sync_triggered:
                        if not self.silent:
                            self.progress_dialog.update(0, 'Syncing Uncollected items')
                        self._sync_uncollected()
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass

                ########################################################################################################
                # SYNC BOOKMARK
                ########################################################################################################

                sync_triggered = False

                try:
                    if trakt_sync._requires_update(trakt_activities['episodes']['paused_at'],
                                                   self.activites['episodes_bookmarked']):
                        cursor = self._get_cursor()
                        cursor.execute('DELETE FROM bookmark WHERE 1=1')
                        cursor.connection.commit()
                        cursor.close()
                        self._sync_bookmarks('episodes')
                        sync_triggered = True
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass

                try:
                    if trakt_sync._requires_update(trakt_activities['movies']['paused_at'],
                                                   self.activites['movies_bookmarked']):
                        self._sync_bookmarks('movies')
                        sync_triggered = True
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass

                try:
                    if sync_triggered:
                        if not self.silent:
                            self.progress_dialog.update(100, 'Syncing bookmarked items')
                except:
                    sync_errors = True
                    import traceback
                    traceback.print_exc()
                    pass

                self._update_activity_record('all_activities', update_time)

            if self.progress_dialog is not None:
                self.progress_dialog.close()
                self.progress_dialog = None
        except:
            try:
                if self.progress_dialog is not None:
                    self.progress_dialog.close()
                    self.progress_dialog = None
            except:
                pass
            import traceback
            traceback.print_exc()
            pass

        return sync_errors

    def get_bookmark(self, trakt_id):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        try:
            cursor.execute("SELECT * FROM bookmark WHERE trakt_id = '%s'" % trakt_id)
            return cursor.fetchone()
        except:
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            tools.try_release_lock(tools.traktSyncDB_lock)


    def set_bookmark(self, trakt_id, time_in_seconds):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        try:
            cursor.execute("REPLACE INTO bookmark Values (?, ?)", (trakt_id, time_in_seconds))
            cursor.connection.commit()
        except:
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            tools.try_release_lock(tools.traktSyncDB_lock)

    def remove_bookmark(self, trakt_id):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        try:
            cursor.execute("DELETE FROM bookmark WHERE trakt_id = '%s'" % trakt_id)
            cursor.connection.commit()
        except:
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            tools.try_release_lock(tools.traktSyncDB_lock)


    def _sync_hidden(self):
        progress_perc = 0
        trakt_api = Trakt.TraktAPI()
        sections = ['calendar', 'progress_watched', 'progress_watched_reset', 'progress_collected',
                    'recommendations']
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))

        for section in sections:
            progress_perc += 20
            if not self.silent:
                self.progress_dialog.update(progress_perc,
                                            'Syncing %s Hidden Items' % section.title().replace('_', ' '))
            to_remove = hidden.TraktSyncDatabase().get_hidden_items(section)
            to_remove = set(i['trakt_id'] for i in to_remove)
            page = 1
            total_pages = 1000
            while page < (total_pages + 1):
                hidden_items = trakt_api.json_response('users/hidden/%s?page=%s' % (section, page))
                if hidden_items is None:
                    return
                page = int(trakt_api.response_headers['X-Pagination-Page']) + 1
                total_pages = int(trakt_api.response_headers['X-Pagination-Page-Count'])

                for item in hidden_items:
                    if 'show' in item:
                        item_id = item['show']['ids']['trakt']
                        item_type = 'show'
                    elif 'movie' in item:
                        item_type = 'movie'
                        item_id = item['movie']['ids']['trakt']
                    else:
                        continue
                    if item_id in to_remove:
                        to_remove.remove(item_id)
                    else:
                        hidden.TraktSyncDatabase().add_hidden_item(item_id, item_type, section)

            if not self.silent:
                self.progress_dialog.update(100, 'Syncing Unhidden items')
            for item in to_remove:
                try:
                    hidden.TraktSyncDatabase().remove_item(section, item)
                except:
                    import traceback
                    traceback.print_exc()
                    pass

        self._update_activity_record('hidden_sync', update_time)

    def _sync_watched_movies(self):
        self.threads = []

        if tools.getSetting('trakt.auth') == '':
            return

        insert_list = []

        if not self.silent:
            self.progress_dialog.update(-1, 'Fetching Watched Movies')
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        trakt_watched = Trakt.TraktAPI().json_response('/sync/watched/movies?extended=full')

        local_watched = movies.TraktSyncDatabase().get_watched_movies()
        local_watched = {i['trakt_id']: i for i in local_watched}

        for movie in trakt_watched:
            if movie['movie']['ids']['trakt'] not in local_watched:
                insert_list.append(movie)

        movie_tasks = len(insert_list)

        if movie_tasks == 0:
            self._update_activity_record('movies_watched', update_time)
            return

        if not self.silent:
            self.progress_dialog.update(0, 'Inserting Watched Movies')

        sql_statement = "INSERT OR IGNORE INTO movies (trakt_id, kodi_meta, collected, watched, last_updated, air_date)" \
                        "VALUES " \
                        "(?, '{}', ?, ?, ?, ?)"

        self._execute_batch_sql(sql_statement, ((i['movie']['ids']['trakt'], 0, 1,
                                                 self.base_date, i['movie'].get('released')) for i in insert_list),
                                movie_tasks)

        self._update_activity_record('movies_watched', update_time)

    def _sync_watched_episodes(self):
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        if not self.silent:
            self.progress_dialog.update(-1, 'Fetching Watched Episodes')
        trakt_watched = Trakt.TraktAPI().json_response('/sync/watched/shows?extended=full')
        trakt_watched = [(show['show']['ids']['trakt'], season['number'], episode['number'])
                         for show in trakt_watched for season in show['seasons'] for episode in season['episodes']]

        local_watched = shows.TraktSyncDatabase().get_watched_episodes()
        local_watched = [(i['show_id'], i['season'], i['number']) for i in local_watched]

        filtered = [i for i in trakt_watched if i not in local_watched]
        self._mill_episodes(filtered, True)

        self._update_activity_record('shows_watched', update_time)

    def _sync_unwatched(self):
        show_sync = shows.TraktSyncDatabase()
        movie_sync = movies.TraktSyncDatabase()
        trakt_watched_movies = Trakt.TraktAPI().json_response('sync/watched/movies')
        trakt_watched_movies = set(int(i['movie']['ids']['trakt']) for i in trakt_watched_movies)
        local_watched_movies = movie_sync.get_watched_movies()
        local_watched_movies = set(int(i['trakt_id']) for i in local_watched_movies)

        trakt_watched_episodes = Trakt.TraktAPI().json_response('sync/watched/shows')
        trakt_watched_episodes = set('%s-%s-%s' % (show['show']['ids']['trakt'], season['number'], episode['number'])
                                     for show in trakt_watched_episodes for season in show['seasons'] for episode
                                     in season['episodes'])
        local_watched_episodes = show_sync.get_watched_episodes()
        local_watched_episodes = set('%s-%s-%s' % (i['show_id'], i['season'], i['number']) for i in
                                     local_watched_episodes)

        workload = local_watched_movies - trakt_watched_movies
        sql_statement = "UPDATE movies SET watched=0 WHERE trakt_id=?"
        self._execute_batch_sql(sql_statement, ((movie,) for movie in workload),
                                len(workload))

        workload = local_watched_episodes - trakt_watched_episodes
        sql_statement = "UPDATE episodes SET watched=0 WHERE show_id=? AND season=? AND number=?"
        self._execute_batch_sql(sql_statement, ((tuple(episode.split('-'))) for episode in workload),
                                len(workload))

        if not self.silent:
            self.progress_dialog.update(100, 'Syncing Unwatched items')

    def _sync_collection_movies(self):
        movie_sync = movies.TraktSyncDatabase()

        insert_list = []
        if not self.silent:
            self.progress_dialog.update(0, 'Fetching Collected Movies')
        local_collection = set(i['trakt_id'] for i in movie_sync.get_collected_movies())

        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        trakt_collecton = Trakt.TraktAPI().json_response('sync/collection/movies?extended=full')

        for item in trakt_collecton:
            if item['movie']['ids']['trakt'] not in local_collection:
                insert_list.append(item)

        if not self.silent:
            self.progress_dialog.update(0, 'Inserting Collected Movies')

        sql_statement = "INSERT OR IGNORE INTO movies (trakt_id, kodi_meta, collected, watched, last_updated, " \
                        "air_date) VALUES (?, '{}', ?, ?, ?, ?) "
        self._execute_batch_sql(sql_statement, ((i['movie']['ids']['trakt'], 1, 0,
                                                 self.base_date, i['movie'].get('released')) for i in insert_list),
                                len(insert_list))

        sql_statement = "UPDATE movies SET collected=1 WHERE trakt_id=?"

        self._execute_batch_sql(sql_statement, [(i['movie']['ids']['trakt'],) for i in trakt_collecton],
                                len(trakt_collecton))

        self._update_activity_record('movies_collected', update_time)

    def _sync_collection_shows(self):
        show_sync = shows.TraktSyncDatabase()
        local_collection = [(i['show_id'], i['season'], i['number'])
                            for i in show_sync.get_collected_episodes()]

        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        if not self.silent:
            self.progress_dialog.update(0, 'Fetching Collected Episodes')
        trakt_collection = Trakt.TraktAPI().json_response('sync/collection/shows?extended=full')
        trakt_collection = [(show['show']['ids']['trakt'], season['number'], episode['number'])
                            for show in trakt_collection for season in show['seasons'] for episode
                            in season['episodes']]
        
        filtered = [i for i in trakt_collection if i not in local_collection]

        self._mill_episodes(filtered, False)
        self._update_activity_record('shows_collected', update_time)

    def _sync_uncollected(self):
        show_sync = shows.TraktSyncDatabase()
        movie_sync = movies.TraktSyncDatabase()
        trakt_collected_movies = Trakt.TraktAPI().json_response('sync/collection/movies')

        if trakt_collected_movies is not None:
            trakt_collected_movies = set(int(i['movie']['ids']['trakt']) for i in trakt_collected_movies)
        else:
            trakt_collected_movies = set()

        local_collected_movies = movie_sync.get_collected_movies()
        local_collected_movies = set(int(i['trakt_id']) for i in local_collected_movies)
        trakt_collected_episodes = Trakt.TraktAPI().json_response('sync/collection/shows')

        if trakt_collected_episodes is not None:
            trakt_collected_episodes = set(
                '%s-%s-%s' % (show['show']['ids']['trakt'], season['number'], episode['number'])
                for show in trakt_collected_episodes for season in show['seasons'] for episode
                in season['episodes'])
        else:
            trakt_collected_episodes = set()

        local_collected_episodes = show_sync.get_collected_episodes()
        local_collected_episodes = set('%s-%s-%s' % (i['show_id'], i['season'], i['number'])
                                       for i in local_collected_episodes)

        workload = local_collected_movies - trakt_collected_movies
        sql_statement = "UPDATE movies SET collected=0 WHERE trakt_id=?"
        self._execute_batch_sql(sql_statement, ((movie,) for movie in workload),
                                len(workload))

        workload = local_collected_episodes - trakt_collected_episodes
        sql_statement = "UPDATE episodes SET collected=0 WHERE show_id=? AND season=? AND number=?"
        self._execute_batch_sql(sql_statement, ((tuple(episode.split('-'))) for episode in workload),
                                len(workload))

        if not self.silent:
            self.progress_dialog.update(100, 'Syncing Uncollected items')

    def _sync_lists(self, lists_to_sync):
        trakt_api = Trakt.TraktAPI()
        media_types = ['movie', 'show']
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))

        total_lists = len(lists_to_sync) * len(media_types)

        processed_lists = 0
        list_sync = lists.TraktSyncDatabase()

        for media_type in media_types:
            for trakt_list in lists_to_sync:
                if not self.silent:
                    processed_lists += 1
                    self.progress_dialog.update(int(float(processed_lists) / float(total_lists) * 100), 'Syncing lists')

                url = 'users/%s/lists/%s/items/%s?extended=full' % (trakt_list['user']['ids']['slug'],
                                                                    trakt_list['ids']['trakt'], media_type)
                list_items = trakt_api.json_response(url, limit=False)

                if list_items is None or len(list_items) == 0:
                    list_sync.remove_list(trakt_list['ids']['trakt'], media_type)
                    continue

                list_items = trakt_api.sort_list(trakt_list['sort_by'], trakt_list['sort_how'], list_items, media_type)
                list_items = [i[media_type] for i in list_items if i['type'] == media_type and i is not None]
                list_sync.add_list(trakt_list['ids']['trakt'], list_items, trakt_list['name'],
                                   tools.quote_plus(trakt_list['user']['ids']['slug']), 'myLists',
                                   media_type, trakt_list['updated_at'], len(list_items), trakt_list['sort_by'],
                                   trakt_list['sort_how'], trakt_list['ids']['slug'])

        if not self.silent:
            self.progress_dialog.update(100, 'Syncing lists')

        self._update_activity_record('lists_sync', update_time)

    def _remove_old_meta_items(self, type):
        last_update = self.activites['%s_meta_update' % type]
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        success = True

        trakt_api = Trakt.TraktAPI()
        updated_item = []
        url = '%s/updates/%s?page=%s'

        if not self.silent:
            self.progress_dialog.update(0, 'Clearing Outdated %s Metadata' % type[:-1].title())

        updates = trakt_api.json_response(url % (type, last_update[:10], 1), limitOverride=500, limit=True)

        for item in updates:
            if not trakt_sync._requires_update(item['updated_at'], last_update):
                continue
            item_id = item[type[:-1]]['ids']['trakt']
            updated_item.append(item_id)

        for i in range(2, int(trakt_api.response_headers['X-Pagination-Page-Count']) + 1):
            progress = (i / (int(trakt_api.response_headers['X-Pagination-Page-Count']) + 1)) * 100
            if not self.silent:
                self.progress_dialog.update(progress)
            updates = trakt_api.json_response(url % (type, last_update[:10], i), limitOverride=500, limit=True)
            for item in updates:
                if not trakt_sync._requires_update(item['updated_at'], last_update):
                    continue
                item_id = item[type[:-1]]['ids']['trakt']
                updated_item.append(item_id)

        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()

        try:
            updated_item = sorted(list(set(updated_item)))

            sql_statements = 0

            if type == 'shows':
                for i in updated_item:
                    cursor.execute('UPDATE shows SET kodi_meta=?, last_updated=? WHERE trakt_id=?',
                                   ('{}', update_time, i))
                    cursor.execute('UPDATE episodes SET kodi_meta=?, last_updated=? WHERE show_id=?',
                                   ('{}', update_time, i))
                    cursor.execute('UPDATE seasons SET kodi_meta=? WHERE show_id=?', ('{}', i))

                    sql_statements += 3

                    # Batch the entries as to not reach SQL expression limit
                    if sql_statements > 500:
                        cursor.connection.commit()
                        sql_statements = 0

            elif type == 'movies':
                for i in updated_item:
                    cursor.execute('UPDATE movies SET kodi_meta=?, last_updated=? WHERE trakt_id=?',
                                   (str({}), update_time, i))
                    # Batch the entries as to not reach SQL expression limit
                    sql_statements += 1
                    if sql_statements > 999:
                        cursor.connection.commit()
                        sql_statements = 0

        except database.OperationalError:
            tools.log('Failed to update some meta items')
            success = False
        finally:
            cursor.connection.commit()
            cursor.close()

        tools.try_release_lock(tools.traktSyncDB_lock)
        return success

    def _mill_episodes(self, trakt_collection, watched):

        episode_insert_list = []
        season_insert_list = []

        sync_type = 'Watched' if watched else 'Collected'

        show_ids = set(i[0] for i in trakt_collection)

        inserted_tasks = 0

        for show_id in show_ids:
            self.task_queue.put(self._pull_show_episodes, show_id)
            inserted_tasks += 1
            progress_perc = (float(inserted_tasks) / float(len(show_ids))) * 100
            if not self.silent:
                self.progress_dialog.update(int(progress_perc))

        self.task_queue.wait_completion()

        for show_id in show_ids:
            try:
                for season in self.results_mill.get(str(show_id), []):
                    season_insert_list.append((show_id, season['number'], season['first_aired']))
                    if 'episodes' in season:
                        for episode in season['episodes']:
                            episode_insert_list.append((show_id, episode['season'], episode['ids']['trakt'],
                                                        episode['number'], episode['first_aired']))
            except KeyError:
                pass
            except TypeError:
                pass

        if not self.silent:
            self.progress_dialog.update(0, 'Inserting %s Shows' % sync_type)

        sql_statement = "INSERT OR IGNORE INTO shows (trakt_id, kodi_meta, last_updated, air_date) " \
                        "VALUES (?, '{}', ?, ?)"
        self._execute_batch_sql(sql_statement, ((i, self.base_date, None) for i in show_ids), len(show_ids))

        if not self.silent:
            self.progress_dialog.update(0, 'Inserting %s Seasons' % sync_type)

        sql_statement = "INSERT OR IGNORE INTO seasons " \
                        "(show_id, season, kodi_meta, air_date) VALUES (?, ?, '{}', ?)"

        self._execute_batch_sql(sql_statement, ((int(i[0]), int(i[1]), i[2]) for i in season_insert_list),
                                len(season_insert_list))

        if not self.silent:
            self.progress_dialog.update(0, 'Inserting %s Episodes' % sync_type)

        sql_statement = "INSERT OR IGNORE INTO episodes " \
                        "(show_id, season, trakt_id, kodi_meta, last_updated, watched, collected, number, " \
                        "air_date) VALUES (?, ?, ?, '{}', ?, ?, ?, ?, ?)"

        self._execute_batch_sql(sql_statement, ((i[0], int(i[1]), int(i[2]), self.base_date, 0,
                                                 0, i[3], i[4]) for i in episode_insert_list),
                                len(episode_insert_list))

        to_be_marked = [i[2] for i in episode_insert_list if (i[0], i[1], i[3]) in trakt_collection]

        if watched:
            query = "UPDATE episodes SET watched=1 WHERE trakt_id=?"
        else:
            query = "UPDATE episodes SET collected=1 WHERE trakt_id=?"

        self._execute_batch_sql(query, ((i,) for i in to_be_marked), len(episode_insert_list))

        return episode_insert_list

    def _update_activity_record(self, record, time):
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        try:
            cursor.execute('UPDATE activities SET %s=? WHERE sync_id=1' % record, (time,))
            cursor.connection.commit()
        except database.OperationalError:
            tools.log('Failed to update activity record: {}'.format(record))
        finally:
            cursor.close()

        tools.try_release_lock(tools.traktSyncDB_lock)

    def _pull_show_episodes(self, show_id):
        self.results_mill.update({str(show_id): database.get(Trakt.TraktAPI().json_response, 24,
                                                             '/shows/{}/seasons?extended=episodes%2Cfull'.format(
                                                                 show_id))})

    def _sync_bookmarks(self, type):
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        if not self.silent:
            self.progress_dialog.update(-1, 'Fetching {} bookmark status'.format(type))

        trakt_api = Trakt.TraktAPI()
        progress = trakt_api.json_response('sync/playback/{}/?extended=full&limit=300'.format(type))

        base_sql_statement = "REPLACE INTO bookmark Values (%s, %s)"
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        sql_statements = 0

        for i in progress:
            if i['progress'] == 0 or i['progress'] == 100:
                continue
            if i[i['type']]['runtime'] is None:
                continue
            if 'episode' in i:
                offset = int((float(i['progress'] / 100) * int(i['episode']['runtime']) * 60))
                cursor.execute(base_sql_statement % (i['episode']['ids']['trakt'], offset))
            if 'movie' in i:
                offset = int((float(i['progress'] / 100) * int(i['movie']['runtime']) * 60))
                cursor.execute(base_sql_statement % (i['movie']['ids']['trakt'], offset))

            # Batch the entries as to not reach SQL expression limit
            sql_statements += 1
            if sql_statements > 999:
                cursor.connection.commit()
                sql_statements = 0

        cursor.connection.commit()
        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
        self._update_activity_record('{}_bookmarked'.format(type), update_time)

    def _execute_batch_sql(self, query, items, max_items):
        inserted_tasks = 0
        tools.traktSyncDB_lock.acquire()
        cursor = self._get_cursor()
        sql_statements = 0

        for item in items:
            inserted_tasks += 1
            progress_perc = (float(inserted_tasks) / float(max_items)) * 100
            if not self.silent:
                self.progress_dialog.update(int(progress_perc))
            cursor.execute(query, item)
            # Batch the entries as to not reach SQL expression limit
            sql_statements += 1
            if sql_statements > 999:
                cursor.connection.commit()
                sql_statements = 0

        if sql_statements > 0:
            cursor.connection.commit()

        cursor.close()
        tools.try_release_lock(tools.traktSyncDB_lock)
