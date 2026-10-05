"""Tests for match and team deduplication."""

import pytest
from src.normalizer import CricketNormalizer


def test_match_deduplication_and_sorting():
    norm = CricketNormalizer()
    raw_matches = [
        {
            "matchId": 200,
            "startDate": "1791200000000",
            "team1": {"teamId": 1, "teamName": "Team A"},
            "team2": {"teamId": 2, "teamName": "Team B"},
            "seriesName": "Series B",
        },
        {
            "matchId": 100,
            "startDate": "1791100000000",
            "team1": {"teamId": 3, "teamName": "Team C"},
            "team2": {"teamId": 4, "teamName": "Team D"},
            "seriesName": "Series A",
        },
        # Duplicate of 200 with different category hint
        {
            "matchId": 200,
            "startDate": "1791200000000",
            "team1": {"teamId": 1, "teamName": "Team A"},
            "team2": {"teamId": 2, "teamName": "Team B"},
            "seriesName": "Series B",
            "seriesCategory": "International",
        },
    ]

    matches, teams, series, venues = norm.process_all_raw_matches(raw_matches)

    assert len(matches) == 2
    # Check chronological ordering (match 100 is earlier than 200)
    assert matches[0].id == 100
    assert matches[1].id == 200
    # Check teams extracted
    assert len(teams) == 4
