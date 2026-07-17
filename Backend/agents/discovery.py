"""
Discovery agent — finds what's actually newsworthy right now, per category,
instead of relying on a hardcoded topic list. This is what makes the app
"real-time": it decides WHAT to cover, not just how to cover it.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import call_llm_json
from config import TAVILY_API_KEY
from tavily import TavilyClient

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# One broad discovery query per category — kept generic so Tavily surfaces
# whatever is actually current, rather than us guessing specific topics.
DISCOVERY_QUERIES = {
    "Politics": "India politics news today",
    "Tech": "technology AI news today",
    "Finance": "business finance markets news today",
    "Sports": "sports news today India",
    "Science": "science space research news today",
}

EXTRACT_HEADLINES_PROMPT = """You are a news editor scanning search results to find
distinct, real news STORIES (not opinion pieces, not "top 10" listicles, not
evergreen explainer articles).

Given a list of search result titles, extract up to 5 genuinely newsworthy,
CURRENT story topics. Rephrase each into a clear, specific topic string
(like a headline), not the raw search result title if it's vague or clickbait.

Skip anything that's not a real dated news event (skip listicles, "how to"
articles, opinion columns, or anything that sounds evergreen rather than current).

Respond with ONLY a JSON object in this format:
{"topics": ["specific topic string 1", "specific topic string 2", ...]}
"""


def discover_topics_for_category(category: str, max_topics: int = 5) -> list:
    """
    Runs a broad search for a category, then asks the LLM to extract
    distinct, current, real news topics from the raw results.
    """
    query = DISCOVERY_QUERIES.get(category)
    if not query:
        return []

    try:
        response = tavily_client.search(query=query, search_depth="basic", max_results=10)
        raw_results = response.get("results", [])
    except Exception as e:
        print(f"Discovery search failed for '{category}': {e}")
        return []

    if not raw_results:
        return []

    titles_text = "\n".join(f"- {r['title']}" for r in raw_results)

    result = call_llm_json(
        prompt=f"Category: {category}\n\nSearch result titles:\n{titles_text}",
        system=EXTRACT_HEADLINES_PROMPT,
        fast=False,
        temperature=0.2,
    )

    topics = result.get("topics", [])
    return topics[:max_topics]


def discover_all_topics(categories: list = None, per_category: int = 3) -> list:
    """
    Runs discovery across all (or specified) categories.
    Returns a flat list of (topic, category) tuples — category comes from
    which discovery query found it, so we don't need a separate classifier
    call just for category (though classify_topic() still adds tags like
    india/international/trending on top of this).
    """
    categories = categories or list(DISCOVERY_QUERIES.keys())
    all_topics = []

    for category in categories:
        print(f"Discovering topics for: {category}")
        topics = discover_topics_for_category(category, max_topics=per_category)
        print(f"  Found {len(topics)}: {topics}")
        for t in topics:
            all_topics.append((t, category))

    return all_topics


if __name__ == "__main__":
    topics = discover_all_topics(per_category=3)
    print("\n" + "=" * 60)
    print(f"TOTAL DISCOVERED: {len(topics)}")
    for t, c in topics:
        print(f"  [{c}] {t}")