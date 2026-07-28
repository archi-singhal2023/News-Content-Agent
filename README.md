# Context — News, Explained

**Live demo:** https://news-content-agent.onrender.com

Most news apps optimize for speed: a headline, a scroll, gone. **Context** does the opposite — it takes a news topic and unpacks it from every angle that actually matters (history, economics, geopolitics, and more), with every claim traced back to a real, verified source.

Built as a multi-agent AI pipeline: no LangChain/LangGraph, no vector database — a hand-rolled orchestration of specialized agents that research, verify, synthesize, and fact-check news topics end to end.

---

## What it does

1. **Discovers** current news topics automatically across categories through agents(Politics, Tech, Finance, Sports, Science).
2. **Triages** each topic: does this story need deep context (a war, a policy change) or is it self-contained (a sports result, a routine announcement)?
3. **Researches** the topic by generating angle-specific search queries (History, Economics, Geopolitics, etc. — chosen dynamically per topic, not fixed), searching trusted news domains, fetching full article text, and filtering out irrelevant or low-quality sources.
4. **Analyzes** each angle, synthesizing multiple sources into a clear paragraph — grounded only in what the sources actually say, never fabricated.
5. **Edits** the pieces together: checks for contradictions between sections, writes a punchy headline, fetches a relevant image, and assembles the final structured explainer.
6. **Classifies** the finished piece into a category and tags (India / International / Trending) based on its actual content.
7. **Serves** it — either from a pre-generated dataset (fast, for the homepage/browse experience) or live, on-demand, when a user searches for something not yet covered.

---

## Architecture

User query > Triage │ deep_dive vs quick_read? > Researcher │────▶│ Tavily search │ (angle-specific queries, trusted-domain whitelist, relevance-verified article fetch) > Analyst │ synthesizes each angle's sources into a paragraph > Editor │ consistency check, headline, image, final assembly > Classifier │ category + tags, based on actual content > Structured JSON → served to frontend

A separate **Discovery** agent runs ahead of all this, scanning Tavily's news search per category to find real, current, dated stories (filtering out hub pages, listicles, and evergreen content) — this is what feeds the pipeline topics to process, rather than a human curating a list.

---

## Tech stack

- **Backend:** Python, Flask, Gunicorn
- **LLM:** Groq (Llama 3.3 70B for synthesis-heavy tasks, Llama 3.1 8B for classification/routing tasks — chosen per-task to balance quality and free-tier rate limits)
- **Search:** Tavily (news-mode search with recency filtering)
- **Images:** Unsplash (keyword-extracted per topic, with category fallbacks)
- **Frontend:** Server-rendered Jinja templates, vanilla JS, no framework
- **Deployment:** Render

Deliberately **no LangChain/LangGraph** — every agent is a plain Python function calling the Groq/Tavily APIs directly, with a shared `call_llm_json()` wrapper handling retries, caching, and JSON-parsing edge cases. This kept every part of the pipeline debuggable and transparent while building it, and avoided an extra abstraction layer's dependency weight on a memory-constrained free-tier deployment.

**No vector database.** The fix: the Researcher agent already organizes sources by angle at search time, so there's no ambiguous retrieval problem left to solve — the Analyst reads each angle's 2-4 sources directly. This is a legitimate architectural simplification once the real bottleneck was identified, not a missing feature.

---

## Key design decisions

- **Triage before research.** Not every story deserves a 4-angle deep-dive — a sports result or celebrity announcement gets a short factual summary instead, decided by an agent.
- **Dynamic angles, not fixed categories.** The Researcher decides which lenses (History, Economics, Technology, etc.) actually make sense for a given story, rather than forcing every topic through the same template.
- **Source verification, not just retrieval.** Every fetched article is checked for topic relevance and content quality before being used; sources that fail (paywalled, bot-blocked, off-topic) are dropped and logged, never silently forced in.
- **Honesty over completeness.** If an angle has no verified sources, it's omitted from the final piece rather than filled in with a vague or fabricated paragraph. If live search can't confirm a claimed story's details, it says so instead of guessing.
- **Consistency checking.** A lightweight fact-check pass flags direct contradictions between sections before publishing — a safety net, not a guarantee.
- **Copyright-conscious.** Card images use licensed stock photos (Unsplash), not scraped article images — real article photos are editorial content the app doesn't have rights to redisplay.

---

## Running locally

```bash
git clone <https://github.com/archi-singhal2023/News-Content-Agent>
cd News-Content-Website
python -m venv .venv
.venv\Scripts\activate        # or source .venv/bin/activate on Mac/Linux
pip install -r requirements.txt
```

## Known limitations

- **Free-tier rate limits.** Groq and Tavily's free tiers cap requests per day/minute; large batch runs are paced with delays to stay within them, and can still occasionally fail mid-run (handled gracefully — partial results are saved, not lost).
- **Live search takes real time.** Deep-dive explainers involve multiple searches and LLM calls; live search on the homepage can take 30-90 seconds for a genuinely new topic, since it's doing real research, not a lookup.
- **Stock imagery, not real article photos.** Card images are topically relevant stock photos, not the actual photos from the source articles (see design decisions above).
- **No persistent long-term archive.** Each batch run replaces the previous dataset rather than accumulating one, so the site reflects "current news" at time of last generation, not a growing historical archive.

## What I'd improve with more time

- Move batch generation to a proper scheduled job (separate from the web process) with persistent storage, so the dataset refreshes automatically without a manual local run
- Add semantic deduplication for near-duplicate discovered topics (currently only exact-slug matching)
- A production-grade retrieval layer, if deployed on infrastructure with more available memory
