# RulesBot — Planning Doc

Use this file to record your design decisions as you work through the lab.
There are no wrong answers — write enough that you could explain your reasoning to another group.

---

## Chunking Strategy

**Chunk size:**
300 characters (for fallback sliding window on long sections).

**Overlap:**
50 characters.

**Why this strategy fits rule book text:**
The strategy uses header-aware splitting because rule books are structured into sections (e.g., SETUP, WINNING). Splitting on headers keeps each chunk aligned to a single, self-contained rule rather than arbitrarily slicing the text. The 300-character chunk size is long enough to carry a rule's meaning but short enough to return targeted results. The overlap of 50 characters ensures that rules spanning a boundary within an oversized section stay retrievable intact.

---

## Retrieval Observations

After implementing retrieval, try these test queries and record what comes back:

| Query | Top result game | Does it make sense? |
|-------|----------------|---------------------|
| "How do you win?" | Various (depends on semantic match) | Yes, generic questions without a game name will search across all games because the game metadata prefilter only engages if a game is mentioned. |
| "What happens when you roll a 7?" | Catan | Yes, rolling a 7 is a prominent and unique mechanic (the Robber) in Catan. |
| "Can two players share a route?" | Ticket to Ride | Yes, claiming and sharing routes is specific to Ticket to Ride. |

**Anything surprising?**
Questions that are highly generic return rules from whichever game has the highest semantic similarity to the query. However, the game name prefilter works exceptionally well—if a user asks "How do you win in Catan?", the semantic search is correctly restricted to Catan chunks before it even runs.

---

## Response Quality

After implementing generation, try 2–3 questions and assess the answers:

| Query | Answer accurate? | Properly grounded? | Cited the right game? |
|-------|-----------------|-------------------|----------------------|
| "How do you win in Monopoly?" | Yes | Yes | Yes (Monopoly) |
| "What happens when you roll a 7 in Catan?" | Yes | Yes | Yes (Catan) |

**What would you change about the prompt to improve grounding?**
The current prompt is already quite strict, instructing the model to rely only on the provided excerpts. To improve grounding further, we could explicitly instruct the LLM to provide verbatim quotes from the rulebook where applicable, which would make the citations even easier to verify.
