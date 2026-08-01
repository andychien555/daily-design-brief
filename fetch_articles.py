#!/usr/bin/env python3
"""
fetch_articles.py
訂閱 config.ARTICLE_FEEDS 裡的來源（UX 好文 + AI／設計 Newsletter），偵測近 N 天
內的新文章，抓「全文」→ Claude 整理成中文重點，寫進 data.json["article_briefs"]
（新到舊），由 generate_html.py 渲染成 X 貼文卡片。

全文取得依每個 feed 的 `fulltext` 決定：
- "feed"：RSS 的 content:encoded 已含整篇全文（WordPress／Substack）→ 直接用。
- "page"：RSS 只有摘要 → 用 r.jina.ai reader 抓文章頁全文（乾淨 markdown）。
- "wix" ：uxtigers.com（Wix server-rendered）專用正文擷取。

機房 IP 封鎖：Substack 的 feed 會擋 GitHub Actions（403）。標了 proxy_fallback 的
feed，直連失敗時改用 r.jina.ai 繞過（jina 從自己的 IP 抓），discovery 與內文都走它。

設計要點（對齊 fetch_podcast.py）：
- article_state.json 冪等快取（鍵：feed_name:guid）：同一篇已摘要 → 重用，不重打 Claude。
- 跨日去重：同一篇只在首次抓到那天顯示（first_shown），之後不再重複佔版面。
- 任何失敗只記 log、不丟例外，單一 feed 失敗不影響其他 feed 與整批早報。
"""

import os
import re
import sys
import html
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

import httpx

import config
from config import (
    ARTICLE_FEEDS,
    ARTICLE_JINA_PREFIX,
    ARTICLE_SHOW_WITHIN_DAYS,
    ARTICLE_MAX_ITEMS,
    ARTICLE_SUMMARY_SINGLE_PASS_MAX,
    ARTICLE_SUMMARY_CHUNK_CHARS,
)
from utils import load_json, save_json, claude_token_cost, record_usage

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

STATE_PATH = config.ARTICLE_STATE_FILE
DATA_PATH = config.DATA_FILE
TPE = config.TPE
UA = {"User-Agent": config.USER_AGENT}
BROWSER_UA = {"User-Agent": config.USER_AGENT_BROWSER}

# RSS 的 content:encoded 完整命名空間標籤。
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"


def log(msg: str) -> None:
    ts = datetime.now(TPE).strftime("%H:%M:%S")
    print(f"[{ts}] [article] {msg}", flush=True)


# ── HTTP / 純文字工具 ───────────────────────────────────────────────
def _fetch_text(url: str, headers: dict, timeout: int = None) -> str:
    with httpx.Client(timeout=timeout or config.HTTP_TIMEOUT, headers=headers,
                      follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text


def _html_to_text(raw: str) -> str:
    """把 HTML 粗略轉純文字：去標籤、還原 entity、壓縮空白。"""
    if not raw:
        return ""
    # 區塊級標籤轉換行，避免段落黏在一起
    txt = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6])\s*/?>", "\n", raw)
    txt = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", "", txt)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html.unescape(txt)
    lines = [ln.strip() for ln in txt.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(ln for ln in lines if ln)).strip()


# ── r.jina.ai reader：page 模式與 Substack proxy fallback 的通用全文抓取 ──
def _clean_markdown(md: str) -> str:
    """把 jina reader 的 markdown 收乾淨：去圖片、把 [文字](網址) 收成純文字、
    壓縮多餘空行，降低餵給 Claude 的 token。"""
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)          # 圖片
    md = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)       # 連結 → 純文字
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def _jina_read(url: str) -> tuple[str, str]:
    """用 r.jina.ai 抓一頁全文，回 (title, body_text)。jina 從自家 IP 抓，
    可繞過 Substack 對機房 IP 的封鎖。輸出開頭為 Title/URL/Published 幾行 metadata，
    正文在 'Markdown Content:' 之後。"""
    raw = _fetch_text(ARTICLE_JINA_PREFIX + url, UA, timeout=config.HTTP_TIMEOUT_LONG)
    title = ""
    m = re.search(r"^Title:\s*(.+)$", raw, re.M)
    if m:
        title = m.group(1).strip()
    marker = raw.find("Markdown Content:")
    body = raw[marker + len("Markdown Content:"):] if marker >= 0 else raw
    return title, _clean_markdown(body)


