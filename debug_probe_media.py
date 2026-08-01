#!/usr/bin/env python3
"""
debug_probe_media.py
One-off probe: does the 6551.io twitter_search response carry media
(extended_entities / photo URLs / video variants)?

Makes a SINGLE API call to stay cheap on quota. Prints the key structure of the
first few tweets plus any media-looking fields found anywhere in the payload.
Never prints the auth token.
"""

import json
import os
import re

import httpx

import config

TOKEN = os.environ["TWITTER_TOKEN"]
API_BASE = os.environ.get("TWITTER_API_BASE", config.TWEETS_API_BASE_DEFAULT)

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

MEDIA_HINTS = re.compile(
    r"media|photo|image|video|thumb|entities|variants|attachment|preview",
    re.I,
)


def walk(obj, path="", found=None, depth=0):
    """Collect paths whose key OR string value looks media-related."""
    if found is None:
        found = []
    if depth > 8:
        return found
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if MEDIA_HINTS.search(k):
                found.append((p, type(v).__name__, str(v)[:160]))
            walk(v, p, found, depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:3]):
            walk(v, f"{path}[{i}]", found, depth + 1)
    elif isinstance(obj, str):
        if "twimg.com" in obj or "video.twimg" in obj:
            found.append((path, "url", obj[:160]))
    return found


def main():
    url = f"{API_BASE}/open/twitter_search"
    payload = {
        "keywords": "design",
        "minLikes": 300,
        "maxResults": 10,
        "product": "Top",
        "lang": "en",
        "excludeReplies": True,
        "excludeRetweets": True,
    }
    print(f"POST {url}")
    print(f"payload: {json.dumps(payload)}\n")

    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=HEADERS, json=payload)

    print(f"HTTP {resp.status_code}")
    if resp.status_code != 200:
        print("body:", resp.text[:800])
        return

    data = resp.json()
    if isinstance(data, dict):
        print("top-level dict keys:", list(data.keys()))
        tweets = []
        for key in ("tweets", "data", "result", "results", "items"):
            val = data.get(key)
            if isinstance(val, list):
                tweets = val
                print(f"tweet list found under: '{key}'")
                break
    else:
        tweets = data if isinstance(data, list) else []
        print("top-level is a list")

    print(f"tweets returned: {len(tweets)}\n")
    if not tweets:
        print("EMPTY RESULT — cannot determine media support.")
        return

    t0 = tweets[0]
    print("=" * 70)
    print("ALL KEYS on tweet[0]:")
    print("=" * 70)
    for k, v in sorted(t0.items()):
        print(f"  {k:<28} {type(v).__name__:<8} {str(v)[:90]}")

    print()
    print("=" * 70)
    print("MEDIA-LOOKING PATHS across first 5 tweets:")
    print("=" * 70)
    hits = []
    for i, t in enumerate(tweets[:5]):
        for p, ty, val in walk(t, f"tweet[{i}]"):
            hits.append((p, ty, val))
    if hits:
        for p, ty, val in hits:
            print(f"  {p}\n      ({ty}) {val}")
    else:
        print("  NONE — no media/entities/twimg URLs anywhere in the payload.")

    print()
    print("=" * 70)
    print("RAW tweet[0] (full JSON):")
    print("=" * 70)
    print(json.dumps(t0, ensure_ascii=False, indent=2)[:6000])


if __name__ == "__main__":
    main()
