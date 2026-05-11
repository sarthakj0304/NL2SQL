"""
postgres_connector.py
─────────────────────
PostgreSQL implementation of BaseConnector.

Uses `psycopg2`. Install with:
    pip install psycopg2-binary

Accepts a standard libpq connection string (DSN), e.g.:
    postgresql://user:password@host:5432/dbname
    host=localhost dbname=mydb user=admin password=secret
"""

from typing import Any, Dict, List, Optional, Tuple

from .base import BaseConnector


def _require_psycopg2():
    try:
        import psycopg2
        return psycopg2
    except ImportError:
        raise ImportError(
            "PostgreSQL support requires psycopg2. "
            "Install it with:  pip install psycopg2-binary"
        )


class PostgresConnector(BaseConnector):
    """
    Connector for PostgreSQL databases.

    Parameters
    ----------
    dsn : str
        A libpq-compatible connection string, e.g.
        ``postgresql://user:pass@localhost:5432/mydb``
    schema : str
        The Postgres schema to introspect (default: ``public``).
    """

    def __init__(self, dsn: str, schema: str = "public") -> None:
        self.dsn = dsn
        self.pg_schema = schema
        _require_psycopg2()  # Fail fast if psycopg2 not installed

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _connect(self):
        psycopg2 = _require_psycopg2()
        return psycopg2.connect(self.dsn)

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
                SELECT table_name
                FROM   information_schema.tables
                WHERE  table_schema = %s
                  AND  table_type   = 'BASE TABLE'
                ORDER  BY table_name;
                """,
                (self.pg_schema,),
            )
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_columns(self, table: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.cursor()

            # Column metadata from information_schema
            cur.execute(
                """
                SELECT column_name,
                       data_type,
                       is_nullable,
                       column_default
                FROM   information_schema.columns
                WHERE  table_schema = %s
                  AND  table_name   = %s
                ORDER  BY ordinal_position;
                """,
                (self.pg_schema, table),
            )
            col_rows = cur.fetchall()

            # Primary key columns
            cur.execute(
                """
                SELECT kcu.column_name
                FROM   information_schema.table_constraints  tc
                JOIN   information_schema.key_column_usage   kcu
                       ON  tc.constraint_name = kcu.constraint_name
                       AND tc.table_schema    = kcu.table_schema
                WHERE  tc.constraint_type = 'PRIMARY KEY'
                  AND  tc.table_schema    = %s
                  AND  tc.table_name      = %s;
                """,
                (self.pg_schema, table),
            )
            pk_cols = {row[0] for row in cur.fetchall()}

            return [
                {
                    "name":    col[0],
                    "type":    col[1].upper(),
                    "notnull": col[2] == "NO",
                    "default": col[3],
                    "pk":      col[0] in pk_cols,
                }
                for col in col_rows
            ]
        finally:
            conn.close()

    def get_foreign_keys(self, table: str) -> List[Dict[str, str]]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT kcu.column_name,
                       ccu.table_name  AS foreign_table,
                       ccu.column_name AS foreign_column
                FROM   information_schema.table_constraints        tc
                JOIN   information_schema.key_column_usage         kcu
                       ON  tc.constraint_name = kcu.constraint_name
                       AND tc.table_schema    = kcu.table_schema
                JOIN   information_schema.constraint_column_usage  ccu
                       ON  tc.constraint_name = ccu.constraint_name
                       AND tc.table_schema    = ccu.table_schema
                WHERE  tc.constraint_type = 'FOREIGN KEY'
                  AND  tc.table_schema    = %s
                  AND  tc.table_name      = %s;
                """,
                (self.pg_schema, table),
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
            col_names_quoted = ", ".join(f'"{c["name"]}"' for c in columns)
            cur.execute(
                f'SELECT {col_names_quoted} FROM "{self.pg_schema}"."{table}" LIMIT %s;',
                (sample_size,),
            )
            rows = cur.fetchall()
            col_index = {col["name"]: i for i, col in enumerate(columns)}

            for col in columns:
                idx = col_index[col["name"]]
                seen: List[str] = []
                for row in rows:
                    val = row[idx]
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
            cur.execute(f'SELECT COUNT(*) FROM "{self.pg_schema}"."{table}";')
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
