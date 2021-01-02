# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from resources.lib.common import tools
from resources.lib.database.skinManager import SkinManager
from resources.lib.modules import mock_modules

_mock_information = tools.get_item_information(
    {
        "trakt_id": 3401782,
        "trakt_show_id": 1390,
        "mediatype": "episode",
        "trakt_season_id": 184210,
    }
)

mock_source = {
    "type": "torrent",
    "info": ["HDTV", "AAC"],
    "quality": "1080p",
    "hash": "hash",
    "size": 140000,
    "provider": "Test Provider",
    "release_title": "Test.Source.HDTV.AAC.1080p",
    "debrid_provider": "Premiumize",
    "seeds": 123,
}


def mock_playing_next():
    from resources.lib.gui.windows.playing_next import PlayingNext

    xbmc.Player = mock_modules.KodiPlayer
    window = PlayingNext(*SkinManager().confirm_skin_path("playing_next.xml"), item_information=_mock_information)
    window.doModal()
    del window


def mock_still_watching():
    from resources.lib.gui.windows.still_watching import StillWatching

    xbmc.Player = mock_modules.KodiPlayer
    window = StillWatching(
        *SkinManager().confirm_skin_path("still_watching.xml"),
        item_information=_mock_information
    )
    window.doModal()
    del window


def mock_resolver():
    resolver = mock_modules.Resolver(
        *SkinManager().confirm_skin_path("resolver.xml"),
        item_information=_mock_information
    )
    resolver.doModal([mock_source], _mock_information, False)


def mock_source_select():
    from resources.lib.gui.windows.source_select import SourceSelect

    sources = [mock_source for i in range(10)]

    window = SourceSelect(
        *SkinManager().confirm_skin_path("source_select.xml"),
        item_information=_mock_information,
        sources=sources
    )
    window.doModal()
    del window


def mock_cache_assist():
    from resources.lib.gui.windows.source_select import ManualCacheWindow

    sources = [mock_source for i in range(10)]

    ManualCacheWindow(
        *SkinManager().confirm_skin_path("manual_caching.xml"),
        item_information=_mock_information,
        sources=sources
    ).doModal()
