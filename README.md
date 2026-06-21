# Product & Design 每日早報

每天台北早上 08:00 自動從 X/Twitter 與 Product Hunt 抓 Product & Design 相關熱門內容，並追蹤多個財經 podcast（游庭皓的財經皓角、股癌 Gooaye、M觀點）抓最新一集做語音轉錄重點，用 Claude 篩選並翻譯成繁體中文摘要，產生靜態網站。

## 架構

```
觸發（兩來源，先到先跑，dedup step 防重複）：
  • Vercel Cron     — workflow_dispatch，每天 08:00 Asia/Taipei (00:00 UTC)，主
  • GitHub schedule — schedule cron，每天 10:00 Asia/Taipei (02:00 UTC)，備援
        │
        ▼
GitHub Actions: Daily Design Brief
  ├─ fetch_tweets.py        # 6551.io API 抓推 → Claude 篩選翻譯
  ├─ fetch_producthunt.py   # PH Atom feed + GraphQL → Claude 摘要
  ├─ fetch_podcast.py       # 逐台偵測 podcast 最新集 MP3 → Groq Whisper 轉錄 → Claude 整理（continue-on-error）
  ├─ generate_html.py       # 渲染 index.html / briefs/*.html / archive.json
  ├─ generate_md.py         # 寫 briefs/*.md（同時是翻譯快取）
  └─ git commit & push
        └─ Deploy workflow ─► GitHub Pages
```

財經 podcast 每天檢查新集（節目更新時間不定，尤其股癌）：

```
  • Daily Design Brief（daily.yml）  — 台北早上一起跑 fetch_podcast.py（所有節目）
  • Podcast Check（podcast-check.yml）— 台北 22:00 (UTC 14:00) 再補一次，只跑 podcast + 重建頁面
```

> 標記 `morning_only` 的節目（規律更新、每天一次即可，如 M觀點）只在早上那次抓；
> 晚間 22:00 那次會跳過、沿用早上的 brief（透過 `PODCAST_RUN=evening` 環境變數控制）。
> 沒標的（如股癌、財經皓角）兩次都檢查，靠 `podcast_state.json` 冪等快取避免重轉錄。

> 財經重點曾用 YouTube 直播當來源，但 GitHub Actions 機房 IP 會被 YouTube 當機器人擋下（cookies 撐不久）。改用 podcast enclosure 直連 MP3 後，機房抓取屬正常行為、不被封鎖，無需 cookies/代理，穩定許多。轉錄走 Groq Whisper，因此 workflow 會先確保 `ffmpeg` 存在（大檔切段用）。

`workflow_run` 監聽 **Daily Design Brief**、**Backfill Translations**、**Podcast Check** 三支 workflow 完成事件，觸發 [deploy.yml](.github/workflows/deploy.yml) 把 `index.html` / `briefs/` 部署到 Pages。

## Setup（一次性設定）

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/daily-design-brief.git
cd daily-design-brief
```

### 2. GitHub Secrets

Repo → Settings → Secrets and variables → Actions：

| Secret | 用途 | 取得位置 |
|---|---|---|
| `TWITTER_TOKEN` | 6551.io Twitter Search API | [6551.io/mcp](https://6551.io/mcp) |
| `ANTHROPIC_API_KEY` | Claude 篩選 + 中文翻譯 + podcast 摘要 | [Anthropic Console](https://console.anthropic.com/settings/keys) |
| `PRODUCTHUNT_API_TOKEN` | Product Hunt GraphQL API | [PH API Dashboard](https://www.producthunt.com/v2/oauth/applications) |
| `GROQ_API_KEY` | Groq Whisper 轉錄 podcast 音檔（沒設定則略過財經區塊） | [Groq Console](https://console.groq.com/keys) |

### 3. 啟用 GitHub Pages

Repo → Settings → Pages → Source 選 **GitHub Actions**

### 4. 觸發設定

[daily.yml](.github/workflows/daily.yml) 有兩個觸發來源：

- **主**：`workflow_dispatch` — 由外部 Vercel Cron 透過 GitHub REST API 觸發（台北 08:00），比 GitHub 內建 `schedule:` 準時。
- **備援**：`schedule:` — GitHub 內建排程（台北 10:00 / UTC 02:00）。Vercel Cron 那天沒觸發時（例如 PAT 過期）由它接手；dedup step 偵測到當天已產生會自動 skip，不重複。

Vercel Cron 用的 GitHub token 存在 **Vercel 專案的 Environment Variables**（不是 repo secrets），到期需更新並 redeploy。手動觸發：
```
POST https://api.github.com/repos/USER/REPO/actions/workflows/daily.yml/dispatches
Body: { "ref": "main" }
Header: Authorization: Bearer <GH_TOKEN>
```

### 5. 第一次手動觸發

Actions → Daily Design Brief → Run workflow

## 自訂搜尋主題

編輯 [config.py](config.py)：

```python
TWEETS_TOP_N = 15            # 最終挑幾則
TWEETS_SINCE_DAYS = 2        # 時間窗（天）

