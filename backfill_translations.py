"""One-shot backfill: fill summary_zh for tweets in data.json.

Used when the daily run produced tweets but Anthropic was overloaded and
the curation/translation step fell back to likes-only ranking with empty
Chinese summaries. This script keeps the existing tweet order and only
fills in summary_zh, then regenerates briefs/*.md and briefs/*.html.
"""
import json
import os
import sys

DATA_FILE = "data.json"


def shape(t: dict) -> dict:
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


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[error] ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    import anthropic

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    tweets = data.get("top_tweets", [])
    missing = [t for t in tweets if not t.get("summary_zh")]
    print(f"Loaded {len(tweets)} tweets, {len(missing)} missing summary_zh")
    if not missing:
        print("Nothing to backfill.")
        return 0

    items = [shape(t) for t in missing]
    prompt = (
        "你是 Product & Design 策展編輯。以下是已選定的推文 JSON 陣列（內容可能是英文、繁體中文或簡體中文），"
        "請為每則寫 1-2 句繁體中文摘要。\n\n"
        "【推文額外欄位】\n"
        "- `quoted`：若這則是引用推文，原文在此（務必把引用原文的觀點納入摘要）\n"
        "- `replying_to`：若這則是回覆某則推文，被回覆的原文在此（摘要應交代脈絡）\n"
        "- `top_replies`：熱門回覆（按讚數排序），可用來統整下方的討論觀點\n\n"
        "【摘要規則】\n"
        "- 1-2 句繁體中文，聚焦核心觀點/takeaway\n"
        "- 若是引用/回覆，摘要要清楚交代「原 po 在說什麼」「這則怎麼回應」\n"
        "- 若 top_replies 內容值得，一句話帶上「討論中 XX 觀點也被提出」\n"
        "- 不要描述作者身分或互動數；語氣平實專業，避免行銷語\n\n"
        '【輸出】只輸出 JSON 陣列（不要 markdown code block、不要其他文字），'
        '格式：[{"id": "...", "summary_zh": "..."}]，順序維持輸入順序。\n\n'
        f"推文：\n{json.dumps(items, ensure_ascii=False)}"
    )

    client = anthropic.Anthropic(api_key=api_key)
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

    by_id = {p["id"]: p["summary_zh"] for p in picks if p.get("id") and p.get("summary_zh")}
    filled = 0
    for t in tweets:
        if not t.get("summary_zh") and t["id"] in by_id:
            t["summary_zh"] = by_id[t["id"]]
            filled += 1
    print(f"Filled {filled}/{len(missing)} summaries")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ {DATA_FILE} updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
