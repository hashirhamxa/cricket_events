"""Tests for output generator file layout and categories."""

from datetime import datetime, timezone
import pytest
from src.generator import OutputGenerator
from src.models import NormalizedMatch, NormalizedTeam, NormalizedSeries, NormalizedVenue
from unittest.mock import MagicMock


def test_generator_partitions_and_stages():
    storage_mock = MagicMock()
    generator = OutputGenerator(storage_mock)

    matches = [
        NormalizedMatch(
            id=1, sourceMatchId=1, seriesName="S1", category="INTERNATIONAL", matchDesc="1st T20I", format="T20",
            teamAId=1, teamBId=2, teamAName="IND", teamBName="PAK", teamAShort="IND", teamBShort="PAK",
            startTime=1791162000000, startTimeUtc="2026-10-05T01:00:00Z", venue="V1",
        ),
        NormalizedMatch(
            id=2, sourceMatchId=2, seriesName="S2", category="T20_LEAGUE", matchDesc="Match 1", format="T20",
            teamAId=3, teamBId=4, teamAName="CSK", teamBName="MI", teamAShort="CSK", teamBShort="MI",
            startTime=1791162000000, startTimeUtc="2026-10-05T01:00:00Z", venue="V2",
        ),
    ]

    teams = {
        1: NormalizedTeam(id=1, name="India", shortName="IND"),
        2: NormalizedTeam(id=2, name="Pakistan", shortName="PAK"),
        3: NormalizedTeam(id=3, name="Chennai", shortName="CSK"),
        4: NormalizedTeam(id=4, name="Mumbai", shortName="MI"),
    }

    series = {
        1: NormalizedSeries(id=1, name="S1", category="INTERNATIONAL", matchCount=1),
        2: NormalizedSeries(id=2, name="S2", category="T20_LEAGUE", matchCount=1),
    }

    venues = {
        "v1": NormalizedVenue(name="V1"),
        "v2": NormalizedVenue(name="V2"),
    }

    index = generator.generate_all_outputs(matches, teams, series, venues)

    # Check stage calls
    staged_paths = [call.args[0] for call in storage_mock.stage_json.call_args_list]
    assert "matches/all.json" in staged_paths
    assert "matches/today.json" in staged_paths
    assert "matches/tomorrow.json" in staged_paths
    assert "matches/upcoming.json" in staged_paths
    assert "matches/international.json" in staged_paths
    assert "matches/t20_leagues.json" in staged_paths
    assert "teams/teams.json" in staged_paths
    assert "series/series.json" in staged_paths
    assert "venues/venues.json" in staged_paths
    assert "index.json" in staged_paths

    assert index.stats.totalMatches == 2
    assert index.stats.internationalMatches == 1
    assert index.stats.t20LeagueMatches == 1
    assert index.stats.totalTeams == 4
