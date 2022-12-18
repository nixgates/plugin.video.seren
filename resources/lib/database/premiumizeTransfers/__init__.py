import collections

from resources.lib.database import Database
from resources.lib.modules.globals import g

schema = {
    'transfers': {
        'columns': collections.OrderedDict(
            [
                ("transfer_id", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(transfer_id)"],
        "default_seed": [],
    }
}


class PremiumizeTransfers(Database):
    """
    Databsae for recording background transfer created by Seren
    """

    def __init__(self):
        super().__init__(g.PREMIUMIZE_DB_PATH, schema)
        self.table_name = next(iter(schema))

    def get_premiumize_transfers(self):
        """
        Fetch all transfer created by Seren not removed
        :return: List of all transfers
        :rtype: list
        """
        return self.fetchall("SELECT * FROM transfers")

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
