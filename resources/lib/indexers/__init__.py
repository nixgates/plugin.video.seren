# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals


def trakt_auth_guard(func):
    """
    Decorator to ensure method will only run if a valid Trakt auth is present
    :param func: method to run
    :return: wrapper method
    """
    import xbmcgui
    from functools import wraps

    from resources.lib.modules.globals import g
    from resources.lib.modules.global_lock import GlobalLock

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Wrapper method
        :param args: method args
        :param kwargs: method kwargs
        :return: method results
        """
        if g.get_setting("trakt.auth"):
            return func(*args, **kwargs)
        with GlobalLock("trakt.auth_guard"):
            if not g.get_setting("trakt.auth"):
                if xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30471)):
                    from resources.lib.indexers.trakt import TraktAPI
                    TraktAPI().auth()
                else:
                    g.cancel_directory()
        if g.get_setting("trakt.auth"):
            return func(*args, **kwargs)
        else:
            g.cancel_directory()

    return wrapper

