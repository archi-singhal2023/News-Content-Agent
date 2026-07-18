import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import call_llm_json

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
    result = call_llm_json(
        prompt=f"News topic: {topic}",
        system=TRIAGE_SYSTEM_PROMPT,
        fast=True,
        temperature=0.1,
    )
    if "category" not in result:
        result["category"] = "quick_read"
        result["reason"] = "Failed to parse, defaulting safe"
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python triage.py \"your topic here\"")
    else:
        topic = " ".join(sys.argv[1:])
        result = triage_topic(topic)
        print(f"{topic}\n  -> {result}")