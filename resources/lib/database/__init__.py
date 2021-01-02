# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import sqlite3
import types
from sqlite3 import InterfaceError

import xbmc
import xbmcvfs
from requests import Response

from resources.lib.common import tools
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g

try:
    import cPickle as pickle
except:
    import pickle


class Database(object):
    def __init__(self, db_file, database_layout, threading_lock):
        self._db_file = db_file
        self._create_db_path()
        self._monitor = xbmc.Monitor()
        self._exit = False
        self._database_layout = database_layout
        self._threading_lock = threading_lock
        self._register_pickler_adapters()
        self._integrity_check_db()

    # region private methods
    def _register_pickler_adapters(self):
        sqlite3.register_adapter(list, self._dumps)
        sqlite3.register_adapter(set, self._dumps)
        sqlite3.register_adapter(dict, self._dumps)
        sqlite3.register_adapter(tuple, self._dumps)
        sqlite3.register_adapter(Response, self._dumps)
        sqlite3.register_converter(str("PICKLE"), self._loads)
        sqlite3.register_adapter(bool, int)
        sqlite3.register_converter(str("BOOLEAN"), lambda v: bool(int(v)))

    @staticmethod
    def _dumps(obj):
        """Pickling method.

        :param obj:Object to be pickled
        :type obj:any
        :return:Bytes with the pickled content
        :rtype:bytes
        """
        if obj is None:
            return None
        retries = 0
        while retries < 2:
            try:
                return sqlite3.Binary(
                    pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
                )
            except RuntimeError:
                retries += 1
                continue

    @staticmethod
    def _loads(value):
        """ Depickling method.

        :param value:Bytes with the pickled object
        :type value:str|bytes
        :return:Depickled value
        :rtype:any
        """
        if value is None:
            return None

        retries = 0
        while retries < 2:
            try:
                return pickle.loads(g.encode_py2(value))
            except pickle.UnpicklingError:
                return None
            except RuntimeError:
                retries += 1
                continue

    def _create_tables(self, connection):
        for table_name, data in self._database_layout.items():
            self._create_table(connection, table_name, data)

    def _create_table(self, connection, table_name, data):
        table_data = [
            self._create_column_expression(column_name, column_declaration)
            for column_name, column_declaration in data["columns"].items()
        ]
        table_data.extend(data["table_constraints"])

        connection.execute(
            "CREATE TABLE IF NOT EXISTS [{}]({})".format(
                table_name, (",".join(table_data))
            )
        )
        if len(data["default_seed"]) == 0:
            return
        query = "INSERT OR IGNORE INTO [{}] ({}) VALUES ({})".format(
            table_name,
            ",".join(data["columns"].keys()),
            ",".join(["?" for i in data["columns"].keys()]),
        )
        for row_values in (tuple(row) for row in data["default_seed"]):
            connection.execute(query, row_values)

    @staticmethod
    def _create_column_expression(column_name, column_declaration):
        return "{} {}".format(column_name, " ".join(column_declaration))

    def __del__(self):
        if not self._exit:
            self.close()

    def _create_db_path(self):
        if not xbmcvfs.exists(os.path.dirname(self._db_file)):
            xbmcvfs.mkdirs(os.path.dirname(self._db_file))

    def _get_connection(self):
        try:
            connection = self.__create_connection()
            return connection
        except Exception:
            self._create_db_path()
            try:
                connection = self.__create_connection()
                self._create_tables(connection)
                connection.commit()
                return connection
            except Exception:
                self.close()
                return None

    def __create_connection(self):
        connection = sqlite3.connect(
            self._db_file, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES
        )
        self._set_connection_settings(connection)
        return connection

    def _integrity_check_db(self):
        db_file_checksum = tools.md5_hash(self._database_layout)
        with GlobalLock(
            self.__class__.__name__, self._threading_lock, True, db_file_checksum
        ) as lock:
            if lock.runned_once():
                return
            if g.read_all_text("{}.md5".format(self._db_file)) == db_file_checksum:
                return
            g.log(
                "Integrity checked failed - {} - {} - rebuilding db".format(
                    self._db_file, db_file_checksum
                )
            )
            self.rebuild_database()
            g.write_all_text("{}.md5".format(self._db_file), db_file_checksum)

    @staticmethod
    def _set_connection_settings(connection):
        connection.row_factory = lambda c, r: dict(
            zip([col[0] for col in c.description], r)
        )
        connection.execute("PRAGMA foreign_keys = ON")
        connection.commit()

    @staticmethod
    def _execute_query(data, cursor, query):
        if isinstance(data, list) or isinstance(data, types.GeneratorType):
            result = cursor.executemany(query, data)
        elif data:
            result = cursor.execute(query, data)
        else:
            result = cursor.execute(query)
        return result

    # endregion

    # region public methods
    @staticmethod
    def chunkify_list_for_query(list_of_expressions):
        chunked_list = []
        while len(list_of_expressions) > 900:
            chunked_list.append(list_of_expressions[:900])
            del list_of_expressions[:900]
        chunked_list.append(list_of_expressions)
        return chunked_list

    def close(self):
        self._exit = True

    def rebuild_database(self):
        g.log("Rebuilding database: {}".format(self._db_file))
        database_schema = self.execute_sql(
            "SELECT m.name from sqlite_master m where type = 'table'"
        ).fetchall()

        self.execute_sql(
            ["DROP TABLE IF EXISTS [{}]".format(t["name"]) for t in database_schema]
        )
        self.execute_sql("VACUUM")
        with self._get_connection() as connection:
            self._create_tables(connection)

    def execute_sql(self, query, data=None):
        retries = 0
        self._register_pickler_adapters()
        monitor = xbmc.Monitor()
        with self._get_connection() as connection:
            while not retries == 50 and not monitor.abortRequested() and not self._exit:
                try:
                    if isinstance(query, list) or isinstance(
                        query, types.GeneratorType
                    ):
                        return [
                            self._execute_query(data, connection.cursor(), i)
                            for i in query
                        ]
                    return self._execute_query(data, connection.cursor(), query)
                except sqlite3.OperationalError as error:
                    if "database is locked" in str(error):
                        g.log(
                            "database is locked waiting: {}".format(self._db_file),
                            "warning",
                        )
                        monitor.waitForAbort(0.1)
                    else:
                        self._log_error(query, data)
                        raise
                except (RuntimeError, InterfaceError):
                    if retries >= 2:
                        self._log_error(query, data)
                        raise
                    monitor.waitForAbort(0.1)
                except:
                    self._log_error(query, data)
                    raise
                retries += 1
            connection.commit()
            return None

    @staticmethod
    def _log_error(query, data):
        if data:
            g.log("{}\n{}".format(query, data), "error")
        else:
            g.log(query, "error")

    # endregion
