"""
generate_match_images.py
CLI script to generate broadcast-grade matchday graphics for cricket fixtures.
Usage:
    python scripts/generate_match_images.py --scope upcoming
    python scripts/generate_match_images.py --scope today
    python scripts/generate_match_images.py --scope all
    python scripts/generate_match_images.py --preview
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from typing import List, Dict, Any
from PIL import Image, ImageDraw

from src.config import BASE_DIR, DATA_DIR, MATCHES_DIR, MATCH_IMAGES_DIR, FONTS_DIR
from src.models import NormalizedMatch
from src.posters import generate_match_card, generate_all_match_images, get_font
from src.image_themes import THEMES_REGISTRY

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("generate_match_images")


def load_matches_from_file(json_path: Path) -> List[NormalizedMatch]:
    """Loads and parses list of NormalizedMatch objects from JSON."""
    if not json_path.exists():
        logger.error(f"File not found: {json_path}")
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [NormalizedMatch.model_validate(item) for item in data]
    return []


def generate_theme_preview_contact_sheet(output_dir: Path = BASE_DIR / "output" / "theme_previews") -> str:
    """
    Generates preview cards for each of the 6 cricket themes and stitches them into a contact sheet.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Generating theme previews and contact sheet...")

    sample_matches = [
        {
            "id": 99001,
            "sourceMatchId": 99001,
            "seriesName": "ICC Champions Trophy 2026",
            "category": "INTERNATIONAL",
            "format": "ODI",
            "matchDesc": "Final",
            "teamAId": 2,
            "teamBId": 3,
            "teamAName": "India",
            "teamBName": "Pakistan",
            "teamAShort": "IND",
            "teamBShort": "PAK",
            "startTime": 1793331000000,
            "startTimeUtc": "2026-10-30T09:00:00Z",
            "venue": "Gaddafi Stadium",
            "city": "Lahore",
            "country": "Pakistan",
        },
        {
            "id": 99002,
            "sourceMatchId": 99002,
            "seriesName": "Pakistan Super League 2026",
            "category": "T20_LEAGUE",
            "format": "T20",
            "matchDesc": "Qualifier 1",
            "teamAId": 10,
            "teamBId": 11,
            "teamAName": "Lahore Qalandars",
            "teamBName": "Karachi Kings",
            "teamAShort": "LQ",
            "teamBShort": "KK",
            "startTime": 1793331000000,
            "startTimeUtc": "2026-10-30T14:30:00Z",
            "venue": "National Stadium",
            "city": "Karachi",
            "country": "Pakistan",
        },
        {
            "id": 99003,
            "sourceMatchId": 99003,
            "seriesName": "The Ashes 2026-27",
            "category": "INTERNATIONAL",
            "format": "TEST",
            "matchDesc": "1st Test • Day 1",
            "teamAId": 4,
            "teamBId": 9,
            "teamAName": "Australia",
            "teamBName": "England",
            "teamAShort": "AUS",
            "teamBShort": "ENG",
            "startTime": 1793331000000,
            "startTimeUtc": "2026-11-20T00:30:00Z",
            "venue": "Melbourne Cricket Ground",
            "city": "Melbourne",
            "country": "Australia",
        },
        {
            "id": 99004,
            "sourceMatchId": 99004,
            "seriesName": "Quaid-e-Azam Trophy 2026",
            "category": "DOMESTIC",
            "format": "TEST",
            "matchDesc": "Round 3",
            "teamAId": 101,
            "teamBId": 102,
            "teamAName": "SNGPL",
            "teamBName": "WAPDA",
            "teamAShort": "SNG",
            "teamBShort": "WAP",
            "startTime": 1793331000000,
            "startTimeUtc": "2026-10-30T04:30:00Z",
            "venue": "Rawalpindi Cricket Stadium",
            "city": "Rawalpindi",
            "country": "Pakistan",
        },
        {
            "id": 99005,
            "sourceMatchId": 99005,
            "seriesName": "Women's Premier League 2026",
            "category": "WOMEN",
            "format": "T20",
            "matchDesc": "Match 12",
            "teamAId": 201,
            "teamBId": 202,
            "teamAName": "Mumbai Indians Women",
            "teamBName": "Royal Challengers Women",
            "teamAShort": "MIW",
            "teamBShort": "RCBW",
            "startTime": 1793331000000,
            "startTimeUtc": "2026-10-30T14:00:00Z",
            "venue": "DY Patil Stadium",
            "city": "Navi Mumbai",
            "country": "India",
        },
        {
            "id": 99006,
            "sourceMatchId": 99006,
            "seriesName": "Super Smash 2026",
            "category": "OTHER",
            "format": "T20",
            "matchDesc": "Match 7",
            "teamAId": 301,
            "teamBId": 302,
            "teamAName": "Auckland Aces",
            "teamBName": "Canterbury Kings",
            "teamAShort": "AKL",
            "teamBShort": "CAN",
            "startTime": 1793331000000,
            "startTimeUtc": "2026-10-30T03:10:00Z",
            "venue": "Eden Park Outer Oval",
            "city": "Auckland",
            "country": "New Zealand",
        },
    ]

    rendered_images = []
    for sm in sample_matches:
        img_path = output_dir / f"preview_{sm['id']}.png"
        generate_match_card(sm, img_path)
        rendered_images.append((sm["seriesName"], img_path))
        logger.info(f"Generated preview: {img_path.name}")

    # Stitch into a 2-column contact sheet
    card_w = 1200
    card_h = 630
    cols = 2
    rows = (len(rendered_images) + cols - 1) // cols
    margin = 40
    header_bar = 120

    sheet_w = cols * card_w + (cols + 1) * margin
    sheet_h = rows * card_h + (rows + 1) * margin + header_bar

    sheet = Image.new("RGB", (sheet_w, sheet_h), (12, 16, 26))
    draw = ImageDraw.Draw(sheet)

    # Header title
    f_title = get_font(size=56, weight="black", family="montserrat")
    title_text = "CRICKET EVENTS • MATCHDAY BANNER THEMES"
    bbox_t = draw.textbbox((0, 0), title_text, font=f_title)
    tw = bbox_t[2] - bbox_t[0]
    draw.text(((sheet_w - tw) // 2, 34), title_text, fill=(255, 255, 255), font=f_title)

    for idx, (label, p) in enumerate(rendered_images):
        col = idx % cols
        row = idx // cols
        x = margin + col * (card_w + margin)
        y = header_bar + margin + row * (card_h + margin)

        card = Image.open(p)
        sheet.paste(card, (x, y))

    contact_path = output_dir / "cricket_themes_contact_sheet.png"
    sheet.save(str(contact_path), format="PNG", optimize=True)
    logger.info(f"Contact sheet saved: {contact_path}")
    return str(contact_path)


def main():
    parser = argparse.ArgumentParser(description="Cricket matchday graphic card generator")
    parser.add_argument("--scope", choices=["upcoming", "today", "tomorrow", "all"], default="upcoming", help="Dataset scope to generate images for")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of images generated")
    parser.add_argument("--workers", type=int, default=8, help="Number of concurrent worker threads")
    parser.add_argument("--force", action="store_true", help="Force regenerate existing images")
    parser.add_argument("--preview", action="store_true", help="Generate theme preview cards and contact sheet")
    args = parser.parse_args()

    if args.preview:
        contact_sheet = generate_theme_preview_contact_sheet()
        print(f"Theme contact sheet ready: {contact_sheet}")
        return

    json_file = MATCHES_DIR / f"{args.scope}.json"
    matches = load_matches_from_file(json_file)
    if not matches:
        logger.warning(f"No matches found in {json_file}")
        return

    if args.limit:
        matches = matches[:args.limit]

    logger.info(f"Loaded {len(matches)} matches from {json_file.name}")
    generate_all_match_images(
        matches=matches,
        output_dir=MATCH_IMAGES_DIR,
        max_workers=args.workers,
        force=args.force
    )
    logger.info("Done.")


if __name__ == "__main__":
    main()
