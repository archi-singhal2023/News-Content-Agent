import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import TAVILY_API_KEY, TRUSTED_DOMAINS
from tavily import TavilyClient

client = TavilyClient(api_key=TAVILY_API_KEY)

response = client.search(
    query="US Iran tensions oil dollar dominance",
    search_depth="basic",
    max_results=5,
    include_domains=TRUSTED_DOMAINS,
)

for result in response["results"]:
    print(result["title"])
    print(result["url"])
    print(result["content"][:150], "...")
    print("---")