# ── Wix（uxtigers.com）專用正文擷取 ────────────────────────────────
def _extract_body_text(page_html: str) -> str:
    """從 Wix 文章頁 HTML 取正文：砍掉 <head>、正文前的導覽列、以及 post-footer
    之後（統計／推薦文章）。切點都退到該標籤的起始 '<'，避免切在標籤中間留半截。"""
    page_html = re.sub(r"(?is)<head.*?</head>", "", page_html)
    start = page_html.find('data-hook="post-title"')
    if start > 0:
        tag = page_html.rfind("<", 0, start)
        if tag > 0:
            page_html = page_html[tag:]
    cut = page_html.find('data-hook="post-footer"')
    if cut > 0:
        tag = page_html.rfind("<", 0, cut)
        page_html = page_html[:tag if tag > 0 else cut]
    return _html_to_text(page_html)


# ── discovery：取近 N 天文章 metadata（feed 或 jina fallback）─────────
def _parse_rss(xml_text: str, feed: dict, via_proxy: bool = False) -> list[dict]:
    win = feed.get("show_within_days", ARTICLE_SHOW_WITHIN_DAYS)
    root = ET.fromstring(xml_text)
    out = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        guid = (item.findtext("guid") or "").strip() or link
        content_encoded = (item.findtext(CONTENT_NS) or "").strip()

        published_dt, published = None, ""
        try:
            published_dt = parsedate_to_datetime(pub_raw).astimezone(TPE)
            published = published_dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        if published_dt is not None and (datetime.now(TPE) - published_dt) > timedelta(days=win):
            continue

        out.append({
            "state_key": f"{feed['name']}:{guid}",
            "title": title,
            "url": link or feed["rss"],
            "published": published,
            "published_dt": published_dt,
            "author": feed["name"],
            "handle": feed.get("handle", ""),
            "source": feed.get("source", ""),
            "content_encoded": content_encoded,
            "via_proxy": via_proxy,
        })
    return out


# jina 對 feed URL 回的 markdown，每篇是一個 `###` 標題區塊。jina 的格式會浮動：
#   A) `### [標題](網址)`（連結型；Substack 標題常為空 → `### [](網址)`）
#   B) `### 標題`\n\n`網址`\n\n`日期`（純文字型）
# 用 block-based 解析同時吃這兩種：每塊取第一個網址、第一個 RFC-822 日期
# （WordPress 為 "+0000"、Substack 為 "GMT"），標題取連結內文字或純標題行。
_JINA_URL_RE = re.compile(r"https?://[^\s)]+")
_JINA_LINK_TITLE_RE = re.compile(r"^\[([^\]]*)\]\(")
_JINA_DATE_RE = re.compile(
    r"[A-Z][a-z]{2},\s+\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}[^\n]*?(?:GMT|[+\-]\d{4})"
)


def _parse_jina_feed(md: str, feed: dict) -> list[dict]:
    win = feed.get("show_within_days", ARTICLE_SHOW_WITHIN_DAYS)
    out, seen = [], set()
    for blk in re.split(r"\n#{2,4}\s+", "\n" + md):
        head_line = blk.splitlines()[0].strip() if blk.strip() else ""
        if not head_line:
            continue
        um = _JINA_URL_RE.search(blk)
        dm = _JINA_DATE_RE.search(blk)
        if not um or not dm:  # 沒有文章連結或日期的區塊（如 feed 自身/分頁）跳過
            continue
        url = um.group(0).rstrip(").,")
        if url in seen:
            continue
        seen.add(url)

        lm = _JINA_LINK_TITLE_RE.match(head_line)
        if lm:
            title = lm.group(1).strip()
        elif head_line.startswith("http"):
            title = ""
        else:
            title = re.sub(r"\]\(.*$", "", head_line).strip()

        published_dt, published = None, ""
        try:
            published_dt = parsedate_to_datetime(dm.group(0)).astimezone(TPE)
            published = published_dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        if published_dt is not None and (datetime.now(TPE) - published_dt) > timedelta(days=win):
            continue

        out.append({
            "state_key": f"{feed['name']}:{url}",
            "title": title,  # 可能為空（Substack）→ 抓內文時由 jina 補
            "url": url,
            "published": published,
            "published_dt": published_dt,
            "author": feed["name"],
            "handle": feed.get("handle", ""),
            "source": feed.get("source", ""),
            "content_encoded": "",
            "via_proxy": True,
        })
    return out


