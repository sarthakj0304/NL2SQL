"""
app.py
──────
NL2SQL Flask API Server

Endpoints
─────────
  POST /api/query     — Translate NL question → SQL → execute → return results
  GET  /api/schema    — Return the schema of the configured database
  

Configuration
─────────────
  Edit backend/config/settings.py to change DB_PATH (the SQLite database to query).
  Users interact with the system only through natural language questions.

Pipeline (per /api/query request)
──────────────────────────────────
  1. Rule engine  — handles trivially simple "show all X" queries instantly
  2. Schema load  — extract full schema from the configured SQLite DB
  3. Schema link  — prune schema to only the tables/cols relevant to the question
  4. Query hints  — NLP-based intent extraction (aggregation, sort, limit...)
  5. Prompt build — Spider-style serialisation for the T5 model
  6. Inference    — T5-Large beam search → raw SQL
  7. Post-process — Extract + normalise SQL from model output
  8. Safety check — Reject any non-SELECT or mutation-containing SQL
  9. Verify       — Check table names exist in schema
 10. Execute      — Run on SQLite, return (columns, rows)
 11. Repair       — If execution fails, fuzzy-fix identifiers and retry
"""

import os
import sys
import logging
import uuid
from google import genai
from dotenv import load_dotenv

load_dotenv()


from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Pipeline imports ──────────────────────────────────────────────────────────
from schema.schema_loader   import load_schema
from schema.schema_linker   import link_schema
from schema.prompt_builder  import build_prompt, build_debug_prompt

from model.inference        import generate_sql, model_is_available, get_active_model_name

from sql.rule_engine        import generate_sql_rule_based
from sql.query_analyser     import analyze_query
from sql.sql_postprocess    import clean_sql
from sql.sql_validator      import is_safe_sql, is_safe_prompt
from sql.sql_verifier       import verify_sql
from sql.sql_repair         import repair_sql
from sql.sql_executor       import run_sql

from utils.response_formatter import format_success, format_error
if os.getenv("GEMINI_API_KEY"):
    gemini_client = genai.Client()
else:
    gemini_client = None
import config.settings
from config.settings import DEFAULT_ERROR_MESSAGE

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("nl2sql")

app = Flask(__name__)
CORS(app)   # Allow cross-origin requests (useful when connecting a frontend later)


