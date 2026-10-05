#!/usr/bin/env python3
"""Script to download and cache team logos for known teams in teams.json."""

import argparse
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.client import CricbuzzClient
from src.images import TeamImageManager
from src.storage import DatasetStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Download and cache team logos")
    parser.add_argument("--force", action="store_true", help="Force redownload of existing cached logos")
    args = parser.parse_args()

    storage = DatasetStorage()
    teams = storage.load_existing_teams()
    if not teams:
        print("No teams found in data/teams/teams.json. Run scripts/fetch_teams.py or scripts/run_pipeline.py first.")
        return

    print(f"Checking logos for {len(teams)} teams...")
    client = CricbuzzClient()
    image_manager = TeamImageManager()

    downloaded, skipped, failed = image_manager.sync_team_images(teams, client, force_redownload=args.force)
    print("\nLogo Download Summary:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped (already cached): {skipped}")
    print(f"  Failed / Missing imageId: {failed}")


if __name__ == "__main__":
    main()
