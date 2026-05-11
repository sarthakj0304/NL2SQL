"""
sqlite_connector.py
───────────────────
SQLite implementation of BaseConnector.

Uses the stdlib `sqlite3` module — no extra dependencies required.
Introspection is done via SQLite's PRAGMA commands and the sqlite_master
system table.
"""

import sqlite3
from typing import Any, Dict, List, Tuple

from .base import BaseConnector


class SQLiteConnector(BaseConnector):
    """
    Connector for local SQLite database files.

    Parameters
    ----------
    db_path : str
        Absolute or relative path to the `.db` / `.sqlite` file.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── BaseConnector primitives ──────────────────────────────────────────────

    def test_connection(self) -> bool:
        try:
            conn = self._connect()
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    def get_tables(self) -> List[str]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_columns(self, table: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table});")
            return [
                {
                    "name":    col[1],
                    "type":    (col[2] or "TEXT").upper(),
                    "notnull": bool(col[3]),
                    "default": col[4],
                    "pk":      bool(col[5]),
                }
                for col in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_foreign_keys(self, table: str) -> List[Dict[str, str]]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA foreign_key_list({table});")
            return [
                {
                    "from_col": fk[3],
                    "to_table": fk[2],
                    "to_col":   fk[4],
                }
                for fk in cursor.fetchall()
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
            cursor = conn.cursor()
            col_names_quoted = ", ".join(f'"{c["name"]}"' for c in columns)
            cursor.execute(f'SELECT {col_names_quoted} FROM "{table}" LIMIT {sample_size};')
            rows = cursor.fetchall()

            for col in columns:
                seen: List[str] = []
                for row in rows:
                    val = row[col["name"]]
                    if val is not None and str(val) not in seen:
                        seen.append(str(val))
                    if len(seen) >= distinct_limit:
                        break
                sample_values[col["name"]] = seen
        except Exception:
            pass  # Non-critical
        finally:
            conn.close()

        return sample_values

    def get_row_count(self, table: str) -> int:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM "{table}";')
            return cursor.fetchone()[0]
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
            cursor = conn.cursor()
            cursor.execute(sql_to_run)
            col_names: List[str] = (
                [desc[0] for desc in cursor.description]
                if cursor.description else []
            )
            rows: List[List[Any]] = [list(row) for row in cursor.fetchall()]
            return col_names, rows
        finally:
            conn.close()
