#!/usr/bin/env python3
"""Script to fetch and discover teams from Cricbuzz directories."""

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.client import CricbuzzClient
from src.parser import CricbuzzParser
from src.normalizer import CricketNormalizer
from src.storage import DatasetStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    client = CricbuzzClient()
    parser_engine = CricbuzzParser()
    normalizer = CricketNormalizer()
    storage = DatasetStorage()

    existing_teams = storage.load_existing_teams()
    print(f"Currently known teams: {len(existing_teams)}")

    pages = client.fetch_all_team_directories()
    new_count = 0

    for cat, html in pages.items():
        raw_teams = parser_engine.parse_team_directory_html(html, category_hint=cat)
        print(f"Directory '{cat}': found {len(raw_teams)} teams")
        for rt in raw_teams:
            t = normalizer.normalize_team(rt, default_category=cat)
            if t and t.id not in existing_teams:
                existing_teams[t.id] = t
                new_count += 1

    print(f"New teams discovered from directories: {new_count}")
    print(f"Total teams now: {len(existing_teams)}")

    # Save to data/teams/teams.json
    storage.prepare_staging()
    storage.stage_json("teams/teams.json", {str(k): v for k, v in existing_teams.items()})
    storage.commit_staging()
    print("Updated data/teams/teams.json successfully.")


if __name__ == "__main__":
    main()
