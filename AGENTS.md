# AGENTS.md — RulesBot

> This file is intended for AI coding agents. If you are reading this, you know nothing about the project yet. Everything below is derived from the actual codebase — no assumptions, no generalizations.

---

## Project Overview

**RulesBot** is a Retrieval-Augmented Generation (RAG) chatbot that answers questions about board game rules. It ingests plain-text rule books, chunks them, embeds the chunks into a local vector store, and uses semantic search + an LLM to produce grounded, cited responses.

This repository is a **lab starter project** designed for incremental implementation across three milestones. Some modules are fully implemented; others are deliberately stubbed and marked with TODOs for students (or agents) to complete.

- **Language**: Python 3
- **UI**: Gradio web interface (launches locally on port 7860 by default)
- **Total source files**: 5 Python modules + `requirements.txt` + `.env.example`
- **No build system**, **no test suite**, **no CI/CD**, **no Docker** — this is an educational starter repo.

---

## Technology Stack

| Layer | Technology | Version (pinned) | Purpose |
|-------|-----------|------------------|---------|
| LLM API | Groq | `groq==0.15.0` | Fast inference via API (`llama-3.3-70b-versatile`) |
| Embeddings | sentence-transformers | `sentence-transformers==3.4.1` | Local embedding model (`all-MiniLM-L6-v2`, 384-dim) |
| Vector DB | ChromaDB | `chromadb==1.5.5` | Persistent local vector store with cosine similarity |
| UI | Gradio | `gradio==5.20.1` | Web-based chat interface |
| Config | python-dotenv | `python-dotenv==1.0.1` | `.env` file loading |

---

## File Structure

```
.
├── app.py                     # Gradio UI + startup orchestration
├── config.py                  # Centralized configuration constants
├── generator.py               # LLM response generation (partial stub)
├── ingest.py                  # Document loading + chunking (fully implemented)
├── retriever.py               # Vector store init + retrieval (partial stub)
├── requirements.txt           # Pinned Python dependencies
├── .env.example               # Template for GROQ_API_KEY
├── .gitignore                 # Ignores .env, venvs, chroma_db/, __pycache__
├── README.md                  # Human-facing setup guide
├── planning.md                # Student design-decision template
├── docs/                      # 8 plain-text rule books
│   ├── catan.txt
│   ├── clue.txt
│   ├── codenames.txt
│   ├── monopoly.txt
│   ├── pandemic.txt
│   ├── risk.txt
│   ├── ticket_to_ride.txt
│   └── uno.txt
└── specs/                     # Design specifications
    ├── system-design.md       # Architecture overview + build-status matrix
    ├── chunk-document-spec.md # Chunking design rationale (pre-filled)
    ├── retrieve-spec.md       # Retrieval design template (blank)
    └── generate-response-spec.md # Generation design template (blank)
```

---

## How to Run

