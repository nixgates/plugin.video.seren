from resources.lib.common import tools
from resources.lib.modules.skin_manager import SkinManager
from resources.lib.modules import mock_modules

_mock_args = tools.quote('{"episode": 1, "item_type": "episode", "season": 2, "trakt_id": 122709}')
mock_source = {
    'type': 'torrent',
    'info': ['HDTV', 'AAC'],
    'quality': '1080p',
    'hash': 'hash',
    'size': 140000,
    'provider': 'Test Provider',
    'release_title': 'Test.Source.HDTV.AAC.1080p',
    'debrid_provider': 'Premiumize'
}


def test_playing_next():
    from resources.lib.gui.windows.playing_next import PlayingNext
    tools.player = mock_modules.KodiPlayer
    PlayingNext(*SkinManager().confirm_skin_path('playing_next.xml'), actionArgs=_mock_args).doModal()


def test_still_watching():
    from resources.lib.gui.windows.still_watching import StillWatching
    tools.player = mock_modules.KodiPlayer
    StillWatching(*SkinManager().confirm_skin_path('still_watching.xml'), actionArgs=_mock_args).doModal()


def test_resolver():
    resolver = mock_modules.Resolver(*SkinManager().confirm_skin_path('resolver.xml'), actionArgs=_mock_args)
    resolver.doModal([mock_source], tools.get_item_information(_mock_args), False)


def test_source_select():
    from resources.lib.gui.windows.source_select import SourceSelect
    sources = [mock_source for i in range(10)]

    SourceSelect(*SkinManager().confirm_skin_path('source_select.xml'),
                 actionArgs=_mock_args, sources=sources).doModal()
