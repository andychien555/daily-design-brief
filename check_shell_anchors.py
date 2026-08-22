#!/usr/bin/env python3
"""
check_shell_anchors.py
Fails when refresh_briefs_shell.py's regexes stop matching the markup that
generate_html.py emits.

Those eight anchors are an unwritten contract between two files. Rename a class
in templates.py and nothing breaks at the point of the change: the next CI run
skips the archive instead, and since that run deliberately no longer fails the
workflow — a stale shell must not cost a day's issue — the only signal is a
warning annotation somebody has to go and read. This is what catches the drift
at the moment the markup moves.

The assertion is stronger than "every regex found something". refresh()
returning UNCHANGED means each anchor located its block *and* the replacement
came out byte-identical to what generate() had just written. A CHANGED verdict
means the two files disagree about the same markup — which is the drift, one
step before an anchor stops matching altogether.

Content does not enter into it: the anchors frame the page — head, masthead,
stylesheet, rail, scripts, colophon — so a day with no tweets exercises them as
fully as a busy one. What the cases below vary is the two shapes a real page
takes (an empty day and a full one) plus the legacy inline <style> that
STYLE_RE still claims to convert.
"""

import json
import sys
import tempfile
from pathlib import Path

import generate_html as g
import refresh_briefs_shell as r
import styles

EMPTY_DAY = {"date": "2026-01-01", "generated_at": "2026-01-01T06:00:00+08:00"}


def verdict(html: str, date: str, issue_no: int = 1) -> str:
    """Run one page through refresh() in a scratch dir. Returns its verdict."""
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / f"{date}.html"
        path.write_text(html, encoding="utf-8")
        return r.refresh(path, issue_no)


def case_generated(name: str, data: dict) -> tuple[str, str, str]:
    """A page straight out of generate() must survive refresh() untouched.

    Both sides take their issue number from issue_number() so that this case
    tests the markup contract and nothing else; whether the two production
    paths agree on that number is its own case below.
    """
    archive: list = []
    html = g.generate(data, archive=archive, base_path="../")
    issue_no = g.issue_number(data["date"], archive)
    return name, verdict(html, data["date"], issue_no), r.UNCHANGED


def case_issue_numbering() -> tuple[str, str, str]:
    """The masthead's № comes from two different mechanisms.

    generate() calls issue_number(), which ranks the date among the published
    ones. refresh() is *told* its number: main() builds a rank map over the
    dates it finds and passes rank.get(stem), falling back to 1 when a date is
    missing from the map. Two routes to one number is two chances to disagree,
    and the ears of every archived page are where it would surface.
    """
    archive = g.load_archive()
    dates = sorted(g.published_dates(archive))
    rank = {d: i + 1 for i, d in enumerate(dates)}
    off = [d for d in dates if rank[d] != g.issue_number(d, archive)]
    got = f"{len(off)} of {len(dates)} disagree" if off else f"all {len(dates)} agree"
    return "issue numbering, both paths", got, f"all {len(dates)} agree"


def case_legacy_inline() -> tuple[str, str, str]:
    """The pre-extraction archive shape.

    STYLE_RE matches the old inline <style> as well as the <link> that replaced
    it, so that the archive could be converted in place. Nothing in briefs/ is
    in that shape any more, which is exactly why the branch needs a test: there
    is no longer a real page left to notice it breaking.
    """
    html = g.generate(EMPTY_DAY, archive=[], base_path="../")
    link = styles.stylesheet_link("../")
    assert link in html, "stylesheet_link() no longer appears in generate() output"
    inline = "  <style>\n" + styles.CSS + "\n  </style>\n"
    issue_no = g.issue_number(EMPTY_DAY["date"], [])
    return (
        "legacy inline <style>",
        verdict(html.replace(link, inline), EMPTY_DAY["date"], issue_no),
        r.CHANGED,
    )


def main() -> int:
    cases = [case_generated("empty day", EMPTY_DAY)]

    # The live data file, when there is one: the shape actually being published
    # today, ears and all. Absent on a fresh checkout, so it is additive.
    try:
        live = json.loads(Path("data.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("-- data.json unreadable; skipping the live-shape case")
    else:
        cases.append(case_generated(f"live data.json ({live.get('date', '?')})", live))

    cases.append(case_legacy_inline())
    cases.append(case_issue_numbering())

    failed = 0
    for name, got, want in cases:
        ok = got == want
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {got} (expected {want})")

    if failed:
        print(
            f"\n!! {failed} of {len(cases)} shell-anchor checks failed.\n"
            f"   An anchor in refresh_briefs_shell.py no longer lines up with the\n"
            f"   markup in generate_html.py / templates.py. Fix the regex there, or\n"
            f"   revert the markup change — otherwise the whole archive silently\n"
            f"   stops receiving shell updates."
        )
        return 1

    print(f"\nOK {len(cases)} shell-anchor checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
