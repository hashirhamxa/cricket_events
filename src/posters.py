"""
posters.py
High-performance, broadcast-grade matchday graphic generator for cricket fixtures using Pillow.
Features:
- Category & format-specific visual themes (International, T20 League, Test, Domestic, Women, Default)
- 2x supersampled internal rendering (2400x1260 -> 1200x630 Lanczos) for razor-sharp antialiasing
- High-res local team crests with aspect-ratio preservation and soft back-glow
- Elegant geometric fallback shields for unbranded/TBC teams
- Format pill badges ([T20], [ODI], [TEST]) and tournament series header
- Intelligent text-fitting and multi-line wrapping (no blunt truncation)
- Stylized dynamic 'VS' center divider with theme-specific lighting & energy accents
- Centered footer badge with vector calendar, venue, city, and match timing
- Concurrent multi-threaded batch rendering
"""

import hashlib
import io
import logging
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Union

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from src.config import BASE_DIR, TEAM_IMAGES_DIR, MATCH_IMAGES_DIR, FONTS_DIR, MATCH_IMAGES_RAW_BASE_URL
from src.image_themes import CricketTheme, get_cricket_theme, THEMES_REGISTRY
from src.models import NormalizedMatch

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Typography & Font Loading Engine
# ==============================================================================

def get_font(
    size: int,
    weight: str = "bold",
    family: str = "inter"
) -> ImageFont.FreeTypeFont:
    """
    Loads font with priority for bundled repository fonts (Inter, Montserrat, Archivo),
    applying the requested weight ('regular', 'medium', 'semibold', 'bold', 'extrabold', 'black').
    Falls back gracefully to system fonts and Pillow default.
    """
    bundled_map = {
        "inter": os.path.join(str(FONTS_DIR), "Inter.ttf"),
        "montserrat": os.path.join(str(FONTS_DIR), "Montserrat.ttf"),
        "archivo": os.path.join(str(FONTS_DIR), "Archivo.ttf")
    }

    target_path = bundled_map.get(family.lower(), bundled_map["inter"])
    if not os.path.exists(target_path):
        for b_path in bundled_map.values():
            if os.path.exists(b_path):
                target_path = b_path
                break

    if os.path.exists(target_path):
        try:
            f = ImageFont.truetype(target_path, size=size)
            weight_map = {
                "regular": "Regular",
                "medium": "Medium",
                "semibold": "SemiBold",
                "bold": "Bold",
                "extrabold": "ExtraBold",
                "black": "Black"
            }
            target_var = weight_map.get(weight.lower(), "Bold")
            var_names = [v.decode() for v in f.get_variation_names()] if hasattr(f, "get_variation_names") else []
            if target_var in var_names:
                f.set_variation_by_name(target_var)
            elif "Bold" in var_names and weight != "regular":
                f.set_variation_by_name("Bold")
            return f
        except Exception:
            pass

    # Fallback to system fonts
    is_bold = weight.lower() in ["bold", "extrabold", "black", "semibold"]
    if is_bold:
        system_candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
            "/System/Library/Fonts/HelveticaNeue-Bold.otf"
        ]
    else:
        system_candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/System/Library/Fonts/HelveticaNeue.otf"
        ]

    for p in system_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                continue

    return ImageFont.load_default()


