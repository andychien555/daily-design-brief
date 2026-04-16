#!/usr/bin/env python3
"""
generate_html.py
Reads data.json and renders a beautiful static HTML morning brief.
"""

import json
from pathlib import Path
from datetime import datetime

def load_data() -> dict:
    with open("data.json", encoding="utf-8") as f:
        return json.load(f)

def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def tweet_card(tweet: dict, rank: int) -> str:
    text = esc(tweet["text"])
    summary = esc(tweet.get("summary_zh", ""))
    author = tweet["author"] or "unknown"
    name = esc(tweet["name"] or author)
    source = esc(tweet.get("source", ""))
    likes = tweet["likes"]
    retweets = tweet["retweets"]
    url = tweet["url"] or f"https://x.com/{author}"

    def fmt(n):
        if n >= 1000:
            return f"{n/1000:.1f}k"
        return str(n)

    summary_html = f'<p class="tweet-summary">{summary}</p>' if summary else ""
    source_html = f'<span class="tweet-source">{source}</span>' if source else ""

    return f"""
    <article class="tweet-card">
      <div class="tweet-rank">#{rank}</div>
      <div class="tweet-meta">
        <a href="https://x.com/{author}" target="_blank" class="tweet-author">
          <span class="author-name">{name}</span>
          <span class="author-handle">@{author}</span>
        </a>
        <a href="{url}" target="_blank" class="tweet-link">↗</a>
      </div>
      {summary_html}
      <p class="tweet-text">{text}</p>
      <div class="tweet-stats">
        <span>♡ {fmt(likes)}</span>
        <span>↺ {fmt(retweets)}</span>
        {source_html}
      </div>
    </article>"""

def criteria_block(criteria: dict) -> str:
    if not criteria:
        return ""
    kw_rows = "".join(
        f"<tr><td>{esc(k['label'])}</td><td><code>{esc(k['query'])}</code></td><td>≥ {k['min_likes']}</td></tr>"
        for k in criteria.get("keyword_pools", [])
    )
    kol_rows = "".join(
        f"<tr><td>{esc(g['label'])}</td><td>{esc(', '.join('@'+u for u in g['users']))}</td></tr>"
        for g in criteria.get("kol_pools", [])
    )
    top_n = criteria.get("top_n", 10)
    formula = esc(criteria.get("score_formula", "likes + retweets × 2"))
    return f"""
  <details class="criteria">
    <summary>📋 篩選標準（點開看我怎麼選的）</summary>
    <div class="criteria-body">
      <p>每天從下列 <strong>關鍵字</strong> 與 <strong>KOL 追蹤</strong> 池合併所有候選推文，去重後依熱度分數排序，取 <strong>Top {top_n}</strong>，再由 Claude 產生中文摘要。</p>
      <p><strong>熱度分數</strong>：<code>{formula}</code></p>

      <h4>關鍵字搜尋池</h4>
      <table>
        <thead><tr><th>主題</th><th>查詢字</th><th>讚數門檻</th></tr></thead>
        <tbody>{kw_rows}</tbody>
      </table>

      <h4>KOL 追蹤池</h4>
      <table>
        <thead><tr><th>分組</th><th>帳號</th></tr></thead>
        <tbody>{kol_rows}</tbody>
      </table>

      <p class="criteria-note">語言過濾：English、排除 replies / retweets。摘要由 Claude Haiku 4.5 自動生成，僅供快速瀏覽，實際內容請以原推文為準。</p>
    </div>
  </details>"""

