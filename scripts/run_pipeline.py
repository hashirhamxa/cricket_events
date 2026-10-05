#!/usr/bin/env python3
"""Main CLI entrypoint to execute the Cricket Data collection and publishing pipeline."""

import argparse
import logging
import sys
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.pipeline import CricketDataPipeline


def setup_logging(debug: bool = False):
    """Configure standard application logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_summary_report(summary):
    """Format and print the standard parity and execution summary."""
    print("\n" + "=" * 50)
    print("CRICKET DATA PIPELINE EXECUTION SUMMARY")
    print("=" * 50)
    print(f"Matches discovered:     {summary.matchesDiscovered}")
    print(f"Upcoming fixtures:      {summary.upcoming}")
    print(f"Today's matches:        {summary.today}")
    print(f"Tomorrow's matches:     {summary.tomorrow}")
    print(f"International matches:  {summary.international}")
    print(f"T20 leagues matches:    {summary.t20Leagues}")
    print(f"Domestic matches:       {summary.domestic}")
    print(f"Women's matches:        {summary.women}")
    print("-" * 50)
    print(f"Unique teams:           {summary.uniqueTeams}")
    print(f"New teams discovered:   {summary.newTeams}")
    print(f"Team images cached:     {summary.teamImagesCached}")
    print(f"Missing team images:    {summary.missingImages}")
    print("-" * 50)
    print(f"Unique series:          {summary.uniqueSeries}")
    print(f"Unique venues:          {summary.uniqueVenues}")
    print(f"Validation status:      {'PASSED' if summary.validationPassed else 'FAILED'}")
    print("=" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run Cricket Data Scraper & Normalization Pipeline")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-logos", action="store_true", help="Skip downloading team logo assets")
    parser.add_argument("--no-team-dirs", action="store_true", help="Skip syncing global team directories")
    args = parser.parse_args()

    setup_logging(debug=args.debug)

    try:
        pipeline = CricketDataPipeline()
        summary = pipeline.run(
            sync_team_directories=not args.no_team_dirs,
            download_logos=not args.no_logos,
        )
        print_summary_report(summary)
    except Exception as e:
        logging.critical(f"Pipeline execution terminated with error: {e}", exc_info=args.debug)
        sys.exit(1)


if __name__ == "__main__":
    main()
