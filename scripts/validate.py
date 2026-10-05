#!/usr/bin/env python3
"""Script to validate all existing production datasets."""

import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config import DATA_DIR
from src.models import (
    NormalizedMatch,
    NormalizedTeam,
    NormalizedSeries,
    NormalizedVenue,
    DatasetIndex,
)
from src.validator import DatasetValidator, ValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    validator = DatasetValidator()

    # Load matches
    all_matches_file = DATA_DIR / "matches" / "all.json"
    if not all_matches_file.exists():
        print("data/matches/all.json not found.")
        sys.exit(1)

    matches_raw = json.loads(all_matches_file.read_text(encoding="utf-8"))
    matches = [NormalizedMatch(**m) for m in matches_raw]

    # Load teams
    teams_file = DATA_DIR / "teams" / "teams.json"
    teams_raw = json.loads(teams_file.read_text(encoding="utf-8")) if teams_file.exists() else {}
    teams = {int(k): NormalizedTeam(**v) for k, v in teams_raw.items()}

    # Load series
    series_file = DATA_DIR / "series" / "series.json"
    series_raw = json.loads(series_file.read_text(encoding="utf-8")) if series_file.exists() else {}
    series = {int(k): NormalizedSeries(**v) for k, v in series_raw.items()}

    # Load venues
    venues_file = DATA_DIR / "venues" / "venues.json"
    venues_raw = json.loads(venues_file.read_text(encoding="utf-8")) if venues_file.exists() else {}
    venues = {k: NormalizedVenue(**v) for k, v in venues_raw.items()}

    # Load index
    index_file = DATA_DIR / "index.json"
    index = DatasetIndex(**json.loads(index_file.read_text(encoding="utf-8"))) if index_file.exists() else None

    print(f"Validating dataset bundle with {len(matches)} matches, {len(teams)} teams, {len(series)} series...")

    try:
        validator.validate_dataset_bundle(
            matches=matches,
            teams=teams,
            series=series,
            venues=venues,
            previous_index=index,
        )
        print("VALIDATION PASSED: All structural and integrity checks succeeded.")
    except ValidationError as e:
        print(f"VALIDATION FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
