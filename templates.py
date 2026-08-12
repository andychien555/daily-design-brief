"""HTML-rendering helpers for generate_html.py.

Pure string builders — no I/O, no data loading. Each function takes a
plain dict and returns the matching HTML fragment.
"""

import re

import config


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_num(n: int) -> str:
    if n >= 10000:
        return f"{n/1000:.0f}k"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def archive_rail_html(active_date: str, base_path: str = "") -> str:
    """Sidebar shell; items populated client-side from archive.json so every
    page (index + historical briefs) stays in sync with the latest archive."""
    return f"""
    <aside class="archive-rail" aria-label="歷史存檔"
           data-active="{esc(active_date)}" data-base="{esc(base_path)}">
      <div class="rail-heading">
        <span class="rail-heading-label">Archive</span>
        <button type="button" class="rail-toggle" aria-label="收合側欄" aria-controls="rail-list" aria-expanded="true">
          <span class="rail-toggle-icon" aria-hidden="true">‹</span>
          <span class="rail-close-icon" aria-hidden="true">✕</span>
        </button>
      </div>
      <div class="rail-search">
        <span class="rail-search-icon" aria-hidden="true">⌕</span>
        <input type="search" class="rail-search-input" placeholder="搜尋關鍵字"
               aria-label="搜尋歷史早報" autocomplete="off" spellcheck="false">
        <button type="button" class="rail-search-clear" aria-label="清除搜尋" hidden>✕</button>
      </div>
      <div class="rail-search-status" role="status" hidden></div>
      <nav id="rail-list" class="rail-list"><div class="rail-loading">載入中…</div></nav>
    </aside>
    <div class="rail-backdrop" aria-hidden="true"></div>"""


