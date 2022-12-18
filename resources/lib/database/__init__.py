import os
import pickle
import sqlite3
import types
from abc import ABCMeta
from abc import abstractmethod
from contextlib import contextmanager
from functools import wraps

import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g

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
    return tuple(
        pickle.dumps(i, protocol=pickle.HIGHEST_PROTOCOL) if i.__class__.__name__ in PICKLE_TYPES else i for i in obj
    )


def _loads(value):
    """Depickling method.

    :param value:Bytes with the pickled object
    :type value:str|bytes
    :return:Depickled value
    :rtype:any
    """
    try:
        return pickle.loads(value) if isinstance(value, pickletype) else value
    except pickle.UnpicklingError:
        return value


PICKLE_TYPES = {"list", "set", "dict", "tuple", "Response"}


class Database:
    def __init__(self, db_file, database_layout):
        self._db_file = db_file
        self._database_layout = database_layout
        self._integrity_check_db()
        self._connection = SQLiteConnection(self._db_file)

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

        connection.execute(f"CREATE TABLE IF NOT EXISTS [{table_name}]({','.join(table_data)})")
        indices = data.get("indices")
        if indices and len(indices) > 0:
            for index_name, columns in indices:
                connection.execute(f"CREATE INDEX IF NOT EXISTS [{index_name}] ON {table_name}({','.join(columns)})")
        default_seed = data["default_seed"]
        if not default_seed or len(default_seed) == 0:
            return
        query = f"""
            INSERT OR IGNORE INTO [{table_name}] ({','.join(data['columns'])})
            VALUES ({','.join(['?' for _ in data['columns']])})
            """

        for row_values in (tuple(row) for row in data["default_seed"]):
            connection.execute(query, row_values)

    @staticmethod
    def _create_column_expression(column_name, column_declaration):
        return f"{column_name} {' '.join(column_declaration)}"

    def _integrity_check_db(self):
        db_file_checksum = tools.md5_hash(self._database_layout)
        try:
            with GlobalLock(self.__class__.__name__, True, db_file_checksum):
                if xbmcvfs.exists(self._db_file) and g.read_all_text(f"{self._db_file}.md5") == db_file_checksum:
                    return
                g.log(f"Integrity checked failed - {self._db_file} - {db_file_checksum} - rebuilding db")
                self.rebuild_database()
                g.write_all_text(f"{self._db_file}.md5", db_file_checksum)
        except RanOnceAlready:
            return

    # endregion

    # region public methods
    def rebuild_database(self):
        g.log(f"Rebuilding database: {self._db_file}")
        with SQLiteConnection(self._db_file) as sqlite:
            with sqlite.transaction() as transaction:
                transaction.execute("PRAGMA writable_schema = ON")
                transaction.execute("DELETE FROM sqlite_master WHERE type IN ('table', 'index', 'trigger')")
                transaction.execute("PRAGMA writable_schema = OFF")

            with sqlite.cursor() as cursor:
                cursor.execute("VACUUM")

            with sqlite.transaction():
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

    def create_temp_table(self, table_name, columns, primary_key=None):
        return TempTable(self, table_name, columns, primary_key)

    # endregion


class _connection(metaclass=ABCMeta):
    def __init__(self, keep_alive=False):
        self._keep_alive = keep_alive
        self._connection = None

    def __enter__(self):
        self.connect()
        if not self._connection:
            g.log("Database _create_connection() failed!", "error")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._keep_alive:
            self.close()

    def __del__(self):
        self.close()

    def connect(self):
        if not self._connection:
            self._connection = self._create_connection()

    def close(self):
        if self._connection:
            self._connection.close()

    @abstractmethod
    def _create_connection(self):
        pass

    @abstractmethod
    def _create_cursor(self):
        pass

    @contextmanager
    def cursor(self):
        self.connect()
        cursor = self._connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def smart_transaction(self, query):
        no_transaction_keywords = ["select ", "vacuum"]

        if (
            isinstance(query, list)
            and any(
                k for k in no_transaction_keywords if any(q for q in query if q[:10].lstrip().lower().startswith(k))
            )
            or not isinstance(query, list)
            and any(k for k in no_transaction_keywords if query[:10].lstrip().lower().startswith(k))
        ):
            with self.cursor() as cursor:
                yield cursor
        else:
            with self.transaction() as transaction:
                yield transaction

    @contextmanager
    def transaction(self):
        with self.cursor() as cursor:
            cursor.execute("BEGIN")
            try:
                yield cursor
            except BaseException as be:
                try:
                    cursor.execute("ROLLBACK")
                finally:
                    if isinstance(be, Exception):
                        raise
            else:
                cursor.execute("COMMIT")

    def fetchall(self, query, data=None):
        return self._execute_query(_dumps(data), "fetchall", query)

    def fetchone(self, query, data=None):
        return self._execute_query(_dumps(data), "fetchone", query)

    def execute_sql(self, query, data=None):
        return self._execute_query(_dumps(data), None, query)

    @abstractmethod
    def _retry_handler(self, exception):
        raise exception

    @_handle_single_item_or_list
    def _execute_query(self, data, result_method, query, retries=50):
        retry_count = 0
        while retry_count <= retries:
            try:
                with self.smart_transaction(query) as cursor:
                    if isinstance(data, (list, types.GeneratorType)):
                        cursor.executemany(query, data)
                    elif data:
                        cursor.execute(query, data)
                    else:
                        cursor.execute(query)

                    if result_method == "fetchone":
                        return cursor.fetchone()
                    elif result_method == "fetchall":
                        return cursor.fetchall()
                    else:
                        return cursor
            except Exception as e:
                try:
                    self._retry_handler(e)
                    retry_count += 1
                except Exception:
                    self._log_error(query, data)
                    raise

    @staticmethod
    def _log_error(query, data):
        if data:
            g.log(f"{query}\n{data}", "error")
        else:
            g.log(query, "error")


