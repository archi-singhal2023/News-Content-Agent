"""
Context — Flask app.

Serves the templates/static frontend AND the API endpoints your spec calls for:
  GET  /api/topics            -> list of topic summaries, filterable by ?tag= / ?category=
  GET  /api/topics/<id>       -> full explainer object
  POST /api/explain           -> live search, same shape

Right now TOPICS is an in-memory mock dict so you can see the whole app working
end to end. Swap the bodies of api_topics / api_topic / api_explain for calls
into your real Triage/Researcher agents + Chroma store — the routes, response
shapes, and templates don't need to change at all.
"""

import re
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Mock data — same shape your real backend already returns.
# ---------------------------------------------------------------------------
TOPICS = {
    "rbi-repo-cut": {
        "id": "rbi-repo-cut",
        "topic": "RBI cuts repo rate to 5.5%",
        "category": "Finance",
        "tags": ["trending", "india", "finance"],
        "type": "deep_dive",
        "headline": "RBI SURPRISES MARKETS WITH THIRD STRAIGHT RATE CUT AS INFLATION COOLS TO AN EIGHT-YEAR LOW",
        "summary": "The Reserve Bank of India cut its repo rate by 25 basis points to 5.5%, the third consecutive cut this cycle. The move follows retail inflation falling below the RBI's target band for four straight months. Home loan EMIs are expected to ease, and the central bank signalled room for one more cut if growth stays soft.",
        "summary_sources": [
            {"title": "RBI Monetary Policy Statement", "url": "https://rbi.org.in"},
            {"title": "Reuters", "url": "https://reuters.com"},
        ],
        "sections": [
            {"angle": "History", "paragraph": "India's repo rate has swung from a pandemic-era low of 4% to a peak of 6.5% during the 2022-23 inflation spike. Past easing cycles show rate cuts alone rarely revive demand without matching credit growth from banks.", "sources": [{"title": "RBI historical rate archive", "url": "https://rbi.org.in"}]},
            {"angle": "Economics", "paragraph": "Lower rates reduce borrowing costs for home and auto loans and typically boost consumption within two to three quarters. Banks have been slow to pass on earlier cuts fully, so the real-economy effect may lag.", "sources": [{"title": "Livemint economics desk", "url": "https://livemint.com"}]},
            {"angle": "Geopolitics", "paragraph": "The cut widens the interest rate gap with the US Federal Reserve, putting mild pressure on the rupee. A weaker rupee helps exporters but raises import costs for oil and electronics.", "sources": [{"title": "Bloomberg markets", "url": "https://bloomberg.com"}]},
            {"angle": "India Impact", "paragraph": "For salaried households, this likely means marginally cheaper EMIs on floating-rate home loans over the next few months. Banks typically take four to eight weeks to reprice existing loans.", "sources": [{"title": "Economic Times", "url": "https://economictimes.com"}]},
        ],
        "dropped_angles": [],
    },
    "budget-tax-slabs": {
        "id": "budget-tax-slabs",
        "topic": "Union Budget 2026 income tax slabs",
        "category": "Finance",
        "tags": ["india", "finance"],
        "type": "deep_dive",
        "headline": "NEW TAX SLABS LEAVE MOST SALARIED INDIANS WITH MORE TAKE-HOME PAY, BUT FINE PRINT MATTERS",
        "summary": "The Union Budget revised income tax slabs under the new regime, raising the no-tax threshold and widening middle slabs. Most salaried taxpayers earning under ₹15 lakh will see some relief, though the old regime remains optional for those with large deductions.",
        "summary_sources": [{"title": "Ministry of Finance Budget Documents", "url": "https://finmin.nic.in"}],
        "sections": [
            {"angle": "History", "paragraph": "India has restructured its tax slabs five times in the past decade, moving gradually toward a simplified regime with fewer exemptions.", "sources": [{"title": "PRS Legislative Research", "url": "https://prsindia.org"}]},
            {"angle": "Economics", "paragraph": "More disposable income for the middle class is intended to support consumption, though economists are split on whether the relief is large enough to meaningfully move spending.", "sources": [{"title": "Mint Budget Analysis", "url": "https://livemint.com"}]},
            {"angle": "India Impact", "paragraph": "Salaried employees should recompute which regime suits them this year, since the new slabs changed the break-even point for common deductions like HRA and 80C.", "sources": [{"title": "Economic Times Wealth", "url": "https://economictimes.com"}]},
        ],
        "dropped_angles": ["Geopolitics"],
    },
    "eu-trade-talks": {
        "id": "eu-trade-talks",
        "topic": "India-EU free trade agreement talks",
        "category": "Politics",
        "tags": ["trending", "international", "politics"],
        "type": "deep_dive",
        "headline": "INDIA AND THE EU EDGE CLOSER TO A TRADE DEAL AFTER YEARS OF STALLED TALKS ON TARIFFS AND CARBON RULES",
        "summary": "India and the EU aim to conclude free trade agreement talks by year end, after more than a decade of on-and-off negotiations. Sticking points include EU carbon border taxes on Indian steel and India's demand for easier movement of skilled workers.",
        "summary_sources": [{"title": "European Commission Trade Statement", "url": "https://ec.europa.eu"}],
        "sections": [
            {"angle": "History", "paragraph": "Talks first began in 2007 and collapsed in 2013 over auto tariffs and data protection standards, restarting in 2022 under pressure to diversify trade away from China.", "sources": [{"title": "European Council archive", "url": "https://consilium.europa.eu"}]},
            {"angle": "Economics", "paragraph": "A deal would cut tariffs on Indian textiles, pharma, and IT services entering Europe, while Indian steel and aluminium exporters worry about the EU's carbon border adjustment mechanism.", "sources": [{"title": "Financial Times", "url": "https://ft.com"}]},
            {"angle": "Geopolitics", "paragraph": "The deal fits a broader European push to reduce reliance on Chinese supply chains, and an Indian push to diversify export markets beyond the US.", "sources": [{"title": "Reuters", "url": "https://reuters.com"}]},
            {"angle": "India Impact", "paragraph": "Indian IT and pharma exporters would likely benefit first. Domestic dairy and auto-parts industries have lobbied hard against opening up too quickly.", "sources": [{"title": "Business Standard", "url": "https://business-standard.com"}]},
        ],
        "dropped_angles": [],
    },
    "ai-safety-summit": {
        "id": "ai-safety-summit",
        "topic": "Global AI Safety Summit outcomes",
        "category": "Tech",
        "tags": ["trending", "international", "tech"],
        "type": "deep_dive",
        "headline": "WORLD LEADERS AGREE ON VOLUNTARY AI SAFETY TESTING BUT STOP SHORT OF BINDING RULES",
        "summary": "Representatives from over 30 countries signed a non-binding declaration on AI safety testing for frontier models, asking labs to share safety evaluations before release but with no enforcement mechanism.",
        "summary_sources": [{"title": "Summit Joint Declaration", "url": "https://gov.uk"}],
        "sections": [
            {"angle": "History", "paragraph": "This is the third such summit since 2023, following earlier meetings that produced similarly voluntary commitments.", "sources": [{"title": "Council on Foreign Relations", "url": "https://cfr.org"}]},
            {"angle": "Economics", "paragraph": "Voluntary rules are cheaper for labs to comply with than binding regulation, which helps explain industry support for the lighter approach.", "sources": [{"title": "MIT Technology Review", "url": "https://technologyreview.com"}]},
            {"angle": "Geopolitics", "paragraph": "The US and UK pushed for a lighter framework, while the EU pointed to its own binding AI Act as the stronger model.", "sources": [{"title": "Politico", "url": "https://politico.com"}]},
            {"angle": "India Impact", "paragraph": "India signed the declaration and says it will draft its own domestic AI governance framework next year.", "sources": [{"title": "MeitY press release", "url": "https://meity.gov.in"}]},
        ],
        "dropped_angles": [],
    },
    "upi-outage": {
        "id": "upi-outage",
        "topic": "UPI faces third outage this month",
        "category": "Tech",
        "tags": ["india", "tech"],
        "type": "quick_read",
        "headline": "UPI GOES DOWN FOR TWO HOURS NATIONWIDE IN THIRD OUTAGE THIS MONTH, NPCI BLAMES BANK-SIDE GLITCH",
        "summary": "UPI transactions failed for nearly two hours nationwide, the third such outage this month. NPCI blamed a technical glitch at a partner bank and said services were restored without data loss.",
        "summary_sources": [{"title": "NPCI Statement", "url": "https://npci.org.in"}],
        "sections": [],
        "dropped_angles": [],
    },
    "gig-worker-code": {
        "id": "gig-worker-code",
        "topic": "Social Security Code for gig workers",
        "category": "Politics",
        "tags": ["india", "politics"],
        "type": "deep_dive",
        "headline": "GIG WORKERS TO GET FORMAL SOCIAL SECURITY COVER AS NEW LABOUR CODE ROLLS OUT NATIONWIDE",
        "summary": "The government has begun rolling out Social Security Code provisions covering gig and platform workers, requiring aggregators to contribute to a welfare fund. Enforcement details remain unclear.",
        "summary_sources": [{"title": "Ministry of Labour notification", "url": "https://labour.gov.in"}],
        "sections": [
            {"angle": "History", "paragraph": "The Code on Social Security was passed in 2020 but implementation was delayed for years, and gig workers were formally recognised for the first time under it.", "sources": [{"title": "PRS Legislative Research", "url": "https://prsindia.org"}]},
            {"angle": "Economics", "paragraph": "Aggregators will contribute 1-2% of revenue per transaction to a welfare fund, a cost companies say will likely be partly passed on through fees or reduced incentives.", "sources": [{"title": "Mint", "url": "https://livemint.com"}]},
            {"angle": "India Impact", "paragraph": "Delivery and ride-hailing workers should see baseline accident and health cover for the first time, though claim mechanisms are still being finalised state by state.", "sources": [{"title": "The Hindu", "url": "https://thehindu.com"}]},
        ],
        "dropped_angles": ["Geopolitics"],
    },
    "semiconductor-fab": {
        "id": "semiconductor-fab",
        "topic": "India's first commercial chip fab breaks ground",
        "category": "Tech",
        "tags": ["trending", "india", "tech"],
        "type": "deep_dive",
        "headline": "INDIA BREAKS GROUND ON ITS FIRST COMMERCIAL SEMICONDUCTOR FAB, A DECADE-LONG BET FINALLY UNDERWAY",
        "summary": "Construction has begun on India's first commercial semiconductor fab, backed by billions in incentives. The plant will initially produce older-generation chips for autos and appliances.",
        "summary_sources": [{"title": "MeitY press briefing", "url": "https://meity.gov.in"}],
        "sections": [
            {"angle": "History", "paragraph": "India has attempted domestic chip manufacturing since the 1980s, with earlier efforts stalling over funding and technology-transfer hurdles.", "sources": [{"title": "Indian Express", "url": "https://indianexpress.com"}]},
            {"angle": "Economics", "paragraph": "The fab is expected to create thousands of jobs and reduce import dependence for chips used in autos and industrial equipment.", "sources": [{"title": "Economic Times", "url": "https://economictimes.com"}]},
            {"angle": "Geopolitics", "paragraph": "The project fits a global trend of reducing reliance on Taiwan for chip supply, aligning with allied efforts to build capacity outside China and Taiwan.", "sources": [{"title": "Nikkei Asia", "url": "https://asia.nikkei.com"}]},
            {"angle": "India Impact", "paragraph": "Auto and electronics manufacturers may eventually source chips domestically, shortening supply chains hit by shortages in 2021-22.", "sources": [{"title": "Business Standard", "url": "https://business-standard.com"}]},
        ],
        "dropped_angles": [],
    },
    "opposition-alliance": {
        "id": "opposition-alliance",
        "topic": "Opposition parties regroup ahead of state polls",
        "category": "Politics",
        "tags": ["india", "politics"],
        "type": "quick_read",
        "headline": "OPPOSITION PARTIES ANNOUNCE SEAT-SHARING DEAL AHEAD OF STATE POLLS TO AVOID VOTE-SPLITTING LOSSES",
        "summary": "Several opposition parties announced a renewed seat-sharing arrangement ahead of state elections, aiming to avoid the vote-splitting that hurt them last cycle. The alliance covers only a handful of states.",
        "summary_sources": [{"title": "The Hindu", "url": "https://thehindu.com"}],
        "sections": [],
        "dropped_angles": [],
    },
    "red-sea-shipping": {
        "id": "red-sea-shipping",
        "topic": "Red Sea shipping disruptions ease",
        "category": "Politics",
        "tags": ["international", "politics"],
        "type": "quick_read",
        "headline": "RED SEA SHIPPING PREMIUMS EASE AS ATTACKS SLOW, BUT MAJOR CARRIERS STAY CAUTIOUS ON ROUTE",
        "summary": "Shipping insurers report a modest drop in premiums for Red Sea routes as attacks on vessels have slowed. Major carriers remain cautious about fully returning, with some still rerouting via the Cape of Good Hope.",
        "summary_sources": [{"title": "Lloyd's List", "url": "https://lloydslist.com"}],
        "sections": [],
        "dropped_angles": [],
    },
    "monsoon-forecast": {
        "id": "monsoon-forecast",
        "topic": "IMD revises monsoon forecast upward",
        "category": "Finance",
        "tags": ["india", "finance"],
        "type": "quick_read",
        "headline": "IMD REVISES MONSOON FORECAST UPWARD, A GOOD SIGN FOR CROP SOWING AND RURAL INCOMES",
        "summary": "The India Meteorological Department raised its monsoon forecast to above-normal rainfall, a positive signal for kharif crop sowing that could support rural incomes and ease food inflation later in the year.",
        "summary_sources": [{"title": "IMD Bulletin", "url": "https://mausam.imd.gov.in"}],
        "sections": [],
        "dropped_angles": [],
    },
    "fed-rate-hold": {
        "id": "fed-rate-hold",
        "topic": "US Federal Reserve holds rates steady",
        "category": "Finance",
        "tags": ["international", "finance"],
        "type": "quick_read",
        "headline": "FED HOLDS RATES STEADY FOR FOURTH STRAIGHT MEETING, SAYS FUTURE MOVES DEPEND ON DATA",
        "summary": "The US Federal Reserve held its benchmark rate steady for a fourth straight meeting, citing mixed signals on inflation and employment, and said future moves depend on incoming data rather than a preset path.",
        "summary_sources": [{"title": "Federal Reserve Statement", "url": "https://federalreserve.gov"}],
        "sections": [],
        "dropped_angles": [],
    },
    "data-protection-rules": {
        "id": "data-protection-rules",
        "topic": "Digital Personal Data Protection rules notified",
        "category": "Tech",
        "tags": ["india", "tech"],
        "type": "deep_dive",
        "headline": "INDIA NOTIFIES LONG-AWAITED DATA PROTECTION RULES, GIVING COMPANIES A YEAR TO COMPLY",
        "summary": "The government notified detailed rules under the Digital Personal Data Protection Act, two years after the law was passed, giving companies a year-long transition period to comply.",
        "summary_sources": [{"title": "MeitY notification", "url": "https://meity.gov.in"}],
        "sections": [
            {"angle": "History", "paragraph": "India's data protection law took over five years and multiple draft versions to pass, following the Supreme Court's 2017 ruling that privacy is a fundamental right.", "sources": [{"title": "PRS Legislative Research", "url": "https://prsindia.org"}]},
            {"angle": "Economics", "paragraph": "Compliance will require most companies handling user data to invest in consent-management systems, a cost likely to weigh more heavily on smaller startups.", "sources": [{"title": "Economic Times", "url": "https://economictimes.com"}]},
            {"angle": "India Impact", "paragraph": "Users should eventually see clearer consent prompts and the right to request data deletion, though the one-year window means changes will roll out gradually.", "sources": [{"title": "MediaNama", "url": "https://medianama.com"}]},
        ],
        "dropped_angles": ["Geopolitics"],
    },
    "issf-trap-gold": {
        "id": "issf-trap-gold",
        "topic": "Neeru Dhanda wins India's first trap shooting gold",
        "category": "Sports",
        "tags": ["trending", "india", "sports"],
        "type": "deep_dive",
        "headline": "NEERU DHANDA CREATES HISTORY, WINS INDIA'S FIRST-EVER INTERNATIONAL GOLD IN WOMEN'S TRAP SHOOTING AT THE ISSF WORLD CUP",
        "summary": "Neeru Dhanda became the first Indian woman to win an international trap shooting gold medal, topping the podium at the ISSF World Cup in Italy. The win is being seen as a breakthrough for a discipline India has historically struggled in compared to rifle and pistol events.",
        "summary_sources": [{"title": "ISSF Results", "url": "https://issf-sports.org"}],
        "sections": [
            {"angle": "History", "paragraph": "India has won Olympic and World Cup medals in rifle and pistol shooting for decades, but trap and skeet events lagged behind due to costlier equipment and fewer dedicated ranges.", "sources": [{"title": "Sportstar", "url": "https://sportstar.thehindu.com"}]},
            {"angle": "Economics", "paragraph": "Trap shooting requires expensive imported cartridges and clay targets, which has historically limited grassroots participation compared to more accessible shooting disciplines.", "sources": [{"title": "Olympic Khel", "url": "https://olympics.com"}]},
            {"angle": "India Impact", "paragraph": "The win is expected to boost funding and visibility for shotgun shooting events ahead of the next Olympic cycle, and may inspire more young women to take up the sport.", "sources": [{"title": "Times of India", "url": "https://timesofindia.com"}]},
        ],
        "dropped_angles": ["Geopolitics"],
    },
    "cricket-wtc-final": {
        "id": "cricket-wtc-final",
        "topic": "India reaches World Test Championship final",
        "category": "Sports",
        "tags": ["india", "sports"],
        "type": "quick_read",
        "headline": "INDIA SEALS WORLD TEST CHAMPIONSHIP FINAL BERTH AFTER DECISIVE SERIES WIN",
        "summary": "India secured a spot in the World Test Championship final after a decisive series win, finishing on top of the points table. It will be India's third WTC final appearance, having fallen short in the previous two.",
        "summary_sources": [{"title": "ICC Standings", "url": "https://icc-cricket.com"}],
        "sections": [],
        "dropped_angles": [],
    },
    "gaganyaan-test": {
        "id": "gaganyaan-test",
        "topic": "ISRO completes Gaganyaan uncrewed test flight",
        "category": "Science",
        "tags": ["trending", "india", "science"],
        "type": "deep_dive",
        "headline": "ISRO PULLS OFF KEY UNCREWED TEST FLIGHT, MOVING INDIA A STEP CLOSER TO ITS FIRST HUMAN SPACEFLIGHT",
        "summary": "ISRO successfully completed an uncrewed test flight of the Gaganyaan crew module, testing the crew escape system and parachute-based splashdown recovery. Officials say a crewed mission remains on track for the next couple of years, pending further test flights.",
        "summary_sources": [{"title": "ISRO Press Release", "url": "https://isro.gov.in"}],
        "sections": [
            {"angle": "History", "paragraph": "India has developed human spaceflight capability gradually since the Gaganyaan programme was approved in 2018, with this uncrewed test following two earlier abort-system tests.", "sources": [{"title": "ISRO archive", "url": "https://isro.gov.in"}]},
            {"angle": "Economics", "paragraph": "The programme has cost several billion rupees so far, with officials arguing the spin-off technologies in materials science and life support systems justify the investment beyond prestige alone.", "sources": [{"title": "Economic Times", "url": "https://economictimes.com"}]},
            {"angle": "Geopolitics", "paragraph": "A successful crewed mission would make India only the fourth country to independently send humans to space, joining the US, Russia, and China.", "sources": [{"title": "Reuters", "url": "https://reuters.com"}]},
            {"angle": "India Impact", "paragraph": "Beyond prestige, the programme is expected to feed into India's planned space station and deepen the domestic aerospace supply chain over the next decade.", "sources": [{"title": "The Hindu", "url": "https://thehindu.com"}]},
        ],
        "dropped_angles": [],
    },
    "sleep-research": {
        "id": "sleep-research",
        "topic": "New research links consistent sleep timing to better health",
        "category": "Daily Rituals",
        "tags": ["trending", "daily-rituals"],
        "type": "quick_read",
        "headline": "NEW STUDY FINDS WHEN YOU SLEEP MATTERS AS MUCH AS HOW LONG, EVEN IF YOU HIT SEVEN HOURS",
        "summary": "A large observational study found that irregular sleep timing was linked to worse cardiovascular and metabolic health markers, even among people who got a full seven to eight hours of sleep on average. Researchers say consistency may matter as much as total duration.",
        "summary_sources": [{"title": "Sleep Health Journal", "url": "https://sleephealthjournal.org"}],
        "sections": [],
        "dropped_angles": [],
    },
    "morning-routine-trend": {
        "id": "morning-routine-trend",
        "topic": "Cold showers and morning walks trend among young professionals",
        "category": "Daily Rituals",
        "tags": ["daily-rituals"],
        "type": "quick_read",
        "headline": "COLD SHOWERS AND EARLY MORNING WALKS ARE HAVING A MOMENT AMONG YOUNG PROFESSIONALS",
        "summary": "Surveys and app usage data suggest a rising number of young professionals in Indian metros are adopting structured morning routines, from cold showers to early walks, often influenced by wellness content online. Doctors note the benefits are real but caution against overly rigid routines becoming a source of stress themselves.",
        "summary_sources": [{"title": "Mint Lifestyle", "url": "https://livemint.com"}],
        "sections": [],
        "dropped_angles": [],
    },
}


