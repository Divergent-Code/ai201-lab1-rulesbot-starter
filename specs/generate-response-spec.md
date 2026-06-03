# Spec: `generate_response()`

**File:** `generator.py`
**Status:** Implemented — grounded generation via Groq (`llama-3.3-70b-versatile`).

---

## Purpose

Given a user query and a list of retrieved rule chunks, generate a response that directly answers the question using only the retrieved text as context. The response must be grounded — it should not draw on the model's general knowledge of board games, only on what was retrieved.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's original question |
| `retrieved_chunks` | `list[dict]` | Ranked list of chunks from `retrieve()`, each with `"text"`, `"game"`, and `"distance"` |

**Output:** `str`

A plain string containing the response to show the user. The response should:
- Answer the question using only the retrieved rule text
- Identify which game the answer comes from
- Acknowledge clearly when the answer is not found in the loaded rules

Returns a fallback string (not an error) when `retrieved_chunks` is empty.

---

## Design Decisions

---

### Context formatting

```
Each retrieved chunk is rendered as a labelled, delimited block:

    [Excerpt 1 — Catan]
    <chunk text>

    [Excerpt 2 — Catan]
    <chunk text>

Chunks are labelled by game (so the model can cite correctly) and numbered
for reference. Distance scores are NOT passed to the model — they're used
earlier for filtering, but they're noise to the LLM. Built by
_build_context(); blocks are joined with blank lines.
```

---

### System prompt — grounding instruction

```
"Base your answer strictly on the provided excerpts. Do not use outside
knowledge about these or any other games, even if you think you know it."
plus
"If the excerpts do not contain the answer, say you couldn't find it in the
loaded rules. Do not guess or invent rules."

(See _SYSTEM_PROMPT in generator.py — rules 1 and 2.)
```

---

### System prompt — citation instruction

```
"State which game the answer is about — each excerpt is labelled with its
game." (_SYSTEM_PROMPT rule 3.) This works hand-in-hand with the
"[Excerpt N — Game]" labels in the context block.
```

---

### Fallback behavior

```
When retrieved_chunks is empty, return without calling the LLM:

"I couldn't find anything relevant in the loaded rule books. Try rephrasing
your question — or check that your ingestion pipeline is working."

(Stored as _NO_RESULTS_MESSAGE.) Separately, if the Groq call raises, a
readable "⚠️ I hit an error reaching the language model: ..." string is
returned so the Gradio UI never breaks.
```

---

### Handling low-relevance chunks

```
Chunks with cosine distance above RELEVANCE_THRESHOLD (config.py, 1.0) are
dropped before building context, so unrelated chunks don't mislead the
model. Tradeoff guard: if the threshold filters out everything, fall back to
the full ranked list rather than refusing — the top hit is still the best
available context, and the grounding instruction lets the model decline if
it truly isn't relevant.
```

---

### Message structure

```
Two messages:
- system: the grounding + citation contract (_SYSTEM_PROMPT).
- user:   the formatted context block, then "Question: <query>", then a
          reminder to answer using only the excerpts above.
Sent with temperature=0.2 to favour faithful, low-variance answers.
```

---

## Implementation Notes

**Test query and response:**

```
Query: How much does a city cost in Catan?
Response: "In Catan, a city costs 2 Grain + 3 Ore, built by upgrading an
           existing settlement."
Correctly grounded? yes
Cited the right game? yes (named Catan)

Grounding check — Query: "What is the airspeed velocity of an unladen
swallow?" → "I couldn't find the answer in the loaded rules..." (correctly
refused rather than guessing).
```

**One thing you changed from your original spec after seeing the actual output:**

```
Added the fall-back-to-all-chunks behaviour when the relevance threshold
filters everything out — without it, a borderline-but-valid question could
be refused even though a usable excerpt was retrieved.
```