def context_html(tweet: dict) -> str:
    """Render quoted/replied-to tweet and top replies if present."""
    ctx = tweet.get("context") or {}
    parts = []
    if ctx.get("quoted_text"):
        qa = esc(ctx.get("quoted_author", ""))
        qt = esc(ctx["quoted_text"])
        label = f"引用 @{qa}" if qa else "引用原文"
        parts.append(f'<div class="ctx-quote"><span class="ctx-label">{label}</span><p>{qt}</p></div>')
    if ctx.get("replied_text"):
        ra = esc(ctx.get("replied_author", ""))
        rt = esc(ctx["replied_text"])
        label = f"回覆 @{ra}" if ra else "回覆原文"
        parts.append(f'<div class="ctx-quote ctx-reply"><span class="ctx-label">{label}</span><p>{rt}</p></div>')
    top_replies = ctx.get("top_replies") or []
    if top_replies:
        items = "".join(
            f'<li><span class="ctx-rep-author">@{esc(r.get("author",""))}</span><span class="ctx-rep-likes">♥ {fmt_num(r.get("likes", 0))}</span><p>{esc(r.get("text",""))}</p></li>'
            for r in top_replies[:3]
        )
        parts.append(
            f'<details class="ctx-replies"><summary>💬 熱門回覆 ({len(top_replies)})</summary><ul>{items}</ul></details>'
        )
    return "\n".join(parts)


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

    ctx = context_html(tweet)
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
        {ctx}
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

    ctx = context_html(tweet)
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
        {ctx}
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
    image_url = esc(product.get("image_url", ""))
    hero_url = esc(product.get("hero_url", ""))

    tagline_html = f'<p class="ph-tagline">{tagline}</p>' if tagline else ""
    summary_html = f'<p class="ph-summary">{summary}</p>' if summary else ""
    author_html = f'<span class="ph-author">Hunter · {author}</span>' if author else ""
    icon_html = (
        f'<img class="ph-thumb" src="{image_url}" alt="" loading="lazy" decoding="async" width="48" height="48">'
        if image_url else ""
    )
    hero_html = (
        f'<div class="ph-hero"><img src="{hero_url}" alt="" loading="lazy" decoding="async"></div>'
        if hero_url else '<div class="ph-hero ph-hero-empty"></div>'
    )

    return f"""
    <article class="ph-card">
      <a class="ph-anchor" href="{url}" target="_blank" rel="noopener">
        {hero_html}
        <div class="ph-body">
          <div class="ph-head">
            {icon_html}
            <div class="ph-head-text">
              <div class="ph-rank">№ {rank:02d}</div>
              <h3 class="ph-title">{title}</h3>
            </div>
          </div>
          {tagline_html}
          {summary_html}
          <div class="ph-foot">
            <span class="chip chip-ph">Product Hunt</span>
            {author_html}
            <span class="ph-arrow" aria-hidden="true">↗</span>
          </div>
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


def _md_inline(text: str) -> str:
    """行內 markdown：先跳脫 HTML，再還原 **粗體** 與 *斜體*。"""
    s = esc(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s


def md_to_html(md: str) -> str:
    """極簡 markdown→HTML，僅支援摘要會用到的子集：
    ## / ### 標題、- 或 * 清單、--- 分隔線、*斜體* / **粗體**、段落。
    """
    lines = (md or "").replace("\r\n", "\n").split("\n")
    html_parts: list[str] = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        if stripped in ("---", "***", "___"):
            close_list()
            html_parts.append('<hr class="yt-rule">')
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_list()
            level = len(m.group(1))
            tag = {1: "h3", 2: "h3", 3: "h4", 4: "h5"}.get(level, "h5")
            html_parts.append(f"<{tag}>{_md_inline(m.group(2))}</{tag}>")
            continue
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_md_inline(m.group(1))}</li>")
            continue
        close_list()
        html_parts.append(f"<p>{_md_inline(stripped)}</p>")

    close_list()
    return "\n".join(html_parts)


def one_liner(md: str, fallback: str) -> str:
    """The real headline for a brief.

    The pipeline titles podcast episodes 「EP686 | 🕸️」, which says nothing and
    cannot carry a broadsheet lead. Every summary opens with a 「## 一句話總結」
    section; that sentence is the headline the editor already wrote.
    """
    lines = [ln.strip() for ln in md.split("\n")]
    for i, ln in enumerate(lines):
        if ln.startswith("##") and "一句話總結" in ln:
            for nxt in lines[i + 1 :]:
                if nxt and not nxt.startswith("#"):
                    return nxt
            break
    return fallback


def strip_one_liner(md: str) -> str:
    """Drop the 「## 一句話總結」 heading and the one sentence under it.

    Only for the lead, whose headline *is* that sentence: printing it again three
    lines below in body type reads as a template rather than as an edit.

    The heading and that sentence, and nothing else. Article notes put their whole
    bullet list under the same heading — 「## 一句話總結」 / the sentence / six
    bullets / 「## 對設計／產品的啟示」 — so skipping to the next `##` deleted
    most of the brief and left the lead with a single paragraph to fill the page.
    """
    lines = md.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith("##") and "一句話總結" in line:
            i += 1
            while i < n and not lines[i].strip():
                i += 1
            # The sentence one_liner() lifted into the headline; a heading here
            # instead means the section was empty and there is nothing to drop.
            if i < n and not lines[i].strip().startswith("#"):
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out).lstrip("\n")


def _text_len(md: str) -> int:
    """摘要的實際字數——拿掉 markdown 記號與空白後剩下的內容。"""
    return len(re.sub(r"[#*\->\s|`]", "", md or ""))


def lead_story(brief: dict, kind: str, source: str) -> str:
    """The front-page lead: kicker, one enormous headline, then the brief itself
    already open. A lead that opens collapsed is not a lead."""
    md = brief.get("summary_md") or brief.get("summary") or ""
    headline = one_liner(md, brief.get("title", ""))
    body = dict(brief)
    body["summary_md"] = strip_one_liner(md)
    card = briefing_section(body) if kind == "財經" else newsletter_card(body)
    # Insert `open` before the class list, not after a literal one: an article
    # card carries `class="yt-brief nl-item"`, so matching on the podcast card's
    # exact opening tag silently left every article lead collapsed.
    card = card.replace("<details ", "<details open ", 1)
    # Two tracks need enough text to fill them. Below this the one paragraph a
    # short brief has gets sliced mid-word across the column rule, and the
    # balancer decides where — see .bs-lead-compact.
    compact = " bs-lead-compact" if _text_len(body["summary_md"]) < 700 else ""
    return f"""
    <article class="bs-lead{compact}">
      <div class="bs-kicker">{esc(kind)} · {esc(source)}</div>
      <h2 class="bs-headline">{esc(headline)}</h2>
      <div class="bs-lead-body">{card}</div>
    </article>"""


def briefing_section(brief: dict) -> str:
    """財經節目重點 — 渲染在早報最上方的完整結構化筆記區塊。"""
    if not brief or not brief.get("summary_md"):
        return ""
    title = esc(brief.get("title", ""))
    url = brief.get("url", "") or "https://www.youtube.com/"
    channel = esc(brief.get("channel", ""))
    published = esc(brief.get("published", ""))
    source = esc(brief.get("transcript_source", ""))
    body = md_to_html(brief.get("summary_md", ""))

    meta_bits = []
    if channel:
        meta_bits.append(f'<span class="yt-channel">{channel}</span>')
    if published:
        meta_bits.append(f'<span class="yt-date">{published}</span>')
    if source:
        meta_bits.append(f'<span class="chip yt-source">逐字稿來源 · {source}</span>')
    meta_html = " ".join(meta_bits)

    return f"""
<details class="yt-brief" aria-label="財經節目重點">
  <summary class="yt-summary">
    <span class="yt-toggle" aria-hidden="true">▸</span>
    <div class="yt-head">
      <div class="yt-kicker">📈 今日財經重點 / Morning Market Brief</div>
      <h2 class="yt-title"><a href="{url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">{title} <span class="yt-arrow" aria-hidden="true">↗</span></a></h2>
      <div class="yt-meta">{meta_html}</div>
      <span class="yt-expand-hint">點開閱讀全文 ▾</span>
    </div>
  </summary>
  <div class="yt-body">{body}</div>
  <div class="yt-foot"><a href="{url}" target="_blank" rel="noopener">▶ 收聽原始節目</a></div>
