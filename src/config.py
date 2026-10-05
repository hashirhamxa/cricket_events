"""Configuration constants and paths for the Cricket Data Repository."""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MATCHES_DIR = DATA_DIR / "matches"
TEAMS_DIR = DATA_DIR / "teams"
SERIES_DIR = DATA_DIR / "series"
VENUES_DIR = DATA_DIR / "venues"
STAGING_DIR = DATA_DIR / "_staging"

IMAGES_DIR = BASE_DIR / "images"
TEAM_IMAGES_DIR = IMAGES_DIR / "teams"
FLAG_IMAGES_DIR = IMAGES_DIR / "flags"
SERIES_IMAGES_DIR = IMAGES_DIR / "series"

RAW_DIR = BASE_DIR / "raw"
DOCS_DIR = BASE_DIR / "docs"

# Cricbuzz Schedule URLs
SCHEDULE_URLS = {
    "all": "https://www.cricbuzz.com/cricket-schedule/upcoming-series/all",
    "international": "https://www.cricbuzz.com/cricket-schedule/upcoming-series/international",
    "t20_leagues": "https://www.cricbuzz.com/cricket-schedule/upcoming-series/league",
    "domestic": "https://www.cricbuzz.com/cricket-schedule/upcoming-series/domestic",
    "women": "https://www.cricbuzz.com/cricket-schedule/upcoming-series/women",
}

# Cricbuzz Team Directories
TEAM_DIRECTORY_URLS = {
    "international": "https://www.cricbuzz.com/cricket-team",
    "domestic": "https://www.cricbuzz.com/cricket-team/domestic",
    "league": "https://www.cricbuzz.com/cricket-team/league",
    "women": "https://www.cricbuzz.com/cricket-team/women",
}

# Cricbuzz CDN Image Pattern
CRICBUZZ_IMAGE_URL = "https://static.cricbuzz.com/a/img/v1/0x0/i1/c{image_id}/i.jpg"

# Network & Client Settings
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT_SECONDS = 20
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.5
REQUEST_DELAY_SECONDS = 0.5

# Partitioning Timezone (for today/tomorrow convenience files)
DEFAULT_TIMEZONE = "Asia/Karachi"

# Validation & Sanity Safeguards
MIN_EXPECTED_MATCHES = 1
SANITY_DROP_THRESHOLD_RATIO = 0.30  # Error if match count drops below 30% of previous run
