import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL, N_RESULTS

# Embedding function and ChromaDB client are initialized once at module load.
# sentence-transformers downloads the model on first use — this may take
# 30–60 seconds the very first time. Subsequent runs use a local cache.
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    embedding_function=_ef,
    metadata={"hnsw:space": "cosine"},
)


def get_collection():
    """Return the ChromaDB collection. Used by app.py during ingestion."""
    return _collection


def embed_and_store(chunks):
    """
    Embed a list of chunks and store them in the vector database.

    This function is already implemented — read through it before moving on.

    _collection.add() takes three parallel lists built from the chunks
    returned by chunk_document():
      - documents : raw text strings — ChromaDB's embedding function converts
                    these to vectors automatically using sentence-transformers
      - metadatas : one dict per chunk, stored alongside the vector so that
                    retrieve() can surface which game a result came from
      - ids       : the unique chunk_id strings used to identify each entry

    You don't generate embeddings manually here — you hand over the text
    and ChromaDB handles the vector math.
    """
    metadatas = []
    for c in chunks:
        meta = {"game": c["game"]}
        if "metadata" in c and c["metadata"]:
            for k, v in c["metadata"].items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                elif isinstance(v, list):
                    meta[k] = ", ".join(map(str, v))
                elif isinstance(v, dict):
                    import json
                    meta[k] = json.dumps(v)
        metadatas.append(meta)

    _collection.add(
        documents=[c["text"] for c in chunks],
        metadatas=metadatas,
        ids=[c["chunk_id"] for c in chunks],
    )
    print(f"Stored {_collection.count()} total chunks in the vector database.")


# Cache of the distinct game names stored in the collection. Built lazily on
# first use so query-time game inference doesn't re-scan the store every call.
_known_games = None


def _games_in_store():
    """Return the set of distinct game names present in the vector store."""
    global _known_games
    if _known_games is None:
        records = _collection.get(include=["metadatas"])
        _known_games = {
            m["game"]
            for m in (records.get("metadatas") or [])
            if m and m.get("game")
        }
    return _known_games


def _infer_game_filter(query):
    """
    Build a metadata prefilter from the games mentioned in the query.

    Matches stored game names against the query text so a question like
    "How do you build a city in Catan?" is restricted to Catan's chunks
    before the semantic search even runs. Returns a ChromaDB `where` dict, or
    None when no game is confidently identified (so search stays global).
    """
    lowered = query.lower()
    matched = sorted(g for g in _games_in_store() if g.lower() in lowered)

    if not matched:
        return None
    if len(matched) == 1:
        return {"game": matched[0]}
    # More than one game named — restrict to just those.
    return {"game": {"$in": matched}}


def _format_results(results):
    """Flatten ChromaDB's per-query nested result lists into a list of dicts."""
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    formatted = []
    for text, meta, distance in zip(documents, metadatas, distances):
        formatted.append({
            "text": text,
            "game": (meta or {}).get("game", "Unknown"),
            "distance": distance,
        })
    return formatted


def retrieve(query, n_results=N_RESULTS, where=None):
    """
    Find the most relevant rule chunks for a user's question.

    Runs a semantic search over the vector store, optionally narrowed by a
    metadata prefilter:
      - If `where` is given, it is used directly as ChromaDB's filter.
      - Otherwise the game is inferred from the query text (e.g. a question
        mentioning "Catan" is restricted to Catan's chunks). This keeps
        retrieval focused and avoids cross-game bleed between similar rules.
      - If a prefiltered search comes back empty (e.g. the game was guessed
        wrong, or that game has no matching rule), it falls back to an
        unfiltered search so the bot can still answer.

    Returns a list of dicts, each with:
      - "text"     : the chunk text
      - "game"     : the game name (pulled from metadata)
      - "distance" : the similarity score (lower = more similar for cosine)
    """
    if _collection.count() == 0:
        return []

    where_filter = where if where is not None else _infer_game_filter(query)

    results = _collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )
    formatted = _format_results(results)

    # Fall back to an unfiltered search if the prefilter excluded everything.
    if not formatted and where_filter is not None:
        results = _collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        formatted = _format_results(results)

    return formatted
