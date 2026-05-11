"""
mysql_connector.py
──────────────────
MySQL / MariaDB implementation of BaseConnector.

Uses `mysql-connector-python`. Install with:
    pip install mysql-connector-python

Accepts either a DSN string or explicit connection kwargs:
    DSN:    mysql://user:password@host:3306/dbname
    kwargs: host, port, user, password, database
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .base import BaseConnector


def _require_mysql():
    try:
        import mysql.connector
        return mysql.connector
    except ImportError:
        raise ImportError(
            "MySQL support requires mysql-connector-python. "
            "Install it with:  pip install mysql-connector-python"
        )


def _parse_dsn(dsn: str) -> Dict[str, Any]:
    """
    Parse a mysql:// DSN into a kwargs dict for mysql.connector.connect().

    Example:
        mysql://user:pass@localhost:3306/mydb
        → {"host": "localhost", "port": 3306, "user": "user",
           "password": "pass", "database": "mydb"}
    """
    parsed = urlparse(dsn)
    kwargs: Dict[str, Any] = {}

    if parsed.hostname:
        kwargs["host"] = parsed.hostname
    if parsed.port:
        kwargs["port"] = parsed.port
    if parsed.username:
        kwargs["user"] = parsed.username
    if parsed.password:
        kwargs["password"] = parsed.password
    # Strip leading slash from path to get db name
    db = (parsed.path or "").lstrip("/")
    if db:
        kwargs["database"] = db

    return kwargs


class MySQLConnector(BaseConnector):
    """
    Connector for MySQL and MariaDB databases.

    Parameters
    ----------
    dsn : str
        A MySQL DSN string, e.g. ``mysql://user:pass@localhost:3306/mydb``
    **kwargs :
        Alternatively, pass explicit connection kwargs
        (host, port, user, password, database). These take precedence over DSN.
    """

    def __init__(self, dsn: str = "", **kwargs) -> None:
        _require_mysql()  # Fail fast if driver not installed
        # Merge DSN-parsed values with explicit kwargs (explicit wins)
        self._conn_kwargs = {**_parse_dsn(dsn), **kwargs} if dsn else kwargs

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _connect(self):
        mysql_connector = _require_mysql()
        return mysql_connector.connect(**self._conn_kwargs)

    @property
    def _database(self) -> str:
        return self._conn_kwargs.get("database", "")

    # ── BaseConnector primitives ──────────────────────────────────────────────

    def test_connection(self) -> bool:
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    def get_tables(self) -> List[str]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT TABLE_NAME
                FROM   information_schema.TABLES
                WHERE  TABLE_SCHEMA = %s
                  AND  TABLE_TYPE   = 'BASE TABLE'
                ORDER  BY TABLE_NAME;
                """,
                (self._database,),
            )
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_columns(self, table: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.cursor()

            # Column metadata
            cur.execute(
                """
                SELECT COLUMN_NAME,
                       DATA_TYPE,
                       IS_NULLABLE,
                       COLUMN_DEFAULT,
                       COLUMN_KEY
                FROM   information_schema.COLUMNS
                WHERE  TABLE_SCHEMA = %s
                  AND  TABLE_NAME   = %s
                ORDER  BY ORDINAL_POSITION;
                """,
                (self._database, table),
            )
            return [
                {
                    "name":    row[0],
                    "type":    row[1].upper(),
                    "notnull": row[2] == "NO",
                    "default": row[3],
                    "pk":      row[4] == "PRI",
                }
                for row in cur.fetchall()
            ]
        finally:
            conn.close()

    def get_foreign_keys(self, table: str) -> List[Dict[str, str]]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT kcu.COLUMN_NAME,
                       kcu.REFERENCED_TABLE_NAME,
                       kcu.REFERENCED_COLUMN_NAME
                FROM   information_schema.KEY_COLUMN_USAGE kcu
                JOIN   information_schema.TABLE_CONSTRAINTS tc
                       ON  tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                       AND tc.TABLE_SCHEMA    = kcu.TABLE_SCHEMA
                       AND tc.TABLE_NAME      = kcu.TABLE_NAME
                WHERE  tc.CONSTRAINT_TYPE          = 'FOREIGN KEY'
                  AND  kcu.TABLE_SCHEMA            = %s
                  AND  kcu.TABLE_NAME              = %s
                  AND  kcu.REFERENCED_TABLE_NAME IS NOT NULL;
                """,
                (self._database, table),
            )
            return [
                {
                    "from_col": row[0],
                    "to_table": row[1],
                    "to_col":   row[2],
                }
                for row in cur.fetchall()
            ]
        finally:
            conn.close()

    def get_sample_values(
        self,
        table: str,
        columns: List[Dict[str, Any]],
        sample_size: int = 10,
        distinct_limit: int = 5,
    ) -> Dict[str, List[str]]:
        sample_values: Dict[str, List[str]] = {col["name"]: [] for col in columns}
        if not columns:
            return sample_values

        conn = self._connect()
        try:
            cur = conn.cursor()
            col_names_quoted = ", ".join(f"`{c['name']}`" for c in columns)
            cur.execute(
                f"SELECT {col_names_quoted} FROM `{table}` LIMIT %s;",
                (sample_size,),
            )
            rows = cur.fetchall()

            for i, col in enumerate(columns):
                seen: List[str] = []
                for row in rows:
                    val = row[i]
                    if val is not None and str(val) not in seen:
                        seen.append(str(val))
                    if len(seen) >= distinct_limit:
                        break
                sample_values[col["name"]] = seen
        except Exception:
            pass
        finally:
            conn.close()

        return sample_values

    def get_row_count(self, table: str) -> int:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM `{table}`;")
            return cur.fetchone()[0]
        except Exception:
            return 0
        finally:
            conn.close()

    def execute_query(
        self,
        sql: str,
        limit: int = 500,
    ) -> Tuple[List[str], List[List[Any]]]:
        sql_stripped = sql.strip().rstrip(";")
        upper = sql_stripped.upper()

        # Auto-inject LIMIT for unbounded SELECT queries
        if upper.startswith("SELECT") and "LIMIT" not in upper:
            sql_to_run = f"{sql_stripped} LIMIT {limit};"
        else:
            sql_to_run = sql_stripped + ";"

        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(sql_to_run)
            col_names: List[str] = (
                [desc[0] for desc in cur.description]
                if cur.description else []
            )
            rows: List[List[Any]] = [list(row) for row in cur.fetchall()]
            return col_names, rows
        finally:
            conn.close()
