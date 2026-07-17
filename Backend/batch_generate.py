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
from agents.classifier import classify_topic

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Just the raw topic strings now — category and tags are decided by the
# classifier agent at generation time, not hardcoded here.
DEMO_TOPICS = [
    "Gujarat High Court upholds death penalty for 38 in 2008 Ahmedabad serial blasts case",
    "Centre names 23 Jaish and Lashkar operatives as terrorists citing J-K attack links",
    "VB-G RAM G scheme replaces MGNREGA with wage changes",
    "US-Iran tensions over oil and dollar dominance",
    "China considers restricting foreign access to advanced AI models",
    "OpenAI floats 5 percent equity stake to US government",
    "SK Hynix lists on Nasdaq in major foreign listing",
    "Tesla Q2 2026 deliveries rise 25 percent amid China and Europe competition",
    "Europe venture funding hits 4 year high in Q2 2026",
    "Anthropic in talks with Samsung to manufacture custom AI chip",
    "Meta unveils Muse Image and Muse Video AI models",
    "JadePuffer first known agentic ransomware system discovered",
    "Hingoli earthquake damages 105 houses in Maharashtra",
    "Air Marshal Ashutosh Dixit assumes charge as Vice Chief of Air Staff",
    "Telstra suffers nationwide outage from software fault",
]

def slugify(topic: str) -> str:
    """Convert a topic string into a safe filename."""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug[:60]  # keep filenames reasonable length

def load_saved_explainer(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def run_batch():
    results_summary = []

    for i, topic in enumerate(DEMO_TOPICS, start=1):
        print(f"\n{'='*70}")
        print(f"[{i}/{len(DEMO_TOPICS)}] {topic}")
        print(f"{'='*70}")

        try:
            explainer = generate_full_explainer(topic)
        except Exception as e:
            print(f"FAILED: {e}")
            results_summary.append({"topic": topic, "status": "failed", "error": str(e)})
            continue

        # Classifier agent decides category + tags based on the actual content
        classification = classify_topic(topic, explainer.get("summary", ""))
        print(f"[Classifier] -> {classification['category']} | tags: {classification['tags']} "
              f"({classification.get('reason', '')})")

        explainer["category"] = classification["category"]
        explainer["tags"] = classification["tags"]
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
    # Save an index file listing all generated explainers, for the frontend to fetch.
    # Built from the actual saved results (which include classifier-assigned
    # category/tags), not from DEMO_TOPICS, since categories are now dynamic.
    index_path = os.path.join(DATA_DIR, "index.json")
    index_data = []
    for r in results_summary:
        if r["status"] == "success":
            saved = load_saved_explainer(r["file"])
            if saved:
                index_data.append({
                    "id": saved["id"],
                    "topic": saved["topic"],
                    "category": saved["category"],
                    "tags": saved["tags"],
                })
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