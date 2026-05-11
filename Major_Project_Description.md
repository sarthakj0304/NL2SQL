# NL2SQL: Transformer-Based Natural Language to SQL Engine
## Major Project Description

### 1. Introduction
The **NL2SQL** system is an advanced, full-stack web application designed to democratize data access. In modern enterprises, vast amounts of critical data are locked behind relational databases (RDBMS), requiring specialized knowledge of Structured Query Language (SQL) to retrieve. This creates a bottleneck where non-technical stakeholders (managers, analysts, executives) must rely on data engineers to answer simple business questions. 

This project solves that bottleneck by providing a conversational interface where users can ask questions in plain English. The system intelligently translates these questions into complex, syntactically correct SQL queries, executes them against the connected database, and returns the data in a human-readable format.

### 2. Core Objectives
- **Accessibility:** Remove the technical barrier to data extraction by allowing natural language queries.
- **Database Agnosticism:** Build a system that is not hardcoded to a single schema. It must dynamically introspect any uploaded or connected database.
- **Multi-Dialect Support:** Support the three major relational database engines natively: SQLite, PostgreSQL, and MySQL.
- **Privacy and Local Execution:** Prioritize local, on-premise Machine Learning inference using open-source models to prevent sensitive schema data from leaking to third-party cloud APIs by default.
- **High Reliability:** Implement a resilient, multi-stage pipeline with automated error recovery (self-healing) so the user rarely sees a crash or syntax error.

### 3. System Architecture
The application is divided into a modern React frontend and a robust Python Flask backend, connected via REST APIs. 

#### 3.1. Frontend Interface (React + Vite + Tailwind CSS)
The frontend is designed to feel like a premium, modern AI chat application.
*   **Database Connection Hub:** A multi-tab interface allows users to either drag-and-drop a local SQLite `.db` file or enter Data Source Name (DSN) credentials to connect securely to remote PostgreSQL or MySQL instances.
*   **Conversational UI:** A dynamic chat interface where users input questions. The UI handles asynchronous loading states, micro-animations (via Framer Motion), and renders the system's response containing both the generated SQL code (with syntax highlighting) and the extracted data in a responsive table.

#### 3.2. Backend Engine (Flask + PyTorch + Transformers)
The backend is a sophisticated pipeline composed of several specialized modules:

1.  **Database Abstraction Layer (Connector Factory):** Instead of tying the logic to SQLite, the system uses a Factory Design Pattern. When a user connects a database, the factory instantiates a specific `BaseConnector` (SQLite, Postgres, or MySQL). The rest of the AI pipeline talks only to this abstract interface, making the system highly extensible.
2.  **Dynamic Schema Introspection:** The active connector queries the database's internal metadata tables (e.g., `information_schema`) to extract table names, column names, data types, primary/foreign key constraints, and a few sample values per column.
3.  **NLP Schema Linking:** Enterprise databases can have hundreds of tables. Feeding all of them to an AI model causes "context bloat" and degrades accuracy. The system uses `rapidfuzz` and token-overlap algorithms to score how relevant each table is to the user's question, pruning the schema down to only the top K most relevant tables.
4.  **Prompt Engineering:** The pruned schema and the user's question are serialized into a specific format expected by the Spider NLP benchmark dataset (`<question> | <db_id> | <schema>`). Hints regarding aggregation (COUNT, SUM) or sorting are also injected.
5.  **Primary Inference (Local T5 Model):** The prompt is fed into `tscholak/3vnuv1vf`, a 770-million parameter T5-Large model fine-tuned specifically for SQL generation. It uses **Beam Search** (`k=4`) to explore multiple generation paths simultaneously, returning the most probable SQL sequence and a confidence score.
6.  **Security and Validation:** The generated SQL passes through strict regex gates that block DML/DDL commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`). Only `SELECT` queries are permitted.
7.  **Self-Healing & Fallback:** 
    *   *Proactive Repair:* If the model hallucinates a column name slightly, the system fuzzy-matches it against the real schema and fixes the typo.
    *   *Reactive Repair (Gemini API):* If the local model yields a low confidence score, or if the generated SQL causes a database execution error, the system automatically falls back to the Google Gemini 1.5 Pro API. It provides Gemini with the exact database error and the schema, asking it to repair the query.

### 4. Innovation and Impact
Unlike traditional BI tools that require drag-and-drop report building, or naive LLM wrappers that hallucinate frequently on large schemas, this project implements a **Hybrid, Schema-Aware Pipeline**. 

By combining the privacy and speed of a specialized local T5 model with the immense reasoning capabilities of a frontier LLM (Gemini) acting solely as a fallback/repair agent, the system achieves state-of-the-art accuracy while maintaining a low operating cost and high data security. The dynamic Connector Factory ensures that this single application can act as a universal English-to-SQL translator for virtually any relational database environment.
