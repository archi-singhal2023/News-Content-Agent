import os
from dotenv import load_dotenv

# .env lives at the project root (one level above backend/), so point to it explicitly
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT_DIR, ".env"))

# --- API Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# --- Model selection ---
MODEL_FAST = "llama-3.1-8b-instant"
MODEL_SMART = "llama-3.3-70b-versatile"

# --- Trusted source domains ---
TRUSTED_DOMAINS = [
    "bbc.com",
    "aljazeera.com",
    "ndtv.com",
    "thehindu.com",
    "indianexpress.com",
    "livemint.com",
    "economictimes.indiatimes.com",
    "theguardian.com",
    "apnews.com",
]

# --- RAG settings ---
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_PERSIST_DIR = "./chroma_db"

# --- Caching ---
CACHE_DIR = "./cache"