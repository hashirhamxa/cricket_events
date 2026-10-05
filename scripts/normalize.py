#!/usr/bin/env python3
"""Script to normalize raw snapshots into canonical domain models."""

import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.parser import CricbuzzParser
from src.normalizer import CricketNormalizer
from src.config import RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = CricbuzzParser()
    normalizer = CricketNormalizer()

    raw_files = list(RAW_DIR.glob("latest_schedule_*.html"))
    if not raw_files:
        print("No raw HTML snapshots found in raw/. Run scripts/fetch_schedule.py first.")
        return

    all_raw_fixtures = []
    for rf in raw_files:
        cat = rf.stem.replace("latest_schedule_", "")
        html = rf.read_text(encoding="utf-8")
        fixtures = parser.parse_schedule_html(html, category_hint=cat)
        print(f"Parsed {len(fixtures)} fixtures from {rf.name}")
        all_raw_fixtures.extend(fixtures)

    matches, teams, series, venues = normalizer.process_all_raw_matches(all_raw_fixtures)
    print(f"\nNormalization Results:")
    print(f"  Matches: {len(matches)}")
    print(f"  Teams:   {len(teams)}")
    print(f"  Series:  {len(series)}")
    print(f"  Venues:  {len(venues)}")


if __name__ == "__main__":
    main()
