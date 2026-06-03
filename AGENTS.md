# AGENTS.md — RulesBot

> This file is intended for AI coding agents. If you are reading this, you know nothing about the project yet. Everything below is derived from the actual codebase — no assumptions, no generalizations.

---

## Project Overview

**RulesBot** is a Retrieval-Augmented Generation (RAG) chatbot that answers questions about board game rules. It ingests plain-text rule books, chunks them, embeds the chunks into a local vector store, and uses semantic search + an LLM to produce grounded, cited responses.

This repository began as a **lab starter project** designed for incremental implementation across three milestones. All three milestones are now implemented: header-aware chunking (`ingest.py`), semantic retrieval with metadata prefiltering (`retriever.py`), and grounded generation (`generator.py`).

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
│   ├── catan.md
│   ├── clue.md
│   ├── codenames.md
│   ├── monopoly.md
│   ├── pandemic.md
│   ├── risk.md
│   ├── ticket_to_ride.md
│   └── uno.md
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
  - `load_documents()`: Reads all `.md` files from `DOCS_PATH`, loads any matching `.json` sidecar as `metadata`, derives game names from filenames (`ticket_to_ride.md` → `"Ticket To Ride"`), returns dicts with `game`, `filename`, `text`, `metadata`.
  - `chunk_document(text, game_name, metadata=None)`: **Header-aware splitter.** Splits Markdown on ATX headers (`split_by_headers()`), making one chunk per section with its header breadcrumb prepended; oversized sections fall back to a character sliding window (`_sliding_window()`, size=300, overlap=50, min_length=50). Returns chunks as `{"text": ..., "game": ..., "chunk_id": ...}` (plus `"metadata"` when provided).
- **`retriever.py`** — Vector storage & retrieval layer.
  - Initializes `SentenceTransformerEmbeddingFunction`, `chromadb.PersistentClient`, and a collection with `metadata={"hnsw:space": "cosine"}` at module import time.
  - `embed_and_store(chunks)`: Adds documents + metadata + IDs to ChromaDB, flattening sidecar metadata (lists → comma strings, dicts → JSON) into queryable scalar fields. **Fully implemented.**
  - `retrieve(query, n_results, where=None)`: **Implemented.** Runs `_collection.query()` with a game metadata prefilter — inferred from the query text via `_infer_game_filter()` unless `where` is passed — and returns ranked dicts with `text`, `game`, `distance`. Falls back to an unfiltered search if a prefilter returns nothing.
- **`generator.py`** — Generation layer.
  - Initializes `Groq` client at module import time.
  - `generate_response(query, retrieved_chunks)`: **Implemented.** Returns `_NO_RESULTS_MESSAGE` when `retrieved_chunks` is empty; otherwise drops weak matches (distance > `RELEVANCE_THRESHOLD`), builds a labelled `[Excerpt N — Game]` context block, and calls the Groq chat-completions API with a strict grounding/citation system prompt (`temperature=0.2`). Wraps the API call to return a readable error string instead of throwing.
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
| Pre-built | `ingest.py` | `chunk_document()` | ✅ Complete — header-aware splitting |
| Pre-built | `retriever.py` | `embed_and_store()` | ✅ Complete |
| Milestone 2 | `retriever.py` | `retrieve()` | ✅ Complete — ChromaDB query + metadata prefilter + result formatting |
| Milestone 2 | `specs/retrieve-spec.md` | Design decisions | ✅ Filled |
| Milestone 3 | `generator.py` | `generate_response()` | ✅ Complete — grounded prompt + Groq API call |
| Milestone 3 | `specs/generate-response-spec.md` | Design decisions | ✅ Filled |

**Consequence**: The full RAG pipeline is wired end to end — a chat query is embedded, prefiltered by game, semantically retrieved, and answered with a grounded, cited response. The fallback "no results" message only appears when retrieval genuinely finds nothing relevant.

---

## Code Style Guidelines

There is **no enforced linter or formatter** in this project (no `ruff`, `black`, `flake8`, or `mypy` configs). However, the existing code follows these informal conventions:

- **Docstrings**: Google-style docstrings with inline TODO markers for milestones (`# TODO (Milestone 2): ...`).
- **Private module globals**: Prefixed with underscore (`_client`, `_ef`, `_collection`) to indicate they are not part of the public API.
- **String formatting**: Uses f-strings consistently.
- **Naming**: `snake_case` for functions and variables, `PascalCase` for Gradio component classes.
- **Chunk IDs**: Format is `{lowercase_underscored_game}_{counter}` (e.g., `ticket_to_ride_0`).
- **Game name normalization**: `filename.replace(".md", "").replace("_", " ").title()`.

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
| `config.py` | Change models, API keys, paths, retrieval counts, and `RELEVANCE_THRESHOLD` here. |
| `retriever.py` | Semantic search + game metadata prefiltering (`retrieve()`, `_infer_game_filter()`). |
| `generator.py` | Grounded prompt construction + Groq call (`generate_response()`, `_SYSTEM_PROMPT`). |
| `ingest.py` | Header-aware chunking (`chunk_document()`, `split_by_headers()`). Modify if you change chunking strategy. |
| `app.py` | UI wiring. Usually does not need changes unless you alter the Gradio layout. |
| `specs/*.md` | Design specs that should be updated as you make implementation decisions. |
| `docs/*.md` | Source documents. Add new `.md` files here to expand the knowledge base. |

---

## Notes & Pitfalls

- **First-run download**: `sentence-transformers` downloads `all-MiniLM-L6-v2` on first use. The machine needs internet access for this initial download (and for Groq API calls).
- **ChromaDB persistence**: Deleting `./chroma_db` is the only way to force re-ingestion. The app will not auto-detect new docs in `docs/` after the first run.
- **Re-ingest after chunking changes**: The chunking strategy is header-aware. If you change `chunk_document()`, delete `./chroma_db` and restart so the store is rebuilt — the app skips ingestion when the collection is already populated.
- **No async/await**: The codebase is entirely synchronous. Groq, ChromaDB, and Gradio are used in blocking mode.
