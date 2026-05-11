# NL2SQL System Architecture & Codebase Audit

## 1. Executive Summary
The NL2SQL (Natural Language to SQL) application is a full-stack, hybrid AI-powered assistant designed to bridge the gap between non-technical users and complex relational databases. The core problem it solves is the inability of business users to extract data from databases without knowing SQL syntax. 

Originally built exclusively for SQLite, the system has been heavily re-architected to feature a unified Multi-Database Connector layer, supporting **SQLite**, **PostgreSQL**, and **MySQL**. Users can upload local database files or connect via DSN credentials through a modern React web interface. The system intelligently converts plain English questions into valid, secure SQL queries, executes them against the connected database, and returns both the query and the resulting data in an intuitive chat interface.

It utilizes a highly resilient, prioritized pipeline. It first attempts to resolve simple queries instantly using a zero-cost Regex rule engine. For complex queries, it relies on a local T5 Machine Learning model (`tscholak/3vnuv1vf`), falling back to the Gemini 1.5 Pro API only when the local model's confidence is low or when an execution error requires automated repair.

---

## 2. Technology Stack
The application is built on a modern, modular architecture leveraging the following core libraries and frameworks:

### Frontend
*   **React (Vite):** Provides a fast, component-based user interface. Vite is used for rapid development and optimized production builds.
*   **Tailwind CSS (v4):** Utilized for rapid, utility-first UI styling. Provides the dark mode, modern chat interface, and responsive design.
*   **Framer Motion:** Adds micro-animations and smooth transitions (e.g., message bubbles popping in, loading indicators) to create a premium, "living" application feel.
*   **Axios:** Handles asynchronous HTTP requests to the Flask backend.

### Backend & Core Logic
*   **Python (Flask):** The lightweight web framework routing HTTP requests (`/upload_db`, `/connect_db`, `/api/query`), handling CORS, and orchestrating the AI pipelines.
*   **Unified Database Layer:** An abstract connector factory architecture that handles database connections dynamically.
    *   `sqlite3` (built-in)
    *   `psycopg2-binary` (PostgreSQL)
    *   `mysql-connector-python` (MySQL/MariaDB)
*   **Hugging Face Transformers (`transformers`):** Loads and runs the primary local NLP model (`tscholak/3vnuv1vf` - T5 Large). It handles the beam search decoding for accurate SQL generation.
*   **PyTorch (`torch`):** The underlying tensor computation framework powering the local T5 model.
*   **Google GenAI SDK (`google-genai`):** Integrates the Gemini API. Serves as a highly capable fallback engine for edge cases, low-confidence T5 outputs, or error repairs.
*   **Rapidfuzz:** Powers the NLP schema linking and fuzzy typo correction.
*   **sqlparse:** For non-destructive SQL structural validation.

---

## 3. File-by-File Directory Audit

### Frontend Directory (`/frontend/src`)
| File | Description |
| :--- | :--- |
| `App.jsx` | The main React application wrapper. Manages the high-level state (connected database, view switching between Upload and Chat). |
| `components/FileUpload.jsx` | Multi-tab UI component handling SQLite drag-and-drop uploads, as well as PostgreSQL/MySQL DSN connection forms. Handles `POST /upload_db` and `POST /connect_db`. |
| `components/ChatComponent.jsx` | The core conversational UI. Renders user messages, SQL code blocks (with syntax highlighting), result tables, and handles the main `POST /api/query` API call. |
| `index.css` | Global stylesheet integrating Tailwind CSS v4 and custom base styles. |

### Backend Directory (`/backend`)
| File/Directory | Description |
| :--- | :--- |
| `app.py` | The main Flask entry point. Defines API routes and orchestrates the rule engine, schema linking, model inference, validation, and Gemini fallback pipeline. |
| `config/settings.py` | Global configuration variables including active DB connection state, model selection, device mapping (CPU/GPU), and generation thresholds. |

#### Database Layer (`/backend/database`)
| File | Description |
| :--- | :--- |
| `connector_factory.py` | Factory pattern implementation that instantiates the correct `BaseConnector` subclass based on the requested `db_type`. |
| `db_connector.py` | Backward-compatible shim that manages the globally active connector state, allowing the rest of the app to query `extract_schema()` without caring about the underlying DB engine. |
| `connectors/base.py` | Abstract Base Class defining the required interface (e.g., `get_tables`, `get_columns`, `execute_query`) that all DB drivers must implement. |
| `connectors/sqlite_connector.py` | SQLite implementation using Python's built-in `sqlite3`. |
| `connectors/postgres_connector.py` | PostgreSQL implementation using `psycopg2`. |
| `connectors/mysql_connector.py` | MySQL implementation using `mysql.connector`. |

#### Model & Schema Logic (`/backend/model` & `/backend/schema`)
| File | Description |
| :--- | :--- |
| `model/load_model.py` | Handles the secure downloading and loading of the Hugging Face model and tokenizer. Includes a multi-tier loading strategy prioritizing `safetensors`. |
| `model/inference.py` | Exposes the `generate_sql` function. Executes the loaded model using beam search (`num_beams=4`) and extracts both the generated sequence and its confidence score. |
| `schema/schema_loader.py` | Thin caching wrapper over the DB connector's `extract_schema()` method. Extracts tables, columns, PKs, FKs, and sample values. |
| `schema/schema_linker.py` | Evaluates the user's natural language question against the database schema to prune irrelevant tables using `rapidfuzz` and token overlap, ensuring the AI model isn't overwhelmed. |
| `schema/prompt_builder.py` | Formats the pruned schema and the user's question into the exact string format expected by the Spider-trained T5 model (`<question> \| <db_id> \| <schema>`). |