def recent_articles(feed: dict) -> list[dict]:
    """回傳某 feed 內近 ARTICLE_SHOW_WITHIN_DAYS 天、最多 ARTICLE_MAX_ITEMS 篇
    文章的 metadata（新到舊）。discover=="jina" 的來源改用 r.jina.ai 繞過封鎖。"""
    if feed.get("discover") == "jina":
        try:
            _, md = _jina_read(feed["rss"])
            items = _parse_jina_feed(md, feed)
        except Exception as e:
            log(f"[warn] {feed['name']} jina discovery 失敗：{e}")
            return []
    else:
        try:
            items = _parse_rss(_fetch_text(feed["rss"], BROWSER_UA), feed)
        except Exception as e:
            log(f"[warn] {feed['name']} 直連 feed 失敗：{e}")
            return []

    items.sort(key=lambda a: a["published_dt"] or datetime.min.replace(tzinfo=TPE), reverse=True)
    return items[:ARTICLE_MAX_ITEMS]


def article_full_text(art: dict, feed: dict) -> tuple[str, str]:
    """依 feed 模式取全文，回 (title, text)。title 可能被 jina 補上（原本為空時）。"""
    mode = feed.get("fulltext", "feed")
    title = art.get("title", "")

    if art.get("via_proxy"):
        # Substack 直連被擋 → 內文也走 jina
        jt, text = _jina_read(art["url"])
        return (title or jt), text
    if mode == "wix":
        return title, _extract_body_text(_fetch_text(art["url"], BROWSER_UA))
    if mode == "feed":
        ce = art.get("content_encoded") or ""
        if ce:
            return title, _html_to_text(ce)
        # feed 沒帶全文 → 退回 jina 抓文章頁
        jt, text = _jina_read(art["url"])
        return (title or jt), text
    # mode == "page"：RSS 只有摘要 → jina 抓文章頁
    jt, text = _jina_read(art["url"])
    return (title or jt), text


# ── Claude 中文重點 ─────────────────────────────────────────────────
def build_system_prompt(topic: str) -> str:
    return (
        "你是一位專業的科技／設計內容編輯。使用者會給你一篇英文文章的全文，"
        f"主題為{topic}。"
        "請忠實整理成結構清楚、可在一兩分鐘內讀完重點的中文筆記，用繁體中文書寫。"
        "保留文章中的具體數據、研究結論與案例；只根據文章內容，不要自行補充或臆測。"
        "這是對他人文章的摘要——描述時用「作者認為…」這類語氣。"
    )


FORMAT_INSTRUCTION = (
    "請輸出以下 Markdown 結構（不要加 ``` 圍欄、不要多餘前言）：\n\n"
    "## 一句話總結\n"
    "（一句話，先講整篇最重要的結論或觀點）\n\n"
    "接著用 3–6 個重點，每個為一個項目符號，以「**粗體標籤：** 」開頭，"
    "後接 1–2 句說明，把相關數據、研究或案例寫進說明裡。範例：\n"
    "- **重點標籤：** 作者指出……（把數據或案例寫進來）。\n\n"
    "最後一段：\n\n"
    "## 對設計／產品的啟示\n"
    "（作者的建議，或這篇對做設計/產品/AI 的人有什麼實務啟發）\n\n"
    "---\n"
    "*本筆記為文章重點摘要，完整內容請見原文。*"
)


def _claude(client, system: str, user: str, max_tokens: int = 3000) -> str:
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    in_tok, out_tok, cost = claude_token_cost(resp.usage, config.CLAUDE_PRICING)
    record_usage(datetime.now(TPE).strftime("%Y-%m-%d"), "article-summary",
                 config.USAGE_LOG_FILE, input_tokens=in_tok, output_tokens=out_tok, cost_usd=cost)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


