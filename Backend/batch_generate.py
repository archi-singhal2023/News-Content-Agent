"""
Batch script — discovers current news topics automatically, runs
generate_full_explainer() over each, and saves each result as a JSON file
in data/, ready for the frontend to read.

Run this on a schedule (daily, or manually) to refresh the site with
real, current news — no hardcoded topic list.
"""
import os
import sys
import json
import re
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pipeline import generate_full_explainer
from agents.classifier import classify_topic
from agents.discovery import discover_all_topics

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def clear_old_data():
    """Remove all existing topic JSON files before a fresh batch run,
    so the site only ever shows the current run's discovered news,
    not an ever-accumulating pile of old stories."""
    removed = 0
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".json"):
            os.remove(os.path.join(DATA_DIR, fname))
            removed += 1
    print(f"Cleared {removed} old data files before fresh run.")

def slugify(topic: str) -> str:
    """Convert a topic string into a safe filename."""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug[:60]


def load_saved_explainer(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


def run_batch(per_category: int = 3):
    clear_old_data()
    print("Discovering current topics...\n")
    discovered = discover_all_topics(per_category=per_category)

    if not discovered:
        print("No topics discovered — aborting batch.")
        return

    print(f"\nProceeding to generate explainers for {len(discovered)} discovered topics.\n")

    results_summary = []
    seen_ids = set()  # avoid saving duplicate topics if discovery overlaps

    for i, (topic, discovery_category) in enumerate(discovered, start=1):
        print(f"\n{'='*70}")
        print(f"[{i}/{len(discovered)}] {topic}")
        print(f"{'='*70}")

        topic_id = slugify(topic)
        if topic_id in seen_ids:
            print("Skipped (duplicate of an already-processed topic this run).")
            continue
        seen_ids.add(topic_id)

        try:
            explainer = generate_full_explainer(topic)
        except Exception as e:
            print(f"FAILED: {e}")
            results_summary.append({"topic": topic, "status": "failed", "error": str(e)})
            continue

        # Classifier agent decides final category + tags based on the actual
        # generated content (more reliable than the discovery-query category alone)
        classification = classify_topic(topic, explainer.get("summary", ""))
        print(f"[Classifier] -> {classification['category']} | tags: {classification['tags']} "
              f"({classification.get('reason', '')})")

        explainer["category"] = classification["category"]
        explainer["tags"] = classification["tags"]
        explainer["id"] = topic_id

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

        time.sleep(5)  # easy on rate limits

    # Rebuild index.json from whatever's actually on disk right now, so stale
    # entries from previous runs get cleaned out too, not just appended to.
    index_data = []
    for fname in os.listdir(DATA_DIR):
        if fname == "index.json" or not fname.endswith(".json"):
            continue
        full = load_saved_explainer(os.path.join(DATA_DIR, fname))
        if not full:
            continue
        # Skip malformed/incomplete files instead of crashing the whole index rebuild
        required_keys = ("id", "topic", "category", "tags")
        if not all(k in full for k in required_keys):
            print(f"Skipping malformed data file (missing keys): {fname}")
            continue
        index_data.append({
            "id": full["id"],
            "topic": full["topic"],
            "category": full["category"],
            "tags": full["tags"],
        })

    index_path = os.path.join(DATA_DIR, "index.json")
    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2)

    print(f"\n\n{'='*70}")
    print("BATCH SUMMARY")
    print(f"{'='*70}")
    for r in results_summary:
        status_icon = "OK" if r["status"] == "success" else "FAILED"
        print(f"[{status_icon}] {r['topic']}")

    success_count = sum(1 for r in results_summary if r["status"] == "success")
    print(f"\n{success_count}/{len(discovered)} completed successfully.")
    print(f"Index rebuilt from {len(index_data)} total files -> {index_path}")


if __name__ == "__main__":
    run_batch(per_category=3)