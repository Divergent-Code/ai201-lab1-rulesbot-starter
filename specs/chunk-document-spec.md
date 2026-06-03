# Spec: `chunk_document()`

**File:** `ingest.py`
**Status:** Implemented — header-aware splitting (see `chunk_document()` and the `split_by_headers()` / `_sliding_window()` helpers).

---

## Purpose

Split a single rule book document into smaller chunks suitable for embedding and semantic retrieval. Each chunk should carry enough context to be meaningful on its own when retrieved in response to a user query.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | The full text of a rule book document |
| `game_name` | `str` | The name of the game this document belongs to (e.g., `"Catan"`) |
| `metadata` | `dict` (optional) | Sidecar metadata for the game (from the `.json` file alongside the `.md`). Attached to every chunk so the vector store can prefilter on it. Defaults to `None`. |

**Output:** `list[dict]`

Each dict in the returned list contains these keys:

| Key | Type | Description |
|-----|------|-------------|
| `"text"` | `str` | The chunk text, prefixed with its header breadcrumb |
| `"game"` | `str` | The game name (passed through from `game_name`) |
| `"chunk_id"` | `str` | A unique identifier for this chunk (e.g., `"catan_0"`, `"catan_1"`) |
| `"metadata"` | `dict` | Present only when `metadata` was provided; the game's sidecar metadata |

Returns an empty list `[]` if the input text is empty or produces no valid chunks.

---

## Design Decisions

---

### Splitting approach

```
Header-aware splitting. The rule books are structured Markdown — an H1
title followed by H2 sections (OVERVIEW, SETUP, BUILDING, WINNING, ...).
`split_by_headers()` walks the text line by line, detects ATX headers
(#, ##, ...), and emits one section per header along with its header
breadcrumb (e.g. "Catan — Official Rules Summary > BUILDING"). Each
section becomes a chunk, with the breadcrumb prepended to the chunk text
so the embedded content knows which rule it describes.

Sections that already fit within `chunk_size` are kept whole — one chunk
per rule. Only oversized sections fall back to `_sliding_window()`, a
character-window splitter, so no single chunk exceeds `chunk_size`.
```

---

### Chunk size

```
300 characters, applied per section (the header prefix is reserved out of
this budget so the total chunk stays within 300). Most rule-book sections
fit in a single chunk at this size; the few that don't are windowed. Going
smaller would fragment individual rules; going larger would merge unrelated
rules into one chunk, making retrieval less precise.
```

---

### Overlap

```
50 characters of overlap, used only when an oversized section is windowed.
If a rule falls exactly on a sub-chunk boundary, neither piece alone
contains the full rule. Overlap duplicates the tail of each piece at the
start of the next so boundary-spanning content can still be retrieved
intact. Sections that fit whole need no overlap at all.
```

---

### Minimum chunk length

```
50 characters. Chunks shorter than this are discarded. Very short segments
typically contain only whitespace or punctuation — content that has no
semantic signal and would just add noise to the vector database.
```

---

### Rationale

```
Rule books are already organized by topic via headers, so splitting on
those headers aligns each chunk with a coherent, self-contained rule —
exactly the unit a question like "What happens when you roll a 7?" wants to
retrieve. Prepending the header breadcrumb gives every chunk context about
which game and section it belongs to, which sharpens both embedding quality
and the citation the LLM can produce. Pure character-window splitting was
the original approach but was indifferent to structure and could split a
rule mid-sentence; header-aware splitting keeps rules intact and only
windows the rare oversized section.
```

---

### Known limitations

```
A section longer than `chunk_size` is still windowed by character offset,
so within those (uncommon) sections a rule can be split mid-sentence —
overlap mitigates but doesn't eliminate this. Documents without Markdown
headers degrade to a single section that gets windowed throughout (i.e.
back to the old behavior). The header regex only matches ATX headers
(`#`-style), not Setext (underline) headers.
```

---

## Implementation Notes

**Actual chunk count produced across all 8 rule books:**

```
201 chunks total:
  Catan 23, Clue 28, Codenames 21, Monopoly 32,
  Pandemic 24, Risk 29, Ticket To Ride 22, Uno 22.
No chunk exceeds 300 characters; all chunk_ids are unique per game.
```

**One thing that surprised you or didn't match your expectations:**

```
Most sections fit within 300 characters and stay whole, so very few chunks
ever hit the sliding-window fallback — the header structure does almost all
of the splitting work on its own.
```
