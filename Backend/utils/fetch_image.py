"""
Fetches a relevant stock photo URL for a topic using Unsplash's free API.
Falls back to a category-based placeholder if no good match is found.
"""
import requests, os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import UNSPLASH_ACCESS_KEY

UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"

# Fallback placeholder images per category, used if Unsplash search fails
# or returns nothing — solid, thematically relevant, never breaks the UI.
CATEGORY_FALLBACKS = {
    "Politics": "https://images.unsplash.com/photo-1541872703-74c5e44368f9",
    "Tech": "https://images.unsplash.com/photo-1518770660439-4636190af475",
    "Finance": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3",
    "Sports": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211",
    "Science": "https://images.unsplash.com/photo-1451187580459-43490279c0fa",
    "Daily Rituals": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085",
}


from utils.llm_client import call_llm_json

IMAGE_QUERY_SYSTEM_PROMPT = """Given a news topic, output 2-3 simple, concrete,
visual search keywords suitable for a stock photo search (like Unsplash).

Think about what a generic, relevant PHOTO would show — not the specific news
event (stock photos won't have specific people/events), but the general visual
theme. E.g. "RBI cuts repo rate" -> "bank, finance, money". "SpaceX launches
satellite" -> "rocket launch, space, night sky".

Respond with ONLY a JSON object: {"keywords": "2-3 words, comma separated"}
"""


def get_image_search_keywords(topic: str) -> str:
    result = call_llm_json(
        prompt=f"Topic: {topic}",
        system=IMAGE_QUERY_SYSTEM_PROMPT,
        fast=True,
        temperature=0.3,
    )
    return result.get("keywords", topic)


def fetch_topic_image(query: str, category: str = "Tech") -> str:
    if not UNSPLASH_ACCESS_KEY:
        return CATEGORY_FALLBACKS.get(category, CATEGORY_FALLBACKS["Tech"])

    search_terms = get_image_search_keywords(query)

    try:
        response = requests.get(
            UNSPLASH_SEARCH_URL,
            params={"query": search_terms, "per_page": 1, "orientation": "portrait"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=8,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            return results[0]["urls"]["regular"]
    except Exception as e:
        print(f"Image search failed for '{search_terms}': {e}")

    return CATEGORY_FALLBACKS.get(category, CATEGORY_FALLBACKS["Tech"])

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "artificial intelligence"
    url = fetch_topic_image(query)
    print(f"Query: {query}\nImage URL: {url}")