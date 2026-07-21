"""
Handles chunking article text and storing/retrieving it via FAISS,
using local, free sentence-transformer embeddings (no API cost).

Replaces chromadb — same public interface (store_research, retrieve_for_angle),
but with a much lighter dependency footprint (no telemetry/grpc/auth machinery),
which matters on memory-constrained deployments.

Storage is in-memory only (no persistence across restarts) — appropriate for
this use case, since each store_research() call is scoped to one topic and
queried within the same request/process lifetime, not looked up days later.
"""
import os
import sys
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL

# In-memory store: collection_name -> {"index": faiss.Index, "documents": [...], "metadatas": [...]}
_collections = {}

_embedding_model = None


def get_embedding_model():
    """Lazy-load the sentence-transformer model — only imported/loaded on first real use."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer  # deferred import
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


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
    """Unique name per topic, same as before — kept for compatibility."""
    safe_hash = hashlib.md5(topic.encode()).hexdigest()[:12]
    return f"topic_{safe_hash}"


def store_research(topic: str, research_result: dict) -> str:
    """
    Chunks and embeds all sources from a research_topic() result into an
    in-memory FAISS index scoped to this topic.

    Returns the collection name so it can be queried later via retrieve_for_angle().
    """
    import faiss  # deferred import
    import numpy as np

    collection_name = _make_collection_name(topic)
    model = get_embedding_model()

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
        _collections[collection_name] = {"index": None, "documents": [], "metadatas": []}
        print(f"Stored 0 chunks in collection '{collection_name}' (no sources)")
        return collection_name

    embeddings = model.encode(documents, convert_to_numpy=True, normalize_embeddings=True)
    embeddings = embeddings.astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product on normalized vectors = cosine similarity
    index.add(embeddings)

    _collections[collection_name] = {
        "index": index,
        "documents": documents,
        "metadatas": metadatas,
    }

    print(f"Stored {len(documents)} chunks across {len(research_result['angles'])} angles "
          f"in collection '{collection_name}'")
    return collection_name


def retrieve_for_angle(collection_name: str, angle: str, query: str, n_results: int = 4) -> list:
    """
    Retrieves the most relevant chunks for a specific angle + query from the collection.
    """
    import numpy as np

    collection = _collections.get(collection_name)
    if not collection or collection["index"] is None:
        return []

    model = get_embedding_model()
    query_embedding = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    query_embedding = query_embedding.astype("float32")

    # Filter to only this angle's chunks first (FAISS itself has no metadata
    # filtering, so we search within the angle-filtered subset directly)
    angle_indices = [i for i, m in enumerate(collection["metadatas"]) if m["angle"] == angle]
    if not angle_indices:
        return []

    angle_embeddings = np.array([collection["index"].reconstruct(i) for i in angle_indices])

    # Brute-force cosine similarity (dot product, since vectors are normalized)
    # against just this angle's subset — small scale, so this is instant.
    scores = angle_embeddings @ query_embedding[0]
    top_k = min(n_results, len(angle_indices))
    top_local_indices = np.argsort(scores)[::-1][:top_k]

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python embed_store.py \"your topic here\"")
    else:
        from agents.researcher import research_topic
        topic = " ".join(sys.argv[1:])
        research_result = research_topic(topic)
        collection_name = store_research(topic, research_result)
        print(f"\nStored under collection: {collection_name}")