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


def fetch_article_text(url: str, timeout: int = 10, min_length: int = 200) -> dict:
    """
    Fetches and cleans article text from a URL.

    Returns:
        {"url": url, "success": bool, "text": str, "error": str or None}
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"url": url, "success": False, "text": "", "error": str(e)}

    soup = BeautifulSoup(response.content, "html.parser")

    # Strip non-content tags before extracting text
    for tag in soup(TAGS_TO_STRIP):
        tag.decompose()

    # Prefer <article> tag if present — most news sites use semantic HTML for the story body
    article_tag = soup.find("article")
    if article_tag:
        paragraphs = article_tag.find_all("p")
    else:
        # Fallback: grab all <p> tags on the page
        paragraphs = soup.find_all("p")

    text = "\n".join(
        p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40
    )
    # ^ filter out tiny <p> tags — usually captions, nav labels, or junk, not real sentences

    if len(text) < min_length:
        return {
            "url": url,
            "success": False,
            "text": text,
            "error": f"Extracted text too short ({len(text)} chars), likely not a real article page",
        }

    return {"url": url, "success": True, "text": text, "error": None}


if __name__ == "__main__":
    test_url = "https://www.reuters.com/world/americas/brics-alternatives-dollar-no-longer-fantasy-economist-oneill-says-2026-07-06"
    result = fetch_article_text(test_url)
    print(f"Success: {result['success']}")
    print(f"Error: {result['error']}")
    print(f"Text length: {len(result['text'])} chars")
    print("---")
    print(result["text"][:1000])