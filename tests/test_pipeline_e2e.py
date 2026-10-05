"""End-to-end integration tests for CricketDataPipeline with mocked client."""

import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock

from src.pipeline import CricketDataPipeline
from src.parser import CricbuzzParser
from src.normalizer import CricketNormalizer
from src.storage import DatasetStorage
from src.images import TeamImageManager
from src.validator import DatasetValidator
from src.generator import OutputGenerator

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_pipeline_e2e_run(tmp_path):
    mock_html = (FIXTURES_DIR / "mock_schedule_rsc.html").read_text(encoding="utf-8")
    mock_teams_html = (FIXTURES_DIR / "mock_teams_rsc.html").read_text(encoding="utf-8")

    # Mock client
    client_mock = MagicMock()
    client_mock.fetch_all_schedules.return_value = {"international": mock_html}
    client_mock.fetch_all_team_directories.return_value = {"international": mock_teams_html}
    client_mock.download_image_bytes.return_value = None  # test gracefully handling missing logos

    # Temp directories
    data_dir = tmp_path / "data"
    staging_dir = data_dir / "_staging"
    images_dir = tmp_path / "images"

    storage = DatasetStorage(data_dir=data_dir, staging_dir=staging_dir)
    image_manager = TeamImageManager(team_dir=images_dir / "teams", flag_dir=images_dir / "flags")
    generator = OutputGenerator(storage=storage)
    parser = CricbuzzParser()
    normalizer = CricketNormalizer()
    validator = DatasetValidator()

    pipeline = CricketDataPipeline(
        client=client_mock,
        parser=parser,
        normalizer=normalizer,
        storage=storage,
        image_manager=image_manager,
        validator=validator,
        generator=generator,
    )

    summary = pipeline.run(sync_team_directories=True, download_logos=False)

    assert summary.matchesDiscovered == 2
    assert summary.validationPassed is True
    assert (data_dir / "matches" / "all.json").exists()
    assert (data_dir / "matches" / "upcoming.json").exists()
    assert (data_dir / "teams" / "teams.json").exists()
    assert (data_dir / "series" / "series.json").exists()
    assert (data_dir / "index.json").exists()

    # Verify content of all.json
    all_matches = json.loads((data_dir / "matches" / "all.json").read_text(encoding="utf-8"))
    assert len(all_matches) == 2
    assert all_matches[0]["id"] == 174134
    assert all_matches[1]["id"] == 174141
