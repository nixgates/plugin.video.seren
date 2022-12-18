import threading
from abc import ABCMeta
from abc import abstractmethod
from contextlib import contextmanager

import xbmc
import xbmcaddon
import xbmcgui


class SettingsCache(metaclass=ABCMeta):
    BOOL_VALUES_SET = {"true", "false", "1", "0"}
    BOOL_TRUE_SET = {"true", "1"}

    @abstractmethod
    def set_setting(self, setting_id, value):
        """
        Set a setting value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param value: The value to store in settings
        :type value: str|float|int|bool
        """
        pass

    @abstractmethod
    def update_settings(self, dictionary):
        """
        Update settings based on a dictionary of Keys/Values

        :param dictionary: The name of the setting
        :type dictionary: dict
        """
        for k, v in dictionary.items():
            self.set_setting(k, v)

    @abstractmethod
    def clear_setting(self, setting_id):
        """
        Clear a setting from the cache.

        Note that for persisted backed settings caches this will also clear the persisted value

        :param setting_id: The name of the setting
        :type setting_id: str
        """
        pass

    @abstractmethod
    def get_setting(self, setting_id, default_value=None):
        """
        Get a setting value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: str|float|int|bool
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or None
        :rtype: str|float|int|bool
        """
        pass

    @abstractmethod
    def get_float_setting(self, setting_id, default_value=None):
        """
        Get a setting as a float value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: float
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0.0
        :rtype: float
        """
        try:
            return float(self.get_setting(setting_id, default_value))
        except (ValueError, TypeError):
            return default_value if default_value is not None else 0.0

    @abstractmethod
    def get_int_setting(self, setting_id, default_value=None):
        """
        Get a setting as an int value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: int
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0
        :rtype: int
        """
        try:
            return int(float(self.get_setting(setting_id, default_value)))
        except (ValueError, TypeError):
            return default_value if default_value is not None else 0

    @abstractmethod
    def get_bool_setting(self, setting_id, default_value=None):
        """
        Get a setting as a bool value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: bool
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or False
        :rtype: bool
        """
        value = self.get_setting(setting_id, default_value)
        if isinstance(value, bool):
            return value
        if value is not None and str(value).lower() in self.BOOL_VALUES_SET:
            return str(value).lower() in self.BOOL_TRUE_SET
        else:
            return default_value if default_value is not None else False


class RuntimeSettingsCache(SettingsCache):
    _KODI_HOME_WINDOW = None
    _SETTINGS_PREFIX = None
    _KODI_ADDON_ID = None
    _KODI_ADDON_VERSION = None

    def __init__(self, settings_prefix="runtime"):
        self._KODI_HOME_WINDOW = xbmcgui.Window(10000)
        self._KODI_ADDON_ID = xbmcaddon.Addon().getAddonInfo("id")
        self._KODI_ADDON_VERSION = xbmcaddon.Addon().getAddonInfo("version")
        self._SETTINGS_PREFIX = settings_prefix

    def __del__(self):
        self._KODI_HOME_WINDOW = None
        del self._KODI_HOME_WINDOW

    def _setting_key(self, setting_id):
        return f"{self._KODI_ADDON_ID}.{self._KODI_ADDON_VERSION}.{self._SETTINGS_PREFIX}.{setting_id}"

    def set_setting(self, setting_id, value):
        """
        Set a runtime setting value

        Lists and Dict may only contain simple types

        :param setting_id: The name of the setting
        :type setting_id: str
        :param value: The value to store in settings
        :type value: str|float|int|bool
        """
        self._KODI_HOME_WINDOW.setProperty(self._setting_key(setting_id), str(value))

    def update_settings(self, dictionary):
        super().update_settings(dictionary)

    def clear_setting(self, setting_id):
        self._KODI_HOME_WINDOW.clearProperty(self._setting_key(setting_id))

    def get_setting(self, setting_id, default_value=None):
        try:
            value = self._KODI_HOME_WINDOW.getProperty(self._setting_key(setting_id))
            if value is None or value == "":
                return default_value if default_value is not None else None
            else:
                return value
        except (ValueError, TypeError):
            return None

    def get_float_setting(self, setting_id, default_value=None):
        return super().get_float_setting(setting_id, default_value)

    def get_int_setting(self, setting_id, default_value=None):
        return super().get_int_setting(setting_id, default_value)

    def get_bool_setting(self, setting_id, default_value=None):
        return super().get_bool_setting(setting_id, default_value)