#### SQL Processing (`/backend/sql`)
| File | Description |
| :--- | :--- |
| `rule_engine.py` | A fast, zero-cost regex-based engine that attempts to solve extremely simple queries ("Show all users") without invoking the ML model. |
| `query_analyser.py` | Extracts query intent (aggregation, sorting, limits, negations) from the NL prompt to guide the prompt builder. |
| `sql_executor.py` | Backward-compatible shim that delegates SQL execution to the active database connector. |
| `sql_validator.py` | A security gatekeeper. Rejects queries containing `DROP`, `DELETE`, `UPDATE`, or `INSERT` to prevent malicious database modification. |
| `sql_verifier.py` | Checks if the generated SQL explicitly maps to the known tables and columns in the extracted schema. |
| `sql_repair.py` | A self-healing module that attempts to fix minor SQL syntax errors, hallucinated column names, or incorrect string literals (e.g., `'Math'` -> `'Mathematics'`) using fuzzy matching before execution. |

---

## 4. The "Life of a Request" (Data Flow)

When a user types "Show me the top 5 highest paid employees" into the Chat UI, the following sequence occurs:

1.  **Frontend Dispatch:** `ChatComponent.jsx` sends a `POST` request with the JSON payload to `/api/query`.
2.  **API Entry (`app.py`):** The Flask route extracts the question and verifies prompt safety.
3.  **Schema Loading (`schema_loader.py`):** The system retrieves the cached schema from the active DB connector.
4.  **Rule Engine (`rule_engine.py`):** Attempts to match the question against hardcoded templates. Fails for complex queries, moving to the AI pipeline.
5.  **Schema Pruning (`schema_linker.py`):** The question is analyzed against the schema to filter out irrelevant tables (e.g., ignoring `departments` if the question only requires `employees`).
6.  **Intent Analysis (`query_analyser.py`):** Detects "top 5" (`LIMIT 5`) and "highest paid" (`ORDER BY ... DESC`).
7.  **Prompt Construction (`prompt_builder.py`):** The pruned schema, question, and hints are serialized into the T5 prompt format.
8.  **Primary Inference (`inference.py`):** The T5 model performs a beam search, returning a raw SQL string and a confidence score.
9.  **Fallback Evaluation (`app.py`):** If the T5 model fails or its confidence score is `< -0.83`, the system falls back to the Gemini API (`google-genai`) using the same pruned schema.
10. **Sanitization & Validation (`sql_postprocess.py`, `sql_validator.py`):** The SQL is cleaned of markdown artifacts and checked for destructive DML/DDL commands. Only `SELECT` is allowed.
11. **Verification & Repair (`sql_verifier.py`, `sql_repair.py`):** The SQL identifiers are checked against the schema. Slight typos or hallucinated string literals are fuzzy-repaired.
12. **Execution (`sql_executor.py`):** The SQL is routed through the Connector Factory and run against the target database (SQLite/PG/MySQL). 
13. **Execution Repair (Gemini Fallback):** If the database throws an execution error, the exact error trace, schema, and original question are sent to the Gemini API for an automated repair attempt.
14. **Response Formulation (`response_formatter.py`):** The fetched data rows and the successful SQL query are formatted into a standard JSON payload.
15. **Frontend Render:** `ChatComponent.jsx` animates the response, rendering the SQL in a code block and the data in a formatted HTML table.

---

## 5. Architectural Scalability & Adaptability Analysis

### Multi-Database Flexibility
The implementation of the `BaseConnector` Interface and the `connector_factory.py` ensures the core AI pipeline (`schema_linker`, `prompt_builder`, `inference`) is completely isolated from database specifics. Adding support for a new database (e.g., Oracle, SQL Server) only requires creating a new subclass of `BaseConnector` that implements 6 primitives (`get_tables`, `get_columns`, etc.). The AI does not care what DB engine is running underneath.

### Schema Pruning Robustness
For enterprise databases with hundreds of tables, feeding the entire schema to an LLM causes context-window overflow and massive hallucinations. The `schema_linker.py` solves this via a hybrid NLP approach:
1. Token overlap and substring containment.
2. Synonym expansion ("youngest" -> `age`, `dob`).
3. Fuzzy matching via Rapidfuzz.
By scoring and selecting only the Top K (`MAX_RELEVANT_TABLES = 6`) tables—and intelligently carrying over Foreign Key dependencies—the system ensures the T5 model receives a dense, highly relevant context window.

### Fallback Reliability (Self-Healing)
Relying solely on a 770M parameter local model can be brittle. The system's robustness comes from its multi-layered self-healing:
1.  **Proactive Local Repair:** `sql_repair.py` fixes minor typos *before* they crash the DB.
2.  **Reactive API Repair:** If the local model hallucinates SQL syntax that the specific DB dialect rejects, the system catches the DB Exception, packages the stack trace with the schema, and asks Gemini to fix it. This creates a highly resilient system that rarely fails gracefully from the user's perspective.

### Bottlenecks & Future Scalability
1.  **Synchronous API:** The Flask backend currently processes requests synchronously. Long-running model inferences block the server thread. Future scaling requires moving to asynchronous frameworks (FastAPI) or background job queues (Celery).
2.  **VRAM Limits:** The T5-Large model instance is held in memory. For multi-tenant production, model serving should be offloaded to a dedicated inference server (e.g., vLLM or Triton) rather than residing inside the Flask web process.
3.  **Global Connection State:** Currently, `_active_connector` in `db_connector.py` is a global state. To support concurrent users querying *different* databases simultaneously, the connection state must be refactored to be tied to a User Session ID or Request Context.
