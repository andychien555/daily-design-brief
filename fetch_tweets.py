#!/usr/bin/env python3
"""
fetch_tweets.py
Fetches trending Product & Design tweets via 6551.io API,
ranks by engagement, summarizes in Traditional Chinese via Claude,
saves results to data.json.
"""

import os
import json
import httpx
from datetime import datetime, timezone, timedelta

TWITTER_TOKEN = os.environ["TWITTER_TOKEN"]
API_BASE = os.environ.get("TWITTER_API_BASE", "https://ai.6551.io")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TOP_N = 10

HEADERS = {
    "Authorization": f"Bearer {TWITTER_TOKEN}",
    "Content-Type": "application/json",
}

# Search queries — product & design topics, last 2 days, Top-sorted
SEARCH_QUERIES = [
    {
        "label": "Product Design × AI UX",
        "query": "product design AI UX",
        "min_likes": 50,
    },
    {
        "label": "Design System × SaaS × Figma",
        "query": "design system SaaS figma",
        "min_likes": 50,
    },
    {
        "label": "AI Agent × Claude × Cursor × Design",
        "query": "AI agent Claude cursor design",
        "min_likes": 100,
    },
    {
        "label": "Vibe Coding × Prototype × Figma",
        "query": "vibe coding prototype figma",
        "min_likes": 50,
    },
]
SINCE_DAYS = 2


def search_tweets(query: str, min_likes: int, max_rows: int = 20, since_date: str | None = None) -> list[dict]:
    """Call 6551.io /open/twitter_search endpoint."""
    url = f"{API_BASE}/open/twitter_search"
    payload = {
        "keywords": query,
        "minLikes": min_likes,
        "maxResults": max_rows,
        "product": "Top",
        "lang": "en",
        "excludeReplies": True,
        "excludeRetweets": True,
    }
    if since_date:
        payload["sinceDate"] = since_date
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=HEADERS, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                for key in ("tweets", "data", "result", "results", "items"):
                    val = data.get(key)
                    if isinstance(val, list):
                        return val
                return []
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  [warn] Query '{query}' failed: {e}")
        return []

def dedupe(tweets: list[dict]) -> list[dict]:
    """Remove duplicate tweets by id."""
    seen = set()
    result = []
    for t in tweets:
        tid = t.get("id") or t.get("tweet_id")
        if tid and tid not in seen:
            seen.add(tid)
            result.append(t)
    return result

def pick_top(tweets: list[dict], n: int = 5) -> list[dict]:
    """Sort by engagement (likes + retweets) and return top n."""
    def score(t):
        return (t.get("favoriteCount") or t.get("like_count") or 0) + \
               (t.get("retweetCount") or t.get("retweet_count") or 0) * 2
    return sorted(tweets, key=score, reverse=True)[:n]

def normalize(tweet: dict, source: str = "") -> dict:
    """Normalize different field name conventions."""
    return {
        "id":       tweet.get("id") or tweet.get("tweet_id", ""),
        "text":     tweet.get("text") or tweet.get("full_text", ""),
        "author":   tweet.get("userScreenName") or tweet.get("username") or tweet.get("screen_name", ""),
        "name":     tweet.get("userName") or tweet.get("name") or tweet.get("userScreenName", ""),
        "likes":    tweet.get("favoriteCount") or tweet.get("like_count") or 0,
        "retweets": tweet.get("retweetCount") or tweet.get("retweet_count") or 0,
        "replies":  tweet.get("replyCount") or tweet.get("reply_count") or 0,
        "created":  tweet.get("createdAt") or tweet.get("created_at", ""),
        "url":      tweet.get("url") or (
                        f"https://x.com/{tweet.get('userScreenName', '')}/status/{tweet.get('id', '')}"
                        if tweet.get("id") else ""
                    ),
        "source":   source,
        "summary_zh": "",
    }

def score(t: dict) -> int:
    return t.get("likes") or 0

