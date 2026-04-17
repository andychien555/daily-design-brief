#!/usr/bin/env python3
"""
generate_md.py
Reads data.json and writes a Markdown file to briefs/YYYY-MM-DD.md.
The MD serves as both human-readable archive and summary cache for future runs.
"""

import json
from pathlib import Path


def load_data() -> dict:
    with open("data.json", encoding="utf-8") as f:
        return json.load(f)


def fmt(n: int) -> str:
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def tweet_block(tweet: dict, rank: int) -> str:
    tid = tweet.get("id", "")
    author = tweet.get("author", "unknown")
    name = tweet.get("name", author)
    text = tweet.get("text", "")
    summary = tweet.get("summary_zh", "")
    likes = tweet.get("likes", 0)
    retweets = tweet.get("retweets", 0)
    replies = tweet.get("replies", 0)
    source = tweet.get("source", "")
    url = tweet.get("url", "")
    ctx = tweet.get("context") or {}

    lines = [f"<!-- tweet_id: {tid} -->"]
    lines.append(f"### #{rank} · [{name} (@{author})]({url})")
    if summary:
        lines.append(f"> {summary}")
    lines.append("")
    lines.append(text)
    lines.append("")

    if ctx.get("quoted_text"):
        qa = ctx.get("quoted_author", "")
        label = f"@{qa}" if qa else "原文"
        lines.append(f"**引用 {label}：**")
        lines.append(f"> {ctx['quoted_text']}")
        lines.append("")

    if ctx.get("replied_text"):
        ra = ctx.get("replied_author", "")
        label = f"@{ra}" if ra else "原文"
        lines.append(f"**回覆 {label}：**")
        lines.append(f"> {ctx['replied_text']}")
        lines.append("")

    stats = f"♥ {fmt(likes)} · ↻ {fmt(retweets)} · 💬 {fmt(replies)}"
    if source:
        stats += f" · `{source}`"
    lines.append(stats)
    lines.append("")
    return "\n".join(lines)


def generate_md(data: dict) -> str:
    date = data.get("date", "")
    date_display = data.get("date_display", date)
    generated_at = data.get("generated_at", "")[:16].replace("T", " ")
    top = data.get("top_tweets") or []
    criteria = data.get("criteria") or {}

    sections = []

    sections.append(f"# Daily Design Brief — {date_display}")
    sections.append(f"*Generated: {generated_at} · {len(top)} tweets*\n")

    sections.append("---\n")

    for i, t in enumerate(top, 1):
        sections.append(tweet_block(t, i))
        sections.append("---\n")

    kw = criteria.get("keyword_pools", [])
    if kw:
        sections.append("## 篩選標準\n")
        sections.append(f"- 時間窗：最近 {criteria.get('since_days', 3)} 天")
        sections.append(f"- 排序：{criteria.get('score_formula', 'likes')}")
        sections.append(f"- Top {criteria.get('top_n', 10)}")
        sections.append("")
        sections.append("| 主題 | 查詢字 | likes 門檻 |")
        sections.append("|---|---|---|")
        for k in kw:
            sections.append(f"| {k['label']} | `{k['query']}` | ≥ {k['min_likes']} |")
        sections.append("")
        rules = criteria.get("claude_filter_rules", [])
        if rules:
            sections.append("**Claude 過濾：** " + " / ".join(rules))
            sections.append("")

    return "\n".join(sections)


def main():
    data = load_data()
    md = generate_md(data)

    briefs = Path("briefs")
    briefs.mkdir(exist_ok=True)
    out = briefs / f"{data['date']}.md"
    out.write_text(md, encoding="utf-8")
    print(f"✅ {out} saved ({len(md)} chars)")


if __name__ == "__main__":
    main()
