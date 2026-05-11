"""
prompt_builder.py
─────────────────
Builds structured prompts for the NL2SQL model.

Uses a Spider-style serialization format that the fine-tuned T5 model
was trained on. The format includes:
  - CREATE TABLE statements (richer than simple "Table: col1, col2")
  - Sample values in comments (anchors the model to real data patterns)
  - Foreign key hints
  - The natural language question

Spider input format:
    "translate English to SQL: <question> | <db_id> | <serialized_schema>"
where serialized_schema uses "|" between tables and ":" between table and cols.

For our PICARD/T5 model we use:
    "<question> | <db_id> | <schema>"
"""

from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Schema serialisers
# ─────────────────────────────────────────────────────────────────────────────

def _serialise_schema_spider(schema: Dict[str, Any], db_id: str = "database") -> str:
    """
    Serialise the schema in the compact Spider format used by PICARD/T5 models:

        table1 : col1 col2 col3 | table2 : col4 col5

    Column names are lower-cased to match training data conventions.
    String/text columns with sample values are annotated inline so the
    model can ground string literals (e.g., use 'Mathematics' not 'Math'):

        table1 : col1 , col2 [val1, val2] , col3 | ...
    """
    # Column types that may contain meaningful string literals
    _TEXT_TYPES = {"text", "varchar", "char", "string", "nvarchar", "clob"}

    parts: List[str] = []
    for table_name, table_info in schema.items():
        col_parts: List[str] = []
        for col in table_info["columns"]:
            col_name = col["name"].lower()
            col_type = col.get("type", "").lower().split("(")[0].strip()
            samples = table_info.get("sample_values", {}).get(col["name"], [])

            # Annotate text columns with up to 3 sample values so the model
            # knows exactly which string literals exist in the data.
            if col_type in _TEXT_TYPES and samples:
                sample_str = ", ".join(f"'{s}'" for s in samples[:3])
                col_parts.append(f"{col_name} [{sample_str}]")
            else:
                col_parts.append(col_name)

        parts.append(f"{table_name.lower()} : {' , '.join(col_parts)}")
    return " | ".join(parts)


def _serialise_schema_sql(schema: Dict[str, Any]) -> str:
    """
    Serialise the schema as SQL CREATE TABLE statements with sample value
    comments — more human-readable and gives the model column type context.

    Used in the human-readable hint section of the prompt.
    """
    lines: List[str] = []

    for table_name, table_info in schema.items():
        cols_ddl: List[str] = []
        for col in table_info["columns"]:
            pk_marker  = " PRIMARY KEY" if col["pk"]      else ""
            nn_marker  = " NOT NULL"    if col["notnull"] else ""
            cols_ddl.append(f"    {col['name']} {col['type']}{pk_marker}{nn_marker}")

        create_stmt = (
            f"CREATE TABLE {table_name} (\n"
            + ",\n".join(cols_ddl)
            + "\n);"
        )
        lines.append(create_stmt)

        # Add sample values as SQL comment
        for col in table_info["columns"]:
            samples = table_info["sample_values"].get(col["name"], [])
            if samples:
                sample_str = ", ".join(samples[:3])
                lines.append(f"-- {table_name}.{col['name']} samples: {sample_str}")

        # Add FK hints
        for fk in table_info.get("foreign_keys", []):
            lines.append(
                f"-- FOREIGN KEY: {table_name}.{fk['from_col']} → "
                f"{fk['to_table']}.{fk['to_col']}"
            )

        lines.append("")  # blank line between tables

    return "\n".join(lines).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Main prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(
    question: str,
    schema: Dict[str, Any],
    db_id: str = "database",
    hints: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build the model input prompt from a natural language question and schema.

    Returns a string in PICARD/Spider T5 format:
        "<question> | <db_id> | <serialized_schema>"

    This is the primary input format for `tscholak/3vnuv1vf` and similar models.

    Parameters
    ----------
    question : str
        The user's natural language question.
    schema : dict
        Pruned schema dict from schema_linker.
    db_id : str
        A logical name for the database (used in the Spider serialization).
    hints : dict, optional
        Optional query analysis hints (aggregation type, sort order, etc.)
        Appended as a prefix to the question when present.
    """
    # Optionally enrich the question with hints for disambiguation
    enriched_question = _enrich_question(question, hints)

    # Spider serialization for the model
    serialized_schema = _serialise_schema_spider(schema, db_id)

    # PICARD T5 input format
    prompt = f"{enriched_question} | {db_id} | {serialized_schema}"

    return prompt


def build_debug_prompt(
    question: str,
    schema: Dict[str, Any],
    db_id: str = "database",
    hints: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a human-readable version of the prompt (for logging/debugging).
    Uses the full CREATE TABLE format with sample values.
    Not used for model inference — only for inspection.
    """
    enriched_question = _enrich_question(question, hints)
    sql_schema = _serialise_schema_sql(schema)

    return (
        f"-- Database: {db_id}\n"
        f"-- Question: {enriched_question}\n\n"
        f"{sql_schema}\n\n"
        f"-- SQL Query:"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Question enrichment
# ─────────────────────────────────────────────────────────────────────────────

def _enrich_question(question: str, hints: Optional[Dict[str, Any]]) -> str:
    """
    Optionally prepend structured hints to the question to guide the model.
    Only applied when hints contain high-confidence signals.
    """
    if not hints:
        return question

    prefix_parts: List[str] = []

    agg = hints.get("aggregation")
    if agg:
        prefix_parts.append(f"[{agg.upper()}]")

    sort = hints.get("sort")
    if sort:
        prefix_parts.append(f"[{sort.upper()}]")

    if prefix_parts:
        return " ".join(prefix_parts) + " " + question

    return question