</details>
"""


def _lead_line(md: str) -> str:
    """從中文重點 markdown 取「一句話總結」那行（第一個非標題／非清單／非分隔線
    的段落），當作卡片上不必展開就看得到的導言。"""
    for raw in (md or "").replace("\r\n", "\n").split("\n"):
        s = raw.strip()
        if not s or s.startswith("#") or s in ("---", "***", "___") or s.startswith(("-", "*", ">")):
            continue
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"\*(.+?)\*", r"\1", s)
        s = re.sub(r"^（|）$", "", s)
        return s
    return ""


def newsletter_card(brief: dict) -> str:
    """把一篇 newsletter 全文重點渲染成一張可展開的重點卡片。

    刻意沿用財經重點（podcast_brief）那組 yt-* class：兩者是同一種東西——標題列
    可點開、展開後是 Claude 整理的中文重點。`.nl-item` 只負責把頭條規格降到列表
    規格（拿掉 3px 橘頂邊、標題小一級），不另立一套樣式。

    `.nl-item` 同時是搜尋索引分辨文章與 podcast 的依據
    （build_search_index.py 的 BLOCK_CLASSES），拿掉它文章就會被歸成 podcast。
    """
    title = esc(brief.get("title", ""))
    url = esc(brief.get("url", "") or "#")
    author = brief.get("author", "") or brief.get("source", "")
    name = esc(author)
    handle = esc(brief.get("handle", ""))
    source = esc(brief.get("source", ""))
    # 分類標籤跟著來源走（config 的 label）——不是每個來源都在談 UX。
    label = esc(brief.get("label", "") or "好文")
    published = esc(brief.get("published", ""))
    initial = esc((author.strip()[:1] or "•").upper())
    lead = esc(_lead_line(brief.get("summary_md", "")))
    body = md_to_html(brief.get("summary_md", ""))

    meta_bits = [
        f'<span class="nl-avatar" aria-hidden="true">{initial}</span>'
        f'<span class="yt-channel">{name}<span class="nl-verified" aria-hidden="true">✔</span></span>'
    ]
    if handle:
        meta_bits.append(f'<span class="nl-handle">@{handle}</span>')
    if published:
        meta_bits.append(f'<span class="yt-date">{published}</span>')
    if source:
        meta_bits.append(f'<span class="chip yt-source">{source}</span>')
    meta_html = " ".join(meta_bits)
    lead_html = f'<p class="nl-lead">{lead}</p>' if lead else ""

    return f"""
<details class="yt-brief nl-item" aria-label="{label}重點">
  <summary class="yt-summary">
    <span class="yt-toggle" aria-hidden="true">▸</span>
    <div class="yt-head">
      <div class="yt-kicker">📄 {label} / {source or 'Newsletter'}</div>
      <h2 class="yt-title"><a href="{url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">{title} <span class="yt-arrow" aria-hidden="true">↗</span></a></h2>
      <div class="yt-meta">{meta_html}</div>
      {lead_html}
      <span class="yt-expand-hint">點開閱讀全文 ▾</span>
    </div>
  </summary>
  <div class="yt-body">{body}</div>
  <div class="yt-foot"><a href="{url}" target="_blank" rel="noopener">↗ 閱讀原文</a></div>
</details>"""



def empty_state() -> str:
    """An empty day is published empty.

    The promise is 「今天該知道的，讀得完」, which is falsifiable by the product
    itself — so padding a thin day is a breach of it, and this state is part of
    keeping the promise rather than an apology for failing it. Flat sentence, no
    hedge, no explanation of the crawler, no substitute content.
    """
    return f"""
    <section class="empty">
      <div class="empty-mark" aria-hidden="true"></div>
      <p class="empty-title">今天沒有抓到值得收的推文。</p>
      <p class="empty-sub">明天 {config.PUBLISH_HOUR} 再出刊。</p>
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
    kw_count = len(criteria.get("keyword_pools", []))
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
      <p>每天從下列 <strong>{kw_count} 組關鍵字</strong> 分別以 <strong>Latest</strong>（最新）與 <strong>Top</strong>（最熱）兩種方式查詢 X 上最近 <strong>{since_days} 天</strong> 的推文，合併去重後，再比對<strong>前兩天已刊出的 tweet 排除重複</strong>，最後交由 Claude Sonnet 4.5 做二次過濾與排序，輸出 <strong>Top {top_n}</strong> 並附繁體中文摘要。</p>
      <p><strong>排序公式</strong>：<code>{formula}</code></p>

      <h4>關鍵字搜尋池</h4>
      <table>
        <thead><tr><th>主題</th><th>查詢字</th><th>讚數門檻</th></tr></thead>
        <tbody>{kw_rows}</tbody>
      </table>

      <h4>Claude 過濾規則</h4>
      <ul>{filter_items}</ul>

      <p class="criteria-note">語言：English / 中文（繁體 + 簡體），排除 replies / retweets。每組關鍵字依語言分別雙模式查詢，每模式各取最多 50 則，合併去重。摘要由 Claude Sonnet 4.5 自動生成，僅供快速瀏覽，實際內容請以原推文為準。</p>
    </div>
  </div>
</dialog>"""
