"""Shared helpers for the daily-design-brief pipeline.

Small, dependency-light utilities extracted from the fetch/render scripts to
remove duplicated logic. Pure functions only — no network, no config coupling.
"""
import json
import os


def strip_code_fence(raw: str) -> str:
    """Strip a leading ```/```json markdown code fence from a Claude response.

    Mirrors the (previously duplicated) inline logic in the fetch scripts:
    returns the inner payload so ``json.loads`` can parse it.
    """
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return raw


def shape_tweet(t: dict) -> dict:
    """Reshape a normalized tweet dict into the compact form sent to Claude."""
    ctx = t.get("context") or {}
    out = {
        "id": t["id"],
        "author": t["author"],
        "likes": t["likes"],
        "retweets": t["retweets"],
        "replies": t["replies"],
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


def load_json(path: str, default=None):
    """Load JSON from ``path``; return ``default`` ({} if unset) on miss/error."""
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: str, data) -> None:
    """Write ``data`` as UTF-8 JSON (ensure_ascii=False, indent=2)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
