import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import call_llm_json
from utils.fetch_article import fetch_article_text
from config import TAVILY_API_KEY, TRUSTED_DOMAINS
from tavily import TavilyClient

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

SUBQUERY_SYSTEM_PROMPT = """You are a research planner for a news explainer app.

Given a news topic, generate 3-4 distinct search queries that would help explain
the FULL context behind this story. Pick whichever angles are most relevant for
THIS specific topic — angles can include (but aren't limited to): history,
economics, geopolitics, technology, business impact, social impact, or impact on India.

Do not force irrelevant angles. Choose only what makes sense for this specific topic.

Respond with ONLY a JSON object in this exact format, nothing else:
{"queries": [{"angle": "short angle name", "query": "specific search query"}, ...]}
"""

def is_likely_article(url: str) -> bool:
    """Filter out video/media pages that won't have useful article text."""
    non_article_patterns = ["/video/", "/videos/", "/watch/", "youtube.com", "/gallery/"]
    return not any(pattern in url.lower() for pattern in non_article_patterns)

def generate_subqueries(topic: str) -> list:
    """
    Given a topic, asks the LLM to break it into 3-4 angle-specific search queries.
    """
    result = call_llm_json(
        prompt=f"News topic: {topic}",
        system=SUBQUERY_SYSTEM_PROMPT,
        fast=False,
        temperature=0.3,
    )
    queries = result.get("queries", [])
    return queries if queries else [{"angle": "general", "query": topic}]



def search_angle(angle_query: dict, topic: str, max_results: int = 4) -> dict:
    """
    Runs a Tavily search, fetches full clean article text, and verifies relevance.
    Drops sources that fail quality checks instead of forcing them in.
    """
    sources = []
    topic_keywords = [w for w in topic.split() if len(w) > 3]  # rough keyword set

    # Allow Wikipedia only for History/background angles — reliable for timelines,
    # but not appropriate for current events, economics, or geopolitics analysis
    angle_lower = angle_query["angle"].lower()
    domains_for_this_angle = TRUSTED_DOMAINS.copy()
    if "history" in angle_lower or "background" in angle_lower:
        domains_for_this_angle += ["en.wikipedia.org", "britannica.com"]

    try:
        response = tavily_client.search(
            query=angle_query["query"],
            search_depth="basic",
            max_results=max_results,
            include_domains=domains_for_this_angle,
        )
        raw_results = response.get("results", [])
    except Exception as e:
        print(f"Whitelisted search failed for '{angle_query['angle']}': {e}")
        raw_results = []

    if not raw_results:
        try:
            response = tavily_client.search(
                query=angle_query["query"], search_depth="basic", max_results=max_results,
                exclude_domains=["facebook.com", "twitter.com", "x.com", "reddit.com",
                                  "instagram.com", "quora.com", "pinterest.com"],
            )
            raw_results = response.get("results", [])
        except Exception as e:
            print(f"Fallback search failed for '{angle_query['angle']}': {e}")

    for r in raw_results:
        if not is_likely_article(r["url"]):
            continue

        fetch_result = fetch_article_text(r["url"], topic_keywords=topic_keywords)

        if fetch_result["success"]:
            sources.append({
                "title": r["title"],
                "url": r["url"],
                "content": fetch_result["text"],
                "source_type": "full_fetch",
            })
        else:
            print(f"    Dropped source (failed quality check): {r['url']} — {fetch_result['error']}")
            # dropped entirely — no weak fallback content forced in

    return {"angle": angle_query["angle"], "query": angle_query["query"], "sources": sources}


def research_topic(topic: str) -> dict:
    subqueries = generate_subqueries(topic)
    print(f"Generated {len(subqueries)} angles: {[q['angle'] for q in subqueries]}")

    results = []
    for sq in subqueries:
        angle_result = search_angle(sq, topic=topic)
        results.append(angle_result)
        print(f"  -> '{angle_result['angle']}': {len(angle_result['sources'])} sources found")

    return {"topic": topic, "angles": results}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python researcher.py \"your topic here\"")
    else:
        topic = " ".join(sys.argv[1:])
        result = research_topic(topic)
        print(json.dumps(result, indent=2)[:3000])