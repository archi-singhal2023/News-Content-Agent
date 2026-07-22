"""
Analyst agent — takes retrieved chunks for one angle and synthesizes them
into a clear, accurate paragraph, with source attribution.
Does NOT invent facts not present in the retrieved text.
"""
import os, sys
import json as json_lib
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import call_llm_json
from rag.embed_store import retrieve_across_all
from agents.researcher import research_topic
from rag.embed_store import store_research
from rag.embed_store import retrieve_for_angle

ANALYST_SYSTEM_PROMPT = """You are a careful news analyst. You will be given several
source excerpts about ONE specific angle of a news topic (e.g. History, Economics,
Geopolitics, or Business Impact).

Your job: write a clear, factual paragraph (4-6 sentences) synthesizing what these
sources say about this angle. Rules:
- Only use information present in the given excerpts. Do NOT add outside knowledge
  or invent facts, dates, or figures not stated in the sources.
- If sources disagree or present different emphases, note that briefly rather than
  picking one side silently.
- Write in a neutral, explanatory tone — like a knowledgeable journalist, not an
  opinion columnist.
- Do not repeat "according to the sources" or similar meta-phrases repeatedly —
  write naturally, as an explainer.

Respond with ONLY a JSON object in this format:
{"paragraph": "your synthesized paragraph here"}
"""


def analyze_angle(collection_name: str, angle: str, query: str) -> dict:
    """
    Retrieves relevant chunks for an angle and synthesizes them into one paragraph.
    Returns the paragraph plus the source URLs actually used, for attribution.
    """
    chunks = retrieve_for_angle(collection_name, angle, query, n_results=4)

    if not chunks:
        return {
            "angle": angle,
            "paragraph": None,
            "sources": [],
            "note": "No verified sources found for this angle — section omitted.",
        }

    excerpts_text = "\n\n---\n\n".join(
        f"Source: {c['title']}\n{c['text'][:800]}" for c in chunks
    )

    result = call_llm_json(
        prompt=f"Angle: {angle}\n\nSource excerpts:\n\n{excerpts_text}",
        system=ANALYST_SYSTEM_PROMPT,
        fast=False,
        temperature=0.2,
    )
    paragraph = result.get("paragraph", "")

    # Deduplicate source URLs used for this angle
    unique_sources = list({c["url"]: c["title"] for c in chunks}.items())

    return {
        "angle": angle,
        "paragraph": paragraph,
        "sources": [{"url": url, "title": title} for url, title in unique_sources],
        "note": None,
    }

SUMMARY_SYSTEM_PROMPT = """You are a news editor writing a short, neutral summary of
CURRENT events for a news app. You will be given source excerpts.

Write a 3-4 line summary of what is currently happening — just the facts of the
present situation, no history, no analysis of causes, no economic impact. Purely
"what is happening right now."

Respond with ONLY a JSON object in this format:
{"summary": "your 3-4 line summary here"}
"""


from rag.embed_store import retrieve_across_all

def generate_current_summary(collection_name: str, topic: str) -> dict:
    """
    Generates the short 'what's happening right now' summary, pulling from
    across ALL angles to get the most current facts.
    """
    chunks = retrieve_across_all(collection_name, f"latest news {topic}", n_results=5)

    if not chunks:
        return {"summary": "", "sources": []}

    excerpts_text = "\n\n---\n\n".join(f"Source: {c['title']}\n{c['text'][:600]}" for c in chunks)

    result = call_llm_json(
        prompt=f"Topic: {topic}\n\nSource excerpts:\n\n{excerpts_text}",
        system=SUMMARY_SYSTEM_PROMPT,
        fast=False,
        temperature=0.2,
    )
    summary = result.get("summary", "")

    unique_sources = list({c["url"]: c["title"] for c in chunks}.items())
    return {
        "summary": summary,
        "sources": [{"url": url, "title": title} for url, title in unique_sources],
    }

if __name__ == "__main__":
    print("This module is used via editor.py's pipeline test — run: python editor.py \"topic\"")