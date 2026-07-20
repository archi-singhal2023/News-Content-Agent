"""
Context — Flask app.
Serves the templates/static frontend AND the real API endpoints, backed by
pre-generated data from local batch_generate.py runs, plus live search via
the real pipeline (user-triggered only — no autonomous background discovery
in production, to avoid burning shared Tavily/Groq quota).
"""
import os, sys, json
from flask import Flask, render_template, jsonify, request

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Backend"))
from pipeline import generate_full_explainer

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Backend", "data")


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def topic_summary(t):
    return {
        "id": t["id"],
        "topic": t["topic"],
        "category": t["category"],
        "tags": t.get("tags", []),
        "headline": t.get("headline", t["topic"].upper()),
        "image_url": t.get("image_url"),
    }


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

        import re
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:60]
        result["id"] = slug

        filepath = os.path.join(DATA_DIR, f"{slug}.json")
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to generate explainer: {str(e)}"}), 500


@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)