def fit_team_name_lines(
    name: str,
    max_width: int,
    initial_size: int = 62,
    min_size: int = 32,
    family: str = "inter"
) -> Tuple[List[str], ImageFont.FreeTypeFont, int]:
    """
    Intelligently fits a team name into 1 or 2 lines with optimal font sizing.
    Returns (lines_of_text, font_object, total_height).
    """
    clean_name = re.sub(r"\s+", " ", name.strip())

    # 1. Try single line with decreasing font sizes
    for size in range(initial_size, min_size - 1, -2):
        f = get_font(size=size, weight="bold", family=family)
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), clean_name, font=f)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            h = bbox[3] - bbox[1]
            return [clean_name], f, h

    # 2. Split into two balanced lines
    words = clean_name.split(" ")
    if len(words) > 1:
        mid = (len(words) + 1) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

        for size in range(initial_size - 6, min_size - 1, -2):
            f = get_font(size=size, weight="bold", family=family)
            dummy_img = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            bbox1 = draw.textbbox((0, 0), line1, font=f)
            bbox2 = draw.textbbox((0, 0), line2, font=f)
            w1 = bbox1[2] - bbox1[0]
            w2 = bbox2[2] - bbox2[0]
            if max(w1, w2) <= max_width:
                h1 = bbox1[3] - bbox1[1]
                h2 = bbox2[3] - bbox2[1]
                return [line1, line2], f, h1 + h2 + 10

    # 3. Truncate with ellipsis at min_size as final fallback
    f = get_font(size=min_size, weight="bold", family=family)
    truncated = clean_name
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    while len(truncated) > 3:
        bbox = draw.textbbox((0, 0), truncated + "...", font=f)
        if (bbox[2] - bbox[0]) <= max_width:
            h = bbox[3] - bbox[1]
            return [truncated + "..."], f, h
        truncated = truncated[:-1]

    return [clean_name], f, 40


# ==============================================================================
# 2. Crest Pre-Processing & Fallback Generation
# ==============================================================================

