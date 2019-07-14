from resources.lib.modules import trakt_sync


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):

    def add_hidden_item(self, trakt_id, item_type, section):
        cursor = self._get_cursor()
        cursor.execute('INSERT OR REPLACE INTO hidden ('
                       'id_section, trakt_id, section, item_type) VALUES '
                       '(?, ?, ?, ?)',
                       ('%s-%s' % (str(section), str(trakt_id)), trakt_id, section, item_type))
        cursor.connection.commit()
        cursor.close()

    def get_hidden_items(self, section, type=''):
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM hidden WHERE section=?',
                       (section,))
        hidden_items = cursor.fetchall()
        cursor.close()

        if type == '':
            return hidden_items
        elif type == 'movies':
            return [i['trakt_id'] for i in hidden_items if i['item_type'] == 'movie']
        elif type == 'shows':
            return [i['trakt_id'] for i in hidden_items if i['item_type'] == 'show']
        else:
            raise Exception

    def remove_item(self, section, trakt_id):
        cursor = self._get_cursor()
        cursor.execute('DELETE FROM hidden WHERE section=? AND trakt_id=?',
                       (str(section), int(trakt_id)))
        cursor.connection.commit()
        cursor.close()
