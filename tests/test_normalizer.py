"""Tests for CricketNormalizer."""

import pytest
from src.normalizer import CricketNormalizer


def test_category_normalization():
    norm = CricketNormalizer()
    assert norm.normalize_category("International") == "INTERNATIONAL"
    assert norm.normalize_category("league") == "T20_LEAGUE"
    assert norm.normalize_category("t20-leagues") == "T20_LEAGUE"
    assert norm.normalize_category("domestic") == "DOMESTIC"
    assert norm.normalize_category("women") == "WOMEN"
    assert norm.normalize_category("unknown_xyz") == "OTHER"
    assert norm.normalize_category(None) == "OTHER"


def test_format_normalization():
    norm = CricketNormalizer()
    assert norm.normalize_format("T20I") == "T20"
    assert norm.normalize_format("t20") == "T20"
    assert norm.normalize_format("ODI") == "ODI"
    assert norm.normalize_format("Test") == "TEST"
    assert norm.normalize_format("100-ball") == "100-BALL"


def test_iso_utc_conversion():
    norm = CricketNormalizer()
    # 1791162000000 -> 2026-10-05 01:00:00 UTC
    iso = norm.format_iso_utc(1791162000000)
    assert iso.endswith("Z")
    assert "2026" in iso


def test_normalize_match_valid():
    norm = CricketNormalizer()
    raw = {
        "matchId": 174134,
        "seriesId": 13281,
        "seriesName": "Indonesia tour of South Korea, 2026",
        "seriesCategory": "International",
        "matchDesc": "3rd T20I",
        "matchFormat": "T20",
        "startDate": "1791162000000",
        "endDate": "1791244799000",
        "team1": {
            "teamId": 299,
            "teamName": "South Korea",
            "teamSName": "SKR",
            "imageId": 172348,
        },
        "team2": {
            "teamId": 566,
            "teamName": "Indonesia",
            "teamSName": "IDN",
            "imageId": 172618,
        },
        "venueInfo": {
            "ground": "Yeonhui Cricket Ground ",
            "city": "Incheon",
            "country": "South Korea ",
            "timezone": "+09:00",
        },
    }

    match = norm.normalize_match(raw)
    assert match is not None
    assert match.id == 174134
    assert match.source == "cricbuzz"
    assert match.teamAId == 299
    assert match.teamBId == 566
    assert match.teamAName == "South Korea"
    assert match.teamBName == "Indonesia"
    assert match.teamAShort == "SKR"
    assert match.teamBShort == "IDN"
    assert match.teamALogo == "images/teams/299.png"
    assert match.teamBLogo == "images/teams/566.png"
    assert match.venue == "Yeonhui Cricket Ground"
    assert match.category == "INTERNATIONAL"
    assert match.format == "T20"


def test_normalize_match_invalid_teams():
    norm = CricketNormalizer()
    raw_invalid = {
        "matchId": 999,
        "team1": {"teamId": 0},
        "team2": {"teamId": 5},
        "startDate": "1791162000000",
    }
    assert norm.normalize_match(raw_invalid) is None