class PersistedSettingsCache(SettingsCache):
    SETTINGS_LOCK_NAME = "PersistedSettingsLock"
    SETTINGS_LIST_NAME = "CachedSettingsList"
    SETTINGS_PERSISTED_FLAG = "SettingsPersistedFlag"
    EMPTY_PERSISTED_SETTING_VALUE = "__EMPTY_PERSISTED_VALUE__"
    _SETTINGS_THREAD_LOCK = threading.RLock()
    _SETTINGS_CACHE = None
    _RUNTIME_SETTINGS = None
    _KODI_MONITOR = None
    _KODI_HOME_WINDOW = None

    def __init__(self):
        self._KODI_HOME_WINDOW = xbmcgui.Window(10000)
        self._KODI_MONITOR = xbmc.Monitor()
        self._SETTINGS_CACHE = RuntimeSettingsCache(settings_prefix="persisted")
        self._RUNTIME_SETTINGS = RuntimeSettingsCache()

    def __del__(self):
        self._KODI_MONITOR = None
        del self._KODI_MONITOR
        self._KODI_HOME_WINDOW = None
        del self._KODI_HOME_WINDOW

    class KodiShutdown(RuntimeError):
        pass

    @contextmanager
    def _settings_lock(self):
        while self._RUNTIME_SETTINGS.get_bool_setting(self.SETTINGS_LOCK_NAME):
            if self._KODI_MONITOR.waitForAbort(0.01):
                raise self.KodiShutdown("Kodi Shutdown")
        try:
            with self._SETTINGS_THREAD_LOCK:
                while self._RUNTIME_SETTINGS.get_bool_setting(self.SETTINGS_LOCK_NAME):
                    if self._KODI_MONITOR.waitForAbort(0.01):
                        raise self.KodiShutdown("Kodi Shutdown")
                # pylint: disable=not-context-manager
                self._RUNTIME_SETTINGS.set_setting(self.SETTINGS_LOCK_NAME, True)
                yield
        finally:
            self._RUNTIME_SETTINGS.clear_setting(self.SETTINGS_LOCK_NAME)

    def _get_settings_list_set(self):
        settings_list = self._RUNTIME_SETTINGS.get_setting(self.SETTINGS_LIST_NAME)
        if settings_list is None or settings_list == "":
            settings_list = set()
        else:
            settings_list = set(settings_list.split(","))
        return settings_list

    def _store_setting_list_set(self, settings_list):
        self._RUNTIME_SETTINGS.set_setting(self.SETTINGS_LIST_NAME, ",".join(settings_list))

    def _set_settings_persisted_flag(self):
        self._RUNTIME_SETTINGS.set_setting(self.SETTINGS_PERSISTED_FLAG, True)

    def get_settings_persisted_flag(self):
        """
        When settings.xml is written to, a onSettingsChanged callback is fired for Monitor objects.
        Kodi addon API provides no way to determine if the event was fired due to a change by addon code
        or by a Kodi settings GUI change.  Neither does it provide the name of the setting that was changed.

        Whenever a setting is updated by the settings cache, a flag is set in runtime settings that can
        indicate to a monitor object if the callback was triggered by addon code and thus safely ignored
        for cache flushing.

        The Kodi Monitor object that implements onSettingsChange() callback should check for this flag using
        get_settings_persisted_flag() and, ONLY if it is False, call clear_cache().

        The persisted settings flag is cleared on calling this method.

        :return: A boolean representing whether a setting change was made within addon code
        :rtype: bool
        """
        with self._settings_lock():
            flag = self._RUNTIME_SETTINGS.get_bool_setting(self.SETTINGS_PERSISTED_FLAG)
            self._RUNTIME_SETTINGS.clear_setting(self.SETTINGS_PERSISTED_FLAG)
            return flag

    def set_setting(self, setting_id, value):
        if isinstance(value, bool):
            value_string = str(value).lower()
        else:
            value_string = str(value) if value is not None and value != "" else self.EMPTY_PERSISTED_SETTING_VALUE

        cache_value = self._SETTINGS_CACHE.get_setting(setting_id)
        if cache_value is not None and cache_value == value_string:
            return
        try:
            with self._settings_lock():
                self._set_setting(setting_id, value_string)
        except self.KodiShutdown:
            return

    def _set_setting(self, setting_id, value_string):
        settings_list = self._get_settings_list_set()
        settings_list.add(setting_id)
        self._store_setting_list_set(settings_list)

        self._SETTINGS_CACHE.set_setting(setting_id, value_string)
        kodi_addon = xbmcaddon.Addon()
        if kodi_addon.getSetting(setting_id) != (
            value_string if value_string != self.EMPTY_PERSISTED_SETTING_VALUE else ""
        ):
            kodi_addon.setSetting(
                setting_id, value_string if value_string != self.EMPTY_PERSISTED_SETTING_VALUE else ""
            )

            self._set_settings_persisted_flag()
        del kodi_addon

    def update_settings(self, dictionary):
        super().update_settings(dictionary)

    def clear_setting(self, setting_id):
        try:
            with self._settings_lock():
                settings_list = self._get_settings_list_set()
                settings_list.discard(setting_id)
                self._store_setting_list_set(settings_list)

                self._SETTINGS_CACHE.clear_setting(setting_id)
                kodi_addon = xbmcaddon.Addon()
                kodi_addon.setSetting(setting_id, "")
                del kodi_addon
                self._set_settings_persisted_flag()
        except self.KodiShutdown:
            return

    def clear_cache(self):
        """
        Clears the cache of all settings values leaving the persisted settings intact
        """
        try:
            with self._settings_lock():
                settings_list = self._get_settings_list_set()

                for setting_id in settings_list:
                    self._SETTINGS_CACHE.clear_setting(setting_id)

                self._RUNTIME_SETTINGS.clear_setting(self.SETTINGS_LIST_NAME)
        except self.KodiShutdown:
            return

    def get_setting(self, setting_id, default_value=None):
        """
        Get a setting value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value:
        :type default_value: str
        :return: The value of the setting as a string
                 If the setting is not stored, the optional default_value if provided or None
        :rtype: str
        """
        value = self._SETTINGS_CACHE.get_setting(setting_id)
        if value == self.EMPTY_PERSISTED_SETTING_VALUE:
            return str(default_value) if default_value else None
        if value is None or value == "":
            try:
                with self._settings_lock():
                    kodi_addon = xbmcaddon.Addon()
                    value = kodi_addon.getSetting(setting_id)
                    del kodi_addon
                    if value is None or value == "":
                        value = str(default_value) if default_value is not None else self.EMPTY_PERSISTED_SETTING_VALUE

                    settings_list = self._get_settings_list_set()
                    settings_list.add(setting_id)
                    self._store_setting_list_set(settings_list)

                    self._SETTINGS_CACHE.set_setting(setting_id, value)
            except self.KodiShutdown:
                return
        return value if value != self.EMPTY_PERSISTED_SETTING_VALUE else None

    def get_float_setting(self, setting_id, default_value=None):
        return super().get_float_setting(setting_id, default_value)

    def get_int_setting(self, setting_id, default_value=None):
        return super().get_int_setting(setting_id, default_value)

    def get_bool_setting(self, setting_id, default_value=None):
        return super().get_bool_setting(setting_id, default_value)
