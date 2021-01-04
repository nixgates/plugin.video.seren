# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.common import tools
from resources.lib.database.trakt_sync import lists
from resources.lib.modules.globals import g
from resources.lib.modules.list_builder import ListBuilder
from resources.lib.modules.metadataHandler import MetadataHandler


class ListsHelper:
    def __init__(self):
        self.title_appends = g.get_setting('general.appendListTitles')
        self.lists_database = lists.TraktSyncDatabase()
        self.builder = ListBuilder()
        self.no_paging = not g.get_bool_setting('general.paginatetraktlists')

    def get_list_items(self):
        arguments = g.REQUEST_PARAMS['action_args']
        media_type = g.REQUEST_PARAMS.get('media_type', arguments.get('type'))
        list_items = self.lists_database.get_list_content(arguments['username'],
                                                          arguments['trakt_id'],
                                                          self._backwards_compatibility(media_type),
                                                          page=g.PAGE,
                                                          no_paging=self.no_paging)

        if not list_items:
            g.log('Failed to pull list {} from Trakt/Database'.format(arguments['trakt_id']), 'error')
            g.cancel_directory()
            return

        if media_type in ['tvshow', 'shows']:
            self.builder.show_list_builder(list_items, no_paging=self.no_paging)
        elif media_type in ['movie', 'movies']:
            self.builder.movie_menu_builder(list_items, no_paging=self.no_paging)

    def my_trakt_lists(self, media_type):
        self._create_list_menu(
            self.lists_database.extract_trakt_page('users/me/lists',
                                                   media_type,
                                                   page=g.PAGE,
                                                   no_paging=self.no_paging,
                                                   ignore_cache=True),
            media_type=media_type)

    def my_liked_lists(self, media_type):
        self._create_list_menu(
            self.lists_database.extract_trakt_page('users/likes/lists',
                                                   media_type,
                                                   page=g.PAGE,
                                                   no_paging=self.no_paging,
                                                   ignore_cache=True),
            media_type=media_type)

    def trending_lists(self, media_type):
        self._create_list_menu(
            self.lists_database.extract_trakt_page('lists/trending',
                                                   media_type,
                                                   page=g.PAGE,
                                                   no_paging=True),
            no_paging=True,
            media_type=media_type)

    def popular_lists(self, media_type):
        self._create_list_menu(
            self.lists_database.extract_trakt_page('lists/popular',
                                                   media_type,
                                                   page=g.PAGE,
                                                   no_paging=True),
            no_paging=True,
            media_type=media_type)

    def _create_list_menu(self, trakt_lists, **params):
        trakt_object = MetadataHandler.trakt_object
        get = MetadataHandler.get_trakt_info
        if not trakt_lists:
            trakt_lists = []

        self.builder.lists_menu_builder(
            [tools.smart_merge_dictionary(trakt_object(trakt_list),
                                          {'args': {'trakt_id': get(trakt_list, 'trakt_id'),
                                              'username': get(trakt_list, 'username'),
                                              'sort_how': get(trakt_list, 'sort_how'),
                                              'sort_by': get(trakt_list, 'sort_by')}})
             for trakt_list in trakt_lists], **params)

    @staticmethod
    def _backwards_compatibility(media_type):
        if media_type == 'movie':
            return 'movies'
        if media_type in ['tvshow', 'show']:
            return 'shows'
        return media_type