def summarize(text: str, title: str, topic: str) -> str:
    if not ANTHROPIC_API_KEY:
        log("[info] ANTHROPIC_API_KEY 未設定 — 無法摘要")
        return ""
    try:
        import anthropic
    except ImportError:
        log("[warn] anthropic 套件未安裝 — 無法摘要")
        return ""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system = build_system_prompt(topic)
    try:
        if len(text) <= ARTICLE_SUMMARY_SINGLE_PASS_MAX:
            user = f"文章標題：{title}\n\n全文：\n{text}\n\n{FORMAT_INSTRUCTION}"
            return _claude(client, system, user)

        log(f"全文 {len(text)} 字 > {ARTICLE_SUMMARY_SINGLE_PASS_MAX} → map-reduce")
        chunks = [
            text[i:i + ARTICLE_SUMMARY_CHUNK_CHARS]
            for i in range(0, len(text), ARTICLE_SUMMARY_CHUNK_CHARS)
        ]
        partials = []
        for i, ch in enumerate(chunks):
            log(f"  條列第 {i+1}/{len(chunks)} 段")
            user = (
                f"以下是文章的第 {i+1}/{len(chunks)} 段，請條列此段重點"
                f"（保留數據、研究與案例，繁體中文）：\n\n{ch}"
            )
            partials.append(_claude(client, system, user, max_tokens=1500))
        merged = "\n\n".join(partials)
        user = (
            f"文章標題：{title}\n\n以下是各段重點條列，請彙整成最終筆記：\n\n"
            f"{merged}\n\n{FORMAT_INSTRUCTION}"
        )
        return _claude(client, system, user)
    except Exception as e:
        log(f"[warn] Claude 摘要失敗：{e}")
        return ""


# ── state / data I/O ────────────────────────────────────────────────
def process_one(art: dict, feed: dict, state: dict, force: bool) -> dict | None:
    key = art["state_key"]
    if not force and key in state:
        log(f"{art['author']}：{art['title'][:32]} 已在快取 → 重用")
        brief = state[key]
        # label 是 feed 的靜態屬性，補進早於這個欄位的快取，省得重抓一輪。
        brief.setdefault("label", feed.get("label", ""))
        return brief

    log(f"新文章：{(art['title'] or art['url'])[:44]}（{art['published']}）")
    try:
        title, text = article_full_text(art, feed)
    except Exception as e:
        log(f"[warn] {(art['title'] or art['url'])[:32]} 抓全文失敗：{e}")
        return None
    if not text:
        log(f"[warn] {(art['title'] or art['url'])[:32]} 全文為空 → 跳過")
        return None
    title = title or art.get("title") or feed["name"]

    summary_md = summarize(text, title, feed.get("topic", ""))
    if not summary_md:
        log(f"[warn] {title[:32]} 摘要為空 → 跳過")
        return None

    brief = {
        "title": title,
        "url": art["url"],
        "published": art["published"],
        "author": art["author"],
        "handle": art.get("handle", ""),
        "source": art.get("source", ""),
        "label": feed.get("label", ""),
        "summary_md": summary_md,
    }
    state[key] = brief
    if len(state) > 120:
        for k in list(state.keys())[:-120]:
            state.pop(k, None)
    save_json(STATE_PATH, state)
    return brief


def main() -> None:
    force = "--force" in sys.argv
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    state = load_json(STATE_PATH)

    collected = []  # (published_dt, brief)
    for feed in ARTICLE_FEEDS:
        try:
            for art in recent_articles(feed):
                brief = process_one(art, feed, state, force)
                if not brief:
                    continue
                # 跨日去重：同一篇只在「首次出現的那天」顯示，之後不再重複，
                # 直到來源發新文章。first_shown 記在 state 快取裡（鍵：state_key）。
                first_shown = brief.get("first_shown")
                if not first_shown:
                    brief["first_shown"] = today
                    sk = art["state_key"]
                    if isinstance(state.get(sk), dict):
                        state[sk]["first_shown"] = today
                    save_json(STATE_PATH, state)
                elif first_shown != today:
                    log(f"{brief['title'][:32]}（{art['published']}）"
                        f"已於 {first_shown} 顯示過 → 今日不重複")
                    continue
                collected.append((art["published_dt"], brief))
        except Exception as e:
            log(f"[warn] {feed['name']} 處理失敗（不影響其他 feed）：{e}")

    collected.sort(key=lambda t: t[0] or datetime.min.replace(tzinfo=TPE), reverse=True)
    briefs = [b for _, b in collected]

    data = load_json(DATA_PATH)
    data["article_briefs"] = briefs
    save_json(DATA_PATH, data)
    log(f"✅ data.json 寫入 {len(briefs)} 則 article_briefs："
        + "、".join((b["title"] or b["source"])[:20] for b in briefs))


if __name__ == "__main__":
    main()
