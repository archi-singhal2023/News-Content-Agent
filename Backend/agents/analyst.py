"""
Analyst agent — takes the sources already grouped by angle (from Researcher)
and synthesizes them into a clear, accurate paragraph, with source attribution.

No vector store, no embeddings, no similarity search — the Researcher already
organizes sources per angle (2-4 sources each), so there's nothing to "retrieve"
that isn't already directly available. This keeps the whole pipeline free of
heavy ML dependencies (removed chromadb/FAISS/sentence-transformers/scikit-learn
entirely), which is what was causing repeated OOM crashes in production.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import call_llm_json

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


def analyze_angle(angle_data: dict) -> dict:
    """
    Synthesizes the sources already gathered for this angle into one paragraph.
    angle_data comes directly from research_topic()'s output — {"angle", "query", "sources"}.
    """
    sources = angle_data.get("sources", [])
    angle = angle_data["angle"]

    if not sources:
        return {
            "angle": angle,
            "paragraph": None,
            "sources": [],
            "note": "No verified sources found for this angle — section omitted.",
        }

    excerpts_text = "\n\n---\n\n".join(
        f"Source: {s['title']}\n{s['content'][:800]}" for s in sources
    )

    result = call_llm_json(
        prompt=f"Angle: {angle}\n\nSource excerpts:\n\n{excerpts_text}",
        system=ANALYST_SYSTEM_PROMPT,
        fast=False,
        temperature=0.2,
    )
    paragraph = result.get("paragraph", "")

    unique_sources = list({s["url"]: s["title"] for s in sources}.items())

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


def generate_current_summary(research_result: dict, topic: str) -> dict:
    """
    Generates the short 'what's happening right now' summary, pulling the
    top 1-2 sources from EACH angle (already gathered by the Researcher) to
    get a spread of the most current facts across all angles.
    """
    pooled_sources = []
    for angle_data in research_result["angles"]:
        pooled_sources.extend(angle_data.get("sources", [])[:2])

    if not pooled_sources:
        return {"summary": "", "sources": []}

    excerpts_text = "\n\n---\n\n".join(
        f"Source: {s['title']}\n{s['content'][:600]}" for s in pooled_sources[:6]
    )

    result = call_llm_json(
        prompt=f"Topic: {topic}\n\nSource excerpts:\n\n{excerpts_text}",
        system=SUMMARY_SYSTEM_PROMPT,
        fast=False,
        temperature=0.2,
    )
    summary = result.get("summary", "")

    unique_sources = list({s["url"]: s["title"] for s in pooled_sources}.items())
    return {
        "summary": summary,
        "sources": [{"url": url, "title": title} for url, title in unique_sources],
    }


if __name__ == "__main__":
    print("This module is used via editor.py's pipeline test — run: python editor.py \"topic\"")