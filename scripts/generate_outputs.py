#!/usr/bin/env python3
"""Script to generate all output JSON files from normalized collections."""

import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config import RAW_DIR
from src.parser import CricbuzzParser
from src.normalizer import CricketNormalizer
from src.generator import OutputGenerator
from src.storage import DatasetStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    storage = DatasetStorage()
    parser = CricbuzzParser()
    normalizer = CricketNormalizer()
    generator = OutputGenerator(storage)

    raw_files = list(RAW_DIR.glob("latest_schedule_*.html"))
    if not raw_files:
        print("No raw HTML snapshots found. Run fetch_schedule.py first.")
        return

    all_raw = []
    for rf in raw_files:
        cat = rf.stem.replace("latest_schedule_", "")
        html = rf.read_text(encoding="utf-8")
        all_raw.extend(parser.parse_schedule_html(html, category_hint=cat))

    existing_teams = storage.load_existing_teams()
    matches, teams, series, venues = normalizer.process_all_raw_matches(all_raw, existing_teams=existing_teams)

    index = generator.generate_all_outputs(matches, teams, series, venues)
    storage.commit_staging()
    print("Generated all outputs successfully.")
    print(f"Stats: {index.stats.model_dump()}")


if __name__ == "__main__":
    main()
