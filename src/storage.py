"""Atomic dataset storage and file persistence layer."""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import (
    DATA_DIR,
    MATCHES_DIR,
    TEAMS_DIR,
    SERIES_DIR,
    VENUES_DIR,
    STAGING_DIR,
)
from src.models import (
    NormalizedMatch,
    NormalizedTeam,
    NormalizedSeries,
    NormalizedVenue,
    DatasetIndex,
)

logger = logging.getLogger(__name__)


class DatasetStorage:
    """Handles loading and atomic saving of cricket datasets."""

    def __init__(self, data_dir: Optional[Path] = None, staging_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.staging_dir = staging_dir or STAGING_DIR

        # Ensure base directories exist
        (self.data_dir / "matches").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "teams").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "series").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "venues").mkdir(parents=True, exist_ok=True)

    def load_existing_teams(self) -> Dict[int, NormalizedTeam]:
        """Load currently stored teams.json."""
        teams_file = self.data_dir / "teams" / "teams.json"
        if not teams_file.exists():
            return {}
        try:
            data = json.loads(teams_file.read_text(encoding="utf-8"))
            teams = {}
            for k, v in data.items():
                teams[int(k)] = NormalizedTeam(**v)
            return teams
        except Exception as e:
            logger.warning(f"Could not load existing teams.json: {e}")
            return {}

    def load_existing_series(self) -> Dict[int, NormalizedSeries]:
        """Load currently stored series.json."""
        series_file = self.data_dir / "series" / "series.json"
        if not series_file.exists():
            return {}
        try:
            data = json.loads(series_file.read_text(encoding="utf-8"))
            series = {}
            for k, v in data.items():
                series[int(k)] = NormalizedSeries(**v)
            return series
        except Exception as e:
            logger.warning(f"Could not load existing series.json: {e}")
            return {}

    def load_existing_index(self) -> Optional[DatasetIndex]:
        """Load existing index.json to check historical metrics."""
        index_file = self.data_dir / "index.json"
        if not index_file.exists():
            return None
        try:
            data = json.loads(index_file.read_text(encoding="utf-8"))
            return DatasetIndex(**data)
        except Exception as e:
            logger.warning(f"Could not load existing index.json: {e}")
            return None

    def prepare_staging(self) -> Path:
        """Create a clean staging directory."""
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)
        (self.staging_dir / "matches").mkdir(parents=True, exist_ok=True)
        (self.staging_dir / "teams").mkdir(parents=True, exist_ok=True)
        (self.staging_dir / "series").mkdir(parents=True, exist_ok=True)
        (self.staging_dir / "venues").mkdir(parents=True, exist_ok=True)
        return self.staging_dir

    def stage_json(self, rel_path: str, data: Any):
        """Write JSON data to a staged relative path."""
        target = self.staging_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            if hasattr(data, "model_dump"):
                json.dump(data.model_dump(), f, indent=2, ensure_ascii=False)
            elif isinstance(data, list):
                dumped = [item.model_dump() if hasattr(item, "model_dump") else item for item in data]
                json.dump(dumped, f, indent=2, ensure_ascii=False)
            elif isinstance(data, dict):
                dumped = {k: (v.model_dump() if hasattr(v, "model_dump") else v) for k, v in data.items()}
                json.dump(dumped, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def commit_staging(self):
        """Atomically promote all staged files to production data directory."""
        logger.info(f"Promoting staged data from {self.staging_dir} to {self.data_dir}")
        for item in self.staging_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(self.staging_dir)
                dest = self.data_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)

        # Cleanup staging
        shutil.rmtree(self.staging_dir, ignore_errors=True)
        logger.info("Staged files successfully committed to production dataset")