# ─────────────────────────────────────────────────────────────────────────────
# File Upload
# ─────────────────────────────────────────────────────────────────────────────

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/upload_db", methods=["POST"])
def upload_db():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    if not (file.filename.endswith(".db") or file.filename.endswith(".sqlite")):
        return jsonify({"error": "Invalid file type"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{file.filename}")
    file.save(file_path)

    config.settings.DB_PATH = file_path
    with open(os.path.join(UPLOAD_FOLDER, "last_db.txt"), "w") as f:
        f.write(file_path)

    try:
        schema = load_schema(file_path)
        return jsonify({
            "success": True,
            "message": f"Database connected successfully! I've indexed {len(schema)} tables.",
            "db_name": file.filename,
            "tables": len(schema)
        })
    except Exception as e:
        log.error("Failed to load schema from uploaded DB: %s", e)
        return jsonify({"error": "Invalid database file"}), 400

# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

# @app.route("/api/health", methods=["GET"])
# def health():
#     """Return the status of the model and database connection."""
#     db_ok = False
#     db_tables = 0
#     try:
#         schema = load_schema(config.settings.DB_PATH)
#         db_ok = True
#         db_tables = len(schema)
#     except Exception as e:
#         log.warning("DB health check failed: %s", e)

#     return jsonify({
#         "status":       "ok" if db_ok else "degraded",
#         "model_loaded": model_is_available(),
#         "model_name":   get_active_model_name(),
#         "db_path":      config.settings.DB_PATH,
#         "db_reachable": db_ok,
#         "db_tables":    db_tables,
#     })


# ─────────────────────────────────────────────────────────────────────────────
# Schema inspection
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/schema", methods=["GET"])
def schema_view():
    """
    Return the full schema of the configured database.

    Response
    --------
    {
      "db_path": "...",
      "tables": {
        "table_name": {
          "columns": [{"name", "type", "pk", "notnull"}, ...],
          "foreign_keys": [...],
          "sample_values": {"col": ["v1", "v2", ...]},
          "row_count": 123
        }
      }
    }
    """
    try:
        schema = load_schema(config.settings.DB_PATH)
        return jsonify({"db_path": config.settings.DB_PATH, "tables": schema})
    except Exception as e:
        log.error("Schema load failed: %s", e)
        return jsonify({"error": f"Could not load schema: {e}"}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Main query endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/query", methods=["POST"])
def query():
    """
    Translate a natural language question into SQL and execute it.

    Request body (JSON)
    -------------------
    {
      "question": "How many students are enrolled in each major?"
    }

    Response (success)
    ------------------
    {
      "success":   true,
      "question":  "...",
      "sql":       "SELECT major, COUNT(*) FROM students GROUP BY major",
      "source":    "model",
      "columns":   ["major", "COUNT(*)"],
      "rows":      [["Computer Science", 42], ["Physics", 17]],
      "row_count": 2
    }

    Response (failure)
    ------------------
    {
      "success":  false,
      "question": "...",
      "message":  "Could not generate a valid SQL query...",
      "stage":    "validation"
    }
    """
    # ── Parse request ─────────────────────────────────────────────────────
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()

    if not question:
        return jsonify({"error": "No question provided. Send JSON: {\"question\": \"...\"}"}), 400

    log.info("Question: %s", question)

    # ── Initial Prompt Safety Check ───────────────────────────────────────
    if not is_safe_prompt(question):
        log.warning("[Validator] Rejected unsafe prompt: %s", question)
        return jsonify(format_error(
            question, 
            "Data manipulation not allowed.", 
            stage="validation"
        )), 422

    # ── Load schema ───────────────────────────────────────────────────────
    try:
        full_schema = load_schema(config.settings.DB_PATH)
    except Exception as e:
        log.error("Could not load schema: %s", e)
        return jsonify(format_error(question, f"Database error: {e}", stage="schema_load")), 500

    # ─────────────────────────────────────────────────────────────────────
    # STAGE 1: Rule engine (instant, zero-cost for simple queries)
    # ─────────────────────────────────────────────────────────────────────
    sql = generate_sql_rule_based(question, schema=full_schema)

    if sql is not None:
        log.info("[Rule engine] Generated: %s", sql)

        if verify_sql(sql, full_schema):
            try:
                columns, rows = run_sql(sql, config.settings.DB_PATH)
                print("\n" + "="*50)
                # print("⚡ OUTPUT SOURCE: RULE ENGINE")
                print("="*50 + "\n")
                log.info("[Rule engine] Success — %d rows", len(rows))
                return jsonify(format_success(
                    question, sql, columns, rows, source="rule_engine"
                ))
            except Exception as e:
                log.warning("[Rule engine] Execution failed: %s — falling through to model", e)

    # ─────────────────────────────────────────────────────────────────────
    # STAGE 2: Model-based generation
    # ─────────────────────────────────────────────────────────────────────
    if not model_is_available():
        return jsonify(format_error(
            question,
            "Model is not loaded. Check server logs for download/load errors.",
            stage="model_unavailable",
        )), 503

    # 2a. Schema linking — prune to relevant tables
    linked_schema = link_schema(question, full_schema)
    log.info(
        "[Schema linker] Tables selected: %s",
        list(linked_schema.keys()),
    )

    # 2b. Query intent hints
    hints = analyze_query(question)
    if hints:
        log.info("[Query analyser] Hints: %s", hints)

    # 2c. Build model prompt
    prompt = build_prompt(question, linked_schema, hints=hints)
    log.debug("[Prompt]\n%s", build_debug_prompt(question, linked_schema, hints=hints))

    # 2d. Model inference
    raw_output, confidence_score = generate_sql(prompt)
    print("\n" + "="*50)
    # print("🤖 OUTPUT SOURCE: MACHINE LEARNING (T5 MODEL)")
    print("="*50 + "\n")
    log.info("[Model] Raw output: %s, confidence: %s", raw_output, confidence_score)

    if not raw_output or confidence_score < -0.83:
        # log.warning("[Model] T5 failed or low confidence. Falling back to Gemini.")
        try:
            if gemini_client:
                gemini_prompt = f"Given this database schema:\n{linked_schema}\nGenerate ONLY a SQL query for this question: '{question}'. Do not include markdown code blocks, just the raw SQL. If the question asks to manipulate or modify data (e.g., DROP, INSERT, UPDATE, DELETE), generate the exact SQL query requested so it can be correctly processed by our system."
                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=gemini_prompt
                )
                raw_output = response.text.replace("```sql", "").replace("```", "").strip()
                print("\n" + "="*50)
                # print("🧠 OUTPUT SOURCE: GEMINI API (Fallback for generation)")
                print("="*50 + "\n")
                log.info("[Gemini] Generated SQL: %s", raw_output)
            else:
                raise Exception("GEMINI_API_KEY is not set.")
        except Exception as gemini_e:
            log.error("[Gemini] Fallback failed: %s", gemini_e)
            if not raw_output:
                return jsonify(format_error(question, DEFAULT_ERROR_MESSAGE, stage="inference")), 422

    # 2e. Post-process
    sql = clean_sql(raw_output)
    log.info("[Post-process] Clean SQL: %s", sql)

    if not sql:
        return jsonify(format_error(
            question, DEFAULT_ERROR_MESSAGE, stage="postprocess"
        )), 422

    # 2f. Safety validation
    if not is_safe_sql(sql):
        log.warning("[Validator] Rejected unsafe SQL: %s", sql)
        return jsonify(format_error(
            question,
            "Data manipulation not allowed.",
            sql=sql,
            stage="validation",
        )), 422

    # 2g. Schema verification (table names)
    if not verify_sql(sql, full_schema):
        log.warning("[Verifier] SQL references unknown tables — attempting repair")
        sql = repair_sql(sql, full_schema)
        log.info("[Repair] Repaired SQL: %s", sql)

        if not verify_sql(sql, full_schema):
            return jsonify(format_error(
                question, DEFAULT_ERROR_MESSAGE, sql=sql, stage="verification"
            )), 422

    # 2h. Execute
    try:
        columns, rows = run_sql(sql, config.settings.DB_PATH)
        log.info("[Executor] Success — %d rows", len(rows))
        return jsonify(format_success(question, sql, columns, rows, source="model"))

    except Exception as exec_error:
        log.warning("[Executor] Failed: %s — attempting SQL repair", exec_error)

        # 2i. Repair and retry
        repaired_sql = repair_sql(sql, full_schema)
        log.info("[Repair] Repaired SQL: %s", repaired_sql)

        if repaired_sql != sql:
            try:
                columns, rows = run_sql(repaired_sql, config.settings.DB_PATH)
                log.info("[Repair+Executor] Success — %d rows", len(rows))
                return jsonify(format_success(
                    question, repaired_sql, columns, rows, source="model+repair"
                ))
            except Exception as repair_error:
                log.error("[Repair+Executor] Also failed: %s", repair_error)

        # Gemini fallback for execution failure
        # log.warning("[Model] T5 SQL execution failed. Falling back to Gemini.")
        try:
            if gemini_client:
                gemini_prompt = f"Given this database schema:\n{linked_schema}\nThe user asked: '{question}'. The following SQL failed to execute: {sql}. Error: {exec_error}. Generate a corrected, valid SQL query. Return ONLY the raw SQL, no markdown."
                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=gemini_prompt
                )
                gemini_sql = clean_sql(response.text.replace("```sql", "").replace("```", "").strip())
                print("\n" + "="*50)
                # print("🧠 OUTPUT SOURCE: GEMINI API (Fallback for execution repair)")
                print("="*50 + "\n")
                log.info("[Gemini Repair] Generated SQL: %s", gemini_sql)

                if not is_safe_sql(gemini_sql):
                    log.warning("[Validator] Rejected unsafe Gemini repair SQL: %s", gemini_sql)
                    return jsonify(format_error(
                        question,
                        "Data manipulation not allowed.",
                        sql=gemini_sql,
                        stage="validation",
                    )), 422
                
                columns, rows = run_sql(gemini_sql, config.settings.DB_PATH)
                return jsonify(format_success(question, gemini_sql, columns, rows, source="gemini_repair"))
            else:
                raise Exception("GEMINI_API_KEY is not set.")
        except Exception as e2:
            log.error("[Gemini Repair] Failed: %s", e2)

        return jsonify(format_error(
            question, DEFAULT_ERROR_MESSAGE, sql=sql, stage="execution"
        )), 422


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run with debug=False in production
    app.run(host="0.0.0.0", port=5010, debug=True)