"""Central configuration for daily-design-brief pipeline.

Tune ingestion knobs (counts, windows, search queries) here without
touching the fetch/render logic.
"""

from datetime import timezone, timedelta

# ── Shared constants ───────────────────────────────────────────────
# Output / state files (single source of truth across fetch + render).
DATA_FILE = "data.json"
ARCHIVE_FILE = "archive.json"
PODCAST_STATE_FILE = "podcast_state.json"
BRIEFS_DIR = "briefs"

# Claude model used for all curation / summarisation calls.
CLAUDE_MODEL = "claude-sonnet-4-5"

# Claude Sonnet 4.5 計價（USD / 百萬 tokens）— 把 resp.usage 換算成每日真實花費。
# ⚠️ 換模型時記得一起更新這裡，否則 usage_log 的金額會失準。
CLAUDE_PRICING = {"input": 3.0, "output": 15.0}

# Groq whisper-large-v3 轉錄計價（USD / 小時音檔）。
WHISPER_PRICE_PER_HOUR = 0.111

# 每日 API token / 轉錄花費的累計記錄（依日期彙整，跨 tweets/PH/podcast 三支腳本）。
USAGE_LOG_FILE = "usage_log.json"

# Asia/Taipei (UTC+8) — pipeline runs and date stamping use this.
TPE = timezone(timedelta(hours=8))

# HTTP client knobs.
USER_AGENT = "Mozilla/5.0 (daily-design-brief)"
USER_AGENT_PODCAST = "Mozilla/5.0 (daily-design-brief podcast fetcher)"
HTTP_TIMEOUT = 30
HTTP_TIMEOUT_LONG = 180

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

# ── 財經 Podcast 重點（財經皓角 / 股癌 / M觀點）───────────────────
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
    {
        # 規律更新、每天檢查一次即可 → 標記 morning_only：晚間 22:00 那次跳過，
        # 只在早上 daily.yml 那次抓（晚間檢查是給股癌這類不定時更新的節目用的）。
        "name": "M觀點",
        "itunes_id": "1487378625",
        "rss": "https://feeds.soundon.fm/podcasts/b8f5a471-f4f7-4763-9678-65887beda63a.xml",
        "morning_only": True,
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
