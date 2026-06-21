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

# ── YouTube 財經直播重點（游庭皓的財經皓角）─────────────────────────
# 從頻道 /streams 分頁動態解析「最新一場已結束」的直播，取逐字稿後由
# Claude 整理成結構化筆記，渲染在早報最上方。
YT_CHANNEL_STREAMS_URL = "https://www.youtube.com/channel/UC0lbAQVpenvfA2QqzsRtL_g/streams"
YT_CHANNEL_NAME = "游庭皓的財經皓角｜早晨財經速解讀"
# 解析頻道最新直播時，先取前 N 筆候選再逐一檢查 live_status。
YT_CANDIDATE_COUNT = 6
# 逐字稿來源：先試字幕，內容過短/失敗才退回 Groq Whisper。
YT_PREFER_SUBTITLES = True
YT_SUBTITLE_LANGS = ["zh-Hant", "zh-TW", "zh-Hans", "zh", "zh-CN", "en"]
# 字幕純文字若少於此字數，視為品質不足 → 退回 Whisper。
YT_SUBTITLE_MIN_CHARS = 200
# Groq Whisper 轉錄設定。
YT_GROQ_MODEL = "whisper-large-v3"
YT_WHISPER_LANGUAGE = "zh"
# 音訊超過此 MB 數 → 用 ffmpeg 切段後逐段轉錄串接。
YT_AUDIO_SEGMENT_MB = 24
YT_AUDIO_SEGMENT_SECONDS = 1500
# 逐字稿 map-reduce 門檻（字數）。
YT_SUMMARY_SINGLE_PASS_MAX = 40000
YT_SUMMARY_CHUNK_CHARS = 12000
