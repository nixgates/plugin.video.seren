# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import sys

from resources.lib.common import tools

if tools.is_stub():
    # noinspection PyUnresolvedReferences
    from mock_kodi import MOCK

from resources.lib.modules import router
from resources.lib.modules.globals import g
from resources.lib.modules.timeLogger import TimeLogger

g.init_globals(sys.argv)

try:
    with TimeLogger('{}'.format(g.REQUEST_PARAMS.get('action', ''))):
        router.dispatch(g.REQUEST_PARAMS)
finally:
    g.deinit()
#xbmc.log(str('SEREN_MODIFICATION')+'===>PHIL', level=xbmc.LOGINFO)
"""
try:
    curr_time = time.time()
    with TimeLogger('{}'.format(g.REQUEST_PARAMS.get('action', ''))):
        router.dispatch(g.REQUEST_PARAMS)
    while time.time() - curr_time < 3:
        #xbmc.log(str(1)+'===>PHIL', level=xbmc.LOGINFO)
        xbmc.sleep(1000)
        #xbmc.log(str(2)+'===>PHIL', level=xbmc.LOGINFO)
        if not xbmc.Player().isPlaying() and not xbmc.getCondVisibility('Window.IsActive(persistent_background.xml)'):
            #xbmc.log(str(3)+'===>PHIL', level=xbmc.LOGINFO)
            #xbmc.log(str(g.REQUEST_PARAMS['smartPlay'])+'===>PHIL', level=xbmc.LOGINFO)
            #xbmc.log(str(g.REQUEST_PARAMS['source_select'])+'===>PHIL', level=xbmc.LOGINFO)
            #del router
            try:
                test_var = str(g.REQUEST_PARAMS['source_select']) == 'true' or str(g.REQUEST_PARAMS['smartPlay']) == 'true'
            except:
                #g.deinit()
                #g.deinit()
                #g.deinit()
                del router
                del g
                del TimeLogger
                exit()
                #break
            if str(g.REQUEST_PARAMS['source_select']) == 'true' or str(g.REQUEST_PARAMS['smartPlay']) == 'true':
                router.dispatch(g.REQUEST_PARAMS)
                xbmc.sleep(1000)
                #g.deinit()
                #g.deinit()
                #g.deinit()
                del router
                del g
                del TimeLogger
                exit()
            else:
                #g.deinit()
                #g.deinit()
                #g.deinit()
                del router
                del g
                del TimeLogger
                exit()
finally:
    try:
        g.deinit()
    except:
        pass
try:
    g.deinit()
    g.deinit()
    del router
    del g
    del TimeLogger
except:
    pass
exit()
"""
