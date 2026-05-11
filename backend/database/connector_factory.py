"""
connector_factory.py
────────────────────
Factory that instantiates the correct BaseConnector subclass based on
the configured database type.

Usage
─────
    from database.connector_factory import get_connector

    # SQLite (file path)
    c = get_connector("sqlite", db_path="database/sample.db")

    # PostgreSQL (DSN string)
    c = get_connector("postgres", dsn="postgresql://user:pass@localhost/mydb")

    # MySQL (DSN string)
    c = get_connector("mysql", dsn="mysql://user:pass@localhost:3306/mydb")

    # Use the connector
    schema = c.extract_schema()
    cols, rows = c.execute_query("SELECT * FROM students")

Supported db_type values (case-insensitive):
    "sqlite"                      → SQLiteConnector
    "postgres" / "postgresql"     → PostgresConnector
    "mysql" / "mariadb"           → MySQLConnector
"""

from typing import Any

from .connectors.base import BaseConnector


def get_connector(db_type: str, **kwargs) -> BaseConnector:
    """
    Return an initialised connector for the requested database type.

    Parameters
    ----------
    db_type : str
        One of: ``"sqlite"``, ``"postgres"``/``"postgresql"``,
        ``"mysql"``/``"mariadb"``.
    **kwargs :
        Passed directly to the connector constructor.

        SQLite:    db_path="path/to/file.db"
        Postgres:  dsn="postgresql://user:pass@host/db"
                   or schema="public" (optional)
        MySQL:     dsn="mysql://user:pass@host:3306/db"
                   or host=, port=, user=, password=, database=

    Returns
    -------
    BaseConnector
        A fully initialised connector ready for use.

    Raises
    ------
    ValueError
        If `db_type` is not recognised.
    ImportError
        If the required driver is not installed.
    """
    db_type_lower = db_type.lower().strip()

    if db_type_lower == "sqlite":
        from .connectors.sqlite_connector import SQLiteConnector
        db_path = kwargs.get("db_path", "")
        if not db_path:
            raise ValueError("SQLite connector requires a 'db_path' argument.")
        return SQLiteConnector(db_path=db_path)

    if db_type_lower in ("postgres", "postgresql"):
        from .connectors.postgres_connector import PostgresConnector
        dsn    = kwargs.get("dsn", "")
        schema = kwargs.get("schema", "public")
        if not dsn:
            raise ValueError(
                "PostgreSQL connector requires a 'dsn' argument, e.g. "
                "postgresql://user:pass@host:5432/dbname"
            )
        return PostgresConnector(dsn=dsn, schema=schema)

    if db_type_lower in ("mysql", "mariadb"):
        from .connectors.mysql_connector import MySQLConnector
        dsn = kwargs.get("dsn", "")
        # Accept either DSN or individual kwargs
        mysql_kwargs = {
            k: v for k, v in kwargs.items()
            if k in ("host", "port", "user", "password", "database")
        }
        return MySQLConnector(dsn=dsn, **mysql_kwargs)

    raise ValueError(
        f"Unknown db_type '{db_type}'. "
        f"Supported values: 'sqlite', 'postgres', 'postgresql', 'mysql', 'mariadb'."
    )
