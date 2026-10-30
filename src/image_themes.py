"""
image_themes.py
Dedicated theme configuration model and registry for cricket fixture matchday graphic cards.
Defines category- and format-specific color palettes, procedural patterns, typography choices,
and center divider styles.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Any, Optional


@dataclass(frozen=True)
class CricketTheme:
    """
    Encapsulates all visual styling tokens for a specific cricket competition category or format.
    """
    theme_id: str
    name: str
    background_top: Tuple[int, int, int]
    background_bottom: Tuple[int, int, int]
    primary: Tuple[int, int, int]              # Main brand color
    secondary: Tuple[int, int, int]            # Complementary brand color
    highlight: Tuple[int, int, int]            # Bright accent / glow
    text_primary: Tuple[int, int, int]         # Main title & team text
    text_secondary: Tuple[int, int, int]       # Sub-label & meta text
    panel_color: Tuple[int, int, int, int]     # RGBA card fill
    panel_border: Tuple[int, int, int, int]    # RGBA card border
    pattern: str                               # Background procedural pattern ID
    center_style: str                          # Central divider style ID
    font_family: str = "inter"                 # "inter", "montserrat", or "archivo"
    crest_container_style: str = "glass_plate" # "glass_plate", "halo", "metallic"


THEMES_REGISTRY: Dict[str, CricketTheme] = {
    # 1. INTERNATIONAL: Prestigious Midnight Navy & Royal Blue, Brilliant Gold, Floodlights
    "international": CricketTheme(
        theme_id="international",
        name="International Cricket",
        background_top=(8, 16, 42),
        background_bottom=(12, 26, 68),
        primary=(30, 115, 245),
        secondary=(245, 185, 30),
        highlight=(255, 230, 140),
        text_primary=(255, 255, 255),
        text_secondary=(180, 205, 245),
        panel_color=(16, 28, 64, 215),
        panel_border=(65, 120, 235, 180),
        pattern="stadium_floodlights",
        center_style="gold_energy_vs",
        font_family="montserrat",
        crest_container_style="glass_plate"
    ),

    # 2. T20_LEAGUE: Obsidian / Dark Violet, Electric Neon Cyan & Magenta, High-Energy Trails
    "t20_league": CricketTheme(
        theme_id="t20_league",
        name="T20 Franchise League",
        background_top=(16, 8, 34),
        background_bottom=(26, 12, 54),
        primary=(0, 240, 255),
        secondary=(255, 0, 128),
        highlight=(255, 220, 0),
        text_primary=(255, 255, 255),
        text_secondary=(220, 190, 255),
        panel_color=(24, 14, 46, 225),
        panel_border=(0, 230, 255, 175),
        pattern="t20_neon_trails",
        center_style="neon_electric_vs",
        font_family="archivo",
        crest_container_style="halo"
    ),

    # 3. TEST: Heritage Red Ball Crimson, Deep Charcoal, Antique Gold & Ivory
    "test": CricketTheme(
        theme_id="test",
        name="Test Match Cricket",
        background_top=(34, 10, 14),
        background_bottom=(18, 14, 16),
        primary=(195, 35, 45),
        secondary=(212, 165, 60),
        highlight=(245, 240, 225),
        text_primary=(255, 255, 255),
        text_secondary=(235, 215, 190),
        panel_color=(32, 16, 18, 225),
        panel_border=(212, 165, 60, 180),
        pattern="red_ball_seam",
        center_style="heraldic_gold_vs",
        font_family="montserrat",
        crest_container_style="metallic"
    ),

    # 4. DOMESTIC: Deep Forest & Emerald Turf, Amber Gold, Outfield Geometry
    "domestic": CricketTheme(
        theme_id="domestic",
        name="Domestic Cricket",
        background_top=(8, 28, 18),
        background_bottom=(14, 22, 16),
        primary=(20, 185, 95),
        secondary=(240, 175, 30),
        highlight=(200, 255, 220),
        text_primary=(255, 255, 255),
        text_secondary=(180, 235, 205),
        panel_color=(14, 32, 22, 220),
        panel_border=(20, 190, 105, 175),
        pattern="pitch_outfield_geometry",
        center_style="classic_green_vs",
        font_family="inter",
        crest_container_style="glass_plate"
    ),

    # 5. WOMEN: Deep Plum & Violet, Vivid Magenta & Rose Gold, Luminous Waves
    "women": CricketTheme(
        theme_id="women",
        name="Women's Cricket",
        background_top=(26, 8, 34),
        background_bottom=(42, 12, 52),
        primary=(255, 45, 125),
        secondary=(255, 120, 80),
        highlight=(255, 215, 230),
        text_primary=(255, 255, 255),
        text_secondary=(245, 195, 225),
        panel_color=(36, 14, 44, 225),
        panel_border=(255, 50, 130, 180),
        pattern="luminous_concentric_waves",
        center_style="rose_glow_vs",
        font_family="montserrat",
        crest_container_style="halo"
    ),

    # 6. DEFAULT / OTHER: Deep Slate, Electric Cyan, Warm Amber
    "default": CricketTheme(
        theme_id="default",
        name="Cricket Match",
        background_top=(12, 16, 28),
        background_bottom=(18, 24, 40),
        primary=(0, 190, 250),
        secondary=(255, 130, 35),
        highlight=(240, 248, 255),
        text_primary=(255, 255, 255),
        text_secondary=(185, 205, 235),
        panel_color=(18, 26, 46, 220),
        panel_border=(50, 130, 225, 175),
        pattern="stadium_floodlights",
        center_style="gold_energy_vs",
        font_family="inter",
        crest_container_style="glass_plate"
    ),
}


def get_cricket_theme(match_or_category: Any) -> CricketTheme:
    """
    Intelligently resolves the optimal CricketTheme based on match attributes or category string.
    Priority order:
    1. Format == 'TEST' -> Test match theme (heritage red & gold)
    2. Category == 'WOMEN' -> Women's cricket theme
    3. Category == 'T20_LEAGUE' -> Franchise T20 theme (electric neon)
    4. Category == 'INTERNATIONAL' -> International cricket theme
    5. Category == 'DOMESTIC' -> Domestic cricket theme
    6. Fallback -> Default theme
    """
    if isinstance(match_or_category, str):
        key = match_or_category.lower().strip()
        if key in THEMES_REGISTRY:
            return THEMES_REGISTRY[key]
        if key in ("t20_leagues", "league", "t20"):
            return THEMES_REGISTRY["t20_league"]
        if key in ("intl", "international"):
            return THEMES_REGISTRY["international"]
        return THEMES_REGISTRY.get("default", THEMES_REGISTRY["international"])

    # Match dict or NormalizedMatch model
    category = ""
    fmt = ""

    if hasattr(match_or_category, "category"):
        category = str(match_or_category.category or "").upper()
    elif isinstance(match_or_category, dict):
        category = str(match_or_category.get("category", "")).upper()

    if hasattr(match_or_category, "format"):
        fmt = str(match_or_category.format or "").upper()
    elif isinstance(match_or_category, dict):
        fmt = str(match_or_category.get("format", "")).upper()

    # 1. Format check: Red ball international test matches get prestigious Test theme
    if fmt == "TEST" and category in ("INTERNATIONAL", ""):
        return THEMES_REGISTRY["test"]

    # 2. Category checks
    if category == "WOMEN":
        return THEMES_REGISTRY["women"]
    if category in ("T20_LEAGUE", "T20_LEAGUES", "LEAGUE"):
        return THEMES_REGISTRY["t20_league"]
    if category == "DOMESTIC":
        return THEMES_REGISTRY["domestic"]
    if fmt == "TEST":
        return THEMES_REGISTRY["test"]
    if category == "INTERNATIONAL":
        return THEMES_REGISTRY["international"]

    return THEMES_REGISTRY["default"]
