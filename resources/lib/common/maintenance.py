import os
import time

import xbmcgui
import xbmcvfs

from resources.lib.common import tools
from resources.lib.database import cache
from resources.lib.database.premiumizeTransfers import PremiumizeTransfers
from resources.lib.database.skinManager import SkinManager
from resources.lib.debrid import all_debrid
from resources.lib.debrid import premiumize
from resources.lib.debrid import real_debrid
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.indexers.tvdb import TVDBAPI
from resources.lib.modules.globals import g
from resources.lib.modules.providers.install_manager import ProviderInstallManager


def update_themes():
    """
    Performn checks for any theme updates
    :return: None
    :rtype: None
    """
    if g.get_bool_setting("skin.updateAutomatic"):
        SkinManager().check_for_updates(silent=True)


def update_provider_packages():
    """
    Perform checks for provider package updates
    :return: None
    :rtype: None
    """
    provider_check_stamp = g.get_float_runtime_setting("provider.updateCheckTimeStamp", 0)
    automatic = g.get_bool_setting("providers.autoupdates")
    if time.time() > (provider_check_stamp + (24 * (60 * 60))):
        available_updates = ProviderInstallManager().check_for_updates(silent=True, automatic=automatic)
        if not automatic and len(available_updates) > 0:
            g.notification(g.ADDON_NAME, g.get_language_string(30253))
        g.set_runtime_setting("provider.updateCheckTimeStamp", str(time.time()))


def refresh_apis():
    """
    Refresh common API tokens
    :return: None
    :rtype: None
    """
    TraktAPI().try_refresh_token()
    real_debrid.RealDebrid().try_refresh_token()
    TVDBAPI().try_refresh_token()


def wipe_install():
    """
    Destroys Seren's user_data folder for current user resetting addon to default
    :return: None
    :rtype: None
    """
    confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30083))
    if confirm == 0:
        return

    confirm = xbmcgui.Dialog().yesno(
        g.ADDON_NAME,
        f"{g.get_language_string(30034)}{g.color_string(g.get_language_string(30035))}",
    )
    if confirm == 0:
        return

    path = tools.validate_path(g.ADDON_USERDATA_PATH)
    if xbmcvfs.exists(path):
        xbmcvfs.rmdir(path, True)
    xbmcvfs.mkdir(g.ADDON_USERDATA_PATH)


def premiumize_transfer_cleanup():
    """
    Cleanup transfers created by Seren at Premiumize
    :return: None
    :rtype: NOne
    """
    service = premiumize.Premiumize()
    premiumize_transfers = PremiumizeTransfers()
    fair_usage = service.get_used_space()
    threshold = g.get_float_setting("premiumize.threshold")

    if fair_usage < threshold:
        g.log("Premiumize Fair Usage below threshold, no cleanup required")
        return
    seren_transfers = premiumize_transfers.get_premiumize_transfers()
    if seren_transfers is None:
        g.log("Failed to cleanup transfers, API error", "error")
        return
    if len(seren_transfers) == 0:
        g.log("No Premiumize transfers have been created")
        return
    g.log("Premiumize Fair Usage is above threshold, cleaning up Seren transfers")
    for i in seren_transfers:
        service.delete_transfer(i["transfer_id"])
        premiumize_transfers.remove_premiumize_transfer(i["transfer_id"])


def account_premium_status_checks():
    """
    Updates premium status settings to reflect current state and advises users of expiries if enabled
    :return: None
    :rtype: None
    """

    def set_settings_status(debrid_provider, status):
        """
        Ease of use method to set premium status setting
        :param debrid_provider: setting prefix for debrid provider
        :type debrid_provider: str
        :param is_premium: Status of premium status
        :type is_premium: bool
        :return: None
        :rtype: None
        """
        g.set_setting(f"{debrid_provider}.premiumstatus", status.title())

    def display_expiry_notification(display_debrid_name):
        """
        Ease of use method to notify user of expiry of debrid premium status
        :param display_debrid_name: Debrid providers full display name
        :type display_debrid_name: str
        :return: None
        :rtype: None
        """
        if g.get_bool_setting("general.accountNotifications"):
            g.notification(
                f"{g.ADDON_NAME}",
                g.get_language_string(30036).format(display_debrid_name),
            )

    valid_debrid_providers = [
        ("Real Debrid", real_debrid.RealDebrid, "rd"),
        ("Premiumize", premiumize.Premiumize, "premiumize"),
        ("All Debrid", all_debrid.AllDebrid, "alldebrid"),
    ]

    for service in valid_debrid_providers:
        service_module = service[1]()
        if service_module.is_service_enabled():
            status = service_module.get_account_status()
            if status == "expired":
                display_expiry_notification(service[0])
            g.log(f"{service[0]}: {status}")
            set_settings_status(service[2], status)


def toggle_reuselanguageinvoker(forced_state=None):
    def _store_and_reload(output):
        with open(file_path, "w+") as addon_xml:
            addon_xml.writelines(output)
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30531))
        g.reload_profile()

    file_path = os.path.join(g.ADDON_DATA_PATH, "addon.xml")

    with open(file_path) as addon_xml:
        file_lines = addon_xml.readlines()

    for i in range(len(file_lines)):
        line_string = file_lines[i]
        if "reuselanguageinvoker" in file_lines[i]:
            if ("false" in line_string and forced_state is None) or ("false" in line_string and forced_state):
                file_lines[i] = file_lines[i].replace("false", "true")
                g.set_setting("reuselanguageinvoker.status", "Enabled")
                _store_and_reload(file_lines)
            elif ("true" in line_string and forced_state is None) or ("true" in line_string and forced_state is False):
                file_lines[i] = file_lines[i].replace("true", "false")
                g.set_setting("reuselanguageinvoker.status", "Disabled")
                _store_and_reload(file_lines)
            break


# def clean_deprecated_settings():
#     """
#     Removes settings no longer defined in the settings.xml file from the users user_data settings file
#     :return: None
#     :rtype: None
#     """
#     settings_helper = SettingsHelper()
#     settings_helper.create_and_clean_settings()
#     if len(settings_helper.valid_settings) != len(
#         settings_helper.current_user_settings
#     ):
#         g.log(
#             "Mismatch in valid settings, cancelling the removal of deprecated settings",
#             "warning",
#         )
#         return
#     if len(settings_helper.removed_settings) == 0:
#         return
#     settings_helper.save_settings()
#     g.log(
#         "Filtered settings, removed {} deprecated settings".format(
#             len(settings_helper.removed_settings)
#         )
#     )


def run_maintenance():
    """
    Entry point for background maintenance cycle
    :return: None
    :rtype: None
    """
    g.log("Performing Maintenance")
    # ADD COMMON HOUSE KEEPING ITEMS HERE #

    # Refresh API tokens

    try:
        refresh_apis()
    except Exception as e:
        g.log(f"Failed to update API keys: {e}", 'error')

    try:
        account_premium_status_checks()
    except Exception as e:
        g.log(f"Failed to check account status: {e}", 'error')
    ProviderInstallManager()
    update_provider_packages()
    update_themes()

    # Check Premiumize Fair Usage for cleanup
    if g.get_bool_setting("premiumize.enabled") and g.get_bool_setting("premiumize.autodelete"):
        try:
            premiumize_transfer_cleanup()
        except Exception as e:
            g.log(f"Failed to cleanup PM transfers: {e}", 'error')

    # clean_deprecated_settings()
    cache.Cache().check_cleanup()
