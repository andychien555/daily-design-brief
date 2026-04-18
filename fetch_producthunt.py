#!/usr/bin/env python3
"""
fetch_producthunt.py
Fetches today's new products from the Product Hunt Atom feed,
writes Traditional Chinese summaries via Claude,
and merges `top_products` into data.json.
"""

import os
import json
import re
import html as html_lib
import httpx
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

from config import (
    PRODUCTS_TOP_N as TOP_N,
    PRODUCTS_WINDOW_DAYS as WINDOW_DAYS,
    PRODUCTS_RSS_URL as RSS_URL,
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch_rss() -> str:
    with httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0 (daily-design-brief)"}) as c:
        r = c.get(RSS_URL)
        r.raise_for_status()
        return r.text


def extract_tagline(content_html: str) -> str:
    """First <p> in the content HTML is the tagline."""
    decoded = html_lib.unescape(content_html)
    m = re.search(r"<p>\s*(.*?)\s*</p>", decoded, re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def parse_entries(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for entry in root.findall("a:entry", NS):
        title = (entry.findtext("a:title", default="", namespaces=NS) or "").strip()
        link_el = entry.find("a:link", NS)
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        published = entry.findtext("a:published", default="", namespaces=NS) or ""
        author = (entry.findtext("a:author/a:name", default="", namespaces=NS) or "").strip()
        content_html = entry.findtext("a:content", default="", namespaces=NS) or ""
        tagline = extract_tagline(content_html)
        out.append({
            "title": title,
            "url": link,
            "published": published,
            "author": author,
            "tagline": tagline,
        })
    return out


def filter_recent(items: list[dict], window_days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    result = []
    for it in items:
        try:
            pub = datetime.fromisoformat(it["published"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                result.append(it)
        except Exception:
            continue
    return result


def summarize_with_claude(products: list[dict]) -> list[dict]:
    """Add Traditional Chinese summaries describing what each product does."""
    if not products:
        return products
    if not ANTHROPIC_API_KEY:
        print("  [info] ANTHROPIC_API_KEY not set — leaving summaries blank")
        return products
    try:
        import anthropic
    except ImportError:
        print("  [warn] anthropic package missing — leaving summaries blank")
        return products

    items = [{"title": p["title"], "tagline": p["tagline"]} for p in products]
    prompt = (
        "你是 Product Hunt 策展編輯。以下是今日的新產品列表（JSON），"
        "請為每個產品寫 1-2 句繁體中文摘要，說明「這個產品是做什麼的」。\n\n"
        "【摘要規則】\n"
        "- 1-2 句繁體中文，聚焦產品用途與目標使用者\n"
        "- 語氣平實專業，避免行銷語與過多形容詞\n"
        "- 保留英文專有名詞（產品名、技術名）\n\n"
        "【輸出】只輸出 JSON 陣列（不要 markdown code block、不要其他文字），"
        '格式：[{"title": "...", "summary_zh": "..."}]，順序需與輸入一致。\n\n'
        f"產品列表：\n{json.dumps(items, ensure_ascii=False)}"
    )

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        picks = json.loads(raw)
        by_title = {p.get("title"): p for p in picks}
        for prod in products:
            match = by_title.get(prod["title"])
            if match:
                prod["summary_zh"] = match.get("summary_zh", "")
        filled = sum(1 for p in products if p.get("summary_zh"))
        print(f"  ✨ Claude summarised {filled}/{len(products)} products")
    except Exception as e:
        print(f"  [warn] Claude summarisation failed: {e}")
    return products


def main():
    print("🏹 Fetching Product Hunt RSS ...")
    try:
        xml_text = fetch_rss()
    except Exception as e:
        print(f"  [warn] RSS fetch failed: {e}")
        xml_text = ""
    items = parse_entries(xml_text) if xml_text else []
    recent = filter_recent(items, WINDOW_DAYS)
    seen = set()
    unique = []
    for it in recent:
        key = it["url"] or it["title"]
        if key and key not in seen:
            seen.add(key)
            unique.append(it)
    top = unique[:TOP_N]
    print(f"  → {len(items)} total · {len(recent)} recent · keeping top {len(top)}")

    for p in top:
        p["summary_zh"] = ""
    top = summarize_with_claude(top)

    data_path = "data.json"
    data = {}
    if os.path.exists(data_path):
        try:
            with open(data_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["top_products"] = top
    criteria = data.setdefault("criteria", {})
    criteria["producthunt"] = {
        "source": "Product Hunt Atom feed",
        "window_days": WINDOW_DAYS,
        "top_n": TOP_N,
    }

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ data.json updated — top {len(top)} products")


if __name__ == "__main__":
    main()
