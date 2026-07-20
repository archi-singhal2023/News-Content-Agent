"""
Editor agent — the final assembly step. Takes the current-situation summary
and all angle analyses, checks for consistency, drops empty/failed angles
gracefully, and assembles one clean structured explainer object.

This does NOT call the LLM for a full rewrite — the Analyst's paragraphs are
already good. The Editor's job is structural assembly + a final consistency
pass, not re-generating content from scratch.
"""
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.researcher import research_topic
from rag.embed_store import store_research
from agents.analyst import generate_current_summary, analyze_angle
from utils.llm_client import call_llm_json
from utils.fetch_image import fetch_topic_image

CONSISTENCY_CHECK_PROMPT = """You are a fact-checking editor. You will be given a
current-situation summary and several angle analyses (History, Economics, etc.)
about the same news topic.

Check if any of the angle paragraphs directly CONTRADICT each other or the summary
on a factual point (e.g. different dates, different numbers for the same fact,
opposite claims about what happened).

Do NOT flag differences in emphasis or scope — only flag direct factual contradictions.

Respond with ONLY a JSON object in this format:
{"has_contradictions": true or false, "notes": "brief explanation if true, empty string if false"}
"""

HEADLINE_SYSTEM_PROMPT = """You are a headline writer for a news app, in the style
of Inshorts — punchy, attention-grabbing, ALL CAPS, single sentence that tells the
core of the story at a glance. Think tabloid-style impact but factually accurate,
no clickbait exaggeration.

Examples of the style:
"NEERU DHANDA CREATES HISTORY, WINS INDIA'S FIRST-EVER INTERNATIONAL GOLD MEDAL IN WOMEN'S TRAP SHOOTING AT THE ISSF WORLD CUP IN ITALY"
"'INDIA WILL SOON HAVE FLYING BUSES FOR TRANSPORT,' SAYS NITIN GADKARI; FIR FILED ON INFLUENCERS OVER E20"

Given a news summary, write ONE punchy headline in this exact style, 15-25 words.

Respond with ONLY a JSON object in this format:
{"headline": "YOUR HEADLINE IN CAPS HERE"}
"""


def generate_headline(topic: str, summary: str) -> str:
    """
    Generates a punchy, Inshorts-style headline from the summary,
    for use on homepage/category cards.
    """
    result = call_llm_json(
        prompt=f"Topic: {topic}\n\nSummary: {summary}",
        system=HEADLINE_SYSTEM_PROMPT,
        fast=True,  # simple rephrasing task, small model is enough
        temperature=0.4,  # a bit more creative than factual synthesis tasks
    )
    return result.get("headline", topic.upper())  # fallback to topic itself if parsing fails


def check_consistency(summary: str, angle_analyses: list) -> dict:
    """
    Runs a lightweight consistency check across the summary and angle paragraphs.
    This is a safety net, not a guarantee — flags obvious contradictions only.
    """
    sections_text = f"Summary: {summary}\n\n"
    for a in angle_analyses:
        if a["paragraph"]:
            sections_text += f"{a['angle']}: {a['paragraph']}\n\n"

    result = call_llm_json(
        prompt=sections_text,
        system=CONSISTENCY_CHECK_PROMPT,
        fast=True,
        temperature=0.1,
    )
    return {
        "has_contradictions": result.get("has_contradictions", False),
        "notes": result.get("notes", ""),
    }


def assemble_explainer(topic: str, summary_result: dict, angle_analyses: list) -> dict:
    """
    Assembles the final structured explainer object.

    Args:
        topic: the original topic string
        summary_result: output of generate_current_summary() -> {"summary", "sources"}
        angle_analyses: list of outputs from analyze_angle() -> [{"angle", "paragraph", "sources", "note"}, ...]

    Returns:
        A clean, final JSON-serializable dict ready to save/serve to the frontend.
    """
    # Drop angles with no paragraph (no verified sources found) — don't show empty sections
    valid_angles = [a for a in angle_analyses if a["paragraph"]]
    dropped_angles = [a["angle"] for a in angle_analyses if not a["paragraph"]]

    consistency = check_consistency(summary_result["summary"], valid_angles)
    headline = generate_headline(topic, summary_result["summary"])
    image_url = fetch_topic_image(topic)
    
    # Collect every unique source used across the whole explainer, for a top-level "all sources" list
    all_sources = {}
    for s in summary_result["sources"]:
        all_sources[s["url"]] = s["title"]
    for a in valid_angles:
        for s in a["sources"]:
            all_sources[s["url"]] = s["title"]

    final_explainer = {
        "topic": topic,
        "headline": headline,
        "image_url": image_url,
        "summary": summary_result["summary"],
        "summary_sources": summary_result["sources"],
        "sections": [
            {
                "angle": a["angle"],
                "paragraph": a["paragraph"],
                "sources": a["sources"],
            }
            for a in valid_angles
        ],
        "dropped_angles": dropped_angles,  # transparency: which angles had no verified sources
        "consistency_check": consistency,
        "all_sources": [{"url": url, "title": title} for url, title in all_sources.items()],
    }

    return final_explainer


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python editor.py \"your topic here\"")
    else:
        topic = " ".join(sys.argv[1:])
        research_result = research_topic(topic)
        collection_name = store_research(topic, research_result)
        summary_result = generate_current_summary(collection_name, topic)
        angle_analyses = [
            analyze_angle(collection_name, a["angle"], a["query"])
            for a in research_result["angles"]
        ]
        final = assemble_explainer(topic, summary_result, angle_analyses)
        print(json.dumps(final, indent=2))