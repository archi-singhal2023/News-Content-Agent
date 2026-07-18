"""
Classifier agent — decides which section of the app a story belongs in
(category) and which cross-cutting tags apply (india/international/trending).

This is deliberately separate from triage.py: Triage decides *how much
context* a story needs (deep_dive vs quick_read). This decides *where it's
filed* (category) and *how it surfaces* (tags). Keeping them separate means
either can be swapped or re-prompted independently without touching the other.
"""
import os
import sys
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import call_llm_json

ALLOWED_CATEGORIES = ["Politics", "Tech", "Finance", "Sports", "Science", "Daily Rituals"]
ALLOWED_TAGS = {"india", "international", "trending"}

CLASSIFIER_SYSTEM_PROMPT = f"""You are a news editor sorting a story into the right section of a news app.

Classify the given news topic into exactly ONE of these categories:
{', '.join(ALLOWED_CATEGORIES)}

Also decide which tags apply, choosing zero or more from this exact list: "india", "international", "trending".
- "india": the story is primarily about India or has major India-specific relevance.
- "international": the story is primarily about events outside India, or a global story with no single-country focus.
- "trending": the story is a major, widely-covered story people are likely actively searching for right now.
  Use this sparingly — only for genuinely high-profile stories, not routine news.

A story usually gets "india" OR "international", not both, and sometimes neither
(e.g. a purely scientific or lifestyle story with no clear geographic angle).

Respond with ONLY a JSON object in this exact format, nothing else:
{{"category": "one of the allowed categories exactly as written", "tags": ["list", "of", "applicable", "tags"], "reason": "one short sentence why"}}
"""


def classify_topic(topic: str, summary: str = "") -> dict:
    """
    Classifies a news topic into a category + tags.
    Returns a dict: {"category": "...", "tags": [...], "reason": "..."}
    """
    prompt = f"News topic: {topic}"
    if summary:
        prompt += f"\n\nSummary: {summary}"

    result = call_llm_json(
        prompt=prompt,
        system=CLASSIFIER_SYSTEM_PROMPT,
        fast=True,
        temperature=0.1,
    )
    return _validate(result, str(result))

def _validate(result, raw_response: str) -> dict:
    if result is None:
        return {
            "category": "Tech",
            "tags": [],
            "reason": "Failed to parse, defaulting safe",
            "raw_response": raw_response,
        }

    category = result.get("category", "")
    if category not in ALLOWED_CATEGORIES:
        result["category"] = _closest_category(category)

    tags = result.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    result["tags"] = [t for t in tags if t in ALLOWED_TAGS]

    result.setdefault("reason", "")
    return result


def _closest_category(value: str) -> str:
    """Case-insensitive exact match against the whitelist first; otherwise a
    safe default. Better to land somewhere findable than crash the pipeline
    or silently produce a category the frontend nav doesn't know about."""
    value_lower = (value or "").strip().lower()
    for cat in ALLOWED_CATEGORIES:
        if cat.lower() == value_lower:
            return cat
    return "Tech"


if __name__ == "__main__":
    test_cases = [
        ("US-Iran tensions over oil and dollar dominance", "Tensions escalated after a series of naval incidents in the Gulf."),
        ("Neeru Dhanda wins India's first trap shooting gold", "India's first international trap shooting gold medal was won today."),
        ("ISRO completes Gaganyaan uncrewed test flight", "The uncrewed test flight tested the crew escape system successfully."),
        ("New research links consistent sleep timing to better health", "A large study found irregular sleep timing linked to worse health markers."),
    ]
    for topic, summary in test_cases:
        result = classify_topic(topic, summary)
        print(f"{topic}\n  -> {result}\n")