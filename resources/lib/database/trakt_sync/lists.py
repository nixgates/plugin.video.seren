# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.database import trakt_sync
from resources.lib.database.cache import use_cache
from resources.lib.modules.metadataHandler import MetadataHandler


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    @use_cache()
    def extract_trakt_page(self, url, media_type, **params):
        result = []
        page_number = params.pop("page", 1)
        params["limit"] = self.page_limit
        get = MetadataHandler.get_trakt_info
        for page in self.trakt_api.get_all_pages_json(url, **params):
            for i in page:
                self.task_queue.put(
                    self._indexed_list_contents,
                    get(i, "username"),
                    get(i, "trakt_id"),
                    media_type,
                    **params
                )
            results = self.task_queue.wait_completion()
            if results is None:
                continue
            for i in page:
                if (
                    not results.get(i.get("trakt_id"))
                    or len(results.get(i.get("trakt_id"))) == 0
                ):
                    continue
                result.append(i)

            if len(result) >= (self.page_limit * page_number):
                return result[
                    self.page_limit * (page_number - 1) : self.page_limit * page_number
                ]
        return result[self.page_limit * (page_number - 1) :]

    def _indexed_list_contents(self, username, trakt_id, media_type, **params):
        return {
            trakt_id: self.get_list_content(username, trakt_id, media_type, **params)
        }

    @use_cache()
    def get_list_content(self, username, trakt_id, media_type, **params):
        list_item_url = "users/{}/lists/{}/items/{}".format(
            username, trakt_id, media_type
        )
        params["pull_all"] = True
        return self._extract_trakt_page(
            list_item_url, media_type, extended="full", **params
        )
