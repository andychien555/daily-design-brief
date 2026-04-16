#!/usr/bin/env python3
"""
fetch_tweets.py
Fetches trending Product & Design tweets via 6551.io API
Saves results to data.json for use by generate_html.py
"""

import os
import json
import httpx
from datetime import datetime, timezone, timedelta

TWITTER_TOKEN = os.environ["TWITTER_TOKEN"]
API_BASE = os.environ.get("TWITTER_API_BASE", "https://ai.6551.io")

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
        "label": "Design Systems",
        "query": "design system Figma component",
        "min_likes": 150,
    },
    {
        "label": "Product Management",
        "query": "product management roadmap strategy",
        "min_likes": 200,
    },
    {
        "label": "Design Thinking",
        "query": "design thinking user research insight",
        "min_likes": 150,
    },
]

def search_tweets(query: str, min_likes: int, max_rows: int = 10) -> list[dict]:
    """Call 6551.io search_twitter_advanced endpoint."""
    url = f"{API_BASE}/v1/twitter/search/advanced"
    payload = {
        "query": query,
        "min_likes": min_likes,
        "max_rows": max_rows,
        "lang": "en",
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=HEADERS, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("tweets", data) if isinstance(data, dict) else data
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

def normalize(tweet: dict) -> dict:
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
    }

def main():
    tz_taipei = timezone(timedelta(hours=8))
    now = datetime.now(tz_taipei)
    date_str = now.strftime("%Y-%m-%d")
    date_display = now.strftime("%Y 年 %m 月 %d 日")

    print(f"📰 Fetching tweets for {date_str} ...")

    sections = []
    for cfg in SEARCH_QUERIES:
        print(f"  🔍 {cfg['label']}: {cfg['query']}")
        raw = search_tweets(cfg["query"], cfg["min_likes"])
        top = pick_top(dedupe(raw), n=5)
        normalized = [normalize(t) for t in top]
        if normalized:
            sections.append({
                "label": cfg["label"],
                "tweets": normalized,
            })
            print(f"     → {len(normalized)} tweets")
        else:
            print(f"     → (no results)")

    output = {
        "date": date_str,
        "date_display": date_display,
        "generated_at": now.isoformat(),
        "sections": sections,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ data.json saved — {sum(len(s['tweets']) for s in sections)} tweets across {len(sections)} sections")

if __name__ == "__main__":
    main()
