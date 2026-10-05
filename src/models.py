"""Pydantic data models for the Cricket Data Repository."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class NormalizedTeam(BaseModel):
    """Normalized team entity."""
    id: int
    name: str
    shortName: str
    country: Optional[str] = None
    category: Optional[str] = None
    imageId: Optional[int] = None
    logo: Optional[str] = None
    flag: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None


class NormalizedSeries(BaseModel):
    """Normalized tournament or series entity."""
    id: int
    name: str
    category: str = "OTHER"
    matchCount: Optional[int] = 0


class NormalizedVenue(BaseModel):
    """Normalized venue entity."""
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None


class NormalizedMatch(BaseModel):
    """Normalized match fixture entity."""
    id: int
    source: str = "cricbuzz"
    sourceMatchId: int

    seriesId: Optional[int] = None
    seriesName: str
    category: str = "OTHER"

    matchDesc: str
    format: str

    teamAId: int
    teamBId: int
    teamAName: str
    teamBName: str
    teamAShort: str
    teamBShort: str
    teamALogo: Optional[str] = None
    teamBLogo: Optional[str] = None

    startTime: int  # epoch milliseconds (UTC)
    startTimeUtc: str  # ISO-8601 UTC
    endTime: Optional[int] = None

    venueId: Optional[int] = None
    venue: str
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None

    status: str = "UPCOMING"


class DatasetStats(BaseModel):
    """Statistics for dataset index."""
    totalMatches: int = 0
    upcomingMatches: int = 0
    todayMatches: int = 0
    tomorrowMatches: int = 0
    internationalMatches: int = 0
    t20LeagueMatches: int = 0
    domesticMatches: int = 0
    womenMatches: int = 0
    totalTeams: int = 0
    totalSeries: int = 0
    totalVenues: int = 0


class DatasetIndex(BaseModel):
    """Index metadata file describing repository freshness and statistics."""
    updatedAt: str
    source: str = "cricbuzz"
    schemaVersion: int = 1
    timezone: str = "Asia/Karachi"
    stats: DatasetStats


class ScrapeSummary(BaseModel):
    """Execution summary report."""
    matchesDiscovered: int = 0
    upcoming: int = 0
    today: int = 0
    tomorrow: int = 0
    international: int = 0
    t20Leagues: int = 0
    domestic: int = 0
    women: int = 0
    uniqueTeams: int = 0
    newTeams: int = 0
    teamImagesCached: int = 0
    missingImages: int = 0
    uniqueSeries: int = 0
    uniqueVenues: int = 0
    validationPassed: bool = False
    testsPassed: bool = False
