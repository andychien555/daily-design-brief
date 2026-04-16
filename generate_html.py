#!/usr/bin/env python3
"""
generate_html.py
Reads data.json and renders an editorial-magazine-styled static HTML morning brief.
"""

import json
from pathlib import Path
from datetime import datetime

WEEKDAY_ZH = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def load_data() -> dict:
    with open("data.json", encoding="utf-8") as f:
        return json.load(f)


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_num(n: int) -> str:
    if n >= 10000:
        return f"{n/1000:.0f}k"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def issue_number(date_str: str) -> int:
    """Stable issue number derived from date — anchored at 2025-01-01 = №001."""
    try:
        anchor = datetime(2025, 1, 1).date()
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        delta = (d - anchor).days
        return max(1, delta + 1)
    except Exception:
        return 1


def weekday_zh(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return WEEKDAY_ZH[d.weekday()]
    except Exception:
        return ""


def lead_card(tweet: dict) -> str:
    """Hero / lead story — first tweet, full-width."""
    text = esc(tweet["text"])
    summary = esc(tweet.get("summary_zh", "")) or text[:120]
    author = tweet["author"] or "unknown"
    name = esc(tweet["name"] or author)
    source = esc(tweet.get("source", ""))
    url = tweet["url"] or f"https://x.com/{author}"
    likes = fmt_num(tweet.get("likes", 0))
    retweets = fmt_num(tweet.get("retweets", 0))
    source_html = f'<span class="chip">{source}</span>' if source else ""

    return f"""
    <article class="lead">
      <a class="lead-anchor" href="{url}" target="_blank" rel="noopener">
        <div class="lead-meta">
          <span class="lead-rank">№ 01 · 頭條</span>
          <span class="lead-rule"></span>
          <span class="lead-author">
            <span class="author-name">{name}</span>
            <span class="author-handle">@{author}</span>
          </span>
        </div>
        <h2 class="lead-summary">{summary}</h2>
        <p class="lead-text">{text}</p>
        <div class="lead-foot">
          <span class="stat"><span class="glyph">♥</span>{likes}</span>
          <span class="stat"><span class="glyph">↻</span>{retweets}</span>
          {source_html}
          <span class="lead-arrow" aria-hidden="true">↗</span>
        </div>
      </a>
    </article>
    """


def tweet_card(tweet: dict, rank: int) -> str:
    text = esc(tweet["text"])
    summary = esc(tweet.get("summary_zh", ""))
    author = tweet["author"] or "unknown"
    name = esc(tweet["name"] or author)
    source = esc(tweet.get("source", ""))
    likes = fmt_num(tweet.get("likes", 0))
    retweets = fmt_num(tweet.get("retweets", 0))
    url = tweet["url"] or f"https://x.com/{author}"

    summary_html = f'<p class="card-summary">{summary}</p>' if summary else ""
    source_html = f'<span class="chip">{source}</span>' if source else ""

    return f"""
    <article class="card">
      <a class="card-anchor" href="{url}" target="_blank" rel="noopener">
        <div class="card-rank">{rank:02d}</div>
        <div class="card-meta">
          <span class="author-name">{name}</span>
          <span class="author-handle">@{author}</span>
        </div>
        {summary_html}
        <p class="card-text">{text}</p>
        <div class="card-foot">
          <span class="stat"><span class="glyph">♥</span>{likes}</span>
          <span class="stat"><span class="glyph">↻</span>{retweets}</span>
          {source_html}
        </div>
      </a>
    </article>"""


def product_card(product: dict, rank: int) -> str:
    title = esc(product.get("title", ""))
    tagline = esc(product.get("tagline", ""))
    summary = esc(product.get("summary_zh", ""))
    url = product.get("url", "") or "https://www.producthunt.com/"
    author = esc(product.get("author", ""))

    tagline_html = f'<p class="ph-tagline">{tagline}</p>' if tagline else ""
    summary_html = f'<p class="ph-summary">{summary}</p>' if summary else ""
    author_html = f'<span class="ph-author">Hunter · {author}</span>' if author else ""

    return f"""
    <article class="ph-card">
      <a class="ph-anchor" href="{url}" target="_blank" rel="noopener">
        <div class="ph-rank">№ {rank:02d}</div>
        <h3 class="ph-title">{title}</h3>
        {tagline_html}
        {summary_html}
        <div class="ph-foot">
          <span class="chip chip-ph">Product Hunt</span>
          {author_html}
          <span class="ph-arrow" aria-hidden="true">↗</span>
        </div>
      </a>
    </article>"""


def products_section(products: list[dict]) -> str:
    if not products:
        return ""
    cards = "\n".join(product_card(p, i + 1) for i, p in enumerate(products))
    return f"""
<div class="grid-divider ph-divider"><span>Product Hunt · 今日新品 / New Launches</span></div>
<div class="ph-grid">{cards}</div>
"""


def empty_state() -> str:
    return """
    <section class="empty">
      <div class="empty-mark">№</div>
      <h2 class="empty-title">No <em>press</em> today.</h2>
      <p class="empty-sub">本日無上稿。爬蟲跑了但 X 沒人在聊有趣的設計、AI、產品。<br>明日 09:00 (UTC+8) 重新出刊。</p>
      <div class="empty-rule"></div>
      <p class="empty-foot">— Editor</p>
    </section>
    """


def criteria_block(criteria: dict) -> str:
    if not criteria:
        return ""
    kw_rows = "".join(
        f"<tr><td>{esc(k['label'])}</td><td><code>{esc(k['query'])}</code></td><td>≥ {k['min_likes']}</td></tr>"
        for k in criteria.get("keyword_pools", [])
    )
    filter_items = "".join(f"<li>{esc(r)}</li>" for r in criteria.get("claude_filter_rules", []))
    top_n = criteria.get("top_n", 10)
    since_days = criteria.get("since_days", 2)
    formula = esc(criteria.get("score_formula", "likes"))
    return f"""
<dialog id="criteria-modal" class="criteria-modal">
  <div class="criteria-modal-inner">
    <div class="criteria-modal-head">
      <h3>編輯方針 / Editorial Method</h3>
      <form method="dialog"><button class="modal-close" aria-label="關閉">✕</button></form>
    </div>
    <div class="criteria-body">
      <p>每天從下列 <strong>4 組關鍵字</strong> 查詢 X 上最近 <strong>{since_days} 天</strong>、熱門 (Top) 排序的推文，去重後交由 Claude Sonnet 4.5 做二次過濾與排序，最後輸出 <strong>Top {top_n}</strong> 並附繁體中文摘要。</p>
      <p><strong>排序公式</strong>：<code>{formula}</code></p>

      <h4>關鍵字搜尋池</h4>
      <table>
        <thead><tr><th>主題</th><th>查詢字</th><th>讚數門檻</th></tr></thead>
        <tbody>{kw_rows}</tbody>
      </table>

      <h4>Claude 過濾規則</h4>
      <ul>{filter_items}</ul>

      <p class="criteria-note">語言：English、排除 replies / retweets。摘要由 Claude Sonnet 4.5 自動生成，僅供快速瀏覽，實際內容請以原推文為準。</p>
    </div>
  </div>
</dialog>"""


def generate(data: dict) -> str:
    date_display = data["date_display"]
    top_tweets = data.get("top_tweets") or []
    total = len(top_tweets)
    issue_no = issue_number(data["date"])
    wkd = weekday_zh(data["date"])
    gen_at = data["generated_at"][:16].replace("T", " ")

    if total == 0:
        body_html = empty_state()
    elif total == 1:
        body_html = lead_card(top_tweets[0])
    else:
        rest_cards = "\n".join(tweet_card(t, i + 2) for i, t in enumerate(top_tweets[1:]))
        body_html = (
            lead_card(top_tweets[0])
            + f'\n<div class="grid-divider"><span>更多 / More from the desk</span></div>\n'
            + f'<div class="cards-grid">{rest_cards}</div>'
        )

    criteria_html = criteria_block(data.get("criteria", {}))
    top_products = data.get("top_products") or []
    products_html = products_section(top_products)
    sources = sorted({t.get("source", "") for t in top_tweets if t.get("source")})
    if top_products:
        sources = sources + ["Product Hunt"]
    sources_label = " · ".join(sources) if sources else "X / Twitter"

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="Product & Design 每日早報 — Issue №{issue_no:03d} · {date_display}" />
  <title>№{issue_no:03d} · Product & Design 早報 · {data['date']}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script>
    (function() {{
      try {{
        var t = localStorage.getItem('theme');
        if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t;
      }} catch (e) {{}}
    }})();
  </script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --paper:    #100d0a;
      --paper-2:  #181410;
      --paper-3:  #1f1a14;
      --ink:      #f2ecdf;
      --ink-2:    #cbc1ad;
      --ink-3:    #8a7f6c;
      --rule:     #2a231c;
      --rule-2:   #3a3025;
      --accent:   #ff5722;
      --accent-2: #f6b94a;
      --sage:     #87a07a;
      --grain-blend: screen;
      --grain-opacity: .035;
      --backdrop: rgba(16, 13, 10, .72);

      --serif: 'Fraunces', 'DM Serif Display', Georgia, serif;
      --sans:  'Inter', system-ui, -apple-system, 'Helvetica Neue', sans-serif;
      --mono:  'JetBrains Mono', ui-monospace, Menlo, monospace;

      --maxw: 1180px;
    }}
    [data-theme="light"] {{
      --paper:    #faf6ed;
      --paper-2:  #f1ead8;
      --paper-3:  #e7dec7;
      --ink:      #1a1612;
      --ink-2:    #403629;
      --ink-3:    #7a6e58;
      --rule:     #dcd3bd;
      --rule-2:   #c6baa0;
      --accent:   #d14412;
      --accent-2: #a56a1d;
      --grain-blend: multiply;
      --grain-opacity: .04;
      --backdrop: rgba(40, 30, 18, .45);
    }}
    html {{ color-scheme: dark; transition: background-color .2s; }}
    html[data-theme="light"] {{ color-scheme: light; }}

    html {{ font-size: 16px; -webkit-font-smoothing: antialiased; }}

    body {{
      font-family: var(--sans);
      font-feature-settings: 'ss01', 'cv11';
      background: var(--paper);
      color: var(--ink);
      min-height: 100vh;
      line-height: 1.55;
      position: relative;
      overflow-x: hidden;
    }}
    /* Subtle paper grain */
    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
      opacity: var(--grain-opacity);
      background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
      mix-blend-mode: var(--grain-blend);
    }}
    body > * {{ position: relative; z-index: 1; }}

    a {{ color: inherit; text-decoration: none; }}

    /* ─────────────── Masthead ─────────────── */
    .masthead {{
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 2.5rem 1.5rem 1.75rem;
      border-bottom: 1px solid var(--rule);
    }}
    .masthead-row {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 1rem;
    }}
    .meta-left, .meta-right {{
      font-family: var(--mono);
      font-size: .72rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: var(--ink-3);
    }}
    .meta-left {{ text-align: left; }}
    .meta-right {{ text-align: right; }}
    .masthead-center {{ text-align: center; }}
    .masthead-title {{
      font-family: var(--serif);
      font-weight: 500;
      font-size: clamp(2.4rem, 6.5vw, 4.8rem);
      line-height: 1;
      letter-spacing: -.025em;
      font-variation-settings: 'opsz' 144, 'SOFT' 30;
    }}
    .masthead-title em {{
      font-style: italic;
      color: var(--accent);
      font-variation-settings: 'opsz' 144, 'SOFT' 80, 'WONK' 1;
      padding-right: .04em;
    }}

    /* ─────────────── Body / Layout ─────────────── */
    main {{
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 2.5rem 1.5rem 5rem;
    }}

    .topbar {{
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 2rem;
      font-family: var(--mono);
      font-size: .7rem;
      letter-spacing: .1em;
      text-transform: uppercase;
      color: var(--ink-3);
    }}
    .topbar .sep {{
      flex: 1;
      height: 1px;
      background: var(--rule);
    }}
    .topbar a,
    .topbar .topbar-link {{
      color: var(--accent);
      transition: color .15s;
    }}
    .topbar a:hover,
    .topbar .topbar-link:hover {{ color: var(--accent-2); }}
    .topbar .topbar-link {{
      background: none;
      border: none;
      padding: 0;
      font: inherit;
      letter-spacing: inherit;
      text-transform: inherit;
      cursor: pointer;
    }}
    .theme-toggle {{
      background: none;
      border: 1px solid var(--rule-2);
      color: var(--ink-3);
      width: 28px;
      height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      border-radius: 2px;
      font-size: .9rem;
      line-height: 1;
      transition: color .15s, border-color .15s, background .15s;
    }}
    .theme-toggle:hover {{
      color: var(--accent);
      border-color: var(--accent);
    }}

    /* ─────────────── Criteria Modal ─────────────── */
    .criteria-modal {{
      padding: 0;
      border: 1px solid var(--rule-2);
      background: var(--paper-2);
      color: var(--ink-2);
      width: min(640px, calc(100vw - 3rem));
      max-height: calc(100vh - 4rem);
      border-radius: 2px;
      box-shadow: 0 30px 60px -20px rgba(0,0,0,.6);
    }}
    .criteria-modal::backdrop {{
      background: var(--backdrop);
      backdrop-filter: blur(3px);
    }}
    .criteria-modal[open] {{
      animation: modal-in .2s ease;
    }}
    @keyframes modal-in {{
      from {{ opacity: 0; transform: translateY(8px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .criteria-modal-inner {{
      padding: 1.75rem 1.9rem 1.9rem;
      max-height: calc(100vh - 4rem);
      overflow-y: auto;
    }}
    .criteria-modal-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1.25rem;
      padding-bottom: .9rem;
      border-bottom: 1px solid var(--rule);
    }}
    .criteria-modal-head h3 {{
      font-family: var(--mono);
      font-size: .72rem;
      letter-spacing: .15em;
      text-transform: uppercase;
      color: var(--ink);
      font-weight: 500;
    }}
    .modal-close {{
      background: none;
      border: none;
      color: var(--ink-3);
      font-size: 1rem;
      cursor: pointer;
      padding: 0;
      line-height: 1;
      transition: color .15s;
    }}
    .modal-close:hover {{ color: var(--accent); }}
    .criteria-body {{
      font-size: .85rem;
      line-height: 1.7;
      color: var(--ink-2);
    }}
    .criteria-body p {{ margin-bottom: .9rem; }}
    .criteria-body strong {{ color: var(--ink); font-weight: 500; }}
    .criteria-body ul {{ padding-left: 1.2rem; margin-bottom: .9rem; }}
    .criteria-body li {{ margin-bottom: .35rem; }}
    .criteria-body h4 {{
      font-family: var(--serif);
      font-style: italic;
      font-size: 1.05rem;
      margin: 1.4rem 0 .5rem;
      color: var(--ink);
      font-weight: 500;
    }}
    .criteria-body table {{
      width: 100%;
      border-collapse: collapse;
      font-size: .8rem;
      margin-bottom: .75rem;
    }}
    .criteria-body th, .criteria-body td {{
      text-align: left;
      padding: .5rem .65rem;
      border-bottom: 1px solid var(--rule);
      vertical-align: top;
    }}
    .criteria-body th {{
      color: var(--ink-3);
      font-weight: 500;
      font-size: .68rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      font-family: var(--mono);
    }}
    .criteria-body code {{
      background: rgba(255, 87, 34, 0.1);
      color: var(--accent);
      padding: 1px 7px;
      border-radius: 2px;
      font-family: var(--mono);
      font-size: .76rem;
    }}
    .criteria-note {{
      font-size: .76rem;
      color: var(--ink-3);
      margin-top: 1rem;
      padding-top: .75rem;
      border-top: 1px dashed var(--rule);
      font-style: italic;
    }}

    /* ─────────────── Lead / Hero Card ─────────────── */
    .lead {{
      margin-bottom: 3rem;
      border-top: 2px solid var(--ink);
      border-bottom: 1px solid var(--rule);
      padding: 2rem 0 2.25rem;
      position: relative;
    }}
    .lead::before {{
      content: '';
      position: absolute;
      top: -2px; left: 0;
      width: 80px; height: 4px;
      background: var(--accent);
    }}
    .lead-anchor {{
      display: block;
      cursor: pointer;
      transition: opacity .15s;
    }}
    .lead-anchor:hover {{ opacity: .92; }}
    .lead-anchor:hover .lead-arrow {{ transform: translate(3px, -3px); color: var(--accent); }}

    .lead-meta {{
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.25rem;
      font-family: var(--mono);
      font-size: .72rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: var(--ink-3);
    }}
    .lead-rank {{
      color: var(--accent);
      font-weight: 500;
    }}
    .lead-rule {{
      flex: 1;
      height: 1px;
      background: var(--rule);
    }}
    .lead-author {{
      display: flex;
      gap: .5rem;
      align-items: baseline;
      text-transform: none;
      letter-spacing: 0;
      font-family: var(--sans);
      font-size: .82rem;
    }}
    .lead-author .author-name {{ color: var(--ink); font-weight: 500; }}
    .lead-author .author-handle {{ color: var(--ink-3); }}

    .lead-summary {{
      font-family: var(--serif);
      font-weight: 400;
      font-size: clamp(1.7rem, 3.4vw, 2.6rem);
      line-height: 1.18;
      letter-spacing: -.01em;
      color: var(--ink);
      margin-bottom: 1rem;
      font-variation-settings: 'opsz' 96, 'SOFT' 30;
    }}
    .lead-text {{
      font-size: 1rem;
      line-height: 1.7;
      color: var(--ink-2);
      max-width: 70ch;
      margin-bottom: 1.5rem;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .lead-foot {{
      display: flex;
      align-items: center;
      gap: 1.25rem;
      font-size: .8rem;
      color: var(--ink-3);
      flex-wrap: wrap;
    }}
    .lead-arrow {{
      margin-left: auto;
      font-size: 1.2rem;
      color: var(--ink-3);
      transition: transform .2s ease, color .2s;
      display: inline-block;
    }}

    /* ─────────────── Section divider ─────────────── */
    .grid-divider {{
      display: flex;
      align-items: center;
      gap: 1rem;
      margin: 0 0 1.5rem;
      font-family: var(--mono);
      font-size: .7rem;
      letter-spacing: .15em;
      text-transform: uppercase;
      color: var(--ink-3);
    }}
    .grid-divider::before,
    .grid-divider::after {{
      content: '';
      flex: 1;
      height: 1px;
      background: var(--rule);
    }}

    /* ─────────────── Cards Grid ─────────────── */
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 0;
      border-top: 1px solid var(--rule);
      border-left: 1px solid var(--rule);
    }}

    .card {{
      border-right: 1px solid var(--rule);
      border-bottom: 1px solid var(--rule);
      background: transparent;
      transition: background .15s;
    }}
    .card:hover {{ background: var(--paper-2); }}
    .card-anchor {{
      display: flex;
      flex-direction: column;
      gap: .65rem;
      padding: 1.25rem 1.4rem 1.4rem;
      height: 100%;
      cursor: pointer;
      position: relative;
    }}
    .card-anchor::after {{
      content: '↗';
      position: absolute;
      top: 1.1rem;
      right: 1.2rem;
      color: var(--ink-3);
      font-size: .95rem;
      transition: transform .2s, color .2s;
    }}
    .card:hover .card-anchor::after {{
      transform: translate(2px, -2px);
      color: var(--accent);
    }}

    .card-rank {{
      font-family: var(--mono);
      font-size: .68rem;
      letter-spacing: .15em;
      color: var(--accent);
      margin-bottom: .15rem;
    }}
    .card-meta {{
      display: flex;
      flex-direction: column;
      gap: .1rem;
      margin-bottom: .25rem;
    }}
    .author-name {{
      font-size: .85rem;
      font-weight: 500;
      color: var(--ink);
    }}
    .author-handle {{
      font-size: .72rem;
      color: var(--ink-3);
      font-family: var(--mono);
    }}

    .card-summary {{
      font-family: var(--serif);
      font-weight: 400;
      font-size: 1.1rem;
      line-height: 1.35;
      color: var(--ink);
      letter-spacing: -.005em;
      font-variation-settings: 'opsz' 36, 'SOFT' 30;
    }}

    .card-text {{
      font-size: .82rem;
      line-height: 1.65;
      color: var(--ink-2);
      flex: 1;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .card-foot {{
      display: flex;
      gap: 1rem;
      align-items: center;
      font-size: .72rem;
      color: var(--ink-3);
      padding-top: .65rem;
      border-top: 1px dashed var(--rule);
      flex-wrap: wrap;
    }}

    .stat {{
      display: inline-flex;
      align-items: center;
      gap: .3rem;
      font-family: var(--mono);
    }}
    .glyph {{
      color: var(--accent);
      font-size: .8rem;
    }}
    .chip {{
      margin-left: auto;
      font-family: var(--mono);
      font-size: .65rem;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--ink-2);
      background: rgba(255, 87, 34, 0.08);
      border: 1px solid rgba(255, 87, 34, 0.18);
      padding: 2px 8px;
      border-radius: 999px;
    }}

    /* ─────────────── Product Hunt Section ─────────────── */
    .ph-divider {{
      margin-top: 3rem;
    }}
    .ph-divider span {{
      color: var(--accent);
    }}
    .ph-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 0;
      border-top: 1px solid var(--rule);
      border-left: 1px solid var(--rule);
      margin-bottom: 3rem;
    }}
    .ph-card {{
      border-right: 1px solid var(--rule);
      border-bottom: 1px solid var(--rule);
      transition: background .15s;
    }}
    .ph-card:hover {{ background: var(--paper-2); }}
    .ph-anchor {{
      display: flex;
      flex-direction: column;
      gap: .55rem;
      padding: 1.25rem 1.4rem 1.4rem;
      height: 100%;
      cursor: pointer;
      position: relative;
    }}
    .ph-rank {{
      font-family: var(--mono);
      font-size: .68rem;
      letter-spacing: .15em;
      color: var(--accent);
      text-transform: uppercase;
    }}
    .ph-title {{
      font-family: var(--serif);
      font-weight: 500;
      font-size: 1.35rem;
      line-height: 1.2;
      letter-spacing: -.01em;
      color: var(--ink);
      font-variation-settings: 'opsz' 72, 'SOFT' 30;
    }}
    .ph-tagline {{
      font-family: var(--sans);
      font-size: .82rem;
      line-height: 1.55;
      color: var(--ink-2);
      font-style: italic;
    }}
    .ph-summary {{
      font-size: .88rem;
      line-height: 1.65;
      color: var(--ink);
      flex: 1;
    }}
    .ph-foot {{
      display: flex;
      gap: .75rem;
      align-items: center;
      font-size: .7rem;
      color: var(--ink-3);
      padding-top: .65rem;
      border-top: 1px dashed var(--rule);
      flex-wrap: wrap;
    }}
    .ph-author {{
      font-family: var(--mono);
      letter-spacing: .04em;
    }}
    .chip-ph {{
      margin-left: 0;
      background: rgba(246, 185, 74, 0.1);
      border-color: rgba(246, 185, 74, 0.25);
      color: var(--accent-2);
    }}
    .ph-arrow {{
      margin-left: auto;
      font-size: 1rem;
      color: var(--ink-3);
      transition: transform .2s, color .2s;
    }}
    .ph-card:hover .ph-arrow {{
      transform: translate(2px, -2px);
      color: var(--accent);
    }}

    /* ─────────────── Empty state ─────────────── */
    .empty {{
      text-align: center;
      padding: 5rem 1rem 4rem;
      border-top: 2px solid var(--ink);
      border-bottom: 1px solid var(--rule);
      position: relative;
    }}
    .empty::before {{
      content: '';
      position: absolute;
      top: -2px; left: 50%;
      transform: translateX(-50%);
      width: 80px; height: 4px;
      background: var(--accent);
    }}
    .empty-mark {{
      font-family: var(--serif);
      font-style: italic;
      font-size: 4rem;
      color: var(--accent);
      line-height: 1;
      margin-bottom: 1rem;
      font-variation-settings: 'opsz' 144, 'SOFT' 100, 'WONK' 1;
    }}
    .empty-title {{
      font-family: var(--serif);
      font-weight: 400;
      font-size: clamp(2rem, 5vw, 3.4rem);
      line-height: 1.1;
      color: var(--ink);
      margin-bottom: 1rem;
      font-variation-settings: 'opsz' 144, 'SOFT' 30;
    }}
    .empty-title em {{
      font-style: italic;
      color: var(--accent);
      font-variation-settings: 'opsz' 144, 'SOFT' 100, 'WONK' 1;
    }}
    .empty-sub {{
      color: var(--ink-2);
      font-size: .92rem;
      line-height: 1.7;
      max-width: 480px;
      margin: 0 auto 1.75rem;
    }}
    .empty-rule {{
      width: 30px;
      height: 1px;
      background: var(--rule-2);
      margin: 0 auto 1rem;
    }}
    .empty-foot {{
      font-family: var(--serif);
      font-style: italic;
      color: var(--ink-3);
      font-size: .9rem;
    }}

    /* ─────────────── Footer ─────────────── */
    footer {{
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 3rem 1.5rem 4rem;
      border-top: 1px solid var(--rule);
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 1.5rem;
      align-items: end;
      font-size: .74rem;
      color: var(--ink-3);
    }}
    .colophon-left {{ text-align: left; }}
    .colophon-center {{
      text-align: center;
      font-family: var(--serif);
      font-style: italic;
      color: var(--ink-2);
      font-size: .9rem;
    }}
    .colophon-center em {{
      color: var(--accent);
      font-style: italic;
    }}
    .colophon-right {{
      text-align: right;
      font-family: var(--mono);
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .colophon-right a {{ color: var(--ink-2); border-bottom: 1px solid var(--rule-2); }}
    .colophon-right a:hover {{ color: var(--accent); border-color: var(--accent); }}

    /* ─────────────── Responsive ─────────────── */
    @media (max-width: 720px) {{
      .masthead-row {{
        grid-template-columns: 1fr;
        text-align: center;
      }}
      .meta-left, .meta-right {{ text-align: center; }}
      .lead-meta {{ flex-wrap: wrap; gap: .5rem; }}
      .lead-author {{ width: 100%; }}
      .cards-grid {{ grid-template-columns: 1fr; }}
      footer {{
        grid-template-columns: 1fr;
        text-align: center;
      }}
      .colophon-left, .colophon-right {{ text-align: center; }}
    }}
  </style>
</head>
<body>

<header class="masthead">
  <div class="masthead-row">
    <div class="meta-left">№{issue_no:03d}</div>
    <div class="masthead-center">
      <h1 class="masthead-title">Product &amp; <em>Design</em></h1>
    </div>
    <div class="meta-right">{data['date']} · {total:02d} 篇</div>
  </div>
</header>

<main>
  <div class="topbar">
    <span>Today's Brief</span>
    <span class="sep"></span>
    {'<button type="button" class="topbar-link" onclick="document.getElementById(&quot;criteria-modal&quot;).showModal()">編輯方針</button>' if criteria_html else ''}
    <a href="archive.html">歷史存檔 / Archive →</a>
    <button type="button" class="theme-toggle" aria-label="切換主題" onclick="toggleTheme()"><span class="theme-icon">☾</span></button>
  </div>

  {body_html}

  {products_html}
</main>

{criteria_html}
<script>
  (function() {{
    document.querySelectorAll('dialog').forEach(function(d) {{
      d.addEventListener('click', function(e) {{ if (e.target === d) d.close(); }});
    }});
    var icon = document.querySelector('.theme-icon');
    if (icon) icon.textContent = document.documentElement.dataset.theme === 'light' ? '☀' : '☾';
  }})();
  function toggleTheme() {{
    var cur = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
    var next = cur === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = next;
    try {{ localStorage.setItem('theme', next); }} catch (e) {{}}
    document.querySelectorAll('.theme-icon').forEach(function(el) {{
      el.textContent = next === 'light' ? '☀' : '☾';
    }});
  }}
</script>

<footer>
  <div class="colophon-left">
    Set in <strong>Fraunces</strong>, <strong>Inter</strong>, <strong>JetBrains Mono</strong>.<br>
    Filtered &amp; summarised by Claude Sonnet 4.5.
  </div>
  <div class="colophon-center">
    Daily at <em>09:00</em> UTC+8 · Made with care.
  </div>
  <div class="colophon-right">
    Source: {sources_label}<br>
    Updated {gen_at}
  </div>
</footer>

</body>
</html>"""


def main():
    data = load_data()
    html = generate(data)

    Path("index.html").write_text(html, encoding="utf-8")
    print(f"OK index.html generated for {data['date']}")

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
    print(f"OK archive.json updated ({len(archive)} entries)")


if __name__ == "__main__":
    main()
