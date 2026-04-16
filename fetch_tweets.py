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

# Search queries — product & design topics, last 3 days, likes ≥ 100
SEARCH_QUERIES = [
    {
        "label": "Product Design",
        "query": "product design",
        "min_likes": 100,
    },
    {
        "label": "Product Management",
        "query": "product management",
        "min_likes": 100,
    },
    {
        "label": "AI Tool",
        "query": "AI tool",
        "min_likes": 100,
    },
    {
        "label": "Vibe Coding",
        "query": "vibe coding",
        "min_likes": 100,
    },
]
SINCE_DAYS = 3


def search_tweets(query: str, min_likes: int, max_rows: int = 30, since_date: str | None = None) -> list[dict]:
    """Call 6551.io /open/twitter_search endpoint.

    Uses 'Latest' product when since_date is given so we get recent tweets
    in the window (Top would return all-time popular, which conflicts with
    a recent date filter and returns nothing).
    """
    url = f"{API_BASE}/open/twitter_search"
    payload = {
        "keywords": query,
        "minLikes": min_likes,
        "maxResults": max_rows,
        "product": "Latest" if since_date else "Top",
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

def fetch_tweet_detail(tweet_id: str) -> dict:
    """Fetch tweet detail including quotedStatus / replyStatus context."""
    url = f"{API_BASE}/open/twitter_tweet_by_id"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=HEADERS, json={"twId": tweet_id})
            if resp.status_code >= 400:
                return {}
            data = resp.json()
            if isinstance(data, dict):
                inner = data.get("data")
                if isinstance(inner, dict):
                    return inner
                return data
    except Exception as e:
        print(f"  [warn] tweet_by_id {tweet_id} failed: {e}")
    return {}

def fetch_top_replies(conversation_id: str, max_results: int = 5) -> list[dict]:
    """Best-effort: find top replies to a tweet via conversationId search.
    Returns [] if the API doesn't support this filter."""
    if not conversation_id:
        return []
    url = f"{API_BASE}/open/twitter_search"
    payload = {
        "conversationId": conversation_id,
        "maxResults": 20,
        "product": "Top",
        "lang": "en",
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=HEADERS, json=payload)
            if resp.status_code >= 400:
                return []
            data = resp.json()
            if isinstance(data, dict):
                for k in ("tweets", "data", "result", "results", "items"):
                    v = data.get(k)
                    if isinstance(v, list):
                        actual_replies = [
                            r for r in v
                            if isinstance(r, dict)
                            and (r.get("id") or r.get("tweet_id")) != conversation_id
                            and (r.get("conversationId") == conversation_id or r.get("inReplyToStatusId") == conversation_id)
                        ]
                        if not actual_replies and v:
                            print(f"  [info] conversationId filter not honored (got {len(v)} unrelated tweets for {conversation_id})")
                            return []
                        replies = [
                            {
                                "author": extract_author(r),
                                "text": r.get("text") or r.get("full_text", ""),
                                "likes": r.get("favoriteCount") or 0,
                            }
                            for r in actual_replies
                        ]
                        replies.sort(key=lambda x: x["likes"], reverse=True)
                        return replies[:max_results]
    except Exception as e:
        print(f"  [warn] replies for {conversation_id} failed: {e}")
    return []

def extract_author(obj: dict) -> str:
    """Try multiple known variants for an author/screen-name field."""
    if not isinstance(obj, dict):
        return ""
    for key in ("userScreenName", "username", "screen_name", "screenName"):
        v = obj.get(key)
        if v:
            return v
    user = obj.get("user")
    if isinstance(user, dict):
        for key in ("screenName", "screen_name", "username", "userScreenName"):
            v = user.get(key)
            if v:
                return v
    return ""

