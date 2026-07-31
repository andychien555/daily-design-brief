#!/usr/bin/env python3
"""
refresh_briefs_shell.py
Re-applies the current chrome — CSS, archive rail markup, rail script — to every
briefs/*.html snapshot.

Historical briefs are written once and never regenerated (their source data is
gone), so a change to styles.py / templates.py / scripts.py would otherwise only
reach the newest page. Anything that must work across the whole archive — the
keyword search box, ?q= highlighting — needs this. Article content is left
untouched; only the shell is swapped.

Also migrates pre-assets briefs: CSS and JS used to be inlined into every
snapshot, so each one carried the same 48KB. Those blocks are replaced with
links to assets/shell.{css,js}.

Idempotent: safe to re-run after any shell change, and on already-migrated
pages (the inline blocks are simply absent).
"""

import re
import sys
from pathlib import Path

import config
from generate_html import ASSETS_DIR, load_archive, published_dates, write_shell_assets
from templates import archive_rail_html

BASE = "../"
CSS_LINK = f'  <link rel="stylesheet" href="{BASE}{ASSETS_DIR}/shell.css">\n'
JS_TAG = f'<script src="{BASE}{ASSETS_DIR}/shell.js"></script>\n'

STYLE_RE = re.compile(r"  <style>\n.*?\n  </style>\n", re.DOTALL)
RAIL_RE = re.compile(
    r"\n    <aside class=\"archive-rail\".*?"
    r"<div class=\"rail-backdrop\" aria-hidden=\"true\"></div>",
    re.DOTALL,
)
RAIL_SCRIPT_RE = re.compile(
    r"\n<script>\n\(function\(\) \{\n"
    r"  var aside = document\.querySelector\('\.archive-rail'\);.*?\n</script>\n",
    re.DOTALL,
)
# The dialog/theme/drawer script — folded into shell.js, so drop it outright.
INTERACTIVE_RE = re.compile(
    r"<script>\n  \(function\(\) \{\n"
    r"    document\.querySelectorAll\('dialog'\).*?\n</script>\n",
    re.DOTALL,
)
# The masthead issue number is derived from the archive, not from the day's
# content, so it is shell too — and it went stale once archive.json hit its
# 90-day cap and stopped growing.
ISSUE_NO_RE = re.compile(r'(Issue |<div class="meta-left">)№\d{3}')


def refresh(path: Path, issue_no: int | None = None) -> bool:
    html = path.read_text(encoding="utf-8")
    original = html

    html, n_style = STYLE_RE.subn(lambda _: CSS_LINK, html, count=1)
    html = INTERACTIVE_RE.sub("", html, count=1)
    html, n_script = RAIL_SCRIPT_RE.subn(lambda _: "\n" + JS_TAG, html, count=1)
    html, n_rail = RAIL_RE.subn(
        lambda _: archive_rail_html(path.stem, BASE), html, count=1
    )
    if issue_no:
        html = ISSUE_NO_RE.sub(lambda m: f"{m.group(1)}№{issue_no:03d}", html)

    # A migrated page has no inline block left to substitute, so the link
    # already being there counts as success — that is what makes this idempotent.
    missing = []
    if not (n_style or CSS_LINK in html):
        missing.append("stylesheet")
    if not (n_script or JS_TAG in html):
        missing.append("shell script")
    if not n_rail:
        missing.append("rail")
    if missing:
        print(f"!! {path.name}: could not locate {', '.join(missing)} — skipped")
        return False

    if html != original:
        path.write_text(html, encoding="utf-8")
        return True
    return False


def main():
    files = sorted(Path(config.BRIEFS_DIR).glob("*.html"))
    if not files:
        print("no briefs to refresh")
        return
    write_shell_assets()
    rank = {d: i + 1 for i, d in enumerate(sorted(published_dates(load_archive())))}
    changed = sum(refresh(f, rank.get(f.stem)) for f in files)
    print(f"OK shell refreshed: {changed} changed / {len(files)} briefs")


if __name__ == "__main__":
    sys.exit(main())
