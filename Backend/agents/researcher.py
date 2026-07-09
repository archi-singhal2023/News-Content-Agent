import os
import sys
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import call_llm
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
    raw_response = call_llm(
        prompt=f"News topic: {topic}",
        system=SUBQUERY_SYSTEM_PROMPT,
        fast=False,  # this needs real reasoning, use the smart model
        temperature=0.3,
        json_mode=True,
    )

    try:
        result = json.loads(raw_response)
        return result.get("queries", [])
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0)).get("queries", [])
            except json.JSONDecodeError:
                pass
        # Fallback: just search the raw topic if query generation fails
        return [{"angle": "general", "query": topic}]



def search_angle(angle_query: dict, max_results: int = 4) -> dict:
    """
    Runs a Tavily search for one angle/sub-query, filtered to trusted domains.
    Falls back to an unrestricted search if the whitelist returns nothing,
    so a narrow whitelist never silently kills an entire angle.
    """
    sources = []
    used_fallback = False

    try:
        response = tavily_client.search(
            query=angle_query["query"],
            search_depth="basic",
            max_results=max_results,
            include_domains=TRUSTED_DOMAINS,
        )
        sources = [s for s in sources if is_likely_article(s["url"])]
        
    except Exception as e:
        print(f"Whitelisted search failed for angle '{angle_query['angle']}': {e}")

    # Fallback: no whitelist, if nothing came back
    if not sources:
        used_fallback = True
        try:
            response = tavily_client.search(
                query=angle_query["query"],
                search_depth="basic",
                max_results=max_results,
            )
            sources = [
                {"title": r["title"], "url": r["url"], "content": r["content"]}
                for r in response.get("results", [])
            ]
        except Exception as e:
            print(f"Fallback search also failed for angle '{angle_query['angle']}': {e}")

    return {
        "angle": angle_query["angle"],
        "query": angle_query["query"],
        "sources": sources,
        "used_fallback": used_fallback,
    }


def research_topic(topic: str) -> dict:
    """
    Full research step: generates sub-queries, then searches each one.
    Returns a dict with the topic and a list of angle-tagged source results.
    """
    subqueries = generate_subqueries(topic)
    print(f"Generated {len(subqueries)} angles: {[q['angle'] for q in subqueries]}")

    results = []
    for sq in subqueries:
        angle_result = search_angle(sq)
        results.append(angle_result)
        print(f"  -> '{angle_result['angle']}': {len(angle_result['sources'])} sources found")

    return {
        "topic": topic,
        "angles": results,
    }


if __name__ == "__main__":
    test_result = research_topic("US-Iran tensions over oil and dollar dominance")
    print(json.dumps(test_result, indent=2)[:3000])  # print first part to keep it readable