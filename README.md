# Product & Design 每日早報

每天台北早上 08:00 自動從 X/Twitter 與 Product Hunt 抓 Product & Design 相關熱門內容，用 Claude 篩選並翻譯成繁體中文摘要，產生靜態網站。

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
  ├─ generate_html.py       # 渲染 index.html / briefs/*.html / archive.json
  ├─ generate_md.py         # 寫 briefs/*.md（同時是翻譯快取）
  └─ git commit & push
        └─ Deploy workflow ─► GitHub Pages
```

`workflow_run` 監聽 Daily Design Brief 完成事件，觸發 [deploy.yml](.github/workflows/deploy.yml) 把 `index.html` / `briefs/` 部署到 Pages。

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
| `ANTHROPIC_API_KEY` | Claude 篩選 + 中文翻譯 | [Anthropic Console](https://console.anthropic.com/settings/keys) |
| `PRODUCTHUNT_API_TOKEN` | Product Hunt GraphQL API | [PH API Dashboard](https://www.producthunt.com/v2/oauth/applications) |

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

實測 < 10K tokens/天。模型：`claude-sonnet-4-5`。

## 失敗 fallback 行為

| 失敗點 | 行為 |
|---|---|
| 6551.io 全部 402 | `top_tweets: []`，網站只剩 PH 區塊 |
| 6551.io 部分 402 | 已抓到的 tweets 照常處理，剩下 query skip |
| Anthropic quota 滿 | `summary_zh` 留空，按 likes 排序輸出英文原文 |
| Product Hunt 失敗 | `top_products: []`，僅出 tweets 區塊 |

> 翻譯快取機制：[fetch_tweets.py](fetch_tweets.py) 在送 Claude 之前會掃近 7 天的 `briefs/*.md`，若推文 id 已有 `summary_zh` 直接沿用，不重打 API。

## 檔案結構

| 路徑 | 說明 |
|---|---|
| [fetch_tweets.py](fetch_tweets.py) | 6551.io 抓推 → Claude 篩選翻譯 → 寫 `data.json` |
| [fetch_producthunt.py](fetch_producthunt.py) | PH Atom feed + GraphQL → Claude 摘要 → 併入 `data.json` |
| [generate_html.py](generate_html.py) | 渲染 `index.html`、`briefs/*.html`、更新 `archive.json` |
| [generate_md.py](generate_md.py) | 寫 `briefs/*.md`（也是隔天的翻譯快取） |
| [templates.py](templates.py) / [styles.py](styles.py) / [scripts.py](scripts.py) | HTML 模板 / CSS / JS |
| [config.py](config.py) | 搜尋 query、TopN、時間窗 |
| `data.json` | 當日原始資料（每日覆蓋） |
| `archive.json` | 最近 90 天索引（headline + 數量），驅動側邊存檔列 |
| `briefs/YYYY-MM-DD.html` | 每天的 HTML 快照 |
| `briefs/YYYY-MM-DD.md` | 每天的 Markdown 版（人類可讀 + 翻譯快取） |
| [.github/workflows/daily.yml](.github/workflows/daily.yml) | 抓資料 → commit pipeline |
| [.github/workflows/deploy.yml](.github/workflows/deploy.yml) | GitHub Pages 部署 |
