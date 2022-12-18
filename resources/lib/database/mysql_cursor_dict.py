import mysql.connector


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
        return dict(zip(self.column_names, row)) if (row := rowdata) else None

    def fetchone(self):
        """Returns next row of a query result set"""
        if row := self._fetch_row():
            return self._row_to_python(row, self.description)
        return None

    def fetchall(self):
        """Returns all rows of a query result set"""
        if not self._have_unread_result():
            from mysql.connector.errors import InterfaceError

            raise InterfaceError(self.ERR_NO_RESULT_TO_FETCH)
        (rows, eof) = self._connection.get_rows()
        if self._nextrow[0]:
            rows.insert(0, self._nextrow[0])
        res = [self._row_to_python(row, self.description) for row in rows]
        self._handle_eof(eof)
        rowcount = len(rows)
        if rowcount >= 0 and self._rowcount == -1:
            self._rowcount = 0
        self._rowcount += rowcount
        return res
