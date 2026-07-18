import os
import sys
import json
import re
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
        fast=True,
        temperature=0.1,
        json_mode=True,
    )

    try:
        result = json.loads(raw_response)
        return result
    except json.JSONDecodeError:
        # Model may have added extra text around the JSON — try to extract just the {...} part
        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        # Still failed — return the raw response so we can see what actually came back
        return {
            "category": "quick_read",
            "reason": "Failed to parse, defaulting safe",
            "raw_response": raw_response,
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python triage.py \"your topic here\"")
    else:
        topic = " ".join(sys.argv[1:])
        result = triage_topic(topic)
        print(f"{topic}\n  -> {result}")