class SQLiteConnection(_connection):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self._create_db_path()

    def _create_connection(self):
        retries = 0
        exception = None
        while retries != 50 and not g.abort_requested():
            try:
                connection = sqlite3.connect(  # pylint: disable=no-member
                    self.path,
                    timeout=30,
                    detect_types=sqlite3.PARSE_DECLTYPES,  # pylint: disable=no-member
                    isolation_level=None,
                    check_same_thread=False,
                )
                self._set_connection_settings(connection)
                return connection
            except Exception as error:
                self._retry_handler(error)
                exception = error
            retries += 1
        # If we reach here we have exceeded our retries so just raise the last exception
        g.log(f"Unable to connect to database '{self.path}' {exception=}", "error")
        raise exception

    def _retry_handler(self, exception):
        if isinstance(exception, sqlite3.OperationalError) and (  # pylint: disable=no-member
            "database is locked" in str(exception) or "unable to open database" in str(exception)
        ):
            g.log(
                f"database is locked waiting: {self.path}",
                "warning",
            )
            g.wait_for_abort(0.1)
        else:
            super()._retry_handler(exception)

    def _create_cursor(self):
        super()._create_cursor()
        return self._connection.cursor()

    @staticmethod
    def _set_connection_settings(connection):
        connection.row_factory = lambda c, r: {
            col[0]: _loads(r[idx]) if isinstance(r[idx], pickletype) else r[idx]
            for idx, col in enumerate(c.description)
        }
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA page_size = 32768")  # no-translate
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = normal")
        connection.execute("PRAGMA temp_store = memory")
        connection.execute("PRAGMA mmap_size = 30000000000")

    def _create_db_path(self):
        if not xbmcvfs.exists(os.path.dirname(self.path)):
            xbmcvfs.mkdirs(os.path.dirname(self.path))


class MySqlConnection(_connection):
    from functools import cached_property

    def __init__(self, config):
        super().__init__(keep_alive=True)
        self.config = {
            'user': config.get("user"),
            'password': config.get("password"),
            'host': config.get("host"),
            'port': config.get("port"),
            'database': config.get("database"),
            'autocommit': True,
            'charset': 'utf8',
            'use_unicode': True,
        }

    @cached_property
    def mysql(self):
        import mysql.connector

        return mysql.connector

    @cached_property
    def MySQLCursorDict(self):
        from resources.lib.database.mysql_cursor_dict import MySQLCursorDict

        return MySQLCursorDict

    def _create_connection(self):
        return self.mysql.connect(**self.config)

    def _create_cursor(self):
        return self._connection.cursor(cursor_class=self.MySQLCursorDict)

    def _retry_handler(self, exception):
        super()._retry_handler(exception)


class TempTable:
    def __init__(self, database, table_name, columns, primary_key=None):
        self.database = database
        self.columns = columns
        self.table_name = table_name
        self.primary_key = primary_key

    def __enter__(self):
        self._drop_table()
        self._create_table()
        return self

    def insert_data(self, data):
        columns = ",".join(f"[{c}]" for c in self.columns)
        placeholder = ",".join("?" for _ in self.columns)

        self.database.execute_sql(
            f"INSERT OR IGNORE INTO [{self.table_name}] ({columns}) VALUES ({placeholder})",
            (tuple(row[i] for i in self.columns) for row in data),
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._drop_table()

    def _create_table(self):
        self.database.execute_sql(
            f"""
            CREATE TABLE IF NOT EXISTS [{self.table_name}] ({",".join(f"[{c}] VARCHAR" for c in self.columns)}{
                f',PRIMARY KEY ({self.primary_key}), UNIQUE ({self.primary_key})' if self.primary_key else ''
            })
            """
        )

    def _drop_table(self):
        self.database.execute_sql(f"drop table if exists [{self.table_name}]")
