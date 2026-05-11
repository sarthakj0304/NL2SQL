"""
schema_loader.py
────────────────
Thin wrapper that loads the full database schema via the active connector.
Caches the schema at module level so we only introspect the DB once
per connection (or on explicit invalidation).

Works with any connector (SQLite, PostgreSQL, MySQL) — the active connector
is managed by db_connector.py and connector_factory.py.
"""

from typing import Any, Dict, Optional

import config.settings as _settings
from database.db_connector import extract_schema, get_active_db_type

# Module-level cache.
# Key is the db_path for SQLite, or a synthetic key like "postgres:<dsn>" for others.
_schema_cache: Dict[str, Any] = {}


def _cache_key(db_path: Optional[str]) -> str:
    """Build a stable cache key for the current connection."""
    db_type = get_active_db_type()
    if db_type == "sqlite":
        return db_path or getattr(_settings, "DB_PATH", "")
    # For remote DBs, use type + dsn as key
    dsn = getattr(_settings, "DB_DSN", "")
    return f"{db_type}:{dsn}"


def load_schema(db_path: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    Load and return the full schema for the currently active database.

    Parameters
    ----------
    db_path : str, optional
        For SQLite: path to the database file (defaults to DB_PATH from settings).
        For Postgres/MySQL: ignored — the active connector is used.
    force_reload : bool
        If True, bypass the in-memory cache and re-extract the schema.

    Returns
    -------
    dict
        Schema dict: {table_name: {columns, foreign_keys, sample_values, row_count}}
    """
    key = _cache_key(db_path)

    if force_reload or key not in _schema_cache:
        # Pass db_path to extract_schema so SQLite backward-compat shim works
        _schema_cache[key] = extract_schema(db_path)

    return _schema_cache[key]


def invalidate_cache(db_path: Optional[str] = None) -> None:
    """
    Clear the cached schema.

    If `db_path` is given, only that SQLite path is cleared.
    Otherwise the entire cache is flushed (used when switching databases).
    """
    if db_path:
        _schema_cache.pop(db_path, None)
    else:
        _schema_cache.clear()