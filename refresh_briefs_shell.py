#!/usr/bin/env python3
"""
refresh_briefs_shell.py
Re-applies the current chrome — head, masthead, CSS, archive rail, scripts, end
mark, colophon — to every briefs/*.html snapshot.

Historical briefs are written once and never regenerated (their source data is
gone), so a change to styles.py / templates.py / scripts.py would otherwise only
reach the newest page. Anything that belongs to the publication rather than to the
day has to come through here: the keyword search box, ?q= highlighting, the
masthead lockup, the typefaces. Article content is left untouched; only the shell
is swapped.

The markup itself lives in generate_html.py and is imported, never duplicated —
two copies of the masthead would drift within a week.

CSS is no longer inlined: what gets swapped now is the one-line <link> to
styles.css, whose ?v= hash changes only when the CSS does. So an unchanged
stylesheet means an untouched archive, and a changed one is 129 one-line diffs
rather than 129 copies of the whole sheet.

Idempotent: safe to re-run after any shell change. Every anchor below must stay
matchable against its own output, which is why the head and interactive-script
patterns stop at a lookahead rather than at their own last line.
"""

import re
import sys
from pathlib import Path

import config
from generate_html import (
    COLOPHON_CENTER,
    COLOPHON_LEFT,
    endmark_block,
    head_block,
    issue_stats,
    load_archive,
    masthead_block,
    published_dates,
)
from scripts import ARCHIVE_RAIL_SCRIPT, INTERACTIVE_SCRIPT
from styles import stylesheet_link, write_stylesheet
from templates import archive_rail_html, empty_state

# "nothing to write" and "could not find where to write" used to be the same
# False, so a run where every anchor had gone stale still reported success.
CHANGED, UNCHANGED, SKIPPED = "changed", "unchanged", "skipped"

# Matches the inline <style> block the archive was written with AND the <link>
# that replaces it, so this stays runnable on a half-migrated archive and
# idempotent once every page has been converted.
STYLE_RE = re.compile(
    r"  (?:<style>\n.*?\n  </style>"
    r"|<link rel=\"stylesheet\" href=\"[^\"]*styles\.css\?v=[0-9a-f]+\">)\n",
    re.DOTALL,
)
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
# Stops at the theme bootstrap rather than at its own last <link>, so a head that
# grows or loses a font link still matches on the next run. The indentation is
# optional because the twelve oldest briefs predate the indented bootstrap.
HEAD_RE = re.compile(r"  <meta name=\"description\".*?(?=\n[ \t]*<script>)", re.DOTALL)
# Matches the pre-broadsheet nameplate too, so the 115 archived issues can be
# lifted onto the current one.
MASTHEAD_RE = re.compile(
    r"<header class=\"(?:masthead|bs-head)\">.*?</header>", re.DOTALL
)
MAIN_RE = re.compile(r"<main>.*?</main>", re.DOTALL)
INTERACTIVE_RE = re.compile(
    r"<script>\n  \(function\(\) \{\n"
    r"    document\.querySelectorAll\('dialog'\).*?\n</script>",
    re.DOTALL,
)
COLOPHON_LEFT_RE = re.compile(
    r"(<div class=\"colophon-left\">\n).*?(\n  </div>)", re.DOTALL
)
COLOPHON_CENTER_RE = re.compile(
    r"(<div class=\"colophon-center\">\n).*?(\n  </div>)", re.DOTALL
)
# The empty state is shell, not content: it is the same sentence on every empty
# day, so a copy or publish-hour change has to reach the archived empty days too.
# Optional — most pages have no empty state — so it stays out of `missing`.
EMPTY_RE = re.compile(r"<section class=\"empty\">.*?</section>", re.DOTALL)


