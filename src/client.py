"""HTTP client for fetching Cricbuzz schedule pages and assets with retries and rate-limiting."""

import logging
import time
from typing import Dict, Optional
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

from src.config import (
    DEFAULT_USER_AGENT,
    REQUEST_TIMEOUT_SECONDS,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    REQUEST_DELAY_SECONDS,
    SCHEDULE_URLS,
    TEAM_DIRECTORY_URLS,
    CRICBUZZ_IMAGE_URL,
    RAW_DIR,
)

logger = logging.getLogger(__name__)


class CricbuzzClient:
    """Resilient HTTP client for interacting with public Cricbuzz endpoints."""

    def __init__(self, user_agent: Optional[str] = None, timeout: int = REQUEST_TIMEOUT_SECONDS):
        self.timeout = timeout
        self.session = requests.Session()

        # Configure retry strategy
        retries = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.headers = {
            "User-Agent": user_agent or DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.session.headers.update(self.headers)

    def fetch_url(self, url: str) -> str:
        """Fetch content of a URL with error handling and throttling."""
        logger.debug(f"Fetching URL: {url}")
        time.sleep(REQUEST_DELAY_SECONDS)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def fetch_schedule_page(self, category: str = "all") -> str:
        """Fetch raw HTML for a specific schedule category."""
        url = SCHEDULE_URLS.get(category)
        if not url:
            raise ValueError(f"Unknown schedule category: {category}. Valid: {list(SCHEDULE_URLS.keys())}")
        return self.fetch_url(url)

    def fetch_all_schedules(self, save_raw: bool = True) -> Dict[str, str]:
        """Fetch all schedule categories and optionally save snapshots in raw/."""
        raw_pages = {}
        for category, url in SCHEDULE_URLS.items():
            logger.info(f"Fetching schedule category '{category}' from {url}")
            try:
                html = self.fetch_schedule_page(category)
                raw_pages[category] = html
                if save_raw:
                    RAW_DIR.mkdir(parents=True, exist_ok=True)
                    raw_file = RAW_DIR / f"latest_schedule_{category}.html"
                    raw_file.write_text(html, encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to fetch schedule category '{category}': {e}")
        return raw_pages

    def fetch_team_directory(self, category: str = "international") -> str:
        """Fetch raw HTML for a specific team directory tab."""
        url = TEAM_DIRECTORY_URLS.get(category)
        if not url:
            raise ValueError(f"Unknown team directory category: {category}")
        return self.fetch_url(url)

    def fetch_all_team_directories(self) -> Dict[str, str]:
        """Fetch all team directory categories."""
        raw_pages = {}
        for category, url in TEAM_DIRECTORY_URLS.items():
            logger.info(f"Fetching team directory '{category}' from {url}")
            try:
                html = self.fetch_team_directory(category)
                raw_pages[category] = html
            except Exception as e:
                logger.error(f"Failed to fetch team directory '{category}': {e}")
        return raw_pages

    def download_image_bytes(self, image_id: int) -> Optional[bytes]:
        """Download raw image bytes for a Cricbuzz image ID."""
        url = CRICBUZZ_IMAGE_URL.format(image_id=image_id)
        logger.debug(f"Downloading image from {url}")
        try:
            time.sleep(0.1)  # small rate limit
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200 and len(resp.content) > 0:
                return resp.content
            logger.warning(f"Image {image_id} returned status {resp.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Error downloading image {image_id}: {e}")
            return None