1. **Create a virtual environment** (strongly recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   On first run, `sentence-transformers` will download `all-MiniLM-L6-v2` (~80 MB) to its local cache.

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and set GROQ_API_KEY=your_key_here
   ```
   Get a free key at https://console.groq.com.

4. **Launch the app**:
   ```bash
   python app.py
   ```
   - First run: parses `docs/`, chunks the text, embeds it, and persists to `./chroma_db`.
   - Subsequent runs: skips ingestion if the ChromaDB collection already has data.
   - Gradio will print a local URL (usually `http://127.0.0.1:7860`).

5. **Re-ingest** (if you change chunking logic or add new docs):
   ```bash
   rm -rf chroma_db/
   python app.py
   ```

---

## Architecture & Data Flow

The codebase follows a **4-stage modular pipeline** with clear separation of concerns:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Ingest    │ →  │  Retrieve   │ →  │   Generate  │ →  │     UI      │
│  ingest.py  │    │ retriever.py│    │ generator.py│    │   app.py    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Module Responsibilities

- **`config.py`** — Single source of truth. Exports constants loaded from environment variables (e.g., `GROQ_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, `CHROMA_COLLECTION`, `CHROMA_PATH`, `N_RESULTS`, `DOCS_PATH`). No runtime mutation.
- **`ingest.py`** — Data ingestion layer.
  - `load_documents()`: Reads all `.txt` files from `DOCS_PATH`, derives game names from filenames (`ticket_to_ride.txt` → `"Ticket To Ride"`), returns dicts with `game`, `filename`, `text`.
  - `chunk_document(text, game_name)`: Sliding-window character chunker (size=300, overlap=50, min_length=50). Returns chunks as `{"text": ..., "game": ..., "chunk_id": ...}`.
- **`retriever.py`** — Vector storage & retrieval layer.
  - Initializes `SentenceTransformerEmbeddingFunction`, `chromadb.PersistentClient`, and a collection with `metadata={"hnsw:space": "cosine"}` at module import time.
  - `embed_and_store(chunks)`: Adds documents + metadata + IDs to ChromaDB. **Fully implemented.**
  - `retrieve(query, n_results)`: **STUB** — currently returns `[]`. Intended to call `_collection.query()` and return ranked dicts with `text`, `game`, `distance`.
- **`generator.py`** — Generation layer.
  - Initializes `Groq` client at module import time.
  - `generate_response(query, retrieved_chunks)`: **STUB** — returns a fallback message when `retrieved_chunks` is empty, otherwise returns a placeholder string. Intended to build a grounded prompt and call the Groq chat-completions API.
- **`app.py`** — Presentation & orchestration layer.
  - `run_ingestion()`: Idempotent loader. Skips if `collection.count() > 0`.
  - `chat(message, history)`: Thin wrapper calling `retrieve()` then `generate_response()`.
  - Gradio `Blocks` UI with a themed `ChatInterface`, 9 built-in example queries, and a sidebar listing loaded rule books.

### Design Patterns in Use

- **Module-level singletons**: `_client`, `_ef`, `_collection` are initialized once at import time to avoid repeated setup cost.
- **Lazy / idempotent ingestion**: `run_ingestion()` checks collection count before doing any work, making restarts fast.
- **Immutable config**: `config.py` exports constants; no function mutates them.

---

## Implementation Status (What Is Done vs. Stubbed)

| Milestone | File | Function / Task | Status |
|-----------|------|-----------------|--------|
| Pre-built | `ingest.py` | `chunk_document()` | ✅ Complete |
| Pre-built | `retriever.py` | `embed_and_store()` | ✅ Complete |
| Milestone 2 | `retriever.py` | `retrieve()` | 🔲 Stub — must implement ChromaDB query + result formatting |
| Milestone 2 | `specs/retrieve-spec.md` | Fill design decisions | 🔲 Blank template |
| Milestone 3 | `generator.py` | `generate_response()` | 🔲 Stub — must implement prompt construction + Groq API call |
| Milestone 3 | `specs/generate-response-spec.md` | Fill design decisions | 🔲 Blank template |

**Consequence**: The app launches and the UI renders, but every chat query currently returns either a fallback "no results" message or a placeholder "not yet implemented" string because `retrieve()` returns an empty list.

---

## Code Style Guidelines

There is **no enforced linter or formatter** in this project (no `ruff`, `black`, `flake8`, or `mypy` configs). However, the existing code follows these informal conventions:

- **Docstrings**: Google-style docstrings with inline TODO markers for milestones (`# TODO (Milestone 2): ...`).
- **Private module globals**: Prefixed with underscore (`_client`, `_ef`, `_collection`) to indicate they are not part of the public API.
- **String formatting**: Uses f-strings consistently.
- **Naming**: `snake_case` for functions and variables, `PascalCase` for Gradio component classes.
- **Chunk IDs**: Format is `{lowercase_underscored_game}_{counter}` (e.g., `ticket_to_ride_0`).
- **Game name normalization**: `filename.replace(".txt", "").replace("_", " ").title()`.

When editing, preserve these conventions. Do not introduce type hints unless the surrounding file already uses them (currently none do).

---

## Testing Instructions

**There is no test suite.** This repo contains zero test files, zero testing frameworks, and zero test commands.

The intended "testing" workflow is manual:

1. Launch the app: `python app.py`
2. Send example queries via the Gradio UI (or the 9 built-in examples).
3. Observe whether `retrieve()` returns relevant chunks.
4. Observe whether `generate_response()` produces a coherent, grounded answer that cites the retrieved chunks.
5. For debugging, add `print()` statements or inspect `chroma_db/` contents directly.

If you add automated tests, place them in a `tests/` directory and update this section.

---

## Security Considerations

- **API keys are loaded from `.env`** via `python-dotenv`. The `.env` file is listed in `.gitignore` and must never be committed.
- **No input sanitization** is currently performed on user chat messages before they are passed to `retrieve()` or `generate_response()`. If you implement `generate_response()`, be aware that user input will reach the LLM API.
- **No rate limiting** or authentication on the Gradio interface. By default it binds to `127.0.0.1`, but Gradio’s `share=True` mode creates a public tunnel — use with caution.
- **Local vector store**: `chroma_db/` is a local SQLite + embedding cache on disk. It is also `.gitignore`d.
- **Dependencies are pinned** in `requirements.txt`, but there is no automated vulnerability scanning or SBOM generation.

---

## Key Files for Agents to Know

| File | Why it matters |
|------|----------------|
| `config.py` | Change models, API keys, paths, and retrieval counts here. |
| `retriever.py` | **Primary work area for Milestone 2.** Implement `retrieve()`. |
| `generator.py` | **Primary work area for Milestone 3.** Implement `generate_response()`. |
| `ingest.py` | Already complete; only modify if you change chunking strategy. |
| `app.py` | UI wiring. Usually does not need changes unless you alter the Gradio layout. |
| `specs/*.md` | Design specs that should be updated as you make implementation decisions. |
| `docs/*.txt` | Source documents. Add new `.txt` files here to expand the knowledge base. |

---

## Notes & Pitfalls

- **First-run download**: `sentence-transformers` downloads `all-MiniLM-L6-v2` on first use. The machine needs internet access for this initial download (and for Groq API calls).
- **ChromaDB persistence**: Deleting `./chroma_db` is the only way to force re-ingestion. The app will not auto-detect new docs in `docs/` after the first run.
- **Stub behavior**: Because `retrieve()` returns `[]`, `generate_response()` never reaches its "real" LLM branch during normal chat usage. You must implement `retrieve()` first before `generate_response()` can be meaningfully tested.
- **No async/await**: The codebase is entirely synchronous. Groq, ChromaDB, and Gradio are used in blocking mode.
