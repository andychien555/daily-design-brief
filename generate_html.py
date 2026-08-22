#!/usr/bin/env python3
"""
generate_html.py
Reads data.json and renders an editorial-magazine-styled static HTML morning brief.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import config
from utils import load_json, save_json
from styles import stylesheet_link, write_stylesheet
from scripts import ARCHIVE_RAIL_SCRIPT, INTERACTIVE_SCRIPT, THEME_BOOTSTRAP_SCRIPT
from templates import (
    archive_rail_html,
    criteria_block,
    empty_state,
    lead_card,
    lead_story,
    newsletter_card,
    products_section,
    tweet_card,
    briefing_section,
)

WEEKDAY_ZH = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# The site's path on its host: "/daily-design-brief/" on a project page, "/" once
# a CNAME moves it to an apex domain. Only 404.html needs it — see generate_404.
SITE_PATH = (urlparse(config.SITE_URL).path or "").rstrip("/") + "/"


def load_data() -> dict:
    with open(config.DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_archive() -> list:
    return load_json(config.ARCHIVE_FILE, default=[])


def published_dates(archive=None) -> set:
    """Every date ever published.

    ``briefs/*.html`` is the source of truth: archive.json only keeps the most
    recent 90 days, so counting it alone caps the issue number once the archive
    fills up. The archive is still folded in so a date whose snapshot is missing
    still counts.
    """
    dates = {p.stem for p in Path(config.BRIEFS_DIR).glob("*.html")}
    if archive:
        dates.update(e["date"] for e in archive if e.get("date"))
    return dates


def issue_number(date_str: str, archive=None) -> int:
    """Issue number = rank of date in chronological publication order.

    ``date_str`` is always counted, even if its snapshot is not yet written.
    """
    dates = published_dates(archive)
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


def date_display_of(date_str: str) -> str:
    """`2026-08-09` → `2026 年 08 月 09 日`.

    Same formatting the fetchers stamp into data.json; recomputed here so the shell
    can be rebuilt for an archived page whose source data is long gone.
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return f"{d.year} 年 {d.month:02d} 月 {d.day:02d} 日"
    except Exception:
        return date_str


def date_dotted(date_str: str) -> str:
    """`2026-08-09` → `2026.08.09`, the masthead's mono form."""
    return date_str.replace("-", ".")


# ── Shell blocks ───────────────────────────────────────────────────
# These four are the parts of the page that belong to the publication rather than
# to the day: identical markup on every issue, and therefore the parts
# refresh_briefs_shell.py has to be able to rebuild inside an archived page. They
# live here, and are imported there, so the markup exists in exactly one place.


def head_block(issue_no: int, date: str, base_path: str = "") -> str:
    """Everything between <meta name="description"> and the closing font <link>.

    refresh_briefs_shell.py anchors on those two ends, so keep them as the first
    and last lines of what this returns.
    """
    display = date_display_of(date)
    title = f"{config.BRAND_NAME_ZH} {config.BRAND_NAME_LATIN} · {date}"
    desc = (
        f"{config.BRAND_NAME_ZH} {config.BRAND_NAME_LATIN} — 財經 · Product · Design "
        f"每日早報 — № {issue_no:03d} · {display}"
    )
    page_url = f"{config.SITE_URL}/" if not base_path else f"{config.SITE_URL}/briefs/{date}.html"
    return f"""  <meta name="description" content="{desc}" />
  <title>{title}</title>
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="{config.BRAND_NAME_ZH} {config.BRAND_NAME_LATIN}" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:image" content="{config.SITE_URL}/assets/og.webp" />
  <meta property="og:url" content="{page_url}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="theme-color" content="#faf6ed" media="(prefers-color-scheme: light)" />
  <meta name="theme-color" content="#14181e" media="(prefers-color-scheme: dark)" />
  <link rel="icon" type="image/svg+xml" href="{base_path}favicon.svg" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">"""


TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)
# A newsletter card reuses the podcast card's class and adds nl-item, so the exact
# attribute value is what separates 財經 from 好文 — the same distinction, and the
# same ordering trap, that build_search_index.py documents.
CLASS_COUNT = {
    "財經": r'class="yt-brief"',
    "好文": r'class="yt-brief nl-item"',
    "推文": r'class="(?:lead|card)"',
    "PRODUCT": r'class="ph-card"',
}


def read_minutes(text: str) -> float:
    """CJK at ~320 chars/min, latin at ~220 words/min. Deliberately unrounded.

    Rounding each item up first would inflate a nine-tweet issue by six minutes,
    and this number is the promise 「讀得完」 stated as a fact on the page. It has
    to be able to embarrass us.
    """
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    words = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk / 320 + words / 220


def issue_stats(main_html: str) -> dict:
    """Section counts and read time, derived from rendered markup.

    Deliberately not from data.json: refresh_briefs_shell.py has to produce the
    same numbers for an archived issue whose source data is long gone, and one
    function reading one source is the only way those two paths cannot drift.
    Safe to key off class names — build_search_index.py already depends on them.
    """
    counts = {k: len(re.findall(p, main_html)) for k, p in CLASS_COUNT.items()}
    text = TAG_RE.sub(" ", SCRIPT_RE.sub(" ", main_html))
    return {"counts": counts, "minutes": max(1, round(read_minutes(text)))}


def masthead_block(
    issue_no: int, date: str, stats: dict, base_path: str = "", meta: bool = True
) -> str:
    """The broadsheet nameplate: engraving full bleed, then a solid ink plate.

    Reversed type sits on a printed block rather than floating over the painting —
    the engraving's sky is bone white, so white type laid directly on it would
    disappear, and a scrim would mean a gradient. The plate is the letterpress
    answer: flat, square, and legible over any part of the image.

    The ears under it are the front page's own table of contents. They are derived
    rather than passed in so that an archived issue reports the same numbers.

    `meta=False` drops the issue line for pages that are not an issue: printing
    「№ 115 · 00 篇」 above a 404 would state something untrue about the archive.
    """
    plate_meta = (
        f"""
      <span class="bs-issue">№ {issue_no:03d}</span>
      <span>{date_dotted(date)}</span>"""
        if meta
        else ""
    )
    ears = ""
    if meta and stats:
        cells = "".join(
            f"<span>{k} <b>{n}</b></span>"
            for k, n in stats["counts"].items()
            if n
        )
        ears = f"""
  <div class="bs-ears">{cells}<span class="bs-ears-rule"></span><span>約 {stats['minutes']} 分鐘</span></div>"""

    return f"""<header class="bs-head">
  <img class="bs-art" src="{base_path}assets/masthead-engraving.webp"
       width="836" height="209" alt="" aria-hidden="true" decoding="async" />
  <div class="bs-plate">
    <h1 class="bs-name">{config.BRAND_NAME_ZH}</h1>
    <div class="bs-plate-meta">
      <span>{config.BRAND_NAME_LATIN}</span>{plate_meta}
    </div>
  </div>{ears}
</header>"""


def endmark_block() -> str:
    """The promise under the masthead is 「讀得完」; this is where it is kept."""
    return """<div class="endmark">
  <span class="endmark-glyph" aria-hidden="true"></span>
  <span class="endmark-label">本期完</span>
</div>"""


COLOPHON_LEFT = """    Set in <strong>思源宋體</strong>, <strong>Inter</strong>, <strong>Noto Sans TC</strong>, <strong>JetBrains Mono</strong>.<br>
    Filtered &amp; summarised by Claude Sonnet 4.5."""

COLOPHON_CENTER = f"""    Daily at <em>{config.PUBLISH_HOUR}</em> UTC+8."""


def generate(data: dict, archive=None, base_path: str = "") -> str:
    top_tweets = data.get("top_tweets") or []
    total = len(top_tweets)
    issue_no = issue_number(data["date"], archive or [])
    gen_at = data["generated_at"][:16].replace("T", " ")
    rail_html = archive_rail_html(data["date"], base_path)

    criteria_html = criteria_block(data.get("criteria", {}))
    podcast_briefs = data.get("podcast_briefs")
    if not podcast_briefs:
        legacy = data.get("podcast_brief") or data.get("youtube_brief")
        podcast_briefs = [legacy] if legacy else []
    article_briefs = list(data.get("article_briefs") or [])

    # The lead is the main course: finance first, an article only when there is no
    # podcast yet, and nothing at all when the day carries neither — in which case
    # the tweet lead card is already the top of the page and promoting it twice
    # would print the same story in two sizes.
    lead_html = ""
    if podcast_briefs:
        lead = podcast_briefs[0]
        podcast_briefs = podcast_briefs[1:]
        lead_html = lead_story(lead, "財經", lead.get("channel", ""))
    elif article_briefs:
        lead = article_briefs.pop(0)
        lead_html = lead_story(lead, lead.get("label", "好文"), lead.get("source", ""))

    podcast_html = "\n".join(briefing_section(b) for b in podcast_briefs)

    # 好文 and 推文 share one grid — the desk, below the lead story. 好文 takes a
    # full row each (styles.py: .cards-grid > .nl-item), 推文 pairs up beneath
    # them; the ordering here is what puts every article above every tweet. The
    # tweet lead stays outside the grid entirely — it is the deck, not a cell.
    # Front page reads lead → deck → 好文 → columns.
    desk_cards = [newsletter_card(b) for b in article_briefs]
    desk_cards += [tweet_card(t, i + 2) for i, t in enumerate(top_tweets[1:])]
    desk_html = ""
    if desk_cards or top_tweets:
        desk_html = (
            '<div class="grid-divider"><span>好文 · 推文 / THE REST OF THE DESK</span></div>\n'
        )
        if top_tweets:
            desk_html += lead_card(top_tweets[0])
        if desk_cards:
            desk_html += f'<div class="cards-grid">{"".join(desk_cards)}</div>'
    if not top_tweets:
        desk_html += empty_state()

    top_products = data.get("top_products") or []
    products_html = products_section(top_products)
    sources = sorted({t.get("source", "") for t in top_tweets if t.get("source")})
    if top_products:
        sources = sources + ["Product Hunt"]
    sources_label = " · ".join(sources) if sources else "X / Twitter"

    main_html = f"""<main>
  <div class="topbar">
    <button type="button" class="rail-drawer-toggle" aria-label="開啟存檔" aria-controls="rail-list" aria-expanded="false"><span aria-hidden="true">☰</span></button>
    <span>Today's Brief</span>
    <span class="sep"></span>
    {'<button type="button" class="topbar-link" onclick="document.getElementById(&quot;criteria-modal&quot;).showModal()">編輯方針</button>' if criteria_html else ''}
    <button type="button" class="theme-toggle" aria-label="切換主題" onclick="toggleTheme()"><span class="theme-icon">☀</span></button>
  </div>
{lead_html}
  {podcast_html}

  {desk_html}

  {products_html}
</main>"""

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
{head_block(issue_no, data['date'], base_path)}
{THEME_BOOTSTRAP_SCRIPT}
{stylesheet_link(base_path)}</head>
<body>
<div class="page-shell">
  {rail_html}
  <div class="page-main">
{masthead_block(issue_no, data['date'], issue_stats(main_html), base_path)}

{main_html}

{endmark_block()}

{criteria_html}
{INTERACTIVE_SCRIPT}

<footer>
  <div class="colophon-left">
{COLOPHON_LEFT}
  </div>
  <div class="colophon-center">
{COLOPHON_CENTER}
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


def generate_404(archive=None) -> str:
    """GitHub Pages serves /404.html for any unresolved path under the project.

    It serves this body while leaving the requested URL in the address bar, so a
    miss on /briefs/2020-01-01.html resolves every relative href against
    /briefs/ — the stylesheet, the engraving, the artwork and the way back all
    404 in turn. <base> pins them to the site root instead. Every other page
    knows its own depth and passes base_path; this one cannot.

    Kept deliberately quiet: one flat sentence and a way back. No apology, no
    search box, no "you might like" — the same refusal the empty state makes.
    """
    latest = max(published_dates(archive or []), default="")
    issue_no = issue_number(latest, archive or []) if latest else 1
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <base href="{SITE_PATH}" />
{head_block(issue_no, latest or "", "")}
{THEME_BOOTSTRAP_SCRIPT}
{stylesheet_link()}</head>
<body>
{masthead_block(issue_no, latest or "", {}, "", meta=False)}

<main>
  <section class="notfound">
    <img class="notfound-art" src="assets/notfound.webp" width="512" height="768"
         alt="" aria-hidden="true" decoding="async" />
    <p class="notfound-title">這一頁不存在。</p>
    <p class="notfound-sub">可能是網址打錯了，或這一期從來沒有出刊。</p>
    <a class="notfound-back" href="./">回到今天的早報</a>
  </section>
</main>

{endmark_block()}
{INTERACTIVE_SCRIPT}
</body>
</html>"""


def main():
    data = load_data()
    archive = load_archive()

    # Before any page, so the <link> the templates emit always has a file to
    # point at. No-op when the CSS is unchanged.
    if write_stylesheet():
        print("OK styles.css written")

    Path("index.html").write_text(generate(data, archive), encoding="utf-8")
    print(f"OK index.html generated for {data['date']}")

    briefs_dir = Path(config.BRIEFS_DIR)
    briefs_dir.mkdir(exist_ok=True)
    brief_path = briefs_dir / f"{data['date']}.html"
    brief_path.write_text(generate(data, archive, base_path="../"), encoding="utf-8")
    print(f"OK {brief_path} generated")

    Path("404.html").write_text(generate_404(archive), encoding="utf-8")
    print("OK 404.html generated")

    # Also append to archive.json for history page
    archive = load_json(config.ARCHIVE_FILE, default=[])

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

    # Stamp the issue number so the sidebar rail can label a trimmed archive the
    # same way each page's own masthead does.
    rank = {d: i + 1 for i, d in enumerate(sorted(published_dates(archive)))}
    for e in archive:
        e["no"] = rank.get(e["date"], 1)

    save_json(config.ARCHIVE_FILE, archive)
    print(f"OK archive.json updated ({len(archive)} entries)")


if __name__ == "__main__":
    main()