def autocrop_transparent_margins(img: Image.Image, padding: int = 6) -> Image.Image:
    """Removes empty transparent border around logos to maximize crest clarity and size."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        w, h = img.size
        x0 = max(0, bbox[0] - padding)
        y0 = max(0, bbox[1] - padding)
        x1 = min(w, bbox[2] + padding)
        y1 = min(h, bbox[3] + padding)
        return img.crop((x0, y0, x1, y1))
    return img


def load_local_team_crest(team_id: int, logo_rel_path: Optional[str] = None) -> Optional[Image.Image]:
    """Loads team crest from repository cache (images/teams/{team_id}.png)."""
    candidates = []
    if logo_rel_path:
        candidates.append(BASE_DIR / logo_rel_path)
    candidates.append(TEAM_IMAGES_DIR / f"{team_id}.png")

    for path in candidates:
        if path.exists() and path.is_file():
            try:
                img = Image.open(path).convert("RGBA")
                return autocrop_transparent_margins(img)
            except Exception:
                continue
    return None


def draw_themed_crest_plate(
    base: Image.Image,
    logo_img: Optional[Image.Image],
    team_name: str,
    team_short: str,
    cx: int,
    cy: int,
    theme: CricketTheme,
    card_size: int = 420
):
    """
    Renders high-res team crest inside a frosted translucent glass plate with ambient back-glow.
    If logo is missing, renders an elegant geometric shield with team short name.
    All coordinates in 2x supersampled space.
    """
    card_w = card_size
    card_h = card_size
    rx = card_w // 2
    ry = card_h // 2
    x0 = cx - rx
    y0 = cy - ry
    x1 = cx + rx
    y1 = cy + ry

    draw_base = ImageDraw.Draw(base)

    # 1. Subtle card drop shadow
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([x0 - 6, y0 - 2, x1 + 6, y1 + 16], radius=36, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    base.alpha_composite(shadow)

    # 2. Main Glass Panel Plate
    draw_base.rounded_rectangle([x0, y0, x1, y1], radius=32, fill=theme.panel_color, outline=theme.panel_border, width=4)

    # 3. Soft internal radial glow behind crest
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    hr, hg, hb = theme.highlight
    gdraw.ellipse([cx - 150, cy - 150, cx + 150, cy + 150], fill=(hr, hg, hb, 35))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=24))
    base.alpha_composite(glow)

    # 4. Draw Logo or Geometric Fallback Shield
    if logo_img is not None:
        lw, lh = logo_img.size
        max_logo_size = card_h - 76  # ~344px max within card
        ratio = min(max_logo_size / lw, max_logo_size / lh)
        nw = max(1, int(lw * ratio))
        nh = max(1, int(lh * ratio))

        resized_logo = logo_img.resize((nw, nh), Image.Resampling.LANCZOS)
        pos_x = cx - nw // 2
        pos_y = cy - nh // 2
        base.paste(resized_logo, (pos_x, pos_y), resized_logo)
    else:
        # High-end Geometric Shield Fallback Badge
        initials = (team_short or team_name[:3] or "TBA").upper()
        if len(initials) > 4:
            initials = initials[:3]

        shield_w = 260
        shield_h = 280
        sx0 = cx - shield_w // 2
        sy0 = cy - shield_h // 2
        sx1 = cx + shield_w // 2
        sy1 = cy + shield_h // 2

        # Shield polygon (pointed bottom)
        shield_pts = [
            (sx0 + 24, sy0),
            (sx1 - 24, sy0),
            (sx1, sy0 + 24),
            (sx1, sy0 + shield_h * 0.65),
            (cx, sy1),
            (sx0, sy0 + shield_h * 0.65),
            (sx0, sy0 + 24)
        ]
        pr, pg, pb = theme.primary
        draw_base.polygon(shield_pts, fill=(pr, pg, pb, 65), outline=theme.highlight)
        f_init = get_font(size=88, weight="black", family=theme.font_family)
        bbox = draw_base.textbbox((0, 0), initials, font=f_init)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw_base.text((cx - tw // 2, cy - th // 2 - 12), initials, fill=theme.text_primary, font=f_init)


# ==============================================================================
# 3. Vector Icons & Procedural Background
# ==============================================================================

def draw_vector_calendar_icon(
    draw: ImageDraw.Draw,
    x: int,
    y: int,
    size: int = 36,
    color: Tuple[int, int, int] = (255, 255, 255)
):
    """Renders a clean vector calendar icon directly with Pillow."""
    w = size
    h = int(size * 0.88)
    draw.rounded_rectangle([x, y + 6, x + w, y + h + 6], radius=6, fill=(color[0], color[1], color[2], 35), outline=color, width=3)
    draw.line([(x, y + 16), (x + w, y + 16)], fill=color, width=3)
    draw.line([(x + 8, y + 1), (x + 8, y + 9)], fill=color, width=3)
    draw.line([(x + w - 8, y + 1), (x + w - 8, y + 9)], fill=color, width=3)
    for gx in [x + 9, x + w // 2, x + w - 9]:
        for gy in [y + 24, y + 31]:
            draw.point((gx, gy), fill=color)


def create_themed_background(
    theme: CricketTheme,
    width: int = 2400,
    height: int = 1260,
    seed_str: str = ""
) -> Image.Image:
    """
    Creates a layered procedural background tailored to the cricket theme.
    Includes top-to-bottom multi-stop gradient, team crest spotlights, and procedural patterns.
    """
    # 1. Base Vertical Multi-stop Gradient
    img = Image.new("RGBA", (width, height), (theme.background_top[0], theme.background_top[1], theme.background_top[2], 255))
    draw = ImageDraw.Draw(img)

    r1, g1, b1 = theme.background_top
    r2, g2, b2 = theme.background_bottom
    for y in range(height):
        factor = y / height
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # 2. Team Crest Soft Ambient Spotlights (left and right)
    spotlights = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    spot_draw = ImageDraw.Draw(spotlights)

    left_cx = 640
    right_cx = 1760
    center_y = 580

    spot_r = 460
    pr, pg, pb = theme.primary
    sr, sg, sb = theme.secondary
    hr, hg, hb = theme.highlight

    for r in range(spot_r, 0, -25):
        alpha = int((1.0 - (r / spot_r)) * 48)
        spot_draw.ellipse([left_cx - r, center_y - r * 0.88, left_cx + r, center_y + r * 0.88], fill=(pr, pg, pb, alpha))
        spot_draw.ellipse([right_cx - r, center_y - r * 0.88, right_cx + r, center_y + r * 0.88], fill=(sr, sg, sb, alpha))

    img = Image.alpha_composite(img, spotlights)

    # 3. Procedural Cricket Geometry Patterns
    pattern_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(pattern_layer)

    p = theme.pattern

    if p == "stadium_floodlights":
        # Stadium Floodlight Beams angling across the top and sides
        beams = [
            [(0, 0), (800, 0), (1400, height), (600, height)],
            [(width, 0), (width - 800, 0), (width - 1400, height), (width - 600, height)]
        ]
        pdraw.polygon(beams[0], fill=(hr, hg, hb, 12))
        pdraw.polygon(beams[1], fill=(sr, sg, sb, 12))
        # Concentric pitch perimeter arcs
        for rad in range(300, 1200, 160):
            pdraw.arc([width // 2 - rad, height // 2 - rad - 80, width // 2 + rad, height // 2 + rad - 80], 0, 360, fill=(hr, hg, hb, 16), width=2)

    elif p == "t20_neon_trails":
        # Dynamic angled high-voltage energy slashes & modern light trails
        pdraw.polygon([(0, 0), (width * 0.35, 0), (width * 0.15, height), (0, height)], fill=(pr, pg, pb, 22))
        pdraw.polygon([(width * 0.65, 0), (width, 0), (width, height), (width * 0.85, height)], fill=(sr, sg, sb, 22))
        pdraw.line([(width * 0.35, 0), (width * 0.15, height)], fill=(pr, pg, pb, 90), width=6)
        pdraw.line([(width * 0.65, 0), (width * 0.85, height)], fill=(sr, sg, sb, 90), width=6)
        # Laser cross slashes
        for i in range(4):
            y_off = 180 + i * 220
            pdraw.line([(0, y_off), (width, y_off + 160)], fill=(hr, hg, hb, 20), width=3)

    elif p == "red_ball_seam":
        # Heritage Red Ball Seam Curves & Dignified Heraldic Lines
        for offset in [-60, 0, 60]:
            pdraw.arc([width // 2 - 800, -300 + offset, width // 2 + 800, height + 500 + offset], 30, 150, fill=(sr, sg, sb, 32), width=4)
        # Vertical stadium framing pillars
        pdraw.line([(left_cx, 80), (left_cx, height - 120)], fill=(sr, sg, sb, 28), width=3)
        pdraw.line([(right_cx, 80), (right_cx, height - 120)], fill=(sr, sg, sb, 28), width=3)

    elif p == "pitch_outfield_geometry":
        # Outfield geometric turf rings and pitch boundary lines
        for rad in range(250, 1050, 140):
            pdraw.arc([width // 2 - rad, height // 2 - rad - 40, width // 2 + rad, height // 2 + rad - 40], -120, 60, fill=(pr, pg, pb, 30), width=3)
        pdraw.line([(width * 0.2, 0), (width * 0.4, height)], fill=(sr, sg, sb, 25), width=4)
        pdraw.line([(width * 0.8, 0), (width * 0.6, height)], fill=(sr, sg, sb, 25), width=4)

    elif p == "luminous_concentric_waves":
        # Sweeping concentric radiant curves and rose gold particle trails
        for rad in range(280, 1150, 130):
            pdraw.arc([width // 2 - rad, height // 2 - rad - 50, width // 2 + rad, height // 2 + rad - 50], 0, 180, fill=(pr, pg, pb, 32), width=4)
            pdraw.arc([width // 2 - rad + 50, height // 2 - rad - 50, width // 2 + rad + 50, height // 2 + rad - 50], 0, 180, fill=(sr, sg, sb, 26), width=3)

    img = Image.alpha_composite(img, pattern_layer)
    return img


# ==============================================================================
# 4. Center 'VS' Divider (Dynamic Energy Accents)
# ==============================================================================

def draw_themed_center_divider(
    draw: ImageDraw.Draw,
    cx: int,
    cy: int,
    theme: CricketTheme,
    base: Optional[Image.Image] = None
):
    """
    Renders stylized bold italic 'VS' with dynamic energy lightning slashes.
    All coordinates in 2x supersampled space.
    """
    vs_font = get_font(size=130, weight="black", family="archivo")
    text = "VS"
    bbox = draw.textbbox((0, 0), text, font=vs_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = cx - tw // 2
    ty = cy - th // 2 - 8

    # Dynamic lightning / angled slash accents
    lightning_tr = [
        (cx + 46, cy - 25),
        (cx + 58, cy - 64),
        (cx + 50, cy - 68),
        (cx + 72, cy - 115),
        (cx + 66, cy - 118),
        (cx + 84, cy - 150)
    ]
    lightning_bl = [
        (cx - 46, cy + 25),
        (cx - 58, cy + 64),
        (cx - 50, cy + 68),
        (cx - 72, cy + 115),
        (cx - 66, cy + 118),
        (cx - 84, cy + 150)
    ]

    pr, pg, pb = theme.primary
    sr, sg, sb = theme.secondary
    hr, hg, hb = theme.highlight

    if base is not None:
        shadow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow_layer)
        sdraw.line(lightning_tr, fill=(0, 0, 0, 200), width=12)
        sdraw.line(lightning_bl, fill=(0, 0, 0, 200), width=12)
        sdraw.text((tx + 6, ty + 8), text, font=vs_font, fill=(0, 0, 0, 220))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=8))
        base.alpha_composite(shadow_layer)

    # Accent color lightning slashes
    draw.line(lightning_tr, fill=(pr, pg, pb, 230), width=6)
    draw.line(lightning_bl, fill=(sr, sg, sb, 230), width=6)

    # Outer glow / highlight text
    draw.text((tx, ty), text, font=vs_font, fill=(255, 255, 255, 255))


# ==============================================================================
# 5. Format Pill Badge & Header Lockup
# ==============================================================================

def draw_format_badge(
    draw: ImageDraw.Draw,
    fmt: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont
) -> Tuple[int, int]:
    """
    Renders format pill badge (e.g. 'T20', 'ODI', 'TEST').
    Returns (badge_width, badge_height).
    """
    fmt_clean = (fmt or "MATCH").upper()
    if fmt_clean == "T20":
        bg_color = (0, 200, 240, 220)
        border_color = (0, 240, 255, 255)
        text_color = (10, 20, 40)
    elif fmt_clean == "ODI":
        bg_color = (245, 175, 25, 220)
        border_color = (255, 225, 100, 255)
        text_color = (20, 14, 4)
    elif fmt_clean == "TEST":
        bg_color = (195, 30, 45, 220)
        border_color = (255, 215, 120, 255)
        text_color = (255, 255, 255)
    else:
        bg_color = (60, 80, 120, 220)
        border_color = (160, 190, 240, 255)
        text_color = (255, 255, 255)

    bbox = draw.textbbox((0, 0), fmt_clean, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    bw = tw + 36
    bh = th + 20

    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=bh // 2, fill=bg_color, outline=border_color, width=3)
    draw.text((x + 18, y + (bh - th) // 2 - 3), fmt_clean, fill=text_color, font=font)
    return bw, bh


def format_date_display(date_str: str) -> str:
    """Formats '2026-10-30T03:30:00Z' or '2026-10-30' into 'FRIDAY, 30 OCT 2026'."""
    try:
        if "T" in date_str:
            d = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return d.strftime("%A, %d %b %Y").upper()
        d = date.fromisoformat(date_str)
        return d.strftime("%A, %d %b %Y").upper()
    except Exception:
        return date_str.upper() if date_str else "UPCOMING FIXTURE"


# ==============================================================================
# 6. Complete Match Card Generator
# ==============================================================================

def generate_match_card(
    match: Union[Dict[str, Any], NormalizedMatch],
    output_path: Union[str, Path],
    width: int = 1200,
    height: int = 630
) -> str:
    """
    Renders and saves the complete cricket matchday fixture graphic using 2x supersampling
    (2400x1260 -> 1200x630 Lanczos).
    Hierarchy:
    1. Centered Tournament / Series Pill Header with Format Badge and Match Description
    2. Large prominent team cards (crest plates with glass backplate & glow)
    3. Dynamic energy 'VS' central divider
    4. Bold multi-line team names below cards
    5. Clean centered footer plate with vector calendar, venue, city, and time
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert NormalizedMatch to dict if necessary
    m = match.model_dump() if hasattr(match, "model_dump") else (match if isinstance(match, dict) else dict(match))

    theme = get_cricket_theme(m)

    # 2x supersampling dimensions
    w2 = width * 2
    h2 = height * 2

    match_id = str(m.get("id", ""))
    img2 = create_themed_background(theme=theme, width=w2, height=h2, seed_str=match_id)
    draw2 = ImageDraw.Draw(img2)

    # --------------------------------------------------------------------------
    # 1. Header: Tournament / Series Lockup with Format Badge
    # --------------------------------------------------------------------------
    header_cy = 145
    series_name = (m.get("seriesName") or theme.name).upper().strip()
    match_desc = (m.get("matchDesc") or "").strip().upper()
    match_format = (m.get("format") or "").strip().upper()

    # Calculate Header Typography
    f_series_size = 50
    f_desc_size = 32
    f_format_size = 28

    f_series = get_font(size=f_series_size, weight="black", family=theme.font_family)
    f_desc = get_font(size=f_desc_size, weight="bold", family=theme.font_family)
    f_badge = get_font(size=f_format_size, weight="black", family="archivo")

    # Format badge width
    dummy_draw = ImageDraw.Draw(img2)
    b_badge_text = dummy_draw.textbbox((0, 0), match_format or "MATCH", font=f_badge)
    badge_w = (b_badge_text[2] - b_badge_text[0]) + 36
    badge_h = (b_badge_text[3] - b_badge_text[1]) + 20

    # Ensure series name fits horizontally
    bbox_s = dummy_draw.textbbox((0, 0), series_name, font=f_series)
    while (bbox_s[2] - bbox_s[0]) > (w2 - 400) and f_series_size > 30:
        f_series_size -= 2
        f_series = get_font(size=f_series_size, weight="black", family=theme.font_family)
        bbox_s = dummy_draw.textbbox((0, 0), series_name, font=f_series)

    tw_s = bbox_s[2] - bbox_s[0]
    th_s = bbox_s[3] - bbox_s[1]

    # Combine Series + Sub-desc in Header Pill
    has_sub = bool(match_desc)
    header_pill_h = 130 if has_sub else 90
    header_pill_w = max(tw_s + badge_w + 120, 720)
    if header_pill_w > (w2 - 120):
        header_pill_w = w2 - 120

    h_x0 = (w2 - header_pill_w) // 2
    h_y0 = header_cy - header_pill_h // 2
    h_x1 = h_x0 + header_pill_w
    h_y1 = h_y0 + header_pill_h

    # Header frosted pill background
    draw2.rounded_rectangle([h_x0 - 4, h_y0 - 4, h_x1 + 4, h_y1 + 4], radius=28, fill=(0, 0, 0, 110))
    draw2.rounded_rectangle([h_x0, h_y0, h_x1, h_y1], radius=26, fill=theme.panel_color, outline=theme.panel_border, width=4)

    # Place Format Badge & Series Name
    content_y = h_y0 + (22 if has_sub else (header_pill_h - th_s) // 2 - 4)
    total_top_row_w = badge_w + 24 + tw_s
    top_row_x0 = (w2 - total_top_row_w) // 2

    # Draw format badge
    draw_format_badge(draw2, match_format, top_row_x0, content_y - 2, f_badge)
    # Draw series name text
    draw2.text((top_row_x0 + badge_w + 24, content_y), series_name, fill=theme.text_primary, font=f_series)

    # Draw sub-description (e.g. '1st T20I' or 'Group D')
    if has_sub:
        bbox_d = dummy_draw.textbbox((0, 0), match_desc, font=f_desc)
        tw_d = bbox_d[2] - bbox_d[0]
        desc_x = (w2 - tw_d) // 2
        desc_y = content_y + th_s + 18
        draw2.text((desc_x, desc_y), match_desc, fill=theme.highlight, font=f_desc)

    # --------------------------------------------------------------------------
    # 2. Team Cards (Left & Right)
    # --------------------------------------------------------------------------
    left_cx = 640
    right_cx = 1760
    card_cy = 580

    team_a_id = m.get("teamAId", 0)
    team_b_id = m.get("teamBId", 0)
    team_a_name = m.get("teamAName", "Team A")
    team_b_name = m.get("teamBName", "Team B")
    team_a_short = m.get("teamAShort", "")
    team_b_short = m.get("teamBShort", "")

    team_a_logo_path = m.get("teamALogo")
    team_b_logo_path = m.get("teamBLogo")

    logo_a = load_local_team_crest(team_a_id, team_a_logo_path)
    logo_b = load_local_team_crest(team_b_id, team_b_logo_path)

    draw_themed_crest_plate(img2, logo_a, team_a_name, team_a_short, left_cx, card_cy, theme, card_size=420)
    draw_themed_crest_plate(img2, logo_b, team_b_name, team_b_short, right_cx, card_cy, theme, card_size=420)

    # --------------------------------------------------------------------------
    # 3. Dynamic Center 'VS' Divider
    # --------------------------------------------------------------------------
    draw_themed_center_divider(
        draw2,
        cx=w2 // 2,
        cy=card_cy,
        theme=theme,
        base=img2
    )

    # --------------------------------------------------------------------------
    # 4. Fitted Team Names Below Cards
    # --------------------------------------------------------------------------
    team_name_max_width = 680
    name_top_y = card_cy + 210 + 26  # 816

    # Team A Name
    a_lines, a_font, _ = fit_team_name_lines(team_a_name, team_name_max_width, initial_size=62, min_size=32, family=theme.font_family)
    a_curr_y = name_top_y
    for line in a_lines:
        b = draw2.textbbox((0, 0), line, font=a_font)
        lw = b[2] - b[0]
        lh = b[3] - b[1]
        draw2.text((left_cx - lw // 2, a_curr_y), line, fill=(255, 255, 255, 255), font=a_font)
        a_curr_y += lh + 8

    # Team B Name
    b_lines, b_font, _ = fit_team_name_lines(team_b_name, team_name_max_width, initial_size=62, min_size=32, family=theme.font_family)
    b_curr_y = name_top_y
    for line in b_lines:
        b = draw2.textbbox((0, 0), line, font=b_font)
        lw = b[2] - b[0]
        lh = b[3] - b[1]
        draw2.text((right_cx - lw // 2, b_curr_y), line, fill=(255, 255, 255, 255), font=b_font)
        b_curr_y += lh + 8

    # --------------------------------------------------------------------------
    # 5. Centered Footer Plate: Date, Venue, City
    # --------------------------------------------------------------------------
    start_utc = m.get("startTimeUtc", "")
    date_str = format_date_display(start_utc)

    venue = (m.get("venue") or "").strip()
    city = (m.get("city") or "").strip()
    country = (m.get("country") or "").strip()

    loc_parts = []
    if venue:
        loc_parts.append(venue)
    if city and city not in venue:
        loc_parts.append(city)
    elif country and not city and country not in venue:
        loc_parts.append(country)

    loc_str = ", ".join(loc_parts).upper()

    footer_items = [date_str]
    if loc_str:
        footer_items.append(loc_str)

    footer_text = "   •   ".join(footer_items)

    footer_font_size = 36
    footer_font = get_font(footer_font_size, weight="bold", family=theme.font_family)
    bbox_footer = draw2.textbbox((0, 0), footer_text, font=footer_font)

    # Scale down footer font if text is very long
    while (bbox_footer[2] - bbox_footer[0]) > (w2 - 340) and footer_font_size > 24:
        footer_font_size -= 2
        footer_font = get_font(footer_font_size, weight="bold", family=theme.font_family)
        bbox_footer = draw2.textbbox((0, 0), footer_text, font=footer_font)

    text_w = bbox_footer[2] - bbox_footer[0]
    text_h = bbox_footer[3] - bbox_footer[1]

    cal_icon_size = 36
    cal_spacing = 20
    footer_content_w = cal_icon_size + cal_spacing + text_w

    footer_w = max(720, min(footer_content_w + 110, w2 - 120))
    footer_h = 96
    footer_y = h2 - 146  # 1114
    fx0 = (w2 - footer_w) // 2

    # Outer subtle footer shadow & plate
    draw2.rounded_rectangle([fx0 - 4, footer_y - 4, fx0 + footer_w + 4, footer_y + footer_h + 4], radius=28, fill=(0, 0, 0, 110))
    draw2.rounded_rectangle([fx0, footer_y, fx0 + footer_w, footer_y + footer_h], radius=26, fill=theme.panel_color, outline=theme.panel_border, width=4)

    # Centered Vector calendar + Text inside footer
    content_start_x = (w2 - footer_content_w) // 2
    draw_vector_calendar_icon(draw2, content_start_x, footer_y + 30, size=cal_icon_size, color=theme.highlight)
    draw2.text((content_start_x + cal_icon_size + cal_spacing, footer_y + 26), footer_text, fill=(255, 255, 255), font=footer_font)

    # --------------------------------------------------------------------------
    # 6. Downsample from 2400x1260 to 1200x630 using Lanczos
    # --------------------------------------------------------------------------
    final_img = img2.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")
    final_img.save(str(output_path), format="PNG", optimize=True)
    return str(output_path)


# ==============================================================================
# 7. Concurrent Batch Generator
# ==============================================================================

def generate_all_match_images(
    matches: List[NormalizedMatch],
    output_dir: Union[str, Path] = MATCH_IMAGES_DIR,
    base_url: str = MATCH_IMAGES_RAW_BASE_URL,
    max_workers: int = 8,
    force: bool = False
) -> List[NormalizedMatch]:
    """
    Renders matchday graphic cards for all provided matches concurrently.
    Sets matchImage and matchImageUrl on each match.
    Avoids re-generating existing images unless force=True.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(matches)
    if total == 0:
        return matches

    logger.info(f"Generating matchday banner images for {total} matches (workers={max_workers})...")

    def render_worker(m: NormalizedMatch) -> Tuple[int, bool]:
        img_filename = f"{m.id}.png"
        target_path = output_dir / img_filename
        m.matchImage = f"images/matches/{img_filename}"
        m.matchImageUrl = f"{base_url}/{img_filename}"

        if not force and target_path.exists() and target_path.stat().st_size > 5000:
            return m.id, False  # Already exists

        try:
            generate_match_card(m, target_path)
            return m.id, True
        except Exception as e:
            logger.error(f"Failed to generate card for match {m.id} ({m.teamAName} vs {m.teamBName}): {e}")
            return m.id, False

    completed = 0
    generated = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(render_worker, m) for m in matches]
        for f in as_completed(futures):
            completed += 1
            mid, was_generated = f.result()
            if was_generated:
                generated += 1
            else:
                skipped += 1
            if completed % 25 == 0 or completed == total:
                logger.info(f"Image generation progress: {completed}/{total} (generated: {generated}, skipped: {skipped})")

    logger.info(f"Match banner generation finished: {generated} generated, {skipped} up-to-date.")
    return matches
