#!/usr/bin/env python3
"""
fetch_articles.py
訂閱 config.ARTICLE_FEEDS 裡的作者 RSS（目前為 Jakob Nielsen 的 UX 文章），
偵測近 N 天內的新文章，抓「全文」（RSS content:encoded）→ Claude 整理成
中文重點筆記，寫進 data.json["article_briefs"]（新到舊）。

設計要點（對齊 fetch_podcast.py）：
- article_state.json 冪等快取（鍵：feed_key:guid）：同一篇已摘要 → 重用，
  不重打 Claude。每天由 daily.yml 呼叫一次即可。
- 純文字文章、無音檔 → 不需下載/Whisper，比 podcast 單純。
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

CONTENT_ENCODED = "{http://purl.org/rss/1.0/modules/content/}encoded"


def log(msg: str) -> None:
    ts = datetime.now(TPE).strftime("%H:%M:%S")
    print(f"[{ts}] [article] {msg}", flush=True)


# ── 1. 取 RSS 並抽出近期文章 ───────────────────────────────────────
def _fetch_rss_text(url: str) -> str:
    with httpx.Client(timeout=config.HTTP_TIMEOUT, headers=UA, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text


def _html_to_text(raw: str) -> str:
    """把 content:encoded 的 HTML 粗略轉純文字：去標籤、還原 entity、壓縮空白。"""
    if not raw:
        return ""
    # 區塊級標籤轉換行，避免段落黏在一起
    txt = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6])\s*/?>", "\n", raw)
    txt = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", "", txt)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html.unescape(txt)
    lines = [ln.strip() for ln in txt.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(ln for ln in lines if ln)).strip()


def recent_articles(feed: dict) -> list[dict]:
    """回傳某 feed 內近 ARTICLE_SHOW_WITHIN_DAYS 天、最多 ARTICLE_MAX_ITEMS 篇文章（新到舊）。"""
    try:
        root = ET.fromstring(_fetch_rss_text(feed["rss"]))
    except Exception as e:
        log(f"[warn] {feed['name']} 取得/解析 RSS 失敗：{e}")
        return []

    out = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        guid = (item.findtext("guid") or "").strip() or link
        enc = item.find(CONTENT_ENCODED)
        body_html = (enc.text if enc is not None else None) or item.findtext("description") or ""

        published_dt, published = None, ""
        try:
            published_dt = parsedate_to_datetime(pub_raw).astimezone(TPE)
            published = published_dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        if published_dt is not None and (datetime.now(TPE) - published_dt) > timedelta(days=ARTICLE_SHOW_WITHIN_DAYS):
            continue

        out.append({
            "state_key": f"{feed['name']}:{guid}",
            "title": title,
            "url": link or feed["rss"],
            "published": published,
            "published_dt": published_dt,
            "author": feed["name"],
            "text": _html_to_text(body_html),
        })
    out.sort(key=lambda a: a["published_dt"] or datetime.min.replace(tzinfo=TPE), reverse=True)
    return out[:ARTICLE_MAX_ITEMS]


# ── 2. Claude 中文重點 ─────────────────────────────────────────────
SYSTEM_PROMPT = (
    "你是一位專業的 UX／產品設計內容編輯。使用者會給你一篇英文文章的全文"
    "（作者為 UX 專家 Jakob Nielsen，內容多為使用者體驗、AI 與產品設計）。"
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
    "- **AI 沒有取代 UX：** 作者指出即使有 AI 生成介面，可用性測試仍是找出真實問題的唯一可靠方法。\n\n"
    "最後一段：\n\n"
    "## 對設計／產品的啟示\n"
    "（作者的建議，或這篇對做設計/產品的人有什麼實務啟發）\n\n"
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


def summarize(text: str, title: str) -> str:
    if not ANTHROPIC_API_KEY:
        log("[info] ANTHROPIC_API_KEY 未設定 — 無法摘要")
        return ""
    try:
        import anthropic
    except ImportError:
        log("[warn] anthropic 套件未安裝 — 無法摘要")
        return ""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        if len(text) <= ARTICLE_SUMMARY_SINGLE_PASS_MAX:
            user = f"文章標題：{title}\n\n全文：\n{text}\n\n{FORMAT_INSTRUCTION}"
            return _claude(client, SYSTEM_PROMPT, user)

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
            partials.append(_claude(client, SYSTEM_PROMPT, user, max_tokens=1500))
        merged = "\n\n".join(partials)
        user = (
            f"文章標題：{title}\n\n以下是各段重點條列，請彙整成最終筆記：\n\n"
            f"{merged}\n\n{FORMAT_INSTRUCTION}"
        )
        return _claude(client, SYSTEM_PROMPT, user)
    except Exception as e:
        log(f"[warn] Claude 摘要失敗：{e}")
        return ""


# ── 3. state / data I/O ────────────────────────────────────────────
def process_one(art: dict, state: dict, force: bool) -> dict | None:
    key = art["state_key"]
    if not force and key in state:
        log(f"{art['author']}：{art['title'][:32]} 已在快取 → 重用")
        return state[key]

    if not art["text"]:
        log(f"[warn] {art['title'][:32]} 全文為空 → 跳過")
        return None

    log(f"新文章：{art['title'][:44]}（{art['published']}）")
    summary_md = summarize(art["text"], art["title"])
    if not summary_md:
        log(f"[warn] {art['title'][:32]} 摘要為空 → 跳過")
        return None

    brief = {
        "title": art["title"],
        "url": art["url"],
        "published": art["published"],
        "author": art["author"],
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
    state = load_json(STATE_PATH)

    collected = []  # (published_dt, brief)
    for feed in ARTICLE_FEEDS:
        try:
            for art in recent_articles(feed):
                brief = process_one(art, state, force)
                if brief:
                    collected.append((art["published_dt"], brief))
        except Exception as e:
            log(f"[warn] {feed['name']} 處理失敗（不影響其他 feed）：{e}")

    collected.sort(key=lambda t: t[0] or datetime.min.replace(tzinfo=TPE), reverse=True)
    briefs = [b for _, b in collected]

    data = load_json(DATA_PATH)
    data["article_briefs"] = briefs
    save_json(DATA_PATH, data)
    log(f"✅ data.json 寫入 {len(briefs)} 則 article_briefs："
        + "、".join(b["title"][:20] for b in briefs))


if __name__ == "__main__":
    main()
