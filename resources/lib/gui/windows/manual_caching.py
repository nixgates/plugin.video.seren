from resources.lib.gui.windows.source_window import SourceWindow
from resources.lib.modules.cacheAssist import CacheAssistHelper
from resources.lib.modules.exceptions import FailureAtRemoteParty
from resources.lib.modules.exceptions import GeneralCachingFailure
from resources.lib.modules.globals import g
from resources.lib.modules.source_sorter import SourceSorter


class ManualCacheWindow(SourceWindow):
    def __init__(self, xml_file, location, item_information=None, sources=None, close_text=None):
        super().__init__(xml_file, location, item_information=item_information, sources=sources)
        self.sources = SourceSorter(self.item_information).sort_sources(self.sources)
        self.cache_assist_helper = CacheAssistHelper()
        self.cached_source = None
        if not close_text:
            close_text = g.get_language_string(30459)
        self.setProperty("close.text", close_text)

    def _cache_item(self):
        uncached_source = self.sources[self.display_list.getSelectedPosition()]
        cache_assist_module = self.cache_assist_helper.manual_cache(uncached_source)

        cache_status = cache_assist_module.do_cache()

        if cache_status['result'] == 'success':
            return cache_status['source']

    def handle_action(self, action_id, control_id=None):
        if action_id == 7:
            if control_id == 1000:
                try:
                    self._cache_item()
                except (GeneralCachingFailure, FailureAtRemoteParty) as e:
                    g.log(e, 'error')
            elif control_id == 2999:
                self.close()

    def doModal(self):
        super().doModal()
        return self.cached_source
