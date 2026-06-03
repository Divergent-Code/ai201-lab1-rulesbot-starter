# 🎲 RulesBot

> A board game rules assistant — because "just read the rulebook" isn't always helpful at 11pm on game night.

RulesBot answers natural language questions about board game rules using a RAG (Retrieval-Augmented Generation) pipeline. Ask it anything: it retrieves relevant rule passages and generates an answer grounded in the actual text.

**This is the completed RulesBot repository.** The UI, infrastructure, retrieval, and generation pipelines are fully implemented.

---

## Getting Started

### 1. Fork and clone

Fork this repo, then clone your fork locally.

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Mac/Linux
# or: .venv\Scripts\activate   # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` will download the embedding model (~80MB) on first run. This only happens once — it's cached locally afterward.

### 4. Add your Groq API key

```bash
cp .env.example .env
```

Open `.env` and replace `your_key_here` with your key from [console.groq.com](https://console.groq.com). No credit card required.

### 5. Run the app

```bash
python app.py
```

RulesBot will start and open in your browser. It is fully functional and ready to answer your questions based on the loaded rule books.

---

## Project Structure

```
ai201-lab1-rulesbot-starter/
├── app.py              # Gradio UI and startup logic — fully built
├── config.py           # Settings (models, paths, retrieval params) — fully built
├── ingest.py           # Document loading + chunking
├── retriever.py        # Vector store + semantic search
├── generator.py        # LLM response generation
├── docs/               # Board game rule documents (pre-loaded)
│   ├── catan.md
│   ├── clue.md
│   ├── codenames.md
│   ├── monopoly.md
│   ├── pandemic.md
│   ├── risk.md
│   ├── ticket_to_ride.md
│   └── uno.md
├── specs/              # Design documents detailing technical decisions
│   ├── system-design.md         # Complete
│   ├── chunk-document-spec.md   # Complete
│   ├── retrieve-spec.md         # Complete
│   └── generate-response-spec.md # Complete
└── planning.md         # Observations and reflections
```

## Design Documentation

Before diving into the code, read `specs/system-design.md`. It explains the architecture and why the technical decisions were made.

---

## Re-ingesting After Changes

ChromaDB persists to disk in `./chroma_db`. If you change your chunking strategy and want to re-ingest, delete that folder and restart the app:

```bash
rm -rf chroma_db/   # Mac/Linux
# or: rmdir /s chroma_db   # Windows
python app.py
```

---

## Rule Books Included

| Game | File |
|------|------|
| Catan | `docs/catan.md` |
| Clue | `docs/clue.md` |
| Codenames | `docs/codenames.md` |
| Monopoly | `docs/monopoly.md` |
| Pandemic | `docs/pandemic.md` |
| Risk | `docs/risk.md` |
| Ticket to Ride | `docs/ticket_to_ride.md` |
| Uno | `docs/uno.md` |
