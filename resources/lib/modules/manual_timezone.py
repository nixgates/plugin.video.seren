# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmcgui

from resources.lib.modules.globals import g
from resources.lib.third_party import pytz


def validate_timezone_detected():
    if g.LOCAL_TIMEZONE and isinstance(g.LOCAL_TIMEZONE, pytz.BaseTzInfo) and g.LOCAL_TIMEZONE.zone != 'UTC':
        return
    else:
        g.set_setting("general.manualtimezone", True)
        notify_timezone_not_detected()


def notify_timezone_not_detected():
    confirm = xbmcgui.Dialog().yesno(g.get_language_string(30549), g.get_language_string(30550))
    if confirm:
        choose_timezone()


def choose_timezone():
    current = g.get_setting("general.localtimezone")
    time_zones = [
        i
        for i in pytz.common_timezones
        if len(i.split('/')) >= 2 and not i.split('/')[0] == 'US'
    ]
    # Note we deliberately don't include the US timezones as they have too many assumptions for historic dates
    try:
        preselect = time_zones.index(current)
    except ValueError:
        preselect = -1
    tz_index = xbmcgui.Dialog().select(
        g.get_language_string(30548), time_zones, preselect=preselect
    )
    if not tz_index == -1:
        g.set_setting("general.localtimezone", time_zones[tz_index])
