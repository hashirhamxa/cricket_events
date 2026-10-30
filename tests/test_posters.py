"""
Unit tests for the cricket matchday poster and image generation engine.
"""

from pathlib import Path
from PIL import Image
import pytest

from src.image_themes import THEMES_REGISTRY, get_cricket_theme, CricketTheme
from src.posters import (
    get_font,
    fit_team_name_lines,
    generate_match_card,
    generate_all_match_images,
)
from src.models import NormalizedMatch


def test_theme_registry_and_properties():
    expected_themes = ["international", "t20_league", "test", "domestic", "women", "default"]
    for theme_id in expected_themes:
        assert theme_id in THEMES_REGISTRY
        t = THEMES_REGISTRY[theme_id]
        assert isinstance(t, CricketTheme)
        assert len(t.background_top) == 3
        assert len(t.background_bottom) == 3
        assert len(t.primary) == 3
        assert len(t.secondary) == 3
        assert len(t.highlight) == 3
        assert len(t.panel_color) == 4
        assert len(t.panel_border) == 4


def test_theme_resolver_matching():
    # Test match priority
    test_match = {"category": "INTERNATIONAL", "format": "TEST"}
    assert get_cricket_theme(test_match).theme_id == "test"

    # Women's cricket
    women_match = {"category": "WOMEN", "format": "T20"}
    assert get_cricket_theme(women_match).theme_id == "women"

    # T20 League
    t20_match = {"category": "T20_LEAGUE", "format": "T20"}
    assert get_cricket_theme(t20_match).theme_id == "t20_league"

    # Domestic
    domestic_match = {"category": "DOMESTIC", "format": "TEST"}
    assert get_cricket_theme(domestic_match).theme_id == "domestic"

    # International ODI
    intl_match = {"category": "INTERNATIONAL", "format": "ODI"}
    assert get_cricket_theme(intl_match).theme_id == "international"

    # Default fallback
    other_match = {"category": "OTHER", "format": "T10"}
    assert get_cricket_theme(other_match).theme_id == "default"

    # String lookups
    assert get_cricket_theme("international").theme_id == "international"
    assert get_cricket_theme("t20_league").theme_id == "t20_league"
    assert get_cricket_theme("unknown_something").theme_id == "default"


def test_font_loader():
    for fam in ["inter", "montserrat", "archivo"]:
        f = get_font(size=36, weight="bold", family=fam)
        assert f is not None
        # Verify text measurement works
        dummy_img = Image.new("RGBA", (100, 100))
        bbox = f.getbbox("CRICKET")
        assert bbox[2] > bbox[0]
        assert bbox[3] > bbox[1]


def test_fit_team_name_lines():
    # Short name fits in 1 line
    lines, font, h = fit_team_name_lines("Pakistan", max_width=600)
    assert len(lines) == 1
    assert lines[0] == "Pakistan"

    # Long multi-word name splits into 2 lines
    lines, font, h = fit_team_name_lines("Royal Challengers Bangalore", max_width=500)
    assert len(lines) in (1, 2)
    assert "Royal" in lines[0]


def test_generate_single_match_card(tmp_path):
    target_path = tmp_path / "card_test.png"
    match = {
        "id": 1001,
        "seriesName": "ICC Cricket World Cup",
        "category": "INTERNATIONAL",
        "format": "ODI",
        "matchDesc": "Final",
        "teamAId": 101,
        "teamBId": 102,
        "teamAName": "Australia",
        "teamBName": "India",
        "teamAShort": "AUS",
        "teamBShort": "IND",
        "startTime": 1793331000000,
        "startTimeUtc": "2026-10-30T09:00:00Z",
        "venue": "Narendra Modi Stadium",
        "city": "Ahmedabad",
        "country": "India",
    }

    result = generate_match_card(match, target_path)
    assert Path(result).exists()
    assert target_path.stat().st_size > 10000

    # Verify Pillow can open it and dimensions are 1200x630
    with Image.open(target_path) as img:
        assert img.size == (1200, 630)
        assert img.format == "PNG"


def test_fallback_crest_generation(tmp_path):
    target_path = tmp_path / "fallback_card.png"
    # Match with fictitious team IDs that have no crest images on disk
    match = {
        "id": 999999,
        "seriesName": "Qualifier Tournament",
        "category": "OTHER",
        "format": "T20",
        "matchDesc": "Playoff",
        "teamAId": 88888,
        "teamBId": 88889,
        "teamAName": "Thunderbolts",
        "teamBName": "Firebirds",
        "teamAShort": "TB",
        "teamBShort": "FB",
        "startTime": 1793331000000,
        "startTimeUtc": "2026-10-30T10:00:00Z",
        "venue": "Centurion Park",
        "city": "Pretoria",
        "country": "South Africa",
    }

    result = generate_match_card(match, target_path)
    assert Path(result).exists()
    with Image.open(target_path) as img:
        assert img.size == (1200, 630)


def test_batch_match_image_generation(tmp_path):
    out_dir = tmp_path / "matches"
    m1 = NormalizedMatch(
        id=5001,
        source="cricbuzz",
        sourceMatchId=5001,
        seriesName="T20 Blast",
        category="T20_LEAGUE",
        format="T20",
        matchDesc="Match 1",
        teamAId=701,
        teamBId=702,
        teamAName="Yorkshire",
        teamBName="Lancashire",
        teamAShort="YOR",
        teamBShort="LAN",
        startTime=1793331000000,
        startTimeUtc="2026-10-30T17:00:00Z",
        venue="Headingley",
        city="Leeds",
        country="England",
    )
    m2 = NormalizedMatch(
        id=5002,
        source="cricbuzz",
        sourceMatchId=5002,
        seriesName="The Ashes",
        category="INTERNATIONAL",
        format="TEST",
        matchDesc="2nd Test",
        teamAId=4,
        teamBId=9,
        teamAName="Australia",
        teamBName="England",
        teamAShort="AUS",
        teamBShort="ENG",
        startTime=1793331000000,
        startTimeUtc="2026-11-28T00:30:00Z",
        venue="Adelaide Oval",
        city="Adelaide",
        country="Australia",
    )

    matches = [m1, m2]
    res = generate_all_match_images(matches, output_dir=out_dir, max_workers=2, force=True)

    assert len(res) == 2
    assert m1.matchImage == "images/matches/5001.png"
    assert m1.matchImageUrl.endswith("images/matches/5001.png")
    assert (out_dir / "5001.png").exists()

    assert m2.matchImage == "images/matches/5002.png"
    assert m2.matchImageUrl.endswith("images/matches/5002.png")
    assert (out_dir / "5002.png").exists()
