# Spec: `retrieve()`

**File:** `retriever.py`
**Status:** Implemented — semantic search with metadata prefiltering.

---

## Purpose

Given a user's natural language query, find the most relevant chunks from the vector store using semantic similarity search. Return them ranked by relevance so that `generate_response()` can use them as context.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's natural language question |
| `n_results` | `int` | Maximum number of chunks to return (default: `N_RESULTS` from `config.py`) |
| `where` | `dict` (optional) | Explicit ChromaDB metadata prefilter. When omitted, the game is inferred from the query text. Defaults to `None`. |

**Output:** `list[dict]`

Each dict in the returned list must contain exactly these keys:

| Key | Type | Description |
|-----|------|-------------|
| `"text"` | `str` | The chunk text |
| `"game"` | `str` | The game name this chunk came from |
| `"distance"` | `float` | Cosine distance score — lower means more similar to the query |

Results should be ordered from most to least relevant (lowest to highest distance). Returns an empty list `[]` if the collection contains no documents.

---

## Design Decisions

---

### Query approach

```
Call _collection.query() with query_texts=[query] (ChromaDB embeds the
query with the same sentence-transformers model used at ingest time),
n_results=n_results, include=["documents", "metadatas", "distances"], and
a where= metadata prefilter.

The prefilter is the key addition: before the semantic search runs, the
query text is scanned for any stored game name (_infer_game_filter()). If a
game is named, the search is restricted to that game's chunks via
where={"game": <name>} (or {"game": {"$in": [...]}} when several games are
named). This keeps results focused and prevents cross-game bleed between
similar rules. Callers can also pass an explicit `where` to override
inference.
```

---

### Return structure

```
One item looks like:

  {
    "text": "Catan — Official Rules Summary > BUILDING\nCities cost 2 Grain + 3 Ore...",
    "game": "Catan",
    "distance": 0.247,
  }

- "text"     comes from results["documents"][0][i]
- "game"     comes from results["metadatas"][0][i]["game"]
- "distance" comes from results["distances"][0][i]

_format_results() zips these three parallel lists into dicts.
```

---

### Handling the nested result structure

```
_collection.query() is built to accept many queries at once, so every
result field is a list-of-lists: one inner list per query. We pass a single
query, so the actual results live at index [0] of documents, metadatas, and
distances. _format_results() reads index [0] of each (guarding against
missing keys) before zipping them together.
```

---

### Relevance threshold

```
retrieve() does not threshold — it returns the top n_results as ranked by
ChromaDB, with their distances, so the caller keeps full information. The
weak-match filtering happens one stage later in generate_response(), using
RELEVANCE_THRESHOLD from config.py. Tradeoff: filtering here would simplify
the generator but would throw away signal (and risk returning nothing);
keeping it in the generator lets that stage decide and fall back gracefully.
```

---

### Edge cases

```
(a) Empty collection — returns [] immediately (guards on _collection.count()).
(b) Query matches no game name — no prefilter is applied, so the search runs
    globally across all games and still returns the closest chunks.
(c) Query names multiple games — prefilter uses {"game": {"$in": [...]}} to
    restrict to exactly those games.
Safety net: if a prefiltered search returns zero rows (e.g. a misdetected
game), retrieve() retries once without the filter so the bot still answers.
```

---

## Implementation Notes

**Test query and top result returned:**

```
Query: How much does a city cost in Catan?
Inferred prefilter: {"game": "Catan"}
Top result game: Catan
Distance score: 0.247
Does it make sense? yes — top chunk is the BUILDING section stating
                    "Cities cost 2 Grain + 3 Ore".
```

**One thing about the query results that surprised you:**

```
Without the prefilter, "What happens when you roll a 7?" pulls chunks from
both Catan and Risk (both mention rolling/7s). Inferring the game from the
query — or naming it explicitly — is what keeps the answer scoped to the
game the user actually means.
```
