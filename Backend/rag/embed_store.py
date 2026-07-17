"""
Handles chunking article text and storing/retrieving it via Chroma
using local, free sentence-transformer embeddings (no API cost).
"""
import os
import sys
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, CHROMA_PERSIST_DIR

import chromadb
from chromadb.utils import embedding_functions

# Local embedding function — runs on CPU, no API calls, no cost
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


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
    """Chroma collection names must be simple strings — hash the topic for a safe unique name."""
    safe_hash = hashlib.md5(topic.encode()).hexdigest()[:12]
    return f"topic_{safe_hash}"


def store_research(topic: str, research_result: dict) -> str:
    """
    Chunks and embeds all sources from a research_topic() result into a
    fresh Chroma collection scoped to this topic.

    Returns the collection name so it can be queried later.
    """
    collection_name = _make_collection_name(topic)

    # Fresh collection each time — delete if it already exists from a prior run
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=collection_name, embedding_function=embedding_fn
    )

    documents, metadatas, ids = [], [], []
    chunk_counter = 0

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
                ids.append(f"chunk_{chunk_counter}")
                chunk_counter += 1

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"Stored {len(documents)} chunks across {len(research_result['angles'])} angles "
          f"in collection '{collection_name}'")
    return collection_name


def retrieve_for_angle(collection_name: str, angle: str, query: str, n_results: int = 4) -> list:
    """
    Retrieves the most relevant chunks for a specific angle + query from the collection.
    """
    collection = chroma_client.get_collection(collection_name, embedding_function=embedding_fn)

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where={"angle": angle},
    )

    retrieved = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        retrieved.append({"text": doc, "url": meta["url"], "title": meta["title"]})

    return retrieved


if __name__ == "__main__":
    import json
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agents.researcher import research_topic

    topic = "US-Iran tensions over oil and dollar dominance"
    research_result = research_topic(topic)

    collection_name = store_research(topic, research_result)

    print("\n--- Test retrieval for 'History' angle ---")
    chunks = retrieve_for_angle(collection_name, "History", "US Iran history timeline")
    for c in chunks:
        print(f"\nFrom: {c['title']} ({c['url']})")
        print(c["text"][:300], "...")