"""Data validation and sanity verification engine for cricket datasets."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict, List, Optional

from src.config import SANITY_DROP_THRESHOLD_RATIO, MIN_EXPECTED_MATCHES
from src.models import (
    NormalizedMatch,
    NormalizedTeam,
    NormalizedSeries,
    NormalizedVenue,
    DatasetIndex,
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when dataset integrity checks fail."""
    pass


class SanityThresholdError(ValidationError):
    """Raised when scraper returns suspiciously degraded match counts."""
    pass


class DatasetValidator:
    """Validates structural correctness and sanity of normalized cricket datasets."""

    ALLOWED_STATUSES = {
        "UPCOMING",
        "LIVE",
        "COMPLETED",
        "CANCELLED",
        "POSTPONED",
        "ABANDONED",
        "UNKNOWN",
    }

    ALLOWED_FORMATS = {"T20", "ODI", "TEST", "OTHER"}

    def validate_matches(self, matches: List[NormalizedMatch], teams: Dict[int, NormalizedTeam]) -> List[str]:
        """Validate a collection of matches. Returns list of warning/error messages."""
        errors = []
        seen_ids = set()

        for idx, m in enumerate(matches):
            # Duplicate ID check
            if m.id in seen_ids:
                errors.append(f"Duplicate match ID {m.id} at index {idx}")
            seen_ids.add(m.id)

            # Match ID sanity
            if m.id <= 0:
                errors.append(f"Invalid match ID {m.id}")

            # Team IDs check
            if m.teamAId <= 0 or m.teamBId <= 0:
                errors.append(f"Match {m.id} has invalid team IDs ({m.teamAId}, {m.teamBId})")
            if m.teamAId == m.teamBId:
                errors.append(f"Match {m.id} has identical Team A and Team B ({m.teamAId})")

            # Team names check
            if not m.teamAName or not m.teamBName:
                errors.append(f"Match {m.id} is missing team name(s)")

            # Team reference check
            if m.teamAId not in teams:
                errors.append(f"Match {m.id} references unknown Team A ID {m.teamAId}")
            if m.teamBId not in teams:
                errors.append(f"Match {m.id} references unknown Team B ID {m.teamBId}")

            # Timestamp validity
            if m.startTime <= 0:
                errors.append(f"Match {m.id} has non-positive start timestamp: {m.startTime}")

            # ISO UTC consistency
            try:
                dt = datetime.fromisoformat(m.startTimeUtc.replace("Z", "+00:00"))
                expected_epoch_sec = int(m.startTime / 1000.0)
                if abs(int(dt.timestamp()) - expected_epoch_sec) > 1:
                    errors.append(f"Match {m.id} startTime ({m.startTime}) does not match startTimeUtc ({m.startTimeUtc})")
            except Exception as e:
                errors.append(f"Match {m.id} has malformed startTimeUtc '{m.startTimeUtc}': {e}")

            if m.endTime and m.endTime < m.startTime:
                errors.append(f"Match {m.id} endTime ({m.endTime}) is earlier than startTime ({m.startTime})")

            # Venue check
            if not m.venue:
                errors.append(f"Match {m.id} has empty venue string")

            # Status check
            if m.status not in self.ALLOWED_STATUSES:
                errors.append(f"Match {m.id} has unexpected status '{m.status}'")

        return errors

    def validate_teams(self, teams: Dict[int, NormalizedTeam]) -> List[str]:
        """Validate team records."""
        errors = []
        for team_id, team in teams.items():
            if team.id != team_id:
                errors.append(f"Team key {team_id} does not match team.id {team.id}")
            if not team.name.strip():
                errors.append(f"Team {team_id} has empty name")
            if not team.shortName.strip():
                errors.append(f"Team {team_id} has empty short name")
        return errors

    def validate_series(self, series: Dict[int, NormalizedSeries]) -> List[str]:
        """Validate series records."""
        errors = []
        for series_id, s in series.items():
            if s.id != series_id:
                errors.append(f"Series key {series_id} does not match series.id {s.id}")
            if not s.name.strip():
                errors.append(f"Series {series_id} has empty name")
        return errors

    def check_sanity_threshold(
        self,
        current_match_count: int,
        previous_index: Optional[DatasetIndex],
    ):
        """
        Verify that newly parsed match count hasn't catastrophically dropped
        compared to previous valid dataset.
        """
        if current_match_count < MIN_EXPECTED_MATCHES:
            raise SanityThresholdError(
                f"Scraper returned {current_match_count} matches, which is below minimum expected ({MIN_EXPECTED_MATCHES})"
            )

        if previous_index and previous_index.stats.totalMatches > 10:
            prev_count = previous_index.stats.totalMatches
            threshold = int(prev_count * SANITY_DROP_THRESHOLD_RATIO)
            if current_match_count < threshold:
                raise SanityThresholdError(
                    f"Match count dropped precipitously from {prev_count} to {current_match_count} "
                    f"(Threshold: {threshold}). Overwrite aborted to protect production data."
                )

    def validate_dataset_bundle(
        self,
        matches: List[NormalizedMatch],
        teams: Dict[int, NormalizedTeam],
        series: Dict[int, NormalizedSeries],
        venues: Dict[str, NormalizedVenue],
        previous_index: Optional[DatasetIndex] = None,
    ):
        """Run all validation suites on the extracted dataset bundle."""
        # 1. Sanity threshold check
        self.check_sanity_threshold(len(matches), previous_index)

        # 2. Match validation
        match_errors = self.validate_matches(matches, teams)
        if match_errors:
            logger.error(f"Match validation failed with {len(match_errors)} errors:")
            for err in match_errors[:10]:
                logger.error(f"  - {err}")
            raise ValidationError(f"Match validation failed ({len(match_errors)} issues): {'; '.join(match_errors)}")

        # 3. Team validation
        team_errors = self.validate_teams(teams)
        if team_errors:
            logger.error(f"Team validation failed with {len(team_errors)} errors")
            raise ValidationError(f"Team validation failed ({len(team_errors)} issues): {'; '.join(team_errors)}")

        # 4. Series validation
        series_errors = self.validate_series(series)
        if series_errors:
            logger.error(f"Series validation failed with {len(series_errors)} errors")
            raise ValidationError(f"Series validation failed ({len(series_errors)} issues): {'; '.join(series_errors)}")

        logger.info("All dataset validation checks PASSED successfully.")
