#!/usr/bin/env python3
"""Script to fetch raw schedule pages from Cricbuzz and save snapshots."""

import argparse
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.client import CricbuzzClient
from src.parser import CricbuzzParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Fetch schedule pages from Cricbuzz")
    parser.add_argument("--category", default="all", choices=["all", "international", "t20_leagues", "domestic", "women", "every"], help="Category to fetch")
    args = parser.parse_args()

    client = CricbuzzClient()
    parser_engine = CricbuzzParser()

    if args.category == "every":
        pages = client.fetch_all_schedules(save_raw=True)
        total = 0
        for cat, html in pages.items():
            matches = parser_engine.parse_schedule_html(html, category_hint=cat)
            print(f"Category '{cat}': {len(matches)} matches parsed")
            total += len(matches)
        print(f"Total raw matches fetched across all categories: {total}")
    else:
        html = client.fetch_schedule_page(args.category)
        matches = parser_engine.parse_schedule_html(html, category_hint=args.category)
        print(f"Fetched {len(matches)} matches for category '{args.category}'")
        for m in matches[:5]:
            print(f"  Match {m.get('matchId')}: {m.get('team1', {}).get('teamName')} vs {m.get('team2', {}).get('teamName')} ({m.get('matchDesc')})")


if __name__ == "__main__":
    main()
