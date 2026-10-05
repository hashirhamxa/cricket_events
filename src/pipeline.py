"""Main pipeline orchestrator coordinating scraper, normalizer, asset cache, validation, and storage."""

from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Any, List

from src.client import CricbuzzClient
from src.parser import CricbuzzParser
from src.normalizer import CricketNormalizer
from src.images import TeamImageManager
from src.storage import DatasetStorage
from src.validator import DatasetValidator
from src.generator import OutputGenerator
from src.models import ScrapeSummary, NormalizedTeam

logger = logging.getLogger(__name__)


class CricketDataPipeline:
    """End-to-end data pipeline for cricket schedule collection and publishing."""

    def __init__(
        self,
        client: Optional[CricbuzzClient] = None,
        parser: Optional[CricbuzzParser] = None,
        normalizer: Optional[CricketNormalizer] = None,
        storage: Optional[DatasetStorage] = None,
        image_manager: Optional[TeamImageManager] = None,
        validator: Optional[DatasetValidator] = None,
        generator: Optional[OutputGenerator] = None,
    ):
        self.client = client or CricbuzzClient()
        self.parser = parser or CricbuzzParser()
        self.normalizer = normalizer or CricketNormalizer()
        self.storage = storage or DatasetStorage()
        self.image_manager = image_manager or TeamImageManager()
        self.validator = validator or DatasetValidator()
        self.generator = generator or OutputGenerator(self.storage)

    def run(self, sync_team_directories: bool = True, download_logos: bool = True) -> ScrapeSummary:
        """Execute the full pipeline run."""
        summary = ScrapeSummary()
        logger.info("==========================================")
        logger.info("Starting Cricket Data Repository Pipeline")
        logger.info("==========================================")

        # 1. Load previous state
        existing_teams = self.storage.load_existing_teams()
        existing_series = self.storage.load_existing_series()
        previous_index = self.storage.load_existing_index()
        logger.info(f"Loaded {len(existing_teams)} existing teams and {len(existing_series)} series")

        # 2. Fetch all schedule category pages
        schedule_pages = self.client.fetch_all_schedules(save_raw=True)
        raw_fixtures: List[Dict[str, Any]] = []

        for category, html in schedule_pages.items():
            parsed_matches = self.parser.parse_schedule_html(html, category_hint=category)
            logger.info(f"Parsed {len(parsed_matches)} matches for category '{category}'")
            raw_fixtures.extend(parsed_matches)

        summary.matchesDiscovered = len(raw_fixtures)

        # 3. Optionally enrich teams from Cricbuzz team directories
        team_catalog: Dict[int, NormalizedTeam] = dict(existing_teams)
        if sync_team_directories:
            logger.info("Syncing team directories from Cricbuzz...")
            team_pages = self.client.fetch_all_team_directories()
            for cat, html in team_pages.items():
                parsed_teams = self.parser.parse_team_directory_html(html, category_hint=cat)
                for raw_t in parsed_teams:
                    t_norm = self.normalizer.normalize_team(raw_t, cat)
                    if t_norm:
                        # If existing team has missing imageId or details, update it
                        if t_norm.id not in team_catalog or (t_norm.imageId and not team_catalog[t_norm.id].imageId):
                            team_catalog[t_norm.id] = t_norm

        # 4. Normalize fixtures and extract all entities
        matches, all_teams, series_map, venues_map = self.normalizer.process_all_raw_matches(
            raw_fixtures,
            existing_teams=team_catalog,
        )

        # Track new teams
        new_team_ids = set(all_teams.keys()) - set(existing_teams.keys())
        summary.uniqueTeams = len(all_teams)
        summary.newTeams = len(new_team_ids)
        summary.uniqueSeries = len(series_map)
        summary.uniqueVenues = len(venues_map)

        logger.info(f"Normalized into {len(matches)} matches, {len(all_teams)} unique teams ({len(new_team_ids)} new)")

        # 5. Download and cache team logos
        if download_logos:
            logger.info("Synchronizing team logos...")
            active_team_ids = {m.teamAId for m in matches} | {m.teamBId for m in matches}
            downloaded, skipped, failed = self.image_manager.sync_team_images(
                all_teams,
                self.client,
                active_team_ids=active_team_ids,
            )
            summary.teamImagesCached = downloaded + skipped
            summary.missingImages = failed
            logger.info(f"Team logo sync: {downloaded} downloaded, {skipped} cached, {failed} missing/failed")

        # 6. Generate staged outputs
        index = self.generator.generate_all_outputs(
            matches=matches,
            teams=all_teams,
            series=series_map,
            venues=venues_map,
        )

        summary.upcoming = index.stats.upcomingMatches
        summary.today = index.stats.todayMatches
        summary.tomorrow = index.stats.tomorrowMatches
        summary.international = index.stats.internationalMatches
        summary.t20Leagues = index.stats.t20LeagueMatches
        summary.domestic = index.stats.domesticMatches
        summary.women = index.stats.womenMatches

        # 7. Validate complete dataset bundle
        logger.info("Validating staged dataset bundle...")
        try:
            self.validator.validate_dataset_bundle(
                matches=matches,
                teams=all_teams,
                series=series_map,
                venues=venues_map,
                previous_index=previous_index,
            )
            summary.validationPassed = True
        except Exception as e:
            logger.critical(f"Validation FAILED: {e}. Aborting commit to protect production data.")
            raise

        # 8. Commit staged files to production
        self.storage.commit_staging()
        logger.info("Pipeline execution COMPLETED successfully!")

        return summary
