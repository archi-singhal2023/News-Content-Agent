"""
Handles chunking article text and storing/retrieving relevant chunks using
TF-IDF + cosine similarity (scikit-learn), NOT neural embeddings.

Why: sentence-transformers requires torch, which is a huge dependency (300+MB,
slow multi-second import, pulls in sympy/transformers/etc.) — this was the
actual root cause of repeated OOM/timeout crashes in production, not chromadb
or FAISS themselves. TF-IDF is pure numpy/scipy under scikit-learn, with a
tiny import footprint, and is fully sufficient for this use case: each
collection is scoped to ONE topic's ~20-60 chunks, and we're just matching an
angle name/query against those chunks — term-overlap similarity is a completely
reasonable and fast way to do that at this scale, not a case that needs deep
semantic embeddings.

Same public interface as before (store_research, retrieve_for_angle), so
pipeline.py, analyst.py, etc. need no changes beyond their imports.
"""
import os
import sys
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHUNK_SIZE, CHUNK_OVERLAP

# In-memory store: collection_name -> {"vectorizer", "matrix", "documents", "metadatas"}
_collections = {}


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """
    Splits text into overlapping word-based chunks.
    Overlap helps preserve context across chunk boundaries.
    """
    words = text.split()
    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += step
    return chunks


def _make_collection_name(topic: str) -> str:
    """Unique name per topic, kept for compatibility with the rest of the codebase."""
    safe_hash = hashlib.md5(topic.encode()).hexdigest()[:12]
    return f"topic_{safe_hash}"


def store_research(topic: str, research_result: dict) -> str:
    """
    Chunks all sources from a research_topic() result and builds a TF-IDF
    matrix over them, scoped to this topic.

    Returns the collection name so it can be queried later via retrieve_for_angle().
    """
    from sklearn.feature_extraction.text import TfidfVectorizer  # deferred import, lightweight

    collection_name = _make_collection_name(topic)

    documents, metadatas = [], []

    for angle_data in research_result["angles"]:
        angle = angle_data["angle"]
        for source in angle_data["sources"]:
            chunks = chunk_text(source["content"])
            for chunk in chunks:
                documents.append(chunk)
                metadatas.append({
                    "angle": angle,
                    "url": source["url"],
                    "title": source["title"],
                })

    if not documents:
        _collections[collection_name] = {"vectorizer": None, "matrix": None,
                                          "documents": [], "metadatas": []}
        print(f"Stored 0 chunks in collection '{collection_name}' (no sources)")
        return collection_name

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    matrix = vectorizer.fit_transform(documents)

    _collections[collection_name] = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "documents": documents,
        "metadatas": metadatas,
    }

    print(f"Stored {len(documents)} chunks across {len(research_result['angles'])} angles "
          f"in collection '{collection_name}'")
    return collection_name


def retrieve_for_angle(collection_name: str, angle: str, query: str, n_results: int = 4) -> list:
    """
    Retrieves the most relevant chunks for a specific angle + query from the collection,
    using TF-IDF cosine similarity restricted to that angle's chunks.
    """
    from sklearn.metrics.pairwise import cosine_similarity  # deferred import

    collection = _collections.get(collection_name)
    if not collection or collection["vectorizer"] is None:
        return []

    angle_indices = [i for i, m in enumerate(collection["metadatas"]) if m["angle"] == angle]
    if not angle_indices:
        return []

    query_vec = collection["vectorizer"].transform([query])
    angle_matrix = collection["matrix"][angle_indices]

    scores = cosine_similarity(query_vec, angle_matrix)[0]
    top_k = min(n_results, len(angle_indices))
    top_local_indices = scores.argsort()[::-1][:top_k]

    retrieved = []
    for local_idx in top_local_indices:
        global_idx = angle_indices[local_idx]
        meta = collection["metadatas"][global_idx]
        retrieved.append({
            "text": collection["documents"][global_idx],
            "url": meta["url"],
            "title": meta["title"],
        })

    return retrieved


def retrieve_across_all(collection_name: str, query: str, n_results: int = 5) -> list:
    """
    Retrieves the most relevant chunks across ALL angles (not restricted to one) —
    used by generate_current_summary() for the broad 'what's happening now' pull.
    """
    from sklearn.metrics.pairwise import cosine_similarity  # deferred import

    collection = _collections.get(collection_name)
    if not collection or collection["vectorizer"] is None:
        return []

    query_vec = collection["vectorizer"].transform([query])
    scores = cosine_similarity(query_vec, collection["matrix"])[0]
    top_k = min(n_results, len(collection["documents"]))
    top_indices = scores.argsort()[::-1][:top_k]

    retrieved = []
    for i in top_indices:
        meta = collection["metadatas"][i]
        retrieved.append({
            "text": collection["documents"][i],
            "url": meta["url"],
            "title": meta["title"],
        })

    return retrieved


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python embed_store.py \"your topic here\"")
    else:
        from agents.researcher import research_topic
        topic = " ".join(sys.argv[1:])
        research_result = research_topic(topic)
        collection_name = store_research(topic, research_result)
        print(f"\nStored under collection: {collection_name}")