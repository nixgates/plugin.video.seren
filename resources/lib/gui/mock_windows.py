import xbmc

from resources.lib.common import tools
from resources.lib.database.skinManager import SkinManager
from resources.lib.modules import mock_modules
from resources.lib.modules.globals import g

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
    "info": {"HEVC", "DV", "HDR", "HYBRID", "REMUX", "ATMOS", "TRUEHD", "7.1"},
    "quality": "1080p",
    "hash": "hash",
    "size": 1400,
    "provider": "Test Provider",
    "release_title": "Test.Source.1999.UHD.BDRemux.TrueHD.Atmos.7.1.HYBRID.DoVi.mkv",
    "debrid_provider": "premiumize",
    "seeds": 123,
}


mock_source_statistics = [
    {
        "torrents": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "torrentsCached": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "cloudFiles": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "totals": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "filtered": {
            "torrents": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "torrentsCached": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "cloudFiles": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "totals": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        },
        "remainingProviders": [
            "Test Provider",
            "Test Provider2",
            "Test Provider3",
            "Test Provider4",
            "Test Provider5",
            "6",
            "7",
            "8",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
        ],
    },
    {
        "torrents": {"4K": 1, "1080p": 2, "720p": 4, "SD": 8, "total": 15},
        "torrentsCached": {"4K": 0, "1080p": 2, "720p": 3, "SD": 3, "total": 8},
        "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
        "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "totals": {"4K": 2, "1080p": 2, "720p": 4, "SD": 8, "total": 16},
        "filtered": {
            "torrents": {"4K": 1, "1080p": 2, "720p": 4, "SD": 8, "total": 15},
            "torrentsCached": {"4K": 0, "1080p": 2, "720p": 3, "SD": 3, "total": 8},
            "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
            "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "totals": {"4K": 2, "1080p": 2, "720p": 3, "SD": 3, "total": 10},
        },
        "remainingProviders": [
            "Test Provider",
            "Test Provider2",
            "Test Provider3",
            "Test Provider4",
            "Test Provider5",
            "6",
            "7",
            "8",
            "8",
            "9",
            "10",
            "11",
            "12",
        ],
    },
    {
        "torrents": {"4K": 1, "1080p": 5, "720p": 8, "SD": 8, "total": 22},
        "torrentsCached": {"4K": 0, "1080p": 3, "720p": 4, "SD": 3, "total": 10},
        "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
        "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "totals": {"4K": 2, "1080p": 5, "720p": 8, "SD": 8, "total": 23},
        "filtered": {
            "torrents": {"4K": 1, "1080p": 4, "720p": 6, "SD": 8, "total": 19},
            "torrentsCached": {"4K": 0, "1080p": 2, "720p": 4, "SD": 3, "total": 9},
            "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
            "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "totals": {"4K": 2, "1080p": 2, "720p": 4, "SD": 3, "total": 11},
        },
        "remainingProviders": [
            "Test Provider",
            "Test Provider2",
            "Test Provider3",
            "Test Provider4",
            "Test Provider5",
            "Test Provider6",
            "Test Provider7",
            "Test Provider8",
        ],
    },
    {
        "torrents": {"4K": 2, "1080p": 7, "720p": 11, "SD": 9, "total": 33},
        "torrentsCached": {"4K": 2, "1080p": 5, "720p": 7, "SD": 4, "total": 17},
        "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
        "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "totals": {"4K": 3, "1080p": 7, "720p": 11, "SD": 9, "total": 34},
        "filtered": {
            "torrents": {"4K": 2, "1080p": 5, "720p": 9, "SD": 9, "total": 25},
            "torrentsCached": {"4K": 2, "1080p": 3, "720p": 6, "SD": 4, "total": 15},
            "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
            "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "totals": {"4K": 3, "1080p": 3, "720p": 6, "SD": 4, "total": 16},
        },
        "remainingProviders": [
            "Test Provider",
            "Test Provider2",
            "Test Provider3",
            "Test Provider4",
            "Test Provider5",
        ],
    },
    {
        "torrents": {"4K": 2, "1080p": 15, "720p": 17, "SD": 12, "total": 46},
        "torrentsCached": {"4K": 2, "1080p": 8, "720p": 9, "SD": 5, "total": 24},
        "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
        "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "totals": {"4K": 3, "1080p": 15, "720p": 17, "SD": 12, "total": 47},
        "filtered": {
            "torrents": {"4K": 2, "1080p": 13, "720p": 11, "SD": 10, "total": 36},
            "torrentsCached": {"4K": 2, "1080p": 5, "720p": 7, "SD": 6, "total": 20},
            "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
            "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "totals": {"4K": 3, "1080p": 5, "720p": 7, "SD": 6, "total": 21},
        },
        "remainingProviders": [
            "Test Provider",
            "Test Provider5",
        ],
    },
    {
        "torrents": {"4K": 2, "1080p": 15, "720p": 17, "SD": 12, "total": 46},
        "torrentsCached": {"4K": 2, "1080p": 8, "720p": 9, "SD": 5, "total": 24},
        "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
        "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        "totals": {"4K": 3, "1080p": 15, "720p": 17, "SD": 12, "total": 47},
        "filtered": {
            "torrents": {"4K": 2, "1080p": 13, "720p": 11, "SD": 10, "total": 36},
            "torrentsCached": {"4K": 2, "1080p": 5, "720p": 7, "SD": 6, "total": 20},
            "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "cloudFiles": {"4K": 1, "1080p": 0, "720p": 0, "SD": 0, "total": 1},
            "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
            "totals": {"4K": 3, "1080p": 5, "720p": 7, "SD": 6, "total": 21},
        },
        "remainingProviders": [],
    },
]

