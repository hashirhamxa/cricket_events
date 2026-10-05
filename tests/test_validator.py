"""Tests for dataset validator and sanity guards."""

import pytest
from src.models import (
    NormalizedMatch,
    NormalizedTeam,
    NormalizedSeries,
    NormalizedVenue,
    DatasetIndex,
    DatasetStats,
)
from src.validator import DatasetValidator, ValidationError, SanityThresholdError


@pytest.fixture
def valid_bundle():
    matches = [
        NormalizedMatch(
            id=101, sourceMatchId=101, seriesId=1, seriesName="Tour 2026", category="INTERNATIONAL",
            matchDesc="1st T20I", format="T20", teamAId=1, teamBId=2, teamAName="India", teamBName="Australia",
            teamAShort="IND", teamBShort="AUS", startTime=1791162000000, startTimeUtc="2026-10-05T01:00:00Z",
            venue="MCG", city="Melbourne", country="Australia", timezone="+10:00", status="UPCOMING",
        )
    ]
    teams = {
        1: NormalizedTeam(id=1, name="India", shortName="IND"),
        2: NormalizedTeam(id=2, name="Australia", shortName="AUS"),
    }
    series = {
        1: NormalizedSeries(id=1, name="Tour 2026", category="INTERNATIONAL", matchCount=1)
    }
    venues = {
        "mcg_melbourne": NormalizedVenue(name="MCG", city="Melbourne", country="Australia", timezone="+10:00")
    }
    return matches, teams, series, venues


def test_validator_passes_on_valid_bundle(valid_bundle):
    matches, teams, series, venues = valid_bundle
    validator = DatasetValidator()
    # Should not raise
    validator.validate_dataset_bundle(matches, teams, series, venues)


def test_validator_detects_duplicate_match_id(valid_bundle):
    matches, teams, series, venues = valid_bundle
    # Add duplicate
    matches.append(matches[0])
    validator = DatasetValidator()
    with pytest.raises(ValidationError, match="Duplicate match ID"):
        validator.validate_dataset_bundle(matches, teams, series, venues)


def test_validator_detects_invalid_team_reference(valid_bundle):
    matches, teams, series, venues = valid_bundle
    matches[0].teamAId = 999  # not in teams
    validator = DatasetValidator()
    with pytest.raises(ValidationError, match="references unknown Team A ID"):
        validator.validate_dataset_bundle(matches, teams, series, venues)


def test_validator_detects_same_team_match(valid_bundle):
    matches, teams, series, venues = valid_bundle
    matches[0].teamBId = matches[0].teamAId
    validator = DatasetValidator()
    with pytest.raises(ValidationError, match="identical Team A and Team B"):
        validator.validate_dataset_bundle(matches, teams, series, venues)


def test_sanity_threshold_drop():
    validator = DatasetValidator()
    prev_index = DatasetIndex(
        updatedAt="2026-10-04T00:00:00Z",
        source="cricbuzz",
        schemaVersion=1,
        stats=DatasetStats(totalMatches=100),
    )
    # If scraper returns 10 matches (< 30% of 100), it must raise SanityThresholdError
    with pytest.raises(SanityThresholdError, match="dropped precipitously"):
        validator.check_sanity_threshold(10, prev_index)
