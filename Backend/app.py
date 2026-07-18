"""
Context — Flask app.

Serves the templates/static frontend (built via Lovable) AND the real API
endpoints, backed by actual pre-generated data from batch_generate.py and
the live pipeline for search.
"""
import os, sys, json
import threading
from flask import Flask, render_template, jsonify, request

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pipeline import generate_full_explainer
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def topic_summary(t):
    """Shape used for list views (carousels) — smaller than the full explainer."""
    return {
        "id": t["id"],
        "topic": t["topic"],
        "category": t["category"],
        "tags": t.get("tags", []),
        "headline": t.get("headline", t["topic"].upper()),
        "image_url": t.get("image_url"),
    }


# ---------------------------------------------------------------------------
# Page routes (render templates)
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/category/<name>")
def category_page(name):
    category = name.replace("-", " ").title()
    return render_template("category.html", category=category)


@app.route("/topic/<topic_id>")
def detail_page(topic_id):
    return render_template("detail.html", topic_id=topic_id)


# ---------------------------------------------------------------------------
# API routes — backed by real pre-generated data + live pipeline
# ---------------------------------------------------------------------------
@app.route("/api/topics")
def api_topics():
    tag = request.args.get("tag")
    category = request.args.get("category")

    index_data = load_json("index.json")
    if index_data is None:
        return jsonify([])

    items = index_data
    if tag:
        items = [t for t in items if tag in t.get("tags", [])]
    if category:
        items = [t for t in items if t.get("category", "").lower() == category.lower()]

    # index.json already has id/topic/category/tags — just need headline too,
    # so pull that from each topic's full JSON file
    results = []
    for t in items:
        full = load_json(f"{t['id']}.json")
        if full:
            results.append(topic_summary(full))
    return jsonify(results)


@app.route("/api/topics/<topic_id>")
def api_topic(topic_id):
    explainer = load_json(f"{topic_id}.json")
    if explainer is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(explainer)


@app.route("/api/explain", methods=["POST"])
def api_explain():
    data = request.get_json(force=True, silent=True) or {}
    query = data.get("topic", "").strip()
    if not query:
        return jsonify({"error": "topic is required"}), 400

    try:
        result = generate_full_explainer(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to generate explainer: {str(e)}"}), 500


@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok"})

def refresh_news_data():
    print("[Scheduler] Refreshing news data...")
    try:
        from batch_generate import run_batch
        run_batch(per_category=3)
        print("[Scheduler] Refresh complete.")
    except Exception as e:
        print(f"[Scheduler] Refresh failed: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_news_data, "interval", hours=6)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    return scheduler


def run_initial_generation_in_background():
    """Runs the first-ever generation in a separate thread so Flask can
    start serving requests immediately, instead of blocking startup."""
    thread = threading.Thread(target=refresh_news_data, daemon=True)
    thread.start()


if not os.path.exists(os.path.join(DATA_DIR, "index.json")):
    print("No existing data found — starting initial generation in background...")
    run_initial_generation_in_background()

start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)