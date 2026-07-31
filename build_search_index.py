#!/usr/bin/env python3
"""
build_search_index.py
Rebuilds search-index.json from every briefs/*.html snapshot.

The site is static, so keyword search runs entirely in the browser against this
index. Parsing the rendered HTML (rather than data.json, which only holds the
current day) means the whole archive is covered by one code path — no separate
backfill, no incremental drift.
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone, timedelta

import config
from utils import load_json, save_json

OUT_FILE = "search-index.json"

# Wrapper elements that open a searchable block, mapped to the block kind.
# ``nl-card`` superseded ``yt-brief`` for articles in 4431e75; briefs written
# before that still use the old wrapper, so both stay mapped.
BLOCK_CLASSES = {
    "lead": "tweet",
    "card": "tweet",
    "ph-card": "product",
    "nl-card": "article",
    "yt-brief": "brief",  # legacy podcast or article — resolved from its kicker
}

# Elements inside a block whose text we keep, mapped to a field name.
FIELD_CLASSES = {
    "lead-summary": "summary",
    "lead-text": "text",
    "card-summary": "summary",
    "card-text": "text",
    "author-name": "name",
    "author-handle": "handle",
    "ph-title": "title",
    "ph-tagline": "tagline",
    "ph-summary": "summary",
    "nl-headline": "title",
    "nl-lead": "summary",
    # The body div carries both classes; map each so whichever the class set
    # yields first lands in the same field.
    "nl-body": "body",
    "nl-name": "name",
    "nl-handle": "handle",
    "yt-kicker": "kicker",
    "yt-title": "title",
    "yt-body": "body",
    "yt-channel": "channel",
}

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}

# Text across an inline tag boundary is one run of words; block tags separate.
INLINE_TAGS = {"a", "b", "code", "em", "i", "mark", "small", "span",
               "strong", "sub", "sup", "u"}


def _clean(s: str) -> str:
    for glyph in ("↗", "▶", "✔"):
        s = s.replace(glyph, " ")
    return re.sub(r"\s+", " ", s).strip()


class BriefParser(HTMLParser):
    """Collects searchable blocks out of one rendered brief."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self.stack: list[dict] = []
        self.block = None
        self.field = None
        self.buf: list[str] = []

    # ---- block/field bookkeeping ----------------------------------------
    def _open_field(self, name: str):
        self.field = name
        self.buf = []

    def _close_field(self):
        if self.block is not None and self.field:
            text = _clean("".join(self.buf))
            if text:
                prev = self.block.get(self.field)
                self.block[self.field] = f"{prev} {text}" if prev else text
        self.field = None
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        classes = set((dict(attrs).get("class") or "").split())
        frame = {"tag": tag, "block": False, "field": False}

        if self.block is None:
            for cls, kind in BLOCK_CLASSES.items():
                if cls in classes:
                    self.block = {"kind": kind}
                    frame["block"] = True
                    break
        elif not self.field:
            for cls in classes:
                if cls in FIELD_CLASSES:
                    self._open_field(FIELD_CLASSES[cls])
                    frame["field"] = True
                    break

        self.stack.append(frame)

    def handle_startendtag(self, tag, attrs):
        if self.field and tag not in INLINE_TAGS:
            self.buf.append(" ")

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        # Pop back to the matching open tag, closing anything left dangling.
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                for frame in reversed(self.stack[i:]):
                    if frame["field"]:
                        self._close_field()
                    if frame["block"]:
                        self.blocks.append(self.block)
                        self.block = None
                del self.stack[i:]
                return
        # Stray close tag — ignore.

    def handle_data(self, data):
        if self.field:
            self.buf.append(data)

    def close(self):
        super().close()
        while self.stack:
            frame = self.stack.pop()
            if frame["field"]:
                self._close_field()
            if frame["block"]:
                self.blocks.append(self.block)
                self.block = None


def _entry(block: dict) -> dict | None:
    """Normalise one parsed block into a compact index entry.

    k = kind, t = headline text, b = body text, m = byline. Short keys keep the
    published JSON small; the whole file is fetched by the browser on first use.
    """
    kind = block.get("kind")

    if kind == "tweet":
        summary = block.get("summary", "")
        text = block.get("text", "")
        if not (summary or text):
            return None
        name = block.get("name", "")
        handle = block.get("handle", "")
        return {
            "k": "tweet",
            "t": summary or text,
            "b": text if summary else "",
            "m": _clean(f"{name} {handle}"),
        }

    if kind == "product":
        title = block.get("title", "")
        if not title:
            return None
        body = _clean(f"{block.get('tagline', '')} {block.get('summary', '')}")
        return {"k": "product", "t": title, "b": body, "m": "Product Hunt"}

    if kind == "article":
        title = block.get("title", "")
        body = _clean(f"{block.get('summary', '')} {block.get('body', '')}")
        if not (title or body):
            return None
        return {
            "k": "article",
            "t": title,
            "b": body,
            "m": _clean(f"{block.get('name', '')} {block.get('handle', '')}"),
        }

    if kind == "brief":
        title = block.get("title", "")
        body = block.get("body", "")
        if not (title or body):
            return None
        # Legacy wrapper carried both kinds; the kicker is the only tell.
        kicker = block.get("kicker", "")
        sub = "article" if "UX" in kicker else "podcast"
        return {"k": sub, "t": title, "b": body, "m": block.get("channel", "")}

    return None


def parse_brief(path: Path) -> list[dict]:
    parser = BriefParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    entries = [_entry(b) for b in parser.blocks]
    return [e for e in entries if e]


def date_display(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return f"{d.year} 年 {d.month:02d} 月 {d.day:02d} 日"
    except ValueError:
        return date_str


def build() -> dict:
    briefs_dir = Path(config.BRIEFS_DIR)
    files = sorted(briefs_dir.glob("*.html"))

    archive = load_json(config.ARCHIVE_FILE, default=[])
    archive_dates = {e["date"] for e in archive if e.get("date")}
    brief_dates = {f.stem for f in files}
    # Same ranking rule as generate_html.issue_number so issue numbers line up.
    ordered = sorted(archive_dates | brief_dates)
    rank = {d: i + 1 for i, d in enumerate(ordered)}

    days = []
    for f in files:
        date = f.stem
        items = parse_brief(f)
        if not items:
            continue
        days.append({
            "d": date,
            "dd": date_display(date),
            "no": rank.get(date, 1),
            "items": items,
        })

    days.sort(key=lambda x: x["d"], reverse=True)
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    return {"generated_at": now, "days": days}


def main():
    index = build()
    save_json(OUT_FILE, index)
    items = sum(len(d["items"]) for d in index["days"])
    size = Path(OUT_FILE).stat().st_size
    print(f"OK {OUT_FILE}: {len(index['days'])} days, {items} items, {size/1024:.0f} KB")


if __name__ == "__main__":
    main()
