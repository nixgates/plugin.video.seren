from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g

SORT_OPTIONS = {
    "sortmethod": [30513, 30237, 30252, 30570, 30251, 30571, 30572, 30573, 30575],
    # None, Resolution, Source Type, Debrid Provider, Size, Low Cam Sort, HEVC, DV/HDR, Audio Channels
    "none": [],
    "resolution": [],
    "sourcetypesort": [30581, 30249, 30470, 30057, 30058, 30631],
    # Other, Cloud, Adaptive, Torrents, Hosters, Direct
    "debridsort": [30513, 30134, 30135, 30333],
    # None, Premiumize, Real-Debrid, AllDebrid
    "size": [],
    "cam": [],
    "hevc": [],
    "hdrsort": [30513, 30590, 30574],
    # None, DV, HDR
    "audiochannels": [],
}
SORT_METHODS = [
    "none",
    "resolution",
    "sourcetypesort",
    "debridsort",
    "size",
    "cam",
    "hevc",
    "hdrsort",
    "audiochannels",
]


class SortSelect(BaseWindow):
    """
    Dialog to provide filter settings
    """

    def __init__(self, xml_file, xml_location):
        super().__init__(xml_file, xml_location)

        self.sort_lists = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]

        self.sort_options = {
            f"general.{key}.{idx}": g.get_int_setting(f"general.{key}.{idx}")
            for key in SORT_OPTIONS
            for idx in range(1, len(SORT_OPTIONS[key]))
        }
        self.sort_options.update(
            {
                f"general.sortmethod.{idx}.reverse": g.get_bool_setting(f"general.sortmethod.{idx}.reverse")
                for idx in range(1, len(SORT_OPTIONS['sortmethod']))
            }
        )
        self.max_level = 8

    def onInit(self):
        self._populate_all_lists()
        self.set_default_focus(control_id=9000)
        super().onInit()

    def _populate_all_lists(self):
        self.max_level = 8
        self._reset_properties()
        for control_id in self.sort_lists:
            self._populate_list(int(control_id / 1000))
        self.setProperty("max_level", str(self.max_level))

    def _reset_properties(self):
        for i in range(len(SORT_OPTIONS['sortmethod'])):
            for j in range(6):
                self.clearProperty(f'general.sortmethod.{i}.label.{j}')
                self.clearProperty(f'general.sortmethod.{i}.label.{j}.last')

    @staticmethod
    def _set_setting_item_properties(menu_item, setting):
        for label in setting:
            if label == "label":
                menu_item.setLabel(g.get_language_string(setting[label]))
            else:
                menu_item.setProperty(label, str(setting[label]))

    def _populate_list(self, level):
        sort_method = f"general.sortmethod.{level}"
        method = SORT_METHODS[self.sort_options[sort_method]]
        options = SORT_OPTIONS[method]
        loops = len(options) if options else 1

        last_lang_code = None
        for idx in range(loops):
            if last_lang_code in [30513, 30581] or self.max_level < level:
                continue

            if idx == 0:
                lang_code = SORT_OPTIONS['sortmethod'][self.sort_options[sort_method]]
                self.setProperty(
                    f'general.sortmethod.{level}.label.{idx}',
                    str(g.get_language_string(lang_code)),
                )
                if lang_code == 30513:
                    self.max_level = level
            else:
                if not options:
                    continue

                lang_code = options[self.sort_options[f'general.{method}.{idx}']]
                self.setProperty(
                    f'general.sortmethod.{level}.label.{idx}',
                    str(g.get_language_string(lang_code)),
                )

            if lang_code in [30513, 30581] or loops == 1 or idx == loops - 1:
                self.setProperty(
                    f'general.sortmethod.{level}.label.{idx}.last',
                    str(True),
                )

            last_lang_code = lang_code
        self.setProperty(
            f"{sort_method}.reverse",
            str(self.sort_options[f"{sort_method}.reverse"]),
        )
        self.setProperty(
            f"{sort_method}",
            method,
        )

    def _cycle_info(self, level, idx):
        sort_method = f"general.sortmethod.{level}"
        method = SORT_METHODS[self.sort_options[sort_method]]
        setting = sort_method if idx == 0 else f'general.{method}.{idx}'

        current = self.sort_options[setting]
        category = setting.split('.')[1]
        new = (current + 1) % len(SORT_OPTIONS[category])

        self.sort_options[setting] = new
        return new

    def _handle_reverse(self, level):
        setting = f"general.sortmethod.{level}.reverse"
        self.sort_options[setting] = not self.sort_options[setting]
        self.setProperty(setting, str(self.sort_options[setting]))

    def _save_settings(self):
        for setting in self.sort_options:
            if (
                setting.endswith(".reverse")
                and SORT_METHODS[self.sort_options[setting.rstrip(".reverse")]] == "debridsort"
            ):
                g.set_setting(setting, False)
            else:
                g.set_setting(setting, self.sort_options[setting])

    def handle_action(self, action, control_id=None):
        if action == 7:
            if control_id in [1111, 2222, 3333, 4444, 5555, 6666, 7777, 8888]:
                self._handle_reverse(int(control_id / 1111))
            elif control_id == 9001:
                self.close()
            else:
                self._cycle_info(int(control_id / 1000), (control_id % 1000) - 1)
                self._populate_all_lists()
                self.setFocusId(control_id)

    def close(self):
        super().close()
        self._save_settings()
        g.open_addon_settings(6, 11)  # Open settings back where we were launched from
