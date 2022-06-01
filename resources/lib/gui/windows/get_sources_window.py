# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import threading

from resources.lib.gui.windows.single_item_window import SingleItemWindow
from resources.lib.modules.globals import g


class GetSourcesWindow(SingleItemWindow):
    def __init__(self, xml, location, item_information=None):
        super(GetSourcesWindow, self).__init__(
            xml, location, item_information=item_information
        )
        self.scraper_class = None

    def update_properties(self, source_statistics):
        # source_statistics = {
        #     "torrents": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #     "torrentsCached": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #     "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #     "cloudFiles": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #     "adaptive": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #     "totals": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #     "filtered": {
        #         "torrents": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #         "torrentsCached": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #         "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #         "cloudFiles": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #         "adaptive": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #         "totals": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
        #     },
        #     "remainingProviders": []
        # }
        try:

            def set_stats_property(source_type, quality, filtered=False):
                property = "{}_{}".format(source_type, quality)
                if filtered:
                    property += "_filtered"
                    stat = source_statistics['filtered'][source_type][quality]
                else:
                    stat = source_statistics[source_type][quality]
                self.setProperty(property, g.UNICODE(stat))

            source_types = [
                "totals",
                "torrents",
                "torrentsCached",
                "hosters",
                "cloudFiles",
                "adaptive",
            ]
            qualities = ["4K", "1080p", "720p", "SD", "total"]

            for filtered in [False, True]:
                for source_type in source_types:
                    for quality in qualities:
                        set_stats_property(source_type, quality, filtered)

            # Set remaining providers string
            self.setProperty(
                "remaining_providers_count",
                g.UNICODE(len(source_statistics["remainingProviders"])),
            )

            self.setProperty(
                "remaining_providers_list",
                g.color_string(' | ').join(
                    [i.upper() for i in source_statistics["remainingProviders"]]
                ),
            )

            remaining_providers_list = self.getControlList(2000)
            remaining_providers_list.reset()
            remaining_providers_list.addItems(source_statistics["remainingProviders"])
        except (KeyError, IndexError) as e:
            g.log('Failed to set window properties, {}'.format(e), 'error')

    def setProgress(self, progress):
        self.setProperty('progress', g.UNICODE(progress))

    def show(self):
        threading.Thread(target=self.doModal).start()
        self.setProperty('process_started', 'false')
        self.setProgress(0)

    def set_scraper_class(self, scraper_class):
        self.scraper_class = scraper_class

    def close(self):
        self.scraper_class.canceled = True
        super(GetSourcesWindow, self).close()
