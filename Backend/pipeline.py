"""
Pipeline orchestrator — the single entry point for generating a news explainer.

generate_full_explainer(topic) is the ONE function the rest of the app calls
(Flask routes, batch scripts, etc). It handles:
1. Triage — classify as deep_dive or quick_read
2. If quick_read -> generate a short standalone summary, skip the heavy pipeline
3. If deep_dive -> run the full Researcher -> RAG -> Analyst -> Editor pipeline
"""
import os
import sys, json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.triage import triage_topic
from agents.researcher import research_topic
from rag.embed_store import store_research
from agents.analyst import generate_current_summary, analyze_angle
from agents.editor import assemble_explainer
from agents.editor import generate_headline
from utils.llm_client import call_llm_json


QUICK_READ_SYSTEM_PROMPT = """You are a news editor writing a short, factual summary
for a simple, self-contained news story (not one that needs deep context).

Write a short summary (3-5 sentences) of what happened, based only on the given
source excerpts. Neutral tone, just the facts.

Respond with ONLY a JSON object in this format:
{"summary": "your summary here"}
"""


def generate_quick_read(topic: str) -> dict:
    """
    For quick_read stories: light research, then a short factual summary with sources.
    """
    research_result = research_topic(topic)

    all_sources = []
    for angle_data in research_result["angles"]:
        all_sources.extend(angle_data["sources"])

    if not all_sources:
        return {
            "topic": topic,
            "type": "quick_read",
            "summary": None,
            "sources": [],
            "note": "No verified sources found for this story.",
        }

    excerpts_text = "\n\n---\n\n".join(
        f"Source: {s['title']}\n{s['content'][:600]}" for s in all_sources[:5]
    )

    result = call_llm_json(
        prompt=f"Topic: {topic}\n\nSource excerpts:\n\n{excerpts_text}",
        system=QUICK_READ_SYSTEM_PROMPT,
        fast=False,
        temperature=0.2,
    )

    summary = result.get("summary", "")

    # Honesty check: if the model itself flagged missing/unclear info, don't
    # publish a shaky summary — surface the gap instead
    uncertainty_flags = ["not specified", "not specify", "sources do not provide",
                          "unfortunately", "do not offer more information", "unclear from"]
    if any(flag in summary.lower() for flag in uncertainty_flags):
        return {
            "topic": topic,
            "type": "quick_read",
            "summary": None,
            "sources": [{"url": s["url"], "title": s["title"]} for s in all_sources[:5]],
            "note": "Could not find verified sources specifically confirming this story's details.",
        }

    unique_sources = list({s["url"]: s["title"] for s in all_sources}.items())
    headline = generate_headline(topic, result.get("summary", "")) if result.get("summary") else topic.upper()
    
    return {
        "topic": topic,
        "type": "quick_read",
        "headline": headline,
        "summary": summary,
        "sources": [{"url": url, "title": title} for url, title in unique_sources[:5]],
        "note": None,
    }


def generate_deep_dive(topic: str) -> dict:
    """
    Full pipeline: Researcher -> RAG storage -> Analyst (summary + all angles) -> Editor.
    """
    research_result = research_topic(topic)
    collection_name = store_research(topic, research_result)

    summary_result = generate_current_summary(collection_name, topic)

    angle_analyses = []
    for angle_data in research_result["angles"]:
        analysis = analyze_angle(collection_name, angle_data["angle"], angle_data["query"])
        angle_analyses.append(analysis)

    final = assemble_explainer(topic, summary_result, angle_analyses)
    final["type"] = "deep_dive"
    return final


def generate_full_explainer(topic: str) -> dict:
    """
    THE single entry point. Classifies the topic, then routes to the
    appropriate pipeline. Always returns a consistent, frontend-ready dict.
    """
    triage_result = triage_topic(topic)
    category = triage_result.get("category", "quick_read")

    print(f"[Triage] '{topic}' -> {category} ({triage_result.get('reason', '')})")

    if category == "deep_dive":
        result = generate_deep_dive(topic)
    else:
        result = generate_quick_read(topic)

    result["triage_reason"] = triage_result.get("reason", "")
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py \"your topic here\"")
    else:
        topic = " ".join(sys.argv[1:])
        result = generate_full_explainer(topic)
        print(json.dumps(result, indent=2)[:2000])