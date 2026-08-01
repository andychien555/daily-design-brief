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
ARTICLE_STATE_FILE = "article_state.json"
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
# 抓需要「像瀏覽器」的站（如 uxtigers.com 文章頁）時用，避免被基本 bot 過濾擋掉。
USER_AGENT_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
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

# ── 好文 / Newsletter 精選 ─────────────────────────────────────────
# 每有新文章就抓「全文」→ Claude 整理成中文重點，渲染成 X 貼文卡片。
# 純文字文章、無音檔 → 不需 Whisper。
#
# discovery（找近期文章清單）：
#   - "direct"（預設）：httpx 直接抓 RSS。
#   - "jina"          ：改用 r.jina.ai reader 抓 feed（jina 從自家 IP 抓，
#                       繞過 Cloudflare TLS 指紋封鎖與 Substack 機房 IP 封鎖）。
# fulltext（取全文）：
#   - "feed"：RSS 的 content:encoded 已含整篇全文（未被擋時最省）。
#   - "page"：RSS 只有摘要 → 用 r.jina.ai reader 抓文章頁全文。
#   - "wix" ：uxtigers.com（Wix server-rendered）專用正文擷取。
#   （discovery 走 jina 的來源，內文也一律走 jina，故 fulltext 對它們不生效。）
#
# 為何這樣配（實測結論）：
#   - Import AI：作者自家 WordPress（jack-clark.net）掛 Cloudflare，curl 過但
#     httpx 吃 403（TLS 指紋），CI 只裝 httpx → discovery 與內文都走 jina。
#   - NN/g：官網 RSS 不擋 httpx（direct）；RSS 只有摘要 → 內文走 jina（page）。
#   - Design with AI：只在 Substack，機房 IP 會被 403 → discovery 與內文走 jina。
#   - Jakob Nielsen：uxtigers.com（Wix）不擋機房，維持 direct + wix 正文擷取。
#   - Y Combinator：YC 官方週報「This Week at YC」。內容不在 blog 上——blog 的
#     newsletter tag 是空的，blog RSS 只有零星 YC 公司新聞（一年約 6 篇）。真正
#     每期全文在 Mailchimp 公開存檔 feed，httpx 直連不被擋 → direct + feed。
# `topic` 會餵進 Claude 系統提示，讓摘要口吻／取材貼近該來源主題。
ARTICLE_JINA_PREFIX = "https://r.jina.ai/"
ARTICLE_FEEDS = [
    {
        "name": "Jakob Nielsen",
        "handle": "jakobnielsen",
        "rss": "https://www.uxtigers.com/blog-feed.xml",
        "source": "UX Tigers",
        "discover": "direct",
        "fulltext": "wix",
        "topic": "使用者體驗、AI 與產品設計（作者為 UX 專家 Jakob Nielsen）",
    },
    {
        "name": "Import AI",
        "handle": "importai",
        "rss": "https://jack-clark.net/feed/",
        "source": "Import AI",
        "discover": "jina",
        "show_within_days": 14,  # 週報，偶有跳週 → 放寬窗避免漏抓
        "topic": "AI 研究進展、產業趨勢與政策（Jack Clark 的 Import AI 週報）",
    },
    {
        "name": "NN/g Nielsen Norman Group",
        "handle": "nngroup",
        "rss": "https://www.nngroup.com/feed/rss/",
        "source": "NN/g",
        "discover": "direct",
        "fulltext": "page",
        "topic": "UX 研究、易用性與介面設計（Nielsen Norman Group 的 UX 專文）",
    },
    {
        "name": "Design with AI",
        "handle": "designwithai",
        "rss": "https://designwithai.substack.com/feed",
        "source": "Substack",
        "discover": "jina",
        "show_within_days": 14,  # 雙週更 → 放寬窗，否則常態被 7 天窗擋掉
        "topic": "AI × 產品／UX 設計的實作與工作流（Xinran Ma 的 Design with AI）",
    },
    {
        "name": "Y Combinator",
        "handle": "ycombinator",
        # Mailchimp 公開存檔 feed（保留最近 10 期，content:encoded 帶整封全文）。
        "rss": "https://us7.campaign-archive.com/feed?u=6507bf4e4c2df3fdbae6ef738&id=547725049b",
        "source": "This Week at YC",
        "discover": "direct",
        "fulltext": "feed",
        "show_within_days": 14,  # 名為週報但常跳期（2026/6 整月停更）→ 放寬窗
        "topic": (
            "創業、AI 產業趨勢與 YC 生態動態（YC 官方週報 This Week at YC）。"
            "每期固定四段：The Latest（本週主打的深度觀點或教學）、YC Community"
            "（YC 公司新聞）、The Launchpad（本週新開張的 YC 公司）、Hacker News"
            "（本週 HN 熱門貼文）。四段都要涵蓋，並直接用「本週主打」「YC 動態」"
            "「新創 launch」「HN 熱門」當重點標籤；名單型的段落請歸納趨勢"
            "（例如題目集中在哪類），不要逐家照抄"
        ),
    },
]
# 只顯示近 N 天內發布的文章（作者約每週兩篇，7 天窗可持續顯示最新一兩篇）。
ARTICLE_SHOW_WITHIN_DAYS = 7
# 單次最多處理幾篇（防首跑或補跑時 backlog 一次爆量、狂打 Claude）。
ARTICLE_MAX_ITEMS = 4
# 全文 map-reduce 門檻（字數）— 與 podcast 同策略。
ARTICLE_SUMMARY_SINGLE_PASS_MAX = 40000
ARTICLE_SUMMARY_CHUNK_CHARS = 12000
