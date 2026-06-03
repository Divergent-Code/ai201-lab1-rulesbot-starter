import os
import re
from config import DOCS_PATH


def load_documents():
    """Load all .md rule documents and their sidecar metadata from the docs folder."""
    import json
    documents = []
    for filename in sorted(os.listdir(DOCS_PATH)):
        if filename.endswith(".md"):
            filepath = os.path.join(DOCS_PATH, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            game_name = filename.replace(".md", "").replace("_", " ").title()
            
            # Load sidecar metadata file if it exists
            metadata = {}
            json_filename = filename.replace(".md", ".json")
            json_filepath = os.path.join(DOCS_PATH, json_filename)
            if os.path.exists(json_filepath):
                try:
                    with open(json_filepath, "r", encoding="utf-8") as f_json:
                        metadata = json.load(f_json)
                except Exception as e:
                    print(f"Warning: Failed to load metadata from {json_filepath}: {e}")

            documents.append({
                "game": game_name,
                "filename": filename,
                "text": text,
                "metadata": metadata,
            })
    print(f"Loaded {len(documents)} rule document(s): {[d['game'] for d in documents]}")
    return documents


# A Markdown ATX header: 1-6 leading '#', a space, then the heading text.
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def split_by_headers(text):
    """
    Split a Markdown document into sections at ATX headers (#, ##, ...).

    Each section is returned as a (header_path, body) tuple, where:
      - header_path is the breadcrumb of the active headers leading to this
        section, e.g. "Catan — Official Rules Summary > BUILDING". This keeps
        a chunk aware of where in the document it came from.
      - body is the text beneath that header, up to the next header of an
        equal-or-shallower level.

    Text that appears before the first header (rare) is emitted with an empty
    header_path so nothing is silently dropped.
    """
    sections = []
    stack = []  # list of (level, title) for the currently active headers
    body_lines = []

    def header_path():
        return " > ".join(title for _, title in stack)

    def flush():
        body = "\n".join(body_lines).strip()
        if body:
            sections.append((header_path(), body))

    for line in text.splitlines():
        match = _HEADER_RE.match(line)
        if match:
            # Close out the section accumulated so far before opening the next.
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            # Pop any headers at the same or deeper level, then push this one,
            # so the stack always reflects the path from the root to here.
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            body_lines = []
        else:
            body_lines.append(line)

    flush()
    return sections


def _sliding_window(text, chunk_size, overlap, min_length):
    """
    Sliding-window character splitter, used as a fallback for sections that are
    too long to embed as a single chunk.

      - Sections that already fit within chunk_size stay intact (one chunk per
        rule) — this is the common case and avoids splitting mid-sentence.
      - Longer sections are walked in windows of chunk_size, advancing by
        (chunk_size - overlap) so adjacent windows share `overlap` characters
        and a rule spanning a boundary can still be retrieved intact.
      - Pieces shorter than min_length are dropped as low-value fragments.
    """
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if len(text) >= min_length else []

    pieces = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(text):
        piece = text[start:start + chunk_size].strip()
        if len(piece) >= min_length:
            pieces.append(piece)
        start += step
    return pieces


def chunk_document(text, game_name, metadata=None):
    """
    Split a rule document into chunks ready for embedding.

    Strategy: header-aware splitting.
      The rule books are structured Markdown — an H1 title followed by H2
      sections like OVERVIEW, SETUP, BUILDING, WINNING. Splitting on those
      headers keeps each chunk aligned to a single, self-contained rule rather
      than slicing the text at arbitrary character offsets. The section's
      header breadcrumb is prepended to the chunk text so the embedded content
      carries the context of which rule it describes, which sharpens retrieval.

    Sizing knobs (applied per section, not across the whole document):
      - chunk_size = 300 characters: long enough to carry one rule's meaning,
        short enough to return targeted results. Sections within this size are
        kept whole; longer ones fall back to a sliding window.
      - overlap = 50 characters: shared window between sub-chunks of an
        oversized section so a rule that spans a boundary stays retrievable.
      - min_length = 50 characters: drops whitespace artifacts and very short
        fragments that add noise without useful semantic content.

    Returns a list of dicts, each with:
      - "text"     : the chunk text, prefixed with its header path (str)
      - "game"     : the game name, e.g. "Catan" (str)
      - "chunk_id" : a unique identifier, e.g. "catan_0", "catan_1" (str)
      - "metadata" : the game's metadata dict (optional)
    """
    chunk_size = 300
    overlap = 50
    min_length = 50

    chunks = []
    prefix = game_name.lower().replace(" ", "_")
    counter = 0

    for header_path, body in split_by_headers(text):
        # Anchor each chunk to its section heading. The breadcrumb is short,
        # so reserve room for it and keep the body within chunk_size overall.
        header_prefix = f"{header_path}\n" if header_path else ""
        body_chunk_size = max(chunk_size - len(header_prefix), min_length)

        for piece in _sliding_window(body, body_chunk_size, overlap, min_length):
            chunk_data = {
                "text": f"{header_prefix}{piece}".strip(),
                "game": game_name,
                "chunk_id": f"{prefix}_{counter}",
            }
            if metadata:
                chunk_data["metadata"] = metadata
            chunks.append(chunk_data)
            counter += 1

    return chunks
