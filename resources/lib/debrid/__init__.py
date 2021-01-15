# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from resources.lib.modules.globals import g


def get_debrid_priorities():
    """
    Gets priorities of each debrid provider
    :return: Returns a list of dictionaries providing priorities of each debrid provider
    """
    p = []

    if g.get_bool_setting('premiumize.enabled'):
        p.append({'slug': 'premiumize', 'priority': g.get_int_setting('premiumize.priority')})
    if g.get_bool_setting('realdebrid.enabled'):
        p.append({'slug': 'real_debrid', 'priority': g.get_int_setting('rd.priority')})
    if g.get_bool_setting('alldebrid.enabled'):
        p.append({'slug': 'all_debrid', 'priority': g.get_int_setting('alldebrid.priority')})

    p = sorted(p, key=lambda i: i['priority'])

    return p