def topic_summary(t):
    return {"id": t["id"], "topic": t["topic"], "category": t["category"], "tags": t["tags"], "headline": t["headline"]}


# ---------------------------------------------------------------------------
# Page routes
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
# API routes — replace bodies with real agent/RAG calls when ready
# ---------------------------------------------------------------------------
@app.route("/api/topics")
def api_topics():
    tag = request.args.get("tag")
    category = request.args.get("category")
    items = list(TOPICS.values())
    if tag:
        items = [t for t in items if tag in t["tags"]]
    if category:
        items = [t for t in items if t["category"].lower() == category.lower()]
    return jsonify([topic_summary(t) for t in items])


@app.route("/api/topics/<topic_id>")
def api_topic(topic_id):
    t = TOPICS.get(topic_id)
    if not t:
        return jsonify({"error": "not found"}), 404
    return jsonify(t)


@app.route("/api/explain", methods=["POST"])
def api_explain():
    data = request.get_json(force=True, silent=True) or {}
    query = data.get("topic", "").strip()
    if not query:
        return jsonify({"error": "topic is required"}), 400

    for t in TOPICS.values():
        if query.lower() in t["topic"].lower():
            return jsonify(t)

    new_id = "live-" + re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:40]
    new_topic = {
        "id": new_id,
        "topic": query,
        "category": "Tech",
        "tags": [],
        "type": "quick_read",
        "headline": f"HERE'S WHAT'S ACTUALLY HAPPENING WITH: {query.upper()}",
        "summary": "This is a live-search placeholder. Once your Triage and Researcher agents are wired in here, this endpoint will return a real Tavily-sourced, RAG-backed summary instead.",
        "summary_sources": [{"title": "Live search — connect your agents", "url": "#"}],
        "sections": [],
        "dropped_angles": [],
    }
    TOPICS[new_id] = new_topic
    return jsonify(new_topic)


if __name__ == "__main__":
    app.run(debug=True)