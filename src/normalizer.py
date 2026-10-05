"""Normalizer for transforming raw scraped Cricbuzz objects into canonical domain models."""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.models import (
    NormalizedMatch,
    NormalizedTeam,
    NormalizedSeries,
    NormalizedVenue,
)

logger = logging.getLogger(__name__)


class CricketNormalizer:
    """Normalizes raw dictionary fixtures into validated domain entities."""

    CATEGORY_MAP = {
        "international": "INTERNATIONAL",
        "league": "T20_LEAGUE",
        "t20_leagues": "T20_LEAGUE",
        "t20-leagues": "T20_LEAGUE",
        "domestic": "DOMESTIC",
        "women": "WOMEN",
    }

    @staticmethod
    def normalize_category(category_raw: Optional[str]) -> str:
        """Map raw category string to standard enum string."""
        if not category_raw:
            return "OTHER"
        cleaned = category_raw.strip().lower()
        return CricketNormalizer.CATEGORY_MAP.get(cleaned, "OTHER")

    @staticmethod
    def normalize_format(format_raw: Optional[str]) -> str:
        """Normalize cricket match format."""
        if not format_raw:
            return "OTHER"
        f = format_raw.strip().upper()
        if "T20" in f:
            return "T20"
        if "ODI" in f:
            return "ODI"
        if "TEST" in f:
            return "TEST"
        return f

    @staticmethod
    def format_iso_utc(epoch_ms: int) -> str:
        """Convert epoch milliseconds to ISO-8601 UTC string."""
        dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def slugify(text: str) -> str:
        """Create a filesystem and URL safe slug."""
        if not text:
            return "unknown"
        s = re.sub(r"[^\w\s-]", "", text.strip().lower())
        return re.sub(r"[-\s]+", "-", s)

    def normalize_match(
        self,
        raw_match: Dict[str, Any],
        known_teams: Optional[Dict[int, NormalizedTeam]] = None,
    ) -> Optional[NormalizedMatch]:
        """Normalize a single raw match dictionary into NormalizedMatch."""
        try:
            match_id = int(raw_match.get("matchId") or raw_match.get("id"))
            series_id = int(raw_match.get("seriesId")) if raw_match.get("seriesId") else None
            series_name = (raw_match.get("seriesName") or "Cricket Series").strip()

            raw_cat = raw_match.get("seriesCategory") or raw_match.get("category")
            category = self.normalize_category(raw_cat)

            match_desc = (raw_match.get("matchDesc") or raw_match.get("text") or "Match").strip()
            match_format = self.normalize_format(raw_match.get("matchFormat") or raw_match.get("format"))

            # Team 1 (Team A)
            t1 = raw_match.get("team1") or {}
            team_a_id = int(t1.get("teamId") or 0)
            team_a_name = (t1.get("teamName") or "Team A").strip()
            team_a_short = (t1.get("teamSName") or team_a_name[:3]).strip().upper()

            # Team 2 (Team B)
            t2 = raw_match.get("team2") or {}
            team_b_id = int(t2.get("teamId") or 0)
            team_b_name = (t2.get("teamName") or "Team B").strip()
            team_b_short = (t2.get("teamSName") or team_b_name[:3]).strip().upper()

            if team_a_id == 0 or team_b_id == 0:
                logger.warning(f"Match {match_id} skipped: invalid team IDs ({team_a_id}, {team_b_id})")
                return None

            # Timestamps
            start_date_raw = raw_match.get("startDate") or raw_match.get("startTime") or raw_match.get("longDate")
            if not start_date_raw:
                logger.warning(f"Match {match_id} skipped: missing start timestamp")
                return None

            start_time = int(start_date_raw)
            start_time_utc = self.format_iso_utc(start_time)

            end_date_raw = raw_match.get("endDate")
            end_time = int(end_date_raw) if end_date_raw else None

            # Venue
            venue_info = raw_match.get("venueInfo") or {}
            venue = (venue_info.get("ground") or raw_match.get("venue") or "TBA").strip()
            city = (venue_info.get("city") or raw_match.get("city") or None)
            if city:
                city = city.strip()
            country = (venue_info.get("country") or raw_match.get("country") or None)
            if country:
                country = country.strip()
            tz_offset = (venue_info.get("timezone") or raw_match.get("timezone") or None)
            if tz_offset:
                tz_offset = tz_offset.strip()

            # Logo paths
            team_a_logo = f"images/teams/{team_a_id}.png"
            team_b_logo = f"images/teams/{team_b_id}.png"

            # Determine status
            status = (raw_match.get("status") or "UPCOMING").strip().upper()

            return NormalizedMatch(
                id=match_id,
                source="cricbuzz",
                sourceMatchId=match_id,
                seriesId=series_id,
                seriesName=series_name,
                category=category,
                matchDesc=match_desc,
                format=match_format,
                teamAId=team_a_id,
                teamBId=team_b_id,
                teamAName=team_a_name,
                teamBName=team_b_name,
                teamAShort=team_a_short,
                teamBShort=team_b_short,
                teamALogo=team_a_logo,
                teamBLogo=team_b_logo,
                startTime=start_time,
                startTimeUtc=start_time_utc,
                endTime=end_time,
                venueId=None,
                venue=venue,
                city=city,
                country=country,
                timezone=tz_offset,
                status=status,
            )
        except Exception as e:
            logger.error(f"Error normalizing match {raw_match.get('matchId')}: {e}")
            return None

    def normalize_team(self, raw_team: Dict[str, Any], default_category: Optional[str] = None) -> Optional[NormalizedTeam]:
        """Normalize a team dictionary into NormalizedTeam."""
        try:
            team_id = int(raw_team.get("teamId") or raw_team.get("id") or 0)
            if team_id == 0:
                return None

            name = (raw_team.get("teamName") or raw_team.get("name") or "").strip()
            if not name:
                return None

            short_name = (raw_team.get("teamSName") or raw_team.get("shortName") or name[:3]).strip().upper()
            country = (raw_team.get("countryName") or raw_team.get("country") or None)
            if country:
                country = country.strip()

            image_id = raw_team.get("imageId")
            image_id = int(image_id) if image_id else None

            logo = f"images/teams/{team_id}.png"
            flag = f"images/flags/{self.slugify(country)}.png" if country else None

            category = self.normalize_category(raw_team.get("directoryCategory") or default_category)

            return NormalizedTeam(
                id=team_id,
                name=name,
                shortName=short_name,
                country=country,
                category=category,
                imageId=image_id,
                logo=logo,
                flag=flag,
            )
        except Exception as e:
            logger.error(f"Error normalizing team: {e}")
            return None

    def process_all_raw_matches(
        self,
        raw_matches: List[Dict[str, Any]],
        existing_teams: Optional[Dict[int, NormalizedTeam]] = None,
    ) -> Tuple[List[NormalizedMatch], Dict[int, NormalizedTeam], Dict[int, NormalizedSeries], Dict[str, NormalizedVenue]]:
        """
        Process a collection of raw scraped matches, deduplicating and extracting
        all normalized matches, teams, series, and venues.
        """
        matches_by_id: Dict[int, NormalizedMatch] = {}
        teams_by_id: Dict[int, NormalizedTeam] = dict(existing_teams or {})
        series_by_id: Dict[int, NormalizedSeries] = {}
        venues_by_key: Dict[str, NormalizedVenue] = {}

        for raw in raw_matches:
            match = self.normalize_match(raw, teams_by_id)
            if not match:
                continue

            # Deduplicate by match ID (latest / most complete wins)
            matches_by_id[match.id] = match

            # Extract teams if present in raw
            for key in ["team1", "team2"]:
                raw_t = raw.get(key)
                if raw_t:
                    t_norm = self.normalize_team(raw_t, match.category)
                    if t_norm:
                        if t_norm.id not in teams_by_id or not teams_by_id[t_norm.id].imageId:
                            teams_by_id[t_norm.id] = t_norm

            # Extract series
            if match.seriesId:
                if match.seriesId not in series_by_id:
                    series_by_id[match.seriesId] = NormalizedSeries(
                        id=match.seriesId,
                        name=match.seriesName,
                        category=match.category,
                        matchCount=1,
                    )
                else:
                    series_by_id[match.seriesId].matchCount = (series_by_id[match.seriesId].matchCount or 0) + 1

            # Extract venue
            if match.venue and match.venue != "TBA":
                venue_key = f"{self.slugify(match.venue)}_{self.slugify(match.city or '')}"
                if venue_key not in venues_by_key:
                    venues_by_key[venue_key] = NormalizedVenue(
                        name=match.venue,
                        city=match.city,
                        country=match.country,
                        timezone=match.timezone,
                    )

        # Sort matches chronologically by startTime then id
        sorted_matches = sorted(matches_by_id.values(), key=lambda m: (m.startTime, m.id))
        return sorted_matches, teams_by_id, series_by_id, venues_by_key
