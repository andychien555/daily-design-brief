#!/usr/bin/env python3
"""
check_podcast_dedupe.py
Fails when fetch_podcast.py's cross-day dedupe can drop a section out of an
issue that was already published.

The dedupe compares an episode's first_shown against "today". That comparison
is only safe while "today" means *the issue being written* — the date
init_brief.py stamps into data.json each morning and generate_html.py reads
back when it decides which briefs/<date>.html to rebuild. Reading a wall clock
instead looks identical for most of the day and diverges exactly when the
22:00 podcast check runs late, which GitHub's scheduler does often: 00:45 on
2026-08-29, 01:28 on 2026-08-30. On both nights the mismatch deleted an
episode that had already been fetched, transcribed and summarised — the dedupe
called it "already shown", generate_html.py rewrote the evening's own page
without it, and the next morning skipped it too because first_shown was
stamped. Fourteen episodes went that way between June and August 2026.

So the cases below all run the pipeline against a frozen clock, with the
network and both APIs replaced. Three of the four put the clock past midnight
while data.json still holds the previous issue — the state that used to be
destructive — and assert the two things that keep it harmless:

  - a section the published issue already carried survives the run, whatever
    happens upstream (held back, aged out, or lost to an error);
  - an episode seen for the first time after midnight is cached but neither
    printed into last night's issue nor stamped, so the morning run — which
    is what readers actually open — still has it to show.

The fourth is an ordinary same-day run, there to prove the guard did not cost
the dedupe its original job: one episode, one issue, no repeats.
"""

import json
import sys
import tempfile
import types
from datetime import datetime
from pathlib import Path

# fetch_podcast imports httpx at module scope for the RSS and audio fetches.
# Nothing here touches the network, and check.yml installs nothing on purpose,
# so a stub keeps this stdlib-only and fast.
sys.modules.setdefault("httpx", types.ModuleType("httpx"))

import config
import fetch_podcast as fp

TPE = config.TPE
YESTERDAY, TODAY = "2026-08-29", "2026-08-30"
SHOW = "股癌 Gooaye"


def episode(ep_id: str, title: str, published: str) -> dict:
    return {
        "episode_id": ep_id,
        "title": title,
        "url": f"https://example.invalid/{ep_id}",
        "published": published,
        "channel": SHOW,
        "transcript_source": "Podcast 音檔 · Whisper",
        "summary_md": f"## {title}",
    }


OLD = episode("ep-old", "EP691", YESTERDAY)   # printed in yesterday's issue
NEW = episode("ep-new", "EP692", TODAY)       # just went up


def run_pipeline(issue_date: str, wall: str, latest: dict, state: dict) -> tuple[list, str]:
    """Run main() in a temp dir with the clock, feed and both APIs replaced."""
    tmp = Path(tempfile.mkdtemp())
    fp.STATE_PATH, fp.DATA_PATH = str(tmp / "state.json"), str(tmp / "data.json")
    fp.PODCASTS = [{"name": SHOW, "itunes_id": "x", "rss": "https://example.invalid/rss"}]

    (tmp / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (tmp / "data.json").write_text(json.dumps({
        "date": issue_date,
        "podcast_briefs": [dict(OLD, first_shown=YESTERDAY)],
    }), encoding="utf-8")

    key = f"x:{latest['episode_id']}"
    published_dt = datetime.strptime(latest["published"], "%Y-%m-%d").replace(tzinfo=TPE)
    fp.resolve_latest_episode = lambda pod: {
        "state_key": key,
        "episode_id": latest["episode_id"],
        "title": latest["title"],
        "url": latest["url"],
        "published": latest["published"],
        "published_dt": published_dt,
        "channel": pod["name"],
        "mp3_url": "https://example.invalid/audio.mp3",
    }

    def fake_process(pod, st, force):
        # Stands in for download → Whisper → Claude, which all land in the cache
        # before main() ever decides whether to print the episode.
        st[key] = dict(latest)
        fp.save_state(st)
        return dict(latest)

    fp.process_one = fake_process
    fp._recent = lambda dt: True

    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.strptime(wall, "%Y-%m-%d").replace(tzinfo=tz)

    fp.datetime = FrozenClock
    try:
        fp.main()
    finally:
        fp.datetime = datetime

    data = json.loads((tmp / "data.json").read_text(encoding="utf-8"))
    saved = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
    return ([b["title"] for b in data.get("podcast_briefs", [])],
            saved.get(key, {}).get("first_shown"))


CASES = [
    # (name, issue date on disk, wall clock, feed's latest, cache, expected titles, expected stamp)
    ("late run, first sighting: cached for the morning, last night's issue intact",
     YESTERDAY, TODAY, NEW, {"x:ep-old": dict(OLD, first_shown=YESTERDAY)},
     ["EP691"], None),
    ("late run, feed unchanged: the published issue is reproduced as-is",
     YESTERDAY, TODAY, OLD, {"x:ep-old": dict(OLD, first_shown=YESTERDAY)},
     ["EP691"], YESTERDAY),
    ("morning run: picks up what the late run cached, and stamps it",
     TODAY, TODAY, NEW, {"x:ep-new": dict(NEW)},
     ["EP692"], TODAY),
    ("same-day rerun: no repeat, and the section stays on the page",
     TODAY, TODAY, NEW, {"x:ep-new": dict(NEW, first_shown=TODAY)},
     ["EP692"], TODAY),
]


def main() -> int:
    failures = 0
    for name, issue_date, wall, latest, state, want_titles, want_stamp in CASES:
        titles, stamp = run_pipeline(issue_date, wall, latest, dict(state))
        ok = titles == want_titles and stamp == want_stamp
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
        if not ok:
            print(f"       issue {issue_date}, clock {wall}, feed {latest['title']}")
            print(f"       printed {titles} (expected {want_titles})")
            print(f"       first_shown {stamp} (expected {want_stamp})")

    if failures:
        print(f"\n{failures} of {len(CASES)} podcast dedupe checks failed")
        return 1
    print(f"\nOK {len(CASES)} podcast dedupe checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