mock_downloads = [
    {
        "speed": "3kbps",
        "progress": "16.4%",
        "filename": "test file #1",
        "eta": "00:05:00",
        "filesize": "4.20gb",
        "downloaded": "0.69gb",
        "hash": "abcdefg",
    },
    {
        "speed": "-",
        "progress": "100%",
        "filename": "test file #2",
        "eta": "00:00:00",
        "filesize": "4.20gb",
        "downloaded": "4.20gb",
        "hash": "gfedcba",
    },
]


def mock_playing_next():
    from resources.lib.gui.windows.playing_next import PlayingNext

    xbmc.Player = mock_modules.KodiPlayer
    try:
        window = PlayingNext(*SkinManager().confirm_skin_path("playing_next.xml"), item_information=_mock_information)
        window.doModal()
    finally:
        del window


def mock_still_watching():
    from resources.lib.gui.windows.still_watching import StillWatching

    xbmc.Player = mock_modules.KodiPlayer
    try:
        window = StillWatching(
            *SkinManager().confirm_skin_path("still_watching.xml"), item_information=_mock_information
        )
        window.doModal()
    finally:
        del window


def mock_get_sources():
    import time

    try:
        get_sources_window = mock_modules.GetSources(
            *SkinManager().confirm_skin_path("get_sources.xml"), item_information=_mock_information
        )
        get_sources_window.setProperty("notification_text", g.get_language_string(30054))
        get_sources_window.show()
        xbmc.sleep(1500)
        get_sources_window.setProperty("has_torrent_providers", "true")
        get_sources_window.setProperty("has_hoster_providers", "true")
        get_sources_window.setProperty("has_adaptive_providers", "true")
        get_sources_window.setProperty("has_direct_providers", "true")
        get_sources_window.setProperty("has_cloud_scrapers", "true")
        start_time = time.time()
        timeout = 15
        get_sources_window.setProperty("process_started", "true")
        for stats in mock_source_statistics:
            runtime = time.time() - start_time
            get_sources_window.setProperty("runtime", str(f"{round(runtime, 2)} seconds"))
            timeout_progress = int(100 - float(1 - (runtime / float(timeout))) * 100)
            get_sources_window.setProperty('timeout_progress', str(timeout_progress))
            get_sources_window.setProgress(
                int(
                    100
                    - (
                        len(stats['remainingProviders'])
                        / float(len(mock_source_statistics[0]["remainingProviders"]))
                        * 100
                    )
                )
            )
            get_sources_window.update_properties(stats)
            xbmc.sleep(750)
        xbmc.sleep(10000)
        get_sources_window.close()
    finally:
        del get_sources_window


def mock_resolver():
    try:
        window = mock_modules.Resolver(
            *SkinManager().confirm_skin_path("resolver.xml"), item_information=_mock_information
        )
        window.doModal([mock_source], _mock_information)
    finally:
        del window


def mock_source_select():
    from resources.lib.gui.windows.source_select import SourceSelect

    sources = [mock_source for _ in range(10)]

    try:
        window = SourceSelect(
            *SkinManager().confirm_skin_path("source_select.xml"),
            item_information=_mock_information,
            sources=sources,
            uncached=sources,
        )
        window.doModal()
    finally:
        del window


def mock_cache_assist():
    from resources.lib.gui.windows.source_select import ManualCacheWindow

    sources = [mock_source for _ in range(10)]

    try:
        window = ManualCacheWindow(
            *SkinManager().confirm_skin_path("manual_caching.xml"), item_information=_mock_information, sources=sources
        )
        window.doModal()
    finally:
        del window


def mock_download_manager():
    try:
        window = mock_modules.DownloadManagerWindow(
            *SkinManager().confirm_skin_path("download_manager.xml"),
            item_information=_mock_information,
            mock_downloads=mock_downloads,
        )
        window.doModal()
    finally:
        del window
