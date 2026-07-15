/**
 * api.js — thin wrappers around the Flask API.
 * Same-origin, so no base URL needed. When you deploy to Render, this
 * keeps working as-is since templates and API are served from one app.
 */

async function fetchTopics({ tag, category } = {}) {
  const params = new URLSearchParams();
  if (tag) params.set("tag", tag);
  if (category) params.set("category", category);
  const qs = params.toString();
  const res = await fetch(`/api/topics${qs ? "?" + qs : ""}`);
  if (!res.ok) throw new Error("Failed to fetch topics");
  return res.json();
}

async function fetchTopic(id) {
  const res = await fetch(`/api/topics/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error("Failed to fetch topic");
  return res.json();
}

async function postExplain(query) {
  const res = await fetch(`/api/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic: query }),
  });
  if (!res.ok) throw new Error("Failed to explain topic");
  return res.json();
}