def refresh(path: Path, issue_no: int | None = None) -> str:
    """Swap the shell on one brief. Returns CHANGED / UNCHANGED / SKIPPED."""
    html = path.read_text(encoding="utf-8")
    original = html
    date = path.stem
    issue_no = issue_no or 1

    # The ears report what the issue actually contains, read back out of the page
    # itself — the day's source data is long gone, and issue_stats() is the same
    # function generate() uses, so a refreshed page cannot disagree with a fresh one.
    found_main = MAIN_RE.search(html)
    stats = issue_stats(found_main.group(0)) if found_main else {}

    html, n_head = HEAD_RE.subn(
        lambda _: head_block(issue_no, date, "../"), html, count=1
    )
    html, n_masthead = MASTHEAD_RE.subn(
        lambda _: masthead_block(issue_no, date, stats, "../"), html, count=1
    )
    html, n_style = STYLE_RE.subn(lambda _: stylesheet_link("../"), html, count=1)
    html, n_rail = RAIL_RE.subn(lambda _: archive_rail_html(date, "../"), html, count=1)
    html, n_script = RAIL_SCRIPT_RE.subn(lambda _: ARCHIVE_RAIL_SCRIPT, html, count=1)
    html, n_inter = INTERACTIVE_RE.subn(lambda _: INTERACTIVE_SCRIPT, html, count=1)
    html, n_cl = COLOPHON_LEFT_RE.subn(
        lambda m: m.group(1) + COLOPHON_LEFT + m.group(2), html, count=1
    )
    html, n_cc = COLOPHON_CENTER_RE.subn(
        lambda m: m.group(1) + COLOPHON_CENTER + m.group(2), html, count=1
    )
    html = EMPTY_RE.sub(lambda _: empty_state().strip(), html, count=1)

    # The end mark is new furniture, so on a pre-brand page it has to be inserted
    # rather than swapped. Guarded so a second run does not stack two of them.
    if 'class="endmark"' not in html:
        html = html.replace("</main>\n", "</main>\n\n" + endmark_block() + "\n", 1)

    # Light is canon, so the pre-JS glyph is the sun. Cosmetic only — the
    # interactive script corrects it on load — so it is not a required anchor.
    html = html.replace(
        '<span class="theme-icon">☾</span>', '<span class="theme-icon">☀</span>'
    )

    missing = [
        name
        for name, n in (
            ("head", n_head),
            ("masthead", n_masthead),
            ("style", n_style),
            ("rail", n_rail),
            ("rail-script", n_script),
            ("interactive", n_inter),
            ("colophon-left", n_cl),
            ("colophon-center", n_cc),
        )
        if not n
    ]
    if missing:
        print(f"!! {path.name}: could not locate {', '.join(missing)} — skipped")
        return SKIPPED

    if html != original:
        path.write_text(html, encoding="utf-8")
        return CHANGED
    return UNCHANGED


def main():
    # Before the file check, not after: the <link> every page carries has to
    # resolve even on a run that refreshes nothing, and a fresh checkout with an
    # empty briefs/ is exactly the case that would otherwise ship no styles.css.
    write_stylesheet()

    files = sorted(Path(config.BRIEFS_DIR).glob("*.html"))
    if not files:
        print("no briefs to refresh")
        return 0
    rank = {d: i + 1 for i, d in enumerate(sorted(published_dates(load_archive())))}
    results = [refresh(f, rank.get(f.stem)) for f in files]
    changed = results.count(CHANGED)
    skipped = results.count(SKIPPED)

    # Printed before the verdict: refresh() writes each page as it goes, so on a
    # partial failure the tree is already half-updated and "how much of it moved"
    # is the first thing the operator needs.
    print(f"OK shell refreshed: {changed} changed / {len(files)} briefs")

    if skipped:
        # A skipped page keeps its old shell entirely — the anchors are the
        # contract between templates.py's markup and this file's regexes, and a
        # rename on either side breaks it silently.
        #
        # Non-zero, but the workflow deliberately does not stop on it. Now that
        # the CSS is one external file, ?v= is only a cache key: a stale page
        # still links styles.css and still gets the current sheet, so a missed
        # anchor costs the masthead, the rail and the search box — not the
        # stylesheet. That is worth a loud warning, not a day with no issue.
        print(
            f"!! {skipped} of {len(files)} briefs kept their old shell — "
            f"an anchor above no longer matches the markup it was written for. "
            f"Fix the pattern in this file, or revert the markup change."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
