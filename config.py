import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"

# --- Embeddings ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Vector store ---
CHROMA_COLLECTION = "rulesbot"
CHROMA_PATH = "./chroma_db"

# --- Retrieval ---
N_RESULTS = 3
# Cosine distance above which a retrieved chunk is treated as a weak match and
# dropped before it reaches the LLM (0 = identical, 2 = opposite).
RELEVANCE_THRESHOLD = 1.0

# --- Documents ---
DOCS_PATH = "./docs"
