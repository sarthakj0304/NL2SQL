"""
base.py
───────
Abstract base class for all database connectors.

Every connector (SQLite, PostgreSQL, MySQL) must implement this interface.
The rest of the pipeline (schema_loader, sql_executor, db_connector) only
talks to this interface — never to a DB-specific driver directly.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseConnector(ABC):
    """
    Abstract database connector.

    Subclasses implement the driver-specific introspection and execution
    methods. The `extract_schema()` method is provided here and orchestrates
    all the abstract methods, so subclasses only need to implement the
    primitives.
    """

    # ── Primitives (must be implemented by subclasses) ────────────────────────

    @abstractmethod
    def get_tables(self) -> List[str]:
        """Return names of all user-accessible tables in the database."""

    @abstractmethod
    def get_columns(self, table: str) -> List[Dict[str, Any]]:
        """
        Return column metadata for `table`.

        Each dict must contain:
            name    : str   — column name
            type    : str   — data type (e.g. "TEXT", "INTEGER", "VARCHAR")
            pk      : bool  — True if part of the primary key
            notnull : bool  — True if the column has a NOT NULL constraint
            default : Any   — default value, or None
        """

    @abstractmethod
    def get_foreign_keys(self, table: str) -> List[Dict[str, str]]:
        """
        Return foreign key metadata for `table`.

        Each dict must contain:
            from_col : str — local column name
            to_table : str — referenced table name
            to_col   : str — referenced column name
        """

    @abstractmethod
    def get_sample_values(
        self,
        table: str,
        columns: List[Dict[str, Any]],
        sample_size: int = 10,
        distinct_limit: int = 5,
    ) -> Dict[str, List[str]]:
        """
        Return up to `distinct_limit` non-null sample values per column.

        Returns a dict {col_name: [val1, val2, ...]}.
        """

    @abstractmethod
    def get_row_count(self, table: str) -> int:
        """Return the total number of rows in `table`."""

    @abstractmethod
    def execute_query(
        self,
        sql: str,
        limit: int = 500,
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Execute a SQL query and return (column_names, rows).

        - Should automatically inject LIMIT for unbounded SELECT queries.
        - Should raise a driver-native exception on failure.
        """

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Perform a lightweight connectivity check.
        Returns True if the database is reachable, False otherwise.
        """

    # ── Composite (provided — subclasses inherit) ─────────────────────────────

    def extract_schema(self) -> Dict[str, Any]:
        """
        Build and return the full schema dict for the connected database.

        Structure:
        {
            "table_name": {
                "columns":      [{name, type, pk, notnull, default}, ...],
                "foreign_keys": [{from_col, to_table, to_col}, ...],
                "sample_values": {col_name: ["val1", "val2", ...]},
                "row_count":    int,
            }
        }

        Subclasses rarely need to override this — just implement the
        abstract primitives above.
        """
        schema: Dict[str, Any] = {}

        for table in self.get_tables():
            columns = self.get_columns(table)
            foreign_keys = self.get_foreign_keys(table)
            sample_values = self.get_sample_values(table, columns)
            row_count = self.get_row_count(table)

            schema[table] = {
                "columns":       columns,
                "foreign_keys":  foreign_keys,
                "sample_values": sample_values,
                "row_count":     row_count,
            }

        return schema
