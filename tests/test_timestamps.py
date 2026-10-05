"""Tests for timestamp consistency and timezone partitioning."""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pytest
from src.normalizer import CricketNormalizer
from src.generator import OutputGenerator
from src.models import NormalizedMatch
from unittest.mock import MagicMock


def test_timestamp_utc_conversion():
    norm = CricketNormalizer()
    # 2026-10-06 00:00:00 UTC = 1791244800000 ms
    epoch = 1791244800000
    iso = norm.format_iso_utc(epoch)
    assert iso == "2026-10-06T00:00:00Z"


def test_today_tomorrow_partitioning():
    storage_mock = MagicMock()
    generator = OutputGenerator(storage_mock, tz_name="Asia/Karachi")

    # Reference time: 2026-10-05 12:00:00 PKT (07:00:00 UTC)
    ref_dt = datetime(2026, 10, 5, 7, 0, 0, tzinfo=timezone.utc)

    # Match 1: Today in PKT (2026-10-05 15:00:00 PKT -> 10:00:00 UTC)
    m1_dt = datetime(2026, 10, 5, 10, 0, 0, tzinfo=timezone.utc)
    m1_epoch = int(m1_dt.timestamp() * 1000)

    # Match 2: Tomorrow in PKT (2026-10-06 15:00:00 PKT -> 10:00:00 UTC)
    m2_dt = datetime(2026, 10, 6, 10, 0, 0, tzinfo=timezone.utc)
    m2_epoch = int(m2_dt.timestamp() * 1000)

    # Match 3: 5 days later
    m3_dt = datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    m3_epoch = int(m3_dt.timestamp() * 1000)

    matches = [
        NormalizedMatch(
            id=1, sourceMatchId=1, seriesName="S1", matchDesc="M1", format="T20",
            teamAId=1, teamBId=2, teamAName="T1", teamBName="T2", teamAShort="T1", teamBShort="T2",
            startTime=m1_epoch, startTimeUtc=m1_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), venue="V1",
        ),
        NormalizedMatch(
            id=2, sourceMatchId=2, seriesName="S1", matchDesc="M2", format="T20",
            teamAId=1, teamBId=2, teamAName="T1", teamBName="T2", teamAShort="T1", teamBShort="T2",
            startTime=m2_epoch, startTimeUtc=m2_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), venue="V1",
        ),
        NormalizedMatch(
            id=3, sourceMatchId=3, seriesName="S1", matchDesc="M3", format="T20",
            teamAId=1, teamBId=2, teamAName="T1", teamBName="T2", teamAShort="T1", teamBShort="T2",
            startTime=m3_epoch, startTimeUtc=m3_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), venue="V1",
        ),
    ]

    index = generator.generate_all_outputs(matches, {}, {}, {}, now_dt=ref_dt)

    assert index.stats.todayMatches == 1
    assert index.stats.tomorrowMatches == 1
    assert index.stats.totalMatches == 3
