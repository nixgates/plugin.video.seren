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


def valid_id_or_none(id_number):
    """
    Helper function to check that an id number from an indexer is valid
    Checks if we have an id_number and it is not 0 or "0"
    :param id_number: The id number to check
    :return: The id number if valid, else None
    """
    return id_number if id_number and id_number != "0" else None
