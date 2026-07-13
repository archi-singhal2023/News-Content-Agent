"""
Batch script — runs generate_full_explainer() over the full demo topic list
and saves each result as a JSON file in data/, ready for the frontend to read.

Run this whenever you want to (re)build your demo dataset.
Each topic is tagged with a category so the frontend can filter by
Trending / India / International / Sports / Finance / Tech / Politics etc.
"""
import os
import sys
import json
import re
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pipeline import generate_full_explainer

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Each entry: (topic, category, tags)
# tags let a story appear in more than one row, e.g. India + Politics
DEMO_TOPICS = [
    ("Gujarat High Court upholds death penalty for 38 in 2008 Ahmedabad serial blasts case",
     "politics", ["india", "trending"]),
    ("Centre names 23 Jaish and Lashkar operatives as terrorists citing J-K attack links",
     "politics", ["india"]),
    ("VB-G RAM G scheme replaces MGNREGA with wage changes",
     "politics", ["india"]),
    ("US-Iran tensions over oil and dollar dominance",
     "international", ["international", "trending"]),
    ("China considers restricting foreign access to advanced AI models",
     "tech", ["international", "tech"]),
    ("OpenAI floats 5 percent equity stake to US government",
     "tech", ["international", "tech", "trending"]),
    ("SK Hynix lists on Nasdaq in major foreign listing",
     "finance", ["international", "finance"]),
    ("Tesla Q2 2026 deliveries rise 25 percent amid China and Europe competition",
     "finance", ["international", "finance"]),
    ("Europe venture funding hits 4 year high in Q2 2026",
     "finance", ["international", "finance"]),
    ("Anthropic in talks with Samsung to manufacture custom AI chip",
     "tech", ["tech", "trending"]),
    ("Meta unveils Muse Image and Muse Video AI models",
     "tech", ["tech"]),
    ("JadePuffer first known agentic ransomware system discovered",
     "tech", ["tech", "trending"]),
    ("Hingoli earthquake damages 105 houses in Maharashtra",
     "india", ["india"]),
    ("Air Marshal Ashutosh Dixit assumes charge as Vice Chief of Air Staff",
     "india", ["india"]),
    ("Telstra suffers nationwide outage from software fault",
     "international", ["international"]),
]


def slugify(topic: str) -> str:
    """Convert a topic string into a safe filename."""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug[:60]  # keep filenames reasonable length


def run_batch():
    results_summary = []

    for i, (topic, category, tags) in enumerate(DEMO_TOPICS, start=1):
        print(f"\n{'='*70}")
        print(f"[{i}/{len(DEMO_TOPICS)}] {topic}")
        print(f"{'='*70}")

        try:
            explainer = generate_full_explainer(topic)
        except Exception as e:
            print(f"FAILED: {e}")
            results_summary.append({"topic": topic, "status": "failed", "error": str(e)})
            continue

        # Attach category/tags metadata for the frontend to filter by
        explainer["category"] = category
        explainer["tags"] = tags
        explainer["id"] = slugify(topic)

        filename = os.path.join(DATA_DIR, f"{explainer['id']}.json")
        with open(filename, "w") as f:
            json.dump(explainer, f, indent=2)

        print(f"Saved -> {filename}")
        results_summary.append({
            "topic": topic,
            "status": "success",
            "type": explainer.get("type"),
            "file": filename,
        })

        time.sleep(1)  # small pause between topics, easy on rate limits

    # Save an index file listing all generated explainers, for the frontend to fetch
    index_path = os.path.join(DATA_DIR, "index.json")
    index_data = [
        {
            "id": slugify(t),
            "topic": t,
            "category": c,
            "tags": tags,
        }
        for t, c, tags in DEMO_TOPICS
    ]
    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2)

    print(f"\n\n{'='*70}")
    print("BATCH SUMMARY")
    print(f"{'='*70}")
    for r in results_summary:
        status_icon = "OK" if r["status"] == "success" else "FAILED"
        print(f"[{status_icon}] {r['topic']}")

    success_count = sum(1 for r in results_summary if r["status"] == "success")
    print(f"\n{success_count}/{len(DEMO_TOPICS)} completed successfully.")
    print(f"Index saved -> {index_path}")


if __name__ == "__main__":
    run_batch()