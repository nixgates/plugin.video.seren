# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import collections
import threading

from resources.lib.database import Database
from resources.lib.modules.globals import g

migrate_db_lock = threading.Lock()

schema = {
    'transfers': {
        'columns': collections.OrderedDict([
            ("transfer_id", ["TEXT", "NOT NULL"]),
        ]),
        "table_constraints": ["UNIQUE(transfer_id)"],
        "default_seed": []
    }
}


class PremiumizeTransfers(Database):
    """
    Databsae for recording background transfer created by Seren
    """
    def __init__(self):
        super(PremiumizeTransfers, self).__init__(g.PREMIUMIZE_DB_PATH, schema, migrate_db_lock)
        self.table_name = next(iter(schema))

    def get_premiumize_transfers(self):
        """
        Fetch all transfer created by Seren not removed
        :return: List of all transfers
        :rtype: list
        """
        return self.execute_sql("SELECT * FROM transfers").fetchall()

    def add_premiumize_transfer(self, transfer_id):
        """
        Add a transfer record to the database
        :param transfer_id: ID from premiumize for the transfer
        :type transfer_id: str
        :return: None
        :rtype: None
        """
        self.execute_sql("REPLACE INTO transfers (transfer_id) VALUES (?)", (transfer_id,))

    def remove_premiumize_transfer(self, transfer_id):
        """
        Removes the transfer from the database if it exists
        :param transfer_id: ID of transfer from Premiumize
        :type transfer_id: str
        :return: None
        :rtype: None
        """
        self.execute_sql("DELETE FROM transfers WHERE transfer_id=?", (transfer_id,))
