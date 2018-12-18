# -*- coding: utf-8 -*-

import time

from resources.lib.common import tools
from resources.lib.modules import database
from resources.lib.modules import customProviders
from resources.lib.modules import resolver


def update_provider_packages():
    if tools.getSetting('providers.autoupdates') == 'false':
        return

    customProviders.providers().check_for_updates(silent=True, automatic=True)


def cache_large_info_requests():
    from resources.lib.indexers import trakt
    trakt = trakt.TraktAPI()
    database.get(trakt.json_response, .5, 'users/me/watched/shows?extended=full', limit=False)


def refresh_apis():
    rd_token = tools.getSetting('rd.auth')
    rd_expiry = int(float(tools.getSetting('rd.expiry')))
    tvdb_token = tools.getSetting('tvdb.jw')
    tvdb_expiry = int(float(tools.getSetting('tvdb.expiry')))

    if rd_token != '':
        if time.time() > (rd_expiry - (30 * 60)):
            from resources.lib.debrid import real_debrid
            tools.log('Service Refreshing Real Debrid Token')
            real_debrid.RealDebrid().refreshToken()

    if tvdb_token != '':
        if time.time() > (tvdb_expiry - (30 * 60)):
            tools.log('Service Refreshing TVDB Token')
            from resources.lib.indexers import tvdb
            if time.time() > tvdb_expiry:
                tvdb.TVDBAPI().newToken()
            else:
                tvdb.TVDBAPI().renewToken()
    else:
        from resources.lib.indexers import tvdb
        tvdb.TVDBAPI().newToken()


def wipe_install():
    confirm = tools.showDialog.yesno(tools.addonName, tools.lang(33021).encode('utf-8'))
    if confirm == 0:
        return

    confirm = tools.showDialog.yesno(tools.addonName, tools.lang(32049).encode('utf-8') +
                                     '%s' % tools.colorString(tools.lang(32050).encode('utf-8')))
    if confirm == 0:
        return

    import shutil, os
    if os.path.exists(tools.dataPath):
        shutil.rmtree(tools.dataPath)
    os.mkdir(tools.dataPath)


def premiumize_transfer_cleanup():
    from resources.lib.debrid import premiumize
    from resources.lib.modules import database
    premiumize = premiumize.PremiumizeBase()
    fair_usage = int(premiumize.account_info()['limit_used'] * 100)
    threshold = int(tools.getSetting('premiumize.threshold'))

    if fair_usage < threshold:
        tools.log('Premiumize Fair Usage below threshold, no cleanup required')
        return
    seren_transfers = database.get_premiumize_transfers()

    if len(seren_transfers) == 0:
        tools.log('No seren transfers have been created')
        return
    tools.log('Premiumize Fair Usage is above threshold, cleaning up Seren transfers')
    for i in seren_transfers:
        premiumize.delete_transfer(i['transfer_id'])
        database.remove_premiumize_transfer(i['transfer_id'])


def account_notifications():
    from resources.lib.debrid import real_debrid
    from resources.lib.debrid import premiumize
    import time

    if tools.getSetting('realdebrid.enabled') == 'true':
        premium_status = real_debrid.RealDebrid().get_url('user')['type']
        if premium_status == 'free':
            tools.showDialog.notification('%s: Real Debrid' % tools.addonName,
                                          tools.lang(32051).encode('utf-8'))

    if tools.getSetting('premiumize.enabled') == 'true':
        premium_status = premiumize.PremiumizeBase().account_info()['premium_until']
        if time.time() > premium_status:
            tools.showDialog.notification('%s: Premiumize' % tools.addonName,
                                          tools.lang(32052).encode('utf-8'))


def run_maintenance():
    tools.log('Performing Maintenance')
    # ADD COMMON HOUSE KEEPING ITEMS HERE #

    # Check cloud account status and alert user if expired

    try:
        if tools.getSetting('general.accountNotifications') == 'true':
            account_notifications()
    except:
        pass

    # Deploy the init.py file for the providers folder and make sure it's refreshed on startup
    try:
        customProviders.providers().deploy_init()
    except:
        pass

    try:
        update_provider_packages()
    except:
        pass

    # Refresh API tokens
    try:
        refresh_apis()
    except:
        pass

    # Check Premiumize Fair Usage for cleanup
    try:
        if tools.getSetting('premiumize.enabled') == 'true' and tools.getSetting('premiumize.autodelete') == 'true':
            premiumize_transfer_cleanup()
    except:
        pass

    # Update current resolver domains
    try:
        resolver.Resolver().getHosterList()
    except:
        pass
