import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import call_llm

TRIAGE_SYSTEM_PROMPT = """You are a news editor deciding how much context a story needs.

Classify the given news topic into exactly one of two categories:

- "deep_dive": stories with meaningful underlying causes, history, economics,
  geopolitics, or broader impact worth explaining (wars, policy changes,
  economic shifts, major tech/business events, elections, etc.)

- "quick_read": self-contained factual events with no meaningful "why" to explain
  (robberies, viral/human-interest stories, sports results, celebrity news,
  weather events, etc.)

Respond with ONLY a JSON object in this exact format, nothing else:
{"category": "deep_dive" or "quick_read", "reason": "one short sentence why"}
"""


def triage_topic(topic: str) -> dict:
    """
    Classifies a news topic as deep_dive or quick_read.
    Returns a dict: {"category": "...", "reason": "..."}
    """
    raw_response = call_llm(
        prompt=f"News topic: {topic}",
        system=TRIAGE_SYSTEM_PROMPT,
        fast=True,          # small model is enough for classification
        temperature=0.1,    # low temperature = consistent, predictable output
    )

    import json
    try:
        result = json.loads(raw_response)
        return result
    except json.JSONDecodeError:
        # Fallback if the model adds extra text despite instructions
        return {"category": "quick_read", "reason": "Failed to parse, defaulting safe"}


if __name__ == "__main__":
    test_topics = [
        "US-Iran tensions over oil and dollar dominance",
        "Fan cycles 12 days to meet favorite cricketer",
        "RBI cuts repo rate by 25 basis points",
        "Local robbery reported in Mumbai suburb",
    ]

    for topic in test_topics:
        result = triage_topic(topic)
        print(f"{topic}\n  -> {result}\n")