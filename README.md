# NL2SQL — AI-Powered Natural Language to SQL Engine

A sophisticated **Natural Language to SQL (NL2SQL)** full-stack system designed to bridge the gap between non-technical users and complex relational databases. It converts natural language questions into SQL queries, executes them on a connected database (SQLite, PostgreSQL, or MySQL), and returns structured results in an intuitive chat interface.

The system utilizes a highly resilient, prioritized pipeline. It attempts to resolve simple queries instantly using a zero-cost Regex rule engine. For complex queries, it relies on a local, Spider-fine-tuned T5 Machine Learning model (`tscholak/3vnuv1vf`), falling back to the Gemini 1.5 Pro API only when the local model's confidence is low or when an execution error requires an automated repair.

---

## Architecture Pipeline

```text
User NL Question
       │
       ▼
┌──────────────────────────┐
│ 1. Rule Engine (Fast)    │  → handles trivial "show all X" queries instantly
└──────────┬───────────────┘
           │ (if no match)
           ▼
┌──────────────────────────┐
│ 2. Schema Loader         │  → dynamically extracts tables, columns, constraints, and samples
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 3. Schema Linker (NLP)   │  → prunes schema to relevant tables (token overlap + Rapidfuzz)
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 4. Query Analyser        │  → detects intent: aggregation, sorting, limits, negation
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 5. Prompt Builder        │  → serializes the pruned schema into the T5 Spider format
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 6. Primary Inference     │  → Local T5-Large Model (tscholak/3vnuv1vf) via Beam Search (k=4)
│                          │    Yields raw SQL and a Confidence Score.
└──────────┬───────────────┘
           │ (if score < -0.83 or failed)
           ├───────────────────────────────► ┌─────────────────────────────┐
           │                                 │ 6b. Gemini API Fallback     │
           ▼                                 └──────────────┬──────────────┘
┌──────────────────────────┐                                │
│ 7. SQL Post-Processor    │ ◄──────────────────────────────┘
│    & Safety Validator    │  → normalizes SQL and rejects non-SELECT / mutations (DML/DDL)
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 8. SQL Verifier & Repair │  → verifies schema identifiers and fuzzy-repairs slight typos
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 9. SQL Executor          │  → executes on SQLite / Postgres / MySQL
└──────────┬───────────────┘
           │ (if DB execution fails)
           ├───────────────────────────────► ┌─────────────────────────────┐
           │                                 │ 9b. Gemini Execution Repair │
           ▼                                 └──────────────┬──────────────┘
┌──────────────────────────┐                                │
│10. Response Formatter    │ ◄──────────────────────────────┘
│    & Frontend Render     │  → returns clean JSON, formatted in a modern React Chat UI
└──────────────────────────┘
```

---

## Features

