# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import sqlite3
import types
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from functools import wraps

import mysql.connector
import xbmcvfs
from requests import Response

from resources.lib.common import tools
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    pickletype = buffer  # noqa: F821  pylint: disable=undefined-variable
except NameError:
    pickletype = bytes


def _handle_single_item_or_list(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if isinstance(args[-1], (list, types.GeneratorType)):
            return [func(*args[:-1] + (i,), **kwargs) for i in args[-1]]
        return func(*args, **kwargs)

    return wrapper


@_handle_single_item_or_list
def _dumps(obj):
    """Pickling method.

    :param obj:Object to be pickled
    :type obj:any
    :return:Bytes with the pickled content
    :rtype:bytes
    """
    if obj is None:
        return None

    return tuple(sqlite3.Binary(pickle.dumps(i, protocol=pickle.HIGHEST_PROTOCOL))
                 if isinstance(i, PICKLE_TYPES) else i for i in obj)


def _loads(value):
    """ Depickling method.

    :param value:Bytes with the pickled object
    :type value:str|bytes
    :return:Depickled value
    :rtype:any
    """
    try:
        if g.PYTHON3:
            return pickle.loads(value) if isinstance(value, pickletype) else value
        else:
            return pickle.loads(str(value)) if isinstance(value, pickletype) else value
    except pickle.UnpicklingError:
        return value


PICKLE_TYPES = (
    list,
    set,
    dict,
    tuple,
    Response
)


class Database(object):
    def __init__(self, db_file, database_layout):
        self._db_file = db_file
        self._database_layout = database_layout
        self._integrity_check_db()

    # region DatabaseSchema
    # region private methods
    def _create_tables(self, connection):
        for table_name, data in self._database_layout.items():
            self._create_table(connection, table_name, data)
        return connection

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

    def _integrity_check_db(self):
        db_file_checksum = tools.md5_hash(self._database_layout)
        try:
            with GlobalLock(self.__class__.__name__, True, db_file_checksum):
                if xbmcvfs.exists(self._db_file) and g.read_all_text("{}.md5".format(self._db_file)) == db_file_checksum:
                    return
                g.log(
                    "Integrity checked failed - {} - {} - rebuilding db".format(
                        self._db_file, db_file_checksum
                    )
                )
                self.rebuild_database()
                g.write_all_text("{}.md5".format(self._db_file), db_file_checksum)
        except RanOnceAlready:
            return

    # endregion

    # region public methods
    def rebuild_database(self):
        g.log("Rebuilding database: {}".format(self._db_file))
        with SQLiteConnection(self._db_file) as sqlite:
            with sqlite.transaction():
                database_schema = sqlite._connection.execute(
                    "SELECT m.name from sqlite_master m where type = 'table'"
                ).fetchall()
            sqlite._connection.execute("PRAGMA foreign_keys = OFF")
            for q in ["DROP TABLE IF EXISTS [{}]".format(t["name"]) for t in database_schema]:
                sqlite._connection.execute(q)

            self._create_tables(sqlite._connection)

    def fetchall(self, query, data=None):
        with SQLiteConnection(self._db_file) as connection:
            return connection.fetchall(query, data)

    def fetchone(self, query, data=None):
        with SQLiteConnection(self._db_file) as connection:
            return connection.fetchone(query, data)

    def execute_sql(self, query, data=None):
        with SQLiteConnection(self._db_file) as connection:
            return connection.execute_sql(query, data)

    def create_temp_table(self, table_name, columns):
        return TempTable(self, table_name, columns)

    # endregion


class _connection:
    __metaclass__ = ABCMeta

    def __init__(self, keep_alive=False):
        self._keep_alive = keep_alive
        self._connection = None
        self._cursor = None

    def __enter__(self):
        self._connection = self._create_connection()
        self._cursor = self._create_cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()
        if not self._keep_alive:
            self._connection.close()

    @abstractmethod
    def _create_connection(self):
        pass

    @abstractmethod
    def _create_cursor(self):
        pass

    @contextmanager
    def smart_transaction(self, query):
        no_transaction_keywords = ["select ", "vacuum"]

        if isinstance(query, list) and any(
                k for k in no_transaction_keywords if any(
                    q for q in query if q[:10].lstrip().lower().startswith(k)
                )
        ) or not isinstance(query, list) and any(
            k for k in no_transaction_keywords if query[:10].lstrip().lower().startswith(k)
        ):
            yield
        else:
            yield self.transaction()

    @contextmanager
    def transaction(self):
        self._cursor.execute('BEGIN')
        try:
            yield self._cursor
        except BaseException as be:
            self._connection.rollback()
            if isinstance(be, Exception):
                raise
        else:
            self._connection.commit()

    def fetchall(self, query, data=None):
        return self._execute_query(_dumps(data), "fetchall", query)

    def fetchone(self, query, data=None):
        return self._execute_query(_dumps(data), "fetchone", query)

    def execute_sql(self, query, data=None):
        return self._execute_query(_dumps(data), None, query)

    @_handle_single_item_or_list
    def _execute_query(self, data, result_method, query):
        try:
            with self.smart_transaction(query):
                if isinstance(data, list) or isinstance(data, types.GeneratorType):
                    self._cursor.executemany(query, data)
                elif data:
                    self._cursor.execute(query, data)
                else:
                    self._cursor.execute(query)

                if result_method == "fetchone":
                    return self._cursor.fetchone()
                elif result_method == "fetchall":
                    return self._cursor.fetchall()
                else:
                    return self._cursor
        except Exception:
            self._log_error(query, data)
            raise

    @staticmethod
    def _log_error(query, data):
        if data:
            g.log("{}\n{}".format(query, data), "error")
        else:
            g.log(query, "error")


class SQLiteConnection(_connection):
    def __init__(self, path):
        super(SQLiteConnection, self).__init__()
        self.path = path
        self._create_db_path()

    def _create_connection(self):
        retries = 0
        while not retries == 50 and not g.abort_requested():
            import sqlite3
            try:
                connection = sqlite3.connect(  # pylint: disable=no-member
                    self.path,
                    timeout=30,
                    detect_types=sqlite3.PARSE_DECLTYPES,  # pylint: disable=no-member
                    isolation_level=None,
                    check_same_thread=False
                )
                self._set_connection_settings(connection)
                return connection
            except sqlite3.OperationalError as error:  # pylint: disable=no-member
                if "database is locked" in g.UNICODE(error):
                    g.log(
                        "database is locked waiting: {}".format(self.path),
                        "warning",
                    )
                    g.wait_for_abort(0.1)
            retries += 1

    def _create_cursor(self):
        return self._connection.cursor()

    @staticmethod
    def _set_connection_settings(connection):
        connection.row_factory = lambda c, r: dict([(col[0], _loads(r[idx])) for idx, col in enumerate(c.description)])
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = normal")
        connection.execute("PRAGMA temp_store = memory")
        connection.execute("PRAGMA mmap_size = 30000000000")
        connection.execute("PRAGMA page_size = 32768")  # no-translate

    def _create_db_path(self):
        if not xbmcvfs.exists(os.path.dirname(self.path)):
            xbmcvfs.mkdirs(os.path.dirname(self.path))


class MySqlConnection(_connection):
    def __init__(self, config):
        super(MySqlConnection, self).__init__(True)
        self.config = {
            'user': config.get("user"),
            'password': config.get("password"),
            'host': config.get("host"),
            'port': config.get("port"),
            'database': config.get("database"),
            'autocommit': True,
            'charset': 'utf8',
            'use_unicode': True
        }

    def _create_connection(self):
        return mysql.connector.connect(**self.config)

    def _create_cursor(self):
        return self._connection.cursor(cursor_class=MySQLCursorDict)


class MySQLCursorDict(mysql.connector.connection.MySQLCursor):
    """
    Cursor fetching rows as dictionaries.

    The fetch methods of this class will return dictionaries instead of tuples.
    Each row is a dictionary that looks like:
        row = {
            "col1": value1,
            "col2": value2
        }
    """
    ERR_NO_RESULT_TO_FETCH = "No result set to fetch from"

    def _row_to_python(self, rowdata, desc=None):
        """Convert a MySQL text result row to Python types

        Returns a dictionary.
        """
        row = rowdata

        if row:
            return dict(zip(self.column_names, row))

        return None

    def fetchone(self):
        """Returns next row of a query result set
        """
        row = self._fetch_row()
        if row:
            return self._row_to_python(row, self.description)
        return None

    def fetchall(self):
        """Returns all rows of a query result set
        """
        if not self._have_unread_result():
            raise mysql.connector.errors.InterfaceError(self.ERR_NO_RESULT_TO_FETCH)
        (rows, eof) = self._connection.get_rows()
        if self._nextrow[0]:
            rows.insert(0, self._nextrow[0])
        res = []
        for row in rows:
            res.append(self._row_to_python(row, self.description))
        self._handle_eof(eof)
        rowcount = len(rows)
        if rowcount >= 0 and self._rowcount == -1:
            self._rowcount = 0
        self._rowcount += rowcount
        return res


class TempTable:
    def __init__(self, database, table_name, columns):
        self.database = database
        self.columns = columns
        self.table_name = table_name

    def __enter__(self):
        self._drop_table()
        self._create_table()
        return self

    def insert_data(self, data):
        columns = ','.join("[{}]".format(c) for c in self.columns)
        placeholder = ','.join('?' for _ in self.columns)

        self.database.execute_sql('INSERT OR IGNORE INTO [{}] ({}) VALUES ({})'
                                  .format(self.table_name, columns, placeholder),
                                  (tuple(row[i] for i in self.columns) for row in data))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._drop_table()

    def _create_table(self):
        self.database.execute_sql('CREATE TABLE IF NOT EXISTS [{}] ({})'
                                  .format(self.table_name,
                                          ','.join("[{}] VARCHAR".format(c) for c in self.columns)))

    def _drop_table(self):
        self.database.execute_sql("drop table if exists [{}]".format(self.table_name))