def generate(data: dict) -> str:
    date_display = data["date_display"]
    top_tweets = data.get("top_tweets") or []
    total = len(top_tweets)
    cards_html = "\n".join(tweet_card(t, i + 1) for i, t in enumerate(top_tweets))
    criteria_html = criteria_block(data.get("criteria", {}))

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Product & Design 每日早報 · {data['date']}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --ink:     #0f0e0d;
      --paper:   #f5f2ec;
      --accent:  #c8460a;
      --muted:   #8a8070;
      --border:  #d8d0c4;
      --card-bg: #faf8f4;
      --hover:   #fff9f4;
    }}

    html {{ font-size: 16px; }}

    body {{
      font-family: 'DM Sans', sans-serif;
      background: var(--paper);
      color: var(--ink);
      min-height: 100vh;
    }}

    /* ── Header ── */
    header {{
      border-bottom: 2px solid var(--ink);
      padding: 2.5rem 0 1.5rem;
      text-align: center;
      position: relative;
    }}
    .masthead-label {{
      font-size: .7rem;
      font-weight: 500;
      letter-spacing: .2em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: .5rem;
    }}
    .masthead-title {{
      font-family: 'DM Serif Display', serif;
      font-size: clamp(2.4rem, 6vw, 4.5rem);
      line-height: 1;
      letter-spacing: -.02em;
    }}
    .masthead-title em {{
      font-style: italic;
      color: var(--accent);
    }}
    .masthead-date {{
      margin-top: .75rem;
      font-size: .8rem;
      letter-spacing: .1em;
      color: var(--muted);
    }}
    .masthead-rule {{
      width: 40px;
      height: 2px;
      background: var(--accent);
      margin: 1rem auto 0;
    }}

    /* ── Layout ── */
    main {{
      max-width: 960px;
      margin: 0 auto;
      padding: 2.5rem 1.5rem 5rem;
    }}

    .brief-intro {{
      font-size: .85rem;
      color: var(--muted);
      border-left: 3px solid var(--accent);
      padding-left: .75rem;
      margin-bottom: 3rem;
      line-height: 1.6;
    }}

    /* ── Criteria ── */
    .criteria {{
      margin-bottom: 2.5rem;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--card-bg);
    }}
    .criteria > summary {{
      cursor: pointer;
      padding: .85rem 1.1rem;
      font-size: .85rem;
      font-weight: 500;
      list-style: none;
      user-select: none;
    }}
    .criteria > summary::-webkit-details-marker {{ display: none; }}
    .criteria > summary::before {{
      content: '▸';
      display: inline-block;
      margin-right: .5rem;
      color: var(--accent);
      transition: transform .15s;
    }}
    .criteria[open] > summary::before {{ transform: rotate(90deg); }}
    .criteria-body {{
      padding: 0 1.1rem 1.1rem;
      font-size: .8rem;
      line-height: 1.6;
      color: #3a332c;
    }}
    .criteria-body p {{ margin-bottom: .75rem; }}
    .criteria-body h4 {{
      font-family: 'DM Serif Display', serif;
      font-size: 1rem;
      margin: 1.25rem 0 .5rem;
      color: var(--ink);
    }}
    .criteria-body table {{
      width: 100%;
      border-collapse: collapse;
      font-size: .75rem;
      margin-bottom: .5rem;
    }}
    .criteria-body th, .criteria-body td {{
      text-align: left;
      padding: .4rem .5rem;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    .criteria-body th {{
      color: var(--muted);
      font-weight: 500;
      font-size: .7rem;
      letter-spacing: .05em;
      text-transform: uppercase;
    }}
    .criteria-body code {{
      background: rgba(200, 70, 10, 0.08);
      color: var(--accent);
      padding: 1px 6px;
      border-radius: 3px;
      font-size: .72rem;
    }}
    .criteria-note {{
      font-size: .72rem;
      color: var(--muted);
      margin-top: 1rem;
    }}

    /* ── Cards grid ── */
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1rem;
    }}

    .tweet-card {{
      position: relative;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 1.1rem 1.2rem;
      display: flex;
      flex-direction: column;
      gap: .55rem;
      transition: background .15s, border-color .15s, transform .15s;
    }}
    .tweet-rank {{
      position: absolute;
      top: -10px;
      left: -8px;
      background: var(--accent);
      color: var(--paper);
      font-family: 'DM Serif Display', serif;
      font-size: .8rem;
      line-height: 1;
      padding: .3rem .5rem;
      border-radius: 3px;
    }}
    .tweet-card:hover {{
      background: var(--hover);
      border-color: var(--accent);
      transform: translateY(-2px);
    }}

    .tweet-meta {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: .5rem;
    }}
    .tweet-author {{
      text-decoration: none;
      color: inherit;
      display: flex;
      flex-direction: column;
      gap: .1rem;
    }}
    .author-name {{
      font-size: .82rem;
      font-weight: 500;
    }}
    .author-handle {{
      font-size: .72rem;
      color: var(--muted);
    }}
    .tweet-link {{
      font-size: .9rem;
      color: var(--muted);
      text-decoration: none;
      flex-shrink: 0;
      transition: color .15s;
    }}
    .tweet-link:hover {{ color: var(--accent); }}

    .tweet-summary {{
      font-size: .88rem;
      line-height: 1.6;
      color: var(--ink);
      font-weight: 500;
      border-left: 2px solid var(--accent);
      padding-left: .65rem;
    }}

    .tweet-text {{
      font-size: .78rem;
      line-height: 1.6;
      color: var(--muted);
      flex: 1;
      display: -webkit-box;
      -webkit-line-clamp: 5;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .tweet-stats {{
      display: flex;
      gap: .85rem;
      align-items: center;
      font-size: .72rem;
      color: var(--muted);
      border-top: 1px solid var(--border);
      padding-top: .5rem;
      flex-wrap: wrap;
    }}
    .tweet-source {{
      margin-left: auto;
      font-size: .68rem;
      color: var(--muted);
      background: rgba(138, 128, 112, 0.1);
      padding: 2px 7px;
      border-radius: 2px;
    }}

    /* ── Footer ── */
    footer {{
      text-align: center;
      font-size: .72rem;
      color: var(--muted);
      padding: 2rem 1rem;
      border-top: 1px solid var(--border);
      letter-spacing: .05em;
    }}
    footer a {{
      color: var(--muted);
    }}

    /* ── Archive link ── */
    .archive-link {{
      text-align: right;
      font-size: .78rem;
      color: var(--muted);
      margin-bottom: 2rem;
    }}
    .archive-link a {{
      color: var(--accent);
      text-decoration: none;
    }}

    @media (max-width: 480px) {{
      .cards-grid {{ grid-template-columns: 1fr; }}
      .masthead-title {{ font-size: 2rem; }}
    }}
  </style>
</head>
<body>

<header>
  <p class="masthead-label">Daily Brief</p>
  <h1 class="masthead-title">Product &amp; <em>Design</em></h1>
  <p class="masthead-date">{date_display} &nbsp;·&nbsp; {total} 則精選推文</p>
  <div class="masthead-rule"></div>
</header>

<main>
  <p class="brief-intro">
    每日從 X (Twitter) 自動精選 Product Design、UI/UX、Product Management、AI × Design 與設計師 KOL 的 Top {total} 熱門推文，
    並用 Claude 產生中文摘要，每天早上 09:00 (UTC+8) 自動更新。
  </p>

  <div class="archive-link">
    <a href="archive.html">📁 歷史存檔 →</a>
  </div>

  {criteria_html}

  <div class="cards-grid">
    {cards_html}
  </div>
</main>

<footer>
  <p>自動生成 · 資料來源 <a href="https://6551.io" target="_blank">6551.io</a> &amp; X/Twitter &nbsp;·&nbsp; {data['generated_at'][:16].replace('T', ' ')}</p>
</footer>

</body>
</html>"""

def main():
    data = load_data()
    html = generate(data)

    Path("index.html").write_text(html, encoding="utf-8")
    print(f"✅ index.html generated for {data['date']}")

    # Also append to archive.json for history page
    archive_path = Path("archive.json")
    archive = []
    if archive_path.exists():
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8"))
        except Exception:
            archive = []

    top = data.get("top_tweets") or []
    sources = sorted({t.get("source", "") for t in top if t.get("source")})
    entry = {
        "date": data["date"],
        "date_display": data["date_display"],
        "generated_at": data["generated_at"],
        "total": len(top),
        "sources": sources,
    }

    # Replace or prepend
    archive = [e for e in archive if e["date"] != data["date"]]
    archive.insert(0, entry)
    archive = archive[:90]  # keep last 90 days

    archive_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ archive.json updated ({len(archive)} entries)")

if __name__ == "__main__":
    main()
