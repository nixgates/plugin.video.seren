# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmcgui

from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.database.providerCache import ProviderCache
from resources.lib.database.skinManager import SkinManager
from resources.lib.gui.windows.resolver_window import ResolverWindow
from resources.lib.modules.getSources import Sources
from resources.lib.modules.globals import g
from resources.lib.modules.resolver import Resolver


class Resolverhelper(object):
    """
    Helper object to stream line resolving items
    """
    @use_cache(1)
    def resolve_silent_or_visible(self, sources, item_information, pack_select=False, overwrite_cache=False):
        """
        Method to handle automatic background or foreground resolving
        :param sources: list of sources to handle
        :param item_information: information on item to play
        :param pack_select: True if you want to perform a manual file selection
        :param overwrite_cache: Set to true if you wish to overwrite the current cached return value
        :return: None if unsuccessful otherwise a playable object
        """
        if g.get_bool_setting('general.tempSilent'):
            return Resolver().resolve_multiple_until_valid_link(sources, item_information, pack_select, True)
        else:
            window = ResolverWindow(*SkinManager().confirm_skin_path('resolver.xml'),
                                    item_information=item_information)
            results = window.doModal(sources, item_information, pack_select)
            del window
            return results


class SourcesHelper(object):
    """
    Helper object to stream line scraping of items
    """
    @use_cache(1)
    def get_sources(self, action_args, overwrite_cache=None):
        """
        Method to handle automatic background or foreground scraping
        :param action_args: action arguments from request uri
        :param overwrite_cache: Set to true if you wish to overwrite the current cached return value
        :return:
        """
        item_information = tools.get_item_information(action_args)
        if not ProviderCache().get_provider_packages():
            yesno = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30477))
            if not yesno:
                return
        sources = Sources(item_information).get_sources()
        if sources is None or len(sources) <= 0 or len(sources[1]) <= 0:
            g.cancel_playback()
            g.notification(g.ADDON_NAME, g.get_language_string(30033), time=5000)
        return sources


def show_persistent_window_if_required(item_information):
    """
    Displays a constant window in the background, used to fill in gaps between windows dropping and opening
    :param item_information:
    :return: WindowDialog
    """
    if g.PLAYLIST.getposition() <= 0 and g.get_int_setting('general.scrapedisplay') == 0:
        from resources.lib.database.skinManager import SkinManager
        from resources.lib.gui.windows.persistent_background import PersistentBackground
        background = PersistentBackground(*SkinManager().confirm_skin_path('persistent_background.xml'),
                                          item_information=item_information)
        background.set_text(g.get_language_string(30031))
        background.show()
        return background
    else:
        return None
