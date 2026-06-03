from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, RELEVANCE_THRESHOLD

_client = Groq(api_key=GROQ_API_KEY)

# The grounding contract. Kept strict on purpose: a confident wrong answer is
# worse than an honest "I couldn't find it", so the model is told to stay
# inside the provided excerpts and to name the game it's answering about.
_SYSTEM_PROMPT = (
    "You are RulesBot, an assistant that answers board-game rules questions.\n"
    "Answer using ONLY the rule excerpts provided in the user's message. Follow these rules:\n"
    "1. Base your answer strictly on the provided excerpts. Do not use outside "
    "knowledge about these or any other games, even if you think you know it.\n"
    "2. If the excerpts do not contain the answer, say you couldn't find it in "
    "the loaded rules. Do not guess or invent rules.\n"
    "3. State which game the answer is about — each excerpt is labelled with its game.\n"
    "4. Be concise and direct, and phrase the answer in plain language."
)

_NO_RESULTS_MESSAGE = (
    "I couldn't find anything relevant in the loaded rule books. "
    "Try rephrasing your question — or check that your ingestion pipeline is working."
)


def _build_context(chunks):
    """Format retrieved chunks into a labelled, delimited context block."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(f"[Excerpt {i} — {chunk['game']}]\n{chunk['text']}")
    return "\n\n".join(blocks)


def generate_response(query, retrieved_chunks):
    """
    Generate a grounded answer from retrieved rule chunks.

    `retrieved_chunks` is the list returned by retrieve(). Each item is a dict
    with "text", "game", and "distance" (cosine distance; lower = closer).

    The response answers using only the retrieved context, names the game it
    came from, and falls back to an honest "not found" message when there is
    nothing relevant to ground the answer in.
    """
    if not retrieved_chunks:
        return _NO_RESULTS_MESSAGE

    # Drop weak matches so unrelated chunks don't mislead the model. If the
    # threshold filters everything out, fall back to the full ranked list
    # rather than refusing — the top hit is still the best available context.
    relevant = [c for c in retrieved_chunks if c.get("distance", 0) <= RELEVANCE_THRESHOLD]
    if not relevant:
        relevant = retrieved_chunks

    context = _build_context(relevant)
    user_message = (
        f"Rule excerpts:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer the question using only the excerpts above."
    )

    try:
        completion = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,  # low: factual, grounded answers over creative ones
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        # The Groq call is the only network hop in the chat path — surface a
        # readable message instead of letting the exception break the UI.
        return f"⚠️ I hit an error reaching the language model: {e}"
