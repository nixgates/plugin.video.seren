from datetime import datetime, timedelta
from resources.lib.modules import trakt_sync
from resources.lib.modules.trakt_sync import shows
from resources.lib.modules.trakt_sync import movies
from resources.lib.modules.trakt_sync import hidden
from resources.lib.common import tools
from resources.lib.indexers import trakt as Trakt
from resources.lib.modules import database

show_sync = shows.TraktSyncDatabase()
movie_sync = movies.TraktSyncDatabase()


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):

    progress_dialog = None
    silent = True
    results_mill = {}

    def run_activities_service(self):
        try:
            import xbmc
            monitor = xbmc.Monitor()
        except:
            pass
        self.sync_activities()
        while not monitor.abortRequested():
            try:
                if monitor.waitForAbort(60 * 30):
                    break

            except:
                import traceback
                traceback.print_exc()
                pass

    def sync_activities(self):

        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))

        if str(self.activites['all_activities']) == self.base_date and tools.getSetting('trakt.auth') != '':
            # Increase the amount of concurrent tasks running during initial and Force Sync processes to speed up task
            tools.showDialog.textviewer(tools.addonName, tools.lang(40133))
            confirmation = tools.showDialog.yesno(tools.addonName, tools.lang(40134))

            if not confirmation:
                return

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
                        self._remove_old_meta_items('shows')
                        self._update_activity_record('shows_meta_update', update_time)
            except:
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
                        self._remove_old_meta_items('movies')
                        self._update_activity_record('movies_meta_update', update_time)
            except:
                import traceback
                traceback.print_exc()
                pass

            if tools.getSetting('trakt.auth') == '':
                if self.progress_dialog is not None:
                    self.progress_dialog.close()
                    self.progress_dialog = None
                self._update_activity_record('all_activities', update_time)
                return

            trakt_activities = Trakt.TraktAPI().json_response('sync/last_activities')

            if trakt_activities is None:
                tools.log('Unable to connect to Trakt', 'error')
                if self.progress_dialog is not None:
                    self.progress_dialog.close()
                    self.progress_dialog = None
                return

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
                    import traceback
                    traceback.print_exc()
                    pass
                try:
                    if trakt_sync._requires_update(trakt_activities['movies']['watched_at'],
                                                   self.activites['movies_watched']):
                        sync_triggered = True
                        self._sync_watched_movies()
                except:
                    import traceback
                    traceback.print_exc()
                    pass
                try:
                    if sync_triggered:
                        if not self.silent:
                            self.progress_dialog.update(100, 'Syncing Unwatched items')
                        self._sync_unwatched()
                except:
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
                    import traceback
                    traceback.print_exc()
                    pass

                try:
                    if trakt_sync._requires_update(trakt_activities['movies']['collected_at'],
                                                   self.activites['movies_collected']):
                        self._sync_collection_movies()
                        sync_triggered = True
                except:
                    import traceback
                    traceback.print_exc()
                    pass

                try:
                    if sync_triggered:
                        if not self.silent:
                            self.progress_dialog.update(100, 'Syncing Uncollected items')
                        self._sync_uncollected()
                except:
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


    def _sync_hidden(self):
        progress_perc = 0
        trakt_api = Trakt.TraktAPI()
        sections = ['calendar', 'progress_watched', 'progress_watched_reset', 'progress_collected',
                    'recommendations']
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))

        for section in sections:
            progress_perc += 20
            if not self.silent:
                self.progress_dialog.update(progress_perc, 'Syncing %s Hidden Items' % section.title().replace('_', ' '))
            to_remove = hidden.TraktSyncDatabase().get_hidden_items(section)
            to_remove = [i['trakt_id'] for i in to_remove]
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
        trakt_watched = Trakt.TraktAPI().json_response('/sync/watched/movies')

        trakt_watched = [i['movie']['ids']['trakt'] for i in trakt_watched]

        local_watched = movies.TraktSyncDatabase().get_watched_movies()
        local_watched = [i['trakt_id'] for i in local_watched]

        for movie in trakt_watched:
            if movie not in local_watched:
                insert_list.append((movie, False, False))

        movie_tasks = len(insert_list)

        if movie_tasks == 0:
            self._update_activity_record('movies_watched', update_time)
            return

        inserted_tasks = 0
        if not self.silent:
            self.progress_dialog.update(0, 'Inserting Watched Movies')


        cursor = self._get_cursor()

        sql_statements = 0

        for i in insert_list:
            inserted_tasks += 1
            progress_perc = (float(inserted_tasks) / float(movie_tasks)) * 100
            if not self.silent:
                self.progress_dialog.update(int(progress_perc))

            cursor.execute(
                "INSERT OR IGNORE INTO movies ("
                "trakt_id, kodi_meta, collected, watched, last_updated)"
                "VALUES "
                "(?, ?, ?, ?, ?)",
                (i[0], str({}), 0, 0, self.base_date))

            sql_statements += 1
            if sql_statements > 999:
                cursor.connection.commit()
                sql_statements = 0

        if not self.silent:
            self.progress_dialog.update(0, 'Marking Movies Watched')

        for item in insert_list:
            # movie_sync.mark_movie_watched(item[1][0])
            cursor.execute('UPDATE movies SET watched=1 WHERE trakt_id=?', (item[0],))

        cursor.connection.commit()
        cursor.close()


        self._update_activity_record('movies_watched', update_time)

    def _sync_watched_episodes(self):

        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        if not self.silent:
            self.progress_dialog.update(-1, 'Fetching Watched Episodes')
        trakt_watched = Trakt.TraktAPI().json_response('/sync/watched/shows')
        trakt_watched = ['%s-%s-%s' % (show['show']['ids']['trakt'], season['number'], episode['number'])
                         for show in trakt_watched for season in show['seasons'] for episode
                         in season['episodes']]

        local_watched = shows.TraktSyncDatabase().get_watched_episodes()
        local_watched = ['%s-%s-%s' % (i['show_id'], i['season'], i['number']) for i in local_watched]

        self._mill_episodes(trakt_watched, local_watched, 1, None)

        self._update_activity_record('shows_watched', update_time)

    def _sync_unwatched(self):

        if not self.silent:
            self.progress_dialog.update(-1, 'Fetching Unwatched Movies')
        trakt_watched_movies = Trakt.TraktAPI().json_response('sync/watched/movies')
        trakt_watched_movies = [i['movie']['ids']['trakt'] for i in trakt_watched_movies]
        local_watched_movies = movie_sync.get_watched_movies()
        local_watched_movies = [i['trakt_id'] for i in local_watched_movies]

        if not self.silent:
            self.progress_dialog.update(-1, 'Fetching Unwatched Episodes')
        trakt_watched_episodes = Trakt.TraktAPI().json_response('sync/watched/shows')
        trakt_watched_episodes = ['%s-%s-%s' % (show['show']['ids']['trakt'], season['number'], episode['number'])
                                  for show in trakt_watched_episodes for season in show['seasons'] for episode
                                  in season['episodes']]
        local_watched_episodes = show_sync.get_watched_episodes()
        local_watched_episodes = ['%s-%s-%s' % (i['show_id'], i['season'], i['number']) for i in local_watched_episodes]

        for movie in local_watched_movies:
            if movie not in trakt_watched_movies:
                movie_sync.mark_movie_unwatched(movie)

        for episode in local_watched_episodes:
            if episode not in trakt_watched_episodes:

                show_sync.mark_episode_unwatched(*episode.split('-'))

    def _sync_collection_movies(self):

        insert_list = []
        if not self.silent:
            self.progress_dialog.update(0, 'Fetching Collected Movies')
        local_collection = [i['trakt_id'] for i in movie_sync.get_collected_movies()]
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        trakt_collecton = [i['movie']['ids']['trakt'] for i in Trakt.TraktAPI().json_response('sync/collection/movies')]

        for item in trakt_collecton:
            if item not in local_collection:
                insert_list.append(item)

        inserted_tasks = 0
        cursor = self._get_cursor()

        if not self.silent:
            self.progress_dialog.update(0, 'Inserting Collected Movies')

        sql_statements = 0

        for i in insert_list:
            inserted_tasks += 1
            progress_perc = (float(inserted_tasks) / float(len(insert_list))) * 100
            if not self.silent:
                self.progress_dialog.update(int(progress_perc))
            cursor.execute(
                "INSERT OR IGNORE INTO movies ("
                "trakt_id, kodi_meta, collected, watched, last_updated)"
                "VALUES "
                "(?, ?, ?, ?, ?)",
                (i, str({}), 0, 0, self.base_date))

            # Batch the entries as to not reach SQL expression limit
            sql_statements += 1
            if sql_statements > 999:
                cursor.connection.commit()
                sql_statements = 0

        cursor.connection.commit()
        cursor.close()

        cursor = self._get_cursor()

        if not self.silent:
            self.progress_dialog.update(0, 'Marking Movies Collected')

        for item in insert_list:
            cursor.execute('UPDATE movies SET collected=1 WHERE trakt_id=?', (item,))
            # movie_sync.mark_movie_collected(item[1][0])
        cursor.connection.commit()
        cursor.close()

        self._update_activity_record('movies_collected', update_time)

    def _sync_collection_shows(self):

        local_collection = ['%s-%s-%s' % (i['show_id'], i['season'], i['number'])
                            for i in show_sync.get_collected_episodes()]

        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        if not self.silent:
            self.progress_dialog.update(0, 'Fetching Collected Episodes')
        trakt_collection = Trakt.TraktAPI().json_response('sync/collection/shows')
        trakt_collection = ['%s-%s-%s' % (show['show']['ids']['trakt'], season['number'], episode['number'])
                            for show in trakt_collection for season in show['seasons'] for episode
                            in season['episodes']]

        self._mill_episodes(trakt_collection, local_collection, None, 1)

        self._update_activity_record('shows_collected', update_time)

    def _sync_uncollected(self):

        if not self.silent:
            self.progress_dialog.update(0, 'Fetching Uncollected Movies')

        trakt_collected_movies = Trakt.TraktAPI().json_response('sync/collected/movies')

        if trakt_collected_movies is not None:
            trakt_collected_movies = [i['movie']['ids']['trakt'] for i in trakt_collected_movies]
        else:
            trakt_collected_movies = []
        local_collected_movies = movie_sync.get_collected_movies()
        local_collected_movies = [i['trakt_id'] for i in local_collected_movies]

        if not self.silent:
            self.progress_dialog.update(0, 'Fetching Uncollected Episodes')

        trakt_collected_episodes = Trakt.TraktAPI().json_response('sync/collected/shows')

        if trakt_collected_episodes is not None:
            trakt_collected_episodes = ['%s-%s-%s' % (show['show']['ids']['trakt'], season['number'], episode['number'])
                                        for show in trakt_collected_episodes for season in show['seasons'] for episode
                                        in season['episodes']]
        else:
            trakt_collected_episodes = []

        local_collected_episodes = show_sync.get_collected_episodes()
        local_collected_episodes = ['%s-%s-%s' % (i['show_id'], i['season'], i['number'])
                                    for i in local_collected_episodes]

        cursor = self._get_cursor()

        sql_statements = 0

        if len(trakt_collected_movies) > 0:
            for movie in local_collected_movies:
                if movie not in trakt_collected_movies:
                    cursor.execute('UPDATE movies SET collected=0 WHERE trakt_id=?', (movie,))
                    # movie_sync.mark_movie_uncollected(movie)

                    sql_statements += 1
                    if sql_statements > 999:
                        cursor.connection.commit()
                        sql_statements = 0

        if len(trakt_collected_episodes) > 0:
            for episode in local_collected_episodes:
                if episode not in trakt_collected_episodes:
                    episode_split = episode.split('-')
                    # show_sync.mark_episode_unwatched(*episode.split('-'))
                    cursor.execute('UPDATE episodes SET watched=0 WHERE show_id=? AND season=? AND number=?',
                                   (episode_split[0], episode_split[1], episode_split[2]))

                    sql_statements += 1
                    if sql_statements > 999:
                        cursor.connection.commit()
                        sql_statements = 0

        cursor.connection.commit()
        cursor.close()

    def _remove_old_meta_items(self, type):

        last_update = self.activites['%s_meta_update' % type]
        update_time = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))

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

        cursor = self._get_cursor()

        updated_item = sorted(list(set(updated_item)))

        sql_statements = 0

        if type == 'shows':
            for i in updated_item:
                cursor.execute('UPDATE shows SET kodi_meta=?, last_updated=? WHERE trakt_id=?',
                               (str({}), update_time, i))
                cursor.execute('UPDATE episodes SET kodi_meta=?, last_updated=? WHERE show_id=?',
                               (str({}), update_time, i))
                cursor.execute('UPDATE seasons SET kodi_meta=? WHERE show_id=?', (str({}), i))

                sql_statements += 3

                # Batch the entries as to not reach SQL expression limit
                if sql_statements > 999:
                    cursor.connection.commit()
                    sql_statements = 0

        elif type == 'movies':
            for i in updated_item:
                cursor.execute('UPDATE movies SET kodi_meta=?, last_updated=? WHERE trakt_id=?',
                               (str({}), update_time, i))

                sql_statements += 1

                # Batch the entries as to not reach SQL expression limit
                sql_statements += 1
                if sql_statements > 999:
                    cursor.connection.commit()
                    sql_statements = 0

        else:
            raise Exception
        cursor.connection.commit()
        cursor.close()

    def _mill_episodes(self, trakt_collection, local_collection, watched, collected):

        episode_insert_list = []
        show_ids = []

        sync_type = 'Watched' if watched == 1 else 'Collected'

        insert_collection = [i for i in trakt_collection if i not in local_collection]

        if len(insert_collection) == 0:
            return

        for i in insert_collection:
            show_ids.append(i.split('-')[0])

        show_ids = list(set(show_ids))

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
                for season in self.results_mill[str(show_id)]:
                    for episode in season['episodes']:
                        episode_string = '%s-%s-%s' % (show_id, episode['season'], episode['number'])

                        if episode_string in trakt_collection:
                            episode_insert_list.append((show_id, episode['season'], episode['ids']['trakt'],
                                                        episode['number']))
            except KeyError:
                pass
            except:
                import traceback
                traceback.print_exc()
                pass

        if not self.silent:
            self.progress_dialog.update(0, 'Inserting %s Shows' % sync_type)

        inserted_tasks = 0

        base_sql_statement = "INSERT OR IGNORE INTO shows (trakt_id, kodi_meta, last_updated) VALUES (%s, '{}', '%s')"
        cursor = self._get_cursor()

        sql_statements = 0

        for i in show_ids:
            inserted_tasks += 1
            progress_perc = (float(inserted_tasks) / float(len(show_ids))) * 100
            if not self.silent:
                self.progress_dialog.update(int(progress_perc))
            cursor.execute(base_sql_statement % (i, self.base_date))

            # Batch the entries as to not reach SQL expression limit
            sql_statements += 1
            if sql_statements > 999:
                cursor.connection.commit()
                sql_statements = 0

        cursor.connection.commit()
        cursor.close()

        base_sql_statement = "INSERT OR IGNORE INTO episodes " \
                             "(show_id, season, trakt_id, kodi_meta, last_updated, watched, collected, number)" \
                             " VALUES (%s, %s, %s, '{}', '%s', 0, 0, %s)"
        cursor = self._get_cursor()

        if not self.silent:
            self.progress_dialog.update(0, 'Inserting %s Episodes' % sync_type)
        inserted_tasks = 0

        sql_statements = 0

        # Insert the episode Records
        for i in episode_insert_list:
            inserted_tasks += 1
            progress_perc = (float(inserted_tasks) / float(len(episode_insert_list))) * 100
            if not self.silent:
                self.progress_dialog.update(int(progress_perc))

            cursor.execute(base_sql_statement % (int(i[0]), int(i[1]), int(i[2]), self.base_date, i[3]))

            # Batch the entries as to not reach SQL expression limit
            sql_statements += 1
            if sql_statements > 999:
                cursor.connection.commit()
                sql_statements = 0

        cursor.connection.commit()
        cursor.close()

        if not self.silent:
            self.progress_dialog.update(0, 'Marking Episodes %s' % sync_type)

        inserted_tasks = 0

        cursor = self._get_cursor()

        # Update episode records watched/collected status
        if watched == 1:
            for i in episode_insert_list:
                inserted_tasks += 1
                progress_perc = (float(inserted_tasks) / float(len(episode_insert_list))) * 100
                if not self.silent:
                    self.progress_dialog.update(int(progress_perc))
                cursor.execute('UPDATE episodes SET watched=1 WHERE trakt_id=?', (int(i[2]),))

        else:
            for i in episode_insert_list:
                inserted_tasks += 1
                progress_perc = (float(inserted_tasks) / float(len(episode_insert_list))) * 100
                if not self.silent:
                    self.progress_dialog.update(int(progress_perc))
                cursor.execute('UPDATE episodes SET collected=1 WHERE trakt_id=?', (int(i[2]),))

        cursor.connection.commit()
        cursor.close()

        return episode_insert_list

    def _update_activity_record(self, record, time):

        cursor = self._get_cursor()
        cursor.execute('UPDATE activities SET %s=? WHERE sync_id=1' % record, (time,))
        cursor.connection.commit()
        cursor.close()

    def _pull_show_episodes(self, show_id):
        self.results_mill.update({str(show_id): database.get(Trakt.TraktAPI().json_response, 24,
                                                        '/shows/%s/seasons?extended=episodes' % show_id)})