def curate_with_claude(candidates: list[dict], top_n: int) -> list[dict]:
    """Use Claude to filter ads/memes/off-topic from candidates, pick top_n, add Chinese summaries.
    Falls back to sorting by likes if API key or package is missing."""
    if not candidates:
        return []
    fallback = sorted(candidates, key=score, reverse=True)[:top_n]

    if not ANTHROPIC_API_KEY:
        print("  [info] ANTHROPIC_API_KEY not set — using likes-only fallback")
        return fallback

    try:
        import anthropic
    except ImportError:
        print("  [warn] anthropic package missing — using likes-only fallback")
        return fallback

    items = [
        {
            "id": t["id"], "author": t["author"],
            "likes": t["likes"], "retweets": t["retweets"], "replies": t["replies"],
            "text": t["text"],
        }
        for t in candidates
    ]
    prompt = (
        "你是 Product & Design 策展編輯。以下是候選英文推文 JSON 陣列，請從中挑出 "
        f"**最多 {top_n} 則** 對 product designer / PM 讀者最有價值的內容，並為每則寫 1-2 句繁體中文摘要。\n\n"
        "【過濾規則】務必排除：\n"
        "1. 純廣告、招聘文（除非 JD 本身有洞見，例如 Ramp 那種）\n"
        "2. 與產品設計/PM 無關（crypto 炒幣、體育 logo、政治議題等）\n"
        "3. Meme / 搞笑但沒內容\n\n"
        "【排序偏好】\n"
        "- 有觀點的原創內容 > 資訊整理/轉述\n"
        "- 過濾後依 likes 高低為主要排序\n\n"
        "【摘要規則】\n"
        "- 1-2 句繁體中文，聚焦核心觀點/takeaway\n"
        "- 不要描述作者身分或互動數；語氣平實專業，避免行銷語\n\n"
        '【輸出】只輸出 JSON 陣列（不要 markdown code block、不要其他文字），'
        '格式：[{"id": "...", "summary_zh": "..."}]，順序即為最終排名。\n\n'
        f"候選推文：\n{json.dumps(items, ensure_ascii=False)}"
    )

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        picks = json.loads(raw)
        by_id = {t["id"]: t for t in candidates}
        ordered = []
        for p in picks[:top_n]:
            tid = p.get("id")
            if tid in by_id:
                tweet = by_id[tid]
                tweet["summary_zh"] = p.get("summary_zh", "")
                ordered.append(tweet)
        if not ordered:
            print("  [warn] Claude returned no usable picks — using fallback")
            return fallback
        print(f"  ✨ Claude curated {len(ordered)}/{len(candidates)} candidates with summaries")
        return ordered
    except Exception as e:
        print(f"  [warn] Claude curation failed: {e} — using fallback")
        return fallback

def main():
    tz_taipei = timezone(timedelta(hours=8))
    now = datetime.now(tz_taipei)
    date_str = now.strftime("%Y-%m-%d")
    date_display = now.strftime("%Y 年 %m 月 %d 日")

    since_date = (now - timedelta(days=SINCE_DAYS)).strftime("%Y-%m-%d")
    print(f"📰 Fetching tweets since {since_date} for {date_str} ...")

    pool = []
    for cfg in SEARCH_QUERIES:
        print(f"  🔍 {cfg['label']}: {cfg['query']}")
        raw = search_tweets(cfg["query"], cfg["min_likes"], max_rows=20, since_date=since_date)
        normalized = [normalize(t, source=cfg["label"]) for t in raw]
        print(f"     → {len(normalized)} candidates")
        pool.extend(normalized)

    seen_ids = set()
    unique = []
    for t in pool:
        if t["id"] and t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            unique.append(t)

    candidate_cap = max(TOP_N * 3, 30)
    candidates = sorted(unique, key=score, reverse=True)[:candidate_cap]
    print(f"  🏆 Pool: {len(pool)} → unique: {len(unique)} → Claude candidates: {len(candidates)}")

    top = curate_with_claude(candidates, TOP_N)

    output = {
        "date": date_str,
        "date_display": date_display,
        "generated_at": now.isoformat(),
        "since_date": since_date,
        "top_tweets": top,
        "criteria": {
            "keyword_pools": [
                {"label": q["label"], "query": q["query"], "min_likes": q["min_likes"]}
                for q in SEARCH_QUERIES
            ],
            "since_days": SINCE_DAYS,
            "top_n": TOP_N,
            "score_formula": "likes（主要）+ Claude 人工過濾廣告/招聘/meme/非設計",
            "claude_filter_rules": [
                "排除純廣告、招聘文（有洞見的 JD 除外）",
                "排除與產品設計/PM 無關（crypto、體育、政治等）",
                "排除 meme/搞笑但無內容",
                "偏好有觀點的原創內容",
            ],
        },
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ data.json saved — top {len(top)} tweets")

if __name__ == "__main__":
    main()
