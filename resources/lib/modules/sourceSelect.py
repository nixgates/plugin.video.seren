# -*- coding: utf-8 -*-

from resources.lib.common import tools


def sourceSelect(uncached_sources, source_list, info):
    try:
        if len(source_list) == 0:
            return None

        from resources.lib.gui.windows.source_select import SourceSelect
        window = SourceSelect('source_select.xml', tools.addonDir, actionArgs=info, sources=source_list)
        selection = window.doModal()
        del window

    except:
        import traceback
        traceback.print_exc()
        return None

    return selection