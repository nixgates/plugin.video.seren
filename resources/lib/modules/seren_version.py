# -*- coding: utf-8 -*-
from resources.lib.modules.globals import g


def do_version_change():
    if g.get_setting("seren.version") == g.CLEAN_VERSION:
        return

    g.log("Clearing cache on Seren version change", "info")
    g.clear_cache(silent=True)

    g.set_setting("seren.version", g.CLEAN_VERSION)
