"""
sql_validator.py
────────────────
SQL safety and type validation.

Two separate concerns:
  1. SAFETY — Block any SQL that could mutate or destroy data.
     Only SELECT queries are allowed (read-only).

  2. SYNTAX — Basic structural sanity check via sqlparse.
"""

import re
import sqlparse
from typing import Optional


# Only these top-level SQL statements are permitted
_ALLOWED_TOP_LEVEL = {"SELECT", "WITH"}

# Dangerous keywords that must never appear (even in subqueries / comments)
_BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
    "ALTER", "CREATE", "REPLACE", "EXEC", "EXECUTE",
    "ATTACH", "DETACH", "PRAGMA",
}

# Compile a pattern to detect blocked keywords as whole words
_BLOCKED_RE = re.compile(
    r"\b(" + "|".join(_BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def is_safe_prompt(prompt: Optional[str]) -> bool:
    """
    Check if the user's natural language prompt contains blatant SQL injection
    attempts or requests for data manipulation (to save API calls/compute).
    
    This is an initial heuristic check looking for explicit SQL syntax patterns.
    """
    if not prompt or not prompt.strip():
        return True
        
    prompt_clean = prompt.lower()
    
    # Block explicit data manipulation SQL commands in the natural language prompt
    blocked_patterns = [
        r"\bdrop\s+table\b",
        r"\bdrop\s+database\b",
        r"\bdelete\s+from\b",
        r"\bupdate\s+[a-z0-9_]+\s+set\b",
        r"\binsert\s+into\b",
        r"\btruncate\s+table\b",
        r"\balter\s+table\b",
        r"\bcreate\s+table\b",
        r"\bcreate\s+database\b",
        r"\breplace\s+into\b",
        r"\bexec\s*\(",
        r"\bexecute\s+immediate\b"
    ]
    
    for pattern in blocked_patterns:
        if re.search(pattern, prompt_clean):
            return False
            
    # Also check if the prompt is essentially just a blocked keyword
    # followed by an identifier (e.g., "DROP students").
    # We require it to be at the start to avoid blocking sentences like "I want to drop the physics class"
    if re.match(r"^\s*(drop|delete|update|insert|truncate|alter|create|replace)\s+[a-z0-9_]+\s*;?\s*$", prompt_clean):
        return False
        
    return True



def is_safe_sql(sql: Optional[str]) -> bool:
    """
    Return True only if `sql` is a read-only SELECT (or WITH...SELECT) query
    and contains no dangerous mutation keywords.

    Parameters
    ----------
    sql : str or None
        The SQL string to validate.

    Returns
    -------
    bool
    """
    if not sql or not sql.strip():
        return False

    sql_clean = sql.strip()

    # 1. Reject if any blocked keyword appears anywhere in the SQL
    if _BLOCKED_RE.search(sql_clean):
        return False

    # 2. Check the top-level statement type via sqlparse
    parsed = sqlparse.parse(sql_clean)
    if not parsed:
        return False

    statement = parsed[0]
    stmt_type = statement.get_type()

    if stmt_type not in (None, "SELECT", "UNKNOWN"):
        return False

    # 3. Ensure the query actually contains SELECT somewhere
    if not re.search(r"\bSELECT\b", sql_clean, re.IGNORECASE):
        return False

    return True


def has_valid_syntax(sql: Optional[str]) -> bool:
    """
    Basic structural syntax check using sqlparse.
    Returns True if sqlparse can parse the statement without obvious errors.
    """
    if not sql or not sql.strip():
        return False

    try:
        parsed = sqlparse.parse(sql.strip())
        return bool(parsed and parsed[0].tokens)
    except Exception:
        return False