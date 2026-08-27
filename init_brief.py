#!/usr/bin/env python3
"""
init_brief.py
Starts the day's data.json: stamps today, starts empty.

Until X ingestion was paused, fetch_tweets.py opened every run by *replacing*
data.json — it was the only fetcher that wrote the whole file rather than
merging one key into it, so it was also the thing that stamped the date and
cleared yesterday out. Dropping that step without this one would have left the
remaining fetchers (podcast, 好文, Product Hunt) merging today's sections into
yesterday's file: generate_html.py reads data["date"], so every issue from then
on would have carried the date of the last day tweets ran, and any fetcher that
failed would have silently reprinted the previous day's section.

This does only that part. It runs first in daily.yml, ahead of every fetcher.
Restoring the tweet step does not mean removing this one — fetch_tweets.py
stamps the same three fields from the same helper.
"""
from datetime import datetime

import config
from utils import brief_skeleton, save_json


def main():
    data = brief_skeleton(datetime.now(config.TPE))
    save_json(config.DATA_FILE, data)
    print(f"OK data.json initialised for {data['date']}")


if __name__ == "__main__":
    main()
