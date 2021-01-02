# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import collections
import threading

from resources.lib.database import Database
from resources.lib.modules.globals import g

migrate_db_lock = threading.Lock()

schema = {
    'packages': {
        'columns': collections.OrderedDict([
            ("pack_name", ["TEXT", "NOT NULL"]),
            ("author", ["TEXT", "NOT NULL"]),
            ("remote_meta", ["TEXT", "NOT NULL"]),
            ("version", ["TEXT", "NOT NULL"]),
            ("services", ["TEXT", "NOT NULL"]),
        ]),
        "table_constraints": ["UNIQUE(pack_name)"],
        "default_seed": []
    },
    'providers': {
        'columns': collections.OrderedDict([
            ("provider_name", ["TEXT", "NOT NULL"]),
            ("package", ["TEXT", "NOT NULL"]),
            ("status", ["TEXT", "NOT NULL"]),
            ("country", ["TEXT", "NOT NULL"]),
            ("provider_type", ["TEXT", "NOT NULL"])
        ]),
        "table_constraints": ["UNIQUE(provider_name)"],
        "default_seed": []
    },
    'package_settings': {
        'columns': collections.OrderedDict([
            ("package", ["TEXT", "NOT NULL"]),
            ("id", ["TEXT", "NOT NULL"]),
            ("type", ["TEXT", "NOT NULL"]),
            ("visible", ["INT", "NOT NULL"]),
            ("value", ["TEXT", "NOT NULL"]),
            ("label", ["TEXT", "NOT NULL"]),
            ("definition", ["PICKLE", "NOT NULL"]),
        ]),
        "table_constraints": ["UNIQUE(package, id)"],
        "default_seed": []
    },
}


class ProviderCache(Database):
    """
    Database class for handling calls to the database file
    """
    def __init__(self):
        super(ProviderCache, self).__init__(g.PROVIDER_CACHE_DB_PATH, schema, migrate_db_lock)
        self.table_name = next(iter(schema))

    @property
    def provider_insert_query(self):
        """
        Query for inserting a provider
        :return: Query for inserting a provider
        :rtype: str
        """
        return "INSERT OR IGNORE INTO providers " \
               "(provider_name, package, status, country, provider_type) VALUES (?, ?, ?, ?, ?)"

    @property
    def package_insert_query(self):
        """
        Query for inserting a package
        :return: Query for inserting a package
        :rtype: str
        """
        return "REPLACE INTO packages (pack_name, author, remote_meta, version, services) VALUES (?, ?, ?, ?, ?)"

    @property
    def package_setting_insert_query(self):
        """
        Query for inserting a package setting
        :return: Query for inserting a package setting
        :rtype: str
        """
        return "INSERT OR IGNORE INTO package_settings (package, id, type, visible, value, label, definition) " \
               "VALUES (?, ?, ?, ?, ?, ?, ?) "

    def get_single_provider(self, provider_name, package):
        """
        Fetches a single provider from the database
        :param provider_name: Name of provider
        :type provider_name: str
        :param package: Name of provider package
        :type package: str
        :return: Provider record
        :rtype: dict
        """
        return self.execute_sql("SELECT * FROM providers WHERE provider_name=? AND package=?",
                                (provider_name, package)).fetchone()

    def get_single_package(self, package_name):
        """
        Fetches a single package details from the database
        :param provider_name: Name of package
        :type provider_name: str
        :return: Package record
        :rtype: dict
        """
        return self.execute_sql("SELECT * FROM packages WHERE pack_name=?", (package_name,)).fetchone()

    def get_providers(self):
        """
        Returns all providers in the database
        :return: List of all provider records
        :rtype: list
        """
        return self.execute_sql("SELECT * FROM providers").fetchall()

    def get_provider_packages(self):
        """
        Returns all packages in the database
        :return: List of all package records
        :rtype: list
        """
        return self.execute_sql("SELECT * FROM packages").fetchall()

    def add_provider_package(self, pack_name, author, remote_meta, version, services):
        """
        Add a provider package to the database
        :param pack_name: Name of package
        :type pack_name: str
        :param author: Author of package
        :type author: str
        :param remote_meta: Url to remote meta.json file
        :type remote_meta: str
        :param version: Version of package
        :type version: str
        :param services: Comma seperated list of all available services
        :type services: str
        :return: None
        :rtype: None
        """
        self.execute_sql(self.package_insert_query, (pack_name, author, remote_meta, version, services))

    def remove_provider_package(self, pack_name):
        """
        Deletes the record for a provider package and all it's providers
        :param pack_name: Name of package
        :type pack_name: str
        :return: None
        :rtype: None
        """
        self.execute_sql(["DELETE FROM packages WHERE pack_name=?",
                          "DELETE FROM providers WHERE package=?"],
                         (pack_name,))

    def add_provider(self, provider_name, package, status, language, provider_type):
        """
        Add a provider to the database
        :param provider_name: Name of provider
        :type provider_name: str
        :param package: Name of package
        :type package: str
        :param status: Status to set for provider (enabled/disabled)
        :type status: str
        :param language: language the provider supplies
        :type language: str
        :param provider_type: Type of source provider provides (hoster,torrent,adaptive)
        :type provider_type: str
        :return: None
        :rtype: None
        """
        self.execute_sql(self.provider_insert_query, (provider_name, package, status, language, provider_type))

    def adjust_provider_status(self, provider_name, package_name, state):
        """
        Change status of provider
        :param provider_name: Name of provider
        :type provider_name: str
        :param package_name: Name of providers package
        :type package_name: str
        :param state: Value to set, (enabled,disabled)
        :type state: str
        :return: None
        :rtype: None
        """
        self.execute_sql("UPDATE providers SET status=? WHERE provider_name=? AND package=?",
                         (state, provider_name, package_name))

    def remove_individual_provider(self, provider_name, package_name):
        """
        Removes the record of a provider from the database
        :param provider_name: name of provider
        :type provider_name: str
        :param package_name: name of package
        :type package_name: str
        :return: none
        :rtype: None
        """
        self.execute_sql("DELETE FROM providers WHERE provider_name=? AND package=?", (provider_name, package_name))

    def remove_package_providers(self, package_name):
        """
        Remove all providers for a given package
        :param package_name: Name of package
        :type package_name: str
        :return: None
        :rtype: None
        """
        self.execute_sql("DELETE FROM providers WHERE package=?", (package_name,))

    def _set_package_setting(self, package_name, setting_id, value):
        """
        Update value for a package setting
        :param package_name: Name of package
        :type package_name: str
        :param setting_id: Id of setting
        :type setting_id: str
        :param value: Value to set to the database
        :type value: any
        :return: None
        :rtype: None
        """
        self.execute_sql("UPDATE package_settings SET value=? WHERE package=? and id=?",
                         (value, package_name, setting_id))

    def _get_package_setting(self, package_name, setting_id):
        return self.execute_sql("SELECT type, value FROM package_settings WHERE package=? and id=?",
                                (package_name, setting_id)).fetchone()