- **Multi-Database Support**: Connect to **SQLite** (via file upload), **PostgreSQL**, or **MySQL** (via DSN/Credentials).
- **Hybrid AI Engine**: Local, privacy-first inference using a 770M parameter T5 model, backed by a Gemini API safety net.
- **Dynamic Schema Introspection**: Extracts table definitions, relationships, and sample values on-the-fly. No hardcoded schemas.
- **Context-Aware Schema Pruning**: NLP-based schema linking ensures the model is not overwhelmed by enterprise-scale databases with hundreds of tables.
- **Self-Healing SQL**: Proactive fuzzy-matching corrects hallucinated column names, and reactive Gemini fallbacks repair syntax errors encountered during execution.
- **Enterprise-Grade Safety**: Strict regex-based validation gates block any destructive commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`).
- **Premium Frontend**: Built with React, Vite, Tailwind CSS v4, and Framer Motion for a fluid, responsive, dark-mode conversational UI.

---

## Repository Structure

```text
NL2SQL/
├── frontend/                     # React / Vite SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatComponent.jsx # Conversational UI & Results Table
│   │   │   └── FileUpload.jsx    # DB Connection Interface (Upload & DSN)
│   │   ├── App.jsx               # Main Application State
│   │   └── index.css             # Tailwind v4 Styles
│   ├── package.json
│   └── vite.config.js
│
├── backend/                      # Python Flask API & Core Engine
│   ├── app.py                    # API Routes (/upload_db, /connect_db, /api/query)
│   ├── config/
│   │   └── settings.py           # Configuration (DB parameters, Models, Thresholds)
│   ├── database/                 # DB Abstraction Layer (Connector Factory)
│   │   ├── connectors/           # SQLite, PostgreSQL, MySQL Connector implementations
│   │   ├── connector_factory.py  # Instantiates the correct connector
│   │   └── db_connector.py       # Active connection state manager
│   ├── model/                    # ML Model Management
│   │   ├── load_model.py         # Multi-tier safe model loading
│   │   └── inference.py          # Beam search generation
│   ├── schema/                   # Schema Introspection & Linking
│   │   ├── schema_loader.py      # Extracts full DB metadata
│   │   ├── schema_linker.py      # Rapidfuzz NLP pruning
│   │   └── prompt_builder.py     # Spider-style serialization
│   ├── sql/                      # Validation, Analysis, & Repair
│   │   ├── query_analyser.py     # Intent extraction (sort, agg, limits)
│   │   ├── rule_engine.py        # Fast-path regex solver
│   │   ├── sql_repair.py         # Fuzzy typo correction
│   │   ├── sql_validator.py      # DML/DDL blocker
│   │   └── sql_verifier.py       # Schema identifier verification
│   └── utils/
│
├── .env                          # Environment Variables (GEMINI_API_KEY)
├── requirements.txt              # Python Dependencies
└── README.md
```

---

## Installation & Setup

### Prerequisites
- **Python 3.9+** (For the backend)
- **Node.js 18+** (For the frontend)
- (Optional) **Gemini API Key** (For the fallback engine)

### 1. Clone the Repository
```bash
git clone <repository_url>
cd NL2SQL
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r ../requirements.txt
```
*Note: On the first run, the T5-Large model (~3 GB) will automatically download and cache.*

Configure your `.env` file in the root or `backend/` directory:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

Start the Flask API:
```bash
python app.py
# Server starts at http://127.0.0.1:5010
```

### 3. Frontend Setup
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
# Vite Server starts at http://localhost:5173
```

---

## How to Use

1. **Open the Web UI**: Navigate to `http://localhost:5173` in your browser.
2. **Connect a Database**:
   - **SQLite**: Drag and drop a `.db` or `.sqlite` file.
   - **PostgreSQL / MySQL**: Enter your connection string (DSN) or host credentials.
3. **Ask Questions**: Type natural language queries into the chat interface. Examples:
   - *"Show me all users who signed up last month."*
   - *"What is the average salary by department, sorted descending?"*
   - *"How many products are out of stock?"*
4. **View Results**: The system will display the generated SQL with syntax highlighting, alongside the executed data in a structured table.

---

## Technologies Used

| Component | Technology |
|---|---|
| **Frontend** | React, Vite, Tailwind CSS v4, Framer Motion, Axios |
| **Backend API** | Python, Flask, Flask-CORS |
| **Primary AI Engine** | Hugging Face Transformers (`tscholak/3vnuv1vf` T5-Large), PyTorch |
| **Fallback AI Engine**| Google GenAI SDK (Gemini 1.5 Pro/Flash) |
| **Database Drivers** | `sqlite3` (built-in), `psycopg2-binary`, `mysql-connector-python` |
| **Schema Linking** | `rapidfuzz` |

---

## Limitations & Considerations

- **Memory Footprint**: The primary T5-Large model requires ~3-4 GB of RAM/VRAM to load.
- **Data Privacy**: Using the Gemini fallback sends the pruned database schema (table names, column names, and up to 3 sample values per column) to Google's API. Actual database rows/contents are **not** sent, except for the specifically extracted sample values.
- **Complex JOINs**: While schema linking prunes massive databases efficiently, extremely complex multi-table relationships may still challenge the context limit.
