# Product & Design 每日早報

每天早上 09:00（台灣時間）自動從 X/Twitter 搜尋 Product & Design 相關熱門推文，生成靜態網站。

## 架構

```
GitHub Actions (cron 每天 01:00 UTC)
  → fetch_tweets.py       # 呼叫 6551.io API 搜尋推文
  → fetch_producthunt.py  # 抓 Product Hunt Atom feed（新品）
  → generate_html.py      # 產生 index.html
  → generate_archive.py   # 產生 archive.html
  → git push              # 推到 repo
GitHub Pages              # 靜態網站自動更新
```

## Setup（一次性設定）

### 1. Fork / 建立這個 Repo

```bash
git clone https://github.com/YOUR_USERNAME/daily-design-brief.git
cd daily-design-brief
```

### 2. 設定 GitHub Secret

在 GitHub Repo → Settings → Secrets and variables → Actions → New repository secret：

| Name | Value |
|---|---|
| `TWITTER_TOKEN` | 你的 6551.io API Token（從 https://6551.io/mcp 取得） |

### 3. 啟用 GitHub Pages

Repo → Settings → Pages → Source 選 **GitHub Actions**

### 4. 第一次手動觸發

Actions → Daily Design Brief → Run workflow

網站就會在幾分鐘後上線：`https://YOUR_USERNAME.github.io/daily-design-brief/`

---

## 自訂搜尋主題

編輯 `config.py` 裡的 `SEARCH_QUERIES`（同檔還可調整 `TWEETS_TOP_N`、`TWEETS_SINCE_DAYS`、`PRODUCTS_TOP_N`、`PRODUCTS_WINDOW_DAYS` 等常數）：

```python
SEARCH_QUERIES = [
    {
        "label": "你的主題名稱",
        "query": "搜尋關鍵字",
        "min_likes": 200,  # 最低 likes 門檻
    },
    ...
]
```

## API 用量（6551.io）

計費單位：

| 單位 | 換算 |
|---|---|
| 1 message | 1 次 API call |
| 1 point | 20 messages |
| Free 每日 | **5 points = 100 messages**（每日 0:00 重置）|
| Free 每月 | 3,000 messages |

目前 pipeline 每天約打 **39 次 API**（12 queries × 2 passes + top 15 候選的 quote/reply 補脈絡），約占免費每日額度的 39%，免費額度足夠。

要擴充 query 數量、或開啟 top replies 等更耗 API 的功能再考慮升級：

- **Plus** $1.9/月 · 20,000 msgs/月（cap × 6.6 倍）
- **Pro** $29/月 · 200,000 msgs/月

dashboard：[6551.io/mcp](https://6551.io/mcp)

## 檔案說明

| 檔案 | 說明 |
|---|---|
| `fetch_tweets.py` | 呼叫 API、儲存 data.json |
| `fetch_producthunt.py` | 從 Product Hunt RSS 抓最近 2 天 Top 6 新品、Claude 做中文摘要、併入 data.json |
| `generate_html.py` | 把 data.json 渲染成 index.html |
| `generate_archive.py` | 更新 archive.html 歷史存檔頁 |
| `data.json` | 當天原始資料（每日覆蓋） |
| `archive.json` | 最近 90 天的紀錄索引 |
| `briefs/YYYY-MM-DD.html` | 每天的快照存檔 |
| `.github/workflows/daily.yml` | GitHub Actions 排程設定 |
