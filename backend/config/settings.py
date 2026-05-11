import torch
import os

# ─────────────────────────────────────────────
# DATABASE CONFIGURATION
# ─────────────────────────────────────────────

# Path to the SQLite database (relative to backend/ or absolute)
# Change this to point to your own database file.
_last_db_file = os.path.join(os.path.dirname(__file__), "..", "uploads", "last_db.txt")
if os.path.exists(_last_db_file):
    with open(_last_db_file, "r") as f:
        DB_PATH = f.read().strip()
else:
    DB_PATH = "database/sample.db"

# Database type: "sqlite" | "postgres" | "postgresql" | "mysql" | "mariadb"
# Set via environment variable DB_TYPE or /connect_db API endpoint.
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# Connection string for Postgres / MySQL (ignored for SQLite)
# Examples:
#   postgresql://user:pass@localhost:5432/mydb
#   mysql://user:pass@localhost:3306/mydb
DB_DSN = os.getenv("DB_DSN", "")

# Postgres schema to introspect (default: public)
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

# ─────────────────────────────────────────────
# MODEL CONFIGURATION
# ─────────────────────────────────────────────

# HuggingFace model for NL2SQL (no API key needed — runs locally)
# This model is T5-Large fine-tuned on the Spider benchmark.
# It will be downloaded automatically on first run (~3 GB).
MODEL_NAME = "tscholak/3vnuv1vf"  # PICARD T5-Large, Spider fine-tuned

# Fallback smaller model (faster, lower accuracy) — used if large model fails to load
FALLBACK_MODEL_NAME = "mrm8488/t5-base-finetuned-wikiSQL"

# Device: CUDA (NVIDIA GPU) > CPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ─────────────────────────────────────────────
# INFERENCE SETTINGS
# ─────────────────────────────────────────────

MAX_INPUT_LENGTH  = 512   # Max tokens for prompt input
MAX_OUTPUT_LENGTH = 256   # Max tokens for generated SQL
BEAM_SIZE         = 4     # Beam search width (higher = better but slower)

# ─────────────────────────────────────────────
# SCHEMA LINKING SETTINGS
# ─────────────────────────────────────────────

# Max tables to include in prompt for large databases
MAX_RELEVANT_TABLES = 6

# Minimum score (0–1) for a table to be included in schema linking
SCHEMA_LINK_THRESHOLD = 0.15

# ─────────────────────────────────────────────
# SQL EXECUTION SETTINGS
# ─────────────────────────────────────────────

MAX_RESULTS = 500  # Max rows returned per query

# ─────────────────────────────────────────────
# RESPONSE MESSAGES
# ─────────────────────────────────────────────

DEFAULT_ERROR_MESSAGE = (
    "Could not generate a valid SQL query for this question. "
    "Please try rephrasing your question or check that it relates to the connected database."
)