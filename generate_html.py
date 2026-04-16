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

def tweet_card(tweet: dict) -> str:
    text = tweet["text"].replace("<", "&lt;").replace(">", "&gt;")
    author = tweet["author"] or "unknown"
    name = tweet["name"] or author
    likes = tweet["likes"]
    retweets = tweet["retweets"]
    url = tweet["url"] or f"https://x.com/{author}"

    # Format numbers
    def fmt(n):
        if n >= 1000:
            return f"{n/1000:.1f}k"
        return str(n)

    return f"""
    <article class="tweet-card">
      <div class="tweet-meta">
        <a href="https://x.com/{author}" target="_blank" class="tweet-author">
          <span class="author-name">{name}</span>
          <span class="author-handle">@{author}</span>
        </a>
        <a href="{url}" target="_blank" class="tweet-link">↗</a>
      </div>
      <p class="tweet-text">{text}</p>
      <div class="tweet-stats">
        <span>♡ {fmt(likes)}</span>
        <span>↺ {fmt(retweets)}</span>
      </div>
    </article>"""

def section_block(section: dict) -> str:
    cards = "\n".join(tweet_card(t) for t in section["tweets"])
    label = section["label"]
    return f"""
  <section class="topic-section">
    <h2 class="topic-label">{label}</h2>
    <div class="cards-grid">
      {cards}
    </div>
  </section>"""

def generate(data: dict) -> str:
    date_display = data["date_display"]
    sections_html = "\n".join(section_block(s) for s in data["sections"])
    total = sum(len(s["tweets"]) for s in data["sections"])

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

    /* ── Section ── */
    .topic-section {{
      margin-bottom: 3.5rem;
    }}
    .topic-label {{
      font-family: 'DM Serif Display', serif;
      font-size: 1.4rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: .4rem;
      margin-bottom: 1.25rem;
    }}

    /* ── Cards grid ── */
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
    }}

    .tweet-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 1.1rem 1.2rem;
      display: flex;
      flex-direction: column;
      gap: .6rem;
      transition: background .15s, border-color .15s, transform .15s;
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

    .tweet-text {{
      font-size: .84rem;
      line-height: 1.65;
      color: #2a2520;
      flex: 1;
      /* clamp to ~6 lines */
      display: -webkit-box;
      -webkit-line-clamp: 6;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .tweet-stats {{
      display: flex;
      gap: 1rem;
      font-size: .72rem;
      color: var(--muted);
      border-top: 1px solid var(--border);
      padding-top: .5rem;
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
    每日從 X (Twitter) 自動精選 Product Design、UI/UX、Design Systems、Product Management 相關熱門推文，
    每天早上 09:00 (UTC+8) 自動更新。
  </p>

  <div class="archive-link">
    <a href="archive.html">📁 歷史存檔 →</a>
  </div>

  {sections_html}
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

    # Store a compact summary (no full tweet text to keep file small)
    entry = {
        "date": data["date"],
        "date_display": data["date_display"],
        "generated_at": data["generated_at"],
        "total": sum(len(s["tweets"]) for s in data["sections"]),
        "sections": [{"label": s["label"], "count": len(s["tweets"])} for s in data["sections"]],
    }

    # Replace or prepend
    archive = [e for e in archive if e["date"] != data["date"]]
    archive.insert(0, entry)
    archive = archive[:90]  # keep last 90 days

    archive_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ archive.json updated ({len(archive)} entries)")

if __name__ == "__main__":
    main()
