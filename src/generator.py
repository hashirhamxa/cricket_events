"""Output generator for partitioned and categorized cricket fixture JSON files."""

from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from src.config import DEFAULT_TIMEZONE
from src.models import (
    NormalizedMatch,
    NormalizedTeam,
    NormalizedSeries,
    NormalizedVenue,
    DatasetIndex,
    DatasetStats,
)
from src.storage import DatasetStorage

logger = logging.getLogger(__name__)


class OutputGenerator:
    """Partitions and outputs normalized datasets into structured mobile-ready JSON files."""

    def __init__(self, storage: DatasetStorage, tz_name: str = DEFAULT_TIMEZONE):
        self.storage = storage
        self.tz_name = tz_name
        try:
            self.tz = ZoneInfo(tz_name)
        except Exception:
            logger.warning(f"ZoneInfo for {tz_name} failed; falling back to UTC+5")
            self.tz = timezone(timedelta(hours=5))

    def generate_all_outputs(
        self,
        matches: List[NormalizedMatch],
        teams: Dict[int, NormalizedTeam],
        series: Dict[int, NormalizedSeries],
        venues: Dict[str, NormalizedVenue],
        now_dt: Optional[datetime] = None,
    ) -> DatasetIndex:
        """
        Stage all match partitions, teams, series, venues, and index files.
        Returns the constructed DatasetIndex.
        """
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)

        # Evaluate today and tomorrow date bounds in the target timezone
        local_now = now_dt.astimezone(self.tz)
        today_date = local_now.date()
        tomorrow_date = today_date + timedelta(days=1)

        today_matches: List[NormalizedMatch] = []
        tomorrow_matches: List[NormalizedMatch] = []
        upcoming_matches: List[NormalizedMatch] = []

        intl_matches: List[NormalizedMatch] = []
        t20_matches: List[NormalizedMatch] = []
        domestic_matches: List[NormalizedMatch] = []
        women_matches: List[NormalizedMatch] = []

        now_epoch_ms = int(now_dt.timestamp() * 1000)
        # Matches within past 4 hours or future are considered upcoming/active
        upcoming_cutoff_ms = now_epoch_ms - (4 * 3600 * 1000)

        for m in matches:
            # Match date in target timezone
            match_dt = datetime.fromtimestamp(m.startTime / 1000.0, tz=self.tz)
            match_date = match_dt.date()

            if match_date == today_date:
                today_matches.append(m)
            elif match_date == tomorrow_date:
                tomorrow_matches.append(m)

            if m.startTime >= upcoming_cutoff_ms or m.status in ("UPCOMING", "LIVE"):
                upcoming_matches.append(m)

            # Categorize
            if m.category == "INTERNATIONAL":
                intl_matches.append(m)
            elif m.category == "T20_LEAGUE":
                t20_matches.append(m)
            elif m.category == "DOMESTIC":
                domestic_matches.append(m)
            elif m.category == "WOMEN":
                women_matches.append(m)

        # Prepare clean staging area
        self.storage.prepare_staging()

        # Stage matches
        self.storage.stage_json("matches/all.json", matches)
        self.storage.stage_json("matches/today.json", today_matches)
        self.storage.stage_json("matches/tomorrow.json", tomorrow_matches)
        self.storage.stage_json("matches/upcoming.json", upcoming_matches)
        self.storage.stage_json("matches/international.json", intl_matches)
        self.storage.stage_json("matches/t20_leagues.json", t20_matches)
        self.storage.stage_json("matches/domestic.json", domestic_matches)
        self.storage.stage_json("matches/women.json", women_matches)

        # Stage entities
        teams_dump = {str(k): v for k, v in teams.items()}
        series_dump = {str(k): v for k, v in series.items()}
        venues_dump = venues

        self.storage.stage_json("teams/teams.json", teams_dump)
        self.storage.stage_json("series/series.json", series_dump)
        self.storage.stage_json("venues/venues.json", venues_dump)

        # Index metadata
        stats = DatasetStats(
            totalMatches=len(matches),
            upcomingMatches=len(upcoming_matches),
            todayMatches=len(today_matches),
            tomorrowMatches=len(tomorrow_matches),
            internationalMatches=len(intl_matches),
            t20LeagueMatches=len(t20_matches),
            domesticMatches=len(domestic_matches),
            womenMatches=len(women_matches),
            totalTeams=len(teams),
            totalSeries=len(series),
            totalVenues=len(venues),
        )

        index = DatasetIndex(
            updatedAt=now_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            source="cricbuzz",
            schemaVersion=1,
            timezone=self.tz_name,
            stats=stats,
        )

        self.storage.stage_json("index.json", index)
        logger.info(f"Successfully staged all JSON outputs. Stats: {stats.model_dump()}")
        return index
