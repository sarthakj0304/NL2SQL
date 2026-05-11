"""
sql_postprocess.py
──────────────────
Cleans and normalises raw SQL output from the model.

T5-based models sometimes produce output with:
  - Trailing explanation text after the SQL
  - Inconsistent keyword casing (select, SELECT, Select)
  - Extra whitespace or newlines
  - Markdown code fences (```sql ... ```)
  - Repeated semicolons or trailing junk

This module strips all of that and returns clean, normalised SQL.
"""

import re
from typing import Optional


# SQL keywords to uppercase-normalise
_SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "LIKE",
    "ORDER", "BY", "GROUP", "HAVING", "LIMIT", "OFFSET", "JOIN",
    "INNER", "LEFT", "RIGHT", "OUTER", "FULL", "ON", "AS", "DISTINCT",
    "COUNT", "SUM", "AVG", "MAX", "MIN", "BETWEEN", "IS", "NULL",
    "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TABLE",
    "ASC", "DESC", "UNION", "INTERSECT", "EXCEPT", "EXISTS", "CASE",
    "WHEN", "THEN", "ELSE", "END", "WITH", "RECURSIVE", "VALUES",
]

# Pre-compiled pattern: match whole-word occurrences of SQL keywords (case-insensitive)
_KEYWORD_RE = re.compile(
    r"\b(" + "|".join(_SQL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def clean_sql(raw_output: str) -> Optional[str]:
    """
    Extract and normalise SQL from raw model output.

    Parameters
    ----------
    raw_output : str
        The raw string decoded from the model's output tokens.

    Returns
    -------
    str or None
        Cleaned SQL string, or None if nothing SQL-like was found.
    """
    if not raw_output or not raw_output.strip():
        return None

    sql = raw_output.strip()

    # 1. Strip markdown code fences
    sql = re.sub(r"```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = sql.replace("```", "")

    # 2. If the output contains a SQL keyword, extract from there forward
    #    (model sometimes prepends explanation text)
    first_kw_match = re.search(r"\b(SELECT|WITH|INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE)\b", sql, re.IGNORECASE)
    if first_kw_match:
        sql = sql[first_kw_match.start():]

    # 3. Truncate at the first double-newline or "---" separator
    #    (some models append reasoning after a blank line)
    sql = re.split(r"\n\n|---", sql)[0]

    # 4. Remove trailing explanation text after the first semicolon
    semi_pos = sql.find(";")
    if semi_pos != -1:
        sql = sql[:semi_pos]

    # 5. Collapse whitespace
    sql = re.sub(r"\s+", " ", sql).strip()

    # 6. Normalise SQL keyword casing to UPPERCASE
    sql = _KEYWORD_RE.sub(lambda m: m.group(0).upper(), sql)

    # 7. Reject if the result doesn't look like SQL
    if not re.search(r"\b(SELECT|WITH|INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE)\b", sql, re.IGNORECASE):
        return None

    return sql