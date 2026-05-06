"""Central configuration for daily-design-brief pipeline.

Tune ingestion knobs (counts, windows, search queries) here without
touching the fetch/render logic.
"""

# ── Twitter / X ingestion ──────────────────────────────────────────
TWEETS_TOP_N = 15
TWEETS_SINCE_DAYS = 2
TWEETS_API_BASE_DEFAULT = "https://ai.6551.io"
# Twitter `lang` codes; "zh" covers both Traditional and Simplified Chinese.
TWEETS_LANGS = ["en", "zh"]

SEARCH_QUERIES = [
    {"label": "Design",             "query": "design",             "min_likes": 500},
    {"label": "UX Design",          "query": "UX design",          "min_likes": 500},
    {"label": "UX Research",        "query": "UX research",        "min_likes": 500},
    {"label": "Product Management", "query": "product management", "min_likes": 500},
    {"label": "AI Product",         "query": "AI product",         "min_likes": 500},
    {"label": "Vibe Coding",        "query": "vibe coding",        "min_likes": 500},
    {"label": "Growth",             "query": "growth",             "min_likes": 500},
    # Targeted queries to catch AI-lab design/product launches that broad
    # keywords miss (e.g. @Flomerboy's Claude tips).
    {"label": "Claude",             "query": "claude",             "min_likes": 500},
    {"label": "OpenAI",             "query": "openai",             "min_likes": 500},
    {"label": "Gemini",             "query": "gemini",             "min_likes": 500},
    {"label": "Tech Hiring",        "query": "tech hiring",        "min_likes": 2000},
    {"label": "Job Market",         "query": "job market",         "min_likes": 2000},
]

# ── Product Hunt ingestion ─────────────────────────────────────────
PRODUCTS_TOP_N = 6
PRODUCTS_WINDOW_DAYS = 2
PRODUCTS_RSS_URL = "https://www.producthunt.com/feed"
