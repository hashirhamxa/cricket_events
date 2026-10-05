"""Tests for CricbuzzParser using offline fixtures."""

from pathlib import Path
import pytest
from src.parser import CricbuzzParser

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_parse_rsc_schedule_fixture():
    fixture_path = FIXTURES_DIR / "mock_schedule_rsc.html"
    html = fixture_path.read_text(encoding="utf-8")

    parser = CricbuzzParser()
    matches = parser.parse_schedule_html(html, category_hint="international")

    assert len(matches) == 2
    m1 = matches[0]
    assert m1["matchId"] == 174134
    assert m1["seriesId"] == 13281
    assert m1["matchDesc"] == "3rd T20I"
    assert m1["matchFormat"] == "T20"
    assert m1["team1"]["teamName"] == "South Korea"
    assert m1["team2"]["teamName"] == "Indonesia"
    assert m1["venueInfo"]["ground"] == "Yeonhui Cricket Ground "
    assert m1["venueInfo"]["city"] == "Incheon"


def test_parse_rsc_teams_fixture():
    fixture_path = FIXTURES_DIR / "mock_teams_rsc.html"
    html = fixture_path.read_text(encoding="utf-8")

    parser = CricbuzzParser()
    teams = parser.parse_team_directory_html(html, category_hint="international")

    assert len(teams) == 3
    t_names = [t["teamName"] for t in teams]
    assert "India" in t_names
    assert "Pakistan" in t_names
    assert "Australia" in t_names


def test_parse_empty_html():
    parser = CricbuzzParser()
    assert parser.parse_schedule_html("") == []
    assert parser.parse_team_directory_html("") == []


def test_dom_fallback():
    html = """
    <html>
        <body>
            <div class="cb-col cb-col-100">
                <a href="/live-cricket-scores/151554/ind-vs-wi-3rd-odi-west-indies-tour-of-india-2026">
                    IND vs WI - 3rd ODI
                </a>
            </div>
        </body>
    </html>
    """
    parser = CricbuzzParser()
    matches = parser.parse_schedule_html(html, category_hint="international")
    assert len(matches) == 1
    assert matches[0]["matchId"] == 151554
    assert matches[0]["format"] == "ODI"