def enrich_with_context(tweets: list[dict]) -> None:
    """For each tweet, fetch the quoted/replied-to tweet and top replies (if available).
    Mutates tweets in place, adding a 'context' dict."""
    quote_schema_logged = False
    reply_schema_logged = False
    for t in tweets:
        ctx = {"quoted_text": "", "quoted_author": "", "replied_text": "", "replied_author": "", "top_replies": []}
        detail = fetch_tweet_detail(t["id"])
        q = detail.get("quotedStatus") if isinstance(detail, dict) else None
        if isinstance(q, dict):
            if not quote_schema_logged:
                print(f"  🔬 quotedStatus keys: {sorted(q.keys())[:25]}")
                quote_schema_logged = True
            ctx["quoted_text"] = q.get("text") or q.get("full_text", "")
            ctx["quoted_author"] = extract_author(q)
        r = detail.get("replyStatus") if isinstance(detail, dict) else None
        if isinstance(r, dict):
            if not reply_schema_logged:
                print(f"  🔬 replyStatus keys: {sorted(r.keys())[:25]}")
                reply_schema_logged = True
            ctx["replied_text"] = r.get("text") or r.get("full_text", "")
            ctx["replied_author"] = extract_author(r)
        # Note: 6551 /open/twitter_search does NOT honor conversationId filter,
        # so we can't reliably pull real replies. Leave top_replies empty until
        # a supported endpoint exists.
        t["context"] = ctx
        badges = []
        if ctx["quoted_text"]:
            badges.append(f"↩quote @{ctx['quoted_author'] or '?'}")
        if ctx["replied_text"]:
            badges.append(f"↩reply to @{ctx['replied_author'] or '?'}")
        if ctx["top_replies"]:
            badges.append(f"{len(ctx['top_replies'])} replies")
        if badges:
            print(f"     · {t['id']} → {', '.join(badges)}")

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

    def shape(t: dict) -> dict:
        ctx = t.get("context") or {}
        out = {
            "id": t["id"], "author": t["author"],
            "likes": t["likes"], "retweets": t["retweets"], "replies": t["replies"],
            "text": t["text"],
        }
        if ctx.get("quoted_text"):
            out["quoted"] = {"author": ctx["quoted_author"], "text": ctx["quoted_text"]}
        if ctx.get("replied_text"):
            out["replying_to"] = {"author": ctx["replied_author"], "text": ctx["replied_text"]}
        if ctx.get("top_replies"):
            out["top_replies"] = [
                {"author": r["author"], "text": r["text"], "likes": r["likes"]}
                for r in ctx["top_replies"]
            ]
        return out

    items = [shape(t) for t in candidates]
    prompt = (
        "你是 Product & Design 策展編輯。以下是候選英文推文 JSON 陣列，請從中挑出 "
        f"**最多 {top_n} 則** 對 product designer / PM 讀者最有價值的內容，並為每則寫 1-2 句繁體中文摘要。\n\n"
        "【推文額外欄位】\n"
        "- `quoted`：若這則是引用推文，原文在此（務必把引用原文的觀點納入摘要）\n"
        "- `replying_to`：若這則是回覆某則推文，被回覆的原文在此（摘要應交代脈絡）\n"
        "- `top_replies`：熱門回覆（按讚數排序），可用來統整下方的討論觀點\n\n"
        "【過濾規則】務必排除：\n"
        "1. 純廣告、招聘文（除非 JD 本身有洞見，例如 Ramp 那種）\n"
        "2. 與產品設計/PM 無關（crypto 炒幣、體育 logo、政治議題等）\n"
        "3. Meme / 搞笑但沒內容\n\n"
        "【排序偏好】\n"
        "- 有觀點的原創內容 > 資訊整理/轉述\n"
        "- 過濾後依 likes 高低為主要排序\n\n"
        "【摘要規則】\n"
        "- 1-2 句繁體中文，聚焦核心觀點/takeaway\n"
        "- 若是引用/回覆，摘要要清楚交代「原 po 在說什麼」「這則怎麼回應」\n"
        "- 若有 top_replies 且內容值得，一句話帶上「討論中 XX 觀點也被提出」這類統整\n"
        "- 不要描述作者身分或互動數；語氣平實專業，避免行銷語\n\n"
        '【輸出】只輸出 JSON 陣列（不要 markdown code block、不要其他文字），'
        '格式：[{"id": "...", "summary_zh": "..."}]，順序即為最終排名。\n\n'
        f"候選推文：\n{json.dumps(items, ensure_ascii=False)}"
    )

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-5",
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

    enrich_limit = min(len(candidates), 15)
    print(f"  🧵 Enriching top {enrich_limit} candidates with quote/reply context ...")
    enrich_with_context(candidates[:enrich_limit])

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
