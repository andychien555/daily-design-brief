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


def claude_token_cost(usage, pricing: dict) -> tuple[int, int, float]:
    """Turn an Anthropic ``resp.usage`` into ``(input_tokens, output_tokens, usd_cost)``.

    ``pricing`` is a ``{"input": $/Mtok, "output": $/Mtok}`` dict (kept out of this
    module so utils stays config-decoupled — callers pass ``config.CLAUDE_PRICING``).
    """
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    cost = in_tok / 1_000_000 * pricing["input"] + out_tok / 1_000_000 * pricing["output"]
    return in_tok, out_tok, cost


def record_usage(date_str: str, label: str, log_file: str, *,
                 input_tokens: int = 0, output_tokens: int = 0,
                 audio_seconds: float = 0.0, cost_usd: float = 0.0) -> None:
    """Append one API call's tokens / audio-seconds / USD cost to a per-day usage log.

    Aggregates by ``date_str`` so the daily job's separate scripts
    (tweets / producthunt / podcast) accumulate into one running daily total.
    Best-effort: never raises into the caller — cost logging must not break the pipeline.
    """
    try:
        log = load_json(log_file, {})
        day = log.setdefault(date_str, {
            "input_tokens": 0, "output_tokens": 0,
            "audio_seconds": 0.0, "cost_usd": 0.0, "calls": [],
        })
        day["input_tokens"] += input_tokens
        day["output_tokens"] += output_tokens
        day["audio_seconds"] = round(day["audio_seconds"] + audio_seconds, 1)
        day["cost_usd"] = round(day["cost_usd"] + cost_usd, 6)
        day["calls"].append({
            "label": label, "input_tokens": input_tokens, "output_tokens": output_tokens,
            "audio_seconds": round(audio_seconds, 1), "cost_usd": round(cost_usd, 6),
        })
        save_json(log_file, log)
        detail = f"{audio_seconds:.0f}s 音檔" if audio_seconds else f"{input_tokens}in/{output_tokens}out"
        print(f"  💰 {label}: {detail} → ${cost_usd:.4f}（{date_str} 累計 ${day['cost_usd']:.4f}）")
    except Exception as e:
        print(f"  [warn] usage log failed: {e}")
