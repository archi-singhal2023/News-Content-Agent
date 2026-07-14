"""
Flask backend — serves the pre-generated explainer dataset to the frontend,
and exposes a live-generation endpoint for user-typed search queries.
"""
import os
import sys
import json

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pipeline import generate_full_explainer

app = Flask(__name__)
CORS(app)  # allows the frontend (different origin) to call this API

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


@app.route("/api/topics", methods=["GET"])
def get_topics():
    """
    Returns the index of all pre-generated topics, with optional filtering
    by category or tag via query params, e.g. /api/topics?tag=india
    """
    index_data = load_json("index.json")
    if index_data is None:
        return jsonify({"error": "No data found. Run batch_generate.py first."}), 404

    tag_filter = request.args.get("tag")
    category_filter = request.args.get("category")

    if tag_filter:
        index_data = [t for t in index_data if tag_filter in t.get("tags", [])]
    if category_filter:
        index_data = [t for t in index_data if t.get("category") == category_filter]

    return jsonify(index_data)


@app.route("/api/topics/<topic_id>", methods=["GET"])
def get_topic_detail(topic_id):
    """
    Returns the full explainer for one topic (used by the detail page).
    """
    explainer = load_json(f"{topic_id}.json")
    if explainer is None:
        return jsonify({"error": "Topic not found"}), 404
    return jsonify(explainer)


@app.route("/api/explain", methods=["POST"])
def explain_live():
    """
    Live generation endpoint — for the search bar. Takes a user-typed topic
    and runs the full pipeline in real time. Slower than pre-generated data,
    since it hits Groq + Tavily live, but works for anything not in the demo set.
    """
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "").strip()

    if not topic:
        return jsonify({"error": "Missing 'topic' in request body"}), 400

    try:
        result = generate_full_explainer(topic)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to generate explainer: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Simple endpoint to confirm the server is up — useful for Render's health checks."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)