"""
Fetches the full text of a news article from its URL and cleans it,
stripping navigation, ads, and boilerplate — so what we feed into the
RAG pipeline is the actual story, not page furniture.
"""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

# Tags that are almost never part of the actual article body
TAGS_TO_STRIP = [
    "script", "style", "nav", "header", "footer", "aside",
    "form", "button", "iframe", "noscript", "svg",
]


def fetch_article_text(url: str, topic_keywords: list = None, timeout: int = 10, min_length: int = 300) -> dict:
    """
    Fetches and cleans article text from a URL.
    Optionally checks the text actually relates to the topic via keyword presence.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"url": url, "success": False, "text": "", "error": str(e)}

    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(TAGS_TO_STRIP):
        tag.decompose()

    article_tag = soup.find("article")
    paragraphs = article_tag.find_all("p") if article_tag else soup.find_all("p")

    text = "\n".join(
        p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40
    )

    if len(text) < min_length:
        return {"url": url, "success": False, "text": text,
                "error": f"Extracted text too short ({len(text)} chars)"}

    # Relevance check: does the article actually mention the topic?
    if topic_keywords:
        text_lower = text.lower()
        matches = sum(1 for kw in topic_keywords if kw.lower() in text_lower)
        if matches == 0:
            return {"url": url, "success": False, "text": text,
                    "error": "Article text doesn't mention any topic keywords — likely irrelevant page"}

    return {"url": url, "success": True, "text": text, "error": None}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python fetch_article.py <url>")
    else:
        result = fetch_article_text(sys.argv[1])
        print(f"Success: {result['success']}")
        print(f"Error: {result['error']}")
        print(f"Text length: {len(result['text'])} chars")
        print("---")
        print(result["text"][:1000])