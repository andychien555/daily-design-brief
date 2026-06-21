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

# ── 財經 Podcast 重點（游庭皓的財經皓角）──────────────────────────
# 每天從 podcast RSS 偵測最新一集，下載直連 MP3 → Groq Whisper 轉錄 →
# Claude 整理成結構化筆記，渲染在早報最上方。
# 改用 podcast 取代 YouTube：直連 MP3 不被機房 IP 封鎖，無需 cookies/代理。
# RSS 來源：iTunes Lookup 查到的「游庭皓的財經皓角」feed（SoundCloud host）。
# 追蹤的 podcast 清單。每個都會偵測「最新一集」，新集就轉錄＋摘要進日報。
# rss 為主來源（直連最即時）；itunes_id 當 feedUrl 失效時的重新定位備援。
PODCASTS = [
    {
        "name": "游庭皓的財經皓角",
        "itunes_id": "1488295306",
        "rss": "https://feeds.soundcloud.com/users/soundcloud:users:735679489/sounds.rss",
    },
    {
        "name": "股癌 Gooaye",
        "itunes_id": "1500839292",
        "rss": "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml",
    },
]
# 只顯示「發布在近 N 天內」的最新一集（股癌週更也能持續顯示，過舊則自動隱藏）。
PODCAST_SHOW_WITHIN_DAYS = 7
# Groq Whisper 轉錄設定（podcast 無字幕，一律走 Whisper）。
PODCAST_GROQ_MODEL = "whisper-large-v3"
PODCAST_WHISPER_LANGUAGE = "zh"
# 音訊超過此 MB 數 → 用 ffmpeg 切段後逐段轉錄串接。
PODCAST_AUDIO_SEGMENT_MB = 24
PODCAST_AUDIO_SEGMENT_SECONDS = 1500
# 逐字稿 map-reduce 門檻（字數）。
PODCAST_SUMMARY_SINGLE_PASS_MAX = 40000
PODCAST_SUMMARY_CHUNK_CHARS = 12000
