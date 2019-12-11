# -*- coding: utf-8 -*-

import sys
import time
from resources.lib.common import tools
from resources.lib.modules import router

if __name__ == '__main__':
    try:
        url = dict(tools.parse_qsl(sys.argv[2].replace('?', '')))
    except:
        url = {}
    start = time.time()
    router.dispatch(url)
    tools.log('Processing Time - %s: %s' % (url.get('action', ''), time.time() - start))
