"""
db_connector.py
───────────────
Backward-compatible shim.

All existing call sites (schema_loader, sql_executor, app.py) continue to
work without any changes. Internally, this module now delegates to the
active connector via connector_factory, which supports SQLite, PostgreSQL,
and MySQL.

Active connection state
───────────────────────
`_active_connector` holds the currently connected BaseConnector instance.
It is set by:
  - `set_connector(connector)`   — called by app.py after upload/connect
  - `set_sqlite(db_path)`        — convenience wrapper for SQLite
  - Falls back to DB_PATH/DB_TYPE from settings if not explicitly set.
"""

from typing import Any, Dict, List, Optional, Tuple

import config.settings as _settings
from database.connector_factory import get_connector
from database.connectors.base import BaseConnector


# ── Active connector registry ─────────────────────────────────────────────────

_active_connector: Optional[BaseConnector] = None


def set_connector(connector: BaseConnector) -> None:
    """Set the globally active connector (called by app.py on upload/connect)."""
    global _active_connector
    _active_connector = connector


def set_sqlite(db_path: str) -> None:
    """Convenience helper — set the active connector to a SQLite file."""
    set_connector(get_connector("sqlite", db_path=db_path))


def _get_active_connector() -> BaseConnector:
    """
    Return the active connector, initialising from settings if needed.
    """
    global _active_connector
    if _active_connector is None:
        db_type = getattr(_settings, "DB_TYPE", "sqlite")
        if db_type == "sqlite":
            db_path = getattr(_settings, "DB_PATH", "database/sample.db")
            _active_connector = get_connector("sqlite", db_path=db_path)
        else:
            dsn = getattr(_settings, "DB_DSN", "")
            schema = getattr(_settings, "DB_SCHEMA", "public")
            _active_connector = get_connector(db_type, dsn=dsn, schema=schema)
    return _active_connector


# ── Public API (backward-compatible signatures) ────────────────────────────────

def extract_schema(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract the full schema from the active (or specified SQLite) database.

    If `db_path` is provided, a temporary SQLite connector is used for that
    call only — the active connector is unchanged. This preserves backward
    compatibility with schema_loader.py which always passes db_path.
    """
    if db_path is not None:
        # Called with an explicit path → temporary SQLite connector
        connector = get_connector("sqlite", db_path=db_path)
        # Also update the active connector so it stays in sync
        set_connector(connector)
        return connector.extract_schema()

    return _get_active_connector().extract_schema()


def execute_query(
    db_path: Optional[str],
    sql: str,
    limit: int = 500,
) -> Tuple[List[str], List[List[Any]]]:
    """
    Execute a SQL query against the active (or specified SQLite) database.

    If `db_path` is provided and a SQLite connector is active, the path
    is used directly. For non-SQLite connectors the active connector is
    always used (db_path is ignored, only present for API compatibility).
    """
    # If a db_path is explicitly given, use a temporary SQLite connector for it
    if db_path is not None:
        active = _get_active_connector()
        from database.connectors.sqlite_connector import SQLiteConnector
        if isinstance(active, SQLiteConnector):
            return get_connector("sqlite", db_path=db_path).execute_query(sql, limit=limit)

    return _get_active_connector().execute_query(sql, limit=limit)


def get_table_names(db_path: Optional[str] = None) -> List[str]:
    """Return all table names. Backward-compatible wrapper."""
    if db_path is not None:
        return get_connector("sqlite", db_path=db_path).get_tables()
    return _get_active_connector().get_tables()


def get_column_names(db_path: str, table: str) -> List[str]:
    """Return column names for a specific table. Backward-compatible wrapper."""
    connector = get_connector("sqlite", db_path=db_path)
    return [col["name"] for col in connector.get_columns(table)]


def get_active_db_type() -> str:
    """Return the db_type string of the currently active connector."""
    active = _get_active_connector()
    from database.connectors.sqlite_connector import SQLiteConnector
    from database.connectors.postgres_connector import PostgresConnector
    from database.connectors.mysql_connector import MySQLConnector
    if isinstance(active, PostgresConnector):
        return "postgres"
    if isinstance(active, MySQLConnector):
        return "mysql"
    return "sqlite"
