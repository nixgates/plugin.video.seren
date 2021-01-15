# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import importlib
import os
import sys

from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.modules.globals import g


class SubtitleService:
    """
    Connects to available subtitle services and retrieves available subtitles for media
    """

    def __init__(self):
        self.task_queue = ThreadPool()
        self.subtitle_languages = g.get_kodi_subtitle_languages()
        self.preferred_language = g.get_kodi_preferred_subtitle_language()
        self.base_request = {
            "languages": ",".join(self.subtitle_languages),
            "preferredlanguage": self.preferred_language,
        }
        self.sources = [A4kSubtitlesAdapter()]

    def get_subtitle(self):
        """
        Fetch subtitle source
        :return: Url to subtitle
        :rtype: str
        """
        if self.sources is None:
            return None
        [
            self.task_queue.put(r.search, self.base_request)
            for r in self.sources
            if r.enabled
        ]
        results = self.task_queue.wait_completion()
        if results is None:
            return None
        try:
            return self.sources[0].download(results[0])
        except IndexError:
            g.log("No subtitles available from A4kSubtitles", "error")
            return None


class A4kSubtitlesAdapter:
    """
    Ease of use adapter for A4kSubtitles
    """

    def __init__(self):
        path = tools.translate_path(
            os.path.join(g.ADDONS_PATH, "service.subtitles.a4kSubtitles")
        )
        try:
            sys.path.append(path)
            self.service = importlib.import_module("a4kSubtitles.api").A4kSubtitlesApi(
                {"kodi": tools.is_stub()}
            )
            self.enabled = True
        except ImportError:
            self.enabled = False

    def search(self, request, **extra):
        """
        Search for a subtitle
        :param request: Dictionary containing currently available subtitles and the preferred language
        :type request: dict
        :param extra: Kwargs to provide video meta and settings to A4kSubtitles
        :type extra: dict
        :return: Available subtitle matches
        :rtype: list
        """
        video_meta = extra.pop("video_meta", None)
        settings = extra.pop("settings", None)
        return self.service.search(request, video_meta=video_meta, settings=settings)

    def download(self, request, **extra):
        """
        Downloads requested subtitle
        :param request: Selected subtitle from search results
        :type request: dict
        :param extra: Kwargs, set settings to settings to request to use
        :type extra: dict
        :return: Path to subtitle
        :rtype: str
        """
        settings = extra.pop("settings", None)
        return self.service.download(request, settings)
