#!/usr/bin/env python3
"""
generate_html.py
Reads data.json and renders an editorial-magazine-styled static HTML morning brief.
"""

import json
from pathlib import Path
from datetime import datetime

from styles import STYLES
from scripts import ARCHIVE_RAIL_SCRIPT, INTERACTIVE_SCRIPT, THEME_BOOTSTRAP_SCRIPT
from templates import (
    archive_rail_html,
    criteria_block,
    empty_state,
    lead_card,
    products_section,
    tweet_card,
)

WEEKDAY_ZH = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def load_data() -> dict:
    with open("data.json", encoding="utf-8") as f:
        return json.load(f)


def load_archive() -> list:
    p = Path("archive.json")
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def issue_number(date_str: str, archive=None) -> int:
    """Issue number = rank of date in chronological publication order.

    If an archive list is supplied, use it as the source of truth for past dates,
    and ensure ``date_str`` itself is counted (even if not yet persisted).
    Without archive, falls back to 1.
    """
    dates = set()
    if archive:
        dates.update(e["date"] for e in archive if e.get("date"))
    dates.add(date_str)
    ordered = sorted(dates)
    try:
        return ordered.index(date_str) + 1
    except ValueError:
        return 1


def weekday_zh(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return WEEKDAY_ZH[d.weekday()]
    except Exception:
        return ""


def generate(data: dict, archive=None, base_path: str = "") -> str:
    date_display = data["date_display"]
    top_tweets = data.get("top_tweets") or []
    total = len(top_tweets)
    issue_no = issue_number(data["date"], archive or [])
    wkd = weekday_zh(data["date"])
    gen_at = data["generated_at"][:16].replace("T", " ")
    rail_html = archive_rail_html(data["date"], base_path)

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
{THEME_BOOTSTRAP_SCRIPT}
{STYLES}</head>
<body>
<div class="page-shell">
  {rail_html}
  <div class="page-main">
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
    <button type="button" class="theme-toggle" aria-label="切換主題" onclick="toggleTheme()"><span class="theme-icon">☾</span></button>
  </div>

  {body_html}

  {products_html}
</main>

{criteria_html}
{INTERACTIVE_SCRIPT}

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
  </div>
</div>
{ARCHIVE_RAIL_SCRIPT}
</body>
</html>"""


def main():
    data = load_data()
    archive = load_archive()

    Path("index.html").write_text(generate(data, archive), encoding="utf-8")
    print(f"OK index.html generated for {data['date']}")

    briefs_dir = Path("briefs")
    briefs_dir.mkdir(exist_ok=True)
    brief_path = briefs_dir / f"{data['date']}.html"
    brief_path.write_text(generate(data, archive, base_path="../"), encoding="utf-8")
    print(f"OK {brief_path} generated")

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
    headline = ""
    if top:
        headline = top[0].get("summary_zh") or top[0].get("text") or ""
    entry = {
        "date": data["date"],
        "date_display": data["date_display"],
        "generated_at": data["generated_at"],
        "total": len(top),
        "sources": sources,
        "headline": headline,
    }

    # Replace or prepend
    archive = [e for e in archive if e["date"] != data["date"]]
    archive.insert(0, entry)
    archive = archive[:90]  # keep last 90 days

    archive_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK archive.json updated ({len(archive)} entries)")


if __name__ == "__main__":
    main()
