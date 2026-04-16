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

# Search queries for Product & Design topics
SEARCH_QUERIES = [
    {
        "label": "Product Design",
        "query": "product design UX",
        "min_likes": 200,
    },
    {
        "label": "UI Design",
        "query": "UI design interface",
        "min_likes": 200,
    },
    {
        "label": "Product Management",
        "query": "product management roadmap strategy",
        "min_likes": 200,
    },
    {
        "label": "AI + Design",
        "query": "AI design product",
        "min_likes": 300,
    },
]

# KOL groups — fetch recent tweets from these accounts, rank by engagement
KOL_GROUPS = [
    {
        "label": "PM 大神近期推文",
        "users": ["cagan", "lennysan", "destraynor", "lissijean", "noah_weiss"],
        "per_user": 10,
        "top_n": 8,
    },
    {
        "label": "設計大神近期推文",
        "users": ["joulee", "lukew", "jnd1er", "leeloowrites"],
        "per_user": 10,
        "top_n": 8,
    },
    {
        "label": "Andy 追蹤的設計師",
        "users": [
            "tomkrcha", "ivanhzhao", "ryolu_",
            "splinetool", "stfnco", "marcelkargul",
            "MagicPathAI", "DilumSanjaya", "mobbin",
        ],
        "per_user": 8,
        "top_n": 10,
    },
]

def search_tweets(query: str, min_likes: int, max_rows: int = 10) -> list[dict]:
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

def fetch_user_tweets(username: str, max_results: int = 10) -> list[dict]:
    """Fetch a user's recent tweets via /open/twitter_search with fromUser filter.

    The /open/twitter_user_tweets endpoint requires a paid plan for most accounts;
    search with fromUser is more permissive on the free tier.
    """
    url = f"{API_BASE}/open/twitter_search"
    payload = {
        "fromUser": username,
        "maxResults": max_results,
        "product": "Latest",
        "excludeReplies": True,
        "excludeRetweets": True,
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=HEADERS, json=payload)
            if resp.status_code >= 400:
                print(f"  [warn] @{username} HTTP {resp.status_code}: {resp.text[:300]}")
                return []
            data = resp.json()
            if isinstance(data, dict):
                for key in ("tweets", "data", "result", "results", "items"):
                    val = data.get(key)
                    if isinstance(val, list):
                        return val
                return []
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  [warn] @{username} failed: {e}")
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
    return (t.get("likes") or 0) + (t.get("retweets") or 0) * 2

def summarize_with_claude(tweets: list[dict]) -> list[dict]:
    """Use Claude Haiku to add a Traditional Chinese summary to each tweet.
    Updates tweets in-place and returns them. Silently no-ops if API key missing."""
    if not ANTHROPIC_API_KEY:
        print("  [info] ANTHROPIC_API_KEY not set — skipping summaries")
        return tweets
    if not tweets:
        return tweets

    try:
        import anthropic
    except ImportError:
        print("  [warn] anthropic package missing — skipping summaries")
        return tweets

    items = [{"id": t["id"], "author": t["author"], "text": t["text"]} for t in tweets]
    prompt = (
        "你是 Product & Design 內容策展編輯。請為下列每則英文推文寫 1-2 句繁體中文摘要，"
        "讓讀者能快速判斷是否要點進去閱讀。聚焦在「這則推文的核心觀點或價值」，不要描述作者身分或互動數。"
        "語氣平實專業，避免行銷語。\n\n"
        "輸入是一個 JSON 陣列。請**只**輸出一個 JSON 陣列，順序與輸入相同，格式為 "
        '[{"id": "...", "summary_zh": "..."}] — 不要任何額外說明或 markdown code block。\n\n'
        f"推文：\n{json.dumps(items, ensure_ascii=False)}"
    )

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        summaries = json.loads(raw)
        by_id = {s["id"]: s.get("summary_zh", "") for s in summaries}
        for t in tweets:
            t["summary_zh"] = by_id.get(t["id"], "")
        filled = sum(1 for t in tweets if t["summary_zh"])
        print(f"  ✍️  Claude summarized {filled}/{len(tweets)} tweets")
    except Exception as e:
        print(f"  [warn] Claude summarization failed: {e}")
    return tweets

def main():
    tz_taipei = timezone(timedelta(hours=8))
    now = datetime.now(tz_taipei)
    date_str = now.strftime("%Y-%m-%d")
    date_display = now.strftime("%Y 年 %m 月 %d 日")

    print(f"📰 Fetching tweets for {date_str} ...")

    pool = []

    for cfg in SEARCH_QUERIES:
        print(f"  🔍 {cfg['label']}: {cfg['query']}")
        raw = search_tweets(cfg["query"], cfg["min_likes"])
        normalized = [normalize(t, source=cfg["label"]) for t in raw]
        print(f"     → {len(normalized)} candidates")
        pool.extend(normalized)

    for group in KOL_GROUPS:
        print(f"  👤 {group['label']}: {len(group['users'])} accounts")
        for username in group["users"]:
            user_tweets = fetch_user_tweets(username, max_results=group["per_user"])
            print(f"     · @{username}: {len(user_tweets)} tweets")
            pool.extend(normalize(t, source=group["label"]) for t in user_tweets)

    seen_ids = set()
    unique = []
    for t in pool:
        if t["id"] and t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            unique.append(t)

    top = sorted(unique, key=score, reverse=True)[:TOP_N]
    print(f"  🏆 Pool: {len(pool)} → unique: {len(unique)} → top {len(top)}")

    summarize_with_claude(top)

    output = {
        "date": date_str,
        "date_display": date_display,
        "generated_at": now.isoformat(),
        "top_tweets": top,
        "criteria": {
            "keyword_pools": [
                {"label": q["label"], "query": q["query"], "min_likes": q["min_likes"]}
                for q in SEARCH_QUERIES
            ],
            "kol_pools": [
                {"label": g["label"], "users": g["users"]}
                for g in KOL_GROUPS
            ],
            "top_n": TOP_N,
            "score_formula": "likes + retweets × 2",
        },
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ data.json saved — top {len(top)} tweets")

if __name__ == "__main__":
    main()