SEARCH_QUERIES = [
    {"label": "Design", "query": "design", "min_likes": 300},
    # ...
]

PRODUCTS_TOP_N = 6
PRODUCTS_WINDOW_DAYS = 2
```

追蹤的財經 podcast 清單與轉錄參數也在 [config.py](config.py)。每台都會偵測「最新一集」，發布在近 `PODCAST_SHOW_WITHIN_DAYS` 天內就轉錄＋摘要進日報（新到舊、每台一則）：

```python
PODCASTS = [
    {"name": "游庭皓的財經皓角", "itunes_id": "1488295306", "rss": "https://feeds.soundcloud.com/.../sounds.rss"},
    {"name": "股癌 Gooaye",      "itunes_id": "1500839292", "rss": "https://feeds.soundon.fm/podcasts/....xml"},
    {"name": "M觀點",            "itunes_id": "1487378625", "rss": "https://feeds.soundon.fm/podcasts/....xml",
     "morning_only": True},  # 規律更新，每天只在早上那次檢查；晚間 22:00 跳過
]
PODCAST_SHOW_WITHIN_DAYS = 7   # 只顯示近 N 天內的最新集（週更節目也能持續顯示，過舊自動隱藏）

PODCAST_GROQ_MODEL = "whisper-large-v3"
PODCAST_WHISPER_LANGUAGE = "zh"
PODCAST_AUDIO_SEGMENT_MB = 24       # 超過就先轉 16kHz 單聲道再切段轉錄
PODCAST_AUDIO_SEGMENT_SECONDS = 1500
PODCAST_SUMMARY_SINGLE_PASS_MAX = 40000  # 逐字稿超過此長度 → map-reduce 摘要
PODCAST_SUMMARY_CHUNK_CHARS = 12000
```

> 加／換 podcast：在 `PODCASTS` 加一筆 `{name, itunes_id, rss}` 即可。`rss` 是主來源（最即時），失效時用 `itunes_id` 經 iTunes Lookup 重新定位 feedUrl。加上 `"morning_only": True` 則該台只在早上 daily.yml 那次檢查、晚間 22:00 跳過（適合規律更新、每天一次即可的節目）。`podcast_state.json` 以 `itunes_id:episode_id` 為鍵做冪等快取，同一集不會重轉錄/重摘要；單台失敗不影響其他台。

## API 用量

### 6551.io（Twitter Search）

每天約 **24–39 次 API call**：
- `len(SEARCH_QUERIES) × 2`（Latest + Top）≈ 24 次
- Top 15 候選的 quote/reply 補脈絡 ≈ 最多 15 次

> **2026-04-30 觀察**：實測打到第 9–10 次 call 就開始 `402 Payment Required`，後續 query 全部失敗。請以 [6551.io/mcp](https://6551.io/mcp) dashboard 的實際剩餘額度為準；如果頻繁打到 cap，可：
> - 縮減 `SEARCH_QUERIES` 數量
> - 升級付費方案

### Anthropic Claude

- `fetch_tweets.py`：1 次 `messages.create`（候選 JSON 進、JSON 帶 `summary_zh` 出）
- `fetch_producthunt.py`：1 次 `messages.create`（6 則產品中文摘要）
- `fetch_podcast.py`：逐字稿 ≤ `PODCAST_SUMMARY_SINGLE_PASS_MAX` 時 1 次 `messages.create`；超過則走 map-reduce（每段條列 + 1 次彙整）。

實測 < 10K tokens/天（podcast 長集 map-reduce 時略增）。模型：`claude-sonnet-4-5`。

### Groq Whisper（Podcast 轉錄）

- 每台每次最多 1 集（`PODCASTS` 有幾台就最多幾集）；命中 `podcast_state.json` 快取則 0 次。每天檢查兩次（早上 + 22:00），`morning_only` 的台只在早上那次檢查；通常只有新集那次才真的轉錄。
- 音檔 > `PODCAST_AUDIO_SEGMENT_MB` 會先用 `ffmpeg` 轉 16kHz 單聲道再切段，分段呼叫 `whisper-large-v3`。
- 沒設 `GROQ_API_KEY` 或沒裝 `groq`／`ffmpeg` → 轉錄回空字串，該台不顯示（不中斷早報）。

## 失敗 fallback 行為

| 失敗點 | 行為 |
|---|---|
| 6551.io 全部 402 | `top_tweets: []`，網站只剩 PH 區塊 |
| 6551.io 部分 402 | 已抓到的 tweets 照常處理，剩下 query skip |
| Anthropic quota 滿 | `summary_zh` 留空，按 likes 排序輸出英文原文 |
| Product Hunt 失敗 | `top_products: []`，僅出 tweets 區塊 |
| 某台 podcast 失敗 | 單台失敗只略過該台，其他台與整批早報照常（step 亦 `continue-on-error`） |
| Podcast RSS 主來源失效 | 自動用 iTunes Lookup（該台 `itunes_id`）重新取得 feedUrl 再抓 |
| 最新集發布超過 `PODCAST_SHOW_WITHIN_DAYS` 天 | 該台自動隱藏，不顯示過舊內容 |

> 翻譯快取機制：[fetch_tweets.py](fetch_tweets.py) 在送 Claude 之前會掃近 7 天的 `briefs/*.md`，若推文 id 已有 `summary_zh` 直接沿用，不重打 API。

## 檔案結構

| 路徑 | 說明 |
|---|---|
| [fetch_tweets.py](fetch_tweets.py) | 6551.io 抓推 → Claude 篩選翻譯 → 寫 `data.json` |
| [fetch_producthunt.py](fetch_producthunt.py) | PH Atom feed + GraphQL → Claude 摘要 → 併入 `data.json` |
| [fetch_podcast.py](fetch_podcast.py) | 逐台偵測 podcast 最新集 MP3 → Groq Whisper 轉錄 → Claude 整理 → 寫 `data.json["podcast_briefs"]`（多台、每台一則） |
| [generate_html.py](generate_html.py) | 渲染 `index.html`、`briefs/*.html`、更新 `archive.json`（財經重點逐則走 `briefing_section`，置於早報最上方） |
| [generate_md.py](generate_md.py) | 寫 `briefs/*.md`（也是隔天的翻譯快取） |
| [templates.py](templates.py) / [styles.py](styles.py) / [scripts.py](scripts.py) | HTML 模板 / CSS / JS |
| [config.py](config.py) | 搜尋 query、TopN、時間窗 |
| `data.json` | 當日原始資料（每日覆蓋），含 `podcast_briefs`（多台列表） |
| `podcast_state.json` | podcast 以 `itunes_id:episode_id` 為鍵的冪等快取，避免重轉錄/重摘要 |
| `archive.json` | 最近 90 天索引（headline + 數量），驅動側邊存檔列 |
| `briefs/YYYY-MM-DD.html` | 每天的 HTML 快照 |
| `briefs/YYYY-MM-DD.md` | 每天的 Markdown 版（人類可讀 + 翻譯快取） |
| [.github/workflows/daily.yml](.github/workflows/daily.yml) | 抓資料 → commit pipeline（早上含 podcast） |
| [.github/workflows/podcast-check.yml](.github/workflows/podcast-check.yml) | 台北 22:00 第二次 podcast 檢查 → 重建頁面 |
| [.github/workflows/deploy.yml](.github/workflows/deploy.yml) | GitHub Pages 部署 |
