"""Image manager for downloading, validating, converting, and caching team assets locally."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from PIL import Image

from src.config import TEAM_IMAGES_DIR, FLAG_IMAGES_DIR
from src.models import NormalizedTeam

logger = logging.getLogger(__name__)


class TeamImageManager:
    """Manages downloading and local caching of team logos and flag assets."""

    def __init__(self, team_dir: Optional[Path] = None, flag_dir: Optional[Path] = None, max_workers: int = 8):
        self.team_dir = team_dir or TEAM_IMAGES_DIR
        self.flag_dir = flag_dir or FLAG_IMAGES_DIR
        self.team_dir.mkdir(parents=True, exist_ok=True)
        self.flag_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers

    def is_valid_image_file(self, file_path: Path) -> bool:
        """Check if an existing file is a valid image with sensible dimensions."""
        if not file_path.exists() or file_path.stat().st_size < 100:
            return False
        try:
            with Image.open(file_path) as img:
                img.verify()
            with Image.open(file_path) as img:
                return img.width >= 10 and img.height >= 10
        except Exception:
            return False

    def validate_and_convert_bytes(self, image_bytes: bytes) -> Optional[bytes]:
        """
        Validate raw image bytes and convert to standard PNG format.
        Rejects HTML errors, corrupted byte streams, or 1x1 placeholder GIFs.
        """
        if not image_bytes or len(image_bytes) < 100:
            return None

        header_sample = image_bytes[:64].lower()
        if b"<html" in header_sample or b"<!doctype" in header_sample:
            logger.warning("Image bytes start with HTML tags; rejecting non-image payload")
            return None

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                if img.width < 10 or img.height < 10:
                    logger.warning(f"Image too small ({img.width}x{img.height}); rejecting placeholder")
                    return None

                output_buf = io.BytesIO()
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    converted = img.convert("RGBA")
                else:
                    converted = img.convert("RGB")

                converted.save(output_buf, format="PNG", optimize=True)
                return output_buf.getvalue()
        except Exception as e:
            logger.warning(f"Failed to process and convert image bytes: {e}")
            return None

    def _download_single_team_logo(self, team: NormalizedTeam, client_downloader) -> Tuple[int, str]:
        """Worker task to download and save one team logo."""
        dest_file = self.team_dir / f"{team.id}.png"
        if not team.imageId:
            return team.id, "missing_image_id"

        raw_bytes = client_downloader.download_image_bytes(team.imageId)
        if not raw_bytes:
            return team.id, "download_failed"

        png_bytes = self.validate_and_convert_bytes(raw_bytes)
        if not png_bytes:
            return team.id, "validation_failed"

        try:
            dest_file.write_bytes(png_bytes)
            return team.id, "success"
        except Exception as e:
            logger.error(f"Failed to write image for team {team.id}: {e}")
            return team.id, "write_failed"

    def sync_team_images(
        self,
        teams: Dict[int, NormalizedTeam],
        client_downloader,
        active_team_ids: Optional[Set[int]] = None,
        force_redownload: bool = False,
    ) -> Tuple[int, int, int]:
        """
        Download and cache team logos using concurrent thread workers.
        Prioritizes teams playing in upcoming matches.
        Returns (downloaded_count, skipped_count, failed_count).
        """
        downloaded = 0
        skipped = 0
        failed = 0

        # Determine which teams need downloading
        pending_teams: List[NormalizedTeam] = []
        for team_id, team in teams.items():
            dest_file = self.team_dir / f"{team_id}.png"
            if not force_redownload and self.is_valid_image_file(dest_file):
                skipped += 1
            else:
                if team.imageId:
                    pending_teams.append(team)
                else:
                    failed += 1

        if not pending_teams:
            return downloaded, skipped, failed

        # Sort pending teams: active match teams first
        active_ids = active_team_ids or set()
        pending_teams.sort(key=lambda t: 0 if t.id in active_ids else 1)

        logger.info(f"Downloading logos for {len(pending_teams)} teams using {self.max_workers} workers...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_team = {
                executor.submit(self._download_single_team_logo, team, client_downloader): team
                for team in pending_teams
            }
            for future in as_completed(future_to_team):
                team = future_to_team[future]
                try:
                    t_id, status = future.result()
                    if status == "success":
                        downloaded += 1
                    else:
                        failed += 1
                        logger.warning(f"Team {team.id} ({team.name}) logo failed with status: {status}")
                except Exception as exc:
                    failed += 1
                    logger.error(f"Team {team.id} ({team.name}) generated an exception: {exc}")

        return downloaded, skipped, failed
